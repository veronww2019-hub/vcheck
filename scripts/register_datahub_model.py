"""Register the VCheck classifier and model metadata in local DataHub."""

from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path
from typing import Any

import datahub.metadata.schema_classes as models
from datahub.metadata.urns import CorpUserUrn, DatasetUrn
from datahub.sdk import DataHubClient, Tag
from datahub.sdk.mlmodel import MLModel
from datahub.sdk.mlmodelgroup import MLModelGroup

DATAHUB_SERVER = "http://localhost:8080"
OWNER = CorpUserUrn("datahub")

MODEL_METADATA_PATH = Path("artifacts/model_metadata.json")
EVALUATION_PATH = Path("artifacts/evaluation_report.json")

MODEL_GROUP_ID = "vcheck.suspicious-message-classifier"
MODEL_ID = "vcheck.suspicious-message-classifier.tfidf-logreg"

TRAINING_DATASET_URN = DatasetUrn(
    platform="file",
    name="vcheck.processed.training_dataset",
    env="PROD",
)

SOURCE_CODE_URL = (
    "https://github.com/veronww2019-hub/vcheck/"
    "tree/main/src/vcheck/ml"
)

TAG_DEFINITIONS: dict[str, tuple[str, str]] = {
    "vcheck": (
        "VCheck",
        "Asset belonging to the VCheck scam-risk prototype.",
    ),
    "model-training": (
        "Model Training",
        "Asset directly involved in model training or evaluation.",
    ),
    "prototype-model": (
        "Prototype Model",
        "Machine-learning model created for prototype development.",
    ),
    "not-production-ready": (
        "Not Production Ready",
        "Asset not validated for unsupervised production use.",
    ),
}


def load_json(path: Path) -> dict[str, Any]:
    """Load one required JSON artifact."""
    if not path.exists():
        raise FileNotFoundError(
            f"Required artifact not found: {path}. "
            "Run python scripts/train_model.py first."
        )

    return json.loads(path.read_text(encoding="utf-8"))


def register_tags(client: DataHubClient) -> dict[str, object]:
    """Create or update tags used by the VCheck model."""
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


def metric_strings(evaluation: dict[str, Any]) -> dict[str, str]:
    """Convert numerical evaluation metrics to DataHub metric strings."""
    return {
        "accuracy": f"{float(evaluation['accuracy']):.6f}",
        "precision_suspicious": (
            f"{float(evaluation['precision_suspicious']):.6f}"
        ),
        "recall_suspicious": (
            f"{float(evaluation['recall_suspicious']):.6f}"
        ),
        "f1_suspicious": (
            f"{float(evaluation['f1_suspicious']):.6f}"
        ),
        "roc_auc": f"{float(evaluation['roc_auc']):.6f}",
    }


