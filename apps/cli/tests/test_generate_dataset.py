"""Tests for the generate-dataset command."""

import tempfile
from pathlib import Path
from typing import cast
from unittest.mock import MagicMock, patch

import pytest
from typer.testing import CliRunner

from cli.commands.providers.albert import AlbertApiProvider
from cli.commands.providers.schema import GeneratedSample, SampleMetadata
from cli.main import app as main_app


runner = CliRunner()


class TestAlbertApiProvider:
    """Tests for AlbertApiProvider."""

    @pytest.fixture
    def mock_albert_client(self, mocker):
        """Mock the Albert client."""
        mock_client = mocker.patch("cli.commands.providers.albert.AlbertClient")

        # Setup default mocks for SDK methods
        mock_instance = mock_client.return_value
        mock_instance.create_collection.return_value = MagicMock(id="col-123")
        mock_instance.upload_document.return_value = MagicMock()
        mock_instance.delete_collection.return_value = None

        return mock_client

    def test_provider_initialization(self, mock_albert_client):
        """Should initialize with API credentials."""
        provider = AlbertApiProvider(
            api_key="test-key", base_url="http://localhost:8000", model="mistral-7b"
        )

        assert provider.api_key == "test-key"
        assert provider.base_url == "http://localhost:8000"
        assert provider.model == "mistral-7b"
        # Albert client should be initialized
        mock_albert_client.assert_called_once()

    def test_base_url_stripping(self, mock_albert_client):
        """Should strip trailing slash from base_url."""
        provider = AlbertApiProvider(
            api_key="test-key", base_url="http://localhost:8000/", model="mistral-7b"
        )

        assert provider.base_url == "http://localhost:8000"

    def test_upload_documents_creates_collection(self, mock_albert_client):
        """Should create a collection and upload documents."""
        provider = AlbertApiProvider(
            api_key="test-key", base_url="http://localhost:8000", model="mistral-7b"
        )

        with tempfile.TemporaryDirectory() as tmpdir:
            tmpdir_path = Path(tmpdir)
            test_doc = tmpdir_path / "test.txt"
            test_doc.write_text("Test content")

            provider.upload_documents([str(test_doc)])

            # Should store collection ID
            assert provider.collection_id == "col-123"

            # Should call SDK methods for collection creation and document upload
            cast(
                MagicMock, provider.albert_client.create_collection
            ).assert_called_once()
            cast(MagicMock, provider.albert_client.upload_document).assert_called_once()

    def test_generate_requires_collection(self, mock_albert_client):
        """Should raise error if generate called without uploaded documents."""
        provider = AlbertApiProvider(
            api_key="test-key", base_url="http://localhost:8000", model="mistral-7b"
        )

        with pytest.raises(RuntimeError, match="No collection ID"):
            list(provider.generate(10))

    def test_cleanup_deletes_collection(self, mock_albert_client):
        """Should delete collection on cleanup."""
        provider = AlbertApiProvider(
            api_key="test-key", base_url="http://localhost:8000", model="mistral-7b"
        )

        with tempfile.TemporaryDirectory() as tmpdir:
            tmpdir_path = Path(tmpdir)
            test_doc = tmpdir_path / "test.txt"
            test_doc.write_text("Test content")
            provider.upload_documents([str(test_doc)])

        provider.cleanup()

        # Should call SDK delete method with collection ID
        cast(
            MagicMock, provider.albert_client.delete_collection
        ).assert_called_once_with("col-123")

    def test_generate_streams_samples(self, mock_albert_client):
        """Should stream samples from LLM response."""
        # Mock LLM response
        mock_chunk1 = MagicMock()
        mock_chunk1.choices = [MagicMock()]
        mock_chunk1.choices[
            0
        ].delta.content = '{"user_input": "What is AI?", "reference": "AI is artificial intelligence", "retrieved_contexts": ["AI definition text"], "_metadata": {"source_file": "test.pdf", "quality_score": 0.95, "topic_summary": "AI basics"}}\n'

        mock_chunk2 = MagicMock()
        mock_chunk2.choices = [MagicMock()]
        mock_chunk2.choices[0].delta.content = None

        mock_albert_client.return_value.chat.completions.create.return_value = [
            mock_chunk1,
            mock_chunk2,
        ]

        provider = AlbertApiProvider(
            api_key="test-key", base_url="http://localhost:8000", model="mistral-7b"
        )

        with tempfile.TemporaryDirectory() as tmpdir:
            tmpdir_path = Path(tmpdir)
            test_doc = tmpdir_path / "test.txt"
            test_doc.write_text("Test content")
            provider.upload_documents([str(test_doc)])

        samples = list(provider.generate(1))

        assert len(samples) == 1
        assert samples[0].user_input == "What is AI?"
        assert samples[0].reference == "AI is artificial intelligence"

    def test_initialization_with_valid_credentials(self, mock_albert_client):
        """Should initialize successfully with valid credentials."""
        provider = AlbertApiProvider(
            api_key="test-key", base_url="http://localhost:8000", model="mistral-7b"
        )

        assert provider.api_key == "test-key"
        assert provider.base_url == "http://localhost:8000"
        assert provider.model == "mistral-7b"
        mock_albert_client.assert_called()


