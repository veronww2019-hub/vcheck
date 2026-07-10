"""Dataset validation, deduplication, provenance preservation, and versioning."""

from __future__ import annotations

import hashlib
import json
import unicodedata
from pathlib import Path
from typing import Any

import pandas as pd

REQUIRED_COLUMNS = {
    "record_id",
    "text",
    "label",
    "source",
    "source_type",
    "language",
    "review_status",
    "is_synthetic",
    "license",
    "created_at",
}


def normalise_text(value: str) -> str:
    normalised = unicodedata.normalize("NFKC", str(value))
    return " ".join(normalised.split()).strip()


def _validate_frame(dataframe: pd.DataFrame, input_path: Path) -> pd.DataFrame:
    missing = REQUIRED_COLUMNS - set(dataframe.columns)
    if missing:
        raise ValueError(f"{input_path} is missing columns: {sorted(missing)}")

    cleaned = dataframe.copy()
    cleaned["text"] = cleaned["text"].map(normalise_text)
    cleaned["label"] = pd.to_numeric(cleaned["label"], errors="raise").astype(int)

    if not set(cleaned["label"].unique()).issubset({0, 1}):
        raise ValueError(f"{input_path} labels must contain only 0 and 1.")

    cleaned = cleaned[cleaned["text"].str.len() >= 3]
    return cleaned


def _dataset_hash(dataframe: pd.DataFrame) -> str:
    canonical = dataframe.sort_values("record_id").to_csv(index=False, lineterminator="\n")
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()


def build_training_dataset(
    input_paths: list[Path],
    output_path: Path,
    manifest_path: Path,
    seed: int = 42,
) -> tuple[pd.DataFrame, dict[str, Any]]:
    existing_paths = [path for path in input_paths if path.exists()]
    if not existing_paths:
        raise FileNotFoundError("No source dataset exists. Generate or fetch data first.")

    frames = [
        _validate_frame(pd.read_csv(path, encoding="utf-8"), path) for path in existing_paths
    ]
    combined = pd.concat(frames, ignore_index=True)
    combined["normalised_text"] = combined["text"].map(normalise_text).str.casefold()

    conflicting_texts = (
        combined.groupby("normalised_text")["label"].nunique().loc[lambda values: values > 1].index
    )
    conflict_count = len(conflicting_texts)
    if conflict_count:
        combined = combined[~combined["normalised_text"].isin(conflicting_texts)]

    before_deduplication = len(combined)
    combined = combined.drop_duplicates(subset=["normalised_text", "label"], keep="first")
    duplicates_removed = before_deduplication - len(combined)
    combined = combined.drop(columns=["normalised_text"])
    combined = combined.sample(frac=1, random_state=seed).reset_index(drop=True)

    if combined["label"].nunique() != 2:
        raise ValueError("Training data must contain both legitimate and suspicious labels.")

    output_path.parent.mkdir(parents=True, exist_ok=True)
    combined.to_csv(output_path, index=False, encoding="utf-8")

    digest = _dataset_hash(combined)
    manifest: dict[str, Any] = {
        "dataset_version": f"sha256:{digest[:16]}",
        "sha256": digest,
        "row_count": len(combined),
        "class_counts": {
            str(key): int(value) for key, value in combined["label"].value_counts().items()
        },
        "source_counts": {
            str(key): int(value) for key, value in combined["source"].value_counts().items()
        },
        "source_type_counts": {
            str(key): int(value)
            for key, value in combined["source_type"].value_counts().items()
        },
        "conflicting_texts_removed": conflict_count,
        "duplicates_removed": duplicates_removed,
        "input_files": [str(path) for path in existing_paths],
        "random_seed": seed,
    }
    manifest_path.parent.mkdir(parents=True, exist_ok=True)
    manifest_path.write_text(json.dumps(manifest, indent=2), encoding="utf-8")
    return combined, manifest
