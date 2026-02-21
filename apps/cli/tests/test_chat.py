"""Tests for the rag-facile chat command."""

from unittest.mock import patch

from typer.testing import CliRunner

from cli.main import app as main_app


runner = CliRunner()


class TestChatCommand:
    """Tests for the `rag-facile chat` / default `rag-facile` command."""

    def test_no_subcommand_launches_chat(self, monkeypatch):
        """Running rag-facile with no args launches chat instead of showing help."""
        monkeypatch.setenv("OPENAI_API_KEY", "test-key")

        with (
            patch("cli.commands.chat.agent._detect_workspace", return_value=None),
            patch("cli.commands.chat.agent.OpenAIServerModel"),
            patch("cli.commands.chat.agent.ToolCallingAgent"),
        ):
            result = runner.invoke(main_app, [], input="q\n")

        assert result.exit_code == 0
        # Chat started: welcome panel visible
        assert "Bonjour" in result.output
        # Help page NOT shown
        assert "Usage:" not in result.output

    def test_chat_alias_also_works(self, monkeypatch):
        """`rag-facile chat` is an explicit alias that starts the same loop."""
        monkeypatch.setenv("OPENAI_API_KEY", "test-key")

        with (
            patch("cli.commands.chat.agent._detect_workspace", return_value=None),
            patch("cli.commands.chat.agent.OpenAIServerModel"),
            patch("cli.commands.chat.agent.ToolCallingAgent"),
        ):
            result = runner.invoke(main_app, ["chat"], input="q\n")

        assert result.exit_code == 0
        assert "Bonjour" in result.output

    def test_no_workspace_warning_shown_chat_still_starts(self, monkeypatch):
        """Outside a workspace: no-workspace hint shown, chat still starts."""
        monkeypatch.setenv("OPENAI_API_KEY", "test-key")

        with (
            patch("cli.commands.chat.agent._detect_workspace", return_value=None),
            patch("cli.commands.chat.agent.OpenAIServerModel"),
            patch("cli.commands.chat.agent.ToolCallingAgent"),
        ):
            result = runner.invoke(main_app, [], input="q\n")

        assert result.exit_code == 0
        # No-workspace hint visible in the welcome panel
        assert "ragfacile.toml" in result.output
        assert "rag-facile setup" in result.output
        # Chat still started
        assert "Bonjour" in result.output

    def test_missing_api_key_exits_with_error(self, monkeypatch):
        """Without an API key, chat exits cleanly with an error message."""
        monkeypatch.delenv("OPENAI_API_KEY", raising=False)
        monkeypatch.delenv("ALBERT_API_KEY", raising=False)

        with patch("cli.commands.chat.agent._detect_workspace", return_value=None):
            result = runner.invoke(main_app, [])

        assert result.exit_code == 1
        assert "No API key found" in result.output

    def test_run_rag_facile_tool_no_workspace(self):
        """run_rag_facile with no workspace still runs the command (no cwd requirement)."""
        from unittest.mock import MagicMock, patch

        from cli.commands.chat import tools

        tools._workspace_root = None
        mock_result = MagicMock()
        mock_result.stdout = "rag-facile v0.17.0"
        mock_result.stderr = ""
        with patch("cli.commands.chat.tools.subprocess.run", return_value=mock_result):
            result = tools.run_rag_facile("version")

        assert "0.17.0" in result
