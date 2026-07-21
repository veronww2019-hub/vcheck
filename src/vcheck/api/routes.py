"""Versioned HTTP routes."""

from __future__ import annotations

from fastapi import APIRouter, Request, status

from vcheck.domain.models import (
    AnalyseMessageRequest,
    AnalyseMessageResponse,
    HealthResponse,
    ModelStatusResponse,
    RuleSummary,
    SubmitReportRequest,
    SubmitReportResponse,
)
from vcheck.services.analyser import MessageAnalyser
from vcheck.services.contextual_analyser import ContextualMessageAnalyser
from vcheck.services.datahub_context import DataHubContextService
from vcheck.services.ml_classifier import MlClassifier
from vcheck.services.report_service import CommunityReportService

router = APIRouter()


def _ml_classifier(request: Request) -> MlClassifier:
    return request.app.state.ml_classifier


def _datahub_context(
    request: Request,
) -> DataHubContextService:
    """Return the shared DataHub context service."""

    return request.app.state.datahub_context


def _analyser(
    request: Request,
) -> ContextualMessageAnalyser:
    """Build the rule/ML analyser with DataHub context."""

    message_analyser = MessageAnalyser(
        ml_classifier=_ml_classifier(request)
    )

    return ContextualMessageAnalyser(
        message_analyser=message_analyser,
        datahub_context=_datahub_context(request),
    )


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

def _community_report_service(
    request: Request,
) -> CommunityReportService:
    """Return the shared community-report service."""

    return request.app.state.community_report_service

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

@router.post(
    "/reports",
    response_model=SubmitReportResponse,
    status_code=201,
)
def submit_community_report(
    payload: SubmitReportRequest,
    request: Request,
) -> SubmitReportResponse:
    """Sanitise and record an unverified community report."""

    result = _community_report_service(
        request
    ).submit_report(
        text=payload.text,
        category=payload.category,
    )

    return SubmitReportResponse.model_validate(result)