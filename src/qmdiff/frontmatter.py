"""YAML frontmatter extraction and filter injection."""

from __future__ import annotations

_DEFAULT_YAML = "---\ntitle: Diff\n---"


def extract_frontmatter(text: str) -> tuple[str, str]:
    """Extract YAML frontmatter and body from a QMD file.

    Returns (yaml_block, body). If no frontmatter is found,
    returns a default YAML block and the full text as body.
    """
    if not text.startswith("---"):
        return _DEFAULT_YAML, text

    # Find closing --- (skip opening ---)
    end = text.index("---", 3)
    yaml = text[: end + 3]
    body = text[end + 3 :]
    # Strip exactly one leading newline from body
    if body.startswith("\n"):
        body = body[1:]
    return yaml, body


def has_format(yaml_block: str) -> bool:
    """Check if the YAML frontmatter contains a format: key."""
    for line in yaml_block.split("\n"):
        if line.startswith("format:"):
            return True
    return False


def inject_filter(yaml_block: str, filter_path: str) -> str:
    """Inject a Lua filter path into the YAML frontmatter.

    Merges with existing filters: key if present.
    """
    lines = yaml_block.strip().split("\n")

    # Find closing ---
    closing = len(lines) - 1
    for i in range(len(lines) - 1, 0, -1):
        if lines[i].strip() == "---":
            closing = i
            break

    # Check if filters: already exists
    filters_idx = None
    for i, line in enumerate(lines):
        if line.startswith("filters:"):
            filters_idx = i
            break

    if filters_idx is not None:
        # Find the end of the existing filters list
        insert_at = filters_idx + 1
        while insert_at < closing and lines[insert_at].startswith("  - "):
            insert_at += 1
        lines.insert(insert_at, f"  - {filter_path}")
    else:
        inject = [
            "filters:",
            f"  - {filter_path}",
        ]
        lines = lines[:closing] + inject + [lines[closing]]

    return "\n".join(lines)


def assemble_qmd(yaml_block: str, body: str, filter_path: str) -> str:
    """Assemble a complete QMD from YAML, body, and filter path."""
    injected_yaml = inject_filter(yaml_block, filter_path)
    return injected_yaml + "\n\n" + body + "\n"
