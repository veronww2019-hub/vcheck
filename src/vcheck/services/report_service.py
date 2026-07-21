"""Sanitise community reports and write their metadata to DataHub."""

from __future__ import annotations

import csv
import os
import re
import uuid
from datetime import datetime, timezone
from pathlib import Path
from threading import Lock
from typing import Protocol

from datahub.emitter.mcp import MetadataChangeProposalWrapper
from datahub.emitter.rest_emitter import DatahubRestEmitter
from datahub.metadata.schema_classes import DatasetPropertiesClass

PROJECT_ROOT = Path(__file__).resolve().parents[3]

DEFAULT_REPORT_PATH = (
    PROJECT_ROOT
    / "data"
    / "evidence"
    / "community_reports.csv"
)

COMMUNITY_DATASET_URN = (
    "urn:li:dataset:(urn:li:dataPlatform:vcheck,"
    "vcheck.evidence.community_reports,PROD)"
)

CSV_COLUMNS = (
    "report_id",
    "category",
    "sanitised_text",
    "review_status",
    "allowed_for_decision",
)

URL_PATTERN = re.compile(
    r"(?i)\b(?:https?://|www\.)[^\s<>\"]+"
)

EMAIL_PATTERN = re.compile(
    r"(?i)\b[A-Z0-9._%+-]+@[A-Z0-9.-]+\.[A-Z]{2,}\b"
)

PHONE_OR_ACCOUNT_PATTERN = re.compile(
    r"(?<!\w)(?:\+?\d[\d\s().-]{6,}\d)(?!\w)"
)

WHITESPACE_PATTERN = re.compile(r"\s+")


class CommunityMetadataWriter(Protocol):
    """Interface for updating the DataHub community asset."""

    def update(
        self,
        *,
        record_count: int,
        report_id: str,
        submitted_at: str,
    ) -> None:
        """Update community-report metadata in DataHub."""


class DataHubCommunityMetadataWriter:
    """Push updated community-report metadata to DataHub."""

    def __init__(
        self,
        gms_url: str | None = None,
        token: str | None = None,
    ) -> None:
        self.gms_url = (
            gms_url
            or os.getenv("DATAHUB_GMS_URL")
            or "http://localhost:8080"
        )

        self.token = token or os.getenv("DATAHUB_GMS_TOKEN")

    def update(
        self,
        *,
        record_count: int,
        report_id: str,
        submitted_at: str,
    ) -> None:
        """Update the existing community-report dataset properties."""

        emitter_options: dict[str, str] = {
            "gms_server": self.gms_url,
        }

        if self.token:
            emitter_options["token"] = self.token

        emitter = DatahubRestEmitter(**emitter_options)
        emitter.test_connection()

        properties = DatasetPropertiesClass(
            name="VCheck Unverified Community Reports",
            description=(
                "Sanitised community-submitted suspicious-message "
                "reports. Reports remain unverified and are excluded "
                "from trusted evidence until reviewed."
            ),
            customProperties={
                "source_classification": "community",
                "review_status": "unverified",
                "freshness_status": "current",
                "reliability_level": "low",
                "allowed_for_decision": "false",
                "evidence_role": "excluded_until_reviewed",
                "synthetic": "mixed_demo_and_user_submitted",
                "contains_personal_data": "sanitised",
                "jurisdiction": "Malaysia prototype",
                "record_count": str(record_count),
                "file_format": "CSV",
                "data_owner": "VCheck",
                "prototype_status": "not_production_ready",
                "last_report_id": report_id,
                "last_report_submitted_at": submitted_at,
            },
        )

        event = MetadataChangeProposalWrapper(
            entityUrn=COMMUNITY_DATASET_URN,
            aspect=properties,
        )

        emitter.emit(event)


