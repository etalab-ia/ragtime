"""Albert API provider for Data Foundry.

Uses Albert API (OpenGateLLM) with hybrid search for document retrieval
and OpenAI-compatible LLM for Q/A generation.
"""

import json
import logging
from collections.abc import Iterator
from datetime import datetime, timezone
from pathlib import Path


try:
    from albert import AlbertClient
except ImportError as e:
    raise ImportError(
        "albert-client package is required. Install with: uv add albert-client"
    ) from e

from .document_preprocessor import DocumentPreprocessor
from .schema import GeneratedSample


logger = logging.getLogger(__name__)


class AlbertApiProvider:
    """Data Foundry provider using Albert API (OpenGateLLM).

    This provider uploads documents to Albert's collections API, uses
    hybrid search for context retrieval, and streams generated Q/A pairs
    from an OpenAI-compatible LLM.
    """

    def __init__(self, api_key: str, base_url: str, model: str):
        """Initialize the Albert API provider.

        Args:
            api_key: OpenAI-compatible API key for Albert API
            base_url: Base URL for Albert API (e.g., http://localhost:8000)
            model: Model name to use for LLM (e.g., "mistral-7b")
        """
        self.api_key = api_key
        self.base_url = base_url.rstrip("/")
        self.model = model

        # Initialize Albert client for all API operations
        self.albert_client = AlbertClient(api_key=api_key, base_url=self.base_url)

        # Initialize document preprocessor for PDF extraction
        self.preprocessor = DocumentPreprocessor()

        # Track resources for cleanup
        self.collection_id: str | None = None

    def upload_documents(self, document_paths: list[str]) -> None:
        """Upload documents to Albert and create a collection.

        Args:
            document_paths: List of paths to documents (PDF, MD, TXT)
                           PDFs are automatically converted to markdown text.
        """
        logger.info(
            f"Starting document upload to Albert API ({len(document_paths)} documents)"
        )
        for doc_path in document_paths:
            logger.debug(f"  - {doc_path}")

        # Preprocess documents (extract PDFs to text)
        processed_paths = self.preprocessor.process_documents(document_paths)
        logger.info(f"Preprocessed {len(processed_paths)} documents")

        # Create a collection using SDK
        collection_name = (
            f"data_foundry_{datetime.now(timezone.utc).strftime('%Y%m%d_%H%M%S')}"
        )

        collection = self.albert_client.collections.create(
            name=collection_name,
            description="RAG Facile Data Foundry",
        )
        self.collection_id = collection.id

        logger.info(f"Created Albert collection: {self.collection_id}")

        # Upload each processed document using SDK
        for i, doc_path in enumerate(processed_paths, 1):
            logger.info(
                f"Uploading document {i}/{len(processed_paths)}: {Path(doc_path).name}"
            )
            logger.debug(f"  Size: {Path(doc_path).stat().st_size} bytes")

            try:
                self.albert_client.documents.upload(
                    file_path=doc_path, collection_id=self.collection_id
                )
                logger.debug("  Upload successful")
            except Exception as e:
                error_msg = f"Failed to upload {doc_path}: {e}"
                logger.error(error_msg)
                raise RuntimeError(error_msg) from e

    def generate(self, num_samples: int) -> Iterator[GeneratedSample]:
        """Generate Q/A samples using hybrid search and LLM.

        Args:
            num_samples: Target number of samples to generate

        Yields:
            GeneratedSample objects as they are generated
        """
        if not self.collection_id:
            raise RuntimeError(
                "No collection ID available. Call upload_documents first."
            )

        # Build the generation prompt
        prompt = self._build_prompt(num_samples)
        logger.debug(f"Generation prompt ({len(prompt)} chars):\n{prompt}\n")

        # Stream the response from LLM
        # The LLM will be responsible for calling search internally
        logger.info(f"Sending prompt to Albert API (collection: {self.collection_id})")
        seen_samples: set[str] = set()
        buffer = ""
        total_response = ""

        try:
            stream = self.albert_client.chat.completions.create(
                model=self.model,
                messages=[{"role": "user", "content": prompt}],
                stream=True,
            )

            for chunk in stream:
                if chunk.choices and chunk.choices[0].delta.content:
                    content = chunk.choices[0].delta.content
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

            logger.info("Completed Albert generation")
            logger.debug(
                f"Total response ({len(total_response)} chars):\n{total_response}\n"
            )
        except Exception as e:
            logger.error(f"LLM generation failed: {e}", exc_info=True)
            raise RuntimeError(f"LLM generation failed: {e}") from e

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
        """Delete collection from Albert API and clean up temporary files."""
        if self.collection_id:
            try:
                self.albert_client.collections.delete(self.collection_id)
            except Exception:
                pass  # Non-critical

        # Clean up temporary files created during preprocessing
        try:
            self.preprocessor.cleanup()
        except Exception:
            pass  # Non-critical

    def _build_prompt(self, num_samples: int) -> str:
        """Build the generation prompt for the LLM."""
        return f"""⚠️ AUTOMATED CONVERSATION - STRICT OUTPUT FORMAT REQUIRED ⚠️

This is an automated system that parses your response programmatically.
You MUST follow the output format exactly - any deviation will break the system.

🔴 CRITICAL: GENERATE EXACTLY {num_samples} SAMPLES - NO MORE, NO LESS 🔴
You MUST generate exactly {num_samples} Question/Answer pairs. Not 3, not {num_samples + 1}, not fewer.
Output exactly {num_samples} JSON objects, one per line.

Requirements:
- Questions and answers must be in French
- Each answer must be fully grounded in the document context
- Ensure diversity - avoid similar questions about the same topics

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

NOW OUTPUT EXACTLY {num_samples} JSONL OBJECTS - NO PREAMBLE, NO EXPLANATIONS, NO TEXT BEFORE OR AFTER."""

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
