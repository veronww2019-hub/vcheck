"""Trust policy for selecting DataHub evidence sources."""

from __future__ import annotations

from collections.abc import Iterable, Mapping
from typing import Any


def _normalise(value: Any) -> str:
    """Convert a metadata value into a normalised lowercase string."""

    if value is None:
        return ""

    return str(value).strip().lower()


def _get_metadata_value(
    source: Mapping[str, Any],
    key: str,
    default: Any = "",
) -> Any:
    """Read a property from either the source or its custom properties."""

    if key in source:
        return source[key]

    custom_properties = source.get(
        "custom_properties",
        source.get("customProperties", {}),
    )

    if isinstance(custom_properties, Mapping):
        return custom_properties.get(key, default)

    return default


def evaluate_evidence_source(
    source: Mapping[str, Any],
) -> dict[str, Any]:
    """
    Evaluate one evidence source using deterministic trust rules.

    Returns a dictionary containing the source's decision, reliability,
    evidence role, and a human-readable reason.
    """

    name = str(
        source.get(
            "name",
            source.get("display_name", "Unnamed evidence source"),
        )
    )

    source_classification = _normalise(
        _get_metadata_value(source, "source_classification")
    )
    review_status = _normalise(
        _get_metadata_value(source, "review_status")
    )
    freshness_status = _normalise(
        _get_metadata_value(source, "freshness_status")
    )
    reliability_level = _normalise(
        _get_metadata_value(source, "reliability_level")
    )
    allowed_for_decision = _normalise(
        _get_metadata_value(source, "allowed_for_decision")
    )
    evidence_role = _normalise(
        _get_metadata_value(source, "evidence_role")
    )

    result: dict[str, Any] = {
        "name": name,
        "urn": source.get("urn"),
        "source_classification": source_classification,
        "review_status": review_status,
        "freshness_status": freshness_status,
        "reliability": reliability_level or "unknown",
        "configured_evidence_role": evidence_role or "unknown",
    }

    # Explicitly blocked evidence must never influence the risk decision.
    if allowed_for_decision in {"false", "no", "0", "blocked"}:
        result.update(
            {
                "decision": "excluded",
                "role": "excluded",
                "reason": (
                    "The source is explicitly not approved for "
                    "decision-making."
                ),
            }
        )
        return result

    # Sources must be reviewed before being trusted.
    if review_status != "reviewed":
        result.update(
            {
                "decision": "excluded",
                "role": "excluded",
                "reason": (
                    "The source has not been reviewed and cannot be used "
                    "as trusted evidence."
                ),
            }
        )
        return result

    # Stale evidence should not be used for the prototype's decision.
    if freshness_status == "stale":
        result.update(
            {
                "decision": "excluded",
                "role": "excluded",
                "reason": (
                    "The source is marked as stale and may no longer be "
                    "reliable."
                ),
            }
        )
        return result

    # Synthetic evidence can help recognise patterns but cannot confirm
    # whether a real message is fraudulent.
    if (
        allowed_for_decision == "supporting_only"
        or source_classification == "synthetic"
    ):
        result.update(
            {
                "decision": "selected",
                "role": "supporting_only",
                "reason": (
                    "The source is reviewed synthetic evidence. It may "
                    "support pattern recognition but cannot independently "
                    "confirm a real scam."
                ),
            }
        )
        return result

    # Reviewed, current, high-reliability official-style guidance becomes
    # primary evidence.
    if source_classification in {
        "official",
        "official_style_guidance",
    }:
        result.update(
            {
                "decision": "selected",
                "role": "primary",
                "reason": (
                    "The source is reviewed, current, and approved as "
                    "primary guidance."
                ),
            }
        )
        return result

    # Demonstration, public, or reviewed community evidence may support the
    # result, but should not become the sole basis of the decision.
    if source_classification in {
        "public",
        "demonstration",
        "community",
    }:
        result.update(
            {
                "decision": "selected",
                "role": "supporting",
                "reason": (
                    "The source is reviewed and current, but is used only "
                    "as supporting evidence."
                ),
            }
        )
        return result

    # Unknown classifications are rejected safely.
    result.update(
        {
            "decision": "excluded",
            "role": "excluded",
            "reason": (
                "The source classification is unknown or unsupported by "
                "the evidence policy."
            ),
        }
    )

    return result


def select_evidence(
    sources: Iterable[Mapping[str, Any]],
) -> dict[str, Any]:
    """
    Evaluate multiple evidence sources.

    Returns selected evidence, excluded evidence, and a provenance summary.
    """

    selected_evidence: list[dict[str, Any]] = []
    excluded_evidence: list[dict[str, Any]] = []

    for source in sources:
        result = evaluate_evidence_source(source)

        if result["decision"] == "selected":
            selected_evidence.append(result)
        else:
            excluded_evidence.append(result)

    primary_count = sum(
        item["role"] == "primary"
        for item in selected_evidence
    )
    supporting_count = sum(
        item["role"] in {"supporting", "supporting_only"}
        for item in selected_evidence
    )

    provenance_summary = (
        f"Selected {len(selected_evidence)} evidence source(s): "
        f"{primary_count} primary and {supporting_count} supporting. "
        f"Excluded {len(excluded_evidence)} source(s) because they did "
        f"not satisfy the trust policy."
    )

    return {
        "selected_evidence": selected_evidence,
        "excluded_evidence": excluded_evidence,
        "provenance_summary": provenance_summary,
    }