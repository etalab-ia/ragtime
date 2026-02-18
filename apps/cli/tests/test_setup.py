"""Tests for the setup command."""

import tempfile
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest
from typer.testing import CliRunner

from cli.commands.setup import (
    FRONTENDS,
    MODULES,
    PROJECT_STRUCTURES,
    get_templates_dir,
    render_template_file,
    run_command,
)
from cli.main import app as main_app


runner = CliRunner()


@pytest.fixture
def preset_config():
    """Default preset config for testing."""
    return {
        "model_alias": "openweight-medium",
        "temperature": 0.7,
        "language": "fr",
        "system_prompt": "Vous êtes un assistant utile.",
        "openai_base_url": "https://albert.api.etalab.gouv.fr/v1",
    }


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

    def test_modules_has_local(self):
        """Should have Local module option."""
        assert "Local" in MODULES
        assert MODULES["Local"]["template"] == "retrieval"
        assert MODULES["Local"]["available"] is True

    def test_project_structures_has_standalone(self):
        """Should have standalone project structure option."""
        assert "Simple (recommended for getting started)" in PROJECT_STRUCTURES
        assert (
            PROJECT_STRUCTURES["Simple (recommended for getting started)"]
            == "standalone"
        )

    def test_project_structures_has_monorepo(self):
        """Should have monorepo project structure option."""
        assert "Monorepo (for multi-app projects)" in PROJECT_STRUCTURES
        assert PROJECT_STRUCTURES["Monorepo (for multi-app projects)"] == "monorepo"


class TestRenderTemplateFile:
    """Tests for render_template_file function."""

    @pytest.fixture
    def temp_template(self):
        """Create a temporary template file for testing."""
        with tempfile.NamedTemporaryFile(mode="w", suffix=".txt", delete=False) as f:
            yield Path(f.name)
        Path(f.name).unlink(missing_ok=True)

    def test_simple_variable_substitution(self, temp_template):
        """Should substitute {{ var }} syntax."""
        temp_template.write_text("Hello {{ name }}!")
        result = render_template_file(temp_template, {"name": "World"})
        assert result == "Hello World!"

    def test_multiple_variables(self, temp_template):
        """Should substitute multiple variables."""
        temp_template.write_text("{{ greeting }} {{ name }}!")
        result = render_template_file(
            temp_template, {"greeting": "Hello", "name": "World"}
        )
        assert result == "Hello World!"

    def test_replace_filter_substitution(self, temp_template):
        """Should handle replace filter syntax."""
        temp_template.write_text(
            "Module: {{ project_name | replace(from='-', to='_') }}"
        )
        result = render_template_file(temp_template, {"project_name": "my-app"})
        assert result == "Module: my_app"

    def test_conditional_true(self, temp_template):
        """Should keep content when condition is true."""
        temp_template.write_text("Start{%- if use_pdf %}\nPDF content\n{%- endif %}End")
        result = render_template_file(temp_template, {"use_pdf": True})
        assert "PDF content" in result
        assert "Start" in result
        assert "End" in result

    def test_conditional_false(self, temp_template):
        """Should remove content when condition is false."""
        temp_template.write_text("Start{%- if use_pdf %}\nPDF content\n{%- endif %}End")
        result = render_template_file(temp_template, {"use_pdf": False})
        assert "PDF content" not in result
        assert "Start" in result
        assert "End" in result

    def test_multiple_conditionals(self, temp_template):
        """Should handle multiple conditional blocks."""
        content = """{%- if use_pdf %}PDF{%- endif %}"""
        temp_template.write_text(content)

        # PDF enabled
        result = render_template_file(temp_template, {"use_pdf": True})
        assert "PDF" in result

        # PDF disabled
        result = render_template_file(temp_template, {"use_pdf": False})
        assert "PDF" not in result

    def test_combined_variables_and_conditionals(self, temp_template):
        """Should handle both variables and conditionals."""
        content = """name: {{ project_name }}
{%- if use_pdf %}
pdf: enabled
{%- endif %}"""
        temp_template.write_text(content)
        result = render_template_file(
            temp_template, {"project_name": "test-app", "use_pdf": True}
        )
        assert "name: test-app" in result
        assert "pdf: enabled" in result

    def test_boolean_variables_not_substituted_as_strings(self, temp_template):
        """Boolean variables should only affect conditionals, not be substituted as text."""
        temp_template.write_text("Value: {{ use_pdf }}")
        result = render_template_file(temp_template, {"use_pdf": True})
        # Boolean should not be substituted as "True" string
        assert result == "Value: {{ use_pdf }}"


