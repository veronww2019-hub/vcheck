"""Register VCheck evidence datasets and trust metadata in DataHub."""

from __future__ import annotations

import os
import sys
from pathlib import Path
from typing import Any

import pandas as pd
from datahub.emitter.mce_builder import make_dataset_urn
from datahub.emitter.mcp import MetadataChangeProposalWrapper
from datahub.emitter.rest_emitter import DatahubRestEmitter
from datahub.metadata.schema_classes import DatasetPropertiesClass

PROJECT_ROOT = Path(__file__).resolve().parents[1]
EVIDENCE_DIR = PROJECT_ROOT / "data" / "evidence"

DATAHUB_GMS_URL = os.getenv(
    "DATAHUB_GMS_URL",
    "http://localhost:8080",
)

DATA_PLATFORM = "vcheck"
ENVIRONMENT = "PROD"


EVIDENCE_SOURCES: dict[str, dict[str, Any]] = {
    "official_scam_guidance": {
        "filename": "official_scam_guidance.csv",
        "display_name": "VCheck Reviewed Scam Guidance",
        "description": (
            "Manually structured and reviewed scam-warning guidance used by "
            "VCheck as primary evidence. This prototype dataset is not presented "
            "as a direct government or law-enforcement database."
        ),
        "custom_properties": {
            "source_classification": "official_style_guidance",
            "review_status": "reviewed",
            "freshness_status": "current",
            "reliability_level": "high",
            "allowed_for_decision": "true",
            "evidence_role": "primary",
            "synthetic": "false",
            "contains_personal_data": "false",
            "jurisdiction": "Malaysia prototype",
        },
    },
    "verified_domains": {
        "filename": "verified_domains.csv",
        "display_name": "VCheck Verified Demonstration Domains",
        "description": (
            "Fictional demonstration domains used to test organisation and domain "
            "matching. These records do not claim to verify real organisations."
        ),
        "custom_properties": {
            "source_classification": "demonstration",
            "review_status": "reviewed",
            "freshness_status": "current",
            "reliability_level": "medium",
            "allowed_for_decision": "true",
            "evidence_role": "domain_demo",
            "synthetic": "true",
            "contains_personal_data": "false",
            "jurisdiction": "Demonstration only",
        },
    },
    "synthetic_scam_patterns": {
        "filename": "synthetic_scam_patterns.csv",
        "display_name": "VCheck Synthetic Scam Pattern Library",
        "description": (
            "Synthetic English and Malay suspicious-message patterns used only "
            "as supporting pattern evidence. They cannot independently confirm "
            "that a real message is fraudulent."
        ),
        "custom_properties": {
            "source_classification": "synthetic",
            "review_status": "reviewed",
            "freshness_status": "current",
            "reliability_level": "medium",
            "allowed_for_decision": "supporting_only",
            "evidence_role": "pattern_support",
            "synthetic": "true",
            "contains_personal_data": "false",
            "jurisdiction": "Malaysia prototype",
        },
    },
    "community_reports": {
        "filename": "community_reports.csv",
        "display_name": "VCheck Unverified Community Reports",
        "description": (
            "Fictional and sanitised community-style reports used to demonstrate "
            "evidence rejection. Reports remain unverified and are excluded from "
            "the trusted risk decision."
        ),
        "custom_properties": {
            "source_classification": "community",
            "review_status": "unverified",
            "freshness_status": "current",
            "reliability_level": "low",
            "allowed_for_decision": "false",
            "evidence_role": "excluded_until_reviewed",
            "synthetic": "true",
            "contains_personal_data": "false",
            "jurisdiction": "Malaysia prototype",
        },
    },
}


def register_evidence_source(
    emitter: DatahubRestEmitter,
    source_name: str,
    configuration: dict[str, Any],
) -> str:
    """Read one evidence CSV and register its metadata in DataHub."""

    csv_path = EVIDENCE_DIR / configuration["filename"]

    if not csv_path.exists():
        raise FileNotFoundError(f"Evidence file not found: {csv_path}")

    dataframe = pd.read_csv(csv_path)

    if dataframe.empty:
        raise ValueError(f"Evidence file contains no records: {csv_path}")

    dataset_urn = make_dataset_urn(
        platform=DATA_PLATFORM,
        name=f"vcheck.evidence.{source_name}",
        env=ENVIRONMENT,
    )

    custom_properties = {
        **configuration["custom_properties"],
        "record_count": str(len(dataframe)),
        "column_count": str(len(dataframe.columns)),
        "columns": ", ".join(str(column) for column in dataframe.columns),
        "file_format": "CSV",
        "local_path": str(csv_path),
        "data_owner": "VCheck",
        "prototype_status": "not_production_ready",
    }

    dataset_properties = DatasetPropertiesClass(
        name=configuration["display_name"],
        description=configuration["description"],
        customProperties=custom_properties,
    )

    metadata_event = MetadataChangeProposalWrapper(
        entityUrn=dataset_urn,
        aspect=dataset_properties,
    )

    emitter.emit(metadata_event)

    print(f"[REGISTERED] {configuration['display_name']}")
    print(f"             URN: {dataset_urn}")
    print(f"             Rows: {len(dataframe)}")
    print(
        "             Decision status: "
        f"{custom_properties['allowed_for_decision']}"
    )

    return dataset_urn


def main() -> int:
    """Register all VCheck evidence sources."""

    print("=" * 70)
    print("VCheck DataHub Evidence Registration")
    print("=" * 70)
    print(f"Project root: {PROJECT_ROOT}")
    print(f"Evidence directory: {EVIDENCE_DIR}")
    print(f"DataHub GMS: {DATAHUB_GMS_URL}")
    print()

    if not EVIDENCE_DIR.exists():
        print(f"[ERROR] Evidence directory does not exist: {EVIDENCE_DIR}")
        return 1

    emitter = DatahubRestEmitter(gms_server=DATAHUB_GMS_URL)

    try:
        print("Testing connection to DataHub...")
        emitter.test_connection()
        print("[OK] Connected to DataHub.")
        print()

        registered_urns: list[str] = []

        for source_name, configuration in EVIDENCE_SOURCES.items():
            urn = register_evidence_source(
                emitter=emitter,
                source_name=source_name,
                configuration=configuration,
            )
            registered_urns.append(urn)
            print()

        print("=" * 70)
        print(f"[SUCCESS] Registered {len(registered_urns)} evidence datasets.")
        print("=" * 70)

        for urn in registered_urns:
            print(urn)

        return 0

    except Exception as exc:
        print()
        print(f"[ERROR] Evidence registration failed: {exc}")
        return 1


if __name__ == "__main__":
    sys.exit(main())