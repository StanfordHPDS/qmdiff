"""Git revision extraction."""

from __future__ import annotations

import subprocess
from pathlib import Path


def validate_revision(rev: str) -> None:
    """Check that a git revision (tag, branch, SHA) exists.

    Raises ValueError if the revision is invalid.
    """
    result = subprocess.run(
        ["git", "rev-parse", "--verify", rev],
        capture_output=True,
        text=True,
    )
    if result.returncode != 0:
        raise ValueError(f"Invalid git revision: {rev}")


def extract_file_at_revision(file_path: str, rev: str, tmp_dir: Path) -> Path:
    """Extract a file's contents at a given git revision to a temp file.

    Returns the path to the temporary .qmd file.
    Raises FileNotFoundError if the file doesn't exist at that revision.
    """
    result = subprocess.run(
        ["git", "show", f"{rev}:{file_path}"],
        capture_output=True,
        text=True,
    )
    if result.returncode != 0:
        raise FileNotFoundError(
            f"File '{file_path}' not found at revision '{rev}': {result.stderr.strip()}"
        )

    stem = Path(file_path).stem
    out = tmp_dir / f"{stem}-{rev}.qmd"
    out.write_text(result.stdout)
    return out
