---
name: tune-pipeline
description: Change or tune configuration parameters (top_k, top_n, chunk_size, preset, model…). Use when the user wants to SET or ADJUST a specific value.
triggers: ["tune", "optimize", "améliorer", "improve", "preset", "slower", "faster", "top_k", "top_n", "chunk", "mets", "set", "change", "modifier", "augmenter", "diminuer"]
---

# Skill: Tune Pipeline

You are helping the user pick the right preset and fine-tune their pipeline parameters.

## Step 1 — Understand their goal
Ask ONE of these depending on what they said:
- "Vous cherchez à améliorer la qualité des réponses, ou la vitesse ?"
- "Quel type de documents traitez-vous ? (PDF juridiques, articles, documentation technique...)"

## Step 2 — Read their current config
Call `run_rag_facile("config show --format json")`. Note the active preset and any overrides.

## Step 3 — Recommend a preset
| Use case | Recommended preset | Why |
|----------|--------------------|-----|
| General purpose | `balanced` | Good speed/quality trade-off |
| Best quality, speed secondary | `accurate` | Larger chunks, multi-query expansion |
| Fast prototyping | `fast` | Minimal reranking overhead |
| Legal / regulatory texts | `legal` | Tuned for long precise passages |
| HR / policy documents | `hr` | Public collections pre-configured |

## Step 4 — Explain the key levers
Only mention the parameters relevant to their symptom:
- **Speed slow?** → lower `top_k`, disable `reranking`, try `fast` preset
- **Answers vague?** → raise `top_n`, enable `multi_query` expansion
- **Missing context?** → raise `chunk_size` or `chunk_overlap`
- **Irrelevant results?** → lower `top_k`, raise reranking `top_n`

## Step 5 — Propose and confirm ONE change at a time
Explain the change and its tradeoff, then ask explicitly:
"Puis-je effectuer ce changement ? Il sera enregistré dans ragfacile.toml et committé dans git."

Wait for an explicit "oui" / "yes" reply, THEN call `run_rag_facile("config set <key> <value>")`.
Never change config without this confirmation exchange.

Use `get_docs("config")` to cite exact field names from the reference documentation.
