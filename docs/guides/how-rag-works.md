# The Science Behind rag-facile

> **New to RAG?** Start with [Understanding the RAG Pipeline](rag-pipeline.md) first — it explains what each stage does. This guide explains *why* the specific approaches used by rag-facile are effective.

Modern RAG systems aren't all equal. This page explains the key scientific principles that separate a trustworthy system from one that frequently gives wrong answers — and how rag-facile puts these principles into practice.

---

## 1. Why plain keyword search isn't enough — and why meaning matters

Traditional document search (like Ctrl+F) matches exact words. Ask "what are the leave entitlements?" and it won't find a passage that uses the word *congés* or *vacances* or *rest days*. It only finds your exact phrase.

rag-facile uses **semantic search**: documents are converted into numeric vectors (think of them as coordinates in a vast "meaning space") so that passages with the *same meaning* land near each other, even if they use different words. This is how the system finds "montant des prestations versées" when you ask "how much will I receive?".

**But semantic search alone has a blind spot**: it can miss documents that must match *exactly* — article numbers like "Article L3141-1", agency codes like "URSSAF", or acronyms like "CADA". For these, old-fashioned keyword (BM25) search is irreplaceable.

That is why rag-facile uses **hybrid search** — semantic and keyword simultaneously — and merges results with a technique called Reciprocal Rank Fusion. Research consistently shows hybrid search outperforms either method alone by **15–30%** in answer relevance.

---

## 2. Why retrieving many documents and then filtering down beats retrieving few

Imagine asking a research assistant to find the most relevant page in a 10,000-page archive. You wouldn't ask them to hand you exactly 3 pages directly — you'd ask them to pull 50 candidates, then carefully pick the best 5.

rag-facile does exactly this, in two steps:

1. **Retrieval** (`top_k`): A fast model fetches a broad set of candidate passages (typically 20–100).
2. **Reranking** (`top_n`): A more powerful cross-encoder model re-reads each passage *jointly with your question* and re-scores them to surface the truly relevant ones.

This two-stage funnel matters because the first-stage model is optimised for speed, not precision. The reranker takes its time and dramatically improves accuracy: **+30–40% over retrieval alone**, at the cost of only about 150 milliseconds. The reranker used by rag-facile — [`BAAI/bge-reranker-v2-m3`](https://huggingface.co/BAAI/bge-reranker-v2-m3), available via the Albert API as `openweight-rerank` — supports multiple languages including French and handles the longer sentence structures typical of French administrative text.

---

## 3. Why AI systems still make things up — and how we detect it

Even with perfect retrieval, language models can "hallucinate": they generate plausible-sounding text that isn't actually supported by the retrieved documents. This happens because the model is drawing on everything it was ever trained on, and sometimes that learned knowledge overrides what the retrieved passage actually says.

There are two kinds of hallucination:

- **Contradictory** — the answer directly contradicts the retrieved passage
- **Unsupported** — the answer adds information that isn't in the retrieved passage at all

rag-facile detects these using an automatic **faithfulness score**: a small dedicated model (100 million parameters) checks whether every claim in the answer can be traced back to the sources. If the score falls below a confidence threshold, the system flags the answer — or refuses to answer and says "I don't know" instead.

For government applications where wrong information can have real consequences, this safety layer is essential.

---

## 4. Why citations aren't just cosmetic

Every answer in rag-facile includes numbered citations pointing to the source passages. This is not just a courtesy feature — it is a **structural honesty mechanism**.

When the model is required to cite every claim it makes, it is significantly less likely to fabricate information. If it can't point to a source, it has been instructed not to make the claim. Research shows citation-enforced generation reduces unsupported claims by over 30%.

You can always click through to the source document to verify what the system told you. For administrative decisions, legal interpretations, or policy questions, this traceability is non-negotiable.

---

## 5. The sovereign AI advantage

All of rag-facile's AI processing runs through the **Albert API** — the French government's own sovereign AI infrastructure. Your documents never leave French systems, no queries are logged by third-party providers, and compliance with RGPD is built in by design.

---

## Key takeaways

| Principle | Why it matters |
|-----------|---------------|
| **Hybrid search** (semantic + keyword) | Catches both meaning-based and exact-term matches — 15–30% better than either alone |
| **Two-stage retrieval + reranking** | Precision on the final answer improves by 30–40% vs retrieval alone |
| **Hallucination detection** | Safety layer for high-stakes government information |
| **Mandatory citations** | Every claim is traceable; reduces fabrication structurally |
| **Sovereign infrastructure** | Data stays within French government systems |

---

## Further reading

- [Understanding the RAG Pipeline](rag-pipeline.md) — stage-by-stage walkthrough
- [RAG-Facile Configuration Reference](../reference/ragfacile-toml.md) — how to tune each stage
- For contributors: [RAG Science Reference](../reference/rag-science.md) — full SOTA research with benchmarks and paper links
- [Retrieval-Augmented Generation](https://arxiv.org/abs/2005.11401) — the original RAG paper (Lewis et al., 2020)
