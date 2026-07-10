"""Core suspicious-message analysis service."""

from __future__ import annotations

import hashlib
import ipaddress
import re
import time
import unicodedata
from dataclasses import dataclass
from urllib.parse import urlparse

from vcheck.domain.models import (
    AnalyseMessageResponse,
    AnalysisMetadata,
    ExtractedUrl,
    MachineLearningAssessment,
    MatchedSignal,
    MlPredictedLabel,
    RiskLevel,
    SignalCategory,
)
from vcheck.domain.rules import TEXT_RULES, TextRule
from vcheck.services.ml_classifier import MlClassifier

URL_PATTERN = re.compile(
    r"(?P<url>(?:https?://|www\.)[^\s<>\[\]{}\"']+)",
    re.IGNORECASE,
)

TRAILING_URL_PUNCTUATION = ".,;:!?)]}"

KNOWN_SHORTENERS = frozenset(
    {
        "bit.ly",
        "tinyurl.com",
        "t.co",
        "goo.gl",
        "is.gd",
        "ow.ly",
        "buff.ly",
        "cutt.ly",
        "rebrand.ly",
    }
)

# These TLDs are not automatically malicious. They only receive a small warning
# because they merit closer verification in unsolicited payment/login messages.
WATCHLIST_TLDS = frozenset({"zip", "top", "xyz", "click", "link", "work", "support"})


@dataclass(frozen=True, slots=True)
class AnalysisResult:
    risk_score: int
    risk_level: RiskLevel
    signals: tuple[MatchedSignal, ...]
    urls: tuple[ExtractedUrl, ...]


