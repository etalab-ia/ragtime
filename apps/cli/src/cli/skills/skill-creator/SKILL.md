---
name: skill-creator
description: Help the user design and write a new skill for the rag-facile agent.
triggers: ["create skill", "new skill", "créer une compétence", "add skill", "custom skill", "write skill", "skill-creator"]
---

# Skill: Skill Creator

You are helping the user create a new custom skill for their rag-facile workspace.
Skills live in `.rag-facile/skills/<name>/SKILL.md` and are loaded automatically.

## Step 1 — Understand what they want the skill to do
Ask: "Quel type de questions ou de tâches voulez-vous que cette compétence gère ?"
Examples: "explain our internal document structure", "help debug our chunking config"

## Step 2 — Name the skill
Suggest a short kebab-case name based on their answer.
Rules: lowercase, hyphens only, no spaces. E.g. `explain-chunks`, `debug-chunking`.

## Step 3 — Define trigger keywords
Ask: "Quels mots ou phrases devraient activer cette compétence automatiquement ?"
These become the `triggers` list in the frontmatter.

## Step 4 — Write the SKILL.md together
Build the file section by section:

```markdown
---
name: <name>
description: <one sentence — what this skill helps with>
triggers: ["keyword1", "keyword2", ...]
---

# Skill: <Name>

<Instructions for the agent — written in imperative, describing HOW to behave>

## <Section 1>
...
```

Good skill instructions:
- Tell the agent what to do step-by-step (numbered flow)
- Reference which tools to call (`run_rag_facile()`, `get_docs()`, etc.)
- Include "never" rules to prevent common mistakes
- Are written for the agent, not the user

## Step 5 — Save the skill
Once the user approves the content, save it to the standard npx skills location:

```
.agents/skills/<name>/SKILL.md
```

Confirm: "Votre compétence '<name>' a été créée dans .agents/skills/ ! Elle sera
disponible lors de votre prochaine session. Tapez `/skills` pour la voir dans la liste."

## Installing skills from the registry (npx skills)
If the user wants a skill from the public registry instead:
Tell them to type `/skills install <package>` in the chat.
Example: `/skills install vercel-labs/agent-skills`
They can browse available skills at https://github.com/search?q=topic%3Aagent-skills
