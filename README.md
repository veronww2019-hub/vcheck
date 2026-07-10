# VCheck Phase 2

VCheck is an explainable suspicious-message risk assistant. Phase 2 combines:

1. deterministic text and URL warning rules;
2. a reproducible word-and-character TF-IDF classifier;
3. explicit dataset provenance and version manifests;
4. honest fallback to rules when no trained model exists.

The model is supporting evidence only. It adds at most 30 risk points and cannot
reduce deterministic warnings.

## Install

```bash
pip install -e ".[dev]"
```

## Build the training data

Generate 1,200 deterministic synthetic messages:

```bash
python scripts/generate_synthetic_dataset.py
```

Optional: fetch the UCI SMS Spam Collection at runtime:

```bash
python scripts/fetch_uci_sms.py
```

Merge, validate, deduplicate, and create a version manifest:

```bash
python scripts/build_training_dataset.py
```

## Train and evaluate

```bash
python scripts/train_model.py
```

This creates:

- `artifacts/suspicious_message_classifier.joblib`
- `artifacts/model_metadata.json`
- `artifacts/evaluation_report.json`

## Run

```bash
uvicorn vcheck.main:app --reload
```

Open `http://127.0.0.1:8000/docs`.

Useful endpoints:

- `GET /health`
- `GET /api/v1/model`
- `POST /api/v1/model/reload`
- `GET /api/v1/rules`
- `POST /api/v1/analyse`

## Tests and quality

```bash
ruff check .
pytest --cov=vcheck --cov-report=term-missing
```

## Data statement

The generated Malaysian-style records contain no real victim information and use
reserved `.example` domains. UCI dataset 228 may optionally be fetched and is not
redistributed in this repository. Its labels are spam/ham, not confirmed fraud.
Review source terms and provide the required citation in the final repository.

## Licence

Project source code and VCheck synthetic templates are licensed under Apache 2.0.
