"""smolagents harness for the rag-facile chat experience.

Entry point: start_chat() — called when the user runs `rag-facile` with no arguments,
or explicitly via `rag-facile chat`.
"""

import os
import time
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

from cli.commands.chat.init import needs_init, read_language, run_init_wizard
from cli.commands.chat.memory import (
    append_turn,
    git_commit_session,
    increment_session_count,
    load_context,
    update_memory,
)
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

# ── Per-language UI strings ───────────────────────────────────────────────────

_UI: dict[str, dict[str, str]] = {
    "fr": {
        "greeting": "Bonjour\u00a0! Je suis votre assistant RAG.",
        "subtitle": (
            "Posez-moi vos questions sur RAG, votre configuration "
            "ou comment améliorer vos résultats.\n"
            "Tapez [bold]q[/bold] ou Ctrl+C pour quitter."
        ),
        "no_workspace_hint": (
            "\n[dim]💡 Aucun ragfacile.toml trouvé — lancez "
            "[bold]rag-facile setup[/bold] pour créer un espace de travail.[/dim]"
        ),
        "thinking": "Réflexion en cours...",
        "you": "Vous",
        "goodbye": "À bientôt\u00a0!",
        "interrupted": "Interrompu.",
        "api_error_hint": "Vérifiez vos variables OPENAI_API_KEY et OPENAI_BASE_URL.",
        "too_many_steps": (
            "J'ai eu besoin de trop d'étapes pour répondre. "
            "Pouvez-vous reformuler ou poser une question plus simple\u00a0?"
        ),
        "rate_limited": "Limite de requêtes atteinte — nouvelle tentative dans {n}s (Ctrl+C pour annuler)\u00a0...",
    },
    "en": {
        "greeting": "Bonjour! I'm your RAG assistant.",
        "subtitle": (
            "Ask me anything about RAG, your pipeline config, or how to improve your results.\n"
            "Type [bold]q[/bold] or press Ctrl+C to quit."
        ),
        "no_workspace_hint": (
            "\n[dim]💡 No ragfacile.toml found — run "
            "[bold]rag-facile setup[/bold] to create a workspace.[/dim]"
        ),
        "thinking": "Thinking...",
        "you": "You",
        "goodbye": "À bientôt!",
        "interrupted": "Interrupted.",
        "api_error_hint": "Check your OPENAI_API_KEY and OPENAI_BASE_URL.",
        "too_many_steps": (
            "I needed too many steps to answer that. "
            "Could you rephrase or break it into smaller questions?"
        ),
        "rate_limited": "Rate limit reached — retrying in {n}s (Ctrl+C to cancel)...",
    },
}

# Albert API allows 10 req/min; smolagents may use several calls per turn.
# Wait 15s on 429 before one automatic retry.
_RATE_LIMIT_WAIT = 15


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
    language = "fr"  # default — overridden once we have a workspace
    if workspace:
        load_dotenv(workspace / ".env")  # load API key + config from project .env
        set_workspace_root(workspace)
        # First-run: initialise .rag-facile/ and capture chosen language
        if needs_init(workspace):
            language = run_init_wizard(workspace)
        else:
            language = read_language(workspace)

    ui = _UI.get(language, _UI["fr"])

    # Load persistent memory — injected into the first user turn (not system prompt)
    # so the model pays full attention to it rather than losing it at the end of
    # smolagents' long built-in system prompt.
    memory_context = load_context(workspace) if workspace else ""

    # Increment session count (best-effort — workspace may be None)
    if workspace:
        increment_session_count(workspace)

    # Build model + agent — typer.Exit propagates naturally on missing API key
    model = _build_model()

    agent = ToolCallingAgent(
        tools=[get_ragfacile_config],
        model=model,
        instructions=_SYSTEM_PROMPT,
        verbosity_level=LogLevel.OFF,  # -1: suppress all smolagents output incl. errors
        max_steps=5,
    )

    session_turns: list[tuple[str, str]] = []  # accumulated for post-session update

    # Welcome
    workspace_line = (
        f"\n[dim]Workspace: {workspace}[/dim]" if workspace else ui["no_workspace_hint"]
    )
    console.print(
        Panel(
            f"[bold]{ui['greeting']}[/bold]\n"
            f"[dim]{ui['subtitle']}[/dim]" + workspace_line,
            border_style="magenta",
            padding=(0, 1),
        )
    )
    console.print()

    # Chat loop
    while True:
        try:
            user_input = console.input(f"[bold cyan]{ui['you']}[/bold cyan]: ").strip()
        except (KeyboardInterrupt, EOFError):
            console.print(f"\n[dim]{ui['goodbye']}[/dim]")
            break

        if not user_input:
            continue

        if user_input.lower() in ("q", "quit", "exit", "bye", "au revoir", "quitter"):
            console.print(f"[dim]{ui['goodbye']}[/dim]")
            break

        # On the first turn: prepend memory context so the model sees it
        # right before the question (much better attention than end-of-system-prompt)
        if memory_context and not session_turns:
            effective_input = (
                f"[Mémoire des sessions précédentes]\n{memory_context}\n\n---\n\n"
                f"{user_input}"
            )
        else:
            effective_input = user_input

        # Retry loop — keeps retrying on 429 until success or Ctrl+C
        response = None
        while True:
            _rate_limited = False
            with console.status(f"[dim]{ui['thinking']}[/dim]", spinner="dots"):
                try:
                    response = agent.run(effective_input, reset=False)
                except KeyboardInterrupt:
                    console.print(f"\n[yellow]{ui['interrupted']}[/yellow]")
                except openai.APIError as exc:
                    console.print(f"[red]API error: {exc}[/red]")
                    console.print(f"[dim]{ui['api_error_hint']}[/dim]")
                except AgentMaxStepsError:
                    console.print(f"[yellow]{ui['too_many_steps']}[/yellow]")
                except AgentError as exc:
                    if "429" in str(exc):
                        _rate_limited = True
                    else:
                        console.print(f"[red]Agent error: {exc}[/red]")

            if not _rate_limited:
                break  # success or non-retryable error — exit retry loop

            # Rate limited: show message, sleep (interruptible by Ctrl+C), then retry
            console.print(
                f"[yellow]{ui['rate_limited'].format(n=_RATE_LIMIT_WAIT)}[/yellow]"
            )
            try:
                time.sleep(_RATE_LIMIT_WAIT)
            except KeyboardInterrupt:
                console.print(f"\n[yellow]{ui['interrupted']}[/yellow]")
                break

        if response is None:
            continue

        console.print("[bold green]Assistant[/bold green]:")
        console.print(Markdown(str(response)))
        console.print()

        # Log turn to today's conversation file
        if workspace:
            append_turn(workspace, "user", user_input)
            append_turn(workspace, "assistant", str(response))
            session_turns.append((user_input, str(response)))

    # ── Post-session: update memory + git commit ──────────────────────────────
    if workspace and session_turns:
        session_log = "\n\n".join(
            f"Vous: {u}\nAssistant: {a}" for u, a in session_turns
        )
        with console.status("[dim]Mise à jour de la mémoire...[/dim]", spinner="dots"):
            update_memory(workspace, session_log)
            git_commit_session(workspace)
