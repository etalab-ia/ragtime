"""Albert API provider for Data Foundry.

Uses Albert API (OpenGateLLM) for document ingestion, search, and Q/A generation.
Leverages the rag_facile pipeline packages (ingestion, storage, retrieval) for
consistency with the main RAG pipeline.
"""

import json
import logging
import time
from collections.abc import Iterator
from pathlib import Path

from .schema import GeneratedSample


logger = logging.getLogger(__name__)


class AlbertApiProvider:
    """Data Foundry provider using Albert API (OpenGateLLM).

    Uses the rag_facile pipeline packages for document processing, storage,
    and retrieval. This ensures consistency with the main RAG pipeline.

    The provider:
    1. Uploads documents to Albert collections (via storage provider)
    2. Searches collections using configured retrieval strategy
    3. Generates Q/A pairs from search results via LLM streaming

    All parameters (chunking, retrieval, generation) come from ragfacile.toml.
    """

    def __init__(self):
        """Initialize the Albert API provider."""
        from rag_facile.core import get_config
        from rag_facile.ingestion import get_provider as get_ingestion_provider
        from rag_facile.storage import get_provider as get_storage_provider

        self.config = get_config()
        self._ingestion = get_ingestion_provider(self.config)
        self._storage = get_storage_provider(self.config)

        # Lazily initialized on first use
        self._client = None
        self.collection_id: int | None = None

    @property
    def client(self):
        """Lazily create Albert client on first use."""
        if self._client is None:
            from albert import AlbertClient

            self._client = AlbertClient()
        return self._client

    def upload_documents(self, document_paths: list[str]) -> None:
        """Upload documents to Albert and create a collection.

        Uses the rag_facile storage provider for Albert collections, which
        respects chunking parameters from ragfacile.toml.

        Args:
            document_paths: List of paths to documents (PDF, MD, HTML)
        """
        logger.info(
            f"Starting document upload to Albert API ({len(document_paths)} documents)"
        )
        for doc_path in document_paths:
            logger.debug(f"  - {doc_path}")

        # Create a collection using the storage provider
        collection_name = f"data_foundry_{int(time.time() * 1000)}"
        self.collection_id = self._storage.create_collection(
            self.client,
            name=collection_name,
            description="RAG Facile Data Foundry",
        )
        logger.info(f"Created Albert collection: {self.collection_id}")

        # Upload documents using the storage provider
        # (which respects config.chunking.chunk_size and chunk_overlap)
        try:
            self._storage.ingest_documents(
                self.client,
                [Path(p) for p in document_paths],
                self.collection_id,
            )
            logger.info(
                f"Ingested {len(document_paths)} documents into collection {self.collection_id}"
            )
        except Exception as e:
            error_msg = f"Failed to ingest documents: {e}"
            logger.error(error_msg)
            raise RuntimeError(error_msg) from e

    def generate(self, num_samples: int) -> Iterator[GeneratedSample]:
        """Generate Q/A samples using retrieval from the collection and LLM.

        Args:
            num_samples: Target number of samples to generate

        Yields:
            GeneratedSample objects as they are generated
        """
        if not self.collection_id:
            raise RuntimeError(
                "No collection ID available. Call upload_documents first."
            )

        # Retrieve sample passages from broad searches to ground the generation prompt
        # (specific chunk IDs for each question will be retrieved during parsing)
        document_context, _ = self._retrieve_document_context()  # noqa: F841

        # Build the generation prompt with document context
        prompt = self._build_prompt(num_samples, document_context)
        logger.debug(f"Generation prompt ({len(prompt)} chars):\n{prompt}\n")

        # Stream the response from LLM
        logger.info(f"Sending prompt to Albert API (collection: {self.collection_id})")
        seen_samples: set[str] = set()
        total_response = ""

        try:
            # Use the eval-specific generation model (openweight-large by default)
            # This is intentionally separate from config.generation.model which
            # controls the RAG pipeline LLM.
            model = self.config.eval.generation_model
            stream = self.client.chat.completions.create(
                model=model,
                messages=[{"role": "user", "content": prompt}],
                stream=True,
            )

            for chunk in stream:
                if chunk.choices and chunk.choices[0].delta.content:
                    total_response += chunk.choices[0].delta.content

            logger.info("Completed Albert generation")
            logger.debug(
                f"Total response ({len(total_response)} chars):\n{total_response}\n"
            )

            # Parse after streaming is complete — handles both single-line JSONL
            # and multi-line pretty-printed JSON objects from the LLM.
            # Each sample will have its own chunk IDs based on searching for that question.
            yield from self._parse_response(total_response, seen_samples)

        except Exception as e:
            logger.error(f"LLM generation failed: {e}", exc_info=True)
            raise RuntimeError(f"LLM generation failed: {e}") from e

    def _parse_response(
        self, response: str, seen_samples: set[str]
    ) -> Iterator[GeneratedSample]:
        """Parse the full LLM response, extracting all valid JSON samples.

        Handles:
        - One JSON object per line (JSONL format)
        - Multi-line pretty-printed JSON objects
        - Markdown code fences (```json ... ```)

        For each sample, searches for that specific question to get chunk IDs
        relevant to that question (not the broad search chunks from generation).
        """
        # Strip markdown code fences wrapping the whole response
        text = response.strip()
        if text.startswith("```"):
            lines = text.split("\n")
            # Drop opening fence (```json or ```) and closing fence (```)
            inner = [
                ln
                for ln in lines[1:]
                if ln.strip() != "```" and ln.strip() != "```json"
            ]
            text = "\n".join(inner)

        # Try line-by-line first (proper JSONL)
        for line in text.splitlines():
            line = line.strip()
            if not line or not line.startswith("{"):
                continue
            try:
                data = json.loads(line)
                if "user_input" in data and "reference" in data:
                    sample = GeneratedSample.from_dict(data)
                    # Search for this specific question to get question-relevant chunk IDs
                    chunk_ids = self._search_for_chunk_ids(sample.user_input)
                    sample.retrieved_chunk_ids = [str(cid) for cid in chunk_ids]
                    if sample.user_input not in seen_samples:
                        seen_samples.add(sample.user_input)
                        yield sample
            except json.JSONDecodeError:
                pass

        # If nothing found, try to extract all JSON objects via brace matching
        if not seen_samples:
            yield from self._extract_json_objects(text, seen_samples)

    def _search_for_chunk_ids(self, question: str) -> list[int]:
        """Search the collection for chunks relevant to a specific question.

        Returns:
            List of chunk IDs from the search results for this question
        """
        if not self.collection_id:
            return []

        try:
            from rag_facile.retrieval import search_chunks

            chunks = search_chunks(
                self.client,
                question,
                [self.collection_id],
                limit=self.config.retrieval.top_k,
                method=self.config.retrieval.strategy,
                score_threshold=self.config.retrieval.score_threshold,
            )
            return [
                chunk.get("chunk_id", 0) for chunk in chunks if chunk.get("chunk_id")
            ]
        except Exception as e:
            logger.debug(f"Failed to search for chunk IDs for question: {e}")
            return []

    def _extract_json_objects(
        self,
        text: str,
        seen_samples: set[str],
    ) -> Iterator[GeneratedSample]:
        """Extract JSON objects from text using brace depth tracking."""
        depth = 0
        start = -1
        for i, ch in enumerate(text):
            if ch == "{":
                if depth == 0:
                    start = i
                depth += 1
            elif ch == "}":
                depth -= 1
                if depth == 0 and start != -1:
                    candidate = text[start : i + 1]
                    try:
                        data = json.loads(candidate)
                        if "user_input" in data and "reference" in data:
                            sample = GeneratedSample.from_dict(data)
                            # Search for this specific question to get question-relevant chunk IDs
                            chunk_ids = self._search_for_chunk_ids(sample.user_input)
                            sample.retrieved_chunk_ids = [str(cid) for cid in chunk_ids]
                            if sample.user_input not in seen_samples:
                                seen_samples.add(sample.user_input)
                                yield sample
                    except json.JSONDecodeError:
                        pass
                    start = -1

    def cleanup(self) -> None:
        """Delete collection from Albert API."""
        if self.collection_id:
            try:
                self._storage.delete_collection(self.client, self.collection_id)
            except Exception:
                pass  # Non-critical

    def _retrieve_document_context(self) -> tuple[str, list[int]]:
        """Retrieve sample passages and chunk IDs from the collection.

        Uses the rag_facile retrieval package with configured search strategy
        to get representative passages from the uploaded documents.

        Returns:
            tuple of (formatted_context_string, list_of_chunk_ids)
            where chunk_ids are the IDs of chunks used in the context
        """
        if not self.collection_id:
            return "[Document context not available]", []

        try:
            from rag_facile.retrieval import search_chunks

            # Delay to allow document indexing in Albert (PDF parsing takes ~5s)
            time.sleep(5.0)

            # Use several broad search queries to capture different aspects
            search_queries = [
                "principaux points",
                "concepts clés",
                "objectifs",
                "informations",
                "contenu",
            ]

            passages = []
            chunk_ids = []
            for query in search_queries:
                try:
                    # Use the retrieval package with configured strategy
                    chunks = search_chunks(
                        self.client,
                        query,
                        [self.collection_id],
                        limit=2,
                        method=self.config.retrieval.strategy,
                        score_threshold=self.config.retrieval.score_threshold,
                    )

                    if chunks:
                        for chunk in chunks:
                            # RetrievedChunk TypedDicts use 'content' and 'chunk_id' keys
                            text = chunk.get("content", "")
                            cid = chunk.get("chunk_id")
                            if text and text not in passages:
                                passages.append(text[:500])  # Limit passage length
                                if cid is not None:
                                    chunk_ids.append(cid)
                except Exception as e:
                    logger.debug(f"Search for '{query}' failed: {e}")
                    continue

            if passages:
                context = "\n\n---\n\n".join(passages[:5])  # Max 5 passages
                return (
                    f"Sample passages from the document:\n\n{context}",
                    chunk_ids[:5],
                )
            else:
                return (
                    "A document has been uploaded to the collection. "
                    "Please generate Q/A pairs based on the document content, "
                    "ensuring each answer is grounded in the uploaded material.",
                    [],
                )

        except Exception as e:
            logger.warning(f"Failed to retrieve document context: {e}")
            return (
                "[Document context retrieval failed. Proceeding without context.]",
                [],
            )

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
