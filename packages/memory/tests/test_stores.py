"""Tests for the three memory storage backends."""

from datetime import datetime

import pytest

from rag_facile.memory.stores import (
    EpisodicLog,
    SemanticStore,
    SessionSnapshot,
    _slugify,
)


# ── Fixtures ──────────────────────────────────────────────────────────────────


@pytest.fixture()
def workspace(tmp_path):
    """Bare workspace — no pre-existing memory files."""
    return tmp_path


@pytest.fixture()
def workspace_with_memory(tmp_path):
    """Workspace with a pre-populated memory.md."""
    agent_dir = tmp_path / ".rag-facile" / "agent"
    agent_dir.mkdir(parents=True)
    (agent_dir / "memory.md").write_text(
        "---\nupdated: 2026-03-01\n---\n\n"
        "# Agent Memory\n\n"
        "## User Identity\n"
        "- Name: Luis\n"
        "- Role: Developer\n\n"
        "## Preferences\n"
        "- [2026-03-01] Language: fr\n\n"
        "## Project State\n"
        "- Preset: balanced\n\n"
        "## Key Facts\n"
        "- [2026-03-01] Working on legal RAG\n\n"
        "## Routing Table\n"
        "| Topic | File |\n"
        "|-------|------|\n\n"
        "## Recent Context\n"
        "- [2026-03-01] Testing memory system\n",
        encoding="utf-8",
    )
    return tmp_path


# ── SemanticStore ─────────────────────────────────────────────────────────────


class TestSemanticStoreLoad:
    def test_returns_empty_when_no_file(self, workspace):
        assert SemanticStore.load(workspace) == ""

    def test_returns_content(self, workspace_with_memory):
        content = SemanticStore.load(workspace_with_memory)
        assert "Agent Memory" in content
        assert "Luis" in content

    def test_respects_max_lines_cap(self, workspace_with_memory):
        content = SemanticStore.load(workspace_with_memory, max_lines=5)
        assert content.count("\n") <= 4  # 5 lines = 4 newlines


class TestSemanticStoreReadSection:
    def test_reads_known_section(self, workspace_with_memory):
        entries = SemanticStore.read_section(workspace_with_memory, "User Identity")
        assert any("Luis" in e for e in entries)

    def test_returns_empty_for_missing_section(self, workspace_with_memory):
        assert SemanticStore.read_section(workspace_with_memory, "Nonexistent") == []

    def test_returns_empty_when_no_file(self, workspace):
        assert SemanticStore.read_section(workspace, "Key Facts") == []

    def test_excludes_blank_lines(self, workspace_with_memory):
        entries = SemanticStore.read_section(workspace_with_memory, "Key Facts")
        assert all(e.strip() for e in entries)


class TestSemanticStoreCreate:
    def test_creates_file(self, workspace):
        path = SemanticStore.create(workspace)
        assert path.exists()
        content = path.read_text()
        assert "## User Identity" in content
        assert "## Key Facts" in content

    def test_creates_directories(self, workspace):
        SemanticStore.create(workspace)
        assert (workspace / ".rag-facile" / "agent").is_dir()


class TestSemanticStoreAddEntry:
    def test_adds_to_existing_section(self, workspace_with_memory):
        SemanticStore.add_entry(workspace_with_memory, "Key Facts", "Uses Albert API")
        content = (
            workspace_with_memory / ".rag-facile" / "agent" / "memory.md"
        ).read_text()
        assert "Uses Albert API" in content
        assert "Working on legal RAG" in content  # existing entry preserved

    def test_date_stamps_entry(self, workspace_with_memory):
        SemanticStore.add_entry(workspace_with_memory, "Key Facts", "Test fact")
        content = (
            workspace_with_memory / ".rag-facile" / "agent" / "memory.md"
        ).read_text()
        # Should have a date stamp like [2026-03-01]
        assert "- [" in content

    def test_creates_file_if_missing(self, workspace):
        SemanticStore.add_entry(workspace, "Key Facts", "First fact")
        path = workspace / ".rag-facile" / "agent" / "memory.md"
        assert path.exists()
        assert "First fact" in path.read_text()

    def test_updates_frontmatter_date(self, workspace_with_memory):
        SemanticStore.add_entry(workspace_with_memory, "Key Facts", "New fact")
        content = (
            workspace_with_memory / ".rag-facile" / "agent" / "memory.md"
        ).read_text()
        # Date should be today's date
        from datetime import date

        assert f"updated: {date.today().isoformat()}" in content


class TestSemanticStoreUpdateFrontmatter:
    def test_updates_existing_field(self, workspace_with_memory):
        SemanticStore.update_frontmatter(workspace_with_memory, updated="2099-12-31")
        content = (
            workspace_with_memory / ".rag-facile" / "agent" / "memory.md"
        ).read_text()
        assert "updated: 2099-12-31" in content

    def test_no_op_when_no_file(self, workspace):
        SemanticStore.update_frontmatter(workspace, updated="2099-12-31")
        # Should not raise


# ── EpisodicLog ───────────────────────────────────────────────────────────────


