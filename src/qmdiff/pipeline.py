"""Pipeline orchestrator for diff generation."""

from __future__ import annotations

import subprocess
from pathlib import Path


class NoDiffError(Exception):
    """Raised when pandiff finds no differences."""


def get_filter_path() -> Path:
    """Return the path to the bundled Lua filter."""
    return Path(__file__).parent / "filters" / "diff-highlight.lua"


def run_pandiff(old: Path, new: Path) -> str:
    """Run pandiff on two files and return the CriticMarkup diff.

    Raises NoDiffError if the files are identical.
    Raises RuntimeError if pandiff fails.
    """
    result = subprocess.run(
        ["pandiff", str(old), str(new)],
        capture_output=True,
        text=True,
    )
    if result.returncode != 0:
        raise RuntimeError(f"pandiff failed: {result.stderr.strip()}")

    diff = result.stdout
    if not diff.strip():
        raise NoDiffError("No differences found between the two files.")

    return diff


def render_diff(
    diff_qmd: Path,
    output: Path,
    fmt: str,
    *,
    keep: bool = False,
) -> None:
    """Render the intermediate diff QMD to the target format.

    Raises RuntimeError if quarto fails.
    Removes the intermediate file unless keep=True.
    """
    result = subprocess.run(
        [
            "quarto",
            "render",
            str(diff_qmd),
            "--to",
            fmt,
            "--output",
            str(output),
        ],
        capture_output=True,
        text=True,
    )
    if result.returncode != 0:
        raise RuntimeError(f"quarto render failed: {result.stderr.strip()}")

    if not keep:
        diff_qmd.unlink(missing_ok=True)
