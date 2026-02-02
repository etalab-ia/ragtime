# PDF Context

PDF text extraction and context formatting for LLM applications.

## Installation

```bash
uv add pdf-context
```

## Usage

```python
from pdf_context import extract_text_from_pdf, format_as_context, process_pdf_file

# Extract raw text
text = extract_text_from_pdf("document.pdf")

# Format for context injection
context = format_as_context(text, "document.pdf")

# Or use the convenience function
context = process_pdf_file("document.pdf")
```
