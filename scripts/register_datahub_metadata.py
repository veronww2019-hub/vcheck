"""Register VCheck datasets and their lineage in local DataHub."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path

import pandas as pd
from datahub.metadata.urns import CorpUserUrn
from datahub.sdk import DataHubClient, Dataset, Tag

DATAHUB_SERVER = "http://localhost:8080"
OWNER = CorpUserUrn("datahub")


@dataclass(frozen=True, slots=True)
class DatasetDefinition:
    name: str
    display_name: str
    path: Path
    description: str
    source_type: str
    review_status: str
    tag_names: tuple[str, ...]


DATASET_DEFINITIONS: tuple[DatasetDefinition, ...] = (
    DatasetDefinition(
        name="vcheck.raw.synthetic_messages",
        display_name="VCheck Synthetic Messages",
        path=Path("data/raw/synthetic_messages.csv"),
        description=(
            "Deterministically generated fictional suspicious and legitimate "
            "messages used to support VCheck model development."
        ),
        source_type="synthetic",
        review_status="template_reviewed",
        tag_names=("vcheck", "synthetic", "training-input"),
    ),
    DatasetDefinition(
        name="vcheck.raw.manual_messages",
        display_name="VCheck Manually Reviewed Messages",
        path=Path("data/raw/manual_messages.csv"),
        description=(
            "Small collection of fictional Malaysian-style messages personally "
            "reviewed for the VCheck prototype."
        ),
        source_type="manually_curated_synthetic",
        review_status="personally_reviewed",
        tag_names=("vcheck", "synthetic", "personally-reviewed", "training-input"),
    ),
    DatasetDefinition(
        name="vcheck.raw.uci_sms_spam_collection",
        display_name="UCI SMS Spam Collection",
        path=Path("data/raw/uci_sms_spam_collection.csv"),
        description=(
            "Optional public SMS spam and ham dataset. Its labels describe "
            "spam and ham rather than confirmed scams."
        ),
        source_type="public_dataset",
        review_status="externally_sourced",
        tag_names=("vcheck", "public-data", "training-input"),
    ),
    DatasetDefinition(
        name="vcheck.processed.training_dataset",
        display_name="VCheck Processed Training Dataset",
        path=Path("data/processed/training_dataset.csv"),
        description=(
            "Validated, normalised, deduplicated training dataset assembled "
            "from available VCheck input sources."
        ),
        source_type="processed_training_data",
        review_status="pipeline_validated",
        tag_names=("vcheck", "processed", "model-training"),
    ),
)


TAG_DEFINITIONS: dict[str, tuple[str, str]] = {
    "vcheck": (
        "VCheck",
        "Asset belonging to the VCheck provenance-aware scam-risk prototype.",
    ),
    "synthetic": (
        "Synthetic",
        "Fictional data generated or written for testing and development.",
    ),
    "personally-reviewed": (
        "Personally Reviewed",
        "Content manually reviewed by the VCheck project developer.",
    ),
    "training-input": (
        "Training Input",
        "Dataset that contributes records to the model-training dataset.",
    ),
    "public-data": (
        "Public Data",
        "Dataset obtained from a publicly available external source.",
    ),
    "processed": (
        "Processed",
        "Dataset produced by validation, normalisation, or transformation.",
    ),
    "model-training": (
        "Model Training",
        "Dataset used directly to train or evaluate a machine-learning model.",
    ),
}


def get_file_properties(path: Path) -> dict[str, str]:
    """Return safe metadata properties for a local CSV file."""
    dataframe = pd.read_csv(path)

    modified_at = datetime.fromtimestamp(
        path.stat().st_mtime,
        tz=timezone.utc,
    ).isoformat()

    return {
        "local_path": path.as_posix(),
        "file_format": "CSV",
        "row_count": str(len(dataframe)),
        "column_count": str(len(dataframe.columns)),
        "last_modified_utc": modified_at,
        "contains_real_victim_data": "false",
    }


def register_tags(client: DataHubClient) -> dict[str, object]:
    """Create the tags used to classify VCheck assets."""
    tag_urns: dict[str, object] = {}

    for name, (display_name, description) in TAG_DEFINITIONS.items():
        tag = Tag(
            name=name,
            display_name=display_name,
            description=description,
            owners=[OWNER],
        )
        client.entities.upsert(tag)
        tag_urns[name] = tag.urn

        print(f"Registered tag: {tag.urn}")

    return tag_urns


def register_dataset(
    client: DataHubClient,
    definition: DatasetDefinition,
    tag_urns: dict[str, object],
) -> Dataset:
    """Register one local VCheck dataset."""
    properties = get_file_properties(definition.path)
    properties.update(
        {
            "source_type": definition.source_type,
            "review_status": definition.review_status,
            "project": "VCheck",
            "environment": "prototype",
        }
    )

    dataset = Dataset(
        platform="file",
        name=definition.name,
        env="PROD",
        display_name=definition.display_name,
        description=definition.description,
        subtype="CSV",
        custom_properties=properties,
        owners=[OWNER],
        tags=[tag_urns[name] for name in definition.tag_names],
    )

    client.entities.upsert(dataset)
    print(f"Registered dataset: {dataset.urn}")

    return dataset


def main() -> None:
    client = DataHubClient(server=DATAHUB_SERVER)
    tag_urns = register_tags(client)

    registered: dict[str, Dataset] = {}

    for definition in DATASET_DEFINITIONS:
        if not definition.path.exists():
            print(f"Skipped missing optional dataset: {definition.path}")
            continue

        registered[definition.name] = register_dataset(
            client=client,
            definition=definition,
            tag_urns=tag_urns,
        )

    processed_name = "vcheck.processed.training_dataset"
    processed_dataset = registered.get(processed_name)

    if processed_dataset is None:
        raise FileNotFoundError(
            "The processed training dataset was not found. "
            "Run scripts/build_training_dataset.py first."
        )

    raw_dataset_names = (
        "vcheck.raw.synthetic_messages",
        "vcheck.raw.manual_messages",
        "vcheck.raw.uci_sms_spam_collection",
    )

    for raw_name in raw_dataset_names:
        raw_dataset = registered.get(raw_name)

        if raw_dataset is None:
            continue

        client.lineage.add_lineage(
            upstream=raw_dataset.urn,
            downstream=processed_dataset.urn,
        )

        print(
            "Added lineage: "
            f"{raw_dataset.display_name} -> {processed_dataset.display_name}"
        )

    print("Phase 3A dataset registration completed.")


if __name__ == "__main__":
    main()