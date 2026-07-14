"""Check VCheck's live evidence context from DataHub."""

from __future__ import annotations

import json
import sys

from vcheck.services.datahub_context import DataHubContextService


def main() -> int:
    service = DataHubContextService()

    try:
        context = service.get_context_bundle()

        print("=" * 70)
        print("VCheck Live DataHub Context Check")
        print("=" * 70)
        print(
            json.dumps(
                context,
                indent=2,
                ensure_ascii=False,
            )
        )

        if not context["available"]:
            print()
            print("[ERROR] DataHub context was unavailable.")
            return 1

        print()
        print(
            "[SUCCESS] VCheck retrieved and evaluated "
            "live DataHub evidence metadata."
        )
        return 0

    finally:
        service.close()


if __name__ == "__main__":
    sys.exit(main())