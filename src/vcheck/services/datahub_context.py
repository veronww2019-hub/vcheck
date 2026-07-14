"""Read VCheck evidence-source metadata from DataHub."""

from __future__ import annotations

import os
from collections.abc import Mapping
from typing import Any, Protocol

from datahub.ingestion.graph.client import (
    DatahubClientConfig,
    DataHubGraph,
)

from vcheck.services.evidence_policy import select_evidence


EVIDENCE_URNS: tuple[str, ...] = (
    (
        "urn:li:dataset:(urn:li:dataPlatform:vcheck,"
        "vcheck.evidence.official_scam_guidance,PROD)"
    ),
    (
        "urn:li:dataset:(urn:li:dataPlatform:vcheck,"
        "vcheck.evidence.verified_domains,PROD)"
    ),
    (
        "urn:li:dataset:(urn:li:dataPlatform:vcheck,"
        "vcheck.evidence.synthetic_scam_patterns,PROD)"
    ),
    (
        "urn:li:dataset:(urn:li:dataPlatform:vcheck,"
        "vcheck.evidence.community_reports,PROD)"
    ),
)


class DataHubUnavailableError(RuntimeError):
    """Raised when VCheck cannot retrieve required DataHub context."""


class GraphClientProtocol(Protocol):
    """Small interface used by the service and its unit tests."""

    def test_connection(self) -> None:
        """Test the DataHub connection."""

    def exists(self, entity_urn: str) -> bool:
        """Return whether an entity exists."""

    def get_dataset_properties(self, entity_urn: str) -> Any:
        """Return the dataset properties aspect."""

    def close(self) -> None:
        """Close the client."""


class DataHubContextService:
    """Retrieve and evaluate VCheck evidence metadata from DataHub."""

    def __init__(
        self,
        gms_url: str | None = None,
        token: str | None = None,
        graph: GraphClientProtocol | None = None,
    ) -> None:
        self.gms_url = (
            gms_url
            or os.getenv("DATAHUB_GMS_URL")
            or "http://localhost:8080"
        )

        self.token = token or os.getenv("DATAHUB_GMS_TOKEN")

        if graph is not None:
            self._graph = graph
            return

        config_values: dict[str, Any] = {
            "server": self.gms_url,
        }

        if self.token:
            config_values["token"] = self.token

        self._graph = DataHubGraph(
            DatahubClientConfig(**config_values)
        )

    def is_available(self) -> bool:
        """Return True when the DataHub GMS connection works."""

        try:
            self._graph.test_connection()
        except Exception:
            return False

        return True

    @staticmethod
    def _properties_to_source(
        urn: str,
        properties: Any,
    ) -> dict[str, Any]:
        """Convert DataHub dataset properties into policy input."""

        custom_properties = getattr(
            properties,
            "customProperties",
            {},
        )

        if not isinstance(custom_properties, Mapping):
            custom_properties = {}

        name = getattr(properties, "name", None)
        description = getattr(properties, "description", None)

        return {
            "urn": urn,
            "name": name or urn,
            "description": description or "",
            "custom_properties": dict(custom_properties),
        }

    def get_evidence_sources(self) -> list[dict[str, Any]]:
        """Retrieve the four registered evidence sources."""

        if not self.is_available():
            raise DataHubUnavailableError(
                f"DataHub is unavailable at {self.gms_url}."
            )

        sources: list[dict[str, Any]] = []

        for urn in EVIDENCE_URNS:
            try:
                exists = self._graph.exists(urn)
            except Exception as exc:
                raise DataHubUnavailableError(
                    f"Could not check DataHub entity: {urn}"
                ) from exc

            if not exists:
                raise DataHubUnavailableError(
                    f"Required DataHub evidence asset does not exist: {urn}"
                )

            try:
                properties = self._graph.get_dataset_properties(urn)
            except Exception as exc:
                raise DataHubUnavailableError(
                    f"Could not read dataset properties for: {urn}"
                ) from exc

            if properties is None:
                raise DataHubUnavailableError(
                    f"No dataset properties were found for: {urn}"
                )

            sources.append(
                self._properties_to_source(
                    urn=urn,
                    properties=properties,
                )
            )

        return sources

    def select_trusted_evidence(self) -> dict[str, Any]:
        """Read DataHub context and apply the evidence trust policy."""

        sources = self.get_evidence_sources()
        return select_evidence(sources)

    def get_context_bundle(self) -> dict[str, Any]:
        """
        Return evidence context without crashing the analyser.

        This method provides the Phase 3C offline fallback.
        """

        try:
            selection = self.select_trusted_evidence()
        except DataHubUnavailableError as exc:
            return {
                "available": False,
                "selected_evidence": [],
                "excluded_evidence": [],
                "provenance_summary": (
                    "Evidence provenance could not be checked."
                ),
                "warning": str(exc),
            }

        return {
            "available": True,
            "selected_evidence": selection["selected_evidence"],
            "excluded_evidence": selection["excluded_evidence"],
            "provenance_summary": selection["provenance_summary"],
            "warning": None,
        }

    def close(self) -> None:
        """Close the underlying DataHub client."""

        try:
            self._graph.close()
        except Exception:
            # Closing must not crash application shutdown.
            pass