class TestGenerateStandalone:
    """Tests for standalone project generation."""

    @pytest.fixture
    def standalone_target(self):
        """Create a temporary directory for standalone generation."""
        with tempfile.TemporaryDirectory() as tmpdir:
            yield Path(tmpdir) / "test-standalone-app"

    @pytest.fixture
    def mock_standalone_deps(self, mocker):
        """Mock dependencies for standalone generation testing."""
        # Mock run_command to avoid actual subprocess calls
        mock_run = mocker.patch("cli.commands.setup.run_command", return_value=True)
        # Mock subprocess.run for dev server (doesn't matter, we won't wait for it)
        mock_subprocess = mocker.patch("subprocess.run")
        # Mock generate_config_file to avoid config generation
        mock_config = mocker.patch("cli.commands.setup.generate_config_file")
        return {
            "run_command": mock_run,
            "subprocess": mock_subprocess,
            "generate_config_file": mock_config,
        }

    def test_creates_target_directory(
        self, standalone_target, mock_standalone_deps, preset_config
    ):
        """Should create the target directory."""
        from cli.commands.setup import generate_standalone

        assert not standalone_target.exists()

        generate_standalone(
            target_path=standalone_target,
            target_display=str(standalone_target),
            frontend_choice="Chainlit",
            selected_modules=[],
            env_config={
                "openai_api_key": "test-key",
                "openai_base_url": "https://api.test.com",
            },
            preset="balanced",
            preset_config=preset_config,
        )

        assert standalone_target.exists()

    def test_creates_pyproject_toml(
        self, standalone_target, mock_standalone_deps, preset_config
    ):
        """Should create pyproject.toml with correct content."""
        from cli.commands.setup import generate_standalone

        generate_standalone(
            target_path=standalone_target,
            target_display=str(standalone_target),
            frontend_choice="Chainlit",
            selected_modules=[],
            env_config={
                "openai_api_key": "test-key",
                "openai_base_url": "https://api.test.com",
            },
            preset="balanced",
            preset_config=preset_config,
        )

        pyproject = standalone_target / "pyproject.toml"
        assert pyproject.exists()
        content = pyproject.read_text()
        assert "chainlit>=1.3.0" in content
        assert "rag-facile-lib" in content
        assert "python-dotenv>=1.0.0" in content

    def test_creates_app_files(
        self, standalone_target, mock_standalone_deps, preset_config
    ):
        """Should create app.py (context_loader.py replaced by pipelines)."""
        from cli.commands.setup import generate_standalone

        generate_standalone(
            target_path=standalone_target,
            target_display=str(standalone_target),
            frontend_choice="Chainlit",
            selected_modules=[],
            env_config={
                "openai_api_key": "test-key",
                "openai_base_url": "https://api.test.com",
            },
            preset="balanced",
            preset_config=preset_config,
        )

        assert (standalone_target / "app.py").exists()
        # context_loader.py no longer exists — replaced by pipelines package
        assert not (standalone_target / "context_loader.py").exists()

    def test_creates_env_file(
        self, standalone_target, mock_standalone_deps, preset_config
    ):
        """Should create .env file with provided config."""
        from cli.commands.setup import generate_standalone

        generate_standalone(
            target_path=standalone_target,
            target_display=str(standalone_target),
            frontend_choice="Chainlit",
            selected_modules=[],
            env_config={
                "openai_api_key": "my-secret-key",
                "openai_base_url": "https://custom.api.com",
            },
            preset="balanced",
            preset_config=preset_config,
        )

        env_file = standalone_target / ".env"
        assert env_file.exists()
        content = env_file.read_text()
        assert "OPENAI_API_KEY=my-secret-key" in content
        assert "OPENAI_BASE_URL=https://custom.api.com" in content
        # OPENAI_MODEL is now in ragfacile.toml, not .env
        assert "OPENAI_MODEL" not in content

    def test_pyproject_includes_library_dependency(
        self, standalone_target, mock_standalone_deps, preset_config
    ):
        """Should include rag-facile-lib as a dependency instead of copying modules."""
        from cli.commands.setup import generate_standalone

        generate_standalone(
            target_path=standalone_target,
            target_display=str(standalone_target),
            frontend_choice="Chainlit",
            selected_modules=[],
            env_config={
                "openai_api_key": "test-key",
                "openai_base_url": "https://api.test.com",
            },
            preset="balanced",
            preset_config=preset_config,
        )

        pyproject = standalone_target / "pyproject.toml"
        assert pyproject.exists()
        content = pyproject.read_text()
        assert "rag-facile-lib" in content

    def test_creates_python_version_file(
        self, standalone_target, mock_standalone_deps, preset_config
    ):
        """Should create .python-version file."""
        from cli.commands.setup import generate_standalone

        generate_standalone(
            target_path=standalone_target,
            target_display=str(standalone_target),
            frontend_choice="Chainlit",
            selected_modules=[],
            env_config={
                "openai_api_key": "test-key",
                "openai_base_url": "https://api.test.com",
            },
            preset="balanced",
            preset_config=preset_config,
        )

        python_version = standalone_target / ".python-version"
        assert python_version.exists()
        assert "3.13" in python_version.read_text()

    def test_pyproject_includes_pypdf_when_local_selected(
        self, standalone_target, mock_standalone_deps, preset_config
    ):
        """Should include rag-facile-lib dependency which provides pypdf and other modules."""
        from cli.commands.setup import generate_standalone

        generate_standalone(
            target_path=standalone_target,
            target_display=str(standalone_target),
            frontend_choice="Chainlit",
            selected_modules=["Local"],
            env_config={
                "openai_api_key": "test-key",
                "openai_base_url": "https://api.test.com",
            },
            preset="balanced",
            preset_config=preset_config,
        )

        pyproject = standalone_target / "pyproject.toml"
        content = pyproject.read_text()
        # pypdf and other dependencies come via rag-facile-lib
        assert "rag-facile-lib" in content

    def test_creates_chainlit_md_for_chainlit(
        self, standalone_target, mock_standalone_deps, preset_config
    ):
        """Should create chainlit.md for Chainlit frontend."""
        from cli.commands.setup import generate_standalone

        generate_standalone(
            target_path=standalone_target,
            target_display=str(standalone_target),
            frontend_choice="Chainlit",
            selected_modules=[],
            env_config={
                "openai_api_key": "test-key",
                "openai_base_url": "https://api.test.com",
            },
            preset="balanced",
            preset_config=preset_config,
        )

        assert (standalone_target / "chainlit.md").exists()

    def test_calls_uv_sync(
        self, standalone_target, mock_standalone_deps, preset_config
    ):
        """Should call uv sync to install dependencies."""
        from cli.commands.setup import generate_standalone

        generate_standalone(
            target_path=standalone_target,
            target_display=str(standalone_target),
            frontend_choice="Chainlit",
            selected_modules=[],
            env_config={
                "openai_api_key": "test-key",
                "openai_base_url": "https://api.test.com",
            },
            preset="balanced",
            preset_config=preset_config,
        )

        # Check run_command was called with uv sync
        calls = mock_standalone_deps["run_command"].call_args_list
        uv_sync_calls = [c for c in calls if c[0][0] == ["uv", "sync"]]
        assert len(uv_sync_calls) == 1

    def test_starts_chainlit_dev_server(
        self, standalone_target, mock_standalone_deps, preset_config
    ):
        """Should start Chainlit dev server with uv run."""
        from cli.commands.setup import generate_standalone

        generate_standalone(
            target_path=standalone_target,
            target_display=str(standalone_target),
            frontend_choice="Chainlit",
            selected_modules=[],
            env_config={
                "openai_api_key": "test-key",
                "openai_base_url": "https://api.test.com",
            },
            preset="balanced",
            preset_config=preset_config,
        )

        # Check subprocess.run was called with chainlit command
        calls = mock_standalone_deps["subprocess"].call_args_list
        assert len(calls) == 1
        cmd = calls[0][0][0]
        assert cmd == ["uv", "run", "chainlit", "run", "app.py", "-w"]

    def _run_generate_standalone(self, standalone_target, preset_config):
        """Helper: invoke generate_standalone with default Chainlit/balanced args."""
        from cli.commands.setup import generate_standalone

        generate_standalone(
            target_path=standalone_target,
            target_display=str(standalone_target),
            frontend_choice="Chainlit",
            selected_modules=[],
            env_config={
                "openai_api_key": "test-key",
                "openai_base_url": "https://api.test.com",
            },
            preset="balanced",
            preset_config=preset_config,
        )

    def test_creates_gitignore(
        self, standalone_target, mock_standalone_deps, preset_config
    ):
        """Should create a .gitignore file."""
        self._run_generate_standalone(standalone_target, preset_config)
        assert (standalone_target / ".gitignore").exists()

    def test_gitignore_protects_env_file(
        self, standalone_target, mock_standalone_deps, preset_config
    ):
        """Should include .env in .gitignore to prevent secret leaks."""
        self._run_generate_standalone(standalone_target, preset_config)
        gitignore = (standalone_target / ".gitignore").read_text()
        assert ".env" in gitignore
        assert ".venv/" in gitignore
        assert "__pycache__/" in gitignore

    def test_runs_git_init(
        self, standalone_target, mock_standalone_deps, preset_config
    ):
        """Should call git init to initialize a repository."""
        self._run_generate_standalone(standalone_target, preset_config)
        calls = mock_standalone_deps["run_command"].call_args_list
        git_init_calls = [c for c in calls if c.args[0] == ["git", "init"]]
        assert len(git_init_calls) == 1


