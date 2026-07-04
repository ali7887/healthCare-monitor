"""Processing pipeline: extraction -> parse/validate, with one bounded retry.

This coordinator ties together the AI orchestration layer (Phase 3) and the
deterministic validation engine (Phase 5). Control flow is deterministic; the
only nondeterministic step is the provider call itself.

Retry policy (Phase 7): at most ONE self-correction retry, triggered only by
retryable provider failures or structurally-unusable output (parsing/schema
failure). Valid notes with clinical/completeness issues are never retried, and
permanent provider failures are never retried.
"""

from __future__ import annotations

import re
from collections.abc import Callable
from dataclasses import dataclass, replace

from app.schemas.clinical_note import ClinicalNote
from app.schemas.validation import ValidationIssue
from app.services.confidence import ConfidenceResult, ConfidenceScorer
from app.services.prompts import DEFAULT_PROMPT_VERSION
from app.services.providers import ExtractionProvider, ExtractionResult, get_provider
from app.services.routing import RoutingEngine, RoutingResult
from app.services.validation import parse_and_validate

# Stable retry-trigger categories (kept as strings for later metrics).
RETRY_TRIGGER_PROVIDER = "provider_retryable_error"
RETRY_TRIGGER_INVALID_JSON = "invalid_json"
RETRY_TRIGGER_SCHEMA = "schema_validation_failed"

MAX_RETRIES = 1

# Rule ids that indicate JSON-level (not schema-shape) failure.
_INVALID_JSON_RULE_IDS = {"ERR_SCHEMA_INVALID_JSON", "ERR_SCHEMA_NOT_OBJECT"}

# Cap prior-output length included in the correction prompt.
_MAX_PRIOR_OUTPUT_CHARS = 2000

_FENCE_RE = re.compile(r"^```(?:json)?\s*|\s*```$", re.IGNORECASE)

ProviderFactory = Callable[..., ExtractionProvider]


@dataclass(frozen=True)
class PipelineRunResult:
    """Unified, inspectable outcome of a pipeline run.

    ``raw_response`` and ``final_response`` both point to the final attempt.
    ``initial_response`` holds attempt 1 only when a retry occurred.
    """

    transcript: str
    extracted_note: ClinicalNote | None
    issues: list[ValidationIssue]
    raw_response: ExtractionResult
    final_response: ExtractionResult
    succeeded: bool
    retry_count: int = 0
    initial_response: ExtractionResult | None = None
    retry_trigger: str | None = None
    retry_context_summary: str | None = None
    confidence: ConfidenceResult | None = None
    routing: RoutingResult | None = None


def _extract_json_text(text: str) -> str:
    """Strip surrounding markdown code fences from a JSON-ish string."""
    stripped = text.strip()
    stripped = _FENCE_RE.sub("", stripped)
    return stripped.strip()


