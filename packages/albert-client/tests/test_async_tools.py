"""Tests for async tools, parsing, and monitoring functionality."""

import tempfile
from pathlib import Path

import pytest
import respx
from httpx import Response

from albert_client import (
    AsyncAlbertClient,
    FileUploadResponse,
    HealthStatus,
    MetricsData,
    OCRResponse,
    ParsedDocument,
    UsageList,
)


@pytest.fixture
def client(api_key, base_url):
    """Create test async client."""
    return AsyncAlbertClient(api_key=api_key, base_url=base_url)


@pytest.fixture
def temp_file():
    """Create a temporary test file."""
    with tempfile.NamedTemporaryFile(mode="w", suffix=".txt", delete=False) as f:
        f.write("Test document content for parsing.")
        temp_path = Path(f.name)

    yield temp_path

    # Cleanup
    temp_path.unlink()


class TestAsyncUsageTracking:
    """Test async usage tracking."""

    @respx.mock
    async def test_get_usage(self, client, base_url):
        """Test async get usage."""
        mock_usage = {
            "object": "list",
            "data": [
                {
                    "date": "2024-01-15",
                    "prompt_tokens": 1000,
                    "completion_tokens": 500,
                    "total_tokens": 1500,
                    "cost": 0.05,
                    "carbon_footprint_gco2eq": 1.2,
                    "requests": 10,
                }
            ],
        }

        respx.get(f"{base_url.rstrip('/')}/me/usage").mock(
            return_value=Response(200, json=mock_usage)
        )

        result = await client.get_usage()

        assert isinstance(result, UsageList)
        assert len(result.data) == 1
        assert result.data[0].total_tokens == 1500

    @respx.mock
    async def test_get_usage_with_dates(self, client, base_url):
        """Test async get usage with date range."""
        mock_usage = {"object": "list", "data": []}

        mock_route = respx.get(f"{base_url.rstrip('/')}/me/usage").mock(
            return_value=Response(200, json=mock_usage)
        )

        result = await client.get_usage(start_date="2024-01-01", end_date="2024-01-31")

        assert (
            mock_route.calls.last.request.url.params.get("start_date") == "2024-01-01"
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
            "pages": [{"page": 0, "text": "Extracted text"}],
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
        mock_ocr = {"pages": [{"page": 0, "text": "Page 1"}], "model": "doctr"}

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

    @respx.mock
    async def test_ocr_beta(self, client, base_url, temp_file):
        """Test async OCR beta."""
        mock_response = {
            "object": "list",
            "data": [{"page": 0, "content": "OCR beta result"}],
        }

        respx.post(f"{base_url.rstrip('/')}/ocr-beta").mock(
            return_value=Response(200, json=mock_response)
        )

        result = await client.ocr_beta(file_path=temp_file, model="gpt-4o-mini")

        assert isinstance(result, ParsedDocument)
        assert result.data[0].content == "OCR beta result"


class TestAsyncParsing:
    """Test async parsing methods."""

    @respx.mock
    async def test_parse(self, client, base_url, temp_file):
        """Test async parse."""
        mock_parsed = {
            "object": "list",
            "data": [{"page": 0, "content": "# Parsed content"}],
        }

        respx.post(f"{base_url.rstrip('/')}/parse-beta").mock(
            return_value=Response(200, json=mock_parsed)
        )

        result = await client.parse(file_path=temp_file)

        assert isinstance(result, ParsedDocument)
        assert len(result.data) == 1

    @respx.mock
    async def test_parse_with_options(self, client, base_url, temp_file):
        """Test async parse with options."""
        mock_parsed = {
            "object": "list",
            "data": [{"page": 0, "content": '{"key": "value"}'}],
        }

        respx.post(f"{base_url.rstrip('/')}/parse-beta").mock(
            return_value=Response(200, json=mock_parsed)
        )

        result = await client.parse(
            file_path=temp_file,
            output_format="json",
            force_ocr=True,
            page_range="0-10",
        )

        assert isinstance(result, ParsedDocument)

    @respx.mock
    async def test_parse_context_manager(self, api_key, base_url, temp_file):
        """Test async parse with context manager."""
        mock_parsed = {"object": "list", "data": [{"page": 0, "content": "Content"}]}

        respx.post(f"{base_url.rstrip('/')}/parse-beta").mock(
            return_value=Response(200, json=mock_parsed)
        )

        async with AsyncAlbertClient(api_key=api_key, base_url=base_url) as client:
            result = await client.parse(file_path=temp_file)
            assert isinstance(result, ParsedDocument)


class TestAsyncFileUpload:
    """Test async file upload."""

    @respx.mock
    async def test_upload_file(self, client, base_url, temp_file):
        """Test async file upload."""
        mock_response = {
            "id": "file_123",
            "filename": temp_file.name,
            "bytes": 1024,
            "created_at": 1234567890,
        }

        respx.post(f"{base_url.rstrip('/')}/files").mock(
            return_value=Response(200, json=mock_response)
        )

        result = await client.upload_file(file_path=temp_file)

        assert isinstance(result, FileUploadResponse)
        assert result.id == "file_123"

    @respx.mock
    async def test_upload_file_with_purpose(self, client, base_url, temp_file):
        """Test async file upload with purpose."""
        mock_response = {
            "id": "file_456",
            "filename": temp_file.name,
            "bytes": 2048,
            "created_at": 1234567890,
            "purpose": "training",
        }

        respx.post(f"{base_url.rstrip('/')}/files").mock(
            return_value=Response(200, json=mock_response)
        )

        result = await client.upload_file(file_path=temp_file, purpose="training")

        assert result.purpose == "training"


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

        assert isinstance(result, HealthStatus)
        assert result.status == "ok"

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

        assert isinstance(result, MetricsData)
        assert result.requests_total == 5000

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

            assert isinstance(health, HealthStatus)
            assert isinstance(metrics, MetricsData)
