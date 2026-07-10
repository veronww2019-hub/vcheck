"""Application configuration.

Phase 1 deliberately keeps configuration simple and dependency-free. Environment
variables can override the values that are likely to change between machines.
"""

from __future__ import annotations

import os
from dataclasses import dataclass


def _split_origins(value: str) -> tuple[str, ...]:
    return tuple(origin.strip() for origin in value.split(",") if origin.strip())


@dataclass(frozen=True, slots=True)
class Settings:
    app_name: str = "VCheck API"
    app_version: str = "0.1.0"
    environment: str = os.getenv("VCHECK_ENV", "development")
    log_level: str = os.getenv("VCHECK_LOG_LEVEL", "INFO").upper()
    allowed_origins: tuple[str, ...] = _split_origins(
        os.getenv(
            "VCHECK_ALLOWED_ORIGINS",
            "http://localhost:3000,http://localhost:5173,http://127.0.0.1:5173",
        )
    )


settings = Settings()
