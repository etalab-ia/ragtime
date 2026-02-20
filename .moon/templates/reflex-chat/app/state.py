import logging
import os
from datetime import datetime, timezone
from typing import Any, TypedDict
from uuid import uuid4

import reflex as rx
from dotenv import load_dotenv
from rag_facile.core import get_config
from rag_facile.core.mediatech import get_collection_name
from rag_facile.pipelines import process_bytes, stream_answer
from rag_facile.tracing import FeedbackRecord, get_store


# Load .env file
load_dotenv()

# Load RAG configuration
rag_config = get_config()

# Checking if the API keys are set properly
if not os.getenv("OPENAI_API_KEY"):
    raise Exception("Please set OPENAI_API_KEY environment variable.")

if not os.getenv("OPENAI_BASE_URL"):
    raise Exception("Please set OPENAI_BASE_URL environment variable for Albert API.")


# ---------------------------------------------------------------------------
# Feedback tag taxonomy
# ---------------------------------------------------------------------------

POSITIVE_TAGS = ["Pertinent", "Complet", "Clair", "Utile", "Précis"]
NEGATIVE_TAGS = [
    "Non pertinent",
    "Incomplet",
    "Confus",
    "Éléments faux",
    "Sources manquantes",
    "Sources erronées / obsolètes",
]


class QA(TypedDict):
    """A question and answer pair."""

    question: str
    answer: str


