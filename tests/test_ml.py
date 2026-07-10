import json
from pathlib import Path

import pandas as pd

from vcheck.domain.models import MlPredictedLabel
from vcheck.ml.dataset import build_training_dataset
from vcheck.ml.synthetic import generate_synthetic_messages
from vcheck.ml.training import train_and_save_model
from vcheck.services.ml_classifier import MlClassifier


def _train_temporary_model(tmp_path: Path) -> MlClassifier:
    raw_path = tmp_path / "raw.csv"
    processed_path = tmp_path / "processed.csv"
    manifest_path = tmp_path / "manifest.json"
    model_path = tmp_path / "model.joblib"
    metadata_path = tmp_path / "metadata.json"
    evaluation_path = tmp_path / "evaluation.json"

    dataframe = generate_synthetic_messages(rows_per_class=40, seed=7)
    dataframe.to_csv(raw_path, index=False)
    build_training_dataset([raw_path], processed_path, manifest_path, seed=7)
    train_and_save_model(
        processed_path,
        manifest_path,
        model_path,
        metadata_path,
        evaluation_path,
        test_size=0.25,
        seed=7,
    )
    return MlClassifier(model_path, metadata_path)


def test_synthetic_generator_is_balanced() -> None:
    dataframe = generate_synthetic_messages(rows_per_class=25, seed=42)
    assert len(dataframe) == 50
    assert dataframe["label"].value_counts().to_dict() == {0: 25, 1: 25}
    assert dataframe["is_synthetic"].all()


def test_dataset_builder_removes_duplicate_and_records_manifest(tmp_path: Path) -> None:
    input_path = tmp_path / "raw.csv"
    output_path = tmp_path / "processed.csv"
    manifest_path = tmp_path / "manifest.json"

    dataframe = generate_synthetic_messages(rows_per_class=20, seed=1)
    duplicated = pd.concat([dataframe, dataframe.iloc[[0]]], ignore_index=True)
    duplicated.to_csv(input_path, index=False)

    processed, manifest = build_training_dataset(
        [input_path], output_path, manifest_path, seed=1
    )

    assert len(processed) == 40
    assert manifest["duplicates_removed"] == 1
    assert manifest["dataset_version"].startswith("sha256:")
    assert json.loads(manifest_path.read_text())["row_count"] == 40


def test_model_trains_loads_and_predicts(tmp_path: Path) -> None:
    classifier = _train_temporary_model(tmp_path)
    assert classifier.available

    suspicious = classifier.assess(
        "URGENT parcel held, pay RM50 now and enter your OTP at http://fee.example"
    )
    legitimate = classifier.assess("Our engineering class starts at 9 AM tomorrow.")

    assert suspicious.predicted_label is MlPredictedLabel.SUSPICIOUS
    assert legitimate.predicted_label is MlPredictedLabel.LEGITIMATE
    assert suspicious.suspicious_probability is not None
    assert legitimate.suspicious_probability is not None
    assert suspicious.suspicious_probability > legitimate.suspicious_probability


def test_missing_model_is_graceful(tmp_path: Path) -> None:
    classifier = MlClassifier(tmp_path / "missing.joblib", tmp_path / "missing.json")
    assessment = classifier.assess("Any message")

    assert not classifier.available
    assert assessment.predicted_label is MlPredictedLabel.UNAVAILABLE
    assert assessment.score_contribution == 0


def test_ml_scoring_bands() -> None:
    assert MlClassifier._score_contribution(0.49) == 0
    assert MlClassifier._score_contribution(0.55) == 10
    assert MlClassifier._score_contribution(0.75) == 20
    assert MlClassifier._score_contribution(0.90) == 30
