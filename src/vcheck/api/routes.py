"""Versioned HTTP routes."""

from __future__ import annotations

from fastapi import APIRouter, Request, status

from vcheck.domain.models import (
    AnalyseMessageRequest,
    AnalyseMessageResponse,
    HealthResponse,
    RuleSummary,
)
from vcheck.services.analyser import MessageAnalyser

router = APIRouter()
analyser = MessageAnalyser()


@router.get(
    "/health",
    response_model=HealthResponse,
    tags=["System"],
    summary="Check whether the service is running",
)
def health(request: Request) -> HealthResponse:
    settings = request.app.state.settings
    return HealthResponse(
        status="ok",
        service=settings.app_name,
        version=settings.app_version,
        environment=settings.environment,
    )


@router.get(
    "/api/v1/rules",
    response_model=list[RuleSummary],
    tags=["Analysis"],
    summary="List the explainable Phase 1 text rules",
)
def list_rules() -> list[RuleSummary]:
    return [
        RuleSummary(
            code=rule.code,
            title=rule.title,
            category=rule.category,
            severity_points=rule.severity_points,
            explanation=rule.explanation,
        )
        for rule in analyser.rules
    ]


@router.post(
    "/api/v1/analyse",
    response_model=AnalyseMessageResponse,
    status_code=status.HTTP_200_OK,
    tags=["Analysis"],
    summary="Assess the risk signals in a suspicious message",
)
def analyse_message(
    payload: AnalyseMessageRequest,
    request: Request,
) -> AnalyseMessageResponse:
    return analyser.analyse(
        text=payload.text,
        request_id=request.state.request_id,
    )
