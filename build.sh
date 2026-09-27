#!/usr/bin/env bash
set -euo pipefail
export TERM="${TERM:-xterm}"

PROJECT="Axiomathic"

# 1. Traditional PDF from exactly the same LaTeX source.
pdflatex -interaction=nonstopmode -halt-on-error "${PROJECT}.tex"
if command -v bibtex >/dev/null 2>&1 && [[ -f "${PROJECT}.aux" ]]; then
  bibtex "$PROJECT" || true
fi
pdflatex -interaction=nonstopmode -halt-on-error "${PROJECT}.tex"
pdflatex -interaction=nonstopmode -halt-on-error "${PROJECT}.tex"

# 2. HTML.  FileDepth=0 (in preamble.tex) gives one web page per chapter.
rm -f ./*.html
lwarpmk html -p "$PROJECT"

# If BibTeX is available, build the HTML bibliography too.
if command -v bibtex >/dev/null 2>&1 && [[ -f "${PROJECT}_html.aux" ]]; then
  bibtex "${PROJECT}_html" || true
  lwarpmk again -p "$PROJECT"
  lwarpmk html -p "$PROJECT"
fi

# Render any TikZ/LaTeX image fragments requested by lwarp.
lwarpmk limages -p "$PROJECT" || true

# 3. Layer the reusable Axiomathic theme on top of lwarp's structural CSS.
cat lwarp.css web/axiomathic.css > site.css
python3 web/postprocess.py

# 4. Gather only deployable static files.
rm -rf site
mkdir -p site
for f in *.html; do
  case "$f" in
    *_html.html) ;;
    *) cp "$f" site/ ;;
  esac
done
cp site.css web/theme.js "${PROJECT}.pdf" site/

# Conventional asset folders are copied verbatim when present.
for d in assets figures images; do
  if [[ -d "$d" ]]; then
    cp -R "$d" site/
  fi
done
if [[ -d lateximages ]]; then
  cp -R lateximages site/
fi

touch site/.nojekyll

echo "Built site/index.html and ${PROJECT}.pdf"
