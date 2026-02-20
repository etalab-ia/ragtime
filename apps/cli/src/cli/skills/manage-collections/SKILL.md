---
name: manage-collections
description: Discover, understand and enable/disable Albert API collections in ragfacile.toml. Use when the user asks about available datasets, wants to add a public collection, or wants to toggle collections on or off.
triggers: ["collections", "dataset public", "collection", "activer", "désactiver", "enable collection", "disable collection"]
---

# Skill: Manage Collections

You help the user discover available collections on the Albert API and configure
which ones are active in their RAG pipeline.

## Step 1 — Fetch available collections
Call `list_collections()` to retrieve all accessible collections.
Present the results clearly: highlight public collections (available to all users)
and the user's private ones separately.

## Step 2 — Explain what collections are
If the user seems unfamiliar, explain briefly:
- Collections are pre-indexed document sets stored on the Albert API
- Public collections include government datasets (service-public.fr, légifrance, etc.)
- Enabling a collection means the RAG pipeline will search it on every query
- Multiple collections can be active simultaneously

## Step 3 — Help them choose
Ask: "Quelles collections souhaitez-vous activer dans votre pipeline RAG ?"
Show the current active collections from `get_ragfacile_config()`.
Suggest relevant public ones based on their use case if known.

## Step 4 — Update the configuration with update_config

CRITICAL: When the user asks to activate or deactivate a collection, you MUST
call `update_config` — do NOT explain how to manually edit ragfacile.toml.
The agent can write the file directly. Manual editing instructions are never helpful here.

Flow:
1. Read the current list from `get_ragfacile_config()` (e.g. `[783, 784, 785]`)
2. Compute the new list (add or remove the requested ID)
3. Say: "Je vais mettre à jour storage.collections : [783, 784, 785] → [783, 784, 785, 79783].
   Puis-je effectuer ce changement ? Il sera enregistré dans ragfacile.toml et committé dans git."
4. Wait for explicit "oui" / "yes"
5. Call: `update_config("storage.collections", "[783, 784, 785, 79783]")`

## Rules
- ALWAYS use update_config — never tell the user to edit the file manually
- Never modify collections without explicit user confirmation
- Always compute the complete new list (not just the delta) before calling update_config
- Remind the user to restart their app after the change takes effect
- Session collections (uploaded files) are separate from public collections — both can be active
