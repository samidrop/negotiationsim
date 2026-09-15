"""Terminal formatting helpers: colour, rules, and simple tables."""

from __future__ import annotations

import os
import sys

_ENABLED = sys.stdout.isatty() and os.environ.get("NO_COLOR") is None

_CODES = {
    "reset": "\033[0m",
    "bold": "\033[1m",
    "dim": "\033[2m",
    "red": "\033[31m",
    "green": "\033[32m",
    "yellow": "\033[33m",
    "blue": "\033[34m",
    "magenta": "\033[35m",
    "cyan": "\033[36m",
}

WIDTH = 74


def paint(text: str, *styles: str) -> str:
    if not _ENABLED or not styles:
        return text
    prefix = "".join(_CODES[s] for s in styles)
    return f"{prefix}{text}{_CODES['reset']}"


def rule(char: str = "-") -> str:
    return paint(char * WIDTH, "dim")


def heading(text: str) -> str:
    return f"\n{paint(text.upper(), 'bold', 'cyan')}\n{rule('=')}"


def subheading(text: str) -> str:
    return f"\n{paint(text, 'bold')}"


def wrap(text: str, indent: str = "") -> str:
    import textwrap

    return textwrap.fill(
        text, width=WIDTH, initial_indent=indent, subsequent_indent=indent
    )


def table(headers: list[str], rows: list[list[str]], aligns: str = "") -> str:
    """Render a plain text table. `aligns` is one char per column: l or r."""
    cols = len(headers)
    aligns = (aligns + "l" * cols)[:cols]
    widths = [len(h) for h in headers]
    for row in rows:
        for i, cell in enumerate(row):
            widths[i] = max(widths[i], len(str(cell)))

    def line(cells: list[str], style: tuple[str, ...] = ()) -> str:
        parts = []
        for i, cell in enumerate(cells):
            text = str(cell)
            parts.append(text.rjust(widths[i]) if aligns[i] == "r" else text.ljust(widths[i]))
        return paint("  ".join(parts).rstrip(), *style)

    out = [line(headers, ("bold",)), paint("  ".join("-" * w for w in widths), "dim")]
    out.extend(line(r) for r in rows)
    return "\n".join(out)


def bar(value: int, maximum: int, width: int = 24, style: str = "green") -> str:
    filled = 0 if maximum <= 0 else max(0, min(width, round(width * value / maximum)))
    return paint("#" * filled, style) + paint("." * (width - filled), "dim")
