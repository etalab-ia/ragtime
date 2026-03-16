"""Abstract base class for trace storage backends.

Concrete providers implement this interface to persist RAG pipeline traces.
The factory in ``__init__.py`` selects the provider based on
``ragfacile.toml`` configuration.
"""

from __future__ import annotations

from abc import ABC, abstractmethod

from ._models import TraceRecord


class TracingProvider(ABC):
    """Abstract RAG trace storage backend.

    Subclasses must implement all abstract methods.  The pipeline logs
    traces via :meth:`log_trace`, applications enrich them with
    :meth:`update_trace`, and user feedback is added via
    :meth:`add_feedback`.
    """

    @abstractmethod
    def log_trace(self, trace: TraceRecord) -> str:
        """Persist a new trace record.

        Args:
            trace: The trace to store.

        Returns:
            The trace ID (same as ``trace.id``).
        """

    @abstractmethod
    def update_trace(self, trace_id: str, **fields: object) -> None:
        """Update specific fields on an existing trace.

        Typical fields updated after initial logging:
        ``response``, ``latency_ms``, ``response_at``,
        ``session_id``, ``user_id``.

        Args:
            trace_id: ID of the trace to update.
            **fields: Field names and new values.
        """

    @abstractmethod
    def get_trace(self, trace_id: str) -> TraceRecord | None:
        """Retrieve a trace by its ID.

        Args:
            trace_id: Trace identifier.

        Returns:
            The trace record, or *None* if not found.
        """

    @abstractmethod
    def list_traces(
        self,
        *,
        session_id: str | None = None,
        user_id: str | None = None,
        limit: int = 50,
        offset: int = 0,
    ) -> list[TraceRecord]:
        """List traces with optional filtering.

        Args:
            session_id: Filter by session.
            user_id: Filter by user.
            limit: Maximum number of traces to return.
            offset: Pagination offset.

        Returns:
            List of matching traces, newest first.
        """

    @abstractmethod
    def add_feedback(
        self,
        trace_id: str,
        score: int | None = None,
        tags: list[str] | None = None,
        comment: str | None = None,
    ) -> None:
        """Add or update user feedback on a trace.

        Args:
            trace_id: ID of the trace to annotate.
            score: Satisfaction score (e.g. 1-5 or +1/-1).
            tags: Structured feedback tags.
            comment: Free-text feedback.
        """

    @abstractmethod
    def delete_traces(self, *, older_than_days: int) -> int:
        """Delete traces older than N days.

        Args:
            older_than_days: Delete traces whose ``created_at`` is older
                than this many days from now (UTC).

        Returns:
            Number of traces deleted.
        """
