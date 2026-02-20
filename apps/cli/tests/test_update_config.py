"""Tests for the update_config tool and its helper functions."""

import subprocess
import tomllib
from unittest.mock import patch

import pytest

from cli.commands.chat.tools import (
    _coerce_value,
    _get_nested,
    _set_nested,
    set_workspace_root,
    update_config,
)


# ── Fixtures ──────────────────────────────────────────────────────────────────


@pytest.fixture(autouse=True)
def reset_workspace():
    """Reset workspace root before and after each test."""
    set_workspace_root(None)
    yield
    set_workspace_root(None)


@pytest.fixture()
def workspace(tmp_path):
    """Workspace with a minimal ragfacile.toml."""
    config = tmp_path / "ragfacile.toml"
    config.write_text(
        '[retrieval]\ntop_k = 10\nstrategy = "semantic"\n\n[generation]\nmodel = "openweight-medium"\n',
        encoding="utf-8",
    )
    set_workspace_root(tmp_path)
    return tmp_path


# ── _coerce_value ─────────────────────────────────────────────────────────────


class TestCoerceValue:
    def test_integer(self):
        assert _coerce_value("10") == 10
        assert isinstance(_coerce_value("10"), int)

    def test_float(self):
        assert _coerce_value("3.14") == pytest.approx(3.14)
        assert isinstance(_coerce_value("3.14"), float)

    def test_bool_true(self):
        assert _coerce_value("true") is True
        assert _coerce_value("True") is True

    def test_bool_false(self):
        assert _coerce_value("false") is False
        assert _coerce_value("False") is False

    def test_string_passthrough(self):
        assert _coerce_value("openweight-large") == "openweight-large"

    def test_zero_is_int(self):
        assert _coerce_value("0") == 0
        assert isinstance(_coerce_value("0"), int)


# ── _get_nested / _set_nested ─────────────────────────────────────────────────


class TestNestedHelpers:
    def test_get_existing_key(self):
        data = {"retrieval": {"top_k": 10}}
        assert _get_nested(data, ["retrieval", "top_k"]) == 10

    def test_get_missing_key_returns_none(self):
        data = {"retrieval": {"top_k": 10}}
        assert _get_nested(data, ["retrieval", "top_n"]) is None

    def test_get_missing_section_returns_none(self):
        data = {}
        assert _get_nested(data, ["retrieval", "top_k"]) is None

    def test_set_existing_key(self):
        data = {"retrieval": {"top_k": 10}}
        _set_nested(data, ["retrieval", "top_k"], 20)
        assert data["retrieval"]["top_k"] == 20

    def test_set_creates_missing_sections(self):
        data: dict = {}
        _set_nested(data, ["new_section", "new_key"], 42)
        assert data["new_section"]["new_key"] == 42


# ── update_config ─────────────────────────────────────────────────────────────


class TestUpdateConfig:
    def _run(self, key: str, value: str, answer: str = "o") -> str:
        with (
            patch("cli.commands.chat.tools.console.input", return_value=answer),
            patch("cli.commands.chat.tools.console.print"),
        ):
            return update_config(key, value)

    def test_updates_value_on_confirm(self, workspace):
        result = self._run("retrieval.top_k", "20")
        assert "✓" in result
        config = tomllib.loads(
            (workspace / "ragfacile.toml").read_text(encoding="utf-8")
        )
        assert config["retrieval"]["top_k"] == 20

    def test_cancels_on_n(self, workspace):
        result = self._run("retrieval.top_k", "20", answer="n")
        assert "annulée" in result.lower()
        config = tomllib.loads(
            (workspace / "ragfacile.toml").read_text(encoding="utf-8")
        )
        assert config["retrieval"]["top_k"] == 10  # unchanged

    def test_coerces_to_int(self, workspace):
        self._run("retrieval.top_k", "15")
        config = tomllib.loads(
            (workspace / "ragfacile.toml").read_text(encoding="utf-8")
        )
        assert config["retrieval"]["top_k"] == 15
        assert isinstance(config["retrieval"]["top_k"], int)

    def test_updates_string_value(self, workspace):
        self._run("generation.model", "openweight-large")
        config = tomllib.loads(
            (workspace / "ragfacile.toml").read_text(encoding="utf-8")
        )
        assert config["generation"]["model"] == "openweight-large"

    def test_creates_new_key(self, workspace):
        self._run("retrieval.top_n", "5")
        config = tomllib.loads(
            (workspace / "ragfacile.toml").read_text(encoding="utf-8")
        )
        assert config["retrieval"]["top_n"] == 5

    def test_commits_to_git(self, workspace):
        with (
            patch("cli.commands.chat.tools.console.input", return_value="o"),
            patch("cli.commands.chat.tools.console.print"),
            patch("cli.commands.chat.tools.subprocess.run") as mock_run,
        ):
            mock_run.return_value.returncode = 0
            result = update_config("retrieval.top_k", "20")

        assert mock_run.call_count == 2  # git add + git commit
        first_call = mock_run.call_args_list[0][0][0]
        assert first_call == ["git", "add", "ragfacile.toml"]
        assert "committé" in result

    def test_skips_commit_silently_on_git_error(self, workspace):
        with (
            patch("cli.commands.chat.tools.console.input", return_value="o"),
            patch("cli.commands.chat.tools.console.print"),
            patch(
                "cli.commands.chat.tools.subprocess.run",
                side_effect=subprocess.CalledProcessError(1, "git"),
            ),
        ):
            result = update_config("retrieval.top_k", "20")
        assert "✓" in result
        assert "committé" not in result  # committed note absent

    def test_returns_hint_when_no_workspace(self):
        result = self._run("retrieval.top_k", "20")
        assert "No workspace detected" in result

    def test_rejects_invalid_key(self, workspace):
        result = self._run("retrieval..top_k", "20")
        assert "Invalid config key" in result

    def test_handles_keyboard_interrupt_on_prompt(self, workspace):
        with (
            patch(
                "cli.commands.chat.tools.console.input", side_effect=KeyboardInterrupt
            ),
            patch("cli.commands.chat.tools.console.print"),
        ):
            result = update_config("retrieval.top_k", "20")
        assert "Annulé" in result