class TestEpisodicLogAppendTurn:
    def test_creates_log_file(self, workspace):
        EpisodicLog.append_turn(workspace, "user", "Bonjour")
        path = EpisodicLog.today_path(workspace)
        assert path.exists()

    def test_user_label_is_vous(self, workspace):
        EpisodicLog.append_turn(workspace, "user", "Bonjour")
        content = EpisodicLog.today_path(workspace).read_text()
        assert "Vous" in content

    def test_assistant_label(self, workspace):
        EpisodicLog.append_turn(workspace, "assistant", "Hello")
        content = EpisodicLog.today_path(workspace).read_text()
        assert "Assistant" in content

    def test_content_preserved(self, workspace):
        EpisodicLog.append_turn(workspace, "user", "What is chunking?")
        content = EpisodicLog.today_path(workspace).read_text()
        assert "chunking" in content

    def test_multiple_turns(self, workspace):
        EpisodicLog.append_turn(workspace, "user", "Q1")
        EpisodicLog.append_turn(workspace, "assistant", "A1")
        EpisodicLog.append_turn(workspace, "user", "Q2")
        content = EpisodicLog.today_path(workspace).read_text()
        assert "Q1" in content
        assert "A1" in content
        assert "Q2" in content

    def test_date_header_written_once(self, workspace):
        EpisodicLog.append_turn(workspace, "user", "First")
        EpisodicLog.append_turn(workspace, "user", "Second")
        content = EpisodicLog.today_path(workspace).read_text()
        from datetime import date

        assert content.count(f"# {date.today().isoformat()}") == 1


class TestEpisodicLogAppendCheckpoint:
    def test_writes_checkpoint(self, workspace):
        EpisodicLog.append_checkpoint(
            workspace,
            summary="Discussed chunking",
            decisions="top_k set to 10",
            facts="User prefers accurate preset",
        )
        content = EpisodicLog.today_path(workspace).read_text()
        assert "Checkpoint" in content
        assert "Discussed chunking" in content
        assert "top_k set to 10" in content

    def test_optional_fields_omitted(self, workspace):
        EpisodicLog.append_checkpoint(workspace, summary="Quick chat")
        content = EpisodicLog.today_path(workspace).read_text()
        assert "Decisions" not in content
        assert "New facts" not in content


class TestEpisodicLogReadRecent:
    def test_returns_empty_when_no_logs(self, workspace):
        assert EpisodicLog.read_recent(workspace) == ""

    def test_returns_today_log(self, workspace):
        EpisodicLog.append_turn(workspace, "user", "Hello")
        result = EpisodicLog.read_recent(workspace, days=1)
        assert "Hello" in result

    def test_respects_days_limit(self, workspace):
        # Create two log files with different dates
        logs_dir = workspace / ".rag-facile" / "agent" / "logs"
        logs_dir.mkdir(parents=True)
        (logs_dir / "2026-02-28.md").write_text("# 2026-02-28\nOld entry")
        (logs_dir / "2026-03-01.md").write_text("# 2026-03-01\nNew entry")
        result = EpisodicLog.read_recent(workspace, days=1)
        assert "New entry" in result
        assert "Old entry" not in result


# ── SessionSnapshot ───────────────────────────────────────────────────────────


class TestSlugify:
    def test_basic(self):
        assert (
            _slugify("Discussed chunking and presets")
            == "discussed-chunking-and-presets"
        )

    def test_max_words(self):
        slug = _slugify("One two three four five six seven", max_words=3)
        assert slug == "one-two-three"

    def test_special_chars_removed(self):
        assert _slugify("What's the best config?") == "whats-the-best-config"

    def test_empty_string(self):
        assert _slugify("") == "session"


class TestSessionSnapshotSave:
    def test_creates_file(self, workspace):
        turns = [
            {"role": "user", "content": "Hello"},
            {"role": "assistant", "content": "Hi!"},
        ]
        path = SessionSnapshot.save(
            workspace,
            turns=turns,
            summary="Test session",
            topics=["testing"],
            start_time=datetime(2026, 3, 1, 21, 30),
        )
        assert path.exists()
        assert "test-session" in path.name

    def test_contains_frontmatter(self, workspace):
        turns = [{"role": "user", "content": "Q"}]
        path = SessionSnapshot.save(
            workspace,
            turns=turns,
            summary="Frontmatter test",
            topics=["meta"],
            start_time=datetime(2026, 3, 1, 21, 30),
        )
        content = path.read_text()
        assert "---" in content
        assert "summary: Frontmatter test" in content
        assert "turns: 1" in content

    def test_contains_transcript(self, workspace):
        turns = [
            {"role": "user", "content": "What is RAG?"},
            {"role": "assistant", "content": "RAG stands for..."},
        ]
        path = SessionSnapshot.save(
            workspace,
            turns=turns,
            summary="RAG basics",
            topics=["RAG"],
            start_time=datetime(2026, 3, 1, 21, 30),
        )
        content = path.read_text()
        assert "What is RAG?" in content
        assert "RAG stands for..." in content


class TestSessionSnapshotListRecent:
    def test_returns_empty_when_no_sessions(self, workspace):
        assert SessionSnapshot.list_recent(workspace) == []

    def test_returns_saved_sessions(self, workspace):
        turns = [{"role": "user", "content": "Hi"}]
        SessionSnapshot.save(
            workspace,
            turns=turns,
            summary="Session one",
            topics=[],
            start_time=datetime(2026, 3, 1, 21, 0),
        )
        result = SessionSnapshot.list_recent(workspace)
        assert len(result) == 1

    def test_respects_n_limit(self, workspace):
        turns = [{"role": "user", "content": "Hi"}]
        for i in range(5):
            SessionSnapshot.save(
                workspace,
                turns=turns,
                summary=f"Session {i}",
                topics=[],
                start_time=datetime(2026, 3, 1, 21, i),
            )
        assert len(SessionSnapshot.list_recent(workspace, n=3)) == 3
