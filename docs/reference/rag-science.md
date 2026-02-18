# RAG Science: Contributor Reference

This reference maps each rag-facile pipeline phase against state-of-the-art research (2024–2026), documents known capability gaps, and provides a prioritised roadmap for contributors. Each section links to the key papers.

> For a non-technical introduction see [The Science Behind rag-facile](../guides/how-rag-works.md).  
> For stage-by-stage configuration see [Understanding the RAG Pipeline](../guides/rag-pipeline.md).

---

## Overview

A production RAG system for French government applications must optimise three competing constraints simultaneously:

1. **Accuracy** — precise retrieval, low hallucination rate, verifiable citations
2. **Sovereignty** — open-weight models, on-premise deployment, RGPD compliance
3. **Cost** — sub-second latency at <€0.01/query for sustainable public service scale

rag-facile is deliberately modular: every phase below can be upgraded independently. The roadmap at the end of this document prioritises changes by impact and effort.

---

## Phase 1 — Ingestion

**Current implementation**: Marker + Albert parse API (PDF, HTML, Markdown)

### State of the art

The dominant pattern in 2024–2025 is **Markdown as the universal intermediate format**: every input type (PDF, DOCX, PPTX, HTML) is converted to clean Markdown before chunking. This produces 12–18% better retrieval consistency than format-specific processing paths.

