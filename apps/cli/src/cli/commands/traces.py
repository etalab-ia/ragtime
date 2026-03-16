"""Inspect and manage RAG pipeline traces."""

from __future__ import annotations

import dataclasses
import json
import sys
from datetime import datetime
from typing import Annotated, Optional

import statistics

import typer
from rich.console import Console
from rich.panel import Panel
from rich.table import Table


console = Console()
err_console = Console(stderr=True)

# ── Helpers ───────────────────────────────────────────────────────────────────

_NO_TRACER_HINT = (
    "[dim]💡 Tracing stores every RAG query for inspection and debugging.\n"
    "   Enable it in ragfacile.toml:\n"
    "   \\[tracing]\n"
    "   enabled = true\n"
    '   provider = "sqlite"   # or "postgres"[/dim]'
)


def _get_tracer():  # type: ignore[return]
    """Load the configured tracing provider, or exit with a helpful message."""
    try:
        from rag_facile.tracing import get_tracer

        return get_tracer()
    except Exception as e:
        console.print(f"[red]✗ Could not load tracing provider: {e}[/red]")
        raise typer.Exit(1)


def _short_id(trace_id: str, length: int = 8) -> str:
    """Return the first N chars of a UUID for compact display."""
    return trace_id[:length]


def _fmt_latency(latency_ms: int | None) -> str:
    if latency_ms is None:
        return "[dim]—[/dim]"
    if latency_ms < 1000:
        return f"{latency_ms} ms"
    return f"{latency_ms / 1000:.1f} s"


def _fmt_score(score: int | None) -> str:
    if score is None:
        return "[dim]—[/dim]"
    stars = "★" * score + "☆" * max(0, 5 - score)
    return stars


def _fmt_dt(dt: datetime | None) -> str:
    if dt is None:
        return "[dim]—[/dim]"
    return dt.strftime("%Y-%m-%d %H:%M")


def _trace_to_dict(trace: object) -> dict:
    """Serialize a TraceRecord to a JSON-safe dict."""
    data = dataclasses.asdict(trace)  # type: ignore[arg-type]
    # Convert datetime objects to ISO strings
    for key, value in data.items():
        if isinstance(value, datetime):
            data[key] = value.isoformat()
    return data


# ── Subcommands ───────────────────────────────────────────────────────────────


def list_traces(
    limit: Annotated[
        int,
        typer.Option("--limit", "-n", help="Maximum number of traces to show"),
    ] = 20,
    session: Annotated[
        Optional[str],
        typer.Option("--session", "-s", help="Filter by session ID"),
    ] = None,
    user: Annotated[
        Optional[str],
        typer.Option("--user", "-u", help="Filter by user ID"),
    ] = None,
) -> None:
    """List recent RAG pipeline traces.

    Shows the most recent traces in a compact table. Use
    ``rag-facile traces show <ID>`` to see full details.

    Examples:
        # Show the 20 most recent traces
        rag-facile traces list

        # Show more traces
        rag-facile traces list --limit 100

        # Filter by session
        rag-facile traces list --session abc-123
    """
    tracer = _get_tracer()
    traces = tracer.list_traces(session_id=session, user_id=user, limit=limit)

    if not traces:
        console.print("[yellow]No traces found.[/yellow]")
        console.print()
        console.print(_NO_TRACER_HINT)
        return

    table = Table(title=f"🔍 Recent Traces (showing {len(traces)})", expand=True)
    table.add_column("ID", style="cyan", no_wrap=True, min_width=10)
    table.add_column("Query", ratio=3, no_wrap=True)
    table.add_column("Model", min_width=12, no_wrap=True)
    table.add_column("Latency", justify="right", min_width=8, no_wrap=True)
    table.add_column("Score", justify="center", min_width=7, no_wrap=True)
    table.add_column("Created", min_width=16, no_wrap=True)

    for t in traces:
        query_preview = (t.query[:60] + "…") if len(t.query) > 60 else t.query
        table.add_row(
            _short_id(t.id),
            query_preview or "[dim](empty)[/dim]",
            t.model or "[dim]—[/dim]",
            _fmt_latency(t.latency_ms),
            _fmt_score(t.feedback_score),
            _fmt_dt(t.created_at),
        )

    console.print()
    console.print(table)
    console.print()
    console.print(
        "[dim]💡 Use the first 8 chars of the ID with: "
        "rag-facile traces show <ID>[/dim]"
    )


