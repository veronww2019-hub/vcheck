"""Verify VCheck's DataHub Agent Context Kit integration."""

from __future__ import annotations

import json
import sys

from vcheck.services.agent_context_service import (
    AgentContextKitService,
)


def main() -> int:
    service = AgentContextKitService()

    try:
        search_result = service.search_vcheck_assets()
        context_bundle = service.get_context_bundle()

        search_results = search_result.get(
            "searchResults",
            [],
        )

        print("=" * 70)
        print("VCheck Agent Context Kit Verification")
        print("=" * 70)
        print(
            "Search results found:",
            len(search_results),
        )
        print(
            "Integration mode:",
            context_bundle["integration_mode"],
        )
        print(
            "Selected evidence:",
            len(context_bundle["selected_evidence"]),
        )
        print(
            "Excluded evidence:",
            len(context_bundle["excluded_evidence"]),
        )
        print()

        print(
            json.dumps(
                context_bundle,
                indent=2,
                ensure_ascii=False,
            )
        )

        if (
            context_bundle["integration_mode"]
            != "agent_context_kit"
        ):
            print()
            print(
                "[ERROR] Agent Context Kit was not the "
                "active integration."
            )
            return 1

        print()
        print(
            "[SUCCESS] VCheck retrieved evidence through "
            "DataHub Agent Context Kit."
        )

        return 0

    finally:
        service.close()


if __name__ == "__main__":
    sys.exit(main())