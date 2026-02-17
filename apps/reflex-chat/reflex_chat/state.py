import os
import json
from typing import Any, TypedDict

import reflex as rx
from pipelines import process_bytes, process_query
from dotenv import load_dotenv

from albert import AlbertClient, ChatCompletionMessageParam
from rag_core import get_config
from rag_core.mediatech import get_collection_name


# Load .env file
load_dotenv()

# Load RAG configuration
rag_config = get_config()

# Checking if the API keys are set properly
if not os.getenv("OPENAI_API_KEY"):
    raise Exception("Please set OPENAI_API_KEY environment variable.")

if not os.getenv("OPENAI_BASE_URL"):
    raise Exception("Please set OPENAI_BASE_URL environment variable for Albert API.")


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

    @rx.event
    def toggle_collection(self, col_id: str):
        """Toggle a collection on/off for RAG retrieval."""
        self.active_collections[col_id] = not self.active_collections.get(col_id, True)
        # Force state refresh
        self.active_collections = self.active_collections

    @rx.var
    def enabled_collection_ids(self) -> list[int]:
        """Get list of enabled collection IDs for RAG queries."""
        return [int(k) for k, v in self.active_collections.items() if v]

    @rx.var
    def collection_items(self) -> list[list[str]]:
        """Get collection items as [id, name, enabled] for rendering."""
        items = []
        for col_id_str, enabled in self.active_collections.items():
            name = get_collection_name(int(col_id_str)) or f"Collection {col_id_str}"
            items.append([col_id_str, name, str(enabled)])
        return items

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

    @rx.event
    def create_chat(self, form_data: dict[str, Any]):
        """Create a new chat."""
        # Add the new chat to the list of chats.
        new_chat_name = form_data["new_chat_name"]
        self.current_chat = new_chat_name
        self._chats[new_chat_name] = []
        self.is_modal_open = False

    @rx.event
    def set_is_modal_open(self, is_open: bool):
        """Set the new chat modal open state.

        Args:
            is_open: Whether the modal is open.
        """
        self.is_modal_open = is_open

    @rx.var
    def selected_chat(self) -> list[QA]:
        """Get the list of questions and answers for the current chat.

        Returns:
            The list of questions and answers.
        """
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
            self._chats = {
                "Intros": [],
            }
        if self.current_chat not in self._chats:
            self.current_chat = list(self._chats.keys())[0]

    @rx.event
    def set_chat(self, chat_name: str):
        """Set the name of the current chat.

        Args:
            chat_name: The name of the chat.
        """
        self.current_chat = chat_name

    @rx.event
    def set_new_chat_name(self, new_chat_name: str):
        """Set the name of the new chat.

        Args:
            new_chat_name: The name of the new chat.
        """
        self.new_chat_name = new_chat_name

    @rx.var
    def chat_titles(self) -> list[str]:
        """Get the list of chat titles.

        Returns:
            The list of chat names.
        """
        return list(self._chats.keys())

    @rx.event
    async def process_question(self, form_data: dict[str, Any]):
        # Get the question from the form
        question = form_data["question"]

        # Check if the question is empty
        if not question:
            return

        async for value in self.openai_process_question(question):
            yield value

    @rx.event
    async def openai_process_question(self, question: str):
        """Get the response from the API.

        Args:
            form_data: A dict with the current question.
        """

        # Add the question to the list of questions.
        qa = QA(question=question, answer="")
        self._chats[self.current_chat].append(qa)

        # Clear the input and start the processing.
        self.processing = True
        yield

        # Build the messages (uses config system prompt)
        messages: list[ChatCompletionMessageParam] = [
            {
                "role": "system",
                "content": rag_config.generation.system_prompt,
            }
        ]

        for qa in self._chats[self.current_chat]:
            messages.append({"role": "user", "content": qa["question"]})
            messages.append({"role": "assistant", "content": qa["answer"]})

        # Remove the last mock answer.
        messages = messages[:-1]

        # Retrieve relevant context via RAG pipeline (search -> rerank -> format)
        # Combine context with the current question to avoid accumulating
        # system messages in the conversation history.
        query_kwargs: dict[str, object] = {}
        if self.enabled_collection_ids:
            query_kwargs["collection_ids"] = self.enabled_collection_ids
        retrieved_context = process_query(question, **query_kwargs)
        if retrieved_context:
            messages[-1]["content"] = (
                "Use the following context to answer the user's question:\n\n"
                f"{retrieved_context}\n\n"
                f"Question: {question}"
            )

        # Start a new session to answer the question (uses config values)
        # Model comes from config with env var override
        model = os.getenv("OPENAI_MODEL") or rag_config.generation.model
        gen_params = {
            "stream": rag_config.generation.streaming,
            "temperature": rag_config.generation.temperature,
            "max_tokens": rag_config.generation.max_tokens,
        }
        session = AlbertClient(
            base_url=os.getenv("OPENAI_BASE_URL"),
        ).chat.completions.create(
            model=model,
            messages=messages,
            **gen_params,
        )

        # Stream the results, yielding after every word.
        try:
            for item in session:
                if item.choices and hasattr(item.choices[0].delta, "content"):
                    answer_text = item.choices[0].delta.content
                    # Ensure answer_text is not None before concatenation
                    if answer_text is not None:
                        self._chats[self.current_chat][-1]["answer"] += answer_text
                    else:
                        # Handle the case where answer_text is None,
                        # perhaps log it or assign a default value.
                        answer_text = ""
                        self._chats[self.current_chat][-1]["answer"] += answer_text
                    self._chats = self._chats
                    yield
        except json.JSONDecodeError:
            # Albert API occasionally sends malformed SSE events; continue
            # with whatever content was streamed so far.
            pass

        # Toggle the processing flag.
        self.processing = False