class State(rx.State):
    """The app state."""

    # A dict from the chat name to the list of questions and answers.
    _chats: dict[str, list[QA]] = {
        "Intros": [],
    }

    # The current chat name.
    current_chat = "Intros"

    # Whether we are processing the question.
    processing: bool = False

    # Whether the new chat modal is open.
    is_modal_open: bool = False

    # Whether documents have been indexed for RAG retrieval.
    has_indexed_docs: bool = False

    # list of attached file names
    attached_files: list[str] = []

    # whether filtering is happening
    is_uploading: bool = False

    # Collection toggles: maps str(collection_id) → enabled status
    active_collections: dict[str, bool] = {
        str(col_id): True for col_id in rag_config.storage.collections
    }

    # ── Feedback state ──
    last_trace_id: str = ""
    feedback_star: int = 0  # 0 = unrated
    feedback_sentiment: str = ""  # "" | "positive" | "negative"
    feedback_tags: list[str] = []
    feedback_comment: str = ""
    feedback_submitted: bool = False
    feedback_visible: bool = False  # controls panel visibility

    # ── Collection management ──

    @rx.event
    def toggle_collection(self, col_id: str):
        """Toggle a collection on/off for RAG retrieval."""
        self.active_collections[col_id] = not self.active_collections.get(col_id, True)
        self.active_collections = self.active_collections

    @rx.var
    def enabled_collection_ids(self) -> list[int]:
        """Get list of enabled collection IDs for RAG queries."""
        return [int(k) for k, v in self.active_collections.items() if v]

    @rx.var
    def collection_items(self) -> list[dict[str, str]]:
        """Get collection items as dicts for rendering."""
        items = []
        for col_id_str, enabled in self.active_collections.items():
            name = get_collection_name(int(col_id_str)) or f"Collection {col_id_str}"
            items.append({"id": col_id_str, "name": name, "enabled": str(enabled)})
        return items

    # ── File upload ──

    async def handle_upload(self, files: list[rx.UploadFile]):
        """Upload files to Albert collection for RAG retrieval."""
        self.is_uploading = True
        for file in files:
            upload_data = await file.read()
            filename = file.filename or "unknown"
            process_bytes(upload_data, filename)
            self.attached_files.append(filename)
            self.has_indexed_docs = True
        self.is_uploading = False

    @rx.event
    def clear_attachment(self, filename: str):
        """Clear an attached file from the UI list."""
        if filename in self.attached_files:
            self.attached_files.remove(filename)
        if not self.attached_files:
            self.has_indexed_docs = False

    # ── Chat management ──

    @rx.event
    def create_chat(self, form_data: dict[str, Any]):
        """Create a new chat."""
        new_chat_name = form_data["new_chat_name"]
        self.current_chat = new_chat_name
        self._chats[new_chat_name] = []
        self.is_modal_open = False

    @rx.event
    def set_is_modal_open(self, is_open: bool):
        """Set the new chat modal open state."""
        self.is_modal_open = is_open

    @rx.var
    def selected_chat(self) -> list[QA]:
        """Get the list of questions and answers for the current chat."""
        return (
            self._chats[self.current_chat] if self.current_chat in self._chats else []
        )

    @rx.event
    def delete_chat(self, chat_name: str):
        """Delete the current chat."""
        if chat_name not in self._chats:
            return
        del self._chats[chat_name]
        if len(self._chats) == 0:
            self._chats = {"Intros": []}
        if self.current_chat not in self._chats:
            self.current_chat = list(self._chats.keys())[0]

    @rx.event
    def set_chat(self, chat_name: str):
        """Set the name of the current chat."""
        self.current_chat = chat_name

    @rx.event
    def set_new_chat_name(self, new_chat_name: str):
        """Set the name of the new chat."""
        self.new_chat_name = new_chat_name

    @rx.var
    def chat_titles(self) -> list[str]:
        """Get the list of chat titles."""
        return list(self._chats.keys())

    # ── Question processing ──

    @rx.event
    async def process_question(self, form_data: dict[str, Any]):
        question = form_data["question"]
        if not question:
            return
        async for value in self.openai_process_question(question):
            yield value

    @rx.event
    async def openai_process_question(self, question: str):
        """Get the response from the pipeline (retrieve + stream + trace)."""
        # Add the question to the list of questions
        qa = QA(question=question, answer="")
        self._chats[self.current_chat].append(qa)

        # Reset feedback state for this new turn
        trace_id = str(uuid4())
        self.last_trace_id = trace_id
        self.feedback_star = 0
        self.feedback_sentiment = ""
        self.feedback_tags = []
        self.feedback_comment = ""
        self.feedback_submitted = False
        self.feedback_visible = False

        self.processing = True
        yield

        # Build message history (system prompt + previous turns, NOT current)
        messages: list[dict[str, str]] = [
            {"role": "system", "content": rag_config.generation.system_prompt}
        ]
        for qa in self._chats[self.current_chat][:-1]:  # exclude current (last) turn
            messages.append({"role": "user", "content": qa["question"]})
            messages.append({"role": "assistant", "content": qa["answer"]})

        # Stream tokens from the pipeline (retrieve → prompt → LLM → trace)
        try:
            async for token in stream_answer(
                question,
                messages,
                trace_id=trace_id,
                session_id=self.router.session.client_token,
                collection_ids=self.enabled_collection_ids,
            ):
                self._chats[self.current_chat][-1]["answer"] += token
                self._chats = self._chats
                yield
        except Exception as exc:  # noqa: BLE001 — broad catch to avoid breaking chat
            logging.getLogger(__name__).error("stream_answer error: %s", exc)

        self.processing = False
        # Show feedback panel after answer is complete
        if rag_config.tracing.enabled:
            self.feedback_visible = True
        yield

    # ── Feedback events ──

    @rx.event
    def set_feedback_star(self, rating: int):
        """Set the star rating."""
        self.feedback_star = rating

    @rx.event
    def set_feedback_sentiment(self, sentiment: str):
        """Set the sentiment (positive/negative) and reset tags."""
        self.feedback_sentiment = sentiment
        self.feedback_tags = []

    @rx.event
    def toggle_feedback_tag(self, tag: str):
        """Toggle a quality tag on/off."""
        if tag in self.feedback_tags:
            self.feedback_tags = [t for t in self.feedback_tags if t != tag]
        else:
            self.feedback_tags = [*self.feedback_tags, tag]

    @rx.event
    def set_feedback_comment(self, comment: str):
        """Update the free-text comment."""
        self.feedback_comment = comment

    @rx.event
    def submit_feedback(self):
        """Persist the feedback record to SQLite."""
        if not self.last_trace_id:
            return

        fb: FeedbackRecord = {
            "feedback_id": str(uuid4()),
            "trace_id": self.last_trace_id,
            "created_at": datetime.now(timezone.utc).isoformat(),
            "star_rating": self.feedback_star or None,
            "sentiment": self.feedback_sentiment or None,
            "tags": self.feedback_tags,
            "comment": self.feedback_comment.strip() or None,
        }
        try:
            get_store().record_feedback(fb)
        except (OSError, RuntimeError) as exc:
            logging.getLogger(__name__).warning("Failed to record feedback: %s", exc)

        self.feedback_submitted = True
        self.feedback_visible = False

    @rx.event
    def dismiss_feedback(self):
        """Dismiss the feedback panel without submitting."""
        self.feedback_visible = False

    # ── Computed vars for feedback UI ──

    @rx.var
    def current_tags(self) -> list[str]:
        """Tags appropriate for the current sentiment selection."""
        if self.feedback_sentiment == "positive":
            return POSITIVE_TAGS
        if self.feedback_sentiment == "negative":
            return NEGATIVE_TAGS
        return []
