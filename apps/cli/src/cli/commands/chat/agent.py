"""smolagents harness for the rag-facile chat experience.

Entry point: start_chat() — called when the user runs `rag-facile` with no arguments,
or explicitly via `rag-facile chat`.
"""

import os
from pathlib import Path

import openai
import typer
from dotenv import load_dotenv
from rich.console import Console
from rich.markdown import Markdown
from rich.panel import Panel
from smolagents import OpenAIServerModel, ToolCallingAgent
from smolagents.monitoring import LogLevel
from smolagents.utils import AgentError, AgentMaxStepsError

from cli.commands.chat.tools import get_ragfacile_config, set_workspace_root


console = Console()

_SYSTEM_PROMPT = """\
You are the rag-facile AI assistant — a friendly expert who helps developers \
build RAG (Retrieval-Augmented Generation) applications using the rag-facile toolkit.

Your users are lambda developers: they know Python but are new to RAG and GenAI. \
Always explain concepts in plain, accessible language. Avoid jargon without explanation.

You can:
- Answer questions about RAG concepts (chunking, embeddings, retrieval, reranking, etc.)
- Explain what configuration parameters do and how to tune them
- Read the current ragfacile.toml to give context-aware advice
- Guide users through the rag-facile workflow step by step

Always be encouraging and educational. When you suggest a change, explain the tradeoff \
in terms of speed vs. quality vs. cost so the user can make an informed decision.
"""


def _detect_workspace() -> Path | None:
    """Walk up from cwd looking for a ragfacile.toml to identify the workspace root."""
    cwd = Path.cwd()
    for path in [cwd, *cwd.parents]:
        if (path / "ragfacile.toml").exists():
            return path
    return None


def _build_model() -> OpenAIServerModel:
    """Construct the OpenAIServerModel pointed at Albert API."""
    api_key = os.environ.get("OPENAI_API_KEY") or os.environ.get("ALBERT_API_KEY", "")
    api_base = os.environ.get("OPENAI_BASE_URL", "https://albert.api.etalab.gouv.fr/v1")
    model_id = os.environ.get("OPENAI_MODEL", "meta-llama/Llama-3.1-70B-Instruct")

    if not api_key:
        console.print(
            "[red]✗ No API key found.[/red]\n"
            "[dim]Set OPENAI_API_KEY or ALBERT_API_KEY in your .env file.[/dim]"
        )
        raise typer.Exit(code=1)

    return OpenAIServerModel(
        model_id=model_id,
        api_base=api_base,
        api_key=api_key,
    )


def start_chat() -> None:
    """Launch the interactive RAG assistant chat loop."""
    # Detect workspace — walk up from cwd for ragfacile.toml
    workspace = _detect_workspace()
    no_workspace_hint = ""
    if workspace:
        load_dotenv(workspace / ".env")  # load API key + config from project .env
        set_workspace_root(workspace)
    else:
        no_workspace_hint = (
            "\n[dim]💡 No ragfacile.toml found — run [bold]rag-facile setup[/bold] "
            "to create a workspace.[/dim]"
        )

    # Build model + agent — typer.Exit propagates naturally on missing API key
    model = _build_model()

    agent = ToolCallingAgent(
        tools=[get_ragfacile_config],
        model=model,
        instructions=_SYSTEM_PROMPT,
        verbosity_level=LogLevel.OFF,  # -1: suppress all smolagents output incl. errors
        max_steps=5,
    )

    # Welcome
    workspace_line = (
        f"\n[dim]Workspace: {workspace}[/dim]" if workspace else no_workspace_hint
    )
    console.print(
        Panel(
            "[bold]Bonjour! I'm your RAG assistant.[/bold]\n"
            "[dim]Ask me anything about RAG, your pipeline config, or how to improve your results.\n"
            "Type [bold]q[/bold] or press Ctrl+C to quit.[/dim]" + workspace_line,
            border_style="magenta",
            padding=(0, 1),
        )
    )
    console.print()

    # Chat loop
    while True:
        try:
            user_input = console.input("[bold cyan]You[/bold cyan]: ").strip()
        except (KeyboardInterrupt, EOFError):
            console.print("\n[dim]À bientôt![/dim]")
            break

        if not user_input:
            continue

        if user_input.lower() in ("q", "quit", "exit", "bye", "au revoir"):
            console.print("[dim]À bientôt![/dim]")
            break

        with console.status("[dim]Thinking...[/dim]", spinner="dots"):
            try:
                response = agent.run(user_input, reset=False)
            except KeyboardInterrupt:
                console.print("\n[yellow]Interrupted.[/yellow]")
                continue
            except openai.APIError as exc:
                console.print(f"[red]API error: {exc}[/red]")
                console.print(
                    "[dim]Check your OPENAI_API_KEY and OPENAI_BASE_URL.[/dim]"
                )
                continue
            except AgentMaxStepsError:
                console.print(
                    "[yellow]I needed too many steps to answer that. "
                    "Could you rephrase or break it into smaller questions?[/yellow]"
                )
                continue
            except AgentError as exc:
                console.print(f"[red]Agent error: {exc}[/red]")
                continue

        console.print("[bold green]Assistant[/bold green]:")
        console.print(Markdown(str(response)))
        console.print()
