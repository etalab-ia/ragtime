"""Tests for the standard file-operation memory tools (read / write / edit / search)."""

import pytest

from rag_facile.memory.tool import (
    _safe_resolve,
    memory_edit,
    memory_read,
    memory_search,
    memory_write,
    set_workspace_root,
)


# ── Fixtures ──────────────────────────────────────────────────────────────────


@pytest.fixture(autouse=True)
def _set_workspace(tmp_path):
    """Point tool workspace to a fresh temp directory for every test."""
    set_workspace_root(tmp_path)
    yield
    set_workspace_root(None)


@pytest.fixture()
def agent_dir(tmp_path):
    """Create and return the .agent/ directory."""
    d = tmp_path / ".agent"
    d.mkdir()
    return d


@pytest.fixture()
def memory_file(agent_dir):
    """Create a sample MEMORY.md and return its path."""
    content = (
        "---\nupdated: 2026-03-01\n---\n\n"
        "# Agent Memory\n\n"
        "## User Identity\n"
        "- Name: Luis\n"
        "- Role: Developer\n\n"
        "## Key Facts\n"
        "- Preset: balanced\n"
    )
    path = agent_dir / "MEMORY.md"
    path.write_text(content, encoding="utf-8")
    return path


# ── _safe_resolve ─────────────────────────────────────────────────────────────


class TestSafeResolve:
    def test_normal_path(self, agent_dir):
        result = _safe_resolve("MEMORY.md", agent_dir)
        assert result == (agent_dir / "MEMORY.md").resolve()

    def test_nested_path(self, agent_dir):
        result = _safe_resolve("logs/today.md", agent_dir)
        assert result.parent.name == "logs"

    def test_rejects_traversal(self, agent_dir):
        with pytest.raises(ValueError, match=""):
            _safe_resolve("../../etc/passwd", agent_dir)

    def test_rejects_absolute_path(self, agent_dir):
        with pytest.raises(ValueError, match=""):
            _safe_resolve("/etc/passwd", agent_dir)


# ── memory_read ───────────────────────────────────────────────────────────────


class TestMemoryRead:
    def test_no_workspace(self):
        set_workspace_root(None)
        result = memory_read.forward(".")
        assert "unavailable" in result.lower()

    def test_dir_listing(self, memory_file):
        result = memory_read.forward(".")
        assert "MEMORY.md" in result
        assert "Files in .agent" in result

    def test_read_file(self, memory_file):
        result = memory_read.forward("MEMORY.md")
        assert "Luis" in result
        # Should have line numbers
        assert "\t" in result

    def test_read_file_with_range(self, memory_file):
        result = memory_read.forward("MEMORY.md:1-3")
        # Should only include first 3 lines
        lines = [line for line in result.splitlines() if line.strip()]
        assert len(lines) <= 3

    def test_file_not_found(self, agent_dir):
        result = memory_read.forward("nonexistent.md")
        assert "not found" in result.lower()

    def test_traversal_rejected(self, agent_dir):
        result = memory_read.forward("../../etc/passwd")
        assert "denied" in result.lower()

    def test_auto_bootstrap(self, agent_dir):
        """Reading MEMORY.md when it doesn't exist should create it from template."""
        result = memory_read.forward("MEMORY.md")
        assert "User Identity" in result
        assert (agent_dir / "MEMORY.md").exists()

    def test_subdir_listing(self, agent_dir):
        logs = agent_dir / "logs"
        logs.mkdir()
        (logs / "2026-03-01.md").write_text("# Log", encoding="utf-8")
        result = memory_read.forward("logs")
        assert "2026-03-01.md" in result


# ── memory_write ──────────────────────────────────────────────────────────────


class TestMemoryWrite:
    def test_no_workspace(self):
        set_workspace_root(None)
        result = memory_write.forward("test.md", "content")
        assert "unavailable" in result.lower()

    def test_create_file(self, agent_dir):
        result = memory_write.forward("notes.md", "# Notes\nHello")
        assert "Written" in result
        assert (agent_dir / "notes.md").exists()
        assert (agent_dir / "notes.md").read_text() == "# Notes\nHello"

    def test_overwrite_file(self, memory_file):
        memory_write.forward("MEMORY.md", "New content")
        assert memory_file.read_text() == "New content"

    def test_creates_parent_dirs(self, agent_dir):
        memory_write.forward("deep/nested/file.md", "content")
        assert (agent_dir / "deep" / "nested" / "file.md").exists()

    def test_traversal_rejected(self, agent_dir):
        result = memory_write.forward("../../evil.md", "bad")
        assert "denied" in result.lower()

    def test_reports_char_count(self, agent_dir):
        result = memory_write.forward("test.md", "hello")
        assert "5 chars" in result


