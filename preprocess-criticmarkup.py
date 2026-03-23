#!/usr/bin/env python3
"""
preprocess-criticmarkup.py

Converts CriticMarkup syntax to Pandoc bracketed spans.
Reads from stdin or a file argument, writes to stdout.

This avoids the LaTeX escaping bugs in filters that inject raw LaTeX,
because the content inside spans goes through Pandoc's normal parser
and serializer, which handles special characters correctly.

CriticMarkup        → Pandoc span
{++ added text ++}  → [added text]{.cm-added}
{-- deleted text --}→ [deleted text]{.cm-deleted}
{~~ old ~> new ~~}  → [old]{.cm-deleted}[new]{.cm-added}
{== highlight ==}   → [highlight]{.cm-highlight}
{>> comment <<}     → [comment]{.cm-comment}
"""

import re
import sys


def collapse_whitespace(text: str) -> str:
    """Collapse internal newlines to spaces (spans are inline elements)."""
    return re.sub(r"\n\s*", " ", text).strip()


def convert_criticmarkup(text: str) -> str:
    """Convert CriticMarkup to Pandoc bracketed spans."""

    # Substitutions first (most specific pattern):
    # {~~old~>new~~} → [old]{.cm-deleted}[new]{.cm-added}
    text = re.sub(
        r"\{~~(.*?)~>(.*?)~~\}",
        lambda m: (
            f"[{collapse_whitespace(m.group(1))}]{{.cm-deleted}}"
            f"[{collapse_whitespace(m.group(2))}]{{.cm-added}}"
        ),
        text,
        flags=re.DOTALL,
    )

    # Additions: {++text++} → [text]{.cm-added}
    text = re.sub(
        r"\{\+\+(.*?)\+\+\}",
        lambda m: f"[{collapse_whitespace(m.group(1))}]{{.cm-added}}",
        text,
        flags=re.DOTALL,
    )

    # Deletions: {--text--} → [text]{.cm-deleted}
    text = re.sub(
        r"\{--(.*?)--\}",
        lambda m: f"[{collapse_whitespace(m.group(1))}]{{.cm-deleted}}",
        text,
        flags=re.DOTALL,
    )

    # Highlights: {==text==} → [text]{.cm-highlight}
    text = re.sub(
        r"\{==(.*?)==\}",
        lambda m: f"[{collapse_whitespace(m.group(1))}]{{.cm-highlight}}",
        text,
        flags=re.DOTALL,
    )

    # Comments: {>>text<<} → [text]{.cm-comment}
    text = re.sub(
        r"\{>>(.*?)<<\}",
        lambda m: f"[{collapse_whitespace(m.group(1))}]{{.cm-comment}}",
        text,
        flags=re.DOTALL,
    )

    return text


if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1] != "-":
        with open(sys.argv[1]) as f:
            text = f.read()
    else:
        text = sys.stdin.read()

    sys.stdout.write(convert_criticmarkup(text))
