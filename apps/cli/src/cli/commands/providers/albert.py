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
        self.collection_id: int | None = None

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

        collection = self.albert_client.create_collection(
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
                self.albert_client.upload_document(
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

        # Retrieve sample passages from the collection to ground the generation
        document_context = self._retrieve_document_context()

        # Build the generation prompt with document context
        prompt = self._build_prompt(num_samples, document_context)
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
                self.albert_client.delete_collection(self.collection_id)
            except Exception:
                pass  # Non-critical

        # Clean up temporary files created during preprocessing
        try:
            self.preprocessor.cleanup()
        except Exception:
            pass  # Non-critical

    def _retrieve_document_context(self) -> str:
        """Retrieve sample passages from the collection to ground generation.

        Uses broad searches to get a representative sample of the document's
        content, which is then included in the prompt to prevent hallucination.

        Returns:
            A formatted string containing sample passages from the document
        """
        if not self.collection_id:
            return "[Document context not available]"

        try:
            import time

            # Delay to allow document indexing in Albert
            # (Search may take time to index newly uploaded documents)
            time.sleep(2.0)

            # Use several broad search queries to capture different aspects
            search_queries = [
                "principaux points",
                "concepts clés",
                "objectifs",
                "informations",
                "contenu",
            ]

            passages = []
            for query in search_queries:
                try:
                    results = self.albert_client.search(
                        prompt=query,
                        collections=[self.collection_id],
                        limit=2,
                    )
                    # SearchResponse has a .data attribute
                    result_list = results.data if hasattr(results, "data") else results
                    if result_list:
                        for result in result_list:
                            # Results can be dicts or objects
                            text = (
                                result.get("text", "")
                                if isinstance(result, dict)
                                else getattr(result, "text", "")
                            )
                            if not text:
                                text = (
                                    result.get("content", "")
                                    if isinstance(result, dict)
                                    else getattr(result, "content", "")
                                )
                            if text and text not in passages:
                                passages.append(text[:500])  # Limit passage length
                except Exception as e:
                    logger.debug(f"Search for '{query}' failed: {e}")
                    continue

            if passages:
                context = "\n\n---\n\n".join(passages[:5])  # Max 5 passages
                return f"Sample passages from the document:\n\n{context}"
            else:
                return (
                    "A document has been uploaded to the collection. "
                    "Please generate Q/A pairs based on the document content, "
                    "ensuring each answer is grounded in the uploaded material."
                )

        except Exception as e:
            logger.warning(f"Failed to retrieve document context: {e}")
            return "[Document context retrieval failed. Proceeding without context.]"

    def _build_prompt(self, num_samples: int, document_context: str) -> str:
        """Build the generation prompt for the LLM with document context.

        Args:
            num_samples: Number of Q/A pairs to generate
            document_context: Sample passages from the document to ground generation

        Returns:
            The formatted prompt string
        """
        return f"""You are helping generate a synthetic evaluation dataset from a document.

DOCUMENT CONTEXT:
{document_context}

TASK:
Generate {num_samples} Question/Answer pairs (Q&A) based ONLY on the document context provided above.

REQUIREMENTS:
- All questions and answers MUST be in French
- Each answer must be grounded in and directly supported by the document passages shown
- Create diverse questions covering different aspects of the document
- For each Q&A pair, include the exact document passage that supports the answer

OUTPUT FORMAT:
Generate exactly {num_samples} JSON objects, one per line (JSONL format). Each object must have this structure:
{{
  "user_input": "Question in French?",
  "retrieved_contexts": ["The exact document passage supporting this answer"],
  "reference": "Answer in French, supported by the context above",
  "_metadata": {{
    "source_file": "document.pdf",
    "quality_score": 0.85,
    "topic_summary": "Brief topic description"
  }}
}}

Output ONLY the JSON lines with no additional text, explanations, or preamble. Start directly with the first JSON object.
Generate exactly {num_samples} Q&A pairs."""

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