class ProcessingPipeline:
    """Runs a transcript through extraction, parsing, validation, and one retry."""

    def __init__(
        self,
        provider_factory: ProviderFactory = get_provider,
        *,
        confidence_scorer: ConfidenceScorer | None = None,
        routing_engine: RoutingEngine | None = None,
    ) -> None:
        self._provider_factory = provider_factory
        self._confidence_scorer = confidence_scorer or ConfidenceScorer()
        self._routing_engine = routing_engine or RoutingEngine()

    # -- public API ----------------------------------------------------------

    def run(
        self,
        transcript: str,
        provider_name: str,
        *,
        model: str | None = None,
        prompt_version: str = DEFAULT_PROMPT_VERSION,
    ) -> PipelineRunResult:
        provider = self._provider_factory(
            provider_name, model=model, prompt_version=prompt_version
        )

        # --- Attempt 1 ---
        attempt1 = provider.extract(transcript)
        note1, issues1 = self._parse(attempt1)
        trigger = self._retry_trigger(attempt1, note1, issues1)

        if trigger is None:
            base = self._build_result(
                transcript=transcript,
                note=note1,
                issues=issues1,
                final=attempt1,
                initial=None,
                retry_count=0,
                trigger=None,
                summary=None,
            )
            return self._finalize(base)

        # --- Attempt 2 (single, bounded self-correction) ---
        summary = self._summarize_retry_context(trigger, attempt1, issues1)
        retry_prompt = self._build_retry_prompt(transcript, attempt1, issues1, trigger)
        attempt2 = provider.extract(retry_prompt)
        note2, issues2 = self._parse(attempt2)

        base = self._build_result(
            transcript=transcript,
            note=note2,
            issues=issues2,
            final=attempt2,
            initial=attempt1,
            retry_count=1,
            trigger=trigger,
            summary=summary,
        )
        return self._finalize(base)

    def _finalize(self, base: PipelineRunResult) -> PipelineRunResult:
        """Attach confidence + routing to the result (no side effects).

        Persistence (including routing HUMAN_REVIEW runs to the DB review table)
        is handled by ``app.services.persistence`` at the API boundary.
        """
        confidence = self._confidence_scorer.calculate(base)
        routing = self._routing_engine.route(base, confidence)
        return replace(base, confidence=confidence, routing=routing)

    # -- internals -----------------------------------------------------------

    def _parse(
        self, result: ExtractionResult
    ) -> tuple[ClinicalNote | None, list[ValidationIssue]]:
        """Parse an extraction result. Provider failures yield (None, [])."""
        if not result.succeeded:
            return None, []
        cleaned = _extract_json_text(result.content or "")
        return parse_and_validate(cleaned)

    def _retry_trigger(
        self,
        result: ExtractionResult,
        note: ClinicalNote | None,
        issues: list[ValidationIssue],
    ) -> str | None:
        """Decide whether attempt 1 warrants a retry, and why.

        Returns a stable trigger category, or None if no retry is warranted.
        """
        # Provider-level failure.
        if not result.succeeded:
            return RETRY_TRIGGER_PROVIDER if result.retryable_error else None

        # Provider succeeded and produced a valid note -> never retry here,
        # even if clinical/completeness issues exist.
        if note is not None:
            return None

        # Provider succeeded but output was structurally unusable.
        rule_ids = {issue.rule_id for issue in issues}
        if rule_ids & _INVALID_JSON_RULE_IDS:
            return RETRY_TRIGGER_INVALID_JSON
        return RETRY_TRIGGER_SCHEMA

    def _summarize_retry_context(
        self,
        trigger: str,
        attempt1: ExtractionResult,
        issues: list[ValidationIssue],
    ) -> str:
        """Produce a compact, human-readable reason for the retry."""
        if trigger == RETRY_TRIGGER_PROVIDER:
            return f"provider retryable error on first attempt: {attempt1.error}"
        if trigger == RETRY_TRIGGER_INVALID_JSON:
            return "previous output was not valid JSON"
        fields = [i.field_path for i in issues if i.field_path]
        if fields:
            return "schema issue fields: " + ", ".join(fields)
        return "schema validation failed on first attempt"

    def _build_retry_prompt(
        self,
        transcript: str,
        attempt1: ExtractionResult,
        issues: list[ValidationIssue],
        trigger: str,
    ) -> str:
        """Compose a correction user-message.

        Passed as the transcript argument to the provider's ``extract`` so the
        unchanged system prompt (JSON-only) still applies; the correction
        context is appended in the user turn. No prior output is fabricated.
        """
        lines: list[str] = [
            "The previous attempt to produce a structured clinical note was not usable.",
        ]

        if trigger == RETRY_TRIGGER_PROVIDER:
            lines.append(
                "The previous attempt failed to return any output due to a provider error."
            )
        elif trigger == RETRY_TRIGGER_INVALID_JSON:
            lines.append("Your previous output was not valid JSON.")
        else:
            lines.append("Your previous output did not conform to the expected schema.")

        if issues:
            lines.append("Issues detected:")
            for issue in issues:
                location = issue.field_path or "(document)"
                lines.append(f"- {location}: {issue.message}")

        prior = attempt1.raw_response_text
        if prior:
            snippet = prior[:_MAX_PRIOR_OUTPUT_CHARS]
            lines.append("Your previous output was:")
            lines.append(snippet)

        lines.append(
            "Return corrected output as a single valid JSON object only, "
            "matching the required schema. Do not include any prose or markdown."
        )
        lines.append("Original transcript:")
        lines.append(transcript)

        return "\n".join(lines)

    def _build_result(
        self,
        *,
        transcript: str,
        note: ClinicalNote | None,
        issues: list[ValidationIssue],
        final: ExtractionResult,
        initial: ExtractionResult | None,
        retry_count: int,
        trigger: str | None,
        summary: str | None,
    ) -> PipelineRunResult:
        succeeded = final.succeeded and note is not None
        return PipelineRunResult(
            transcript=transcript,
            extracted_note=note,
            issues=issues,
            raw_response=final,
            final_response=final,
            succeeded=succeeded,
            retry_count=retry_count,
            initial_response=initial,
            retry_trigger=trigger,
            retry_context_summary=summary,
        )
