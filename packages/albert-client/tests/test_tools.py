"""Tests for OCR, usage tracking, and monitoring functionality."""

import pytest
import respx
from httpx import Response

from albert import (
    AlbertClient,
    OCRResponse,
    UsageList,
)


@pytest.fixture
def client(api_key, base_url):
    """Create test client."""
    return AlbertClient(api_key=api_key, base_url=base_url)


@pytest.fixture
def temp_file(tmp_path):
    """Create a temporary test file."""
    f = tmp_path / "test.txt"
    f.write_text("Test document content.")
    return f


class TestUsageTracking:
    """Test get_usage method."""

    @pytest.fixture
    def mock_usage_list(self):
        """Mock usage data."""
        return {
            "object": "list",
            "data": [
                {
                    "object": "me.usage",
                    "created": 1705276800,  # 2024-01-15
                    "model": "gpt-4",
                    "usage": {
                        "total_tokens": 1500,
                        "cost": 0.05,
                    },
                },
                {
                    "object": "me.usage",
                    "created": 1705363200,  # 2024-01-16
                    "model": "gpt-4",
                    "usage": {
                        "total_tokens": 3000,
                        "cost": 0.10,
                    },
                },
            ],
        }

    @respx.mock
    def test_get_usage_all(self, client, base_url, mock_usage_list):
        """Test getting all usage statistics."""
        respx.get(f"{base_url.rstrip('/')}/me/usage").mock(
            return_value=Response(200, json=mock_usage_list)
        )

        result = client.get_usage()

        assert isinstance(result, UsageList)
        assert result.object == "list"
        assert len(result.data) == 2
        assert result.data[0].created == 1705276800
        assert result.data[0].usage.total_tokens == 1500
        assert result.data[0].usage.cost == 0.05

    @respx.mock
    def test_get_usage_with_time_range(self, client, base_url, mock_usage_list):
        """Test getting usage with time filters."""
        mock_route = respx.get(f"{base_url.rstrip('/')}/me/usage").mock(
            return_value=Response(200, json=mock_usage_list)
        )

        result = client.get_usage(start_time=1705276800, end_time=1705363200)

        # Verify query params
        assert (
            mock_route.calls.last.request.url.params.get("start_time") == "1705276800"
        )
        assert mock_route.calls.last.request.url.params.get("end_time") == "1705363200"

        assert isinstance(result, UsageList)

    @respx.mock
    def test_get_usage_empty(self, client, base_url):
        """Test getting usage when no data exists."""
        respx.get(f"{base_url.rstrip('/')}/me/usage").mock(
            return_value=Response(200, json={"object": "list", "data": []})
        )

        result = client.get_usage()

        assert isinstance(result, UsageList)
        assert len(result.data) == 0


class TestOCR:
    """Test OCR methods."""

    @pytest.fixture
    def mock_ocr_response(self):
        """Mock OCR response data."""
        return {
            "pages": [
                {
                    "index": 0,
                    "markdown": "This is the extracted text from page 1.",
                    "images": [],
                }
            ],
            "id": "ocr_123",
            "model": "doctr",
        }

    @respx.mock
    def test_ocr_with_url_string(self, client, base_url, mock_ocr_response):
        """Test OCR with a URL string."""
        respx.post(f"{base_url.rstrip('/')}/ocr").mock(
            return_value=Response(200, json=mock_ocr_response)
        )

        result = client.ocr(document="https://example.com/doc.pdf")

        assert isinstance(result, OCRResponse)
        assert len(result.pages) == 1
        assert result.pages[0].markdown == "This is the extracted text from page 1."
        assert result.model == "doctr"

    @respx.mock
    def test_ocr_with_document_dict(self, client, base_url, mock_ocr_response):
        """Test OCR with a document dictionary."""
        respx.post(f"{base_url.rstrip('/')}/ocr").mock(
            return_value=Response(200, json=mock_ocr_response)
        )

        result = client.ocr(document={"document_url": "https://example.com/doc.pdf"})

        assert isinstance(result, OCRResponse)
        assert len(result.pages) == 1

    @respx.mock
    def test_ocr_with_pages(self, client, base_url, mock_ocr_response):
        """Test OCR with specific pages."""
        mock_route = respx.post(f"{base_url.rstrip('/')}/ocr").mock(
            return_value=Response(200, json=mock_ocr_response)
        )

        result = client.ocr(
            document="https://example.com/doc.pdf", pages=[0, 1, 2], model="doctr"
        )

        # Verify request body
        request_body = mock_route.calls.last.request.content.decode()
        assert "[0,1,2]" in request_body or "[0, 1, 2]" in request_body
        assert "doctr" in request_body

        assert isinstance(result, OCRResponse)


class TestHealthMonitoring:
    """Test health and monitoring methods."""

    @respx.mock
    def test_health_check(self, client, base_url):
        """Test API health check."""
        mock_health = {
            "status": "ok",
            "version": "1.0.0",
            "timestamp": 1234567890,
        }

        respx.get(f"{base_url.rstrip('/')}/health").mock(
            return_value=Response(200, json=mock_health)
        )

        result = client.health_check()

        assert isinstance(result, dict)
        assert result["status"] == "ok"
        assert result["version"] == "1.0.0"

    @respx.mock
    def test_get_metrics(self, client, base_url):
        """Test getting API metrics."""
        mock_metrics = {
            "requests_total": 10000,
            "requests_per_second": 50.5,
            "average_latency_ms": 120.3,
            "error_rate": 0.01,
            "uptime_seconds": 86400,
        }

        respx.get(f"{base_url.rstrip('/')}/metrics").mock(
            return_value=Response(200, json=mock_metrics)
        )

        result = client.get_metrics()

        assert isinstance(result, dict)
        assert result["requests_total"] == 10000
        assert result["requests_per_second"] == 50.5
