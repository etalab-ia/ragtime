"""Albert API provider for Data Foundry.

Uses Albert API (OpenGateLLM) with hybrid search for document retrieval
and OpenAI-compatible LLM for Q/A generation.
"""

import json
from collections.abc import Iterator
from datetime import datetime, timezone

try:
    import requests
except ImportError as e:
    raise ImportError(
        "requests package is required. Install with: uv add requests"
    ) from e

try:
    from openai import OpenAI
except ImportError as e:
    raise ImportError("openai package is required. Install with: uv add openai") from e

from .schema import GeneratedSample


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

        # Initialize OpenAI client for Albert API
        self.llm_client = OpenAI(api_key=api_key, base_url=self.base_url)

        # Track resources for cleanup
        self.collection_id: str | None = None

    def upload_documents(self, document_paths: list[str]) -> None:
        """Upload documents to Albert and create a collection.

        Args:
            document_paths: List of paths to documents (PDF, MD, TXT)
        """
        # Create a collection
        collection_name = (
            f"data_foundry_{datetime.now(timezone.utc).strftime('%Y%m%d_%H%M%S')}"
        )

        collection_data = {
            "name": collection_name,
            "description": "RAG Facile Data Foundry",
        }
        response = requests.post(
            f"{self.base_url}/v1/collections",
            json=collection_data,
            headers={"Authorization": f"Bearer {self.api_key}"},
        )
        response.raise_for_status()
        collection_response = response.json()
        self.collection_id = collection_response.get("id")

        if not self.collection_id:
            raise ValueError("Failed to create collection: no ID in response")

        # Upload each document
        for doc_path in document_paths:
            with open(doc_path, "rb") as f:
                files = {"file": (doc_path, f)}
                doc_response = requests.post(
                    f"{self.base_url}/v1/documents",
                    files=files,
                    data={"collection_id": self.collection_id},
                    headers={"Authorization": f"Bearer {self.api_key}"},
                )
                doc_response.raise_for_status()

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

        # Stream the response from LLM
        # The LLM will be responsible for calling search internally
        seen_samples: set[str] = set()
        buffer = ""

        try:
            stream = self.llm_client.chat.completions.create(
                model=self.model,
                messages=[{"role": "user", "content": prompt}],
                stream=True,
            )

            for chunk in stream:
                if chunk.choices and chunk.choices[0].delta.content:
                    content = chunk.choices[0].delta.content
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
        except Exception as e:
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
        """Delete collection from Albert API."""
        if self.collection_id:
            try:
                requests.delete(
                    f"{self.base_url}/v1/collections/{self.collection_id}",
                    headers={"Authorization": f"Bearer {self.api_key}"},
                )
            except Exception:
                pass  # Non-critical

    def _build_prompt(self, num_samples: int) -> str:
        """Build the generation prompt for the LLM.

        The prompt instructs the LLM to:
        1. Use the hybrid search API to find relevant contexts
        2. Generate Q/A pairs from those contexts
        3. Return results in JSON format
        """
        return f"""You are a Q/A dataset generator for French government documents.

Your task: Generate {num_samples} high-quality Question/Answer pairs in French.

For each Q/A pair, you MUST:
1. Use the hybrid search API to retrieve relevant document passages
   - Call: POST {self.base_url}/v1/search
   - Body: {{"query": "<your-query>", "collection_id": "{self.collection_id}", "limit": 5}}
   - Merge results from semantic and keyword search
2. Create questions that are answerable from the retrieved contexts
3. Answers must be grounded in the actual document text

Requirements:
- Questions and answers MUST be in French
- Each answer must cite specific text from the documents
- Ensure diversity - avoid similar questions about the same topics
- Return each Q/A pair as JSON on its own line (JSONL format)

Return format (one JSON object per line):
{{
  "user_input": "Question in French?",
  "retrieved_contexts": ["Exact passage from document...", "Another relevant passage..."],
  "reference": "Complete answer in French, grounded in the context.",
  "_metadata": {{
    "source_file": "document_name.pdf",
    "quality_score": 0.95,
    "topic_summary": "Brief topic for diversity tracking"
  }}
}}

Generate {num_samples} Q/A pairs now. Output each as a complete JSON object on its own line."""

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
