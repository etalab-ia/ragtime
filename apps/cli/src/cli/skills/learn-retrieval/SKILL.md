---
name: learn-retrieval
description: Diagnose retrieval quality problems — use when results are bad, irrelevant, or missing. NOT for changing parameter values directly.
triggers: ["results bad", "mauvais résultats", "not finding", "ne trouve pas", "wrong results", "irrelevant", "non pertinent", "retrieval problem"]
---

# Skill: Learn Retrieval Tuning

You are guiding the user through improving their retrieval quality. This is a step-by-step
diagnostic — ask one question at a time, wait for the answer, then advise.

## Diagnostic flow

**Step 1 — Understand the symptom**
Ask: "Pouvez-vous me décrire le problème ? Par exemple : le système ne trouve pas les bons
passages, ou il trouve trop peu de résultats ?"

**Step 2 — Check current config**
Call `run_rag_facile("config show --format json")` to read the current settings. Look for:
- `retrieval.top_k` (how many candidates to retrieve)
- `reranking.top_n` (how many to keep after reranking)
- `retrieval.strategy` (semantic / hybrid / lexical)

**Step 3 — Diagnose**
| Symptom | Likely cause | Fix |
|---------|-------------|-----|
| Missing relevant passages | `top_k` too low | Increase `top_k` (try 15–20) |
| Too many irrelevant results | `top_n` too high | Decrease `top_n` (try 3–5) |
| Keyword match failing | strategy = "semantic" | Try strategy = "hybrid" |
| Slow responses | `top_k` too high | Decrease `top_k`, increase `top_n` ratio |

**Step 4 — Suggest a concrete change**
Tell the user exactly which line to change in ragfacile.toml, e.g.:
"Dans votre ragfacile.toml, changez `top_k = 10` en `top_k = 20`."

**Step 5 — Invite them to test**
"Essayez avec cette configuration et dites-moi si les résultats s'améliorent."

## Never
- Change config without explicit user confirmation
- Suggest more than one change at a time (too confusing for new users)
