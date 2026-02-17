"""Uninstall RAG Facile and its toolchain."""

import os
import platform
import shutil
import subprocess
from pathlib import Path

import typer
from rich.console import Console
from rich.table import Table


console = Console()

# Directories managed by the installer
PROTO_HOME = Path(os.environ.get("PROTO_HOME", Path.home() / ".proto"))
UV_TOOLS_DIR = Path.home() / ".local" / "share" / "uv" / "tools"
UV_BIN_DIR = Path.home() / ".local" / "bin"

# Shell profile candidates (Unix)
SHELL_PROFILES = [
    Path.home() / ".zshrc",
    Path.home() / ".bashrc",
    Path.home() / ".bash_profile",
    Path.home() / ".profile",
]

# Marker comment added by install.sh
INSTALLER_MARKER = "# Added by RAG Facile installer"


def _is_windows() -> bool:
    return platform.system() == "Windows"


def _tool_exists(name: str) -> bool:
    return shutil.which(name) is not None


def _run_quiet(cmd: list[str]) -> bool:
    """Run a command silently, return True on success."""
    try:
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=30)
        return result.returncode == 0
    except (subprocess.TimeoutExpired, FileNotFoundError):
        return False


def _collect_items_to_remove(
    *,
    include_tools: bool = False,
) -> list[tuple[str, str, bool]]:
    """Collect (label, detail, exists) tuples for everything that will be removed.

    Args:
        include_tools: If True, also include the toolchain (proto, moon, uv,
            just, direnv) and shell profile entries.
    """
    items: list[tuple[str, str, bool]] = []

    # rag-facile CLI (always removed)
    rf_bin = shutil.which("rag-facile")
    items.append(
        (
            "rag-facile CLI",
            str(rf_bin) if rf_bin else str(UV_BIN_DIR / "rag-facile"),
            rf_bin is not None,
        )
    )

    if not include_tools:
        return items

    # Proto-managed tools
    for tool in ("moon", "uv", "just"):
        exists = _tool_exists(tool)
        items.append((tool, "proto-managed tool", exists))

    # Proto itself
    items.append(("proto", str(PROTO_HOME), PROTO_HOME.exists()))

    # direnv (Unix only)
    if not _is_windows():
        items.append(("direnv", "shell environment manager", _tool_exists("direnv")))

    # Shell profile entries (Unix only)
    if not _is_windows():
        profiles_with_marker = [
            p for p in SHELL_PROFILES if _profile_has_installer_entries(p)
        ]
        if profiles_with_marker:
            names = ", ".join(p.name for p in profiles_with_marker)
            items.append(("Shell profile entries", names, True))

    return items


def _profile_has_installer_entries(profile: Path) -> bool:
    """Check if a shell profile has lines added by the RAG Facile installer."""
    if not profile.exists():
        return False
    try:
        content = profile.read_text()
        return INSTALLER_MARKER in content or "direnv hook" in content
    except OSError:
        return False


def _clean_shell_profile(profile: Path) -> bool:
    """Remove RAG Facile installer entries and direnv hook from a shell profile."""
    if not profile.exists():
        return False
    try:
        lines = profile.read_text().splitlines(keepends=True)
    except OSError:
        return False

    cleaned: list[str] = []
    skip_next = False
    changed = False

    for line in lines:
        stripped = line.strip()

        # Skip the marker comment and the line immediately after it (the export/eval line)
        if stripped == INSTALLER_MARKER:
            skip_next = True
            changed = True
            continue
        if skip_next:
            skip_next = False
            continue

        # Remove direnv hook lines
        if "direnv hook" in stripped:
            changed = True
            continue

        cleaned.append(line)

    if changed:
        # Remove trailing blank lines that were left behind
        content = "".join(cleaned).rstrip("\n") + "\n"
        profile.write_text(content)

    return changed


def _clean_windows_path() -> bool:
    """Remove RAG Facile-related entries from Windows User PATH via PowerShell.

    Uses PowerShell instead of the ``winreg`` module so the code type-checks
    cleanly on macOS/Linux (where ``winreg`` is unavailable).
    """
    if not _is_windows():
        return False

    proto_home_win = str(PROTO_HOME).replace("/", "\\")
    uv_bin_win = str(UV_BIN_DIR).replace("/", "\\")

    script = (
        "$key = [Microsoft.Win32.Registry]::CurrentUser.OpenSubKey('Environment', $true); "
        "$cur = $key.GetValue('Path', '', 'DoNotExpandEnvironmentNames'); "
        "if (-not $cur) { exit 1 }; "
        f"$rem = @('{proto_home_win}\\bin', '{proto_home_win}\\shims', '{uv_bin_win}'); "
        "$ent = $cur -split ';' | Where-Object { $_ -and $_ -notin $rem }; "
        "$new = $ent -join ';'; "
        "if ($new -ne $cur) { $key.SetValue('Path', $new, 'ExpandString'); Write-Output 'cleaned' }; "
        "$key.Close()"
    )
    try:
        result = subprocess.run(
            ["powershell", "-NoProfile", "-Command", script],
            capture_output=True,
            text=True,
            timeout=15,
        )
        return "cleaned" in result.stdout
    except (FileNotFoundError, subprocess.TimeoutExpired, OSError):
        return False


