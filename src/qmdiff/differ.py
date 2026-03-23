"""Word-level differ for Quarto manuscripts.

Tokenizes text into atomic units (code blocks, citations, math, inline code,
shortcodes, cross-references, and words), then diffs at the token level using
difflib. Code blocks are never diffed — the new version is used as-is.
"""

from __future__ import annotations

import difflib
import re

# Order matters: earlier patterns take priority.
# Each pattern should capture the full atomic token.
_TOKEN_PATTERNS = [
    # Fenced code blocks (``` with optional language)
    r"```[^\n]*\n.*?```",
    # Display math ($$...$$)
    r"\$\$\n.*?\n\$\$",
    # Shortcodes ({{< ... >}})
    r"\{\{<.*?>\}\}",
    # Citations ([...@...])
    r"\[[^\]]*@[^\]]+\]",
    # Inline code (`...`)
    r"`[^`]+`",
    # Inline math ($...$) — single $, not $$
    r"(?<!\$)\$(?!\$)[^$]+\$(?!\$)",
    # Cross-references (@sec-, @fig-, @tbl-, @eq-, @lst-, @thm-, etc.)
    r"@[a-zA-Z][\w-]*",
    # Regular words
    r"\S+",
    # Whitespace (preserved for roundtrip fidelity)
    r"\s+",
]

_TOKEN_RE = re.compile("|".join(f"({p})" for p in _TOKEN_PATTERNS), re.DOTALL)


def tokenize(text: str) -> list[str]:
    """Tokenize text into atomic units for diffing.

    Returns a list of tokens. Joining them reproduces the original text.
    """
    if not text:
        return []
    return [m.group() for m in _TOKEN_RE.finditer(text)]


def _is_code_block(token: str) -> bool:
    """Check if a token is a fenced code block."""
    return token.startswith("```")


def diff_texts(old: str, new: str) -> str:
    """Produce a CriticMarkup diff between old and new text.

    Code blocks are not diffed — the new version is emitted as-is.
    All other tokens are diffed at the word level.
    """
    old_tokens = tokenize(old)
    new_tokens = tokenize(new)

    sm = difflib.SequenceMatcher(None, old_tokens, new_tokens)
    parts: list[str] = []

    for op, i1, i2, j1, j2 in sm.get_opcodes():
        if op == "equal":
            parts.extend(old_tokens[i1:i2])
        elif op == "insert":
            _emit_insertions(new_tokens[j1:j2], parts)
        elif op == "delete":
            _emit_deletions(old_tokens[i1:i2], parts)
        elif op == "replace":
            _emit_replacement(old_tokens[i1:i2], new_tokens[j1:j2], parts)

    return "".join(parts)


def _emit_insertions(tokens: list[str], parts: list[str]) -> None:
    """Emit inserted tokens, skipping whitespace-only tokens from markup."""
    for token in tokens:
        if _is_code_block(token):
            parts.append(token)
        elif token.strip():
            parts.append("{++" + token + "++}")
        else:
            parts.append(token)


def _emit_deletions(tokens: list[str], parts: list[str]) -> None:
    """Emit deleted tokens."""
    for token in tokens:
        if _is_code_block(token):
            # Deleted code block — omit entirely
            pass
        elif token.strip():
            parts.append("{--" + token + "--}")
        else:
            parts.append(token)


def _emit_replacement(
    old_tokens: list[str], new_tokens: list[str], parts: list[str]
) -> None:
    """Emit a replacement, handling code blocks specially."""
    old_code = [t for t in old_tokens if _is_code_block(t)]
    new_code = [t for t in new_tokens if _is_code_block(t)]
    old_prose = [t for t in old_tokens if not _is_code_block(t)]
    new_prose = [t for t in new_tokens if not _is_code_block(t)]

    # If there are no code blocks, simple replacement
    if not old_code and not new_code:
        for token in old_prose:
            if token.strip():
                parts.append("{--" + token + "--}")
            else:
                parts.append(token)
        for token in new_prose:
            if token.strip():
                parts.append("{++" + token + "++}")
            else:
                parts.append(token)
        return

    # Mixed code and prose: emit prose diffs, then new code blocks
    for token in old_prose:
        if token.strip():
            parts.append("{--" + token + "--}")
        else:
            parts.append(token)
    for token in new_prose:
        if token.strip():
            parts.append("{++" + token + "++}")
        else:
            parts.append(token)
    for code in new_code:
        parts.append(code)
