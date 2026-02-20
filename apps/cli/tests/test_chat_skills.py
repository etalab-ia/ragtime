"""Tests for the skills system (discover, load, auto-detect, install, format)."""

import subprocess
from unittest.mock import MagicMock, patch

import pytest

from cli.commands.chat.skills import (
    _extract_description,
    _extract_triggers,
    auto_detect_skill,
    discover_skills,
    format_skills_list,
    install_skill,
    load_skill,
)


# ── Fixtures ──────────────────────────────────────────────────────────────────


@pytest.fixture()
def workspace(tmp_path):
    """Workspace with a .agents/skills/ directory containing one skill."""
    skill_dir = tmp_path / ".agents" / "skills" / "my-skill"
    skill_dir.mkdir(parents=True)
    (skill_dir / "SKILL.md").write_text(
        "---\nname: my-skill\ndescription: A test skill.\n"
        'triggers: ["test", "demo"]\n---\n\n# Skill: My Skill\nDo something.',
        encoding="utf-8",
    )
    return tmp_path


@pytest.fixture()
def builtin_dir(tmp_path):
    """Minimal built-in skills directory."""
    skill = tmp_path / "builtin-skill"
    skill.mkdir()
    (skill / "SKILL.md").write_text(
        "---\nname: builtin-skill\ndescription: A built-in skill.\n"
        'triggers: ["builtin"]\n---\n\n# Skill: Builtin\nBuilt-in content.',
        encoding="utf-8",
    )
    return tmp_path


# ── discover_skills ───────────────────────────────────────────────────────────


class TestDiscoverSkills:
    def test_returns_builtin_skills(self, builtin_dir):
        with patch(
            "cli.commands.chat.skills._builtin_skills_dir", return_value=builtin_dir
        ):
            skills = discover_skills(workspace=None)
        assert "builtin-skill" in skills

    def test_returns_workspace_skills(self, workspace, builtin_dir):
        with patch(
            "cli.commands.chat.skills._builtin_skills_dir", return_value=builtin_dir
        ):
            skills = discover_skills(workspace)
        assert "my-skill" in skills
        assert "builtin-skill" in skills

    def test_workspace_skill_overrides_builtin(self, tmp_path, builtin_dir):
        """A workspace skill with the same name shadows the built-in."""
        override_dir = tmp_path / ".agents" / "skills" / "builtin-skill"
        override_dir.mkdir(parents=True)
        (override_dir / "SKILL.md").write_text(
            "---\nname: builtin-skill\ndescription: Overridden.\ntriggers: []\n---\nOverride.",
            encoding="utf-8",
        )
        with patch(
            "cli.commands.chat.skills._builtin_skills_dir", return_value=builtin_dir
        ):
            skills = discover_skills(tmp_path)
        assert "Overridden" in skills["builtin-skill"].read_text()

    def test_no_workspace_returns_only_builtins(self, builtin_dir):
        with patch(
            "cli.commands.chat.skills._builtin_skills_dir", return_value=builtin_dir
        ):
            skills = discover_skills(workspace=None)
        assert all(".agents" not in str(p) for p in skills.values())


# ── load_skill ────────────────────────────────────────────────────────────────


class TestLoadSkill:
    def test_returns_skill_content(self, workspace):
        skill_path = workspace / ".agents" / "skills" / "my-skill" / "SKILL.md"
        content = load_skill(skill_path)
        assert "# Skill: My Skill" in content


# ── format_skills_list ────────────────────────────────────────────────────────


class TestFormatSkillsList:
    def test_shows_workspace_skills(self, workspace, builtin_dir):
        with patch(
            "cli.commands.chat.skills._builtin_skills_dir", return_value=builtin_dir
        ):
            skills = discover_skills(workspace)
        result = format_skills_list(skills)
        assert "my-skill" in result
        assert "A test skill." in result

    def test_shows_no_skills_hint_when_empty(self, builtin_dir):
        with patch("cli.commands.chat.skills._builtin_skills_dir", return_value=None):
            skills = discover_skills(workspace=None)
        result = format_skills_list(skills)
        assert "No skills available" in result

    def test_shows_install_hint_when_no_workspace_skills(self, builtin_dir):
        with patch(
            "cli.commands.chat.skills._builtin_skills_dir", return_value=builtin_dir
        ):
            skills = discover_skills(workspace=None)
        result = format_skills_list(skills)
        assert "/skills install" in result


# ── auto_detect_skill ─────────────────────────────────────────────────────────
# Built-in skills are routed by the LLM via activate_skill().
# auto_detect_skill() is a keyword fallback for external/npx skills only.


class TestAutoDetectSkill:
    def test_detects_external_skill_by_frontmatter_trigger(self, workspace):
        skills = {
            "my-skill": workspace / ".agents" / "skills" / "my-skill" / "SKILL.md"
        }
        result = auto_detect_skill("can you show me a test demo", skills)
        assert result == "my-skill"

    def test_returns_none_when_no_match(self, workspace):
        skills = {
            "my-skill": workspace / ".agents" / "skills" / "my-skill" / "SKILL.md"
        }
        result = auto_detect_skill("bonjour, comment ça va?", skills)
        assert result is None

    def test_returns_none_when_no_skills(self):
        result = auto_detect_skill("what is rag?", {})
        assert result is None


# ── _extract_description / _extract_triggers ──────────────────────────────────


class TestExtractFrontmatter:
    def test_extracts_description(self, workspace):
        path = workspace / ".agents" / "skills" / "my-skill" / "SKILL.md"
        assert _extract_description(path) == "A test skill."

    def test_extracts_triggers(self, workspace):
        path = workspace / ".agents" / "skills" / "my-skill" / "SKILL.md"
        triggers = _extract_triggers(path)
        assert "test" in triggers
        assert "demo" in triggers

    def test_returns_empty_on_missing_file(self, tmp_path):
        assert _extract_description(tmp_path / "nonexistent.md") == ""
        assert _extract_triggers(tmp_path / "nonexistent.md") == []


# ── install_skill ─────────────────────────────────────────────────────────────


class TestInstallSkill:
    def test_success(self, workspace):
        mock_result = MagicMock()
        mock_result.returncode = 0
        with patch("cli.commands.chat.skills.subprocess.run", return_value=mock_result):
            result = install_skill("org/my-pkg", workspace)
        assert "installed" in result.lower()

    def test_failure_returns_stderr(self, workspace):
        mock_result = MagicMock()
        mock_result.returncode = 1
        mock_result.stderr = "Package not found"
        mock_result.stdout = ""
        with patch("cli.commands.chat.skills.subprocess.run", return_value=mock_result):
            result = install_skill("bad/pkg", workspace)
        assert "Package not found" in result

    def test_no_npx(self, workspace):
        with patch(
            "cli.commands.chat.skills.subprocess.run", side_effect=FileNotFoundError
        ):
            result = install_skill("org/pkg", workspace)
        assert "npx is not installed" in result

    def test_timeout(self, workspace):
        with patch(
            "cli.commands.chat.skills.subprocess.run",
            side_effect=subprocess.TimeoutExpired("npx", 60),
        ):
            result = install_skill("org/pkg", workspace)
        assert "timed out" in result.lower()

    def test_rejects_flag_like_package_name(self, workspace):
        result = install_skill("--evil-flag", workspace)
        assert result == "Invalid package name."

    def test_rejects_empty_package_name(self, workspace):
        result = install_skill("", workspace)
        assert result == "Invalid package name."
