"""Tools, parsing, and monitoring types for Albert API.

Models for OCR, document parsing, file uploads, usage tracking, and health monitoring.
"""

from typing import Any, Literal

from albert_client._models import BaseModel


# Usage tracking types


class UsageRecord(BaseModel):
    """Usage statistics for a specific date."""

    date: str  # ISO date format (YYYY-MM-DD)
    prompt_tokens: int
    completion_tokens: int
    total_tokens: int
    cost: float  # USD
    carbon_footprint_gco2eq: float | None = None
    requests: int


class UsageList(BaseModel):
    """Response from listing usage statistics."""

    object: Literal["list"] = "list"
    data: list[UsageRecord]


# OCR types


class BoundingBox(BaseModel):
    """Bounding box coordinates for detected text."""

    x: float
    y: float
    width: float
    height: float


class OCRText(BaseModel):
    """Detected text with optional bounding box."""

    text: str
    bbox: BoundingBox | None = None
    confidence: float | None = None


class OCRPageObject(BaseModel):
    """OCR results for a single page."""

    page: int
    text: str | None = None
    texts: list[OCRText] | None = None
    images: list[str] | None = None  # Base64 encoded images


class OCRUsage(BaseModel):
    """OCR-specific usage information."""

    pages: int
    images: int | None = None


class OCRResponse(BaseModel):
    """Response from OCR operation."""

    pages: list[OCRPageObject]
    document_annotation: str | None = None
    id: str | None = None
    model: str | None = None
    # Can be Usage (from search.py) or OCRUsage - using Any to avoid circular imports
    usage: Any = None
    usage_info: OCRUsage | None = None


# Parsing types

ParsedDocumentOutputFormat = Literal["markdown", "json", "html"]
"""Output format for parsed documents."""


class ParsedDocumentPage(BaseModel):
    """A page from a parsed document."""

    page: int
    content: str
    metadata: dict[str, Any] | None = None


class ParsedDocument(BaseModel):
    """Response from document parsing."""

    object: Literal["list"] = "list"
    data: list[ParsedDocumentPage]
    # Usage information (from search.py) - using Any to avoid circular imports
    usage: Any = None


# File upload types


class FileUploadResponse(BaseModel):
    """Response from file upload."""

    id: str
    filename: str
    bytes: int
    created_at: int  # Unix timestamp
    purpose: str | None = None


# Health & Monitoring types


class HealthStatus(BaseModel):
    """API health status."""

    status: str  # e.g., "ok", "degraded", "down"
    version: str | None = None
    timestamp: int | None = None


class MetricsData(BaseModel):
    """API metrics data."""

    requests_total: int | None = None
    requests_per_second: float | None = None
    average_latency_ms: float | None = None
    error_rate: float | None = None
    uptime_seconds: int | None = None
