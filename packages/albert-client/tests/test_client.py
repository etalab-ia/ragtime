"""Tests for AlbertClient."""

import pytest
import respx
from httpx import Response

from albert_client import AlbertClient


class TestClientInitialization:
    """Test client initialization."""

    def test_init_with_api_key(self, api_key, base_url):
        """Test initialization with explicit API key."""
        client = AlbertClient(api_key=api_key, base_url=base_url)
        assert client.api_key == api_key
        assert client.base_url == base_url

    def test_init_with_env_var(self, base_url, monkeypatch):
        """Test initialization with ALBERT_API_KEY env var."""
        api_key = "albert_from_env"
        monkeypatch.setenv("ALBERT_API_KEY", api_key)

        client = AlbertClient(base_url=base_url)
        assert client.api_key == api_key

    def test_init_with_openai_api_key_fallback(self, base_url, monkeypatch):
        """Test initialization with OPENAI_API_KEY env var (fallback)."""
        api_key = "openai_from_env"
        monkeypatch.setenv("OPENAI_API_KEY", api_key)

        client = AlbertClient(base_url=base_url)
        assert client.api_key == api_key

    def test_init_albert_api_key_takes_precedence(self, base_url, monkeypatch):
        """Test that ALBERT_API_KEY takes precedence over OPENAI_API_KEY."""
        albert_key = "albert_key"
        openai_key = "openai_key"
        monkeypatch.setenv("ALBERT_API_KEY", albert_key)
        monkeypatch.setenv("OPENAI_API_KEY", openai_key)

        client = AlbertClient(base_url=base_url)
        assert client.api_key == albert_key

    def test_init_without_api_key_raises_error(self, base_url):
        """Test that missing API key raises ValueError."""
        with pytest.raises(ValueError, match="Albert API key is required"):
            AlbertClient(base_url=base_url)

    def test_default_base_url(self, api_key):
        """Test default base URL is Albert production."""
        client = AlbertClient(api_key=api_key)
        assert "albert.api.etalab.gouv.fr/v1" in client.base_url


class TestOpenAICompatibleEndpoints:
    """Test OpenAI-compatible endpoint passthrough."""

    def test_chat_attribute_exists(self, api_key, base_url):
        """Test that chat attribute is available."""
        client = AlbertClient(api_key=api_key, base_url=base_url)
        assert hasattr(client, "chat")
        assert hasattr(client.chat, "completions")

    def test_embeddings_attribute_exists(self, api_key, base_url):
        """Test that embeddings attribute is available."""
        client = AlbertClient(api_key=api_key, base_url=base_url)
        assert hasattr(client, "embeddings")

    def test_audio_attribute_exists(self, api_key, base_url):
        """Test that audio attribute is available."""
        client = AlbertClient(api_key=api_key, base_url=base_url)
        assert hasattr(client, "audio")

    def test_models_attribute_exists(self, api_key, base_url):
        """Test that models attribute is available."""
        client = AlbertClient(api_key=api_key, base_url=base_url)
        assert hasattr(client, "models")

    @respx.mock
    def test_chat_completion_call(self, api_key, base_url):
        """Test that chat.completions.create actually works."""
        client = AlbertClient(api_key=api_key, base_url=base_url)

        # Mock the chat completion endpoint (strip trailing slash from base_url)
        respx.post(f"{base_url.rstrip('/')}/chat/completions").mock(
            return_value=Response(
                200,
                json={
                    "id": "chatcmpl-123",
                    "object": "chat.completion",
                    "created": 1234567890,
                    "model": "AgentPublic/llama3-instruct-8b",
                    "choices": [
                        {
                            "index": 0,
                            "message": {
                                "role": "assistant",
                                "content": "Hello! How can I help you?",
                            },
                            "finish_reason": "stop",
                        }
                    ],
                },
            )
        )

        # Make request
        response = client.chat.completions.create(
            model="AgentPublic/llama3-instruct-8b",
            messages=[{"role": "user", "content": "Hello"}],
        )

        # Verify response
        assert response.choices[0].message.content == "Hello! How can I help you?"


class TestClientProperties:
    """Test client properties."""

    def test_api_key_property(self, api_key, base_url):
        """Test api_key property."""
        client = AlbertClient(api_key=api_key, base_url=base_url)
        assert client.api_key == api_key

    def test_base_url_property(self, api_key, base_url):
        """Test base_url property."""
        client = AlbertClient(api_key=api_key, base_url=base_url)
        assert client.base_url == base_url
