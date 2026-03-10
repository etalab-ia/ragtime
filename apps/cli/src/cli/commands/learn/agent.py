"""smolagents harness for the rag-facile learn experience.

Entry point: start_chat() — called when the user runs `rag-facile learn`.
"""

import os
import time
from collections.abc import Callable
from datetime import datetime
from pathlib import Path

import openai
import typer
from dotenv import load_dotenv
from rich.markdown import Markdown
from rich.panel import Panel
from smolagents import OpenAIServerModel, ToolCallingAgent
from smolagents.memory import ActionStep, TaskStep
from smolagents.monitoring import LogLevel
from smolagents.utils import AgentError, AgentMaxStepsError

from cli.commands.learn._console import console
from cli.commands.learn.init import (
    needs_init,
    read_experience,
    read_language,
    run_init_wizard,
)
from cli.commands.learn.skills import (
    discover_skills,
    format_skills_list,
    install_skill,
    load_skill,
)
from cli.commands.learn.tools import (
    _set_memory_workspace,
    activate_skill,
    get_agents_md,
    get_docs,
    get_recent_git_activity,
    memory_edit,
    memory_read,
    memory_search,
    memory_write,
    run_rag_facile,
    set_available_skills,
    set_workspace_root,
)


_SYSTEM_PROMPT = """\
You are the rag-facile AI assistant — a friendly expert who helps developers \
build RAG (Retrieval-Augmented Generation) applications using the rag-facile toolkit.

Your users are lambda developers: they know Python but are new to RAG and GenAI. \
Always explain concepts in plain, accessible language. Avoid jargon without explanation.

You can:
- Answer questions about RAG concepts (chunking, embeddings, retrieval, reranking, etc.)
- Explain what configuration parameters do and how to tune them
- Run CLI commands on behalf of the user (config show, config set, collections list, etc.)
- Guide users through the rag-facile workflow step by step

Always be encouraging and educational. When you suggest a change, explain the tradeoff \
in terms of speed vs. quality vs. cost so the user can make an informed decision.

## Architecture rag-facile — faits essentiels

Avant de répondre à toute question sur rag-facile, rappelle-toi ces faits \
fondamentaux qui le distinguent d'un RAG générique :

- **Pas de base vectorielle externe** : rag-facile utilise Albert API pour \
  l'embedding ET le stockage vectoriel. Pas de Qdrant, Chroma, FAISS, Pinecone, \
  Milvus, Weaviate — ces outils ne s'appliquent PAS à rag-facile.
- **Collections Albert** : une collection est un espace de stockage géré par \
  le service Albert. Elle est créée automatiquement par rag-facile lors de \
  l'upload d'un document. L'utilisateur n'a pas à écrire de code pour créer \
  une collection.
- **Collections publiques** : des collections pré-indexées (service-public.fr, \
  legifrance, data.gouv.fr…) sont disponibles et configurables dans \
  ragfacile.toml sous la clé ``[storage] collections = [...]``.
- **Voir les collections disponibles** : appeler ``run_rag_facile("collections list")`` \
  — ne jamais décrire des collections fictives.
- **Presets** : 5 configurations prêtes à l'emploi (balanced, fast, accurate, \
  legal, hr) définissent les paramètres du pipeline dans ragfacile.toml.
- **Pipeline géré** : l'utilisateur n'importe pas de bibliothèques RAG (LangChain, \
  LlamaIndex…). rag-facile fournit le pipeline complet via ``rag-facile setup``.

## Skill activation

Before responding, decide if ONE skill clearly applies. Call activate_skill(name) as \
your FIRST action ONLY WHEN you are confident it matches — do NOT force a skill if unsure.

- explain-rag      → user asks WHAT something IS or HOW it works, specifically about RAG \
or rag-facile concepts (chunking, embeddings, retrieval, reranking, presets…). \
DO NOT use for general questions or simple factual lookups unrelated to RAG.

- learn-retrieval  → user reports a QUALITY PROBLEM with their results (bad, irrelevant, \
not finding the right documents). \
DO NOT use if the user is requesting a specific parameter change — use tune-pipeline instead.

- tune-pipeline    → user wants to CHANGE or SET a specific config parameter \
(top_k, top_n, chunk_size, preset, model…). \
DO NOT use for questions about what a parameter means — use explain-rag for that. \
If the user BOTH reports a problem AND asks to change a value, prefer tune-pipeline.

- explore-codebase → user asks WHERE something is implemented in the rag-facile source code, \
or wants to navigate a specific package or file. \
DO NOT use for conceptual questions about how RAG works — use explain-rag for that.

- rag-cli          → user wants to run a CLI operation OR view current state: list collections, show/inspect config values, change a config parameter, generate a dataset, or any other rag-facile command. Use run_rag_facile() for all of these — including reads.

- skill-creator    → user explicitly wants to CREATE a new custom skill file. \
Requires the user to have stated a skill topic or purpose. \
DO NOT use if the user is merely asking about skills or how they work.

Only activate ONE skill per session. If no skill clearly fits, respond directly in \
natural language — this is always a valid choice.

## Memory — persistent file storage

You have a memory directory (.agent/) that persists across sessions.

IMPORTANT: ALWAYS read your memory directory before doing anything else. \
Use memory_read(".") to see what files exist from previous sessions.

MEMORY PROTOCOL:
1. memory_read(".")          → check your memory directory
2. memory_read("MEMORY.md")  → read your curated facts
3. Work on the user's task
4. memory_write() or memory_edit() → save important facts proactively

SEARCH BEFORE READ: When you need a specific fact but don't know which file it's in, \
use memory_search("query") FIRST. It returns ranked snippets with file:line references \
that you can drill into with memory_read("file:start-end").

ASSUME INTERRUPTION: Your context window might be reset at any moment. \
Record progress to memory so future sessions can pick up where you left off.

Users can type /new to start a fresh session. Your memory will be saved automatically \
before the reset — any facts you wrote to MEMORY.md will be available in the next session.

Keep memory organized: use memory_edit() to update existing facts. \
Use memory_write() to create or overwrite entire files. \
Available memory sections in MEMORY.md: \
User Identity, Preferences, Project State, Key Facts, Routing Table, Recent Context.

## RULE — Always use tools; never answer from memory

When the user asks to SEE or READ current state (config values, collections, version), \
call run_rag_facile() to get live data. NEVER describe config values from memory — \
they may be stale or wrong.

When the user asks to DO something you have a tool for, USE the tool. \
Do NOT explain how to do it manually.

- "montre-moi la config storage" → run_rag_facile("config show"), present actual output
- "active la collection 785" → read config first, then confirm + run_rag_facile("config set ...")
- "mets top_k à 15" → confirm first, then run_rag_facile("config set retrieval.top_k 15")
- "quelle version ?" → run_rag_facile("version")

The agent's value is live data and real actions — not cached knowledge.

## Language

Always respond in the language specified in the ``[Profil utilisateur]`` block \
(the ``Language`` field).  If Language is ``fr``, respond in French — even when \
skills or documentation are written in English.  If Language is ``en``, respond \
in English.  When no profile is present, default to French.

## Response style — adapt to the user profile

The first turn of every session contains a ``[Profil utilisateur]`` block that
includes the user's experience level.  Read it and adjust your responses:

- **Some experience** — Normal explanations; skip "what is RAG / what is an
  embedding" basics.  Still use a numbered summary for procedures with ≥3 steps.

- **Expert** — Be concise and direct.  Assume full familiarity with RAG
  concepts.  Skip step-by-step breakdowns unless the user asks.

If no profile is present, default to the **New to RAG** format below.

## STRICT RULE — Format for new users

When Experience level is ``New to RAG``, apply ALL of the following:

**Tool selection rules:**

- *Abstract RAG concepts* (what is chunking, what is an embedding, \
  how does retrieval work in general): answer from your knowledge, \
  no tools needed.

- *Current config values* (what is top_k set to, which preset is active): \
  call run_rag_facile("config show") — live data, not docs.

- *rag-facile product questions* (how to install, how presets work, \
  what the evaluation command does, how to set up a workspace): \
  call get_docs() with the relevant topic, then distill the result \
  into the format below. Never copy the raw doc structure.

**Reply structure (always in this exact order, nothing else):**
1. One plain sentence answering the question — zero jargon.
2. A numbered list of 3–5 steps or ideas, each in plain language.
3. Exactly this question: "Voulez-vous que j'explique l'une de ces étapes en détail ?"
4. A ``## Glossaire`` section — each term on its own line, prefixed with ``- ``, \
one plain sentence per entry.

**Absolutely forbidden:** tables, ASCII diagrams, sub-sections, \
inline term definitions, bullet sub-lists, more than 5 numbered items.

Examples (always follow this exact format):

---
Q : C'est quoi le RAG ?
R : Le RAG, c'est un système qui cherche les bons passages dans vos documents avant de générer une réponse.

Les grandes étapes :
1. On découpe vos documents en petits extraits.
2. On les indexe pour pouvoir les retrouver rapidement.
3. Quand vous posez une question, on récupère les extraits les plus pertinents.
4. On les donne au modèle de langage pour qu'il rédige la réponse.

Voulez-vous que j'explique l'une de ces étapes en détail ?

## Glossaire
- **Chunk** : un extrait de texte découpé depuis un document.
- **Indexation** : l'opération qui rend les extraits recherchables rapidement.
- **Modèle de langage (LLM)** : le programme qui rédige la réponse finale.

---
Q : C'est quoi un embedding ?
R : Un embedding, c'est une façon de transformer du texte en nombres pour que l'ordinateur puisse comparer des phrases.

Comment ça fonctionne :
1. Chaque extrait de texte est converti en une liste de nombres.
2. Des textes similaires donnent des listes de nombres proches.
3. Quand vous posez une question, elle est aussi convertie en nombres.
4. On cherche les extraits dont les nombres sont les plus proches de votre question.

Voulez-vous que j'explique l'une de ces étapes en détail ?

## Glossaire
- **Embedding** : représentation numérique d'un texte sous forme de vecteur.
- **Vecteur** : liste de nombres qui encode le sens d'un texte.
- **Similarité** : mesure de proximité entre deux vecteurs.

---
Q : Pourquoi mon système RAG donne de mauvaises réponses ?
R : Un RAG peut donner de mauvaises réponses pour plusieurs raisons liées à la qualité de la récupération ou du modèle.

Les causes les plus fréquentes :
1. Les documents récupérés ne contiennent pas la bonne information.
2. Les extraits sont trop petits ou trop grands pour être utiles.
3. La question est trop vague pour trouver les bons passages.
4. Le modèle invente des informations quand il ne sait pas.

Voulez-vous que j'explique comment corriger l'une de ces causes ?

## Glossaire
- **Récupération** : étape où les passages pertinents sont extraits de la base documentaire.
- **Hallucination** : fait pour un modèle de générer des informations fausses présentées comme vraies.
---

## STRICT RULE — Configuration changes

NEVER change a config setting immediately when a user asks. \
You MUST follow this exact two-step flow every time, with no exceptions:

Step 1 — Explain and ask. In a single reply:
  - State what you are about to change and the old → new value
  - Explain the concrete impact (speed, quality, cost)
  - End with an EXPLICIT question such as:
    "Puis-je effectuer ce changement ?"

Step 2 — Wait. Do NOT call run_rag_facile yet. Stop and wait for the user's reply.

Step 3 — Only if the user replies with a clear yes ("oui", "yes", "ok", "vas-y", \
"go ahead", etc.) in a NEW message, call run_rag_facile("config set <key> <value>").

If the user's original message already sounds like a confirmation ("mets top_k à 15"), \
treat it as a REQUEST, not a confirmation — still ask the explicit question in Step 1.

## Language

Respond in **French** by default. If the user writes in a different language, \
adapt and respond in their language for the rest of the conversation.
"""

