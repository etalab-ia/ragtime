# pdf-context

PDF text extraction and context formatting for LLM applications.

## Overview

This package provides utilities for extracting text from PDF files and formatting it for injection into LLM prompts. It uses a "context-injection" approach where the entire PDF content is added to the conversation context, suitable for smaller documents that fit within the model's context window.

## Installation

The package is part of the rag-facile monorepo. It's automatically available when working within the workspace.

```bash
uv sync
```

## Usage

### Basic Usage

```python
from pdf_context import extract_text_from_pdf, format_as_context, process_pdf_file

# Extract raw text from a PDF
text = extract_text_from_pdf("path/to/document.pdf")

# Format the text for LLM context injection
context = format_as_context(text, "document.pdf")

# Or use the convenience function that does both
context = process_pdf_file("path/to/document.pdf")
```

### Processing Multiple Files

```python
from pdf_context import process_multiple_files

# Process multiple PDFs at once
context = process_multiple_files([
    "path/to/doc1.pdf",
    "path/to/doc2.pdf",
])
```

### Working with Bytes

```python
from pdf_context import extract_text_from_bytes

# Useful when you have PDF content in memory (e.g., from an upload)
pdf_bytes = uploaded_file.read()
text = extract_text_from_bytes(pdf_bytes)
```

## Integration Examples

### Chainlit

```python
import chainlit as cl
from pdf_context import process_pdf_file

@cl.on_message
async def main(message: cl.Message):
    file_content = ""

    if message.elements:
        for element in message.elements:
            if element.name.endswith(".pdf") and element.path:
                try:
                    file_content += process_pdf_file(element.path, element.name)
                except Exception as e:
                    file_content += f"\n\nError reading PDF '{element.name}': {e}\n"

    user_message = message.content + file_content
    # ... rest of your chat logic
```

### Reflex

```python
import reflex as rx
from pdf_context import extract_text_from_bytes, format_as_context

class State(rx.State):
    async def handle_upload(self, files: list[rx.UploadFile]):
        for file in files:
            if file.filename.endswith(".pdf"):
                content = await file.read()
                text = extract_text_from_bytes(content)
                context = format_as_context(text, file.filename)
                # ... use context in your chat
```

## Limitations

- **Context window**: The entire PDF content is injected into the prompt. Large PDFs may exceed the model's context window.
- **Text only**: Only extracts plain text. Images, tables structure, and formatting are not preserved.
- **No persistence**: Documents are not stored; they must be re-uploaded each session.

For large document collections or advanced retrieval needs, consider implementing a full RAG pipeline with embeddings and vector storage.

## API Reference

### `extract_text_from_pdf(path: str | Path) -> str`

Extract all text content from a PDF file.

### `extract_text_from_bytes(pdf_bytes: bytes) -> str`

Extract all text content from PDF bytes (useful for uploads).

### `format_as_context(text: str, filename: str) -> str`

Format extracted text with delimiters for context injection.

### `process_pdf_file(path: str | Path, filename: str | None = None) -> str`

Convenience function that extracts text and formats it in one call.

### `process_multiple_files(paths: list[str | Path]) -> str`

Process multiple PDF files and combine their formatted context.
