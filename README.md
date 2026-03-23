# qmdiff

Generate highlighted diffs between two versions of a Quarto manuscript. Produces a rendered document (PDF, HTML, or DOCX) showing additions in blue and deletions in red strikethrough.

## Prerequisites

qmdiff requires [**Quarto**](https://quarto.org/docs/get-started/) to be installed and on your PATH. qmdiff will check for this at startup and show install instructions if it's missing.

## Installation

```bash
uv tool install git+https://github.com/StanfordHPDS/qmdiff
```

Or for development:

```bash
git clone https://github.com/StanfordHPDS/qmdiff
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

1. Tokenizes both files into atomic units (prose words, code blocks, citations, math, inline code, cross-references, shortcodes)
2. Diffs prose at the word level using Python's `difflib`, producing CriticMarkup (`{++ ++}`, `{-- --}`)
3. Passes code blocks through from the new version without diff markup (so they remain executable)
4. Converts CriticMarkup to Pandoc bracketed spans
5. Extracts YAML frontmatter and injects a bundled Lua filter
6. Renders via `quarto render` with the Lua filter applying format-specific styling

The tokenizer ensures that Quarto-specific syntax (citations, math, cross-references, etc.) is never split by diff markers. If your YAML frontmatter specifies a custom format (e.g., `jasa-pdf`), qmdiff respects it rather than overriding with `--to`.
