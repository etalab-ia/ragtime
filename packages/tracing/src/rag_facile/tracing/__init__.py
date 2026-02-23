"""Tracing - RAG pipeline observability and trace persistence.

Provides a :class:`TracingProvider` interface for logging RAG pipeline
traces (queries, retrieved chunks, LLM responses, user feedback) with a
built-in SQLite backend and a no-op fallback.

Typical usage from the pipeline::

    from rag_facile.tracing import get_tracer, set_current_trace_id

    tracer = get_tracer()
    trace_id = tracer.log_trace(trace)
    set_current_trace_id(trace_id)

Typical usage from an application (after LLM generation)::

    from rag_facile.tracing import get_tracer, get_current_trace_id

    trace_id = get_current_trace_id()
    if trace_id:
        get_tracer().update_trace(trace_id, response=answer, latency_ms=42)
"""

from __future__ import annotations

import contextvars
import threading
from pathlib import Path
from collections.abc import Callable
from typing import Any

from ._base import TracingProvider
from ._models import FeedbackUpdate, TraceRecord

# ── Singleton tracer cache ────────────────────────────────────────────────────

_tracer: TracingProvider | None = None
_lock = threading.Lock()

# ── Trace ID propagation via contextvars ──────────────────────────────────────
# Set by the pipeline after logging a trace; read by apps to enrich it with
# LLM response and user feedback.  Thread-safe and async-safe.

_current_trace_id: contextvars.ContextVar[str | None] = contextvars.ContextVar(
    "rag_trace_id",
    default=None,
)


def get_current_trace_id() -> str | None:
    """Return the trace ID set by the most recent ``process_query()`` call.

    Returns *None* if no trace has been logged in the current context.
    """
    return _current_trace_id.get()


def set_current_trace_id(trace_id: str | None) -> None:
    """Set the current trace ID (called by the pipeline after logging)."""
    _current_trace_id.set(trace_id)


# ── Trace event hook ──────────────────────────────────────────────────────────
# Allows UI frameworks to subscribe to trace events without coupling to a
# specific provider.

_on_trace_logged: Callable[[TraceRecord], None] | None = None


def set_trace_hook(callback: Callable[[TraceRecord], None] | None) -> None:
    """Register a callback invoked after every trace is logged.

    UI frameworks can use this to bridge RAG traces into their own
    persistence layer (e.g., Chainlit's BaseDataLayer metadata,
    Reflex state).

    Pass *None* to clear the hook.

    Args:
        callback: Function receiving the :class:`TraceRecord` after logging.
    """
    global _on_trace_logged  # noqa: PLW0603
    _on_trace_logged = callback


def _notify_hook(trace: TraceRecord) -> None:
    """Invoke the trace hook if one is registered."""
    if _on_trace_logged is not None:
        _on_trace_logged(trace)


# ── Factory ───────────────────────────────────────────────────────────────────


def _resolve_db_path(raw_path: str) -> Path:
    """Resolve the database path relative to the workspace root.

    If the path is relative, it's resolved relative to the directory
    containing ``ragfacile.toml`` (found by walking up from CWD).
    This ensures the database lands at the workspace root regardless
    of which subdirectory an app runs from (e.g. ``apps/chainlit-chat/``).
    """
    db = Path(raw_path)
    if db.is_absolute():
        return db

    # Walk up from CWD to find ragfacile.toml → its parent = workspace root
    from rag_facile.core.loader import _find_config_file

    config_file = _find_config_file()
    if config_file is not None:
        return config_file.parent / db

    # Fallback: resolve relative to CWD (standalone projects without ragfacile.toml)
    return Path.cwd() / db


def get_tracer(config: Any | None = None) -> TracingProvider:
    """Return a configured tracing provider (singleton).

    Reads ``[tracing]`` from ``ragfacile.toml`` on first call.
    Subsequent calls return the cached instance.

    Args:
        config: Optional RAGConfig.  If *None*, loads from ragfacile.toml.

    Returns:
        A :class:`TracingProvider` ready to log traces.
    """
    global _tracer  # noqa: PLW0603
    if _tracer is not None:
        return _tracer

    with _lock:
        if _tracer is not None:
            return _tracer

        if config is None:
            from rag_facile.core import get_config

            config = get_config()

        tracing_cfg = config.tracing

        if not tracing_cfg.enabled:
            from .noop import NoopProvider

            _tracer = NoopProvider()
        else:
            match tracing_cfg.provider:
                case "sqlite":
                    from .sqlite import SQLiteProvider

                    _tracer = SQLiteProvider(_resolve_db_path(tracing_cfg.database))
                case "none":
                    from .noop import NoopProvider

                    _tracer = NoopProvider()
                case _:
                    msg = (
                        f"Unknown tracing provider: {tracing_cfg.provider!r}. "
                        "Expected 'sqlite' or 'none'."
                    )
                    raise ValueError(msg)

    return _tracer


def _reset_tracer() -> None:
    """Reset the singleton (for testing only)."""
    global _tracer  # noqa: PLW0603
    _tracer = None


__all__ = [
    "FeedbackUpdate",
    "TraceRecord",
    "TracingProvider",
    "_notify_hook",
    "_reset_tracer",
    "get_current_trace_id",
    "get_tracer",
    "set_current_trace_id",
    "set_trace_hook",
]
