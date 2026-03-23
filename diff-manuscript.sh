#!/usr/bin/env bash
set -euo pipefail

# ── Usage ───────────────────────────────────────────────────────────
usage() {
  cat <<EOF
Usage: $(basename "$0") OLD NEW [OPTIONS]

Generate a highlighted diff of two Quarto documents.

Arguments:
  OLD           Path to the original .qmd file
  NEW           Path to the revised .qmd file

Options:
  --to FORMAT   Output format: pdf (default), html, docx
  --output FILE Output filename (default: <NEW>-diff.<ext>)
  --keep        Keep the intermediate .qmd file
  -h, --help    Show this help

Examples:
  $(basename "$0") manuscript-v1.qmd manuscript-v2.qmd
  $(basename "$0") manuscript-v1.qmd manuscript-v2.qmd --to html
  $(basename "$0") manuscript-v1.qmd manuscript-v2.qmd --to pdf --output changes.pdf

With git (diff current file against a tagged version):
  git show v1-submission:manuscript.qmd > /tmp/old.qmd
  $(basename "$0") /tmp/old.qmd manuscript.qmd
EOF
  exit 0
}

# ── Parse arguments ─────────────────────────────────────────────────
[[ $# -lt 2 ]] && usage

OLD="$1"; shift
NEW="$1"; shift

FORMAT="pdf"
OUTPUT=""
KEEP=false

while [[ $# -gt 0 ]]; do
  case "$1" in
    --to)     FORMAT="$2"; shift 2 ;;
    --output) OUTPUT="$2"; shift 2 ;;
    --keep)   KEEP=true; shift ;;
    -h|--help) usage ;;
    *) echo "Unknown option: $1" >&2; exit 1 ;;
  esac
done

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
BASENAME="$(basename "${NEW%.qmd}")"
DIFF_QMD="${BASENAME}-diff.qmd"

if [[ -z "$OUTPUT" ]]; then
  case "$FORMAT" in
    pdf)  OUTPUT="${BASENAME}-diff.pdf" ;;
    html) OUTPUT="${BASENAME}-diff.html" ;;
    docx) OUTPUT="${BASENAME}-diff.docx" ;;
    *)    OUTPUT="${BASENAME}-diff.${FORMAT}" ;;
  esac
fi

# ── Check dependencies ──────────────────────────────────────────────
for cmd in pandiff python3 quarto; do
  if ! command -v "$cmd" &>/dev/null; then
    echo "Error: '$cmd' not found. Please install it first." >&2
    [[ "$cmd" == "pandiff" ]] && echo "  npm install -g pandiff" >&2
    exit 1
  fi
done

# ── Step 1: Extract YAML header from the new version ────────────────
echo "• Extracting metadata from ${NEW}..."
YAML=$(python3 -c "
import sys
text = open(sys.argv[1]).read()
# Find YAML frontmatter between --- delimiters
if text.startswith('---'):
    end = text.index('---', 3)
    print(text[:end + 3])
else:
    print('---\ntitle: Diff\n---')
" "$NEW")

# ── Step 2: Generate CriticMarkup diff ──────────────────────────────
echo "• Generating diff..."
DIFF=$(pandiff "$OLD" "$NEW" 2>/dev/null)

if [[ -z "$DIFF" ]]; then
  echo "No differences found between the two files."
  exit 0
fi

# ── Step 3: Preprocess CriticMarkup → Pandoc spans ──────────────────
echo "• Converting markup..."
PROCESSED=$(echo "$DIFF" | python3 "$SCRIPT_DIR/preprocess-criticmarkup.py")

# ── Step 4: Assemble the diff QMD ───────────────────────────────────
# Inject the Lua filter path into the YAML header
FILTER_PATH="$SCRIPT_DIR/diff-highlight.lua"

python3 - "$YAML" "$PROCESSED" "$FILTER_PATH" "$DIFF_QMD" <<'PYEOF'
import sys

yaml_block = sys.argv[1]
body = sys.argv[2]
filter_path = sys.argv[3]
output_path = sys.argv[4]

# Parse the YAML block and inject the filter
lines = yaml_block.strip().split("\n")
# Find the closing ---
closing = len(lines) - 1
for i in range(len(lines) - 1, 0, -1):
    if lines[i].strip() == "---":
        closing = i
        break

# Insert filter before closing ---
inject = [
    f"filters:",
    f"  - {filter_path}",
]
lines = lines[:closing] + inject + [lines[closing]]

with open(output_path, "w") as f:
    f.write("\n".join(lines))
    f.write("\n\n")
    f.write(body)
    f.write("\n")

PYEOF

echo "• Wrote ${DIFF_QMD}"

# ── Step 5: Render ──────────────────────────────────────────────────
echo "• Rendering to ${FORMAT}..."
quarto render "$DIFF_QMD" --to "$FORMAT" --output "$OUTPUT"

# ── Cleanup ─────────────────────────────────────────────────────────
if [[ "$KEEP" == false ]]; then
  rm -f "$DIFF_QMD"
fi

echo "✓ Done → ${OUTPUT}"
