"""Tests for the rag-facile traces command group."""

from __future__ import annotations

import json
from datetime import datetime, timezone
from unittest.mock import MagicMock, patch

from typer.testing import CliRunner

from cli.main import app as main_app


runner = CliRunner()

# ── Fixtures ──────────────────────────────────────────────────────────────────


def _make_trace(
    trace_id: str = "a1b2c3d4-0000-0000-0000-000000000000",
    query: str = "What is RAG?",
    model: str = "openweight-medium",
    latency_ms: int | None = 1200,
    feedback_score: int | None = None,
    feedback_comment: str | None = None,
    response: str | None = "RAG stands for Retrieval-Augmented Generation.",
):
    """Build a minimal TraceRecord-like mock."""
    from rag_facile.tracing import TraceRecord

    return TraceRecord(
        id=trace_id,
        query=query,
        model=model,
        latency_ms=latency_ms,
        feedback_score=feedback_score,
        feedback_tags=[],
        feedback_comment=feedback_comment,
        response=response,
        created_at=datetime(2026, 3, 10, 12, 0, 0, tzinfo=timezone.utc),
        temperature=0.2,
    )


def _mock_tracer(traces=None, trace_by_id=None, delete_count=0):
    """Return a mock TracingProvider."""
    tracer = MagicMock()
    tracer.list_traces.return_value = traces if traces is not None else []
    tracer.get_trace.return_value = trace_by_id
    tracer.delete_traces.return_value = delete_count
    return tracer


# ── traces list ───────────────────────────────────────────────────────────────


class TestTracesListCommand:
    def test_empty_tracer_shows_no_traces_message(self):
        """list with no traces shows helpful message."""
        with patch("rag_facile.tracing.get_tracer", return_value=_mock_tracer()):
            result = runner.invoke(main_app, ["traces", "list"])
        assert result.exit_code == 0
        assert "No traces found" in result.output

    def test_list_shows_table_with_traces(self):
        """list renders a table when traces exist."""
        traces = [
            _make_trace(trace_id=f"a1b2c3d4-000{i}-0000-0000-000000000000")
            for i in range(3)
        ]
        with patch(
            "rag_facile.tracing.get_tracer", return_value=_mock_tracer(traces=traces)
        ):
            result = runner.invoke(main_app, ["traces", "list"])
        assert result.exit_code == 0
        assert "a1b2c3d4" in result.output
        # Query column may be truncated by Rich in narrow terminal — check prefix
        assert "Wh" in result.output  # "What is RAG?" starts with "Wh"

    def test_list_passes_limit_option(self):
        """--limit is forwarded to list_traces."""
        mock = _mock_tracer()
        with patch("rag_facile.tracing.get_tracer", return_value=mock):
            runner.invoke(main_app, ["traces", "list", "--limit", "5"])
        mock.list_traces.assert_called_once_with(session_id=None, user_id=None, limit=5)

    def test_list_passes_session_filter(self):
        """--session is forwarded to list_traces."""
        mock = _mock_tracer()
        with patch("rag_facile.tracing.get_tracer", return_value=mock):
            runner.invoke(main_app, ["traces", "list", "--session", "my-session"])
        mock.list_traces.assert_called_once_with(
            session_id="my-session", user_id=None, limit=20
        )


# ── traces show ───────────────────────────────────────────────────────────────


class TestTracesShowCommand:
    def test_show_unknown_id_exits_with_error(self):
        """show with unknown ID exits 1 and prints error."""
        mock = _mock_tracer(traces=[], trace_by_id=None)
        with patch("rag_facile.tracing.get_tracer", return_value=mock):
            result = runner.invoke(main_app, ["traces", "show", "nonexistent-id"])
        assert result.exit_code == 1
        assert "not found" in result.output.lower()

    def test_show_exact_id_displays_detail(self):
        """show with exact ID renders trace detail panels."""
        trace = _make_trace()
        mock = _mock_tracer(trace_by_id=trace)
        with patch("rag_facile.tracing.get_tracer", return_value=mock):
            result = runner.invoke(main_app, ["traces", "show", trace.id])
        assert result.exit_code == 0
        assert "What is RAG" in result.output
        assert "openweight-medium" in result.output
        assert "RAG stands for" in result.output

    def test_show_prefix_resolves_unique_match(self):
        """show with a unique prefix resolves to the matching trace."""
        trace = _make_trace(trace_id="a1b2c3d4-1111-0000-0000-000000000000")
        # get_trace returns None for prefix, list_traces returns the trace
        mock = _mock_tracer(traces=[trace], trace_by_id=None)
        with patch("rag_facile.tracing.get_tracer", return_value=mock):
            result = runner.invoke(main_app, ["traces", "show", "a1b2c3d4"])
        assert result.exit_code == 0
        assert "What is RAG" in result.output


# ── traces stats ──────────────────────────────────────────────────────────────


