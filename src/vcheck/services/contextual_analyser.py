"""Add DataHub evidence context to VCheck analysis results."""

from __future__ import annotations

from collections.abc import Mapping
from typing import Any, Protocol

from vcheck.domain.models import AnalyseMessageResponse
from vcheck.services.analyser import MessageAnalyser


class ContextBundleProvider(Protocol):
    """Interface required from a DataHub context provider."""

    def get_context_bundle(self) -> dict[str, Any]:
        """Return selected and excluded DataHub evidence."""


class ContextualMessageAnalyser:
    """
    Combine the existing rule/ML analyser with DataHub context.

    The existing analyser remains responsible for the risk score.
    DataHub provides provenance-aware evidence explanations.
    """

    def __init__(
        self,
        message_analyser: MessageAnalyser,
        datahub_context: ContextBundleProvider,
    ) -> None:
        self._message_analyser = message_analyser
        self._datahub_context = datahub_context

    @property
    def rules(self):  # type: ignore[no-untyped-def]
        """Expose the existing rules for the rules endpoint."""

        return self._message_analyser.rules

    def analyse(
        self,
        text: str,
        request_id: str,
    ) -> AnalyseMessageResponse:
        """Analyse a message and attach DataHub evidence context."""

        base_result = self._message_analyser.analyse(
            text=text,
            request_id=request_id,
        )

        context = self._safe_context_bundle()

        response_data = base_result.model_dump()

        response_data.update(
            {
                "datahub_context_available": bool(
                    context.get("available", False)
                ),
                "datahub_integration_mode": context.get(
                    "integration_mode",
                    "unavailable",
                ),
                "selected_evidence": context.get(
                    "selected_evidence",
                    [],
                ),
                "excluded_evidence": context.get(
                    "excluded_evidence",
                    [],
                ),
                "provenance_summary": context.get(
                    "provenance_summary",
                    "Evidence provenance was not checked.",
                ),
                "context_warning": context.get("warning"),
            }
        )

        return AnalyseMessageResponse.model_validate(response_data)

    def _safe_context_bundle(self) -> Mapping[str, Any]:
        """
        Retrieve DataHub context without allowing it to crash analysis.

        DataHubContextService already handles expected connection failures.
        This additional guard protects the API from unexpected integration
        errors.
        """

        try:
            return self._datahub_context.get_context_bundle()
        except Exception as exc:
            return {
                "available": False,
                "selected_evidence": [],
                "excluded_evidence": [],
                "provenance_summary": (
                    "Evidence provenance could not be checked."
                ),
                "warning": (
                    "The rule and machine-learning analysis completed, "
                    f"but DataHub context retrieval failed: {exc}"
                ),
            }