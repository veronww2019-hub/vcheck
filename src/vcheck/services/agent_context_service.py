"""Read VCheck evidence using DataHub Agent Context Kit tools."""

from __future__ import annotations

import os
from collections.abc import Mapping
from typing import Any

from datahub.sdk.main_client import DataHubClient
from datahub_agent_context.context import DataHubContext
from datahub_agent_context.mcp_tools.entities import get_entities
from datahub_agent_context.mcp_tools.search import search

from vcheck.services.datahub_context import (
    EVIDENCE_URNS,
    DataHubContextService,
)
from vcheck.services.evidence_policy import select_evidence

REQUIRED_TRUST_PROPERTIES = {
    "source_classification",
    "review_status",
    "freshness_status",
    "reliability_level",
    "allowed_for_decision",
    "evidence_role",
}


def _as_mapping(value: Any) -> Mapping[str, Any]:
    """Return a mapping or an empty mapping."""

    if isinstance(value, Mapping):
        return value

    return {}


def _first_non_empty(*values: Any) -> str:
    """Return the first non-empty string representation."""

    for value in values:
        if value is not None and str(value).strip():
            return str(value).strip()

    return ""


class AgentContextKitService:
    """
    Retrieve evidence through the DataHub Agent Context Kit.

    The existing Python SDK service remains as a resilience fallback.
    """

    def __init__(
        self,
        gms_url: str | None = None,
        token: str | None = None,
        fallback: DataHubContextService | None = None,
    ) -> None:
        self.gms_url = (
            gms_url
            or os.getenv("DATAHUB_GMS_URL")
            or "http://localhost:8080"
        )

        self.token = token or os.getenv("DATAHUB_GMS_TOKEN")

        if not self.token:
            raise ValueError(
                "DATAHUB_GMS_TOKEN is required for the "
                "DataHub Agent Context Kit."
            )

        self._client = DataHubClient(
            server=self.gms_url,
            token=self.token,
        )

        self._fallback = fallback or DataHubContextService(
            gms_url=self.gms_url,
            token=self.token,
        )

    @staticmethod
    def _extract_custom_properties(
        entity: Mapping[str, Any],
    ) -> dict[str, Any]:
        """Find and normalise custom properties from Agent Context."""

        properties = _as_mapping(entity.get("properties"))
        aspects = _as_mapping(entity.get("aspects"))
        dataset_properties = _as_mapping(
            aspects.get("datasetProperties")
        )

        candidates = (
            entity.get("customProperties"),
            entity.get("custom_properties"),
            properties.get("customProperties"),
            properties.get("custom_properties"),
            dataset_properties.get("customProperties"),
            dataset_properties.get("custom_properties"),
        )

        for candidate in candidates:
            # Some Agent Context Kit versions return:
            # {"review_status": "reviewed"}
            if isinstance(candidate, Mapping):
                return {
                    str(key): value
                    for key, value in candidate.items()
                }

            # Other versions return:
            # [{"key": "review_status", "value": "reviewed"}]
            if isinstance(candidate, list):
                normalised: dict[str, Any] = {}

                for item in candidate:
                    if not isinstance(item, Mapping):
                        continue

                    key = item.get("key")
                    value = item.get("value")

                    if key is not None:
                        normalised[str(key)] = value

                if normalised:
                    return normalised

        return {}

    @classmethod
    def _entity_to_source(
        cls,
        entity: Mapping[str, Any],
    ) -> dict[str, Any]:
        """Convert an Agent Context entity into trust-policy input."""

        properties = _as_mapping(entity.get("properties"))
        aspects = _as_mapping(entity.get("aspects"))
        dataset_properties = _as_mapping(
            aspects.get("datasetProperties")
        )

        urn = _first_non_empty(entity.get("urn"))

        name = _first_non_empty(
            entity.get("name"),
            properties.get("name"),
            dataset_properties.get("name"),
            urn,
        )

        description = _first_non_empty(
            entity.get("description"),
            properties.get("description"),
            dataset_properties.get("description"),
        )

        custom_properties = cls._extract_custom_properties(
            entity
        )

        missing_properties = (
            REQUIRED_TRUST_PROPERTIES
            - set(custom_properties)
        )

        if missing_properties:
            missing = ", ".join(
                sorted(missing_properties)
            )
            raise ValueError(
                f"Agent Context entity {urn} is missing "
                f"trust properties: {missing}"
            )

        return {
            "urn": urn,
            "name": name,
            "description": description,
            "custom_properties": custom_properties,
        }

    def get_evidence_sources(self) -> list[dict[str, Any]]:
        """Retrieve the four evidence assets through get_entities."""

        with DataHubContext(self._client):
            response = get_entities(
                urns=list(EVIDENCE_URNS)
            )

        # Agent Context Kit versions may return either:
        # 1. a list of entities directly, or
        # 2. a dictionary containing an "entities" field.
        if isinstance(response, list):
            entities = response
        elif isinstance(response, Mapping):
            entities = response.get(
                "entities",
                response.get("results", []),
            )
        else:
            raise ValueError(
                "Agent Context Kit returned an unsupported "
                f"response type: {type(response).__name__}"
            )

        if not isinstance(entities, list):
            raise ValueError(
                "Agent Context Kit returned an invalid "
                "entities collection."
            )

        sources_by_urn: dict[str, dict[str, Any]] = {}

        for raw_entity in entities:
            if not isinstance(raw_entity, Mapping):
                continue

            source = self._entity_to_source(raw_entity)

            if source["urn"]:
                sources_by_urn[str(source["urn"])] = source

        missing_urns = [
            urn
            for urn in EVIDENCE_URNS
            if urn not in sources_by_urn
        ]

        if missing_urns:
            raise ValueError(
                "Agent Context Kit did not return all required "
                f"evidence assets: {missing_urns}"
            )

        return [
            sources_by_urn[urn]
            for urn in EVIDENCE_URNS
        ]

    def search_vcheck_assets(self) -> dict[str, Any]:
            """Demonstrate the Agent Context Kit search tool."""

            with DataHubContext(self._client):
                return search(
                query="VCheck",
                num_results=20,
            )

    def get_context_bundle(self) -> dict[str, Any]:
        """Retrieve and evaluate evidence with a safe fallback."""

        try:
            sources = self.get_evidence_sources()
            selection = select_evidence(sources)

            return {
                "available": True,
                "integration_mode": "agent_context_kit",
                "selected_evidence": (
                    selection["selected_evidence"]
                ),
                "excluded_evidence": (
                    selection["excluded_evidence"]
                ),
                "provenance_summary": (
                    selection["provenance_summary"]
                ),
                "warning": None,
            }

        except Exception as agent_context_error:
            fallback_bundle = (
                self._fallback.get_context_bundle()
            )

            if fallback_bundle["available"]:
                fallback_bundle[
                    "integration_mode"
                ] = "python_sdk_fallback"

                fallback_bundle["warning"] = (
                    "Agent Context Kit retrieval failed, so "
                    "VCheck used its Python SDK fallback: "
                    f"{agent_context_error}"
                )

                return fallback_bundle

            return {
                "available": False,
                "integration_mode": "unavailable",
                "selected_evidence": [],
                "excluded_evidence": [],
                "provenance_summary": (
                    "Evidence provenance could not be checked."
                ),
                "warning": (
                    "Both Agent Context Kit and DataHub SDK "
                    f"retrieval failed: {agent_context_error}"
                ),
            }

    def close(self) -> None:
        """Close any underlying clients when supported."""

        self._fallback.close()

        close_method = getattr(
            self._client,
            "close",
            None,
        )

        if callable(close_method):
            close_method()