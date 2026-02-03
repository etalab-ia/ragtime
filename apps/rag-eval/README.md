# RAG Eval CLI

CLI tool for searching and managing RAG evaluation datasets.

## Installation

```bash
# From the workspace root
uv pip install -e apps/rag-eval
```

## Configuration

Copy `.env.example` to `.env` and configure:

```bash
cp .env.example .env
# Edit .env with your HuggingFace token
```

Get your HuggingFace token at: https://huggingface.co/settings/tokens

## Usage

### List known dataset sources

```bash
rag-eval sources
```

### Search HuggingFace datasets

```bash
# General search
rag-eval search hf "french QA datasets"

# Search within AgentPublic organization
rag-eval search hf "legislation" --author AgentPublic

# Convenience command for AgentPublic datasets
rag-eval search agent-public
rag-eval search agent-public "travail"
```

## Integration with Letta Code

This CLI is designed to be used by Letta Code agents to discover evaluation datasets. The typical workflow:

1. User asks Letta Code to find relevant evaluation datasets
2. Letta Code uses `rag-eval search` commands to discover datasets
3. Letta Code uses web search for additional dataset discovery
4. Results are formatted for the Letta Evals framework

## Future Features

- `rag-eval fetch <dataset>` - Download and convert datasets to Letta Evals format
- `rag-eval validate <dataset.jsonl>` - Validate dataset format
- Synthetic dataset generation from source documents
