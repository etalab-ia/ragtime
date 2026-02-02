# Reflex Chat App

A user-friendly, highly customizable Python web app designed to demonstrate LLMs in a ChatGPT format.

<div align="center">
<img src="./docs/demo.gif" alt="icon"/>
</div>

# Getting Started

### 1. Environment Configuration

This app is configured to use the [Albert API](https://albert.sites.beta.gouv.fr/). You must provide your API key and the base URL. Create a `.env` file in this directory based on `.env.example`:

```bash
cp .env.example .env
```

Edit the `.env` file to add your `OPENAI_API_KEY` and `OPENAI_BASE_URL`.

### 2. Run the application

If you are at the **root of the monorepo**:
```bash
just reflex-chat
```

If you are in **this directory** (or using the generated template):
```bash
just sync  # Setup dependencies (Python 3.13)
just run   # Run the application
```

Or directly using `uv`:
```bash
uv run reflex run
```

# Features

- 100% Python-based, including the UI, using Reflex
- Create and delete chat sessions
- The application is fully customizable and no knowledge of web dev is required to use it.
  - See https://reflex.dev/docs/styling/overview for more details
- Easily swap out any LLM
- Responsive design for various devices

# Contributing

We welcome contributions to improve and extend the LLM Web UI.
If you'd like to contribute, please do the following:

- Fork the repository and make your changes.
- Once you're ready, submit a pull request for review.

# License

The following repo is licensed under the MIT License.