def main() -> None:
    metadata = load_json(MODEL_METADATA_PATH)
    evaluation = load_json(EVALUATION_PATH)

    client = DataHubClient(server=DATAHUB_SERVER)
    tag_urns = register_tags(client)

    trained_at = datetime.fromisoformat(
        str(metadata["trained_at"]).replace("Z", "+00:00")
    )

    model_group = MLModelGroup(
        id=MODEL_GROUP_ID,
        name="VCheck Suspicious Message Classifier",
        display_name="VCheck Suspicious Message Classifier",
        platform="scikit-learn",
        description=(
            "Model family for VCheck text classifiers that estimate whether "
            "a submitted message resembles suspicious or spam-style content."
        ),
        custom_properties={
            "project": "VCheck",
            "framework": "scikit-learn",
            "task": "binary text classification",
            "input_type": "message text",
            "lifecycle": "prototype",
        },
        owners=[OWNER],
        tags=[
            tag_urns["vcheck"],
            tag_urns["prototype-model"],
            tag_urns["not-production-ready"],
        ],
    )

    client.entities.upsert(model_group)
    print(f"Registered model group: {model_group.urn}")

    intended_use = models.IntendedUseClass(
        primaryUses=[
            (
                "Provide supporting evidence when assessing suspicious "
                "messages submitted to the VCheck prototype."
            ),
            (
                "Combine probabilistic text classification with deterministic "
                "warning rules."
            ),
        ],
        outOfScopeUses=[
            "Do not treat a prediction as proof that a message is fraudulent.",
            "Do not use the model as a replacement for banks or authorities.",
            "Do not use the model for automatic enforcement or punishment.",
            "Do not claim real-world accuracy from the prototype evaluation.",
        ],
    )

    training_data = models.TrainingDataClass(
        trainingData=[
            models.BaseDataClass(
                dataset=str(TRAINING_DATASET_URN),
                motivation=(
                    "Validated and deduplicated VCheck training records "
                    "assembled from synthetic, manually curated, and public "
                    "spam-style sources."
                ),
                preProcessing=[
                    "Validated required columns and binary labels",
                    "Normalised text and metadata fields",
                    "Removed duplicate records",
                    "Created a stratified training and test split",
                    "Applied word and character TF-IDF vectorisation",
                ],
            )
        ]
    )

    evaluation_data = models.EvaluationDataClass(
        evaluationData=[
            models.BaseDataClass(
                dataset=str(TRAINING_DATASET_URN),
                motivation=(
                    "A stratified holdout split from the processed prototype "
                    "dataset was used for evaluation."
                ),
                preProcessing=[
                    (
                        f"Used a {float(metadata['test_size']):.0%} "
                        "stratified holdout split"
                    ),
                    (
                        f"Used random seed "
                        f"{metadata['random_seed']}"
                    ),
                    "Evaluation data was not used to fit the classifier",
                ],
            )
        ]
    )

    source_code = models.SourceCodeClass(
        sourceCode=[
            models.SourceCodeUrlClass(
                type=models.SourceCodeUrlTypeClass.ML_MODEL_SOURCE_CODE,
                sourceCodeUrl=SOURCE_CODE_URL,
            )
        ]
    )

    ethical_considerations = models.EthicalConsiderationsClass(
        data=[
            (
                "The prototype training data contains synthetic messages and "
                "a public SMS spam dataset."
            ),
            "No real scam-victim messages are required by the prototype.",
        ],
        risksAndHarms=[
            (
                "A false positive may incorrectly make a legitimate message "
                "appear suspicious."
            ),
            (
                "A false negative may provide reassurance about a message "
                "that is actually harmful."
            ),
            (
                "Synthetic language patterns may not represent real-world "
                "Malaysian message distributions."
            ),
        ],
        mitigations=[
            "The classifier is supporting evidence only.",
            "Deterministic warning rules remain visible to the user.",
            "The application provides explanations rather than only a label.",
            "The model is explicitly marked as not production ready.",
            "Users are advised to verify requests through official channels.",
        ],
    )

    limitations = metadata.get("limitations", [])

    classifier = MLModel(
        id=MODEL_ID,
        platform="scikit-learn",
        version=str(metadata["model_version"]),
        aliases=["latest", "prototype"],
        name="VCheck TF-IDF Logistic Regression Classifier",
        description=(
            "A prototype binary text classifier using word and character "
            "TF-IDF features with logistic regression. It estimates whether "
            "a message resembles suspicious or spam-style training examples."
        ),
        training_metrics=metric_strings(evaluation),
        hyper_params={
            "classifier": "LogisticRegression",
            "solver": "lbfgs",
            "C": "2.0",
            "class_weight": "balanced",
            "max_iter": "2000",
            "word_ngram_range": "1-2",
            "character_ngram_range": "3-5",
            "random_seed": str(metadata["random_seed"]),
            "test_size": str(metadata["test_size"]),
        },
        external_url=SOURCE_CODE_URL,
        custom_properties={
            "project": "VCheck",
            "lifecycle": "prototype",
            "review_status": "prototype_reviewed",
            "artifact_path": (
                "artifacts/suspicious_message_classifier.joblib"
            ),
            "dataset_version": str(metadata["dataset_version"]),
            "trained_at": str(metadata["trained_at"]),
            "training_rows": str(metadata["training_rows"]),
            "test_rows": str(metadata["test_rows"]),
            "positive_label": str(metadata["positive_label"]),
            "positive_label_name": str(metadata["positive_label_name"]),
            "python_version": str(metadata["python_version"]),
            "scikit_learn_version": str(
                metadata["scikit_learn_version"]
            ),
            "confusion_matrix": json.dumps(
                evaluation["confusion_matrix"]
            ),
            "limitations": " | ".join(str(item) for item in limitations),
            "real_world_validation": "false",
            "contains_real_victim_data": "false",
        },
        created=trained_at,
        last_modified=trained_at,
        owners=[OWNER],
        tags=[
            tag_urns["vcheck"],
            tag_urns["model-training"],
            tag_urns["prototype-model"],
            tag_urns["not-production-ready"],
        ],
        model_group=model_group.urn,
        extra_aspects=[
            intended_use,
            training_data,
            evaluation_data,
            source_code,
            ethical_considerations,
        ],
    )

    client.entities.upsert(classifier)

    print(f"Registered ML model: {classifier.urn}")
    print(
        "Linked training dataset: "
        f"{TRAINING_DATASET_URN} -> {classifier.urn}"
    )
    print("Phase 3B model registration completed.")


if __name__ == "__main__":
    main()