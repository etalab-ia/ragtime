"""Tests for the learn first-run init wizard."""

from unittest.mock import patch

from typer.testing import CliRunner

from cli.commands.learn.init import (
    _profile_template,
    needs_init,
    read_language,
    run_init_wizard,
)
from cli.main import app as main_app


runner = CliRunner()


class TestNeedsInit:
    def test_returns_true_when_no_agent_dir(self, tmp_path):
        assert needs_init(tmp_path) is True

    def test_returns_false_when_agent_dir_exists(self, tmp_path):
        (tmp_path / ".agent").mkdir(parents=True)
        assert needs_init(tmp_path) is False


class TestProfileTemplate:
    def test_contains_experience_and_language(self):
        result = _profile_template("new", "fr")
        assert "New to RAG" in result
        assert "Language: fr" in result

    def test_session_count_starts_at_zero(self):
        result = _profile_template("intermediate", "en")
        assert "0" in result


class TestReadLanguage:
    def test_returns_fr_when_no_profile(self, tmp_path):
        assert read_language(tmp_path) == "fr"

    def test_reads_language_from_profile(self, tmp_path):
        (tmp_path / ".agent").mkdir(parents=True)
        (tmp_path / ".agent" / "profile.md").write_text(
            "## Preferences\n- Language: en\n", encoding="utf-8"
        )
        assert read_language(tmp_path) == "en"

    def test_returns_fr_as_default_when_language_line_absent(self, tmp_path):
        (tmp_path / ".agent").mkdir(parents=True)
        (tmp_path / ".agent" / "profile.md").write_text(
            "## Preferences\n", encoding="utf-8"
        )
        assert read_language(tmp_path) == "fr"


# questionary.select mock helpers (experience only — language is always French)
def _exp_new():
    return [type("Q", (), {"ask": lambda self: "new"})()]


def _exp_intermediate():
    return [type("Q", (), {"ask": lambda self: "intermediate"})()]


def _exp_expert():
    return [type("Q", (), {"ask": lambda self: "expert"})()]


class TestRunInitWizard:
    def test_creates_profile_file(self, tmp_path):
        """Wizard creates profile.md in the workspace."""
        with (
            patch(
                "cli.commands.learn.init.questionary.select",
                side_effect=_exp_new(),
            ),
            patch("cli.commands.learn.init._git_add"),
        ):
            run_init_wizard(tmp_path)

        assert (tmp_path / ".agent" / "profile.md").exists()

    def test_always_returns_french(self, tmp_path):
        """Wizard always returns 'fr' — language is not selectable."""
        with (
            patch(
                "cli.commands.learn.init.questionary.select",
                side_effect=_exp_intermediate(),
            ),
            patch("cli.commands.learn.init._git_add"),
        ):
            lang = run_init_wizard(tmp_path)
        assert lang == "fr"

    def test_creates_skills_directory(self, tmp_path):
        with (
            patch(
                "cli.commands.learn.init.questionary.select",
                side_effect=_exp_intermediate(),
            ),
            patch("cli.commands.learn.init._git_add"),
        ):
            run_init_wizard(tmp_path)

        assert (tmp_path / ".agents" / "skills").is_dir()

    def test_experience_reflected_in_profile(self, tmp_path):
        with (
            patch(
                "cli.commands.learn.init.questionary.select",
                side_effect=_exp_expert(),
            ),
            patch("cli.commands.learn.init._git_add"),
        ):
            run_init_wizard(tmp_path)

        profile = (tmp_path / ".agent" / "profile.md").read_text()
        assert "Expert" in profile

    def test_falls_back_to_defaults_on_non_interactive(self, tmp_path):
        """If questionary raises EOFError (non-interactive env), defaults are used."""
        with (
            patch(
                "cli.commands.learn.init.questionary.select",
                side_effect=EOFError("non-interactive terminal"),
            ),
            patch("cli.commands.learn.init._git_add"),
        ):
            run_init_wizard(tmp_path)  # should not raise

        assert (tmp_path / ".agent" / "profile.md").exists()

    def test_git_add_called_for_workspace_git(self, tmp_path):
        with (
            patch(
                "cli.commands.learn.init.questionary.select",
                side_effect=_exp_new(),
            ),
            patch("cli.commands.learn.init._git_add") as mock_git,
        ):
            run_init_wizard(tmp_path)

        mock_git.assert_called_once_with(tmp_path)

    def test_idempotent_when_run_twice(self, tmp_path):
        """Running wizard twice overwrites files cleanly without error."""
        for _ in range(2):
            with (
                patch(
                    "cli.commands.learn.init.questionary.select",
                    side_effect=_exp_new(),
                ),
                patch("cli.commands.learn.init._git_add"),
            ):
                run_init_wizard(tmp_path)

        assert (tmp_path / ".agent" / "profile.md").exists()


class TestChatInitIntegration:
    def test_init_runs_when_no_rag_facile_dir(self, tmp_path, monkeypatch):
        """start_learn() calls init wizard when .agent/ is absent."""
        (tmp_path / "ragfacile.toml").write_text('[meta]\npreset = "balanced"\n')
        monkeypatch.setenv("OPENAI_API_KEY", "test-key")

        with (
            patch("cli.commands.learn.agent._detect_workspace", return_value=tmp_path),
            patch("cli.commands.learn.agent.OpenAIServerModel"),
            patch("cli.commands.learn.agent.ToolCallingAgent"),
            patch("cli.commands.learn.agent.run_init_wizard") as mock_init,
            patch("cli.commands.learn.agent.needs_init", return_value=True),
        ):
            result = runner.invoke(main_app, ["learn"], input="q\n")

        assert result.exit_code == 0
        mock_init.assert_called_once_with(tmp_path)

    def test_init_skipped_when_already_initialised(self, tmp_path, monkeypatch):
        """start_learn() skips init wizard when .agent/ already exists."""
        (tmp_path / "ragfacile.toml").write_text('[meta]\npreset = "balanced"\n')
        monkeypatch.setenv("OPENAI_API_KEY", "test-key")

        with (
            patch("cli.commands.learn.agent._detect_workspace", return_value=tmp_path),
            patch("cli.commands.learn.agent.OpenAIServerModel"),
            patch("cli.commands.learn.agent.ToolCallingAgent"),
            patch("cli.commands.learn.agent.run_init_wizard") as mock_init,
            patch("cli.commands.learn.agent.needs_init", return_value=False),
        ):
            result = runner.invoke(main_app, ["learn"], input="q\n")

        assert result.exit_code == 0
        mock_init.assert_not_called()
