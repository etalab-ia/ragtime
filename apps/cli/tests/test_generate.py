"""Tests for the generate command."""

from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest
from cli.commands.generate import (
    FRONTENDS,
    MODULES,
    get_templates_dir,
    run_command,
)
from cli.main import app as main_app
from typer.testing import CliRunner

runner = CliRunner()


class TestGetTemplatesDir:
    """Tests for get_templates_dir function."""

    def test_returns_path_object(self):
        """Should return a Path object."""
        result = get_templates_dir()
        assert isinstance(result, Path)

    def test_path_ends_with_moon_templates(self):
        """Should return path ending with .moon/templates."""
        result = get_templates_dir()
        assert result.parts[-2:] == (".moon", "templates")

    def test_path_exists_in_repo(self):
        """Templates directory should exist when running from repo."""
        result = get_templates_dir()
        assert result.exists(), f"Templates dir not found at {result}"


class TestRunCommand:
    """Tests for run_command function."""

    def test_successful_command(self, mocker):
        """Should return True for successful command."""
        mock_run = mocker.patch("subprocess.run")
        mock_run.return_value = MagicMock(returncode=0, stderr="")

        result = run_command(["echo", "hello"], "test command")

        assert result is True
        mock_run.assert_called_once()

    def test_failed_command(self, mocker):
        """Should return False for failed command."""
        mock_run = mocker.patch("subprocess.run")
        mock_run.return_value = MagicMock(returncode=1, stderr="error message")

        result = run_command(["false"], "failing command")

        assert result is False

    def test_command_with_cwd(self, mocker):
        """Should pass cwd to subprocess.run."""
        mock_run = mocker.patch("subprocess.run")
        mock_run.return_value = MagicMock(returncode=0, stderr="")
        test_path = Path("/tmp/test")

        run_command(["ls"], "list files", cwd=test_path)

        mock_run.assert_called_once()
        call_kwargs = mock_run.call_args[1]
        assert call_kwargs["cwd"] == test_path


class TestConstants:
    """Tests for module constants."""

    def test_frontends_has_chainlit(self):
        """Should have Chainlit frontend option."""
        assert "Chainlit" in FRONTENDS
        assert FRONTENDS["Chainlit"] == "chainlit-chat"

    def test_frontends_has_reflex(self):
        """Should have Reflex frontend option."""
        assert "Reflex" in FRONTENDS
        assert FRONTENDS["Reflex"] == "reflex-chat"

    def test_modules_has_pdf(self):
        """Should have PDF module option."""
        assert "PDF" in MODULES
        assert MODULES["PDF"]["template"] == "pdf-context"
        assert MODULES["PDF"]["available"] is True

    def test_modules_has_chroma(self):
        """Should have Chroma module option (not yet available)."""
        assert "Chroma" in MODULES
        assert MODULES["Chroma"]["template"] == "chroma-context"
        assert MODULES["Chroma"]["available"] is False


