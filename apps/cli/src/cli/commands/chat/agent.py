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
from rich.markdown import Markdown
from rich.panel import Panel
from smolagents import OpenAIServerModel, ToolCallingAgent
from smolagents.monitoring import LogLevel
from smolagents.utils import AgentError, AgentMaxStepsError

from cli.commands.chat._console import console

from cli.commands.chat.init import needs_init, read_language, run_init_wizard
from cli.commands.chat.skills import (
    auto_detect_skill,
    discover_skills,
    format_skills_list,
    install_skill,
    load_skill,
)
from cli.commands.chat.memory import (
    append_turn,
    git_commit_session,
    increment_session_count,
    load_context,
    update_memory,
)
from cli.commands.chat.tools import (
    get_agents_md,
    get_docs,
    get_ragfacile_config,
    get_recent_git_activity,
    set_workspace_root,
    update_config,
)


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
        "skill_loaded": "📚 Compétence '{name}' activée.",
        "skill_cleared": "📚 Compétence désactivée.",
        "skill_not_found": "Compétence '{name}' introuvable. Tapez /skills pour voir la liste.",
        "skill_installing": "Installation de '{pkg}'...",
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
        "skill_loaded": "📚 Skill '{name}' activated.",
        "skill_cleared": "📚 Skill deactivated.",
        "skill_not_found": "Skill '{name}' not found. Type /skills to see the list.",
        "skill_installing": "Installing '{pkg}'...",
    },
}

# Albert API allows 10 req/min; smolagents may use several calls per turn.
# Wait 15s on 429 before one automatic retry.
_RATE_LIMIT_WAIT = 15


_TOOL_ICONS: dict[str, str] = {
    "get_ragfacile_config": "⚙️",
    "get_agents_md": "📋",
    "get_recent_git_activity": "📜",
    "get_docs": "📖",
    "update_config": "✏️",
}


def _with_notification(tool):
    """Wrap a smolagents tool's forward() to print a dim notification before calling.

    Shown unconditionally (not gated behind --debug) so users always see
    what the agent is doing, without needing the full smolagents trace.
    Guards against double-wrapping so repeated start_chat() calls are safe.
    """
    if getattr(tool, "_notification_wrapped", False):
        return tool

    _original = tool.forward
    icon = _TOOL_ICONS.get(tool.name, "🔧")
    name = tool.name

    def _notifying(*args: object, **kwargs: object) -> object:
        console.print(f"[dim]{icon} {name}[/dim]")
        return _original(*args, **kwargs)

    tool.forward = _notifying
    tool._notification_wrapped = True
    return tool


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
    # Use Albert model aliases (resolved server-side) rather than raw model IDs.
    # openweight-large = the largest available generation model (best quality).
    # Override with OPENAI_MODEL in .env for a different size or provider.
    model_id = os.environ.get("OPENAI_MODEL", "openweight-large")

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


def start_chat(debug: bool = False) -> None:
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

    # Discover skills: built-in + workspace (.agents/skills/)
    available_skills = discover_skills(workspace)
    active_skill: str | None = None  # name of currently loaded skill
    active_skill_content: str | None = None  # SKILL.md content to inject
    skill_injected = False  # True once content has been sent to agent

    # Build model + agent — typer.Exit propagates naturally on missing API key
    model = _build_model()

    tools = [
        _with_notification(t)
        for t in [
            get_ragfacile_config,
            get_agents_md,
            get_recent_git_activity,
            get_docs,
            update_config,
        ]
    ]

    agent = ToolCallingAgent(
        tools=tools,
        model=model,
        instructions=_SYSTEM_PROMPT,
        verbosity_level=LogLevel.INFO if debug else LogLevel.OFF,
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

        # ── /skills slash commands ────────────────────────────────────────────
        _skill_bootstrap = (
            False  # set True when explicit load should run agent immediately
        )
        if user_input == "/skills" or user_input.startswith("/skills "):
            parts = user_input.split(None, 2)  # ["/skills", cmd?, arg?]
            sub = parts[1].lower() if len(parts) > 1 else ""
            arg = parts[2] if len(parts) > 2 else ""

            if sub == "" or sub == "list":
                # Refresh discovery so newly installed skills appear
                available_skills = discover_skills(workspace)
                console.print(format_skills_list(available_skills))

            elif sub == "install":
                if not arg:
                    console.print("[yellow]Usage: /skills install <package>[/yellow]")
                elif workspace is None:
                    console.print(
                        "[yellow]No workspace detected — cannot install skills.[/yellow]"
                    )
                else:
                    with console.status(
                        f"[dim]{ui['skill_installing'].format(pkg=arg)}[/dim]",
                        spinner="dots",
                    ):
                        result = install_skill(arg, workspace)
                    console.print(result)
                    available_skills = discover_skills(workspace)

            elif sub == "clear":
                active_skill = None
                active_skill_content = None
                skill_injected = False
                console.print(f"[dim]{ui['skill_cleared']}[/dim]")

            elif sub in available_skills:
                # /skills <name> — explicit load: activate and bootstrap the flow
                active_skill = sub
                active_skill_content = load_skill(available_skills[sub])
                console.print(f"[dim]{ui['skill_loaded'].format(name=sub)}[/dim]")
                # Inject skill + trigger word so the agent starts its flow immediately
                user_input = (
                    f"[Compétence chargée: {sub}]\n{active_skill_content}\n\n---\n\n"
                    "Commence."
                )
                skill_injected = True
                _skill_bootstrap = (
                    True  # skip the outer continue — fall through to agent
                )

            else:
                console.print(f"[dim]{ui['skill_not_found'].format(name=sub)}[/dim]")

            if not _skill_bootstrap:
                continue

        # ── Auto-detect skill from message (only if none active) ─────────────
        if active_skill is None:
            detected = auto_detect_skill(user_input, available_skills)
            if detected:
                active_skill = detected
                active_skill_content = load_skill(available_skills[detected])
                skill_injected = False
                console.print(f"[dim]{ui['skill_loaded'].format(name=detected)}[/dim]")

        # Build effective_input — layer memory (first turn) + skill (on load) + message
        effective_input = user_input

        # Inject memory on first turn of the session
        if memory_context and not session_turns:
            effective_input = (
                f"[Mémoire des sessions précédentes]\n{memory_context}\n\n---\n\n"
                f"{effective_input}"
            )

        # Inject skill content the first time a skill becomes active
        if active_skill_content and not skill_injected:
            effective_input = (
                f"[Compétence chargée: {active_skill}]\n{active_skill_content}\n\n---\n\n"
                f"{effective_input}"
            )
            skill_injected = True

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
