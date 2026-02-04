"""Tests for the eval generate command."""

import tempfile
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest
from cli.commands.eval.providers.albert import AlbertApiProvider
from cli.commands.eval.providers.schema import GeneratedSample, SampleMetadata
from cli.main import app as main_app
from typer.testing import CliRunner

runner = CliRunner()


class TestAlbertApiProvider:
    """Tests for AlbertApiProvider."""

    @pytest.fixture
    def mock_requests(self, mocker):
        """Mock the requests library."""
        mock_req = mocker.patch("cli.commands.eval.providers.albert.requests")
        return mock_req

    @pytest.fixture
    def mock_openai(self, mocker):
        """Mock the OpenAI client."""
        mock_client = mocker.patch("cli.commands.eval.providers.albert.OpenAI")
        return mock_client

    def test_provider_initialization(self, mock_requests, mock_openai):
        """Should initialize with API credentials."""
        provider = AlbertApiProvider(
            api_key="test-key", base_url="http://localhost:8000", model="mistral-7b"
        )

        assert provider.api_key == "test-key"
        assert provider.base_url == "http://localhost:8000"
        assert provider.model == "mistral-7b"
        # OpenAI client should be initialized
        mock_openai.assert_called_once()

    def test_base_url_stripping(self, mock_requests, mock_openai):
        """Should strip trailing slash from base_url."""
        provider = AlbertApiProvider(
            api_key="test-key", base_url="http://localhost:8000/", model="mistral-7b"
        )

        assert provider.base_url == "http://localhost:8000"

    def test_upload_documents_creates_collection(self, mock_requests, mock_openai):
        """Should create a collection and upload documents."""
        # Mock responses for collection creation and document upload
        collection_response = MagicMock()
        collection_response.json.return_value = {"id": "col-123"}

        upload_response = MagicMock()
        upload_response.status_code = 201
        upload_response.raise_for_status = MagicMock()

        mock_requests.post.side_effect = [collection_response, upload_response]

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

            # Should call POST for collection creation
            calls = mock_requests.post.call_args_list
            assert len(calls) >= 2  # Collection creation + document upload

            # First call should be to create collection
            first_call = calls[0]
            assert "/collections" in first_call[0][0]

    def test_generate_requires_collection(self, mock_requests, mock_openai):
        """Should raise error if generate called without uploaded documents."""
        provider = AlbertApiProvider(
            api_key="test-key", base_url="http://localhost:8000", model="mistral-7b"
        )

        with pytest.raises(RuntimeError, match="No collection ID"):
            list(provider.generate(10))

    def test_cleanup_deletes_collection(self, mock_requests, mock_openai):
        """Should delete collection on cleanup."""
        # Mock responses for collection creation and document upload
        collection_response = MagicMock()
        collection_response.json.return_value = {"id": "col-123"}

        upload_response = MagicMock()
        upload_response.status_code = 201
        upload_response.raise_for_status = MagicMock()

        mock_requests.post.side_effect = [collection_response, upload_response]
        mock_requests.delete.return_value = MagicMock()

        provider = AlbertApiProvider(
            api_key="test-key", base_url="http://localhost:8000", model="mistral-7b"
        )

        with tempfile.TemporaryDirectory() as tmpdir:
            tmpdir_path = Path(tmpdir)
            test_doc = tmpdir_path / "test.txt"
            test_doc.write_text("Test content")
            provider.upload_documents([str(test_doc)])

        provider.cleanup()

        # Should call DELETE with collection ID
        delete_calls = mock_requests.delete.call_args_list
        assert len(delete_calls) >= 1
        assert "col-123" in delete_calls[0][0][0]

    def test_generate_streams_samples(self, mock_requests, mock_openai):
        """Should stream samples from LLM response."""
        # Mock responses for collection creation and document upload
        collection_response = MagicMock()
        collection_response.json.return_value = {"id": "col-123"}

        upload_response = MagicMock()
        upload_response.status_code = 201
        upload_response.raise_for_status = MagicMock()

        mock_requests.post.side_effect = [collection_response, upload_response]

        # Mock LLM response
        mock_chunk1 = MagicMock()
        mock_chunk1.choices = [MagicMock()]
        mock_chunk1.choices[
            0
        ].delta.content = '{"user_input": "What is AI?", "reference": "AI is artificial intelligence", "retrieved_contexts": ["AI definition text"], "_metadata": {"source_file": "test.pdf", "quality_score": 0.95, "topic_summary": "AI basics"}}\n'

        mock_chunk2 = MagicMock()
        mock_chunk2.choices = [MagicMock()]
        mock_chunk2.choices[0].delta.content = None

        mock_openai.return_value.chat.completions.create.return_value = [
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

    def test_initialization_with_valid_credentials(self, mock_openai):
        """Should initialize successfully with valid credentials."""
        provider = AlbertApiProvider(
            api_key="test-key", base_url="http://localhost:8000", model="mistral-7b"
        )

        assert provider.api_key == "test-key"
        assert provider.base_url == "http://localhost:8000"
        assert provider.model == "mistral-7b"
        mock_openai.assert_called()


class TestEvalGenerateCommand:
    """Tests for the eval generate CLI command."""

    def test_generate_command_requires_provider(self):
        """Should fail if --provider is not specified."""
        with tempfile.TemporaryDirectory() as tmpdir:
            result = runner.invoke(
                main_app, ["eval", "generate", tmpdir, "--provider", ""]
            )
            assert result.exit_code != 0

    def test_generate_invalid_provider(self):
        """Should fail with invalid provider name."""
        with tempfile.TemporaryDirectory() as tmpdir:
            result = runner.invoke(
                main_app, ["eval", "generate", tmpdir, "--provider", "invalid"]
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
                ["eval", "generate", str(tmpdir_path), "--provider", "letta"],
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
                ["eval", "generate", tmpdir, "--provider", "letta"],
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

            with patch("cli.commands.eval.providers.get_provider") as mock_get_provider:
                # Mock provider to fail early (we just want to check output)
                mock_provider = MagicMock()
                mock_provider.upload_documents.side_effect = Exception("Test error")
                mock_get_provider.return_value = mock_provider

                result = runner.invoke(
                    main_app,
                    ["eval", "generate", str(tmpdir_path), "--provider", "albert"],
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
