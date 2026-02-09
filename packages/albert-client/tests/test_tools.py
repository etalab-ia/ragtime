"""Tests for tools, parsing, and monitoring functionality."""

import tempfile
from pathlib import Path

import pytest
import respx
from httpx import Response

from albert_client import (
    AlbertClient,
    FileUploadResponse,
    HealthStatus,
    MetricsData,
    OCRResponse,
    ParsedDocument,
    UsageList,
)


@pytest.fixture
def client(api_key, base_url):
    """Create test client."""
    return AlbertClient(api_key=api_key, base_url=base_url)


@pytest.fixture
def temp_file():
    """Create a temporary test file."""
    with tempfile.NamedTemporaryFile(mode="w", suffix=".txt", delete=False) as f:
        f.write("Test document content for parsing.")
        temp_path = Path(f.name)

    yield temp_path

    # Cleanup
    temp_path.unlink()


class TestUsageTracking:
    """Test get_usage method."""

    @pytest.fixture
    def mock_usage_list(self):
        """Mock usage data."""
        return {
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
                },
                {
                    "date": "2024-01-16",
                    "prompt_tokens": 2000,
                    "completion_tokens": 1000,
                    "total_tokens": 3000,
                    "cost": 0.10,
                    "carbon_footprint_gco2eq": 2.4,
                    "requests": 20,
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
        assert result.data[0].date == "2024-01-15"
        assert result.data[0].total_tokens == 1500
        assert result.data[0].cost == 0.05

    @respx.mock
    def test_get_usage_with_date_range(self, client, base_url, mock_usage_list):
        """Test getting usage with date filters."""
        mock_route = respx.get(f"{base_url.rstrip('/')}/me/usage").mock(
            return_value=Response(200, json=mock_usage_list)
        )

        result = client.get_usage(start_date="2024-01-01", end_date="2024-01-31")

        # Verify query params
        assert (
            mock_route.calls.last.request.url.params.get("start_date") == "2024-01-01"
        )
        assert mock_route.calls.last.request.url.params.get("end_date") == "2024-01-31"

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
                    "page": 0,
                    "text": "This is the extracted text from page 1.",
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
        assert result.pages[0].text == "This is the extracted text from page 1."
        assert result.model == "doctr"

    @respx.mock
    def test_ocr_with_document_dict(self, client, base_url, mock_ocr_response):
        """Test OCR with a document dictionary."""
        respx.post(f"{base_url.rstrip('/')}/ocr").mock(
            return_value=Response(200, json=mock_ocr_response)
        )

        result = client.ocr(document={"url": "https://example.com/doc.pdf"})

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

    @respx.mock
    def test_ocr_beta(self, client, base_url, temp_file):
        """Test simple OCR beta method."""
        mock_response = {
            "object": "list",
            "data": [{"page": 0, "content": "Extracted text from OCR beta"}],
        }

        respx.post(f"{base_url.rstrip('/')}/ocr-beta").mock(
            return_value=Response(200, json=mock_response)
        )

        result = client.ocr_beta(file_path=temp_file, model="gpt-4o-mini", dpi=200)

        assert isinstance(result, ParsedDocument)
        assert len(result.data) == 1
        assert result.data[0].content == "Extracted text from OCR beta"


class TestParsing:
    """Test document parsing method."""

    @pytest.fixture
    def mock_parsed_document(self):
        """Mock parsed document data."""
        return {
            "object": "list",
            "data": [
                {"page": 0, "content": "# Page 1\n\nThis is the first page."},
                {"page": 1, "content": "# Page 2\n\nThis is the second page."},
            ],
        }

    @respx.mock
    def test_parse_default_markdown(
        self, client, base_url, temp_file, mock_parsed_document
    ):
        """Test parsing document to markdown."""
        respx.post(f"{base_url.rstrip('/')}/parse-beta").mock(
            return_value=Response(200, json=mock_parsed_document)
        )

        result = client.parse(file_path=temp_file)

        assert isinstance(result, ParsedDocument)
        assert len(result.data) == 2
        assert result.data[0].content.startswith("# Page 1")

    @respx.mock
    def test_parse_with_options(
        self, client, base_url, temp_file, mock_parsed_document
    ):
        """Test parsing with custom options."""
        mock_route = respx.post(f"{base_url.rstrip('/')}/parse-beta").mock(
            return_value=Response(200, json=mock_parsed_document)
        )

        result = client.parse(
            file_path=temp_file,
            output_format="json",
            force_ocr=True,
            page_range="0-5",
            paginate_output=True,
        )

        # Verify form data
        request = mock_route.calls.last.request
        assert b"json" in request.content
        assert b"True" in request.content or b"true" in request.content
        assert b"0-5" in request.content

        assert isinstance(result, ParsedDocument)


class TestFileUpload:
    """Test file upload method."""

    @respx.mock
    def test_upload_file(self, client, base_url, temp_file):
        """Test uploading a file."""
        mock_response = {
            "id": "file_abc123",
            "filename": temp_file.name,
            "bytes": 1024,
            "created_at": 1234567890,
            "purpose": "analysis",
        }

        respx.post(f"{base_url.rstrip('/')}/files").mock(
            return_value=Response(200, json=mock_response)
        )

        result = client.upload_file(file_path=temp_file, purpose="analysis")

        assert isinstance(result, FileUploadResponse)
        assert result.id == "file_abc123"
        assert result.bytes == 1024
        assert result.purpose == "analysis"

    @respx.mock
    def test_upload_file_without_purpose(self, client, base_url, temp_file):
        """Test uploading a file without purpose."""
        mock_response = {
            "id": "file_xyz789",
            "filename": temp_file.name,
            "bytes": 512,
            "created_at": 1234567890,
        }

        respx.post(f"{base_url.rstrip('/')}/files").mock(
            return_value=Response(200, json=mock_response)
        )

        result = client.upload_file(file_path=temp_file)

        assert isinstance(result, FileUploadResponse)
        assert result.id == "file_xyz789"


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

        assert isinstance(result, HealthStatus)
        assert result.status == "ok"
        assert result.version == "1.0.0"

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

        assert isinstance(result, MetricsData)
        assert result.requests_total == 10000
        assert result.requests_per_second == 50.5
        assert result.average_latency_ms == 120.3
        assert result.error_rate == 0.01
