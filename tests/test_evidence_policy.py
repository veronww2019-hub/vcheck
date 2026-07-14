"""Tests for the VCheck evidence-selection trust policy."""

from vcheck.services.evidence_policy import (
    evaluate_evidence_source,
    select_evidence,
)


def test_official_reviewed_current_is_primary() -> None:
    source = {
        "name": "Reviewed Scam Guidance",
        "source_classification": "official_style_guidance",
        "review_status": "reviewed",
        "freshness_status": "current",
        "reliability_level": "high",
        "allowed_for_decision": "true",
        "evidence_role": "primary",
    }

    result = evaluate_evidence_source(source)

    assert result["decision"] == "selected"
    assert result["role"] == "primary"
    assert result["reliability"] == "high"


def test_synthetic_evidence_is_supporting_only() -> None:
    source = {
        "name": "Synthetic Scam Pattern Library",
        "source_classification": "synthetic",
        "review_status": "reviewed",
        "freshness_status": "current",
        "reliability_level": "medium",
        "allowed_for_decision": "supporting_only",
        "evidence_role": "pattern_support",
    }

    result = evaluate_evidence_source(source)

    assert result["decision"] == "selected"
    assert result["role"] == "supporting_only"
    assert "cannot independently confirm" in result["reason"]


def test_unverified_community_evidence_is_excluded() -> None:
    source = {
        "name": "Community Reports",
        "source_classification": "community",
        "review_status": "unverified",
        "freshness_status": "current",
        "reliability_level": "low",
        "allowed_for_decision": "false",
        "evidence_role": "excluded_until_reviewed",
    }

    result = evaluate_evidence_source(source)

    assert result["decision"] == "excluded"
    assert result["role"] == "excluded"


def test_stale_evidence_is_excluded() -> None:
    source = {
        "name": "Old Scam Guidance",
        "source_classification": "official",
        "review_status": "reviewed",
        "freshness_status": "stale",
        "reliability_level": "high",
        "allowed_for_decision": "true",
    }

    result = evaluate_evidence_source(source)

    assert result["decision"] == "excluded"
    assert "stale" in result["reason"].lower()


def test_unknown_classification_is_excluded() -> None:
    source = {
        "name": "Unknown Source",
        "source_classification": "mystery",
        "review_status": "reviewed",
        "freshness_status": "current",
        "reliability_level": "unknown",
        "allowed_for_decision": "true",
    }

    result = evaluate_evidence_source(source)

    assert result["decision"] == "excluded"
    assert "unknown or unsupported" in result["reason"]


def test_select_evidence_returns_selected_and_excluded() -> None:
    sources = [
        {
            "name": "Reviewed Scam Guidance",
            "source_classification": "official_style_guidance",
            "review_status": "reviewed",
            "freshness_status": "current",
            "reliability_level": "high",
            "allowed_for_decision": "true",
        },
        {
            "name": "Synthetic Patterns",
            "source_classification": "synthetic",
            "review_status": "reviewed",
            "freshness_status": "current",
            "reliability_level": "medium",
            "allowed_for_decision": "supporting_only",
        },
        {
            "name": "Community Reports",
            "source_classification": "community",
            "review_status": "unverified",
            "freshness_status": "current",
            "reliability_level": "low",
            "allowed_for_decision": "false",
        },
    ]

    result = select_evidence(sources)

    assert len(result["selected_evidence"]) == 2
    assert len(result["excluded_evidence"]) == 1

    selected_roles = {
        item["role"]
        for item in result["selected_evidence"]
    }

    assert selected_roles == {"primary", "supporting_only"}
    assert "Selected 2 evidence source(s)" in result[
        "provenance_summary"
    ]