# ── Newbie format enforcement ─────────────────────────────────────────────────

# Appended to the user message immediately before agent.run() for new users.
# Proximity to generation = stronger compliance than system prompt alone.
_FORMAT_ANCHOR = (
    "\n\n---\n"
    "FORMAT OBLIGATOIRE : intro courte (1-2 phrases) + "
    "liste numérotée (max 5 étapes) + ## Glossaire avec des tirets. "
    "PAS de tableaux. PAS de sous-titres. Commence ta réponse :"
)


def _is_newbie_format_ok(text: str) -> bool:
    """Return True when a response follows the required newbie format.

    Checks:
    - Contains ## Glossaire
    - Contains at least one numbered step (1. …)
    - No markdown tables (|…|)
    - No sub-sections beyond ## Glossaire (extra ## headers)
    - Reasonably short (< 600 words)
    """
    import re

    has_glossaire = "## Glossaire" in text or "##Glossaire" in text
    has_steps = bool(re.search(r"^\d+[.\s]", text, re.MULTILINE))
    no_tables = not bool(re.search(r"^\|.+\|", text, re.MULTILINE))
    extra_headers = re.findall(r"^#{2,3}\s+", text, re.MULTILINE)
    # Allow at most one ## header (the Glossaire itself)
    no_extra_sections = len(extra_headers) <= 1
    not_too_long = len(text.split()) < 600
    return (
        has_glossaire and has_steps and no_tables and no_extra_sections and not_too_long
    )


