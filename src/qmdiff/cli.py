"""CLI entry point for qmdiff."""

from __future__ import annotations

import tempfile
from pathlib import Path

import click

from qmdiff import __version__
from qmdiff.criticmarkup import convert_criticmarkup
from qmdiff.deps import check_dependencies
from qmdiff.differ import diff_texts
from qmdiff.frontmatter import extract_frontmatter, has_format, assemble_qmd
from qmdiff.git import validate_revision, extract_file_at_revision
from qmdiff.pipeline import get_filter_path, render_diff


@click.command()
@click.version_option(version=__version__)
@click.argument("files", nargs=-1, required=True)
@click.option("--output", "-o", required=True, help="Output filename (e.g. diff.pdf).")
@click.option(
    "--to",
    "fmt",
    default=None,
    type=click.Choice(["pdf", "html", "docx"]),
    help="Output format. Inferred from --output extension if omitted.",
)
@click.option(
    "--rev", default=None, help="Git revision to diff against (tag, branch, SHA)."
)
@click.option("--keep", is_flag=True, help="Keep the intermediate .qmd file.")
@click.option(
    "--yaml-from",
    "yaml_from",
    default=None,
    type=click.Path(exists=True),
    help="File to read YAML frontmatter from (default: first file).",
)
def main(
    files: tuple[str, ...],
    output: str,
    fmt: str | None,
    rev: str | None,
    keep: bool,
    yaml_from: str | None,
) -> None:
    """Generate a highlighted diff between two Quarto manuscript versions."""
    # --- Validate file count ---
    if rev:
        if len(files) != 1:
            raise click.UsageError("With --rev, provide exactly one file.")
    else:
        if len(files) != 2:
            raise click.UsageError("Provide exactly two files (OLD NEW), or use --rev.")

    # --- Infer format from output extension if --to not given ---
    # fmt stays None if YAML has a format: key (let quarto use it)
    output_path = Path(output)
    if fmt is None:
        ext = output_path.suffix.lstrip(".")
        if ext not in ("pdf", "html", "docx"):
            raise click.UsageError(
                f"Cannot infer format from '{output}'. Use --to pdf|html|docx."
            )
        # Will be refined in _run_pipeline after reading YAML
        fmt = ext

    # --- Check dependencies ---
    try:
        check_dependencies()
    except Exception as e:
        raise click.ClickException(str(e))

    # --- Resolve YAML source: default is files[0] (OLD in two-file, current in git) ---
    yaml_source = Path(yaml_from) if yaml_from else Path(files[0])

    # --- Resolve input files ---
    if rev:
        validate_revision(rev)
        current_file = Path(files[0])
        with tempfile.TemporaryDirectory() as tmp:
            old_file = extract_file_at_revision(files[0], rev, Path(tmp))
            _run_pipeline(old_file, current_file, output_path, fmt, keep, yaml_source)
    else:
        old_file = Path(files[0])
        new_file = Path(files[1])
        _run_pipeline(old_file, new_file, output_path, fmt, keep, yaml_source)


def _run_pipeline(
    old: Path, new: Path, output: Path, fmt: str, keep: bool, yaml_source: Path
) -> None:
    """Run the full diff pipeline."""
    click.echo("Generating diff...")

    old_text = old.read_text()
    new_text = new.read_text()

    diff = diff_texts(old_text, new_text)
    if diff == new_text:
        click.echo("No differences found.")
        return

    click.echo("Converting markup...")
    processed = convert_criticmarkup(diff)

    click.echo("Extracting metadata...")
    source_text = yaml_source.read_text()
    yaml, _body = extract_frontmatter(source_text)

    # If YAML already specifies a format, let quarto use it
    render_fmt = None if has_format(yaml) else fmt

    filter_path = get_filter_path()
    diff_qmd = output.with_suffix(".qmd")
    diff_qmd.write_text(assemble_qmd(yaml, processed, str(filter_path)))
    click.echo(f"Wrote {diff_qmd}")

    click.echo(f"Rendering to {render_fmt or 'YAML format'}...")
    render_diff(diff_qmd, output, render_fmt, keep=keep)
    click.echo(f"Done -> {output}")
