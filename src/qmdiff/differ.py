"""Word-level differ for Quarto manuscripts.

Tokenizes text into atomic units (code blocks, citations, math, inline code,
shortcodes, cross-references, and words), then diffs using a two-level
approach: paragraphs are matched first, then word-level diffs are computed
within matched paragraphs. This prevents cross-section matching artifacts.

Code blocks are never diffed — the new version is used as-is.
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


def _split_paragraphs(text: str) -> list[str]:
    """Split text into paragraphs (separated by blank lines).

    Code blocks are treated as single paragraphs regardless of blank lines
    within them.
    """
    # First, protect code blocks by replacing them with placeholders
    code_blocks: list[str] = []
    code_re = re.compile(r"```[^\n]*\n.*?```", re.DOTALL)

    def _replace_code(m: re.Match) -> str:
        code_blocks.append(m.group())
        return f"\x00CODE{len(code_blocks) - 1}\x00"

    protected = code_re.sub(_replace_code, text)

    # Split on blank lines
    raw_paras = re.split(r"\n\n+", protected)

    # Restore code blocks
    result = []
    for para in raw_paras:
        restored = para
        for i, code in enumerate(code_blocks):
            restored = restored.replace(f"\x00CODE{i}\x00", code)
        if restored.strip():
            result.append(restored)

    return result


_SIMILARITY_THRESHOLD = 0.4


def _paragraph_similarity(old_para: str, new_para: str) -> float:
    """Compute similarity ratio between two paragraphs (0.0 to 1.0)."""
    return difflib.SequenceMatcher(None, old_para.split(), new_para.split()).ratio()


def _diff_paragraph(old_para: str, new_para: str) -> str:
    """Word-level diff of a single paragraph pair.

    If paragraphs are too dissimilar, emits a full delete + add instead
    of interleaved word-level diffs.
    """
    if _paragraph_similarity(old_para, new_para) < _SIMILARITY_THRESHOLD:
        return _mark_deleted(old_para) + "\n\n" + _mark_added(new_para)

    old_tokens = tokenize(old_para)
    new_tokens = tokenize(new_para)

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


def _mark_deleted(para: str) -> str:
    """Mark an entire paragraph as deleted."""
    tokens = tokenize(para)
    parts: list[str] = []
    for token in tokens:
        if _is_code_block(token):
            pass  # Omit deleted code blocks
        elif token.strip():
            parts.append("{--" + token + "--}")
        else:
            parts.append(token)
    return "".join(parts)


def _mark_added(para: str) -> str:
    """Mark an entire paragraph as added."""
    tokens = tokenize(para)
    parts: list[str] = []
    for token in tokens:
        if _is_code_block(token):
            parts.append(token)  # Code blocks pass through
        elif token.strip():
            parts.append("{++" + token + "++}")
        else:
            parts.append(token)
    return "".join(parts)


def diff_texts(old: str, new: str) -> str:
    """Produce a CriticMarkup diff between old and new text.

    Uses a two-level approach: paragraphs are matched first via difflib,
    then word-level diffs are computed within matched paragraph pairs.
    Code blocks are not diffed — the new version is emitted as-is.
    """
    old_paras = _split_paragraphs(old)
    new_paras = _split_paragraphs(new)

    sm = difflib.SequenceMatcher(None, old_paras, new_paras)
    result_parts: list[str] = []

    for op, i1, i2, j1, j2 in sm.get_opcodes():
        if op == "equal":
            result_parts.extend(old_paras[i1:i2])
        elif op == "insert":
            for para in new_paras[j1:j2]:
                result_parts.append(_mark_added(para))
        elif op == "delete":
            for para in old_paras[i1:i2]:
                result_parts.append(_mark_deleted(para))
        elif op == "replace":
            # Match paragraphs within the replaced block for word-level diffs
            old_block = old_paras[i1:i2]
            new_block = new_paras[j1:j2]

            # Pair up paragraphs for word-level diff, handle unequal lengths
            paired = min(len(old_block), len(new_block))
            for k in range(paired):
                result_parts.append(_diff_paragraph(old_block[k], new_block[k]))

            # Remaining unpaired paragraphs
            for para in old_block[paired:]:
                result_parts.append(_mark_deleted(para))
            for para in new_block[paired:]:
                result_parts.append(_mark_added(para))

    result = "\n\n".join(result_parts)
    # Preserve trailing newline if original had one
    if new.endswith("\n") and not result.endswith("\n"):
        result += "\n"
    return result


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