# ── memory_edit ───────────────────────────────────────────────────────────────


class TestMemoryEdit:
    def test_no_workspace(self):
        set_workspace_root(None)
        result = memory_edit.forward("MEMORY.md", "old", "new")
        assert "unavailable" in result.lower()

    def test_successful_edit(self, memory_file):
        result = memory_edit.forward(
            "MEMORY.md", "Preset: balanced", "Preset: accurate"
        )
        assert "replaced 1" in result.lower()
        content = memory_file.read_text()
        assert "Preset: accurate" in content
        assert "Preset: balanced" not in content

    def test_not_found(self, memory_file):
        result = memory_edit.forward("MEMORY.md", "nonexistent text", "replacement")
        assert "not found" in result.lower()

    def test_not_unique(self, agent_dir):
        path = agent_dir / "test.md"
        path.write_text("hello world\nhello world", encoding="utf-8")
        result = memory_edit.forward("test.md", "hello world", "goodbye")
        assert "2 matches" in result.lower()

    def test_file_not_found(self, agent_dir):
        result = memory_edit.forward("nonexistent.md", "old", "new")
        assert "not found" in result.lower()

    def test_traversal_rejected(self, agent_dir):
        result = memory_edit.forward("../../evil.md", "old", "new")
        assert "denied" in result.lower()

    def test_cannot_edit_directory(self, agent_dir):
        (agent_dir / "subdir").mkdir()
        result = memory_edit.forward("subdir", "old", "new")
        assert "directory" in result.lower()


# ── memory_search ─────────────────────────────────────────────────────────────


class TestMemorySearch:
    def test_no_workspace(self):
        set_workspace_root(None)
        result = memory_search.forward("anything")
        assert "unavailable" in result.lower()

    def test_search_finds_content(self, memory_file):
        result = memory_search.forward("Luis Developer")
        assert "result" in result.lower()
        assert "MEMORY.md" in result

    def test_search_no_results(self, memory_file):
        result = memory_search.forward("kubernetes orchestration")
        assert "no results" in result.lower()

    def test_search_returns_line_references(self, memory_file):
        result = memory_search.forward("balanced preset")
        # Should contain file:line-line references
        assert "MEMORY.md:" in result

    def test_search_across_multiple_files(self, agent_dir):
        """Search should find content in different files."""
        # MEMORY.md
        (agent_dir / "MEMORY.md").write_text(
            "## Key Facts\n- Albert is an API\n", encoding="utf-8"
        )
        # Log file
        logs = agent_dir / "logs"
        logs.mkdir()
        (logs / "2026-03-01.md").write_text(
            "## 14:30\nAlbert API returned an error\n", encoding="utf-8"
        )
        result = memory_search.forward("Albert API")
        assert "MEMORY.md" in result
        assert "logs/" in result

    def test_search_output_format(self, memory_file):
        result = memory_search.forward("Luis")
        # Should have numbered results with scores
        assert "1." in result
        # Should have the drill-in hint
        assert "memory_read" in result

    def test_search_empty_agent_dir(self, agent_dir):
        result = memory_search.forward("anything")
        assert "no results" in result.lower()

    def test_search_uses_albert_when_credentials_present(
        self, memory_file, monkeypatch
    ):
        """When OPENAI_API_KEY is set, Albert semantic results are fused in."""
        sem_result = {
            "file": "MEMORY.md",
            "line_start": 3,
            "line_end": 5,
            "score": 0.9,
            "snippet": "Albert semantic hit",
        }

        monkeypatch.setenv("OPENAI_API_KEY", "test-key")

        import rag_facile.memory.tool as tool_mod

        # Reset singleton so _get_albert_index creates a fresh one
        tool_mod._albert_index = None

        mock_index = __import__("unittest.mock", fromlist=["MagicMock"]).MagicMock()
        mock_index.search.return_value = [sem_result]

        with __import__("unittest.mock", fromlist=["patch"]).patch(
            "rag_facile.memory.tool._get_albert_index", return_value=mock_index
        ):
            result = memory_search.forward("Albert")

        assert "result" in result.lower()
        mock_index.search.assert_called_once()

    def test_search_falls_back_to_keyword_when_no_credentials(
        self, memory_file, monkeypatch
    ):
        """When no API key is present, memory_search uses keyword results only."""
        monkeypatch.delenv("OPENAI_API_KEY", raising=False)
        monkeypatch.delenv("ALBERT_API_KEY", raising=False)

        import rag_facile.memory.tool as tool_mod

        tool_mod._albert_index = None

        result = memory_search.forward("Luis Developer")
        # Keyword search still finds content
        assert "result" in result.lower()