class TestGenerateStandaloneReflex:
    """Tests for standalone Reflex project generation."""

    @pytest.fixture
    def standalone_target(self):
        """Create a temporary directory for standalone generation."""
        with tempfile.TemporaryDirectory() as tmpdir:
            yield Path(tmpdir) / "test-reflex-app"

    @pytest.fixture
    def mock_standalone_deps(self, mocker):
        """Mock dependencies for standalone generation testing."""
        mock_run = mocker.patch("cli.commands.setup.run_command", return_value=True)
        mock_subprocess = mocker.patch("subprocess.run")
        return {"run_command": mock_run, "subprocess": mock_subprocess}

    def test_creates_reflex_pyproject(
        self, standalone_target, mock_standalone_deps, preset_config
    ):
        """Should create pyproject.toml with Reflex dependencies."""
        from cli.commands.setup import generate_standalone

        generate_standalone(
            target_path=standalone_target,
            target_display=str(standalone_target),
            frontend_choice="Reflex",
            selected_modules=[],
            env_config={
                "openai_api_key": "test-key",
                "openai_base_url": "https://api.test.com",
            },
            preset="balanced",
            preset_config=preset_config,
        )

        pyproject = standalone_target / "pyproject.toml"
        assert pyproject.exists()
        content = pyproject.read_text()
        assert "reflex>=0.7.0" in content
        assert "chainlit" not in content.lower()

    def test_creates_rxconfig(
        self, standalone_target, mock_standalone_deps, preset_config
    ):
        """Should create rxconfig.py for Reflex frontend."""
        from cli.commands.setup import generate_standalone

        generate_standalone(
            target_path=standalone_target,
            target_display=str(standalone_target),
            frontend_choice="Reflex",
            selected_modules=[],
            env_config={
                "openai_api_key": "test-key",
                "openai_base_url": "https://api.test.com",
            },
            preset="balanced",
            preset_config=preset_config,
        )

        assert (standalone_target / "rxconfig.py").exists()

    def test_starts_reflex_dev_server(
        self, standalone_target, mock_standalone_deps, preset_config
    ):
        """Should start Reflex dev server with uv run."""
        from cli.commands.setup import generate_standalone

        generate_standalone(
            target_path=standalone_target,
            target_display=str(standalone_target),
            frontend_choice="Reflex",
            selected_modules=[],
            env_config={
                "openai_api_key": "test-key",
                "openai_base_url": "https://api.test.com",
            },
            preset="balanced",
            preset_config=preset_config,
        )

        calls = mock_standalone_deps["subprocess"].call_args_list
        assert len(calls) == 1
        cmd = calls[0][0][0]
        assert cmd == ["uv", "run", "reflex", "run"]


