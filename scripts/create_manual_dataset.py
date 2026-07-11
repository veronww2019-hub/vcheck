"""Create personally reviewed fictional Malaysian-style training examples."""

from __future__ import annotations

import uuid
from datetime import date
from pathlib import Path

import pandas as pd

OUTPUT_PATH = Path("data/raw/manual_messages.csv")
SOURCE_NAME = "vcheck_manual_messages"
CREATED_AT = date(2026, 7, 11).isoformat()

MANUAL_MESSAGES: tuple[dict[str, object], ...] = (
    {
        "text": (
            "Tindakan segera: akaun bank anda akan dibekukan. "
            "Sahkan OTP sekarang di https://bank-check.example."
        ),
        "label": 1,
        "language": "ms",
    },
    {
        "text": (
            "Pakej anda ditahan. Buat pemindahan RM5 sebagai yuran pelepasan "
            "melalui http://parcel-help.example."
        ),
        "label": 1,
        "language": "ms",
    },
    {
        "text": (
            "Notis akhir LHDN: bayar RM300 sekarang atau tindakan undang-undang "
            "akan diambil. Semak di https://tax-payment.example."
        ),
        "label": 1,
        "language": "ms",
    },
    {
        "text": (
            "Tahniah, anda diterima untuk kerja sambilan. Bayar deposit RM80 "
            "untuk aktifkan akaun sebelum tawaran tamat."
        ),
        "label": 1,
        "language": "ms",
    },
    {
        "text": (
            "Waran tangkap telah dikeluarkan. Pindahkan wang RM500 sekarang "
            "untuk menghentikan tindakan polis."
        ),
        "label": 1,
        "language": "ms",
    },
    {
        "text": (
            "Saya pegawai bank. Pasang AnyDesk dan kongsi skrin supaya akaun "
            "anda boleh disahkan."
        ),
        "label": 1,
        "language": "ms",
    },
    {
        "text": (
            "Mesyuarat projek dipindahkan ke Bilik Seminar B2 pada pukul "
            "2 petang esok."
        ),
        "label": 0,
        "language": "ms",
    },
    {
        "text": (
            "Peringatan rasmi universiti: tarikh akhir urusan yuran pengajian "
            "ialah 25 Julai. Sila semak portal pelajar untuk maklumat lanjut."
        ),
        "label": 0,
        "language": "ms",
    },
    {
        "text": (
            "Pakej anda sedia untuk diambil di kaunter. Sila semak aplikasi "
            "rasmi kurier untuk waktu operasi."
        ),
        "label": 0,
        "language": "ms",
    },
    {
        "text": (
            "Peringatan keselamatan bank: jangan kongsi OTP, TAC, kata laluan, "
            "atau PIN dengan sesiapa."
        ),
        "label": 0,
        "language": "ms",
    },
    {
        "text": "Tolong beli susu dan roti semasa balik dari kampus petang ini.",
        "label": 0,
        "language": "ms",
    },
    {
        "text": (
            "Kelas tutorial petang ini dibatalkan. Pensyarah akan maklumkan "
            "tarikh kelas ganti melalui portal universiti."
        ),
        "label": 0,
        "language": "ms",
    },
)


def create_manual_dataset(output_path: Path = OUTPUT_PATH) -> pd.DataFrame:
    """Build and write the manually reviewed fictional dataset."""
    rows: list[dict[str, object]] = []

    for index, example in enumerate(MANUAL_MESSAGES):
        text = str(example["text"])
        label = int(example["label"])

        record_id = str(
            uuid.uuid5(
                uuid.NAMESPACE_URL,
                f"{SOURCE_NAME}:{index}:{label}:{text}",
            )
        )

        rows.append(
            {
                "record_id": record_id,
                "text": text,
                "label": label,
                "source": SOURCE_NAME,
                "source_type": "manually_curated_synthetic",
                "language": str(example["language"]),
                "review_status": "personally_reviewed",
                "is_synthetic": True,
                "license": "Apache-2.0",
                "created_at": CREATED_AT,
            }
        )

    dataframe = pd.DataFrame(rows)

    output_path.parent.mkdir(parents=True, exist_ok=True)
    dataframe.to_csv(output_path, index=False, encoding="utf-8")

    return dataframe


def main() -> None:
    dataframe = create_manual_dataset()

    print(f"Created {OUTPUT_PATH} with {len(dataframe)} rows.")
    print(dataframe["label"].value_counts().sort_index().to_dict())


if __name__ == "__main__":
    main()