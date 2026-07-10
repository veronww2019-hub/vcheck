"""Safe loading and inference wrapper for the trained scikit-learn model."""

from __future__ import annotations

import json
import logging
from pathlib import Path
from typing import Any

import joblib

from vcheck.domain.models import MachineLearningAssessment, MlPredictedLabel

logger = logging.getLogger(__name__)


class MlClassifier:
    """Load the model once and provide a stable, typed prediction interface."""

    def __init__(self, model_path: Path, metadata_path: Path) -> None:
        self._model_path = model_path
        self._metadata_path = metadata_path
        self._model: Any | None = None
        self._metadata: dict[str, Any] = {}
        self._load_error: str | None = None
        self.reload()

    @property
    def available(self) -> bool:
        return self._model is not None

    @property
    def model_path(self) -> Path:
        return self._model_path

    @property
    def metadata(self) -> dict[str, Any]:
        return dict(self._metadata)

    @property
    def load_error(self) -> str | None:
        return self._load_error

    def reload(self) -> None:
        self._model = None
        self._metadata = {}
        self._load_error = None

        if not self._model_path.exists() or not self._metadata_path.exists():
            self._load_error = "Model artifacts have not been generated yet."
            return

        try:
            self._model = joblib.load(self._model_path)
            self._metadata = json.loads(self._metadata_path.read_text(encoding="utf-8"))
        except (OSError, ValueError, TypeError, json.JSONDecodeError) as exc:
            logger.exception("Unable to load ML model artifacts")
            self._model = None
            self._metadata = {}
            self._load_error = f"Unable to load model artifacts: {type(exc).__name__}"

    def assess(self, text: str) -> MachineLearningAssessment:
        if self._model is None:
            return MachineLearningAssessment(
                available=False,
                predicted_label=MlPredictedLabel.UNAVAILABLE,
                score_contribution=0,
                explanation=(
                    "The trained model is unavailable, so this result uses explainable rules only."
                ),
            )

        probability = float(self._model.predict_proba([text])[0][1])
        predicted_label = (
            MlPredictedLabel.SUSPICIOUS
            if probability >= 0.5
            else MlPredictedLabel.LEGITIMATE
        )
        confidence = probability if probability >= 0.5 else 1.0 - probability
        contribution = self._score_contribution(probability)

        return MachineLearningAssessment(
            available=True,
            predicted_label=predicted_label,
            suspicious_probability=round(probability, 4),
            confidence=round(confidence, 4),
            score_contribution=contribution,
            model_version=self._metadata.get("model_version"),
            trained_at=self._metadata.get("trained_at"),
            dataset_version=self._metadata.get("dataset_version"),
            explanation=(
                "The text model provides supporting evidence only. Its contribution is capped "
                "at 30 points and cannot reduce warnings found by deterministic rules."
            ),
        )

    @staticmethod
    def _score_contribution(suspicious_probability: float) -> int:
        if suspicious_probability >= 0.90:
            return 30
        if suspicious_probability >= 0.75:
            return 20
        if suspicious_probability >= 0.55:
            return 10
        return 0
