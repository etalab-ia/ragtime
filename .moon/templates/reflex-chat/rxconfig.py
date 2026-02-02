from pathlib import Path

from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv(Path(__file__).parent / ".env")

import reflex as rx  # noqa: E402

config = rx.Config(
    app_name="{{ project_name | replace(from='-', to='_') }}",
    plugins=[
        rx.plugins.SitemapPlugin(),
        rx.plugins.TailwindV4Plugin(),
    ],
)
