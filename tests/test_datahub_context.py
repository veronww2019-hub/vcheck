"""Tests for reading VCheck evidence metadata from DataHub."""

from __future__ import annotations

from typing import Any

from vcheck.services.datahub_context import (
    EVIDENCE_URNS,
    DataHubContextService,
)


class FakeDatasetProperties:
    """Small stand-in for DataHub's DatasetPropertiesClass."""

    def __init__(
        self,
        name: str,
        custom_properties: dict[str, str],
    ) -> None:
        self.name = name
        self.description = f"Description for {name}"
        self.customProperties = custom_properties


class FakeGraph:
    """Fake graph client so tests do not require Docker."""

    def __init__(
        self,
        properties_by_urn: dict[str, FakeDatasetProperties],
        available: bool = True,
    ) -> None:
        self.properties_by_urn = properties_by_urn
        self.available = available
        self.closed = False

    def test_connection(self) -> None:
        if not self.available:
            raise ConnectionError("DataHub is offline")

    def exists(self, entity_urn: str) -> bool:
        return entity_urn in self.properties_by_urn

    def get_dataset_properties(
        self,
        entity_urn: str,
    ) -> FakeDatasetProperties | None:
        return self.properties_by_urn.get(entity_urn)

    def close(self) -> None:
        self.closed = True


def _fake_properties() -> dict[str, FakeDatasetProperties]:
    return {
        EVIDENCE_URNS[0]: FakeDatasetProperties(
            name="VCheck Reviewed Scam Guidance",
            custom_properties={
                "source_classification": "official_style_guidance",
                "review_status": "reviewed",
                "freshness_status": "current",
                "reliability_level": "high",
                "allowed_for_decision": "true",
                "evidence_role": "primary",
            },
        ),
        EVIDENCE_URNS[1]: FakeDatasetProperties(
            name="VCheck Verified Demonstration Domains",
            custom_properties={
                "source_classification": "demonstration",
                "review_status": "reviewed",
                "freshness_status": "current",
                "reliability_level": "medium",
                "allowed_for_decision": "true",
                "evidence_role": "domain_demo",
            },
        ),
        EVIDENCE_URNS[2]: FakeDatasetProperties(
            name="VCheck Synthetic Scam Pattern Library",
            custom_properties={
                "source_classification": "synthetic",
                "review_status": "reviewed",
                "freshness_status": "current",
                "reliability_level": "medium",
                "allowed_for_decision": "supporting_only",
                "evidence_role": "pattern_support",
            },
        ),
        EVIDENCE_URNS[3]: FakeDatasetProperties(
            name="VCheck Unverified Community Reports",
            custom_properties={
                "source_classification": "community",
                "review_status": "unverified",
                "freshness_status": "current",
                "reliability_level": "low",
                "allowed_for_decision": "false",
                "evidence_role": "excluded_until_reviewed",
            },
        ),
    }


def test_reads_all_four_evidence_sources() -> None:
    graph = FakeGraph(_fake_properties())
    service = DataHubContextService(graph=graph)

    sources = service.get_evidence_sources()

    assert len(sources) == 4
    assert sources[0]["name"] == "VCheck Reviewed Scam Guidance"
    assert (
        sources[0]["custom_properties"]["review_status"]
        == "reviewed"
    )


def test_applies_policy_to_datahub_metadata() -> None:
    graph = FakeGraph(_fake_properties())
    service = DataHubContextService(graph=graph)

    result = service.select_trusted_evidence()

    assert len(result["selected_evidence"]) == 3
    assert len(result["excluded_evidence"]) == 1

    selected_roles = {
        source["role"]
        for source in result["selected_evidence"]
    }

    assert "primary" in selected_roles
    assert "supporting_only" in selected_roles

    excluded = result["excluded_evidence"][0]

    assert excluded["name"] == (
        "VCheck Unverified Community Reports"
    )
    assert excluded["role"] == "excluded"


def test_offline_datahub_returns_safe_fallback() -> None:
    graph = FakeGraph(
        properties_by_urn={},
        available=False,
    )
    service = DataHubContextService(graph=graph)

    result = service.get_context_bundle()

    assert result["available"] is False
    assert result["selected_evidence"] == []
    assert result["excluded_evidence"] == []
    assert result["warning"]


def test_context_bundle_contains_provenance_results() -> None:
    graph = FakeGraph(_fake_properties())
    service = DataHubContextService(graph=graph)

    result = service.get_context_bundle()

    assert result["available"] is True
    assert len(result["selected_evidence"]) == 3
    assert len(result["excluded_evidence"]) == 1
    assert result["warning"] is None
    assert "Selected 3 evidence source(s)" in (
        result["provenance_summary"]
    )


def test_close_closes_graph_client() -> None:
    graph = FakeGraph(_fake_properties())
    service = DataHubContextService(graph=graph)

    service.close()

    assert graph.closed is True