class TestWorkspaceCommand:
    """Integration tests for workspace generation."""

    def test_workspace_command_exists(self):
        """The setup command should be registered."""
        result = runner.invoke(main_app, ["setup", "--help"])
        assert result.exit_code == 0
        assert "workspace" in result.output.lower()

    def test_workspace_requires_target(self):
        """Should show help when no target provided and not interactive."""
        # In non-interactive mode, questionary returns None
        with patch("cli.commands.setup.questionary") as mock_q:
            mock_q.text.return_value.ask.return_value = None
            result = runner.invoke(main_app, ["setup"])
            assert result.exit_code == 1

    @pytest.fixture
    def mock_generation_monorepo(self, mocker, tmp_path):
        """Mock all external calls for monorepo workspace generation."""
        # Mock shutil.which to pretend moon is installed
        mocker.patch("shutil.which", return_value="/usr/bin/moon")

        # Mock questionary interactions - select monorepo mode (requires --expert)
        mock_q = mocker.patch("cli.commands.setup.questionary")
        # Use side_effect to return different values for different select calls
        mock_q.select.return_value.ask.side_effect = [
            "Monorepo (for multi-app projects)",  # First call: structure selection
            "balanced",  # Second call: preset selection
            "Chainlit",  # Third call: frontend selection
            "Local",  # Fourth call: pipeline selection
        ]
        mock_q.confirm.return_value.ask.return_value = True
        mock_q.text.return_value.ask.return_value = "test-value"

        # Mock subprocess.run for moon commands
        mock_run = mocker.patch("subprocess.run")
        mock_run.return_value = MagicMock(returncode=0, stderr="")

        # Mock shutil.copytree (copies frontend template into target workspace)
        mock_copytree = mocker.patch("shutil.copytree")

        return {
            "questionary": mock_q,
            "subprocess_run": mock_run,
            "copytree": mock_copytree,
            "tmp_path": tmp_path,
        }

    @pytest.fixture
    def mock_generation_standalone(self, mocker, tmp_path):
        """Mock all external calls for standalone workspace generation (--expert mode)."""
        # Mock shutil.which to pretend tools are installed
        mocker.patch("shutil.which", return_value="/usr/bin/uv")

        # Mock questionary interactions - select standalone mode (requires --expert)
        mock_q = mocker.patch("cli.commands.setup.questionary")
        mock_q.select.return_value.ask.side_effect = [
            "Simple (recommended for getting started)",  # First call: structure selection
            "balanced",  # Second call: preset selection
            "Chainlit",  # Third call: frontend selection
            "Local",  # Fourth call: pipeline selection
        ]
        mock_q.confirm.return_value.ask.return_value = True
        mock_q.text.return_value.ask.return_value = "test-value"

        # Mock subprocess.run
        mock_run = mocker.patch("subprocess.run")
        mock_run.return_value = MagicMock(returncode=0, stderr="")

        # Mock run_command for uv sync
        mock_run_cmd = mocker.patch("cli.commands.setup.run_command", return_value=True)

        return {
            "questionary": mock_q,
            "subprocess_run": mock_run,
            "run_command": mock_run_cmd,
            "tmp_path": tmp_path,
        }

    # Legacy fixture name for backwards compatibility
    @pytest.fixture
    def mock_generation(self, mock_generation_monorepo):
        """Alias for mock_generation_monorepo for backwards compatibility."""
        return mock_generation_monorepo

    def test_workspace_generation_flow(self, mock_generation, tmp_path):
        """Should execute the full generation flow."""
        target = tmp_path / "test-app"
        # Create the app directory structure that moon generate would create
        (target / "apps" / "chainlit-chat").mkdir(parents=True)

        result = runner.invoke(main_app, ["setup", str(target), "--expert"])

        # Should complete successfully
        assert result.exit_code == 0, f"Failed with: {result.output}"
        assert "Workspace generation complete" in result.output

    def test_workspace_creates_target_directory(self, mock_generation, tmp_path):
        """Should create target directory if it doesn't exist."""
        target = tmp_path / "new-app"
        assert not target.exists()

        runner.invoke(main_app, ["setup", str(target), "--expert"])

        assert target.exists()

    def test_workspace_runs_moon_init(self, mock_generation, tmp_path):
        """Should run moon init in the target directory."""
        target = tmp_path / "test-app"

        runner.invoke(main_app, ["setup", str(target), "--expert"])

        # Check moon init was called
        calls = mock_generation["subprocess_run"].call_args_list
        moon_init_calls = [c for c in calls if "moon" in c[0][0] and "init" in c[0][0]]
        assert len(moon_init_calls) >= 1

    def test_workspace_runs_moon_generate(self, mock_generation, tmp_path):
        """Should run moon generate for the frontend app template."""
        target = tmp_path / "test-app"

        runner.invoke(main_app, ["setup", str(target), "--expert"])

        # Check moon generate was called for the frontend app
        calls = mock_generation["subprocess_run"].call_args_list
        generate_calls = [
            c for c in calls if "moon" in c[0][0] and "generate" in c[0][0]
        ]
        assert (
            len(generate_calls) >= 1
        )  # frontend app (no more sys-config or package templates)

    def test_workspace_with_force_flag(self, mock_generation, tmp_path):
        """Should pass --force flag to moon generate."""
        target = tmp_path / "test-app"

        runner.invoke(main_app, ["setup", str(target), "--force", "--expert"])

        calls = mock_generation["subprocess_run"].call_args_list
        force_calls = [c for c in calls if "--force" in c[0][0]]
        assert len(force_calls) >= 1

    def test_workspace_copies_templates(self, mock_generation, tmp_path):
        """Should copy templates to target workspace."""
        target = tmp_path / "test-app"

        runner.invoke(main_app, ["setup", str(target), "--expert"])

        # copytree should be called for each template
        assert mock_generation["copytree"].call_count >= 1

    def test_workspace_creates_gitignore(self, mock_generation, tmp_path):
        """Should create a .gitignore at the workspace root."""
        target = tmp_path / "test-app"

        runner.invoke(main_app, ["setup", str(target), "--expert"])

        assert (target / ".gitignore").exists()

    def test_workspace_gitignore_protects_env_file(self, mock_generation, tmp_path):
        """Should include .env in the workspace .gitignore."""
        target = tmp_path / "test-app"

        runner.invoke(main_app, ["setup", str(target), "--expert"])

        gitignore = (target / ".gitignore").read_text()
        assert ".env" in gitignore
        assert ".venv/" in gitignore
        assert "__pycache__/" in gitignore

    def test_workspace_runs_git_init(self, mock_generation, tmp_path):
        """Should run git init before moon init."""
        target = tmp_path / "test-app"

        runner.invoke(main_app, ["setup", str(target), "--expert"])

        calls = mock_generation["subprocess_run"].call_args_list
        git_init_calls = [c for c in calls if c.args[0] == ["git", "init"]]
        assert len(git_init_calls) == 1