# ── Per-language UI strings ───────────────────────────────────────────────────

_UI: dict[str, dict[str, str]] = {
    "fr": {
        "greeting": "Bonjour\u00a0! Je suis votre assistant RAG.",
        "subtitle": (
            "Posez-moi vos questions sur RAG, votre configuration "
            "ou comment améliorer vos résultats.\n"
            "Tapez [bold]/new[/bold] pour une nouvelle session, "
            "[bold]q[/bold] ou Ctrl+C pour quitter."
        ),
        "no_workspace_hint": (
            "\n[dim]💡 Aucun ragfacile.toml trouvé — lancez "
            "[bold]rag-facile setup[/bold] pour créer un espace de travail.[/dim]"
        ),
        "thinking": "Réflexion en cours...",
        "you": "Vous",
        "goodbye": "À bientôt\u00a0!",
        "interrupted": "Interrompu.",
        "api_error_hint": "Vérifiez vos variables OPENAI_API_KEY, OPENAI_BASE_URL et RAG_ASSISTANT_MODEL.",
        "too_many_steps": (
            "J'ai eu besoin de trop d'étapes pour répondre. "
            "Pouvez-vous reformuler ou poser une question plus simple\u00a0?"
        ),
        "rate_limited": "Limite de requêtes atteinte — nouvelle tentative dans {n}s (Ctrl+C pour annuler)\u00a0...",
        "session_reset": "🔄 Nouvelle session — mémoire sauvegardée.",
        "skill_loaded": "📚 Compétence '{name}' activée.",
        "skill_cleared": "📚 Compétence désactivée.",
        "skill_not_found": "Compétence '{name}' introuvable. Tapez /skills pour voir la liste.",
        "skill_installing": "Installation de '{pkg}'...",
    },
    "en": {
        "greeting": "Bonjour! I'm your RAG assistant.",
        "subtitle": (
            "Ask me anything about RAG, your pipeline config, or how to improve your results.\n"
            "Type [bold]/new[/bold] for a new session, "
            "[bold]q[/bold] or Ctrl+C to quit."
        ),
        "no_workspace_hint": (
            "\n[dim]💡 No ragfacile.toml found — run "
            "[bold]rag-facile setup[/bold] to create a workspace.[/dim]"
        ),
        "thinking": "Thinking...",
        "you": "You",
        "goodbye": "À bientôt!",
        "interrupted": "Interrupted.",
        "api_error_hint": "Check your OPENAI_API_KEY, OPENAI_BASE_URL and RAG_ASSISTANT_MODEL.",
        "too_many_steps": (
            "I needed too many steps to answer that. "
            "Could you rephrase or break it into smaller questions?"
        ),
        "rate_limited": "Rate limit reached — retrying in {n}s (Ctrl+C to cancel)...",
        "session_reset": "🔄 New session — memory saved.",
        "skill_loaded": "📚 Skill '{name}' activated.",
        "skill_cleared": "📚 Skill deactivated.",
        "skill_not_found": "Skill '{name}' not found. Type /skills to see the list.",
        "skill_installing": "Installing '{pkg}'...",
    },
}

