"""Tests for the document preprocessor."""

import tempfile
from pathlib import Path
from unittest.mock import patch

import pytest
from cli.commands.providers.document_preprocessor import DocumentPreprocessor


class TestDocumentPreprocessor:
    """Tests for DocumentPreprocessor."""

    def test_preprocessor_initialization(self):
        """Should initialize with optional temp directory."""
        preprocessor = DocumentPreprocessor()
        assert preprocessor.processed_files == []

        preprocessor_with_dir = DocumentPreprocessor(temp_dir="/tmp")
        assert preprocessor_with_dir.temp_dir == "/tmp"

    def test_process_non_pdf_documents(self):
        """Should keep non-PDF documents unchanged."""
        with tempfile.TemporaryDirectory() as tmpdir:
            tmpdir_path = Path(tmpdir)

            # Create test files
            txt_file = tmpdir_path / "test.txt"
            txt_file.write_text("Test content")

            md_file = tmpdir_path / "test.md"
            md_file.write_text("# Markdown content")

            preprocessor = DocumentPreprocessor()
            processed = preprocessor.process_documents([str(txt_file), str(md_file)])

            # Should return original paths for non-PDF files
            assert len(processed) == 2
            assert str(txt_file) in processed
            assert str(md_file) in processed
            # Should not create temporary files for non-PDFs
            assert len(preprocessor.processed_files) == 0

    @patch("cli.commands.providers.document_preprocessor.extract_text_from_pdf")
    def test_process_pdf_documents(self, mock_extract):
        """Should extract PDF to markdown text file."""
        mock_extract.return_value = "Extracted PDF content\n\nMore content"

        with tempfile.TemporaryDirectory() as tmpdir:
            tmpdir_path = Path(tmpdir)

            # Create test PDF file
            pdf_file = tmpdir_path / "test.pdf"
            pdf_file.write_bytes(b"%PDF-1.0\n...")  # Minimal PDF header

            preprocessor = DocumentPreprocessor()
            processed = preprocessor.process_documents([str(pdf_file)])

            # Should return a different path (temporary markdown file)
            assert len(processed) == 1
            assert processed[0] != str(pdf_file)
            assert processed[0].endswith(".md")

            # Temporary file should exist
            temp_path = Path(processed[0])
            assert temp_path.exists()

            # File should contain extracted content with header
            content = temp_path.read_text(encoding="utf-8")
            assert "# test" in content
            assert "Extracted PDF content" in content

            # Should track the temporary file
            assert len(preprocessor.processed_files) == 1

    @patch("cli.commands.providers.document_preprocessor.extract_text_from_pdf")
    def test_mixed_document_types(self, mock_extract):
        """Should handle mix of PDF and non-PDF documents."""
        mock_extract.return_value = "Extracted content"

        with tempfile.TemporaryDirectory() as tmpdir:
            tmpdir_path = Path(tmpdir)

            # Create mixed files
            txt_file = tmpdir_path / "test.txt"
            txt_file.write_text("Text content")

            pdf_file = tmpdir_path / "test.pdf"
            pdf_file.write_bytes(b"%PDF-1.0\n...")

            md_file = tmpdir_path / "test.md"
            md_file.write_text("# Markdown")

            preprocessor = DocumentPreprocessor()
            processed = preprocessor.process_documents(
                [str(txt_file), str(pdf_file), str(md_file)]
            )

            # Should have 3 paths
            assert len(processed) == 3

            # Should have created 1 temporary file (for PDF)
            assert len(preprocessor.processed_files) == 1

            # Verify content
            temp_path = Path(processed[1])
            content = temp_path.read_text(encoding="utf-8")
            assert "Extracted content" in content

    def test_cleanup_removes_temporary_files(self):
        """Should remove temporary files on cleanup."""
        with tempfile.TemporaryDirectory() as tmpdir:
            tmpdir_path = Path(tmpdir)

            # Create test files
            txt_file = tmpdir_path / "test.txt"
            txt_file.write_text("Test content")

            preprocessor = DocumentPreprocessor()

            # Create a fake temporary file to track
            with tempfile.NamedTemporaryFile(
                mode="w", suffix=".md", delete=False
            ) as tmp:
                tmp.write("Temporary content")
                tmp_path = Path(tmp.name)

            # Manually add to tracked files (simulating preprocessing)
            preprocessor.processed_files.append(tmp_path)
            assert tmp_path.exists()

            # Cleanup should remove it
            preprocessor.cleanup()
            assert not tmp_path.exists()

    @patch("cli.commands.providers.document_preprocessor.extract_text_from_pdf")
    def test_cleanup_handles_missing_files(self, mock_extract):
        """Should handle missing files gracefully during cleanup."""
        preprocessor = DocumentPreprocessor()

        # Add a non-existent file path
        preprocessor.processed_files.append(Path("/nonexistent/file.md"))

        # Should not raise an error
        preprocessor.cleanup()

    @patch("cli.commands.providers.document_preprocessor.extract_text_from_pdf")
    def test_extraction_error_handling(self, mock_extract):
        """Should raise error when PDF extraction fails."""
        mock_extract.side_effect = RuntimeError("Failed to extract PDF")

        with tempfile.TemporaryDirectory() as tmpdir:
            tmpdir_path = Path(tmpdir)
            pdf_file = tmpdir_path / "test.pdf"
            pdf_file.write_bytes(b"%PDF-1.0\n...")

            preprocessor = DocumentPreprocessor()

            with pytest.raises(RuntimeError, match="Failed to extract text from PDF"):
                preprocessor.process_documents([str(pdf_file)])

    def test_nonexistent_file_error(self):
        """Should raise error for non-existent PDF files."""
        preprocessor = DocumentPreprocessor()

        with pytest.raises(FileNotFoundError, match="PDF file not found"):
            preprocessor.process_documents(["/nonexistent/file.pdf"])

    @patch("cli.commands.providers.document_preprocessor.extract_text_from_pdf")
    def test_temp_dir_parameter(self, mock_extract):
        """Should use specified temp directory for extracted files."""
        mock_extract.return_value = "Extracted content"

        with tempfile.TemporaryDirectory() as tmpdir:
            tmpdir_path = Path(tmpdir)
            custom_temp_dir = tmpdir_path / "custom_temp"
            custom_temp_dir.mkdir()

            # Create test PDF
            pdf_file = tmpdir_path / "test.pdf"
            pdf_file.write_bytes(b"%PDF-1.0\n...")

            preprocessor = DocumentPreprocessor(temp_dir=str(custom_temp_dir))
            processed = preprocessor.process_documents([str(pdf_file)])

            # Temporary file should be in custom directory
            temp_path = Path(processed[0])
            assert str(custom_temp_dir) in str(temp_path)
