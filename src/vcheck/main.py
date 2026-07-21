"""FastAPI application entry point."""

from __future__ import annotations

import logging
import uuid
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from vcheck.api.routes import router
from vcheck.core.config import settings
from vcheck.core.logging import configure_logging
from vcheck.services.datahub_context import DataHubContextService
from vcheck.services.ml_classifier import MlClassifier
from vcheck.services.report_service import CommunityReportService

configure_logging()
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    """Create and close shared application services."""

    app.state.settings = settings

    app.state.ml_classifier = MlClassifier(
        model_path=settings.model_path,
        metadata_path=settings.model_metadata_path,
    )

    app.state.datahub_context = DataHubContextService()
    app.state.community_report_service = CommunityReportService()

    logger.info(
        "Starting %s version=%s environment=%s",
        settings.app_name,
        settings.app_version,
        settings.environment,
    )

    try:
        yield
    finally:
        app.state.datahub_context.close()
        logger.info("Stopping %s", settings.app_name)


app = FastAPI(
    title=settings.app_name,
    version=settings.app_version,
    description=(
        "Hybrid rules and machine-learning suspicious-message risk analysis. "
        "This prototype does not make definitive fraud determinations."
    ),
    lifespan=lifespan,
    docs_url="/docs",
    redoc_url="/redoc",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=list(settings.allowed_origins),
    allow_credentials=False,
    allow_methods=["GET", "POST"],
    allow_headers=["Content-Type", "X-Request-ID"],
    expose_headers=["X-Request-ID"],
)


@app.middleware("http")
async def add_request_id(request: Request, call_next):  # type: ignore[no-untyped-def]
    supplied_request_id = request.headers.get("X-Request-ID", "").strip()
    request_id = supplied_request_id[:100] if supplied_request_id else str(uuid.uuid4())
    request.state.request_id = request_id

    response = await call_next(request)
    response.headers["X-Request-ID"] = request_id
    return response


@app.exception_handler(Exception)
async def unexpected_exception_handler(request: Request, exc: Exception) -> JSONResponse:
    request_id = getattr(request.state, "request_id", "unknown")
    logger.exception("Unhandled error request_id=%s path=%s", request_id, request.url.path)
    return JSONResponse(
        status_code=500,
        content={
            "detail": "An unexpected server error occurred.",
            "request_id": request_id,
        },
        headers={"X-Request-ID": request_id},
    )


@app.get("/", tags=["System"], include_in_schema=False)
def root() -> dict[str, str]:
    return {
        "service": settings.app_name,
        "version": settings.app_version,
        "docs": "/docs",
        "health": "/health",
    }


app.include_router(router)