# Albert API allows 10 req/min; smolagents may use several calls per turn.
# Wait 15s on 429 before one automatic retry.
_RATE_LIMIT_WAIT = 15


class _SessionState:
    """Mutable session state — reset via ``new()`` for /new command."""

    __slots__ = (
        "turns",
        "start",
        "turn_count",
        "first_turn",
        "active_skill",
        "active_skill_content",
        "skill_injected",
    )

    def __init__(self) -> None:
        self.reset()

    def reset(self) -> None:
        """Reset all fields to their initial values."""
        self.turns: list[dict[str, str]] = []
        self.start: datetime = datetime.now()  # noqa: DTZ005
        self.turn_count: int = 0
        self.first_turn: bool = True
        self.active_skill: str | None = None
        self.active_skill_content: str | None = None
        self.skill_injected: bool = False


# Maximum number of ActionSteps to keep in the agent's memory.
# Older steps have their model_input_messages cleared to free memory,
# and then are removed, keeping only the most recent ones.
_MAX_AGENT_STEPS = 20


def _trim_agent_memory(step: ActionStep, *, agent: ToolCallingAgent) -> None:
    """Step callback: prune old steps from the agent's in-memory history.

    Keeps:
    - All ``TaskStep`` instances (required for context)
    - The most recent *_MAX_AGENT_STEPS* ``ActionStep`` instances
    Removes older ``ActionStep`` instances and clears their
    ``model_input_messages`` to free the largest objects first.
    """
    action_steps = [s for s in agent.memory.steps if isinstance(s, ActionStep)]
    if len(action_steps) <= _MAX_AGENT_STEPS:
        return

    # Steps to prune: oldest action steps beyond the limit
    steps_to_prune = action_steps[:-_MAX_AGENT_STEPS]
    to_prune = {id(s) for s in steps_to_prune}
    for s in steps_to_prune:
        s.model_input_messages = None  # free largest object first

    agent.memory.steps = [
        s
        for s in agent.memory.steps
        if isinstance(s, TaskStep) or id(s) not in to_prune
    ]


