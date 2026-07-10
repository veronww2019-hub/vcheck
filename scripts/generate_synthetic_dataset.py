"""Generate deterministic Malaysian-style synthetic training messages."""

from __future__ import annotations

import argparse
from pathlib import Path

from vcheck.ml.synthetic import write_synthetic_dataset


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--output",
        type=Path,
        default=Path("data/raw/synthetic_messages.csv"),
    )
    parser.add_argument("--rows-per-class", type=int, default=600)
    parser.add_argument("--seed", type=int, default=42)
    args = parser.parse_args()

    dataframe = write_synthetic_dataset(
        output_path=args.output,
        rows_per_class=args.rows_per_class,
        seed=args.seed,
    )
    print(f"Created {args.output} with {len(dataframe)} rows.")
    print(dataframe["label"].value_counts().sort_index().to_dict())


if __name__ == "__main__":
    main()