class MessageAnalyser:
    """Run deterministic, auditable Phase 1 analysis."""

    analysis_version = "hybrid-0.2.0"

    def __init__(
        self,
        rules: tuple[TextRule, ...] = TEXT_RULES,
        ml_classifier: MlClassifier | None = None,
    ) -> None:
        self._rules = rules
        self._ml_classifier = ml_classifier

    @property
    def rules(self) -> tuple[TextRule, ...]:
        return self._rules

    def analyse(self, text: str, request_id: str) -> AnalyseMessageResponse:
        started = time.perf_counter()
        normalised_text = self._normalise_text(text)

        signals = list(self._match_text_rules(normalised_text))
        urls = self._extract_and_assess_urls(normalised_text)
        signals.extend(self._signals_from_urls(urls))
        signals = self._deduplicate_signals(signals)

        rule_score = min(sum(signal.severity_points for signal in signals), 100)
        machine_learning = (
            self._ml_classifier.assess(normalised_text)
            if self._ml_classifier is not None
            else self._unavailable_ml_assessment()
        )
        risk_score = min(rule_score + machine_learning.score_contribution, 100)
        risk_level = self._risk_level(risk_score)

        processing_time_ms = round((time.perf_counter() - started) * 1000, 3)
        fingerprint = hashlib.sha256(normalised_text.encode("utf-8")).hexdigest()[:16]

        return AnalyseMessageResponse(
            request_id=request_id,
            risk_level=risk_level,
            risk_score=risk_score,
            rule_score=rule_score,
            summary=self._build_summary(
                risk_level, signals, urls, machine_learning.score_contribution
            ),
            warning_signs=signals,
            extracted_urls=urls,
            machine_learning=machine_learning,
            recommended_actions=self._recommended_actions(risk_level, bool(urls)),
            metadata=AnalysisMetadata(
                analysis_version=self.analysis_version,
                rules_evaluated=len(self._rules),
                processing_time_ms=processing_time_ms,
                input_fingerprint=fingerprint,
            ),
            disclaimer=(
                "VCheck provides an automated risk indication, not proof that a "
                "message is legitimate or fraudulent. Verify important requests through "
                "official channels."
            ),
        )

    @staticmethod
    def _unavailable_ml_assessment() -> MachineLearningAssessment:
        return MachineLearningAssessment(
            available=False,
            predicted_label=MlPredictedLabel.UNAVAILABLE,
            score_contribution=0,
            explanation="No ML classifier was configured; explainable rules were used only.",
        )

    @staticmethod
    def _normalise_text(text: str) -> str:
        unicode_normalised = unicodedata.normalize("NFKC", text)
        return re.sub(r"\s+", " ", unicode_normalised).strip()

    @staticmethod
    def _safe_excerpt(match: re.Match[str], limit: int = 80) -> str:
        excerpt = match.group(0).strip()
        return excerpt if len(excerpt) <= limit else f"{excerpt[: limit - 1]}…"

    def _match_text_rules(self, text: str) -> tuple[MatchedSignal, ...]:
        matched: list[MatchedSignal] = []
        for rule in self._rules:
            match = rule.pattern.search(text)
            if not match:
                continue
            matched.append(
                MatchedSignal(
                    code=rule.code,
                    title=rule.title,
                    category=rule.category,
                    severity_points=rule.severity_points,
                    explanation=rule.explanation,
                    matched_excerpt=self._safe_excerpt(match),
                )
            )
        return tuple(matched)

    @staticmethod
    def _normalise_url(raw_url: str) -> str:
        cleaned = raw_url.rstrip(TRAILING_URL_PUNCTUATION)
        return cleaned if "://" in cleaned else f"https://{cleaned}"

    def _extract_and_assess_urls(self, text: str) -> list[ExtractedUrl]:
        seen: set[str] = set()
        assessed: list[ExtractedUrl] = []

        for match in URL_PATTERN.finditer(text):
            original = match.group("url").rstrip(TRAILING_URL_PUNCTUATION)
            normalised = self._normalise_url(original)
            if normalised.lower() in seen:
                continue
            seen.add(normalised.lower())

            parsed = urlparse(normalised)
            hostname = parsed.hostname.lower() if parsed.hostname else None
            tld = hostname.rsplit(".", maxsplit=1)[-1] if hostname and "." in hostname else ""

            is_ip = False
            if hostname:
                try:
                    ipaddress.ip_address(hostname)
                    is_ip = True
                except ValueError:
                    is_ip = False

            assessed.append(
                ExtractedUrl(
                    original=original,
                    normalised=normalised,
                    hostname=hostname,
                    uses_https=parsed.scheme.lower() == "https",
                    is_ip_address=is_ip,
                    uses_punycode=bool(hostname and "xn--" in hostname),
                    is_known_shortener=bool(hostname and hostname in KNOWN_SHORTENERS),
                    has_suspicious_tld=tld in WATCHLIST_TLDS,
                )
            )

        return assessed

    @staticmethod
    def _signals_from_urls(urls: list[ExtractedUrl]) -> list[MatchedSignal]:
        if not urls:
            return []

        signals: list[MatchedSignal] = [
            MatchedSignal(
                code="contains_link",
                title="Message contains a link",
                category=SignalCategory.LINK,
                severity_points=6,
                explanation="Unsolicited links should be verified before opening.",
                matched_excerpt=urls[0].original,
            )
        ]

        checks = (
            (
                "ip_address_link",
                "Link uses an IP address",
                20,
                "A raw IP address hides the normal website name and requires extra caution.",
                lambda url: url.is_ip_address,
            ),
            (
                "punycode_link",
                "Link uses an internationalised punycode domain",
                18,
                "Punycode can be legitimate but may also disguise a look-alike domain.",
                lambda url: url.uses_punycode,
            ),
            (
                "shortened_link",
                "Shortened link",
                12,
                "A link shortener hides the final destination until the link is resolved.",
                lambda url: url.is_known_shortener,
            ),
            (
                "non_https_link",
                "Link does not use HTTPS",
                7,
                "The link uses unencrypted HTTP and should not be used for sensitive actions.",
                lambda url: not url.uses_https,
            ),
            (
                "watchlist_tld",
                "Link uses a domain ending that needs closer verification",
                6,
                "The domain ending is not proof of fraud, but deserves closer inspection.",
                lambda url: url.has_suspicious_tld,
            ),
        )

        for code, title, points, explanation, predicate in checks:
            matching_url = next((url for url in urls if predicate(url)), None)
            if matching_url:
                signals.append(
                    MatchedSignal(
                        code=code,
                        title=title,
                        category=SignalCategory.LINK,
                        severity_points=points,
                        explanation=explanation,
                        matched_excerpt=matching_url.original,
                    )
                )

        return signals

    @staticmethod
    def _deduplicate_signals(signals: list[MatchedSignal]) -> list[MatchedSignal]:
        unique: dict[str, MatchedSignal] = {}
        for signal in signals:
            unique.setdefault(signal.code, signal)
        return sorted(
            unique.values(),
            key=lambda signal: (-signal.severity_points, signal.code),
        )

    @staticmethod
    def _risk_level(score: int) -> RiskLevel:
        if score >= 45:
            return RiskLevel.HIGH
        if score >= 20:
            return RiskLevel.MEDIUM
        return RiskLevel.LOW

    @staticmethod
    def _build_summary(
        risk_level: RiskLevel,
        signals: list[MatchedSignal],
        urls: list[ExtractedUrl],
        ml_contribution: int,
    ) -> str:
        if not signals and ml_contribution == 0:
            return (
                "No warning signs in the current rule set or ML scoring bands were detected. "
                "This does not prove the message is safe."
            )

        if not signals:
            return (
                f"{risk_level.value} risk based on supporting ML evidence. "
                "No deterministic warning rule matched, so independent verification is important."
            )

        strongest = ", ".join(signal.title.lower() for signal in signals[:3])
        link_note = f" {len(urls)} link(s) were extracted for inspection." if urls else ""
        ml_note = (
            f" The ML model added {ml_contribution} supporting point(s)."
            if ml_contribution
            else ""
        )
        return (
            f"{risk_level.value} risk: detected {len(signals)} warning sign(s), "
            f"including {strongest}.{link_note}{ml_note}"
        )

    @staticmethod
    def _recommended_actions(risk_level: RiskLevel, contains_url: bool) -> list[str]:
        universal = [
            (
                "Verify the request using the organisation's official app, website, "
                "or published number."
            ),
            "Do not share passwords, OTP/TAC codes, PINs, or banking credentials.",
        ]

        if risk_level is RiskLevel.HIGH:
            actions = [
                "Do not reply, transfer money, or provide personal information.",
                "Contact the claimed organisation through a separately verified channel.",
            ]
        elif risk_level is RiskLevel.MEDIUM:
            actions = [
                "Pause before acting and independently verify the sender and request.",
            ]
        else:
            actions = [
                "Remain cautious if the sender is unfamiliar or the request is unexpected.",
            ]

        if contains_url:
            actions.append(
                "Do not open the submitted link until its domain is independently verified."
            )

        return actions + universal