class TestGenerateDatasetCommand:
    """Tests for the generate-dataset CLI command."""

    def test_generate_command_requires_provider(self):
        """Should fail if --provider is not specified."""
        with tempfile.TemporaryDirectory() as tmpdir:
            result = runner.invoke(
                main_app, ["generate-dataset", tmpdir, "--provider", ""]
            )
            assert result.exit_code != 0

    def test_generate_invalid_provider(self):
        """Should fail with invalid provider name."""
        with tempfile.TemporaryDirectory() as tmpdir:
            result = runner.invoke(
                main_app, ["generate-dataset", tmpdir, "--provider", "invalid"]
            )
            assert result.exit_code != 0
            assert "Unknown provider" in result.output or "invalid" in result.output

    def test_generate_letta_requires_env_vars(self):
        """Letta provider should require LETTA_API_KEY and DATA_FOUNDRY_AGENT_ID."""
        with tempfile.TemporaryDirectory() as tmpdir:
            tmpdir_path = Path(tmpdir)
            # Create a test document
            (tmpdir_path / "test.txt").write_text("Test content")

            result = runner.invoke(
                main_app,
                ["generate-dataset", str(tmpdir_path), "--provider", "letta"],
                env={},
            )

            assert result.exit_code != 0
            assert (
                "LETTA_API_KEY" in result.output
                or "DATA_FOUNDRY_AGENT_ID" in result.output
            )

    def test_generate_no_documents_error(self):
        """Should fail if no documents found in directory."""
        with tempfile.TemporaryDirectory() as tmpdir:
            result = runner.invoke(
                main_app,
                ["generate-dataset", tmpdir, "--provider", "letta"],
                env={"LETTA_API_KEY": "test-key", "DATA_FOUNDRY_AGENT_ID": "test-id"},
            )

            assert result.exit_code != 0
            assert "No documents found" in result.output

    def test_generate_shows_provider_info(self):
        """Should display provider information in output."""
        with tempfile.TemporaryDirectory() as tmpdir:
            tmpdir_path = Path(tmpdir)
            # Create a test document
            (tmpdir_path / "test.txt").write_text("Test content")

            with patch("cli.commands.providers.get_provider") as mock_get_provider:
                # Mock provider to fail early (we just want to check output)
                mock_provider = MagicMock()
                mock_provider.upload_documents.side_effect = Exception("Test error")
                mock_get_provider.return_value = mock_provider

                result = runner.invoke(
                    main_app,
                    ["generate-dataset", str(tmpdir_path), "--provider", "albert"],
                    env={
                        "OPENAI_API_KEY": "test-key",
                        "OPENAI_BASE_URL": "http://localhost:8000",
                        "OPENAI_MODEL": "test-model",
                    },
                )

                # Should show provider in output
                assert "Provider: albert" in result.output


class TestGeneratedSampleSchema:
    """Tests for GeneratedSample and SampleMetadata classes."""

    def test_sample_to_dict(self):
        """Should convert sample to Ragas-compatible dict."""
        metadata = SampleMetadata(
            source_file="test.pdf", quality_score=0.95, topic_summary="Test topic"
        )
        sample = GeneratedSample(
            user_input="What is this?",
            retrieved_contexts=["Context 1", "Context 2"],
            reference="This is an answer",
            metadata=metadata,
        )

        result = sample.to_dict()

        assert result["user_input"] == "What is this?"
        assert result["reference"] == "This is an answer"
        assert result["retrieved_contexts"] == ["Context 1", "Context 2"]
        assert result["_metadata"]["source_file"] == "test.pdf"
        assert result["_metadata"]["quality_score"] == 0.95

    def test_sample_from_dict(self):
        """Should create sample from dict."""
        data = {
            "user_input": "What is this?",
            "reference": "This is an answer",
            "retrieved_contexts": ["Context 1"],
            "_metadata": {
                "source_file": "test.pdf",
                "quality_score": 0.95,
                "topic_summary": "Test",
            },
        }

        sample = GeneratedSample.from_dict(data)

        assert sample.user_input == "What is this?"
        assert sample.reference == "This is an answer"
        assert sample.metadata.source_file == "test.pdf"