class TestWorkspaceCommand:
    """Integration tests for workspace generation."""

    def test_workspace_command_exists(self):
        """The workspace subcommand should be registered."""
        result = runner.invoke(main_app, ["generate", "workspace", "--help"])
        assert result.exit_code == 0
        assert "Generate a new RAG Facile workspace" in result.output

    def test_workspace_requires_target(self):
        """Should show help when no target provided and not interactive."""
        # In non-interactive mode, questionary returns None
        with patch("cli.commands.generate.questionary") as mock_q:
            mock_q.text.return_value.ask.return_value = None
            result = runner.invoke(main_app, ["generate", "workspace"])
            assert result.exit_code == 1

    @pytest.fixture
    def mock_generation(self, mocker, tmp_path):
        """Mock all external calls for workspace generation."""
        # Mock shutil.which to pretend moon is installed
        mocker.patch("shutil.which", return_value="/usr/bin/moon")

        # Mock questionary interactions
        mock_q = mocker.patch("cli.commands.generate.questionary")
        mock_q.select.return_value.ask.return_value = "Chainlit"
        mock_q.checkbox.return_value.ask.return_value = ["PDF"]
        mock_q.confirm.return_value.ask.return_value = True
        mock_q.text.return_value.ask.return_value = "test-value"

        # Mock subprocess.run for moon commands
        mock_run = mocker.patch("subprocess.run")
        mock_run.return_value = MagicMock(returncode=0, stderr="")

        # Mock shutil.copytree (templates copy)
        mock_copytree = mocker.patch("shutil.copytree")

        # Mock yaml operations
        mocker.patch("yaml.safe_load", return_value={})
        mocker.patch("yaml.dump")

        # Mock open for .env file writing
        mocker.patch("builtins.open", mocker.mock_open())

        return {
            "questionary": mock_q,
            "subprocess_run": mock_run,
            "copytree": mock_copytree,
            "tmp_path": tmp_path,
        }

    def test_workspace_generation_flow(self, mock_generation, tmp_path):
        """Should execute the full generation flow."""
        target = tmp_path / "test-app"
        # Create the app directory structure that moon generate would create
        (target / "apps" / "chainlit-chat").mkdir(parents=True)

        result = runner.invoke(main_app, ["generate", "workspace", str(target)])

        # Should complete successfully
        assert result.exit_code == 0, f"Failed with: {result.output}"
        assert "Workspace generation complete" in result.output

    def test_workspace_creates_target_directory(self, mock_generation, tmp_path):
        """Should create target directory if it doesn't exist."""
        target = tmp_path / "new-app"
        assert not target.exists()

        runner.invoke(main_app, ["generate", "workspace", str(target)])

        assert target.exists()

    def test_workspace_runs_moon_init(self, mock_generation, tmp_path):
        """Should run moon init in the target directory."""
        target = tmp_path / "test-app"

        runner.invoke(main_app, ["generate", "workspace", str(target)])

        # Check moon init was called
        calls = mock_generation["subprocess_run"].call_args_list
        moon_init_calls = [c for c in calls if "moon" in c[0][0] and "init" in c[0][0]]
        assert len(moon_init_calls) >= 1

    def test_workspace_runs_moon_generate(self, mock_generation, tmp_path):
        """Should run moon generate for templates."""
        target = tmp_path / "test-app"

        runner.invoke(main_app, ["generate", "workspace", str(target)])

        # Check moon generate was called for sys-config and chainlit-chat
        calls = mock_generation["subprocess_run"].call_args_list
        generate_calls = [
            c for c in calls if "moon" in c[0][0] and "generate" in c[0][0]
        ]
        assert len(generate_calls) >= 2  # sys-config + app

    def test_workspace_with_force_flag(self, mock_generation, tmp_path):
        """Should pass --force flag to moon generate."""
        target = tmp_path / "test-app"

        runner.invoke(main_app, ["generate", "workspace", str(target), "--force"])

        calls = mock_generation["subprocess_run"].call_args_list
        force_calls = [c for c in calls if "--force" in c[0][0]]
        assert len(force_calls) >= 1

    def test_workspace_copies_templates(self, mock_generation, tmp_path):
        """Should copy templates to target workspace."""
        target = tmp_path / "test-app"

        runner.invoke(main_app, ["generate", "workspace", str(target)])

        # copytree should be called for each template
        assert mock_generation["copytree"].call_count >= 1


class TestPathNormalization:
    """Tests for macOS path normalization."""

    def test_private_tmp_normalized_in_output(self, mocker, tmp_path):
        """Should normalize /private/tmp to /tmp in output."""
        # Create a path that looks like macOS /private/tmp
        mock_q = mocker.patch("cli.commands.generate.questionary")
        mock_q.select.return_value.ask.return_value = "Chainlit"
        mock_q.checkbox.return_value.ask.return_value = []
        mock_q.confirm.return_value.ask.return_value = False  # Abort early

        # Use a path under /private/tmp if on macOS
        result = runner.invoke(
            main_app, ["generate", "workspace", "/private/tmp/test-app"]
        )

        # Output should show /tmp not /private/tmp
        if "/private/tmp" in result.output:
            pytest.fail("Output contains /private/tmp instead of /tmp")
