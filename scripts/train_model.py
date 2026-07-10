"""Train, evaluate, and save the Phase 2 text classifier."""

from __future__ import annotations

import argparse
from pathlib import Path

from vcheck.ml.training import train_and_save_model


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--dataset",
        type=Path,
        default=Path("data/processed/training_dataset.csv"),
    )
    parser.add_argument(
        "--dataset-manifest",
        type=Path,
        default=Path("data/processed/dataset_manifest.json"),
    )
    parser.add_argument(
        "--model",
        type=Path,
        default=Path("artifacts/suspicious_message_classifier.joblib"),
    )
    parser.add_argument(
        "--metadata",
        type=Path,
        default=Path("artifacts/model_metadata.json"),
    )
    parser.add_argument(
        "--evaluation",
        type=Path,
        default=Path("artifacts/evaluation_report.json"),
    )
    parser.add_argument("--test-size", type=float, default=0.2)
    parser.add_argument("--seed", type=int, default=42)
    args = parser.parse_args()

    metadata, evaluation = train_and_save_model(
        dataset_path=args.dataset,
        dataset_manifest_path=args.dataset_manifest,
        model_path=args.model,
        model_metadata_path=args.metadata,
        evaluation_path=args.evaluation,
        test_size=args.test_size,
        seed=args.seed,
    )

    print(f"Saved model: {args.model}")
    print(f"Model version: {metadata['model_version']}")
    print(f"Dataset version: {metadata['dataset_version']}")
    print(f"Accuracy: {evaluation['accuracy']:.4f}")
    print(f"Suspicious precision: {evaluation['precision_suspicious']:.4f}")
    print(f"Suspicious recall: {evaluation['recall_suspicious']:.4f}")
    print(f"Suspicious F1: {evaluation['f1_suspicious']:.4f}")
    print(f"ROC AUC: {evaluation['roc_auc']:.4f}")
    print(f"Confusion matrix [[TN, FP], [FN, TP]]: {evaluation['confusion_matrix']}")


if __name__ == "__main__":
    main()
