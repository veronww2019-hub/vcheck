# VCheck API — Phase 1

A modular FastAPI backend that analyses suspicious messages using explainable rules.

## What Phase 1 does

- Accepts a pasted message
- Normalises the text safely
- Extracts URLs
- Detects explainable scam-warning signals
- Returns a 0–100 risk score and Low/Medium/High level
- Returns clear recommended actions
- Provides API documentation and automated tests

## What Phase 1 does not do yet

- It does not verify bank accounts, phone numbers, or domains against live services
- It does not use DataHub yet
- It does not use machine learning yet
- It does not make a legal or definitive determination that a message is a scam

## Setup using the existing hackathon virtual environment

Extract this project as:

```text
C:\Users\veron\datahub-hackathon\vcheck
```

Then open PowerShell:

```powershell
cd C:\Users\veron\datahub-hackathon
.\.venv\Scripts\Activate.ps1
cd vcheck
python -m pip install --upgrade pip
pip install -e ".[dev]"
```

Run the API:

```powershell
uvicorn vcheck.main:app --reload
```

Open:

- Swagger UI: http://127.0.0.1:8000/docs
- Health endpoint: http://127.0.0.1:8000/health

Run tests:

```powershell
pytest --cov=vcheck --cov-report=term-missing
```

Check code quality:

```powershell
ruff check .
```