_TOOL_ICONS: dict[str, str] = {
    "activate_skill": "📚",
    "get_agents_md": "📋",
    "get_recent_git_activity": "📜",
    "get_docs": "📖",
    "memory_search": "🔍",
    "run_rag_facile": "🖥️",
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
    # Intentionally separate from OPENAI_MODEL (RAG pipeline) — the assistant
    # and the RAG pipeline are different use cases with different quality needs.
    # Override with RAG_ASSISTANT_MODEL in .env for a lighter/faster model.
    model_id = os.environ.get("RAG_ASSISTANT_MODEL", "openweight-large")

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


def _finalize(
    workspace: Path | None,
    session_turns: list[dict[str, str]],
    session_start: datetime,
) -> None:
    """End-of-session housekeeping (best-effort, never raises)."""
    if not workspace or not session_turns:
        return
    try:
        from rag_facile.memory.lifecycle import finalize_session

        # Build an LLM-backed fact extractor if API credentials are available.
        extract_fn = _build_extract_fn()

        finalize_session(
            workspace, session_turns, session_start, extract_facts_fn=extract_fn
        )
    except Exception as exc:  # noqa: BLE001 — session finalization must never crash the CLI
        import logging

        logging.warning("Session finalization failed: %s", exc)


def _build_extract_fn() -> Callable[[str], list[tuple[str, str]]] | None:
    """Return an ``extract_facts_fn`` closure, or None if credentials are missing."""
    api_key = os.environ.get("OPENAI_API_KEY") or os.environ.get("ALBERT_API_KEY", "")
    api_base = os.environ.get("OPENAI_BASE_URL", "https://albert.api.etalab.gouv.fr/v1")
    model = os.environ.get("RAG_ASSISTANT_MODEL", "openweight-large")

    if not api_key:
        return None

    from rag_facile.memory.lifecycle import extract_facts_with_llm

    def _extract(transcript: str) -> list[tuple[str, str]]:
        return extract_facts_with_llm(
            transcript, api_key=api_key, api_base=api_base, model=model
        )

    return _extract


def start_chat(debug: bool = False) -> None:
    """Launch the interactive RAG assistant chat loop."""
    # Detect workspace — walk up from cwd for ragfacile.toml
    workspace = _detect_workspace()
    language = "fr"  # default — overridden once we have a workspace
    experience = "new"  # default — overridden once we have a workspace
    if workspace:
        load_dotenv(workspace / ".env")  # load API key + config from project .env
        set_workspace_root(workspace)
        _set_memory_workspace(workspace)
        # First-run: initialise .agent/ and capture chosen language
        if needs_init(workspace):
            language = run_init_wizard(workspace)
        else:
            language = read_language(workspace)
        experience = read_experience(workspace)

    ui = _UI.get(language, _UI["fr"])

    # Load persistent memory — injected into the first user turn (not system prompt)
    # so the model pays full attention to it rather than losing it at the end of
    # smolagents' long built-in system prompt.
    from rag_facile.memory.context import bootstrap_context
    from rag_facile.memory.stores import EpisodicLog, SemanticStore

    # Compact old episodic logs before loading context (prunes stale data)
    if workspace:
        from rag_facile.memory.lifecycle import compact_episodic_logs

        compact_episodic_logs(workspace)

    profile_context = bootstrap_context(workspace) if workspace else ""

    # Ensure MEMORY.md exists (creates from template on first session)
    if workspace and not (workspace / ".agent" / "MEMORY.md").exists():
        SemanticStore.create(workspace)

    # Session state — used by lifecycle hooks; reset by /new
    ss = _SessionState()

    # Discover skills: built-in + workspace (.agents/skills/)
    available_skills = discover_skills(workspace)
    set_available_skills(available_skills)  # expose to activate_skill tool

    # Build model + agent — typer.Exit propagates naturally on missing API key
    model = _build_model()

    # Side-effect hook: when the agent calls activate_skill(), persist the returned
    # content so it's injected into subsequent turns (same as explicit /skills load).
    def _on_skill_activated(skill_name: str, content: str) -> None:
        ss.active_skill = skill_name
        ss.active_skill_content = content
        ss.skill_injected = True  # content already in agent context this turn
        console.print(f"[dim]{ui['skill_loaded'].format(name=skill_name)}[/dim]")

    def _wrap_activate_skill(tool_obj):
        """Extend _with_notification to also persist skill state."""
        _original_forward = tool_obj.forward

        def _forward(name: str, **kwargs: object) -> object:
            result = _original_forward(name, **kwargs)
            if isinstance(result, str) and not result.startswith("Skill '"):
                # Successful activation — result IS the skill content
                _on_skill_activated(name, result)
            return result

        tool_obj.forward = _forward
        tool_obj._notification_wrapped = True  # prevent double-wrap
        return tool_obj

    tools = [
        _with_notification(t)
        for t in [
            get_agents_md,
            get_recent_git_activity,
            get_docs,
            run_rag_facile,
            memory_read,
            memory_write,
            memory_edit,
            memory_search,
        ]
    ] + [_wrap_activate_skill(activate_skill)]

    agent = ToolCallingAgent(
        tools=tools,
        model=model,
        instructions=_SYSTEM_PROMPT,
        verbosity_level=LogLevel.INFO if debug else LogLevel.OFF,
        max_steps=5,
        step_callbacks=[_trim_agent_memory],
    )

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
            _finalize(workspace, ss.turns, ss.start)
            break

        if not user_input:
            continue

        if user_input.lower() in ("q", "quit", "exit", "bye", "au revoir", "quitter"):
            console.print(f"[dim]{ui['goodbye']}[/dim]")
            _finalize(workspace, ss.turns, ss.start)
            break

        # ── /new — reset session ──────────────────────────────────────────────
        if user_input.strip().lower() == "/new":
            _finalize(workspace, ss.turns, ss.start)
            ss.reset()

            # Reset agent conversation history
            if hasattr(agent, "memory") and agent.memory is not None:
                agent.memory.reset()

            # Reload profile context for the new session
            profile_context = bootstrap_context(workspace) if workspace else ""

            console.print(f"[dim]{ui['session_reset']}[/dim]")
            console.print()
            continue

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
                ss.active_skill = None
                ss.active_skill_content = None
                ss.skill_injected = False
                console.print(f"[dim]{ui['skill_cleared']}[/dim]")

            elif sub in available_skills:
                # /skills <name> — explicit load: activate and bootstrap the flow
                ss.active_skill = sub
                ss.active_skill_content = load_skill(available_skills[sub])
                console.print(f"[dim]{ui['skill_loaded'].format(name=sub)}[/dim]")
                # Inject skill + trigger word so the agent starts its flow immediately
                user_input = (
                    f"[Compétence chargée: {sub}]\n{ss.active_skill_content}\n\n---\n\n"
                    "Commence."
                )
                ss.skill_injected = True
                _skill_bootstrap = (
                    True  # skip the outer continue — fall through to agent
                )

            else:
                console.print(f"[dim]{ui['skill_not_found'].format(name=sub)}[/dim]")

            if not _skill_bootstrap:
                continue

        # Skill activation is handled by the agent itself via the activate_skill tool.
        # No keyword auto-detection here — the LLM picks the right skill semantically.

        # Episodic logging — record user turn
        if workspace:
            EpisodicLog.append_turn(workspace, "user", user_input)
        ss.turns.append({"role": "user", "content": user_input})
        ss.turn_count += 1

        # Build effective_input — layer memory (first turn) + skill (on load) + message
        effective_input = user_input

        # Inject profile on first turn of the session
        if profile_context and ss.first_turn:
            effective_input = (
                f"[Profil utilisateur]\n{profile_context}\n\n---\n\n{effective_input}"
            )
            ss.first_turn = False

        # Inject skill content the first time a skill becomes active
        if ss.active_skill_content and not ss.skill_injected:
            effective_input = (
                f"[Compétence chargée: {ss.active_skill}]\n{ss.active_skill_content}\n\n---\n\n"
                f"{effective_input}"
            )
            ss.skill_injected = True

        # 1b — Format anchor: append reminder close to generation point for new users.
        # Proximity bias means this is more effective than system prompt rules alone.
        if experience == "new":
            effective_input = effective_input + _FORMAT_ANCHOR

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

        response_text = str(response)

        # 1c — Post-processing validator: if the response violates newbie format,
        # do one targeted retry with an explicit violation message.
        if experience == "new" and not _is_newbie_format_ok(response_text):
            retry_input = (
                f"Ta réponse précédente ne respecte pas le format requis "
                f"(tableaux, sous-titres, ou trop longue). "
                f"Réécris-la en suivant EXACTEMENT ce format : "
                f"1 phrase d'intro + max 5 étapes numérotées + ## Glossaire avec des tirets. "
                f"PAS de tableaux. PAS de sous-titres.\n\n"
                f"Question initiale : {user_input}"
            )
            with console.status(f"[dim]{ui['thinking']}[/dim]", spinner="dots"):
                try:
                    retry_response = agent.run(retry_input, reset=False)
                    response_text = str(retry_response)
                except (openai.APIError, AgentError, AgentMaxStepsError):
                    pass  # keep original response on retry failure

        # Episodic logging — record assistant turn
        if workspace:
            EpisodicLog.append_turn(workspace, "assistant", response_text)
        ss.turns.append({"role": "assistant", "content": response_text})
        ss.turn_count += 1

        # Mid-session checkpoint every 8 turns
        if workspace:
            from rag_facile.memory.lifecycle import run_checkpoint, should_checkpoint

            if should_checkpoint(ss.turn_count):
                run_checkpoint(workspace, ss.turns[-8:])

        console.print("[bold green]Assistant[/bold green]:")
        console.print(Markdown(response_text))
        console.print()
