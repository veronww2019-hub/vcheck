"""Tests for sanitised community-report submission."""

from __future__ import annotations

import csv
from pathlib import Path

from vcheck.services.report_service import (
    CommunityReportService,
    sanitise_report_text,
)


class FakeMetadataWriter:
    """Record DataHub write-back calls without using Docker."""

    def __init__(self) -> None:
        self.calls: list[dict[str, object]] = []

    def update(
        self,
        *,
        record_count: int,
        report_id: str,
        submitted_at: str,
    ) -> None:
        self.calls.append(
            {
                "record_count": record_count,
                "report_id": report_id,
                "submitted_at": submitted_at,
            }
        )


class BrokenMetadataWriter:
    """Simulate DataHub being unavailable."""

    def update(
        self,
        *,
        record_count: int,
        report_id: str,
        submitted_at: str,
    ) -> None:
        raise ConnectionError("DataHub is offline")


def _read_rows(path: Path) -> list[dict[str, str]]:
    with path.open(
        "r",
        encoding="utf-8-sig",
        newline="",
    ) as file:
        return list(csv.DictReader(file))


def test_sanitise_report_text_masks_sensitive_values() -> None:
    original = (
        "Email victim@example.com or call +60 12-345 6789. "
        "Open https://fake.example/login."
    )

    result = sanitise_report_text(original)

    assert "victim@example.com" not in result
    assert "+60 12-345 6789" not in result
    assert "https://fake.example/login" not in result
    assert "[EMAIL]" in result
    assert "[PHONE_OR_ACCOUNT]" in result
    assert "[URL]" in result


def test_report_is_saved_as_unverified(
    tmp_path: Path,
) -> None:
    csv_path = tmp_path / "community_reports.csv"
    writer = FakeMetadataWriter()

    service = CommunityReportService(
        csv_path=csv_path,
        metadata_writer=writer,
    )

    result = service.submit_report(
        text=(
            "Akaun anda akan dibekukan. "
            "Hubungi +60 12-345 6789 melalui "
            "http://fake.example."
        ),
        category="banking",
    )

    rows = _read_rows(csv_path)

    assert len(rows) == 1
    assert rows[0]["review_status"] == "unverified"
    assert rows[0]["allowed_for_decision"] == "false"
    assert "[PHONE_OR_ACCOUNT]" in rows[0]["sanitised_text"]
    assert "[URL]" in rows[0]["sanitised_text"]

    assert result["saved_locally"] is True
    assert result["allowed_for_decision"] is False
    assert result["datahub_writeback_available"] is True

    assert len(writer.calls) == 1
    assert writer.calls[0]["record_count"] == 1


def test_report_still_saves_when_datahub_is_offline(
    tmp_path: Path,
) -> None:
    csv_path = tmp_path / "community_reports.csv"

    service = CommunityReportService(
        csv_path=csv_path,
        metadata_writer=BrokenMetadataWriter(),
    )

    result = service.submit_report(
        text="Please pay through http://fake.example.",
        category="payment",
    )

    rows = _read_rows(csv_path)

    assert len(rows) == 1
    assert result["saved_locally"] is True
    assert result["datahub_writeback_available"] is False
    assert result["writeback_warning"] is not None