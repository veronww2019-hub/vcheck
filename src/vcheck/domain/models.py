"""Typed request and response models for VCheck."""

from __future__ import annotations

from enum import Enum

from pydantic import BaseModel, ConfigDict, Field, field_validator


class RiskLevel(str, Enum):
    LOW = "Low"
    MEDIUM = "Medium"
    HIGH = "High"


class SignalCategory(str, Enum):
    PRESSURE = "pressure"
    FINANCIAL = "financial"
    CREDENTIALS = "credentials"
    IMPERSONATION = "impersonation"
    REWARD = "reward"
    SECRECY = "secrecy"
    REMOTE_ACCESS = "remote_access"
    LINK = "link"


class MlPredictedLabel(str, Enum):
    SUSPICIOUS = "suspicious"
    LEGITIMATE = "legitimate"
    UNAVAILABLE = "unavailable"


class AnalyseMessageRequest(BaseModel):
    model_config = ConfigDict(
        str_strip_whitespace=True,
        json_schema_extra={
            "examples": [
                {
                    "text": (
                        "URGENT: Your parcel is being held. Pay RM2 now at "
                        "http://parcel-payment.example or delivery will be cancelled."
                    )
                }
            ]
        },
    )

    text: str = Field(
        min_length=3,
        max_length=10_000,
        description="Message text to assess. Do not include unnecessary personal information.",
    )

    @field_validator("text")
    @classmethod
    def reject_blank_like_text(cls, value: str) -> str:
        if not any(character.isalnum() for character in value):
            raise ValueError("Message must contain at least one letter or number.")
        return value


class MatchedSignal(BaseModel):
    code: str
    title: str
    category: SignalCategory
    severity_points: int = Field(ge=1, le=100)
    explanation: str
    matched_excerpt: str | None = None


class ExtractedUrl(BaseModel):
    original: str
    normalised: str
    hostname: str | None
    uses_https: bool
    is_ip_address: bool
    uses_punycode: bool
    is_known_shortener: bool
    has_suspicious_tld: bool


class MachineLearningAssessment(BaseModel):
    available: bool
    predicted_label: MlPredictedLabel
    suspicious_probability: float | None = Field(default=None, ge=0, le=1)
    confidence: float | None = Field(default=None, ge=0, le=1)
    score_contribution: int = Field(ge=0, le=30)
    model_version: str | None = None
    trained_at: str | None = None
    dataset_version: str | None = None
    explanation: str


class AnalysisMetadata(BaseModel):
    analysis_version: str
    rules_evaluated: int = Field(ge=0)
    processing_time_ms: float = Field(ge=0)
    input_fingerprint: str


class AnalyseMessageResponse(BaseModel):
    request_id: str
    risk_level: RiskLevel
    risk_score: int = Field(ge=0, le=100)
    rule_score: int = Field(ge=0, le=100)
    summary: str
    warning_signs: list[MatchedSignal]
    extracted_urls: list[ExtractedUrl]
    machine_learning: MachineLearningAssessment
    recommended_actions: list[str]
    metadata: AnalysisMetadata
    disclaimer: str


class HealthResponse(BaseModel):
    status: str
    service: str
    version: str
    environment: str
    model_available: bool


class RuleSummary(BaseModel):
    code: str
    title: str
    category: SignalCategory
    severity_points: int
    explanation: str


class ModelStatusResponse(BaseModel):
    available: bool
    model_path: str
    model_version: str | None = None
    trained_at: str | None = None
    dataset_version: str | None = None
    training_rows: int | None = Field(default=None, ge=0)
    message: str
