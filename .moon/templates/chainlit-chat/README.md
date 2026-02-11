# Chainlit Chat

This is a simple Chainlit-based chat application designed to benchmark the Albert API using the OpenAI-compatible Functions Streaming pattern via the albert-client SDK.

## Setup

1.  **Environment Variables**:
    Copy `.env.example` to `.env` and fill in your API details.
    ```bash
    cp .env.example .env
    ```
    For Albert API:
    ```
    OPENAI_API_KEY=<your-albert-api-key>
    OPENAI_BASE_URL=https://albert.sites.beta.gouv.fr/v1
    OPENAI_MODEL=meta-llama/Meta-Llama-3-8B-Instruct # or appropriate model ID
    ```

> [!TIP]
> RAG parameters like model names, temperature, and retrieval settings are now managed in `ragfacile.toml` via the configuration system. Use `rag-facile config` to customize them.

2.  **Dependencies**:
    This project is managed as part of the workspace. Ensure you have `uv` installed.
    ```bash
    uv sync
    ```

## Running the App

You can run the application using the `just` command runner.

If you are at the **root of the monorepo**:
```bash
just chainlit-chat
```

If you are in **this directory** (or using the generated template):
```bash
just sync  # Setup dependencies (Python 3.13)
just run   # Run the application
```
