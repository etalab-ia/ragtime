"""No-op tracing provider.

Returns trace IDs but persists nothing.  Used when tracing is disabled
(``tracing.enabled = false`` or ``tracing.provider = "none"``).
"""

from __future__ import annotations

from ._base import TracingProvider
from ._models import TraceRecord


class NoopProvider(TracingProvider):
    """Tracing provider that discards all data.

    All write methods are no-ops; reads return empty results.
    This allows pipeline code to call ``get_tracer()`` unconditionally
    without checking whether tracing is enabled.
    """

    def log_trace(self, trace: TraceRecord) -> str:
        """Accept and discard the trace, returning its ID."""
        return trace.id

    def update_trace(self, trace_id: str, **fields: object) -> None:
        """No-op update."""

    def get_trace(self, trace_id: str) -> TraceRecord | None:
        """Always returns None."""
        return None

    def list_traces(
        self,
        *,
        session_id: str | None = None,
        user_id: str | None = None,
        limit: int = 50,
        offset: int = 0,
    ) -> list[TraceRecord]:
        """Always returns an empty list."""
        return []

    def add_feedback(
        self,
        trace_id: str,
        score: int | None = None,
        tags: list[str] | None = None,
        comment: str | None = None,
    ) -> None:
        """No-op feedback."""

    def delete_traces(self, *, older_than_days: int) -> int:
        """No-op delete. Returns 0."""
        return 0
