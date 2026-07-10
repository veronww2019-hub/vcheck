"""Fetch and reshape UCI SMS Spam Collection dataset 228.

The dataset is fetched at execution time and is not redistributed in this repository.
Review the source's terms and citation before publication.
"""

from __future__ import annotations

import argparse
import io
import uuid
import zipfile
from datetime import date
from pathlib import Path
from urllib.error import URLError
from urllib.request import Request, urlopen

import pandas as pd

UCI_ARCHIVE_URL = (
    "https://archive.ics.uci.edu/static/public/228/sms%2Bspam%2Bcollection.zip"
)


def _download_collection() -> pd.DataFrame:
    request = Request(UCI_ARCHIVE_URL, headers={"User-Agent": "VCheck/0.2"})
    with urlopen(request, timeout=30) as response:  # noqa: S310 - fixed official URL
        archive_bytes = response.read()

    with (
        zipfile.ZipFile(io.BytesIO(archive_bytes)) as archive,
        archive.open("SMSSpamCollection") as dataset_file,
    ):
        dataframe = pd.read_csv(
            dataset_file,
            sep="\t",
            names=["raw_label", "text"],
            encoding="utf-8",
        )
    return dataframe


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--output",
        type=Path,
        default=Path("data/raw/uci_sms_spam_collection.csv"),
    )
    args = parser.parse_args()

    try:
        raw = _download_collection()
    except URLError as exc:
        raise SystemExit(
            "Could not download the optional UCI dataset. Check your internet connection "
            "and try again, or continue using the synthetic dataset only."
        ) from exc
    raw["raw_label"] = raw["raw_label"].astype(str).str.casefold()
    label_map = {"ham": 0, "spam": 1}
    unknown = sorted(set(raw["raw_label"]) - set(label_map))
    if unknown:
        raise ValueError(f"Unexpected UCI labels: {unknown}")

    created_at = date.today().isoformat()
    output = pd.DataFrame(
        {
            "record_id": [
                str(uuid.uuid5(uuid.NAMESPACE_URL, f"uci-228:{index}:{text}"))
                for index, text in enumerate(raw["text"])
            ],
            "text": raw["text"].astype(str),
            "label": raw["raw_label"].map(label_map).astype(int),
            "source": "uci_sms_spam_collection_228",
            "source_type": "public",
            "language": "en",
            "review_status": "source_documented",
            "is_synthetic": False,
            "license": "review_source_terms_before_redistribution",
            "created_at": created_at,
        }
    )

    args.output.parent.mkdir(parents=True, exist_ok=True)
    output.to_csv(args.output, index=False, encoding="utf-8")
    print(f"Created {args.output} with {len(output)} rows.")
    print(output["label"].value_counts().sort_index().to_dict())
    print("Citation: Almeida, T. & Hidalgo, J. (2011), UCI dataset DOI 10.24432/C5CC84.")


if __name__ == "__main__":
    main()