class TestStandaloneWorkspaceCommand:
    """Integration tests for standalone workspace generation via CLI."""

    @pytest.fixture
    def mock_standalone_cli(self, mocker, tmp_path):
        """Mock all external calls for standalone CLI generation (default mode, no --expert)."""
        # Mock shutil.which to pretend tools are installed
        mocker.patch("shutil.which", return_value="/usr/bin/uv")

        # Mock questionary interactions - default mode skips structure, frontend, and pipeline
        mock_q = mocker.patch("cli.commands.setup.questionary")
        mock_q.select.return_value.ask.side_effect = [
            "balanced",  # Only call: preset selection
        ]
        mock_q.confirm.return_value.ask.return_value = True
        mock_q.text.return_value.ask.return_value = "test-value"

        # Mock subprocess.run for dev server
        mock_run = mocker.patch("subprocess.run")
        mock_run.return_value = MagicMock(returncode=0, stderr="")

        # Mock run_command for uv sync
        mock_run_cmd = mocker.patch("cli.commands.setup.run_command", return_value=True)

        return {
            "questionary": mock_q,
            "subprocess_run": mock_run,
            "run_command": mock_run_cmd,
            "tmp_path": tmp_path,
        }

    def test_standalone_generation_via_cli(self, mock_standalone_cli, tmp_path):
        """Should generate standalone project via CLI."""
        target = tmp_path / "standalone-app"

        result = runner.invoke(main_app, ["setup", str(target)])

        assert result.exit_code == 0, f"Failed with: {result.output}"
        assert "Project generation complete" in result.output

    def test_standalone_creates_flat_structure(self, mock_standalone_cli, tmp_path):
        """Should create files at root, not in apps/ subdirectory."""
        target = tmp_path / "standalone-app"

        runner.invoke(main_app, ["setup", str(target)])

        # Files should be at root, not in apps/
        assert (target / "pyproject.toml").exists()
        assert (target / "app.py").exists()
        assert not (target / "apps").exists()
        assert not (target / ".moon").exists()

    def test_standalone_does_not_run_moon_init_or_generate(
        self, mock_standalone_cli, tmp_path
    ):
        """Should not run moon init or generate commands in standalone mode."""
        target = tmp_path / "standalone-app"

        runner.invoke(main_app, ["setup", str(target)])

        # Check no moon init/generate commands were called
        # (moon --version is allowed for toolchain verification)
        calls = mock_standalone_cli["subprocess_run"].call_args_list
        moon_init_calls = [c for c in calls if "moon" in str(c) and "init" in str(c)]
        moon_generate_calls = [
            c for c in calls if "moon" in str(c) and "generate" in str(c)
        ]
        assert len(moon_init_calls) == 0, "moon init should not be called"
        assert len(moon_generate_calls) == 0, "moon generate should not be called"

    def test_standalone_runs_uv_commands(self, mock_standalone_cli, tmp_path):
        """Should run uv commands in standalone mode."""
        target = tmp_path / "standalone-app"

        runner.invoke(main_app, ["setup", str(target)])

        # Check uv sync was called
        calls = mock_standalone_cli["run_command"].call_args_list
        uv_calls = [c for c in calls if "uv" in str(c[0][0])]
        assert len(uv_calls) >= 1

    def test_standalone_shows_project_generation_complete(
        self, mock_standalone_cli, tmp_path
    ):
        """Should show 'Project generation complete' (standalone-specific message)."""
        target = tmp_path / "standalone-app"

        result = runner.invoke(main_app, ["setup", str(target)])

        # Standalone mode shows "Project generation complete"
        # Monorepo mode shows "Workspace generation complete"
        assert "Project generation complete" in result.output


