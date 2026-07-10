"""Application configuration loaded from environment variables."""

from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path


def _split_origins(value: str) -> tuple[str, ...]:
    return tuple(origin.strip() for origin in value.split(",") if origin.strip())


def _project_root() -> Path:
    # src/vcheck/core/config.py -> project root is four parents above this file.
    return Path(__file__).resolve().parents[3]


@dataclass(frozen=True, slots=True)
class Settings:
    app_name: str = "VCheck API"
    app_version: str = "0.2.0"
    environment: str = os.getenv("VCHECK_ENV", "development")
    log_level: str = os.getenv("VCHECK_LOG_LEVEL", "INFO").upper()
    allowed_origins: tuple[str, ...] = _split_origins(
        os.getenv(
            "VCHECK_ALLOWED_ORIGINS",
            "http://localhost:3000,http://localhost:5173,http://127.0.0.1:5173",
        )
    )
    model_path: Path = Path(
        os.getenv(
            "VCHECK_MODEL_PATH",
            str(_project_root() / "artifacts" / "suspicious_message_classifier.joblib"),
        )
    )
    model_metadata_path: Path = Path(
        os.getenv(
            "VCHECK_MODEL_METADATA_PATH",
            str(_project_root() / "artifacts" / "model_metadata.json"),
        )
    )


settings = Settings()
