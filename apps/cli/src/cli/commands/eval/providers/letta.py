"""Letta Cloud provider for Data Foundry.

Uses Letta Cloud's agent API to generate synthetic Q/A pairs.
"""

import json
from collections.abc import Iterator
from datetime import datetime, timezone

from .schema import GeneratedSample


class LettaProvider:
    """Data Foundry provider using Letta Cloud.

    This provider uploads documents to Letta Cloud, creates a conversation
    with a pre-configured data-foundry agent, and streams generated Q/A pairs.
    """

    def __init__(self, api_key: str, agent_id: str):
        """Initialize the Letta provider.

        Args:
            api_key: Letta Cloud API key
            agent_id: ID of the data-foundry agent on Letta Cloud
        """
        try:
            from letta_client import Letta
        except ImportError as e:
            raise ImportError(
                "letta-client package is required. Install with: uv add letta-client"
            ) from e

        self.client = Letta(api_key=api_key)
        self.agent_id = agent_id
        self.folder_id: str | None = None
        self.conversation_id: str | None = None

    def upload_documents(self, document_paths: list[str]) -> None:
        """Upload documents to Letta Cloud and attach to agent.

        Args:
            document_paths: List of paths to documents
        """
        # Create a unique folder for this run
        folder_name = (
            f"data_foundry_{datetime.now(timezone.utc).strftime('%Y%m%d_%H%M%S')}"
        )
        folder = self.client.folders.create(name=folder_name)
        self.folder_id = folder.id

        # Upload each document
        for doc_path in document_paths:
            with open(doc_path, "rb") as f:
                self.client.folders.files.upload(file=f, folder_id=folder.id)

        # Attach folder to the agent
        self.client.agents.folders.attach(
            agent_id=self.agent_id, folder_id=self.folder_id
        )

    def generate(self, num_samples: int) -> Iterator[GeneratedSample]:
        """Generate Q/A samples using the Letta agent.

        Args:
            num_samples: Target number of samples to generate

        Yields:
            GeneratedSample objects as they are generated
        """
        # Create a new conversation for this run
        conversation = self.client.conversations.create(agent_id=self.agent_id)
        self.conversation_id = conversation.id

        # Build the generation prompt
        prompt = self._build_prompt(num_samples)

        # Stream the response
        stream = self.client.conversations.messages.create(
            conversation_id=self.conversation_id,
            messages=[{"role": "user", "content": prompt}],
        )

        # Parse samples from the streaming response
        # Use a buffer to process only complete lines (more efficient than
        # re-parsing the entire response on each chunk)
        seen_samples: set[str] = set()
        buffer = ""

        for msg in stream:
            if hasattr(msg, "message_type") and msg.message_type == "assistant_message":
                content = (
                    msg.content if isinstance(msg.content, str) else str(msg.content)
                )
                buffer += content

                # Split into lines, keeping the last (possibly incomplete) line
                lines = buffer.split("\n")
                buffer = lines.pop()  # Keep incomplete line in buffer

                # Process complete lines
                for line in lines:
                    yield from self._process_line(line, seen_samples)

        # Process any remaining content in the buffer
        if buffer:
            yield from self._process_line(buffer, seen_samples)

    def _process_line(
        self, line: str, seen_samples: set[str]
    ) -> Iterator[GeneratedSample]:
        """Process a single line, yielding unique samples."""
        for sample in self._extract_samples(line):
            sample_key = sample.user_input
            if sample_key not in seen_samples:
                seen_samples.add(sample_key)
                yield sample

    def cleanup(self) -> None:
        """Detach and delete folder from Letta Cloud."""
        if self.folder_id:
            try:
                self.client.agents.folders.detach(
                    agent_id=self.agent_id, folder_id=self.folder_id
                )
            except Exception:
                pass  # Non-critical

            try:
                self.client.folders.delete(folder_id=self.folder_id)
            except Exception:
                pass  # Non-critical

    def _build_prompt(self, num_samples: int) -> str:
        """Build the generation prompt for the agent."""
        return f"""Generate {num_samples} Question/Answer pairs from the uploaded documents.

Requirements:
- Questions and answers must be in French
- Each answer must be fully grounded in the document context
- Ensure diversity - avoid similar questions about the same topics
- Self-critique each pair for quality before outputting

Return each sample as a JSON object on its own line with this exact structure:
{{
  "user_input": "Question in French?",
  "retrieved_contexts": ["The exact text passage that answers the question..."],
  "reference": "The answer in French, fully grounded in the context.",
  "_metadata": {{
    "source_file": "filename.pdf",
    "quality_score": 0.95,
    "topic_summary": "Brief topic for diversity tracking"
  }}
}}

Start generating now. Output each JSON sample on its own line as you generate them."""

    def _extract_samples(self, line: str) -> Iterator[GeneratedSample]:
        """Extract JSON sample from a single line."""
        line = line.strip()
        if not line or not line.startswith("{"):
            return

        try:
            data = json.loads(line)
            if "user_input" in data and "reference" in data:
                yield GeneratedSample.from_dict(data)
        except json.JSONDecodeError:
            pass  # Incomplete JSON, skip