| Parser | Table accuracy | Speed | Cost | Licence |
|--------|---------------|-------|------|---------|
| **[Docling](https://github.com/DS4SD/docling)** (IBM, 2024) | 97.9% | 30× faster than OCR | Free | MIT |
| **[olmOCR](https://huggingface.co/allenai/olmOCR-7B-0225-preview)** (AllenAI, Feb 2025) | SOTA scanned docs | ~30 pages/sec | $176/1M pages | Apache 2.0 |
| Marker (current) | Good | Moderate | Free | GPL-3.0 |

**Multimodal gap**: OpenRAG implements VLM image captioning (moondream/LLaVA) and Whisper transcription for audio. rag-facile currently ignores embedded images.

### Upgrade priorities

| Upgrade | Impact | Effort |
|---------|--------|--------|
| Docling for PDFs with complex tables | +15–25% table accuracy | Medium |
| Markdown normalisation layer | +5–10% downstream consistency | Low |
| VLM image captioning | +8–12% on diagram-heavy documents | High |

---

## Phase 2 — Chunking

**Current implementation**: Albert server-side fixed chunking — `chunk_size=1024`, `overlap=100`

### State of the art

A widely-cited 2024 benchmark ([arXiv:2410.13070](https://arxiv.org/abs/2410.13070)) found that **fixed-size chunking with moderate overlap achieves 98% of semantic chunking quality at 0.01× the computational cost**. Over-engineering this phase rarely pays off.

| Strategy | Recall gain | Storage cost | Best for |
|----------|------------|-------------|----------|
| Fixed-size (current) | baseline | 1× | General text |
| **Late chunking** — Jina AI, 2024 | +7–12% | 1× | Multi-hop queries |
| **Proposition indexing** — Dense X Retrieval ([arXiv:2312.06648](https://arxiv.org/abs/2312.06648)) | +17–25% | 3–5× | Factoid QA |
| **RAPTOR** hierarchical summaries ([arXiv:2401.18059](https://arxiv.org/abs/2401.18059)) | +20% | 2× | Long-doc reasoning |

Late chunking (embed the full document first, then split the embeddings) preserves cross-boundary context without extra storage. Proposition indexing decomposes text into atomic factoids before indexing — highest recall gains, but significant storage overhead.

**French administrative text**: Article-level boundary detection improves coherence by 8–15% on legal corpora.

---

## Phase 3 — Embedding

**Current implementation**: `openweight-embeddings` via Albert API (proprietary model details not public)

### State of the art

**RTEB (Retrieval Task Evaluation Benchmark)** replaced MTEB as the key benchmark for production retrieval in early 2026. Unlike MTEB, RTEB is industry-oriented — it tests on real enterprise verticals including **French legal document retrieval** — and uses private datasets to prevent overfitting.

#### RTEB Leaderboard (January 2026)

| Model | RTEB score | Context window | French legal | Licence |
|-------|-----------|---------------|-------------|---------|
| **[Octen-Embedding-8B](https://huggingface.co/Octen/Octen-Embedding-8B)** | **0.8045** 🥇 | 32 768 | ✅ Explicit | Apache 2.0 |
| [Octen-Embedding-4B](https://huggingface.co/Octen/Octen-Embedding-4B) | 0.7834 | 32 768 | ✅ | Apache 2.0 |
| voyage-3-large | 0.7812 | 32 000 | ✅ | Commercial |
| Qwen3-Embedding-8B | 0.7547 | 32 768 | ✅ | Non-commercial |
| multilingual-e5-large-instruct | 0.6097 | 512 | ✅ 100 langs | MIT |
| BGE-M3 | 0.5893 | 8 192 | ✅ | Apache 2.0 |

See the full [Octen technical blog post](https://octen-team.github.io/octen_blog/posts/octen-rteb-first-place/) for training methodology (LoRA on Qwen3, hard-negative mining, multi-positive utilisation, cross-device negative sharing). Note: Octen raised a [fairness concern](https://github.com/embeddings-benchmark/mteb/issues/3902) about unequal access to RTEB's private datasets — treat benchmark scores as directional until resolved.

#### Other notable models

- **[multilingual-e5-large-instruct](https://huggingface.co/intfloat/multilingual-e5-large-instruct)** ([arXiv:2402.05672](https://arxiv.org/abs/2402.05672)) — MIT licence, 100 languages, proven production baseline
- **[CamemBERT 2.0](https://huggingface.co/almanach/camembertav2-base)** ([arXiv:2411.08868](https://arxiv.org/abs/2411.08868), Nov 2024) — French-only, DeBERTaV3 architecture, strong on legal/administrative text
- **MMTEB** ([arXiv:2502.13595](https://arxiv.org/abs/2502.13595), Feb 2025) — 500+ tasks, 250+ languages; complements RTEB for academic evaluation

#### Efficiency: Matryoshka Representation Learning (MRL)

MRL ([arXiv:2205.13147](https://arxiv.org/abs/2205.13147)) trains a single embedding to be valid at multiple dimensionalities. Truncating from 1024d to 512d combined with int8 quantisation delivers **8× storage and speed reduction with <2% accuracy loss** — critical for cost-efficient sovereign deployment.

#### ColBERT late interaction

ColBERT v2 ([arXiv:2112.01488](https://arxiv.org/abs/2112.01488)) stores per-token embeddings (rather than a single vector per chunk) and scores with a MaxSim operation. This gives **+5–15% recall vs bi-encoders** on BEIR benchmarks, at 10–100× the storage cost. Best suited to high-precision legal search where storage budget allows.

---

## Phase 4 — Storage

**Current implementation**: Albert collections (proprietary hosted vector store)

### State of the art

| Database | P95 latency | Native hybrid search | Sovereign | Licence |
|----------|------------|---------------------|-----------|---------|
| **[Qdrant](https://qdrant.tech)** | 30–40 ms | ✅ (v1.10+) | ✅ self-host | Apache 2.0 |
| [Weaviate](https://weaviate.io) | 50–70 ms | ✅ | ✅ self-host | BSD-3 |
| [Milvus](https://milvus.io) | 40–60 ms | ⚠️ partial | ✅ self-host | Apache 2.0 |
| pgvector (PostgreSQL) | 60–100 ms | ❌ manual | ✅ self-host | PostgreSQL |
| Pinecone | 40–50 ms | ✅ | ❌ cloud-only | Proprietary |

**HNSW production defaults**: `M=16`, `ef_construction=200`. Int8 quantisation gives 4× storage reduction at <3% recall loss and is natively supported by Qdrant, Milvus, and Weaviate.

**RGPD isolation**: Collection-per-organisation provides strong data separation in multi-tenant government deployments.

**Recommendation**: Qdrant for sovereign self-hosted deployments; Albert collections remain convenient for teams using Albert's hosted infrastructure exclusively.

---

## Phase 5 — Query Processing

**Current implementation**: ❌ No preprocessing — raw query sent directly to retrieval

This is **the largest single quality gap** in rag-facile. Unprocessed queries miss 15–30% of relevant documents due to vocabulary mismatch between informal user language and formal document vocabulary.

### State of the art

| Technique | Accuracy gain | Added latency | Key reference |
|-----------|--------------|--------------|---------------|
| **HyDE** | +12–18% | 800–1 500 ms | [arXiv:2212.10496](https://arxiv.org/abs/2212.10496) |
| Step-back prompting | +8–12% | 500–800 ms | [arXiv:2310.06117](https://arxiv.org/abs/2310.06117) |
| Multi-query + RRF | +3–7% | ~600 ms | — |
| LLM query rewriting | +2–5% | 200–500 ms | — |

**HyDE (Hypothetical Document Embeddings)**: The model generates a hypothetical answer to the user's question, then uses the *embedding of that answer* — rather than the question itself — to retrieve documents. Because the hypothetical answer uses document-like vocabulary, semantic similarity improves dramatically. Especially effective for French administrative queries, where users ask informally ("combien je touche ?") while documents use formal vocabulary ("montant des prestations versées").

**French-specific preprocessing**: Abbreviation expansion is critical — 30–40% of government queries contain administrative acronyms (CAF, URSSAF, CADA, DILA) that may not appear verbatim in documents.

---

## Phase 6 — Retrieval

**Current implementation**: Albert hybrid search (BM25 + semantic + Reciprocal Rank Fusion) ✅

### State of the art

Hybrid search is the production standard. BM25 + dense + RRF consistently outperforms pure semantic search by **15–30%** on BEIR and MS MARCO benchmarks. BM25 is irreplaceable for exact French term matching: legal article numbers ("Article L3141-1"), agency names, and administrative codes.

**Optimal `top_k`**: Retrieve 50–100 candidates for the reranking stage. Sending more than 20 chunks to the LLM context degrades quality due to the lost-in-the-middle effect (see Phase 8).

**Advanced**: FLARE (Forward-Looking Active REtrieval, [arXiv:2305.06983](https://arxiv.org/abs/2305.06983)) triggers retrieval only when the model expresses uncertainty mid-generation. Reduces retrieval cost while maintaining quality on conversational pipelines.

---

## Phase 7 — Reranking

**Current implementation**: `BAAI/bge-reranker-v2-m3` via Albert API alias `openweight-rerank` ✅

**Reranking is the highest-ROI single optimisation in a RAG pipeline: +30–40% precision at ~150 ms P50.**

### State of the art

| Reranker | Accuracy gain vs retrieval-only | Context length | Licence |
|----------|--------------------------------|---------------|---------|
| **[BGE-reranker-v2-m3](https://huggingface.co/BAAI/bge-reranker-v2-m3)** (current — `openweight-rerank`) | +32–42% | 8 192 | MIT |
| [Alibaba GTE-multilingual](https://huggingface.co/Alibaba-NLP/gte-multilingual-reranker-base) | +35–45% | 8 192 | Apache 2.0 |
| RankGPT (LLM-based listwise) | +45–55% | 32 000+ | Proprietary API |

**Optimal funnel**: Retrieve 100 → rerank 50 → return top 5–7 to the LLM. French text is 15–20% longer than English, making the 8 192-token context window of GTE-multilingual important for administrative documents.

**LLM-based rerankers** (RankGPT and variants) provide higher accuracy but at 10–50× the cost of cross-encoder rerankers. Reserve for premium tiers or legal research use cases.

---

## Phase 8 — Context Assembly

**Current implementation**: Basic assembly with citations 🔶

### State of the art

**Lost-in-the-middle effect** ([arXiv:2307.03172](https://arxiv.org/abs/2307.03172)): LLMs have U-shaped attention — they attend most strongly to content at the beginning and end of their context window, least to the middle. The most relevant chunk should always be placed **first**; the second-most relevant **last**. This ordering alone can improve answer accuracy by 5–12%.

**Context compression**: [LLMLingua](https://github.com/microsoft/LLMLingua) ([arXiv:2310.05736](https://arxiv.org/abs/2310.05736)) uses a small language model to identify and remove low-information tokens, achieving up to 20× compression with minimal accuracy loss. The practical sweet spot for French administrative RAG is 4–8 K tokens in context.

**Deduplication**: When the same passage is retrieved by both BM25 and semantic search, it should appear only once in the assembled context.

---

## Phase 9 — Generation

**Current implementation**: Albert `openweight-medium` 🔶

### State of the art

**Temperature**: `T=0.2` for factual administrative RAG; `T=0.0` for strict citation mode. Higher temperatures increase creativity at the expense of factual consistency.

**System prompt design** is the highest-leverage, lowest-effort intervention available. Three instructions reduce hallucination by ~37% on RAG benchmarks:

1. "Answer only from the context provided."
2. "Cite every claim with a numbered reference [1], [2]…"
3. "If the answer is not in the context, say 'I don't know'."

**Multi-turn query contextualisation**: In a conversation, follow-up questions ("what about exceptions?") lose their context outside the dialogue. Rewriting each follow-up as a standalone question before retrieval — a technique called Dense Conversational Retrieval — improves multi-turn accuracy by +14% and reduces hallucination by 37%.

---

## Phase 10 — Hallucination Detection

**Current implementation**: ❌ Not implemented — critical safety gap

### State of the art

| Method | F1 on hallucination detection | Latency | Licence |
|--------|------------------------------|---------|---------|
| **[HHEM-2.1-Open](https://huggingface.co/vectara/hallucination_evaluation_model)** (Vectara) | 0.87 | ~50 ms | Apache 2.0 |
| SelfCheckGPT-NLI ([arXiv:2303.08896](https://arxiv.org/abs/2303.08896)) | 0.79 | 200–400 ms | MIT |
| GPT-3.5-as-judge | 0.81 | 500–800 ms | Proprietary |

**HHEM-2.1-Open**: A 100 M parameter NLI model trained specifically for hallucination detection. Outperforms GPT-3.5 on factual consistency benchmarks and runs in ~50 ms on CPU. Apache 2.0 licence.

**Recommended thresholds**: Factual Consistency Score (FCS) < 0.5 → surface a warning to the user; FCS < 0.3 → refuse to answer, return "I don't know".

**Corrective RAG (CRAG)** ([arXiv:2401.15884](https://arxiv.org/abs/2401.15884)): Evaluates retrieval confidence at query time and falls back to a web search if confidence is too low. Addresses cases where your document corpus simply doesn't contain the answer.

**Citation-enforced generation** (LongCite, [arXiv:2406.12931](https://arxiv.org/abs/2406.12931)): Fine-tunes the generative model itself to produce inline sentence-level citations. Achieves ~90% citation accuracy and structurally reduces unsupported claims.

---

## Priority Upgrade Roadmap

### Phase A — Quick wins (1–2 weeks, estimated +25–35% quality, –30% hallucination risk)

All of these are low-effort, high-signal changes:

1. **HyDE query preprocessing** — single LLM call before retrieval: +12–18% recall ([arXiv:2212.10496](https://arxiv.org/abs/2212.10496))
2. **Lost-in-the-middle reordering** — best chunk first, second-best last: +5–12% ([arXiv:2307.03172](https://arxiv.org/abs/2307.03172))
3. **Optimise system prompt** — strict citations + "I don't know" fallback: –25–37% hallucination
4. **HHEM-2.1-Open integration** — hallucination faithfulness gate: critical safety improvement
5. **French abbreviation expansion** — CAF, URSSAF, CADA dictionary: +8–12% on government queries
6. **Temperature T=0.2** — factual consistency default

### Phase B — Sovereign stack (3–6 weeks, cost and compliance)

1. **Qdrant self-hosted** — full data sovereignty, RGPD audit transparency
2. **Octen-Embedding-8B integration** — best-in-class French legal embeddings, Apache 2.0
3. **Collection-per-organisation architecture** — multi-tenant data isolation
4. **Int8 quantisation** — 4× storage and infrastructure cost reduction

### Phase C — Advanced quality (6–12 weeks, estimated +20–30% additional quality)

1. **Late chunking** — embed-then-split context preservation: +7–12%
2. **Multi-query + RRF** — query expansion for ambiguous questions: +3–7%
3. **LLMLingua context compression** — 2–4× cost reduction on generation ([arXiv:2310.05736](https://arxiv.org/abs/2310.05736))
4. **Multi-turn query contextualisation** — conversation accuracy: +14%
5. **Docling integration** — complex PDF table extraction: +15–25% on structured documents

### Phase D — Agentic (3–6 months)

1. **RAPTOR hierarchical indexing** — long-document reasoning: +20% ([arXiv:2401.18059](https://arxiv.org/abs/2401.18059))
2. **CRAG with web fallback** — dynamic retrieval correction when corpus is insufficient: +12–18% ([arXiv:2401.15884](https://arxiv.org/abs/2401.15884))
3. **VLM image captioning** — multimodal document understanding
4. **MCP tool integration + ReAct orchestration** (LangGraph) — agentic workflows

---

## Evaluation

Use **[Inspect AI](https://github.com/UKGovernmentBEIS/inspect_ai)** (UK AISI, MIT licence) as the evaluation orchestration framework. Route the judge to Albert for zero incremental cost:

```python
from inspect_ai import eval, Task
from inspect_ai.scorer import model_graded_qa

task = Task(
    dataset="french_gov_qa_benchmark",   # 500+ curated Q&A pairs
    plan=[rag_pipeline_solver()],
    scorer=model_graded_qa(
        model="openai/openweight-medium",  # Albert via OpenAI-compatible endpoint
        template=FRENCH_RAG_GRADING_TEMPLATE,
    ),
)
results = eval(task)
```

**Tiered scoring strategy**:

| Tier | Tool | Cost | Use when |
|------|------|------|----------|
| 0 | F1 / ROUGE / exact match | Free | Regression gate on every PR |
| 1 | HHEM-2.1-Open | Free | Hallucination rate on every PR |
| 2 | Albert-as-judge | Zero incremental | Weekly quality report |
| 3 | RAGAS with Albert backend | Low | Deep quality analysis |
| 4 | Human evaluation | High | Quarterly gold benchmark |

**Target metrics**: >80% accuracy on French government Q&A benchmark · <5% hallucination rate (HHEM) · <2 s P95 end-to-end latency · >85% citation precision.

---

## Key Papers

| Topic | Paper | Link |
|-------|-------|------|
| Original RAG | Lewis et al., 2020 | [arXiv:2005.11401](https://arxiv.org/abs/2005.11401) |
| HyDE — hypothetical document embeddings | Gao et al., 2022 | [arXiv:2212.10496](https://arxiv.org/abs/2212.10496) |
| Lost-in-the-middle — context position effects | Liu et al., 2023 | [arXiv:2307.03172](https://arxiv.org/abs/2307.03172) |
| RAPTOR — hierarchical summarisation | Sarthi et al., 2024 | [arXiv:2401.18059](https://arxiv.org/abs/2401.18059) |
| CRAG — corrective RAG | Yan et al., 2024 | [arXiv:2401.15884](https://arxiv.org/abs/2401.15884) |
| Self-RAG — reflection tokens | Asai et al., 2023 | [arXiv:2310.11511](https://arxiv.org/abs/2310.11511) |
| FLARE — active retrieval | Jiang et al., 2023 | [arXiv:2305.06983](https://arxiv.org/abs/2305.06983) |
| LongCite — citation-enforced generation | Zhang et al., 2024 | [arXiv:2406.12931](https://arxiv.org/abs/2406.12931) |
| Fixed vs semantic chunking | The Impact of Chunking Strategies on Retrieval-Augmented Generation Performance | [arXiv:2410.13070](https://arxiv.org/abs/2410.13070) |
| Dense X Retrieval — proposition indexing | Chen et al., 2023 | [arXiv:2312.06648](https://arxiv.org/abs/2312.06648) |
| LLMLingua — context compression | Jiang et al., 2023 | [arXiv:2310.05736](https://arxiv.org/abs/2310.05736) |
| Step-back prompting | Zheng et al., 2023 | [arXiv:2310.06117](https://arxiv.org/abs/2310.06117) |
| Matryoshka Representation Learning | Kusupati et al., 2022 | [arXiv:2205.13147](https://arxiv.org/abs/2205.13147) |
| ColBERT v2 — late interaction | Santhanam et al., 2021 | [arXiv:2112.01488](https://arxiv.org/abs/2112.01488) |
| Multilingual E5 | Wang et al., 2024 | [arXiv:2402.05672](https://arxiv.org/abs/2402.05672) |
| MTEB-French benchmark | Ciancone et al., 2024 | [arXiv:2405.20468](https://arxiv.org/abs/2405.20468) |
| CamemBERT 2.0 | Martin et al., 2024 | [arXiv:2411.08868](https://arxiv.org/abs/2411.08868) |
| MMTEB — 250-language benchmark | Kerboua et al., 2025 | [arXiv:2502.13595](https://arxiv.org/abs/2502.13595) |
| SelfCheckGPT — sampling-based faithfulness | Manakul et al., 2023 | [arXiv:2303.08896](https://arxiv.org/abs/2303.08896) |
| Octen-Embedding-8B — RTEB #1 | Octen Team, Jan 2026 | [Blog post](https://octen-team.github.io/octen_blog/posts/octen-rteb-first-place/) |

---

## Contributing

To propose an improvement to a pipeline phase:

1. **Cite evidence** — link the paper or benchmark supporting the change.
2. **Prototype** — test on the French government Q&A evaluation set (contact maintainers for access).
3. **Measure** — report accuracy delta, latency delta, and cost delta vs the current implementation.
4. **Open a PR** — include Inspect AI evaluation results demonstrating the improvement.

Priority is given to changes in Phase A and Phase B of the roadmap above.
