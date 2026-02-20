"""Shared Rich console instance for the chat module.

Both agent.py and tools.py import from here so spinner management and
interactive prompts (e.g. update_config confirmation) share one Console.
"""

from rich.console import Console

console = Console()