def show_trace(
    trace_id: Annotated[str, typer.Argument(help="Trace ID (or prefix)")],
) -> None:
    """Show full detail of a RAG pipeline trace.

    Displays all fields: identity, pipeline data (query, retrieved chunks,
    context), LLM data (response, model, latency), and user feedback.

    Examples:
        rag-facile traces show a1b2c3d4-...
        rag-facile traces show a1b2c3d4
    """
    tracer = _get_tracer()

    # Try exact match first; if not found and looks like a prefix, search list
    trace = tracer.get_trace(trace_id)
    if trace is None and len(trace_id) < 36:
        # Prefix search via list_traces (scan up to 1000 recent traces)
        candidates = tracer.list_traces(limit=1000)
        matches = [t for t in candidates if t.id.startswith(trace_id)]
        if len(matches) == 1:
            trace = matches[0]
        elif len(matches) > 1:
            console.print(
                f"[yellow]Ambiguous prefix '{trace_id}' matches {len(matches)} traces. "
                "Use a longer prefix or the full ID.[/yellow]"
            )
            for m in matches[:5]:
                console.print(f"  [cyan]{m.id}[/cyan]  {m.query[:60]}")
            raise typer.Exit(1)

    if trace is None:
        console.print(f"[red]✗ Trace not found: {trace_id!r}[/red]")
        raise typer.Exit(1)

    # ── Identity panel ──
    identity_lines = [
        f"[bold]ID:[/bold]         {trace.id}",
        f"[bold]Created:[/bold]    {_fmt_dt(trace.created_at)}",
        f"[bold]Response at:[/bold]{_fmt_dt(trace.response_at)}",
        f"[bold]Session:[/bold]    {trace.session_id or '—'}",
        f"[bold]User:[/bold]       {trace.user_id or '—'}",
    ]
    console.print(
        Panel("\n".join(identity_lines), title="Identity", border_style="cyan")
    )

    # ── Query / pipeline panel ──
    pipeline_lines = [
        f"[bold]Query:[/bold]\n  {trace.query or '(empty)'}",
    ]
    if trace.expanded_queries:
        expanded = "\n  ".join(f"• {q}" for q in trace.expanded_queries)
        pipeline_lines.append(f"\n[bold]Expanded queries:[/bold]\n  {expanded}")
    pipeline_lines.append(
        f"\n[bold]Retrieved chunks:[/bold] {len(trace.retrieved_chunks)}"
        f"   [bold]Reranked:[/bold] {len(trace.reranked_chunks)}"
    )
    if trace.collection_ids:
        pipeline_lines.append(
            f"[bold]Collections:[/bold] {', '.join(str(c) for c in trace.collection_ids)}"
        )
    if trace.formatted_context:
        ctx_preview = (
            (trace.formatted_context[:300] + "…")
            if len(trace.formatted_context) > 300
            else trace.formatted_context
        )
        pipeline_lines.append(
            f"\n[bold]Context (preview):[/bold]\n[dim]{ctx_preview}[/dim]"
        )
    console.print(
        Panel("\n".join(pipeline_lines), title="RAG Pipeline", border_style="blue")
    )

    # ── LLM panel ──
    llm_lines = [
        f"[bold]Model:[/bold]       {trace.model or '—'}",
        f"[bold]Temperature:[/bold] {trace.temperature}",
        f"[bold]Latency:[/bold]     {_fmt_latency(trace.latency_ms)}",
    ]
    if trace.response:
        resp_preview = (
            (trace.response[:400] + "…")
            if len(trace.response) > 400
            else trace.response
        )
        llm_lines.append(f"\n[bold]Response:[/bold]\n{resp_preview}")
    console.print(
        Panel("\n".join(llm_lines), title="LLM Generation", border_style="green")
    )

    # ── Feedback panel (only if any feedback exists) ──
    if (
        trace.feedback_score is not None
        or trace.feedback_comment
        or trace.feedback_tags
    ):
        fb_lines = [
            f"[bold]Score:[/bold]   {_fmt_score(trace.feedback_score)}  ({trace.feedback_score})",
        ]
        if trace.feedback_tags:
            fb_lines.append(f"[bold]Tags:[/bold]    {', '.join(trace.feedback_tags)}")
        if trace.feedback_comment:
            fb_lines.append(f"[bold]Comment:[/bold] {trace.feedback_comment}")
        console.print(
            Panel("\n".join(fb_lines), title="User Feedback", border_style="yellow")
        )


