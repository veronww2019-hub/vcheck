"""Explainable text-rule definitions used by the Phase 1 analyser."""

from __future__ import annotations

import re
from dataclasses import dataclass

from vcheck.domain.models import SignalCategory


@dataclass(frozen=True, slots=True)
class TextRule:
    code: str
    title: str
    category: SignalCategory
    severity_points: int
    explanation: str
    pattern: re.Pattern[str]


TEXT_RULES: tuple[TextRule, ...] = (
    TextRule(
        code="urgent_pressure",
        title="Urgent pressure",
        category=SignalCategory.PRESSURE,
        severity_points=12,
        explanation="The message pressures the recipient to act quickly before verifying it.",
        pattern=re.compile(
            r"\b(urgent|immediately|act now|right now|final warning|last chance|"
            r"within\s+\d+\s*(minutes?|hours?)|before it is too late)\b",
            re.IGNORECASE,
        ),
    ),
    TextRule(
        code="threatened_consequence",
        title="Threatened consequence",
        category=SignalCategory.PRESSURE,
        severity_points=16,
        explanation="The message threatens account, service, legal, or delivery consequences.",
        pattern=re.compile(
            r"\b(account (?:will be )?(?:blocked|closed|suspended|frozen)|"
            r"service (?:will be )?(?:terminated|disconnected)|legal action|"
            r"delivery (?:will be )?(?:cancelled|canceled)|police action)\b",
            re.IGNORECASE,
        ),
    ),
    TextRule(
        code="payment_request",
        title="Payment or transfer request",
        category=SignalCategory.FINANCIAL,
        severity_points=18,
        explanation="The message requests money, a fee, a deposit, or a bank transfer.",
        pattern=re.compile(
            r"\b(pay(?:ment)?|transfer|bank in|deposit|processing fee|release fee|"
            r"delivery fee|admin fee|send money|duitnow|rm\s?\d+(?:[.,]\d{1,2})?)\b",
            re.IGNORECASE,
        ),
    ),
    TextRule(
        code="credential_request",
        title="Sensitive credential request",
        category=SignalCategory.CREDENTIALS,
        severity_points=28,
        explanation="The message asks for credentials or security codes that should not be shared.",
        pattern=re.compile(
            r"\b(otp|tac|one[- ]time password|password|passcode|pin number|"
            r"verification code|login details|security answer)\b",
            re.IGNORECASE,
        ),
    ),
    TextRule(
        code="impersonation_claim",
        title="Organisation or authority impersonation",
        category=SignalCategory.IMPERSONATION,
        severity_points=10,
        explanation="The sender claims to represent a bank, authority, courier, or platform.",
        pattern=re.compile(
            r"\b(bank negara|lhdn|polis|police|court|customs|immigration|"
            r"bank officer|customer service|courier|parcel service|shopee|lazada)\b",
            re.IGNORECASE,
        ),
    ),
    TextRule(
        code="unexpected_reward",
        title="Unexpected reward or refund",
        category=SignalCategory.REWARD,
        severity_points=14,
        explanation="Unexpected rewards and refunds can be used to attract clicks or payments.",
        pattern=re.compile(
            r"\b(you (?:have )?won|winner|claim (?:your )?(?:prize|reward)|"
            r"cash prize|free gift|unexpected refund|rebate approved)\b",
            re.IGNORECASE,
        ),
    ),
    TextRule(
        code="secrecy_request",
        title="Request for secrecy",
        category=SignalCategory.SECRECY,
        severity_points=14,
        explanation="The sender discourages the recipient from checking with other people.",
        pattern=re.compile(
            r"\b(do not tell|don't tell|keep this secret|confidential transaction|"
            r"do not contact the bank|do not inform anyone)\b",
            re.IGNORECASE,
        ),
    ),
    TextRule(
        code="remote_access_request",
        title="Remote-access software request",
        category=SignalCategory.REMOTE_ACCESS,
        severity_points=30,
        explanation="The message asks the recipient to install or use remote-access software.",
        pattern=re.compile(
            r"\b(anydesk|teamviewer|remote desktop|screen sharing|"
            r"install this app to assist|remote access)\b",
            re.IGNORECASE,
        ),
    ),
)
