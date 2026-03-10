---
name: explain-rag
description: Explain any RAG concept in plain language, adapted to the user's level.
triggers: ["what is", "explain", "how does", "comment fonctionne", "c'est quoi", "understand", "comprendre"]
---

# Skill: Explain RAG

You are explaining a RAG concept. Adapt your explanation to the user's experience level
(stored in profile.md — new / intermediate / expert).

## For new users — MANDATORY format (no exceptions)

**get_docs() rules:**
- General RAG concepts (chunking, embeddings, retrieval…): DO NOT call `get_docs()`. Answer from knowledge — the docs break this format.
- rag-facile specific facts (config params, CLI commands, presets…): `get_docs()` is allowed to get the facts, but you MUST distill the result into the format below. Never copy the doc structure.

Use this exact structure, nothing else:

1. One plain sentence answering the question — zero jargon.
2. A numbered list of 3–5 steps or ideas in plain language.
3. "Voulez-vous que j'explique l'une de ces étapes en détail ?"
4. A `## Glossaire` section — each term on its own line prefixed with `- `, one plain sentence per entry.

Forbidden: tables, ASCII diagrams, sub-sections, inline definitions.

Example:

---
Le RAG, c'est un système qui cherche les bons passages dans vos documents avant de générer une réponse.

Les grandes étapes :
1. On découpe vos documents en petits extraits.
2. On les indexe pour pouvoir les retrouver rapidement.
3. Quand vous posez une question, on récupère les extraits les plus pertinents.
4. On les donne au modèle de langage pour qu'il rédige la réponse.

Voulez-vous que j'explique l'une de ces étapes en détail ?

## Glossaire
- **Chunk** : un extrait de texte découpé depuis un document.
- **Indexation** : l'opération qui rend les extraits recherchables rapidement.
- **Modèle de langage (LLM)** : le programme qui rédige la réponse finale.
---

## For intermediate users
- Lead with the technical definition, then show how it applies to rag-facile
- Mention the relevant ragfacile.toml parameter if one exists
- One follow-up question about their specific use case

## For expert users
- Direct, precise, no analogies unless asked
- Link to the relevant rag-science reference if applicable

## Key RAG concepts to cover well
- **Chunking**: splitting documents into overlapping segments for embedding
- **Embedding**: converting text to dense vectors for semantic similarity search
- **Retrieval**: finding the top-k most similar chunks to a query
- **Reranking**: re-scoring retrieved chunks with a cross-encoder for precision
- **Context window**: how retrieved chunks are assembled into the LLM prompt
- **RAG vs fine-tuning**: RAG = live knowledge, fine-tuning = baked-in behaviour
- **Hallucination**: when the LLM generates plausible but unfounded content

Use `get_docs("rag")` or `get_docs("science")` to read the actual rag-facile documentation
before answering, so explanations cite real project content rather than generic knowledge.
