"""Merge, validate, deduplicate, and version raw datasets."""

from __future__ import annotations

import argparse
from pathlib import Path

from vcheck.ml.dataset import build_training_dataset


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--inputs",
        type=Path,
        nargs="+",
        default=[
            Path("data/raw/synthetic_messages.csv"),
            Path("data/raw/manual_messages.csv"),
            Path("data/raw/uci_sms_spam_collection.csv"),
        ],
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=Path("data/processed/training_dataset.csv"),
    )
    parser.add_argument(
        "--manifest",
        type=Path,
        default=Path("data/processed/dataset_manifest.json"),
    )
    parser.add_argument("--seed", type=int, default=42)
    args = parser.parse_args()

    dataframe, manifest = build_training_dataset(
        input_paths=args.inputs,
        output_path=args.output,
        manifest_path=args.manifest,
        seed=args.seed,
    )
    print(f"Created {args.output} with {len(dataframe)} rows.")
    print(f"Dataset version: {manifest['dataset_version']}")
    print(f"Sources: {manifest['source_counts']}")
    print(f"Classes: {manifest['class_counts']}")


if __name__ == "__main__":
    main()
