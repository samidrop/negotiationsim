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


# --------------------------------------------------------------------------
# Layout helpers: panels and side-by-side columns.
# --------------------------------------------------------------------------

import re as _re

_ANSI = _re.compile(r"\033\[[0-9;]*m")


def visible_len(text: str) -> int:
    """Length as the eye sees it, ignoring invisible colour codes."""
    return len(_ANSI.sub("", text))


def pad(text: str, width: int) -> str:
    return text + " " * max(0, width - visible_len(text))


def truncate(text: str, width: int) -> str:
    if visible_len(text) <= width:
        return text
    plain = _ANSI.sub("", text)
    return plain[: max(0, width - 1)] + "~"


def columns(left: list[str], right: list[str], left_width: int, gap: str = " | ") -> str:
    """Put two blocks of text side by side, like a main view and a sidebar."""
    height = max(len(left), len(right))
    lines = []
    for i in range(height):
        l = truncate(left[i], left_width) if i < len(left) else ""
        r = right[i] if i < len(right) else ""
        lines.append(pad(l, left_width) + paint(gap, "dim") + r)
    return "\n".join(lines)


def panel(lines: list[str], title: str = "", width: int = WIDTH) -> str:
    """A boxed block of text."""
    inner = width - 4
    top = f"+- {paint(title, 'bold')} " + "-" * max(0, inner - visible_len(title) - 1) + "+"
    if not title:
        top = "+" + "-" * (width - 2) + "+"
    body = [f"| {pad(truncate(line, inner), inner)} |" for line in lines]
    bottom = "+" + "-" * (width - 2) + "+"
    return "\n".join([paint(top, "dim"), *body, paint(bottom, "dim")])


def meter(value: int, maximum: int, threshold: int | None = None, width: int = 18) -> str:
    """A horizontal bar with an optional walk-away marker shown as a pipe."""
    cells = []
    for i in range(width):
        lo = maximum * i / width
        filled = value > lo
        at_threshold = (
            threshold is not None and lo <= threshold < maximum * (i + 1) / width
        )
        if at_threshold:
            cells.append(paint("|", "bold", "red"))
        elif filled:
            cells.append(paint("#", "green" if threshold is None or value >= threshold else "yellow"))
        else:
            cells.append(paint(".", "dim"))
    return "".join(cells)
