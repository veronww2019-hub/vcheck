"""Versioned HTTP routes."""

from __future__ import annotations

from fastapi import APIRouter, Request, status

from vcheck.domain.models import (
    AnalyseMessageRequest,
    AnalyseMessageResponse,
    HealthResponse,
    ModelStatusResponse,
    RuleSummary,
)
from vcheck.services.analyser import MessageAnalyser
from vcheck.services.ml_classifier import MlClassifier

router = APIRouter()


def _ml_classifier(request: Request) -> MlClassifier:
    return request.app.state.ml_classifier


def _analyser(request: Request) -> MessageAnalyser:
    return MessageAnalyser(ml_classifier=_ml_classifier(request))


@router.get(
    "/health",
    response_model=HealthResponse,
    tags=["System"],
    summary="Check whether the service is running",
)
def health(request: Request) -> HealthResponse:
    settings = request.app.state.settings
    classifier = _ml_classifier(request)
    return HealthResponse(
        status="ok",
        service=settings.app_name,
        version=settings.app_version,
        environment=settings.environment,
        model_available=classifier.available,
    )


@router.get(
    "/api/v1/rules",
    response_model=list[RuleSummary],
    tags=["Analysis"],
    summary="List the explainable text rules",
)
def list_rules(request: Request) -> list[RuleSummary]:
    return [
        RuleSummary(
            code=rule.code,
            title=rule.title,
            category=rule.category,
            severity_points=rule.severity_points,
            explanation=rule.explanation,
        )
        for rule in _analyser(request).rules
    ]


@router.get(
    "/api/v1/model",
    response_model=ModelStatusResponse,
    tags=["Machine Learning"],
    summary="Inspect whether the trained model is available",
)
def model_status(request: Request) -> ModelStatusResponse:
    classifier = _ml_classifier(request)
    metadata = classifier.metadata
    return ModelStatusResponse(
        available=classifier.available,
        model_path=str(classifier.model_path),
        model_version=metadata.get("model_version"),
        trained_at=metadata.get("trained_at"),
        dataset_version=metadata.get("dataset_version"),
        training_rows=metadata.get("training_rows"),
        message=(
            "Model loaded and ready."
            if classifier.available
            else classifier.load_error or "Model unavailable."
        ),
    )


@router.post(
    "/api/v1/model/reload",
    response_model=ModelStatusResponse,
    tags=["Machine Learning"],
    summary="Reload model artifacts after local training",
)
def reload_model(request: Request) -> ModelStatusResponse:
    classifier = _ml_classifier(request)
    classifier.reload()
    return model_status(request)


@router.post(
    "/api/v1/analyse",
    response_model=AnalyseMessageResponse,
    status_code=status.HTTP_200_OK,
    tags=["Analysis"],
    summary="Assess a message with rules and supporting ML evidence",
)
def analyse_message(
    payload: AnalyseMessageRequest,
    request: Request,
) -> AnalyseMessageResponse:
    return _analyser(request).analyse(
        text=payload.text,
        request_id=request.state.request_id,
    )
