"""Logging configuration for the API."""

from __future__ import annotations

import logging

from vcheck.core.config import settings


def configure_logging() -> None:
    """Configure consistent application logging once at startup."""
    logging.basicConfig(
        level=getattr(logging, settings.log_level, logging.INFO),
        format="%(asctime)s | %(levelname)s | %(name)s | %(message)s",
    )
