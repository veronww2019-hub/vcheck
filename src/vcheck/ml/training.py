"""Training, evaluation, and versioned model-artifact creation."""

from __future__ import annotations

import json
import platform
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import joblib
import pandas as pd
import sklearn
from sklearn.metrics import (
    accuracy_score,
    classification_report,
    confusion_matrix,
    f1_score,
    precision_score,
    recall_score,
    roc_auc_score,
)
from sklearn.model_selection import train_test_split

from vcheck.ml.pipeline import build_text_pipeline


def train_and_save_model(
    dataset_path: Path,
    dataset_manifest_path: Path,
    model_path: Path,
    model_metadata_path: Path,
    evaluation_path: Path,
    test_size: float = 0.2,
    seed: int = 42,
) -> tuple[dict[str, Any], dict[str, Any]]:
    dataframe = pd.read_csv(dataset_path, encoding="utf-8")
    required = {"text", "label"}
    if missing := required - set(dataframe.columns):
        raise ValueError(f"Training dataset is missing columns: {sorted(missing)}")
    if len(dataframe) < 40:
        raise ValueError("At least 40 rows are required for this prototype training run.")
    if dataframe["label"].nunique() != 2:
        raise ValueError("Training dataset must contain both classes.")

    manifest = json.loads(dataset_manifest_path.read_text(encoding="utf-8"))
    texts = dataframe["text"].astype(str)
    labels = dataframe["label"].astype(int)

    x_train, x_test, y_train, y_test = train_test_split(
        texts,
        labels,
        test_size=test_size,
        random_state=seed,
        stratify=labels,
    )

    pipeline = build_text_pipeline(random_state=seed)
    pipeline.fit(x_train, y_train)

    predictions = pipeline.predict(x_test)
    probabilities = pipeline.predict_proba(x_test)[:, 1]
    report = classification_report(
        y_test,
        predictions,
        target_names=["legitimate", "suspicious"],
        output_dict=True,
        zero_division=0,
    )
    matrix = confusion_matrix(y_test, predictions, labels=[0, 1])

    evaluation: dict[str, Any] = {
        "test_rows": len(x_test),
        "accuracy": float(accuracy_score(y_test, predictions)),
        "precision_suspicious": float(precision_score(y_test, predictions, zero_division=0)),
        "recall_suspicious": float(recall_score(y_test, predictions, zero_division=0)),
        "f1_suspicious": float(f1_score(y_test, predictions, zero_division=0)),
        "roc_auc": float(roc_auc_score(y_test, probabilities)),
        "confusion_matrix": matrix.tolist(),
        "classification_report": report,
    }

    trained_at = datetime.now(timezone.utc).replace(microsecond=0).isoformat()
    metadata: dict[str, Any] = {
        "model_version": "tfidf-logreg-0.2.0",
        "trained_at": trained_at,
        "dataset_version": manifest["dataset_version"],
        "training_rows": len(x_train),
        "test_rows": len(x_test),
        "positive_label": 1,
        "positive_label_name": "suspicious",
        "random_seed": seed,
        "test_size": test_size,
        "python_version": platform.python_version(),
        "scikit_learn_version": sklearn.__version__,
        "evaluation": {
            "accuracy": evaluation["accuracy"],
            "precision_suspicious": evaluation["precision_suspicious"],
            "recall_suspicious": evaluation["recall_suspicious"],
            "f1_suspicious": evaluation["f1_suspicious"],
            "roc_auc": evaluation["roc_auc"],
        },
        "limitations": [
            "The public source labels spam, not confirmed fraud.",
            "Synthetic examples may not represent real-world language distributions.",
            "A prediction is supporting evidence and not proof that a message is fraudulent.",
        ],
    }

    model_path.parent.mkdir(parents=True, exist_ok=True)
    joblib.dump(pipeline, model_path)
    model_metadata_path.write_text(json.dumps(metadata, indent=2), encoding="utf-8")
    evaluation_path.write_text(json.dumps(evaluation, indent=2), encoding="utf-8")
    return metadata, evaluation
