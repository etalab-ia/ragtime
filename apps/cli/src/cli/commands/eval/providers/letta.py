"""Letta Cloud provider for Data Foundry.

Uses Letta Cloud's agent API to generate synthetic Q/A pairs.
"""

import json
import logging
from collections.abc import Iterator
from datetime import datetime, timezone
from pathlib import Path

from .document_preprocessor import DocumentPreprocessor
from .schema import GeneratedSample

logger = logging.getLogger(__name__)


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

        # Initialize document preprocessor for PDF extraction
        self.preprocessor = DocumentPreprocessor()

    def upload_documents(self, document_paths: list[str]) -> None:
        """Upload documents to Letta Cloud and attach to agent.

        Args:
            document_paths: List of paths to documents (PDF, MD, TXT)
                           PDFs are automatically converted to markdown text.
        """
        logger.info(
            f"Starting document upload to Letta Cloud ({len(document_paths)} documents)"
        )
        for doc_path in document_paths:
            logger.debug(f"  - {doc_path}")

        # Preprocess documents (extract PDFs to text)
        processed_paths = self.preprocessor.process_documents(document_paths)
        logger.info(f"Preprocessed {len(processed_paths)} documents")

        # Create a unique folder for this run
        folder_name = (
            f"data_foundry_{datetime.now(timezone.utc).strftime('%Y%m%d_%H%M%S')}"
        )
        folder = self.client.folders.create(name=folder_name)
        self.folder_id = folder.id
        logger.info(f"Created Letta folder: {self.folder_id} ({folder_name})")

        # Upload each processed document
        for i, doc_path in enumerate(processed_paths, 1):
            logger.info(
                f"Uploading document {i}/{len(processed_paths)}: {Path(doc_path).name}"
            )
            with open(doc_path, "rb") as f:
                self.client.folders.files.upload(file=f, folder_id=folder.id)
                logger.debug("  Upload successful")

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
        logger.info(f"Created Letta conversation: {self.conversation_id}")

        # Build the generation prompt
        prompt = self._build_prompt(num_samples)
        logger.debug(f"Generation prompt ({len(prompt)} chars):\n{prompt}\n")
        logger.info("Sending prompt to Letta agent...")

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
        total_response = ""

        for msg in stream:
            if hasattr(msg, "message_type") and msg.message_type == "assistant_message":
                content = (
                    msg.content if isinstance(msg.content, str) else str(msg.content)
                )
                total_response += content
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

        logger.info("Completed Letta generation")
        logger.debug(
            f"Total response ({len(total_response)} chars):\n{total_response}\n"
        )

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
        """Detach and delete folder from Letta Cloud and clean up temporary files."""
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

        # Clean up temporary files created during preprocessing
        try:
            self.preprocessor.cleanup()
        except Exception:
            pass  # Non-critical

    def _build_prompt(self, num_samples: int) -> str:
        """Build the generation prompt for the agent."""
        return f"""⚠️ AUTOMATED CONVERSATION - STRICT OUTPUT FORMAT REQUIRED ⚠️

This is an automated system that parses your response programmatically.
You MUST follow the output format exactly - any deviation will break the system.

Generate {num_samples} Question/Answer pairs from the uploaded documents.

Requirements:
- Questions and answers must be in French
- Each answer must be fully grounded in the document context
- Ensure diversity - avoid similar questions about the same topics
- Self-critique each pair for quality before outputting

🔴 CRITICAL OUTPUT FORMAT 🔴
Return ONLY valid JSONL with NO additional text, comments, explanations, or preamble.
Do not output anything before the first JSON object or after the last JSON object.
Each line must be a complete, valid JSON object with this exact structure:
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

NOW OUTPUT ONLY THE JSONL - NO PREAMBLE, NO EXPLANATIONS, NO TEXT BEFORE OR AFTER."""

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
