"""Tests for async OCR, usage tracking, and monitoring functionality."""

import pytest
import respx
from httpx import Response

from albert import (
    AsyncAlbertClient,
    OCRResponse,
    UsageList,
)


@pytest.fixture
def client(api_key, base_url):
    """Create test async client."""
    return AsyncAlbertClient(api_key=api_key, base_url=base_url)


@pytest.fixture
def temp_file(tmp_path):
    """Create a temporary test file."""
    f = tmp_path / "test.txt"
    f.write_text("Test document content.")
    return f


class TestAsyncUsageTracking:
    """Test async usage tracking."""

    @respx.mock
    async def test_get_usage(self, client, base_url):
        """Test async get usage."""
        mock_usage = {
            "object": "list",
            "data": [
                {
                    "created": 1705276800,
                    "model": "gpt-4",
                    "usage": {
                        "total_tokens": 1500,
                        "cost": 0.05,
                    },
                }
            ],
        }

        respx.get(f"{base_url.rstrip('/')}/me/usage").mock(
            return_value=Response(200, json=mock_usage)
        )

        result = await client.get_usage()

        assert isinstance(result, UsageList)
        assert len(result.data) == 1
        assert result.data[0].usage.total_tokens == 1500

    @respx.mock
    async def test_get_usage_with_time_range(self, client, base_url):
        """Test async get usage with date range."""
        mock_usage = {"object": "list", "data": []}

        mock_route = respx.get(f"{base_url.rstrip('/')}/me/usage").mock(
            return_value=Response(200, json=mock_usage)
        )

        result = await client.get_usage(start_time=1705276800, end_time=1705363200)

        assert (
            mock_route.calls.last.request.url.params.get("start_time") == "1705276800"
        )
        assert isinstance(result, UsageList)

    @respx.mock
    async def test_usage_context_manager(self, api_key, base_url):
        """Test async usage with context manager."""
        mock_usage = {"object": "list", "data": []}

        respx.get(f"{base_url.rstrip('/')}/me/usage").mock(
            return_value=Response(200, json=mock_usage)
        )

        async with AsyncAlbertClient(api_key=api_key, base_url=base_url) as client:
            result = await client.get_usage()
            assert isinstance(result, UsageList)


class TestAsyncOCR:
    """Test async OCR methods."""

    @respx.mock
    async def test_ocr(self, client, base_url):
        """Test async OCR."""
        mock_ocr = {
            "pages": [{"index": 0, "markdown": "Extracted text"}],
            "id": "ocr_123",
            "model": "doctr",
        }

        respx.post(f"{base_url.rstrip('/')}/ocr").mock(
            return_value=Response(200, json=mock_ocr)
        )

        result = await client.ocr(document="https://example.com/doc.pdf")

        assert isinstance(result, OCRResponse)
        assert len(result.pages) == 1

    @respx.mock
    async def test_ocr_with_options(self, client, base_url):
        """Test async OCR with options."""
        mock_ocr = {"pages": [{"index": 0, "markdown": "Page 1"}], "model": "doctr"}

        respx.post(f"{base_url.rstrip('/')}/ocr").mock(
            return_value=Response(200, json=mock_ocr)
        )

        result = await client.ocr(
            document="https://example.com/doc.pdf",
            model="doctr",
            pages=[0, 1],
            include_image_base64=True,
        )

        assert isinstance(result, OCRResponse)


class TestAsyncHealthMonitoring:
    """Test async health and monitoring."""

    @respx.mock
    async def test_health_check(self, client, base_url):
        """Test async health check."""
        mock_health = {"status": "ok", "version": "1.0.0"}

        respx.get(f"{base_url.rstrip('/')}/health").mock(
            return_value=Response(200, json=mock_health)
        )

        result = await client.health_check()

        assert isinstance(result, dict)
        assert result["status"] == "ok"

    @respx.mock
    async def test_get_metrics(self, client, base_url):
        """Test async get metrics."""
        mock_metrics = {
            "requests_total": 5000,
            "requests_per_second": 25.5,
            "average_latency_ms": 100.0,
        }

        respx.get(f"{base_url.rstrip('/')}/metrics").mock(
            return_value=Response(200, json=mock_metrics)
        )

        result = await client.get_metrics()

        assert isinstance(result, dict)
        assert result["requests_total"] == 5000

    @respx.mock
    async def test_monitoring_context_manager(self, api_key, base_url):
        """Test async monitoring with context manager."""
        mock_health = {"status": "ok"}
        mock_metrics = {"requests_total": 1000}

        respx.get(f"{base_url.rstrip('/')}/health").mock(
            return_value=Response(200, json=mock_health)
        )
        respx.get(f"{base_url.rstrip('/')}/metrics").mock(
            return_value=Response(200, json=mock_metrics)
        )

        async with AsyncAlbertClient(api_key=api_key, base_url=base_url) as client:
            health = await client.health_check()
            metrics = await client.get_metrics()

            assert isinstance(health, dict)
            assert isinstance(metrics, dict)
