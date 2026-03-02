"""Tests for the rag-facile learn command."""

from unittest.mock import patch

from typer.testing import CliRunner

from cli.main import app as main_app


runner = CliRunner()


class TestLearnCommand:
    """Tests for the `rag-facile learn` command and no-args behaviour."""

    def test_no_subcommand_shows_help(self):
        """Running rag-facile with no args shows help, not the learning assistant."""
        result = runner.invoke(main_app, [])

        assert result.exit_code == 0
        # Help is shown
        assert "Usage:" in result.output
        # Learning assistant NOT started
        assert "Bonjour" not in result.output

    def test_learn_command_starts_assistant(self, monkeypatch):
        """`rag-facile learn` starts the interactive learning assistant."""
        monkeypatch.setenv("OPENAI_API_KEY", "test-key")

        with (
            patch("cli.commands.learn.agent._detect_workspace", return_value=None),
            patch("cli.commands.learn.agent.OpenAIServerModel"),
            patch("cli.commands.learn.agent.ToolCallingAgent"),
        ):
            result = runner.invoke(main_app, ["learn"], input="q\n")

        assert result.exit_code == 0
        # Welcome panel visible
        assert "Bonjour" in result.output
        # Help page NOT shown
        assert "Usage:" not in result.output

    def test_no_workspace_warning_shown_learn_still_starts(self, monkeypatch):
        """Outside a workspace: no-workspace hint shown, learn still starts."""
        monkeypatch.setenv("OPENAI_API_KEY", "test-key")

        with (
            patch("cli.commands.learn.agent._detect_workspace", return_value=None),
            patch("cli.commands.learn.agent.OpenAIServerModel"),
            patch("cli.commands.learn.agent.ToolCallingAgent"),
        ):
            result = runner.invoke(main_app, ["learn"], input="q\n")

        assert result.exit_code == 0
        # No-workspace hint visible in the welcome panel
        assert "ragfacile.toml" in result.output
        # Learn still started
        assert "Bonjour" in result.output

    def test_missing_api_key_exits_with_error(self, monkeypatch):
        """Without an API key, learn exits cleanly with an error message."""
        monkeypatch.delenv("OPENAI_API_KEY", raising=False)
        monkeypatch.delenv("ALBERT_API_KEY", raising=False)

        with patch("cli.commands.learn.agent._detect_workspace", return_value=None):
            result = runner.invoke(main_app, ["learn"])

        assert result.exit_code == 1
        assert "No API key found" in result.output

    def test_run_rag_facile_tool_no_workspace(self):
        """run_rag_facile with no workspace still runs the command (no cwd requirement)."""
        from unittest.mock import MagicMock, patch

        from cli.commands.learn import tools

        tools._workspace_root = None
        mock_result = MagicMock()
        mock_result.stdout = "rag-facile v0.17.0"
        mock_result.stderr = ""
        with patch("cli.commands.learn.tools.subprocess.run", return_value=mock_result):
            result = tools.run_rag_facile("version")

        assert "0.17.0" in result


class TestNewCommand:
    """/new command resets session and saves memory."""

    def test_new_command_prints_reset_message(self, monkeypatch):
        """/new shows the session reset message."""
        monkeypatch.setenv("OPENAI_API_KEY", "test-key")

        with (
            patch("cli.commands.learn.agent._detect_workspace", return_value=None),
            patch("cli.commands.learn.agent.OpenAIServerModel"),
            patch("cli.commands.learn.agent.ToolCallingAgent"),
        ):
            # Type /new, then q to quit
            result = runner.invoke(main_app, ["learn"], input="/new\nq\n")

        assert result.exit_code == 0
        # Session reset message visible (without workspace, finalize is a no-op)
        assert "session" in result.output.lower()

    def test_new_command_calls_finalize(self, monkeypatch, tmp_path):
        """/new triggers session finalization before resetting."""
        monkeypatch.setenv("OPENAI_API_KEY", "test-key")

        # Create a minimal workspace
        (tmp_path / "ragfacile.toml").write_text("")
        (tmp_path / ".env").write_text("")
        agent_dir = tmp_path / ".agent"
        agent_dir.mkdir()
        (agent_dir / "profile.md").write_text(
            "# Profile\n\n## Session Count\n0\n", encoding="utf-8"
        )
        (agent_dir / "MEMORY.md").write_text("# Memory\n", encoding="utf-8")

        with (
            patch("cli.commands.learn.agent._detect_workspace", return_value=tmp_path),
            patch("cli.commands.learn.agent.OpenAIServerModel"),
            patch("cli.commands.learn.agent.ToolCallingAgent") as mock_agent_cls,
            patch("cli.commands.learn.agent.needs_init", return_value=False),
            patch("cli.commands.learn.agent.read_language", return_value="en"),
            patch("cli.commands.learn.agent._finalize") as mock_finalize,
        ):
            mock_agent = mock_agent_cls.return_value
            mock_agent.run.return_value = "Hello!"
            mock_agent.memory = None

            # Ask a question, then /new, then quit
            result = runner.invoke(main_app, ["learn"], input="hello\n/new\nq\n")

        assert result.exit_code == 0
        # _finalize called twice: once for /new, once for quit
        assert mock_finalize.call_count == 2
