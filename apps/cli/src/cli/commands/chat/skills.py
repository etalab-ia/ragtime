"""Skills system for the rag-facile chat agent.

Skills are Markdown instruction files (SKILL.md) that specialise the agent's
behaviour for a specific task. They are discovered from three locations:

  1. Built-in  — bundled with the CLI package at cli/skills/
  2. npx       — installed via `npx skills add <pkg>` into <workspace>/.agents/skills/
  3. Project   — hand-crafted by the user at <workspace>/.rag-facile/skills/

Skills are loaded by injecting their SKILL.md content into the agent's system
prompt. Only one skill is active at a time per session.
"""

from __future__ import annotations

import subprocess
from pathlib import Path

import yaml

# ── Discovery ─────────────────────────────────────────────────────────────────


def _builtin_skills_dir() -> Path | None:
    """Return the bundled skills directory (installed package or dev repo).

    In both cases the path is the same relative to this file:
      <installed>  site-packages/cli/skills/
      <dev>        apps/cli/src/cli/skills/
    Both resolve to parents[2] / "skills" from cli/commands/chat/skills.py.
    """
    candidate = Path(__file__).resolve().parents[2] / "skills"
    return candidate if candidate.exists() else None


_WORKSPACE_SKILLS_DIR = ".agents/skills"  # standard npx skills location


def discover_skills(workspace: Path | None) -> dict[str, Path]:
    """Return {skill_name: SKILL.md path} from built-in and workspace skills.

    Sources scanned in priority order:
      1. Built-in   (cli/skills/ — bundled with the CLI)
      2. Workspace  (<workspace>/.agents/skills/) — standard npx skills location

    `npx skills add <pkg>` installs directly here with no extra steps.
    Workspace skills override built-ins so users can shadow any built-in.
    """
    skills: dict[str, Path] = {}

    # 1 — Built-in
    builtin = _builtin_skills_dir()
    if builtin:
        for skill_md in sorted(builtin.glob("*/SKILL.md")):
            skills[skill_md.parent.name] = skill_md

    if workspace is None:
        return skills

    # 2 — Workspace (.agents/skills/ — npx skills standard)
    workspace_dir = workspace / _WORKSPACE_SKILLS_DIR
    if workspace_dir.exists():
        for skill_md in sorted(workspace_dir.glob("*/SKILL.md")):
            skills[skill_md.parent.name] = skill_md

    return skills


# ── Loading ───────────────────────────────────────────────────────────────────


def load_skill(skill_path: Path) -> str:
    """Return the SKILL.md content to inject into the agent's system prompt."""
    return skill_path.read_text(encoding="utf-8")


def format_skills_list(skills: dict[str, Path]) -> str:
    """Format the skills list for display in the chat UI."""
    if not skills:
        return "No skills available."

    builtin_dir = _builtin_skills_dir()
    lines = ["📚 Available Skills\n"]

    built_in = {
        n: p for n, p in skills.items() if builtin_dir and p.is_relative_to(builtin_dir)
    }
    workspace_skills = {n: p for n, p in skills.items() if ".agents/skills" in str(p)}

    if built_in:
        lines.append("Built-in:")
        for name, path in sorted(built_in.items()):
            desc = _extract_description(path)
            lines.append(f"  {name:<22} {desc}")

    if workspace_skills:
        lines.append("\nWorkspace skills (.agents/skills/):")
        for name, path in sorted(workspace_skills.items()):
            desc = _extract_description(path)
            lines.append(f"  {name:<22} {desc}")
    else:
        lines.append(
            "\nWorkspace skills (.agents/skills/): none yet\n"
            "  Type '/skills install <pkg>' to install from the registry, or\n"
            "  ask me to help you create one with '/skills create <name>'."
        )

    return "\n".join(lines)


_frontmatter_cache: dict[Path, dict] = {}


def _parse_frontmatter(skill_path: Path) -> dict:
    """Parse and cache YAML frontmatter from a SKILL.md file.

    Parses once per path; result is cached for the session to avoid
    re-reading files on every discover/detect call.
    """
    if skill_path in _frontmatter_cache:
        return _frontmatter_cache[skill_path]
    result: dict = {}
    try:
        content = skill_path.read_text(encoding="utf-8")
        if content.startswith("---"):
            end = content.find("---", 3)
            if end != -1:
                result = yaml.safe_load(content[3:end]) or {}
    except (OSError, yaml.YAMLError):
        pass
    _frontmatter_cache[skill_path] = result
    return result


def _extract_description(skill_path: Path) -> str:
    """Pull the description from SKILL.md YAML frontmatter."""
    return str(_parse_frontmatter(skill_path).get("description", ""))


def _extract_triggers(skill_path: Path) -> list[str]:
    """Pull the triggers list from SKILL.md YAML frontmatter."""
    raw = _parse_frontmatter(skill_path).get("triggers", [])
    return [str(t) for t in raw] if isinstance(raw, list) else []


# ── Keyword-based detection (external/npx skills only) ────────────────────────


def auto_detect_skill(
    message: str,
    available: dict[str, Path],
) -> str | None:
    """Return the best matching skill name for a user message, or None.

    Matches against the ``triggers`` list in each skill's YAML frontmatter.
    Built-in skills are routed semantically by the LLM via ``activate_skill``;
    this function is a keyword fallback for external / npx skills that define
    their own triggers.
    """
    msg_lower = message.lower()
    for skill_name, skill_path in available.items():
        triggers = _extract_triggers(skill_path)
        if any(t.lower() in msg_lower for t in triggers):
            return skill_name
    return None


# ── npx skills integration ────────────────────────────────────────────────────


def install_skill(package: str, workspace: Path) -> str:
    """Install a skill package via `npx skills add` into <workspace>/.agents/skills/.

    Returns a human-readable result message.
    """
    if not package or package.startswith("-"):
        return "Invalid package name."
    try:
        result = subprocess.run(
            ["npx", "skills", "add", package, "--yes"],
            cwd=workspace,
            capture_output=True,
            text=True,
            timeout=60,
        )
        if result.returncode == 0:
            installed = (
                [
                    p.parent.name
                    for p in (workspace / ".agents" / "skills").glob("*/SKILL.md")
                ]
                if (workspace / ".agents" / "skills").exists()
                else []
            )
            names = ", ".join(installed) if installed else package
            return (
                f"✓ Skill '{names}' installed to .agents/skills/. "
                "Type `/skills` to see the updated list."
            )
        return f"Installation failed:\n{result.stderr.strip() or result.stdout.strip()}"
    except FileNotFoundError:
        return (
            "npx is not installed or not on PATH. "
            "Install Node.js to use the skills registry."
        )
    except subprocess.TimeoutExpired:
        return "Installation timed out. Check your internet connection and try again."