def sanitise_report_text(text: str) -> str:
    """Remove common sensitive identifiers from submitted text."""

    sanitised = URL_PATTERN.sub("[URL]", text)
    sanitised = EMAIL_PATTERN.sub("[EMAIL]", sanitised)
    sanitised = PHONE_OR_ACCOUNT_PATTERN.sub(
        "[PHONE_OR_ACCOUNT]",
        sanitised,
    )
    sanitised = WHITESPACE_PATTERN.sub(" ", sanitised).strip()

    # Prevent spreadsheet software from interpreting the text as a formula.
    if sanitised.startswith(("=", "+", "-", "@")):
        sanitised = f"'{sanitised}"

    return sanitised


class CommunityReportService:
    """Save sanitised reports and update DataHub context."""

    def __init__(
        self,
        csv_path: Path | None = None,
        metadata_writer: CommunityMetadataWriter | None = None,
    ) -> None:
        self.csv_path = csv_path or DEFAULT_REPORT_PATH
        self.metadata_writer = (
            metadata_writer
            or DataHubCommunityMetadataWriter()
        )
        self._write_lock = Lock()

    def submit_report(
        self,
        *,
        text: str,
        category: str,
    ) -> dict[str, object]:
        """Sanitise and save one report."""

        sanitised_text = sanitise_report_text(text)

        if not sanitised_text:
            raise ValueError(
                "The report contains no usable text after sanitisation."
            )

        submitted_at = datetime.now(timezone.utc).isoformat()
        report_id = self._make_report_id()

        normalised_category = (
            category.strip().lower().replace(" ", "_")
            or "unspecified"
        )

        row = {
            "report_id": report_id,
            "category": normalised_category,
            "sanitised_text": sanitised_text,
            "review_status": "unverified",
            "allowed_for_decision": "false",
        }

        with self._write_lock:
            self._ensure_csv_exists()
            self._append_row(row)
            record_count = self._count_records()

        writeback_available = True
        writeback_warning: str | None = None

        try:
            self.metadata_writer.update(
                record_count=record_count,
                report_id=report_id,
                submitted_at=submitted_at,
            )
        except Exception as exc:
            writeback_available = False
            writeback_warning = (
                "The sanitised report was saved locally, but DataHub "
                f"metadata write-back failed: {exc}"
            )

        return {
            "report_id": report_id,
            "category": normalised_category,
            "sanitised_text": sanitised_text,
            "submitted_at": submitted_at,
            "review_status": "unverified",
            "allowed_for_decision": False,
            "saved_locally": True,
            "datahub_writeback_available": writeback_available,
            "writeback_warning": writeback_warning,
            "explanation": (
                "The report was sanitised and stored as unverified "
                "community context. It is not permitted to influence "
                "trusted risk decisions until reviewed."
            ),
        }

    def _ensure_csv_exists(self) -> None:
        self.csv_path.parent.mkdir(
            parents=True,
            exist_ok=True,
        )

        if self.csv_path.exists() and self.csv_path.stat().st_size > 0:
            return

        with self.csv_path.open(
            "w",
            encoding="utf-8",
            newline="",
        ) as file:
            writer = csv.DictWriter(
                file,
                fieldnames=CSV_COLUMNS,
            )
            writer.writeheader()

    def _append_row(
        self,
        row: dict[str, str],
    ) -> None:
        with self.csv_path.open(
            "a",
            encoding="utf-8",
            newline="",
        ) as file:
            writer = csv.DictWriter(
                file,
                fieldnames=CSV_COLUMNS,
            )
            writer.writerow(row)

    def _count_records(self) -> int:
        with self.csv_path.open(
            "r",
            encoding="utf-8-sig",
            newline="",
        ) as file:
            return sum(1 for _ in csv.DictReader(file))

    @staticmethod
    def _make_report_id() -> str:
        timestamp = datetime.now(timezone.utc).strftime(
            "%Y%m%d%H%M%S"
        )
        suffix = uuid.uuid4().hex[:6].upper()

        return f"COM-{timestamp}-{suffix}"