def stats_traces() -> None:
    """Show aggregate statistics for RAG pipeline traces.

    Computes counts, latency distribution, and feedback breakdown
    from the most recent 10,000 traces.

    Examples:
        rag-facile traces stats
    """
    tracer = _get_tracer()
    traces = tracer.list_traces(limit=10_000)

    total = len(traces)
    if total == 0:
        console.print("[yellow]No traces found.[/yellow]")
        console.print()
        console.print(_NO_TRACER_HINT)
        return

    # Latency stats (only traces with a response)
    latencies = [t.latency_ms for t in traces if t.latency_ms is not None]
    with_response = sum(1 for t in traces if t.response is not None)
    with_feedback = sum(1 for t in traces if t.feedback_score is not None)

    # Feedback score distribution
    score_dist: dict[int, int] = {}
    for t in traces:
        if t.feedback_score is not None:
            score_dist[t.feedback_score] = score_dist.get(t.feedback_score, 0) + 1

    # Date range
    dates = [t.created_at for t in traces if t.created_at is not None]
    oldest = min(dates) if dates else None
    newest = max(dates) if dates else None

    # ── Overview panel ──
    overview_lines = [
        f"[bold]Total traces:[/bold]       {total:,}",
        f"[bold]With response:[/bold]      {with_response:,}  ({with_response / total * 100:.0f}%)",
        f"[bold]With feedback:[/bold]      {with_feedback:,}  ({with_feedback / total * 100:.0f}%)",
        f"[bold]Date range:[/bold]         {_fmt_dt(oldest)} → {_fmt_dt(newest)}",
    ]
    console.print(
        Panel(
            "\n".join(overview_lines), title="📊 Trace Statistics", border_style="cyan"
        )
    )

    # ── Latency panel ──
    if latencies:
        avg_ms = int(statistics.mean(latencies))
        sorted_lat = sorted(latencies)
        p50 = int(statistics.median(latencies))
        p95 = sorted_lat[int(len(sorted_lat) * 0.95)]
        latency_lines = [
            f"[bold]Count:[/bold]  {len(latencies):,}",
            f"[bold]Avg:[/bold]    {_fmt_latency(avg_ms)}",
            f"[bold]Min:[/bold]    {_fmt_latency(sorted_lat[0])}",
            f"[bold]p50:[/bold]    {_fmt_latency(p50)}",
            f"[bold]p95:[/bold]    {_fmt_latency(p95)}",
            f"[bold]Max:[/bold]    {_fmt_latency(sorted_lat[-1])}",
        ]
        console.print(
            Panel("\n".join(latency_lines), title="⏱ Latency", border_style="blue")
        )

    # ── Feedback distribution ──
    if score_dist:
        fb_table = Table(title="⭐ Feedback Distribution", expand=False)
        fb_table.add_column("Score", style="bold", min_width=8)
        fb_table.add_column("Stars", min_width=10)
        fb_table.add_column("Count", justify="right", min_width=6)
        fb_table.add_column("Share", justify="right", min_width=8)

        for score in sorted(score_dist.keys(), reverse=True):
            count = score_dist[score]
            share = count / with_feedback * 100
            fb_table.add_row(
                str(score),
                "★" * score + "☆" * max(0, 5 - score),
                str(count),
                f"{share:.0f}%",
            )
        console.print()
        console.print(fb_table)


def export_traces(
    output: Annotated[
        Optional[str],
        typer.Option("--output", "-o", help="Output file path (default: stdout)"),
    ] = None,
    limit: Annotated[
        int,
        typer.Option("--limit", "-n", help="Maximum number of traces to export"),
    ] = 1000,
    session: Annotated[
        Optional[str],
        typer.Option("--session", "-s", help="Filter by session ID"),
    ] = None,
) -> None:
    """Export traces as JSONL for offline analysis or evaluation.

    Each line is a JSON object representing one trace. Compatible with
    RAGAS and other evaluation frameworks.

    Examples:
        # Export to file
        rag-facile traces export --output traces.jsonl

        # Pipe to another tool
        rag-facile traces export | head -5

        # Export recent session
        rag-facile traces export --session abc-123 --output session.jsonl
    """
    tracer = _get_tracer()
    traces = tracer.list_traces(session_id=session, limit=limit)

    if not traces:
        err_console.print("[yellow]No traces to export.[/yellow]")
        return

    def _write_jsonl(f) -> None:  # type: ignore[type-arg]
        for t in traces:
            f.write(json.dumps(_trace_to_dict(t), ensure_ascii=False) + "\n")

    if output:
        from pathlib import Path

        out_path = Path(output)
        out_path.parent.mkdir(parents=True, exist_ok=True)
        with out_path.open("w", encoding="utf-8") as f:
            _write_jsonl(f)
        err_console.print(
            f"[green]✓ Exported {len(traces):,} traces → {out_path}[/green]"
        )
    else:
        _write_jsonl(sys.stdout)


def prune_traces(
    days: Annotated[
        int,
        typer.Option("--days", "-d", help="Delete traces older than this many days"),
    ] = 30,
    yes: Annotated[
        bool,
        typer.Option("--yes", "-y", help="Skip confirmation prompt"),
    ] = False,
) -> None:
    """Delete traces older than N days to reclaim storage.

    Examples:
        # Delete traces older than 30 days (default), with confirmation
        rag-facile traces prune

        # Delete traces older than 7 days, skip confirmation
        rag-facile traces prune --days 7 --yes
    """
    tracer = _get_tracer()

    if not yes:
        confirm = typer.confirm(
            f"Delete all traces older than {days} days?", default=False
        )
        if not confirm:
            console.print("[dim]Aborted.[/dim]")
            raise typer.Exit(0)

    deleted = tracer.delete_traces(older_than_days=days)

    if deleted == 0:
        console.print(f"[dim]No traces older than {days} days found.[/dim]")
    else:
        console.print(
            f"[green]✓ Deleted {deleted:,} trace{'s' if deleted != 1 else ''} "
            f"older than {days} days.[/green]"
        )