def run(
    all_tools: bool = typer.Option(
        False,
        "--all",
        help="Also remove the toolchain (proto, moon, uv, just, direnv)",
    ),
    yes: bool = typer.Option(False, "--yes", "-y", help="Skip confirmation prompt"),
) -> None:
    """Remove the RAG Facile CLI.

    By default, only removes the rag-facile CLI itself. Use --all to also
    remove the entire toolchain installed by the installer (proto, moon,
    uv, just, direnv, and shell profile entries).
    """
    items = _collect_items_to_remove(include_tools=all_tools)
    found_items = [(label, detail, exists) for label, detail, exists in items if exists]

    if not found_items:
        console.print("[green]Nothing to uninstall — rag-facile not found.[/green]")
        raise typer.Exit()

    # Show what will be removed
    console.print("\n[bold]The following will be removed:[/bold]\n")
    table = Table(show_header=False, box=None, padding=(0, 2))
    for label, detail, _ in found_items:
        table.add_row(f"[red]✗[/red]  {label}", f"[dim]{detail}[/dim]")
    console.print(table)

    if not all_tools:
        console.print(
            "\n[dim]Tip: use --all to also remove the toolchain "
            "(proto, moon, uv, just, direnv).[/dim]"
        )

    console.print()

    if not yes:
        confirm = typer.confirm("Proceed with uninstall?", default=False)
        if not confirm:
            console.print("[yellow]Uninstall cancelled.[/yellow]")
            raise typer.Exit()

    # Step 1: Remove rag-facile CLI (while uv still exists)
    console.print("\n[bold]Removing rag-facile CLI...[/bold]")
    if _tool_exists("uv"):
        if _run_quiet(["uv", "tool", "uninstall", "rag-facile-cli"]):
            console.print("  [green]✓[/green] Removed rag-facile CLI")
        else:
            # Fallback: manual removal
            _remove_cli_manually()
    else:
        _remove_cli_manually()

    if not all_tools:
        console.print(
            "\n[bold green]RAG Facile CLI has been uninstalled.[/bold green]\n"
        )
        raise typer.Exit()

    # Step 2: Remove proto-managed tools
    if _tool_exists("proto"):
        console.print("\n[bold]Removing proto-managed tools...[/bold]")
        for tool in ("moon", "uv", "just"):
            if _run_quiet(["proto", "uninstall", tool]):
                console.print(f"  [green]✓[/green] Removed {tool}")
            else:
                console.print(f"  [dim]⊘[/dim] {tool} was not installed via proto")

    # Step 3: Remove proto itself
    if PROTO_HOME.exists():
        console.print("\n[bold]Removing proto...[/bold]")
        shutil.rmtree(PROTO_HOME, ignore_errors=True)
        console.print(f"  [green]✓[/green] Removed {PROTO_HOME}")

    # Step 4: Remove direnv (Unix only)
    if not _is_windows() and _tool_exists("direnv"):
        console.print("\n[bold]Removing direnv...[/bold]")
        if _tool_exists("brew"):
            _run_quiet(["brew", "uninstall", "direnv"])
            console.print("  [green]✓[/green] Removed direnv (brew)")
        elif _tool_exists("apt-get"):
            _run_quiet(["sudo", "apt-get", "remove", "-y", "direnv"])
            console.print("  [green]✓[/green] Removed direnv (apt)")
        else:
            console.print(
                "  [yellow]![/yellow] Could not auto-remove direnv — remove it manually"
            )

    # Step 5: Clean shell profiles / Windows PATH
    if _is_windows():
        console.print("\n[bold]Cleaning Windows PATH...[/bold]")
        if _clean_windows_path():
            console.print("  [green]✓[/green] Removed toolchain entries from User PATH")
        else:
            console.print("  [dim]⊘[/dim] No entries to remove")
    else:
        console.print("\n[bold]Cleaning shell profiles...[/bold]")
        cleaned_any = False
        for profile in SHELL_PROFILES:
            if _clean_shell_profile(profile):
                console.print(f"  [green]✓[/green] Cleaned {profile.name}")
                cleaned_any = True
        if not cleaned_any:
            console.print("  [dim]⊘[/dim] No installer entries found")

    # Done
    console.print(
        "\n[bold green]RAG Facile and its toolchain have been uninstalled.[/bold green]"
    )
    console.print("[dim]Restart your terminal to apply PATH changes.[/dim]\n")


def _remove_cli_manually() -> None:
    """Remove the rag-facile CLI by deleting its files directly."""
    # Remove the entry point script
    rf_bin = UV_BIN_DIR / "rag-facile"
    if rf_bin.exists():
        rf_bin.unlink()

    # Remove the tool virtual environment
    tool_dir = UV_TOOLS_DIR / "rag-facile-cli"
    if tool_dir.exists():
        shutil.rmtree(tool_dir, ignore_errors=True)

    console.print("  [green]✓[/green] Removed rag-facile CLI")
