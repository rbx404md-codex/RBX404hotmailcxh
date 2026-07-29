#!/usr/bin/env python3
"""
╔══════════════════════════════════════════╗
║        🧹 CACHE CLEANER  •  @RBX404      ║
╚══════════════════════════════════════════╝
Usage: python clear_cache.py
"""

import os
import shutil
import time

try:
    from rich.console import Console
    from rich.panel import Panel
    from rich.table import Table
    from rich import box
    from rich.text import Text
    from rich.progress import Progress, SpinnerColumn, TextColumn, BarColumn
except ImportError:
    os.system("pip install rich -q")
    from rich.console import Console
    from rich.panel import Panel
    from rich.table import Table
    from rich import box
    from rich.text import Text
    from rich.progress import Progress, SpinnerColumn, TextColumn, BarColumn

console = Console()

BOT_DIR = os.path.dirname(os.path.abspath(__file__))


def _human_size(b: int) -> str:
    for unit in ["B", "KB", "MB", "GB"]:
        if b < 1024:
            return f"{b:.2f} {unit}"
        b /= 1024
    return f"{b:.2f} TB"


def _dir_size(path: str) -> int:
    total = 0
    try:
        for dirpath, dirnames, filenames in os.walk(path):
            for f in filenames:
                try:
                    total += os.path.getsize(os.path.join(dirpath, f))
                except:
                    pass
    except:
        pass
    return total


def clear_pycache(base: str):
    """Remove all __pycache__ dirs and .pyc files."""
    removed_dirs  = 0
    removed_files = 0
    freed_bytes   = 0

    for root, dirs, files in os.walk(base):
        # Skip .git
        dirs[:] = [d for d in dirs if d != ".git"]

        if "__pycache__" in dirs:
            path = os.path.join(root, "__pycache__")
            sz = _dir_size(path)
            try:
                shutil.rmtree(path)
                freed_bytes += sz
                removed_dirs += 1
            except Exception as e:
                console.print(f"  [red]Failed to remove {path}: {e}[/red]")
            dirs.remove("__pycache__")

        for f in files:
            if f.endswith(".pyc") or f.endswith(".pyo"):
                fp = os.path.join(root, f)
                try:
                    sz = os.path.getsize(fp)
                    os.remove(fp)
                    freed_bytes += sz
                    removed_files += 1
                except:
                    pass

    return removed_dirs, removed_files, freed_bytes


def clear_log_file(base: str):
    """Truncate bot.log to zero."""
    log_path = os.path.join(base, "bot.log")
    freed = 0
    if os.path.exists(log_path):
        try:
            freed = os.path.getsize(log_path)
            with open(log_path, "w") as f:
                f.truncate(0)
        except:
            pass
    return freed


def clear_tmp_files(base: str):
    """Remove temp / leftover files."""
    patterns = [".tmp", ".bak", "~"]
    removed = 0
    freed   = 0
    for root, dirs, files in os.walk(base):
        dirs[:] = [d for d in dirs if d != ".git"]
        for f in files:
            if any(f.endswith(p) for p in patterns):
                fp = os.path.join(root, f)
                try:
                    freed += os.path.getsize(fp)
                    os.remove(fp)
                    removed += 1
                except:
                    pass
    return removed, freed


def main():
    console.print()
    console.print(Panel.fit(
        "[bold cyan]🧹  CACHE CLEANER[/bold cyan]\n"
        "[dim]Blackout Zone Checker Bot  •  Dev: @RBX404[/dim]",
        border_style="cyan"
    ))
    console.print()

    start = time.time()

    results = {}

    with Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        BarColumn(bar_width=30),
        console=console,
        transient=True,
    ) as progress:
        t1 = progress.add_task("[cyan]Clearing __pycache__ & .pyc files...", total=None)
        dirs, files, freed1 = clear_pycache(BOT_DIR)
        progress.update(t1, completed=True)
        results["pycache"] = (dirs, files, freed1)

        t2 = progress.add_task("[yellow]Truncating bot.log...", total=None)
        freed2 = clear_log_file(BOT_DIR)
        progress.update(t2, completed=True)
        results["log"] = freed2

        t3 = progress.add_task("[magenta]Removing temp files...", total=None)
        tmp_cnt, freed3 = clear_tmp_files(BOT_DIR)
        progress.update(t3, completed=True)
        results["tmp"] = (tmp_cnt, freed3)

    elapsed = time.time() - start
    total_freed = results["pycache"][2] + results["log"] + results["tmp"][1]

    # Build summary table
    table = Table(box=box.ROUNDED, show_header=True, header_style="bold magenta",
                  title="[bold white]🧹 Cache Clean Summary[/bold white]")
    table.add_column("Item",      style="bold cyan",  no_wrap=True)
    table.add_column("Removed",   style="white",      justify="right")
    table.add_column("Freed",     style="bold green",  justify="right")

    d, f, sz = results["pycache"]
    table.add_row(
        "📁 __pycache__ dirs",
        str(d),
        _human_size(sz)
    )
    table.add_row(
        "🐍 .pyc/.pyo files",
        str(f),
        ""
    )
    table.add_row(
        "📋 bot.log",
        "truncated",
        _human_size(results["log"])
    )
    tc, ts = results["tmp"]
    table.add_row(
        "🗑️  temp files",
        str(tc),
        _human_size(ts)
    )

    console.print(table)
    console.print()
    console.print(Panel(
        f"[bold green]✅ Done![/bold green]  "
        f"Freed [bold yellow]{_human_size(total_freed)}[/bold yellow]  •  "
        f"took [dim]{elapsed:.2f}s[/dim]",
        border_style="green"
    ))
    console.print()

    # Return summary dict for bot command use
    return {
        "pycache_dirs":  results["pycache"][0],
        "pyc_files":     results["pycache"][1],
        "freed_pycache": results["pycache"][2],
        "freed_log":     results["log"],
        "freed_tmp":     results["tmp"][1],
        "tmp_files":     results["tmp"][0],
        "total_freed":   total_freed,
        "elapsed":       elapsed,
    }


def run_cache_clear() -> dict:
    """Call from bot — returns summary dict without printing to console."""
    results = {}

    dirs, files, freed1 = clear_pycache(BOT_DIR)
    results["pycache_dirs"]  = dirs
    results["pyc_files"]     = files
    results["freed_pycache"] = freed1

    freed2 = clear_log_file(BOT_DIR)
    results["freed_log"]     = freed2

    tmp_cnt, freed3 = clear_tmp_files(BOT_DIR)
    results["tmp_files"]     = tmp_cnt
    results["freed_tmp"]     = freed3

    results["total_freed"]   = freed1 + freed2 + freed3
    return results


if __name__ == "__main__":
    main()
