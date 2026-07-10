# VCheck data folders

- `raw/`: source-specific CSV files created by the generation and import scripts.
- `processed/`: validated, deduplicated training data plus a provenance manifest.

Generated CSV files are ignored by Git to avoid accidentally committing large or
license-sensitive data. The scripts and manifests make the workflow reproducible.

Labels:

- `0`: legitimate/ham-style message
- `1`: suspicious/spam-or-scam-style message

Important: UCI's public collection is labelled spam/ham, not confirmed fraud. VCheck
preserves the source field and treats the model as supporting evidence only.
