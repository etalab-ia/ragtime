import logging
import os
from datetime import datetime, timezone
from uuid import uuid4

import chainlit as cl
import engineio
import engineio.payload
from chainlit.input_widget import Switch
from dotenv import load_dotenv
from rag_facile.core import get_config
from rag_facile.core.mediatech import get_collection_name
from rag_facile.pipelines import get_accepted_mime_types, process_file, stream_answer
from rag_facile.tracing import FeedbackRecord, get_store


# Increase the number of packets allowed in a single payload to prevent "Too
# many packets in payload" errors. This is especially helpful during streaming
# or when WebSockets are falling back to polling.
engineio.payload.Payload.max_decode_packets = 200

load_dotenv()

# Load RAG configuration
rag_config = get_config()


# ---------------------------------------------------------------------------
# Feedback tag taxonomy
# ---------------------------------------------------------------------------

_POSITIVE_TAGS = ["Pertinent", "Complet", "Clair", "Utile", "Précis"]
_NEGATIVE_TAGS = [
    "Non pertinent",
    "Incomplet",
    "Confus",
    "Éléments faux",
    "Sources manquantes",
    "Sources erronées / obsolètes",
]


# ---------------------------------------------------------------------------
# Lifecycle hooks
# ---------------------------------------------------------------------------


@cl.on_chat_start
async def start_chat():
    cl.user_session.set(
        "message_history",
        [{"role": "system", "content": rag_config.generation.system_prompt}],
    )

    # Initialise active collections from config
    active_collections = list(rag_config.storage.collections)
    cl.user_session.set("active_collections", active_collections)

    # Show collection toggles in the settings panel (gear icon in header)
    widgets = []
    for col_id in rag_config.storage.collections:
        name = get_collection_name(col_id) or f"Collection {col_id}"
        widgets.append(Switch(id=f"col_{col_id}", label=f"📚 {name}", initial=True))
    if widgets:
        await cl.ChatSettings(widgets).send()


@cl.on_settings_update
async def on_settings_update(settings: dict) -> None:
    """Update active collections when the user toggles settings."""
    active = [
        col_id
        for col_id in rag_config.storage.collections
        if settings.get(f"col_{col_id}", True)
    ]
    cl.user_session.set("active_collections", active)


# ---------------------------------------------------------------------------
# Main message handler
# ---------------------------------------------------------------------------


@cl.on_message
async def main(message: cl.Message):
    message_history = cl.user_session.get("message_history")
    active_collections: list[int] = cl.user_session.get("active_collections") or []

    # Handle attachments — ingest into Albert collection for RAG retrieval
    if message.elements:
        allowed_extensions = {
            ext for exts in get_accepted_mime_types().values() for ext in exts
        }
        for element in message.elements:
            if element.path:
                suffix = os.path.splitext(element.name)[1].lower()
                if suffix not in allowed_extensions:
                    await cl.Message(
                        content=f"Unsupported file type '{suffix}'. "
                        f"Accepted formats: {', '.join(sorted(allowed_extensions))}"
                    ).send()
                    continue
                try:
                    status = process_file(element.path, element.name)
                    await cl.Message(content=status).send()
                except (OSError, ValueError) as e:
                    await cl.Message(
                        content=f"Error indexing '{element.name}': {e!s}"
                    ).send()

    # Pre-generate trace_id so we can attach feedback before stream ends
    trace_id = str(uuid4())
    cl.user_session.set("last_trace_id", trace_id)

    msg = cl.Message(content="")
    await msg.send()

    # Full RAG turn: retrieve → prompt → stream → trace (all inside stream_answer)
    async for token in stream_answer(
        message.content,
        message_history,
        trace_id=trace_id,
        session_id=cl.user_session.get("id", ""),
        collection_ids=active_collections,
    ):
        await msg.stream_token(token)

    # Append clean question + answer to history (no injected context)
    message_history.append({"role": "user", "content": message.content})
    message_history.append({"role": "assistant", "content": msg.content})
    await msg.update()

    # Feedback UI — created OUTSIDE any cl.Step to avoid issue #1202
    if rag_config.tracing.enabled:
        await _show_feedback_ui(trace_id)


