# qmdiff

Generate highlighted diffs between two versions of a Quarto manuscript. Produces a rendered document (PDF, HTML, or DOCX) showing additions in blue and deletions in red strikethrough.

## Prerequisites

qmdiff requires two external tools to be installed and on your PATH:

- [**pandiff**](https://github.com/davidar/pandiff) — generates the underlying diff
  ```bash
  npm install -g pandiff
  ```
- [**Quarto**](https://quarto.org/docs/get-started/) — renders the final output

qmdiff will check for these at startup and show install instructions if they're missing.

## Installation

```bash
uv tool install git+https://github.com/malcolmbarrett/qmdiff
```

Or for development:

```bash
git clone https://github.com/malcolmbarrett/qmdiff
cd qmdiff
uv sync
```

## Usage

### Two-file mode

Compare two `.qmd` files directly:

```bash
qmdiff manuscript-v1.qmd manuscript-v2.qmd --output diff.pdf
qmdiff manuscript-v1.qmd manuscript-v2.qmd --output diff.html --to html
qmdiff manuscript-v1.qmd manuscript-v2.qmd --output diff.docx --to docx
```

### Git mode

Compare the current version of a file against a previous git revision:

```bash
qmdiff manuscript.qmd --rev v1-submission --output diff.pdf
qmdiff manuscript.qmd --rev HEAD~3 --output diff.html
```

### Options

| Option | Description |
|---|---|
| `--output`, `-o` | Output filename (required) |
| `--to` | Output format: `pdf`, `html`, `docx` (inferred from `--output` extension if omitted) |
| `--rev` | Git revision to diff against (tag, branch, or SHA) |
| `--yaml-from` | File to read YAML frontmatter from (default: first file in two-file mode, current file in git mode) |
| `--keep` | Keep the intermediate `.qmd` file |
| `--version` | Show version |
| `--help` | Show help |

## How it works

1. Runs `pandiff` to generate a CriticMarkup diff between the two versions
2. Converts CriticMarkup (`{++ ++}`, `{-- --}`, `{~~ ~> ~~}`) to Pandoc bracketed spans
3. Extracts YAML frontmatter and injects a bundled Lua filter
4. Renders via `quarto render` with the Lua filter applying format-specific styling

The CriticMarkup-to-spans conversion happens before Pandoc parsing, which avoids LaTeX escaping bugs that occur when injecting raw LaTeX in filters.
