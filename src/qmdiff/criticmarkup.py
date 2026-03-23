"""CriticMarkup to Pandoc span conversion.

Converts CriticMarkup syntax to Pandoc bracketed spans so that
Pandoc's normal parser handles special characters correctly,
avoiding LaTeX escaping bugs.

CriticMarkup        -> Pandoc span
{++ added text ++}  -> [added text]{.cm-added}
{-- deleted text --}-> [deleted text]{.cm-deleted}
{~~ old ~> new ~~}  -> [old]{.cm-deleted}[new]{.cm-added}
{== highlight ==}   -> [highlight]{.cm-highlight}
{>> comment <<}     -> [comment]{.cm-comment}
"""

import re


def collapse_whitespace(text: str) -> str:
    """Collapse internal newlines to spaces (spans are inline elements)."""
    return re.sub(r"\n\s*", " ", text).strip()


def convert_criticmarkup(text: str) -> str:
    """Convert CriticMarkup to Pandoc bracketed spans."""

    # Substitutions first (most specific pattern):
    # {~~old~>new~~} -> [old]{.cm-deleted}[new]{.cm-added}
    text = re.sub(
        r"\{~~(.*?)~>(.*?)~~\}",
        lambda m: (
            f"[{collapse_whitespace(m.group(1))}]{{.cm-deleted}}"
            f"[{collapse_whitespace(m.group(2))}]{{.cm-added}}"
        ),
        text,
        flags=re.DOTALL,
    )

    # Additions: {++text++} -> [text]{.cm-added}
    text = re.sub(
        r"\{\+\+(.*?)\+\+\}",
        lambda m: f"[{collapse_whitespace(m.group(1))}]{{.cm-added}}",
        text,
        flags=re.DOTALL,
    )

    # Deletions: {--text--} -> [text]{.cm-deleted}
    text = re.sub(
        r"\{--(.*?)--\}",
        lambda m: f"[{collapse_whitespace(m.group(1))}]{{.cm-deleted}}",
        text,
        flags=re.DOTALL,
    )

    # Highlights: {==text==} -> [text]{.cm-highlight}
    text = re.sub(
        r"\{==(.*?)==\}",
        lambda m: f"[{collapse_whitespace(m.group(1))}]{{.cm-highlight}}",
        text,
        flags=re.DOTALL,
    )

    # Comments: {>>text<<} -> [text]{.cm-comment}
    text = re.sub(
        r"\{>>(.*?)<<\}",
        lambda m: f"[{collapse_whitespace(m.group(1))}]{{.cm-comment}}",
        text,
        flags=re.DOTALL,
    )

    return text