# ---------------------------------------------------------------------------
# Feedback UI helpers
# ---------------------------------------------------------------------------


async def _show_feedback_ui(trace_id: str) -> None:
    """Send star-rating action row for the last answer."""
    await cl.Message(
        content="**Comment évaluez-vous la réponse ?**",
        actions=[
            cl.Action(
                name=f"star_{i}",
                value=str(i),
                label="⭐" * i,
                payload={"trace_id": trace_id},
            )
            for i in range(1, 6)
        ],
    ).send()


async def _ask_sentiment(trace_id: str, star: int) -> None:
    """Prompt thumbs up/down after a star rating."""
    res = await cl.AskActionMessage(
        content="👍 Positive ou 👎 Négative ?",
        actions=[
            cl.Action(name="positive", label="👍 Positive", value="positive"),
            cl.Action(name="negative", label="👎 Négative", value="negative"),
        ],
        timeout=120,
    ).send()
    if res:
        await _ask_tags(trace_id, star, res.get("value", ""))


async def _ask_tags(trace_id: str, star: int, sentiment: str) -> None:
    """Prompt quality tags, then free-text comment, then persist."""
    tags_list = _POSITIVE_TAGS if sentiment == "positive" else _NEGATIVE_TAGS
    tag_res = await cl.AskActionMessage(
        content="Sélectionnez les étiquettes applicables :",
        actions=[cl.Action(name=f"tag_{t}", label=t, value=t) for t in tags_list],
        timeout=120,
    ).send()
    selected_tags = [tag_res["value"]] if tag_res else []

    comment_res = await cl.AskUserMessage(
        content="Commentaires (optionnel — appuyez sur Entrée pour ignorer) :",
        timeout=120,
    ).send()
    comment = comment_res["output"].strip() if comment_res else None
    if not comment:
        comment = None

    _persist_feedback(
        trace_id=trace_id,
        star=star,
        sentiment=sentiment,
        tags=selected_tags,
        comment=comment,
    )


def _persist_feedback(
    trace_id: str,
    star: int | None,
    sentiment: str | None,
    tags: list[str],
    comment: str | None,
) -> None:
    """Write feedback record to the trace store."""
    fb: FeedbackRecord = {
        "feedback_id": str(uuid4()),
        "trace_id": trace_id,
        "created_at": datetime.now(timezone.utc).isoformat(),
        "star_rating": star,
        "sentiment": sentiment,
        "tags": tags,
        "comment": comment,
    }
    try:
        get_store().record_feedback(fb)
    except (OSError, RuntimeError) as exc:
        logging.getLogger(__name__).warning("Failed to record feedback: %s", exc)


# ---------------------------------------------------------------------------
# Star rating callbacks (one per rating level)
#
# Chainlit's @cl.action_callback only accepts a plain string name — no regex
# support.  We register 5 thin callbacks that all delegate to one helper,
# keeping the logic in a single place.
# ---------------------------------------------------------------------------


async def _on_star(action: cl.Action, rating: int) -> None:
    """Shared handler for all star rating actions."""
    cl.user_session.set("pending_star", rating)
    await _ask_sentiment(action.payload["trace_id"], rating)


@cl.action_callback("star_1")
async def on_star_1(action: cl.Action):
    await _on_star(action, 1)


@cl.action_callback("star_2")
async def on_star_2(action: cl.Action):
    await _on_star(action, 2)


@cl.action_callback("star_3")
async def on_star_3(action: cl.Action):
    await _on_star(action, 3)


@cl.action_callback("star_4")
async def on_star_4(action: cl.Action):
    await _on_star(action, 4)


@cl.action_callback("star_5")
async def on_star_5(action: cl.Action):
    await _on_star(action, 5)
