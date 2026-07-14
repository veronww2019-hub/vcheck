"""Tests for analysis enriched with DataHub evidence context."""

from __future__ import annotations

from typing import Any

from vcheck.services.analyser import MessageAnalyser
from vcheck.services.contextual_analyser import (
    ContextualMessageAnalyser,
)


class FakeDataHubContext:
    """Return predictable evidence context without Docker."""

    def __init__(
        self,
        bundle: dict[str, Any],
    ) -> None:
        self.bundle = bundle

    def get_context_bundle(self) -> dict[str, Any]:
        return self.bundle


class BrokenDataHubContext:
    """Simulate an unexpected DataHub integration error."""

    def get_context_bundle(self) -> dict[str, Any]:
        raise RuntimeError("Unexpected test error")


def test_context_is_added_to_analysis_response() -> None:
    context = FakeDataHubContext(
        {
            "available": True,
            "selected_evidence": [
                {
                    "name": "VCheck Reviewed Scam Guidance",
                    "urn": "urn:li:dataset:official",
                    "source_classification": (
                        "official_style_guidance"
                    ),
                    "review_status": "reviewed",
                    "freshness_status": "current",
                    "reliability": "high",
                    "configured_evidence_role": "primary",
                    "decision": "selected",
                    "role": "primary",
                    "reason": (
                        "The source is reviewed, current, and approved "
                        "as primary guidance."
                    ),
                },
                {
                    "name": "VCheck Synthetic Scam Patterns",
                    "urn": "urn:li:dataset:synthetic",
                    "source_classification": "synthetic",
                    "review_status": "reviewed",
                    "freshness_status": "current",
                    "reliability": "medium",
                    "configured_evidence_role": (
                        "pattern_support"
                    ),
                    "decision": "selected",
                    "role": "supporting_only",
                    "reason": (
                        "Synthetic evidence is supporting only."
                    ),
                },
            ],
            "excluded_evidence": [
                {
                    "name": "VCheck Community Reports",
                    "urn": "urn:li:dataset:community",
                    "source_classification": "community",
                    "review_status": "unverified",
                    "freshness_status": "current",
                    "reliability": "low",
                    "configured_evidence_role": (
                        "excluded_until_reviewed"
                    ),
                    "decision": "excluded",
                    "role": "excluded",
                    "reason": (
                        "The source is explicitly not approved for "
                        "decision-making."
                    ),
                }
            ],
            "provenance_summary": (
                "Selected 2 evidence sources and excluded 1 source."
            ),
            "warning": None,
        }
    )

    analyser = ContextualMessageAnalyser(
        message_analyser=MessageAnalyser(),
        datahub_context=context,
    )

    result = analyser.analyse(
        text=(
            "Tindakan segera: akaun anda akan dibekukan. "
            "Sahkan OTP sekarang."
        ),
        request_id="context-test",
    )

    assert result.datahub_context_available is True
    assert len(result.selected_evidence) == 2
    assert len(result.excluded_evidence) == 1
    assert result.selected_evidence[0].role == "primary"
    assert result.selected_evidence[1].role == "supporting_only"
    assert result.excluded_evidence[0].role == "excluded"
    assert result.context_warning is None


def test_unexpected_context_failure_does_not_break_analysis() -> None:
    analyser = ContextualMessageAnalyser(
        message_analyser=MessageAnalyser(),
        datahub_context=BrokenDataHubContext(),
    )

    result = analyser.analyse(
        text="Please pay RM5 now.",
        request_id="fallback-test",
    )

    assert result.risk_score > 0
    assert result.datahub_context_available is False
    assert result.selected_evidence == []
    assert result.excluded_evidence == []
    assert result.context_warning is not None
    assert "Unexpected test error" in result.context_warning