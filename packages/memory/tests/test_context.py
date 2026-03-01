"""Tests for the bootstrap context loader."""

from rag_facile.memory.context import bootstrap_context
from rag_facile.memory.stores import EpisodicLog, SemanticStore


class TestBootstrapContext:
    def test_returns_empty_when_no_files(self, tmp_path):
        assert bootstrap_context(tmp_path) == ""

    def test_includes_semantic_store(self, tmp_path):
        SemanticStore.create(tmp_path)
        result = bootstrap_context(tmp_path)
        assert "Semantic Store" in result
        assert "User Identity" in result

    def test_includes_profile(self, tmp_path):
        agent_dir = tmp_path / ".rag-facile" / "agent"
        agent_dir.mkdir(parents=True)
        (agent_dir / "profile.md").write_text(
            "# Profile\n- Language: fr\n", encoding="utf-8"
        )
        result = bootstrap_context(tmp_path)
        assert "Profile" in result
        assert "Language: fr" in result

    def test_includes_recent_logs(self, tmp_path):
        EpisodicLog.append_turn(tmp_path, "user", "Hello memory")
        result = bootstrap_context(tmp_path)
        assert "Recent Conversations" in result
        assert "Hello memory" in result

    def test_combines_all_sections(self, tmp_path):
        SemanticStore.create(tmp_path)
        agent_dir = tmp_path / ".rag-facile" / "agent"
        (agent_dir / "profile.md").write_text(
            "# Profile\n- Language: en\n", encoding="utf-8"
        )
        EpisodicLog.append_turn(tmp_path, "user", "Test turn")

        result = bootstrap_context(tmp_path)
        assert "Semantic Store" in result
        assert "Profile" in result
        assert "Recent Conversations" in result
        # Sections separated by dividers
        assert "---" in result

    def test_respects_log_days(self, tmp_path):
        logs_dir = tmp_path / ".rag-facile" / "agent" / "logs"
        logs_dir.mkdir(parents=True)
        (logs_dir / "2020-01-01.md").write_text("# Old\nOld entry")
        (logs_dir / "2099-12-31.md").write_text("# Future\nFuture entry")

        result = bootstrap_context(tmp_path, log_days=1)
        assert "Future entry" in result
        assert "Old entry" not in result
