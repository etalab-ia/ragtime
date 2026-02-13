# Understanding the RAG Pipeline

This guide explains what happens under the hood when your RAG application answers a question. Each stage of the pipeline is a knob you can tune in [`ragfacile.toml`](../reference/ragfacile-toml.md).

## What is RAG?

**Retrieval-Augmented Generation (RAG)** is a technique that improves AI-generated answers by first *retrieving* relevant documents, then feeding them as context to a language model. Instead of relying solely on what the model was trained on, it grounds its answers in your actual data.

This matters for government applications: answers must be accurate, sourced, and traceable.

> For a broader introduction, see [Retrieval-Augmented Generation](https://en.wikipedia.org/wiki/Retrieval-augmented_generation) on Wikipedia.

## The Pipeline at a Glance

```
Your Documents                              User's Question
     │                                            │
     ▼                                            ▼
┌──────────┐                               ┌───────────┐
│ Ingestion│                               │   Query   │
│ (parse)  │                               │Enhancement│
└────┬─────┘                               └─────┬─────┘
     ▼                                            ▼
┌──────────┐                               ┌───────────┐
│ Chunking │                               │ Retrieval │◄── Vector Store
│ (split)  │                               │ (search)  │
└────┬─────┘                               └─────┬─────┘
     ▼                                            ▼
┌──────────┐                               ┌───────────┐
│Embedding │                               │ Reranking │
│(vectorize)│                              │ (refine)  │
└────┬─────┘                               └─────┬─────┘
     ▼                                            ▼
┌──────────┐                               ┌───────────┐
│ Storage  │──────────────────────────────►│  Context  │
│ (index)  │                               │ (assemble)│
└──────────┘                               └─────┬─────┘
                                                  ▼
                                           ┌───────────┐
                                           │Generation │
                                           │  (answer) │
                                           └─────┬─────┘
                                                  ▼
                                           ┌───────────┐
                                           │Hallucin.  │
                                           │ (verify)  │
                                           └─────┬─────┘
                                                  ▼
                                           ┌───────────┐
                                           │Formatting │
                                           │ (present) │
                                           └───────────┘
```

The left side happens **once** when you load your documents. The right side happens **for every question**.

## Stages Explained

### 1. Ingestion

**What it does**: Reads your raw files (PDF, Markdown, plain text) and converts them into clean, structured text.

**Why it matters**: Garbage in, garbage out. If a scanned PDF isn't OCR-processed correctly, all downstream stages suffer. Good ingestion preserves the document's structure — headings, lists, tables — which helps the model understand context.

**Key choices**: Enable OCR for scanned documents. Higher DPI gives better quality but slower processing.

### 2. Chunking

**What it does**: Splits long documents into smaller pieces (chunks) that fit within model context windows and can be individually indexed.

**Why it matters**: Chunks that are too large dilute the relevant information; chunks that are too small lose context. The strategy matters — `semantic` chunking tries to keep related ideas together, while `fixed-size` is faster.

**Tip**: Start with `semantic` chunking at 512 tokens. Increase `chunk_overlap` if answers seem to miss context that spans chunk boundaries.

### 3. Embedding

**What it does**: Converts each text chunk into a high-dimensional numeric vector (a list of numbers) that captures its meaning.

**Why it matters**: Vectors enable *semantic search* — finding documents by meaning rather than exact keyword matches. "congés annuels" and "vacances" would be close together in vector space even though they share no words.

> For a deeper dive, see [Embedding (machine learning)](https://en.wikipedia.org/wiki/Embedding_(machine_learning)) on Wikipedia.

### 4. Storage

**What it does**: Saves the vectors in an index (vector store) so they can be searched efficiently.

**Why it matters**: The backend choice affects performance, scalability, and features. `albert-collections` is the default for sovereign AI.

### 5. Query Enhancement

**What it does**: Improves the user's question *before* searching. This can include rewriting vague queries, expanding with synonyms, or fixing typos.

**Why it matters**: Users don't always phrase questions optimally. "comment ça marche les RTT?" is harder to match than "Quelles sont les règles de prise des RTT ?". Query enhancement bridges this gap.

**Tip**: Enable for user-facing applications. Disable for evaluation and benchmarks where you want to measure raw retrieval quality.

### 6. Retrieval

**What it does**: Searches the vector store to find the most relevant chunks for the (possibly enhanced) query.

**Why it matters**: This is the core of RAG. The retrieval method determines what information the model sees:

| Method | How it works | Best for |
|--------|-------------|----------|
| **Semantic** | Matches by meaning (vector similarity) | Natural language questions |
| **Lexical** | Matches by keywords (BM25) | Exact terms, codes, acronyms |
| **Hybrid** | Combines both | General use (recommended) |

The `top_k` parameter controls how many chunks are retrieved. More chunks means more context but also more noise.

### 7. Reranking

**What it does**: Takes the initial retrieval results and re-scores them with a more powerful (but slower) model to surface the truly relevant chunks.

**Why it matters**: Retrieval casts a wide net (`top_k` = 10–20); reranking narrows it down to the best (`top_n` = 3–5). This significantly improves precision, especially when `top_k` is large.

**Tip**: Always enable reranking in production. Disable it only for speed-critical prototypes.

### 8. Context Assembly

**What it does**: Selects and organizes the final set of chunks that will be passed to the language model, respecting the token budget.

**Why it matters**: Language models have finite context windows. This stage deduplicates, orders, and formats chunks to maximize information density within the available tokens.

### 9. Generation

**What it does**: Sends the assembled context + the user's question to a language model, which produces the answer.

**Why it matters**: The model choice and temperature directly affect answer quality:
- **Temperature 0.0–0.3**: Deterministic, factual — good for legal/policy
- **Temperature 0.5–0.7**: Balanced — good for general use
- **Temperature 0.8+**: Creative — rarely useful for RAG

The `system_prompt` shapes the model's personality and citation behavior.

### 10. Hallucination Detection

**What it does**: Validates that the generated answer is actually grounded in the retrieved context, not fabricated by the model.

**Why it matters**: For government applications, accuracy is non-negotiable. This stage catches answers that sound plausible but aren't supported by the source documents.

| Method | How it works |
|--------|-------------|
| **citation-check** | Verifies every claim maps to a cited source |
| **fact-check** | Cross-references claims against the context |
| **entailment** | Uses NLI to check if the context logically implies the answer |

### 11. Formatting

**What it does**: Formats the final answer for presentation — Markdown, HTML, or plain text — and optionally appends source citations.

**Why it matters**: Consistent formatting and clear source attribution builds user trust. The `language` setting ensures the response matches the user's language.

## Configuring the Pipeline

Every stage maps to a section in `ragfacile.toml`. To get started quickly, choose a preset:

| Preset | Philosophy | Key tradeoffs |
|--------|-----------|---------------|
| **balanced** | Quality/speed tradeoff | Semantic chunking, hybrid retrieval, reranking on |
| **fast** | Speed-optimized | Fixed-size chunking, semantic-only retrieval, reranking off |
| **accurate** | Quality-optimized | Large models, high top_k, hallucination detection on |
| **legal** | Strict citations | Paragraph chunking, low temperature, reject hallucinations |
| **hr** | Privacy-aware, approachable | Query enhancement on, friendly prompts |

```bash
# Apply a preset
rag-facile config preset apply balanced

# Customize individual settings
rag-facile config set generation.temperature 0.5
```

For the full configuration reference, see [`ragfacile.toml` Reference](../reference/ragfacile-toml.md).

## Further Reading

- [Retrieval-Augmented Generation for Knowledge-Intensive NLP Tasks](https://arxiv.org/abs/2005.11401) — the original RAG paper by Lewis et al.
- [Retrieval-Augmented Generation](https://en.wikipedia.org/wiki/Retrieval-augmented_generation) — Wikipedia overview
- [Embedding (machine learning)](https://en.wikipedia.org/wiki/Embedding_(machine_learning)) — Wikipedia overview of vector embeddings
