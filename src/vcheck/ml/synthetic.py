"""Deterministic generation of labelled, non-personal synthetic messages."""

from __future__ import annotations

import random
import uuid
from dataclasses import dataclass
from datetime import date
from pathlib import Path

import pandas as pd


@dataclass(frozen=True, slots=True)
class Template:
    text: str
    language: str


SUSPICIOUS_TEMPLATES: tuple[Template, ...] = (
    Template(
        "URGENT: Your {service} account will be suspended. Verify now at {url}.",
        "en",
    ),
    Template(
        "Parcel anda ditahan. Bayar yuran RM{fee} segera melalui {url}.",
        "ms",
    ),
    Template(
        "Tahniah! Anda menang hadiah RM{amount}. Bayar processing fee RM{fee} untuk claim.",
        "mixed",
    ),
    Template(
        "Saya pegawai {organisation}. Berikan OTP anda sekarang untuk pengesahan.",
        "ms",
    ),
    Template(
        "Final warning: transfer RM{amount} today or legal action will be taken.",
        "en",
    ),
    Template(
        "Kerja sambilan mudah dari rumah. Deposit RM{fee} dahulu untuk aktifkan akaun.",
        "ms",
    ),
    Template(
        "Your refund is ready. Login using {url} and enter your verification code.",
        "en",
    ),
    Template(
        "Jangan beritahu sesiapa. This confidential transaction must be completed now.",
        "mixed",
    ),
    Template(
        "Customer service here. Install {remote_app} so we can secure your bank account.",
        "en",
    ),
    Template(
        "You have won a free gift. Click {url} before the offer expires tonight.",
        "en",
    ),
)

LEGITIMATE_TEMPLATES: tuple[Template, ...] = (
    Template("Hi {name}, our class starts at {time} in the engineering lab.", "en"),
    Template("Mesyuarat kumpulan kita esok pukul {time} di perpustakaan.", "ms"),
    Template("Your order is ready for pickup. Please check the official app for details.", "en"),
    Template("Reminder: submit the assignment before {time} through the university portal.", "en"),
    Template("Saya dah sampai kampus. Jumpa dekat kafeteria ya.", "ms"),
    Template("The workshop venue changed to Seminar Room {room}.", "en"),
    Template("Mom asked whether you will be home for dinner at {time}.", "en"),
    Template("Bil anda sudah tersedia. Semak jumlah dalam aplikasi rasmi syarikat.", "ms"),
    Template("Your appointment is confirmed for {time}. Reply if you need to reschedule.", "en"),
    Template("Can you send me the slides from today's lecture when you are free?", "en"),
)

SERVICES = ("email", "shopping", "cloud", "delivery")
ORGANISATIONS = ("bank", "courier company", "tax office", "support centre")
NAMES = ("Aina", "Daniel", "Mei", "Ravi", "Sara", "Veron")
TIMES = ("9 AM", "11:30 AM", "2 PM", "4:15 PM", "7 PM")
ROOMS = ("A", "B2", "3", "5C")
REMOTE_APPS = ("a remote support app", "screen sharing software", "remote desktop software")
SAFE_URLS = (
    "http://verify-account.example",
    "http://parcel-fee.example",
    "https://reward-centre.example",
    "https://secure-login.example",
)


def _render(template: Template, rng: random.Random) -> str:
    return template.text.format(
        service=rng.choice(SERVICES),
        organisation=rng.choice(ORGANISATIONS),
        name=rng.choice(NAMES),
        time=rng.choice(TIMES),
        room=rng.choice(ROOMS),
        amount=rng.choice((50, 100, 500, 2_000)),
        fee=rng.choice((2, 5, 20, 50)),
        remote_app=rng.choice(REMOTE_APPS),
        url=rng.choice(SAFE_URLS),
    )


def generate_synthetic_messages(rows_per_class: int = 600, seed: int = 42) -> pd.DataFrame:
    if rows_per_class < 20:
        raise ValueError("rows_per_class must be at least 20.")

    rng = random.Random(seed)
    generated: list[dict[str, object]] = []
    created_at = date(2026, 7, 10).isoformat()

    for label, templates in ((1, SUSPICIOUS_TEMPLATES), (0, LEGITIMATE_TEMPLATES)):
        for index in range(rows_per_class):
            template = templates[index % len(templates)]
            text = _render(template, rng)
            # Add harmless variation so the model does not only memorise ten strings.
            if index % 3 == 0:
                text = f"{text} Ref {rng.randint(1000, 9999)}"
            elif index % 3 == 1:
                text = text.replace(".", "!")

            generated.append(
                {
                    "record_id": str(
                        uuid.uuid5(uuid.NAMESPACE_URL, f"{seed}:{label}:{index}:{text}")
                    ),
                    "text": text,
                    "label": label,
                    "source": "vcheck_synthetic_messages",
                    "source_type": "synthetic",
                    "language": template.language,
                    "review_status": "template_reviewed",
                    "is_synthetic": True,
                    "license": "Apache-2.0",
                    "created_at": created_at,
                }
            )

    dataframe = pd.DataFrame(generated)
    return dataframe.sample(frac=1, random_state=seed).reset_index(drop=True)


def write_synthetic_dataset(output_path: Path, rows_per_class: int, seed: int) -> pd.DataFrame:
    dataframe = generate_synthetic_messages(rows_per_class=rows_per_class, seed=seed)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    dataframe.to_csv(output_path, index=False, encoding="utf-8")
    return dataframe