class TestPathNormalization:
    """Tests for macOS path normalization."""

    def test_private_tmp_normalized_in_output(self, mocker, tmp_path):
        """Should normalize /private/tmp to /tmp in output."""
        # Create a path that looks like macOS /private/tmp
        mock_q = mocker.patch("cli.commands.setup.questionary")
        # Default mode: only preset select (no structure/frontend/pipeline)
        mock_q.select.return_value.ask.side_effect = [
            "balanced",  # Preset
        ]
        mock_q.checkbox.return_value.ask.return_value = []
        mock_q.confirm.return_value.ask.return_value = False  # Abort early

        # Use a path under /private/tmp if on macOS
        result = runner.invoke(main_app, ["setup", "/private/tmp/test-app"])

        # Output should show /tmp not /private/tmp
        if "/private/tmp" in result.output:
            pytest.fail("Output contains /private/tmp instead of /tmp")


class TestStructureSelectionPrompt:
    """Tests for the project structure selection prompt."""

    def test_structure_prompt_appears_in_expert_mode(self, mocker):
        """With --expert, should ask for structure, then preset, then frontend, then pipeline."""
        mock_q = mocker.patch("cli.commands.setup.questionary")
        mock_q.select.return_value.ask.side_effect = [
            "Simple (recommended for getting started)",  # Structure
            "balanced",  # Preset
            "Chainlit",  # Frontend
            None,  # Pipeline - return None to abort
        ]

        runner.invoke(main_app, ["setup", "/tmp/test", "--expert"])

        # Should have been called four times before abort
        assert mock_q.select.call_count == 4

        # First call should be for structure
        first_call_prompt = mock_q.select.call_args_list[0][0][0]
        assert "structure" in first_call_prompt.lower()

        # Second call should be for preset
        second_call_prompt = mock_q.select.call_args_list[1][0][0]
        assert "preset" in second_call_prompt.lower()

        # Third call should be for frontend
        third_call_prompt = mock_q.select.call_args_list[2][0][0]
        assert "frontend" in third_call_prompt.lower()

        # Fourth call should be for pipeline
        fourth_call_prompt = mock_q.select.call_args_list[3][0][0]
        assert "pipeline" in fourth_call_prompt.lower()

    def test_aborts_when_structure_not_selected(self, mocker):
        """Should abort when user doesn't select a structure in expert mode."""
        mock_q = mocker.patch("cli.commands.setup.questionary")
        mock_q.select.return_value.ask.side_effect = [
            None,  # No structure selected
        ]

        result = runner.invoke(main_app, ["setup", "/tmp/test", "--expert"])

        assert result.exit_code == 1
        assert "Aborted" in result.output

    def test_default_mode_skips_structure_frontend_and_pipeline_prompts(self, mocker):
        """Without --expert, should only ask for preset (1 select)."""
        mock_q = mocker.patch("cli.commands.setup.questionary")
        mock_q.select.return_value.ask.side_effect = [
            "balanced",  # Only call: preset selection
        ]
        mock_q.text.return_value.ask.return_value = "test-key"
        mock_q.confirm.return_value.ask.return_value = False  # Abort at confirmation

        runner.invoke(main_app, ["setup", "/tmp/test"])

        # Should have been called once (preset only), no structure, frontend, or pipeline
        assert mock_q.select.call_count == 1

        # Only call should be for preset (not structure or frontend)
        first_call_prompt = mock_q.select.call_args_list[0][0][0]
        assert "preset" in first_call_prompt.lower()

    def test_default_mode_defaults_to_standalone_chainlit_and_albert_rag(self, mocker):
        """Without --expert, should default to standalone + Chainlit + Albert RAG."""
        mock_q = mocker.patch("cli.commands.setup.questionary")
        mock_q.select.return_value.ask.side_effect = [
            "balanced",  # Only select: Preset
        ]
        mock_q.text.return_value.ask.return_value = "test-key"
        mock_q.confirm.return_value.ask.return_value = False  # Abort at confirmation

        result = runner.invoke(main_app, ["setup", "/tmp/test"])

        # Summary should show Albert RAG as pipeline
        assert "Albert RAG" in result.output
        # Summary should show Chainlit as frontend
        assert "Chainlit" in result.output
        # Summary should show standalone structure
        # Rich adds ANSI codes around parentheses, so check substrings separately
        assert "Simple" in result.output
        assert "standalone" in result.output
