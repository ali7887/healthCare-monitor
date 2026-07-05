"""Domain telemetry: structured events for the critical user-visible flows.

Thin helper functions over :func:`app.core.logging.log_event` — deliberately
not a framework. Each helper logs **safe metadata only** (ids, statuses,
counts, outcome categories) so we get operational visibility into review,
assistant, and dashboard activity without ever writing raw clinical text or a
full payload to the logs.

When called inside a request the correlation ``request_id`` is attached
automatically by the log formatter (via the request contextvar), so these
helpers don't take it as a parameter.
"""

from __future__ import annotations

from uuid import UUID

from app.core.logging import get_logger, log_event

_logger = get_logger("telemetry")

# ``str`` is accepted alongside ``UUID`` so seed scripts / tests can pass either.
IdLike = UUID | str


# --- Runs -----------------------------------------------------------------


def log_run_detail(run_id: IdLike, *, found: bool) -> None:
    """A single-run trace fetch (found or 404)."""
    log_event(
        _logger,
        "run_detail_fetch",
        run_id=str(run_id),
        outcome="found" if found else "not_found",
    )


# --- Reviews --------------------------------------------------------------


def log_review_decision(
    *, review_id: IdLike, run_id: IdLike, action: str, run_status: str, edited: bool
) -> None:
    """A completed human review decision (approve/reject)."""
    log_event(
        _logger,
        "review_decision",
        review_id=str(review_id),
        run_id=str(run_id),
        action=action,
        run_status=run_status,
        edited=edited,
    )


def log_review_conflict(*, review_id: IdLike) -> None:
    """A rejected re-decision on an already-decided review (409)."""
    log_event(
        _logger,
        "review_conflict",
        review_id=str(review_id),
        outcome="conflict",
    )


def log_review_not_found(*, review_id: IdLike) -> None:
    """An action against a review item that does not exist (404)."""
    log_event(
        _logger,
        "review_not_found",
        review_id=str(review_id),
        outcome="not_found",
    )


# --- AI reviewer assistant ------------------------------------------------


def log_assistant_request(*, run_id: IdLike, edited_supplied: bool) -> None:
    """An advisory assistant analysis was requested."""
    log_event(
        _logger,
        "assistant_analyze_request",
        run_id=str(run_id),
        edited_supplied=edited_supplied,
    )


def log_assistant_success(*, run_id: IdLike, risk_count: int) -> None:
    """An advisory analysis completed; ``outcome`` mirrors the UI state."""
    log_event(
        _logger,
        "assistant_analyze_success",
        run_id=str(run_id),
        risk_count=risk_count,
        outcome="risk_alert" if risk_count > 0 else "stable",
    )


def log_assistant_failure(*, run_id: IdLike, reason: str) -> None:
    """An advisory analysis could not be produced (e.g. unknown run)."""
    log_event(
        _logger,
        "assistant_analyze_failure",
        run_id=str(run_id),
        outcome="failure",
        reason=reason,
    )


# --- Dashboard ------------------------------------------------------------


def log_dashboard_stats(*, total_runs: int) -> None:
    """Aggregate dashboard stats fetch."""
    log_event(_logger, "dashboard_stats_fetch", total_runs=total_runs)


def log_dashboard_timeseries(*, days: int, point_count: int) -> None:
    """Dashboard throughput time-series fetch."""
    log_event(
        _logger,
        "dashboard_timeseries_fetch",
        days=days,
        point_count=point_count,
    )


# --- Seed -----------------------------------------------------------------


def log_seed_complete(*, total: int, reset: bool) -> None:
    """The demo seed finished loading its dataset."""
    log_event(
        _logger,
        "seed_demo_complete",
        total=total,
        mode="reset" if reset else "append",
    )