class TestTracesStatsCommand:
    def test_stats_empty_shows_no_traces(self):
        """stats with no traces shows empty state."""
        with patch("rag_facile.tracing.get_tracer", return_value=_mock_tracer()):
            result = runner.invoke(main_app, ["traces", "stats"])
        assert result.exit_code == 0
        assert "No traces found" in result.output

    def test_stats_shows_overview(self):
        """stats shows total count and latency."""
        traces = [
            _make_trace(
                trace_id=f"aaaabbbb-000{i}-0000-0000-000000000000",
                latency_ms=1000 + i * 100,
            )
            for i in range(5)
        ]
        with patch(
            "rag_facile.tracing.get_tracer", return_value=_mock_tracer(traces=traces)
        ):
            result = runner.invoke(main_app, ["traces", "stats"])
        assert result.exit_code == 0
        assert "5" in result.output  # total count

    def test_stats_shows_feedback_when_present(self):
        """stats shows feedback distribution when traces have scores."""
        traces = [
            _make_trace(
                trace_id=f"ccccdddd-000{i}-0000-0000-000000000000",
                feedback_score=5,
            )
            for i in range(3)
        ]
        with patch(
            "rag_facile.tracing.get_tracer", return_value=_mock_tracer(traces=traces)
        ):
            result = runner.invoke(main_app, ["traces", "stats"])
        assert result.exit_code == 0
        assert "Feedback" in result.output


# ── traces export ─────────────────────────────────────────────────────────────


class TestTracesExportCommand:
    def test_export_empty_prints_nothing_to_stdout(self):
        """export with no traces exits cleanly with no JSONL lines."""
        with patch("rag_facile.tracing.get_tracer", return_value=_mock_tracer()):
            result = runner.invoke(main_app, ["traces", "export"])
        assert result.exit_code == 0
        # No JSON objects in stdout
        json_lines = [
            line for line in result.output.splitlines() if line.strip().startswith("{")
        ]
        assert json_lines == []

    def test_export_stdout_produces_valid_jsonl(self):
        """export to stdout produces one valid JSON object per trace."""
        traces = [
            _make_trace(trace_id=f"eeeeffff-000{i}-0000-0000-000000000000")
            for i in range(3)
        ]
        with patch(
            "rag_facile.tracing.get_tracer", return_value=_mock_tracer(traces=traces)
        ):
            result = runner.invoke(main_app, ["traces", "export"])
        assert result.exit_code == 0
        # Filter to only JSON lines (banner/misc output is ignored)
        json_lines = [
            line for line in result.output.splitlines() if line.strip().startswith("{")
        ]
        assert len(json_lines) == 3
        for line in json_lines:
            obj = json.loads(line)
            assert "id" in obj
            assert "query" in obj
            assert obj["query"] == "What is RAG?"

    def test_export_to_file(self, tmp_path):
        """export --output writes JSONL to the specified file."""
        traces = [_make_trace()]
        out_file = tmp_path / "traces.jsonl"
        with patch(
            "rag_facile.tracing.get_tracer", return_value=_mock_tracer(traces=traces)
        ):
            result = runner.invoke(
                main_app, ["traces", "export", "--output", str(out_file)]
            )
        assert result.exit_code == 0
        assert out_file.exists()
        lines = out_file.read_text().strip().splitlines()
        assert len(lines) == 1
        obj = json.loads(lines[0])
        assert obj["id"] == "a1b2c3d4-0000-0000-0000-000000000000"


# ── traces prune ──────────────────────────────────────────────────────────────


class TestTracesPruneCommand:
    def test_prune_with_yes_flag_deletes_and_reports(self):
        """prune --yes deletes traces and shows count."""
        mock = _mock_tracer(delete_count=42)
        with patch("rag_facile.tracing.get_tracer", return_value=mock):
            result = runner.invoke(main_app, ["traces", "prune", "--yes"])
        assert result.exit_code == 0
        mock.delete_traces.assert_called_once_with(older_than_days=30)
        assert "42" in result.output

    def test_prune_custom_days(self):
        """--days is forwarded to delete_traces."""
        mock = _mock_tracer(delete_count=7)
        with patch("rag_facile.tracing.get_tracer", return_value=mock):
            result = runner.invoke(
                main_app, ["traces", "prune", "--days", "7", "--yes"]
            )
        assert result.exit_code == 0
        mock.delete_traces.assert_called_once_with(older_than_days=7)

    def test_prune_zero_deleted_shows_friendly_message(self):
        """prune with nothing to delete shows 'no traces' message."""
        mock = _mock_tracer(delete_count=0)
        with patch("rag_facile.tracing.get_tracer", return_value=mock):
            result = runner.invoke(main_app, ["traces", "prune", "--yes"])
        assert result.exit_code == 0
        assert "No traces" in result.output or "0" in result.output

    def test_prune_aborted_does_not_call_delete(self):
        """Answering 'n' to confirmation skips delete."""
        mock = _mock_tracer(delete_count=10)
        with patch("rag_facile.tracing.get_tracer", return_value=mock):
            result = runner.invoke(main_app, ["traces", "prune"], input="n\n")
        assert result.exit_code == 0
        mock.delete_traces.assert_not_called()

    def test_prune_confirmed_calls_delete(self):
        """Answering 'y' to confirmation proceeds with delete."""
        mock = _mock_tracer(delete_count=5)
        with patch("rag_facile.tracing.get_tracer", return_value=mock):
            result = runner.invoke(main_app, ["traces", "prune"], input="y\n")
        assert result.exit_code == 0
        mock.delete_traces.assert_called_once_with(older_than_days=30)
