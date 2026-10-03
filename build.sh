#!/usr/bin/env bash
set -euo pipefail
export TERM="${TERM:-xterm}"

PROJECT="Axiomathic"
WEBPROJECT="${PROJECT}_web"

log() {
  printf '\n==> %s\n' "$*"
}

log "Cleaning previous generated site artefacts"
rm -rf site "${WEBPROJECT}-images" lateximages
rm -f ./*.html site.css "${WEBPROJECT}.tex"

log "Building ordinary PDF from ${PROJECT}.tex"
pdflatex -interaction=nonstopmode -halt-on-error "${PROJECT}.tex"
if command -v bibtex >/dev/null 2>&1 && [[ -f "${PROJECT}.aux" ]]; then
  bibtex "$PROJECT" || true
fi
pdflatex -interaction=nonstopmode -halt-on-error "${PROJECT}.tex"
pdflatex -interaction=nonstopmode -halt-on-error "${PROJECT}.tex"

log "Creating temporary lwarp wrapper ${WEBPROJECT}.tex"
cat > "${WEBPROJECT}.tex" <<'TEX'
\def\AXIOMATHICWEB{}
\input{Axiomathic.tex}
TEX

log "Priming lwarp"
pdflatex -interaction=nonstopmode -halt-on-error "${WEBPROJECT}.tex"

log "Building first HTML pass"
lwarpmk html -p "$WEBPROJECT"

if command -v bibtex >/dev/null 2>&1 && [[ -f "${WEBPROJECT}_html.aux" ]]; then
  log "Building HTML bibliography"
  bibtex "${WEBPROJECT}_html" || true
  lwarpmk again -p "$WEBPROJECT"
  lwarpmk html -p "$WEBPROJECT"
fi

log "Rendering lwarp LaTeX/TikZ image fragments"
# This is intentionally not hidden behind `|| true`: if TikZ/image generation
# fails, the GitHub Actions log should show the real error rather than shipping
# broken <img> references.
lwarpmk limages -p "$WEBPROJECT"

log "Generated lwarp image files"
find "${WEBPROJECT}-images" lateximages -maxdepth 2 -type f 2>/dev/null | sort || true

log "Converting generated SVGs to PNG fallback images when rsvg-convert is available"
# GitHub Pages normally serves SVG correctly, but some lwarp-generated SVGs have
# been awkward in-browser. PNG fallbacks are more predictable for TikZ diagrams.
if command -v rsvg-convert >/dev/null 2>&1 && [[ -d "${WEBPROJECT}-images" ]]; then
  while IFS= read -r -d '' svg; do
    png="${svg%.svg}.png"
    rsvg-convert "$svg" -o "$png"
  done < <(find "${WEBPROJECT}-images" -type f -name '*.svg' -print0)
else
  echo "rsvg-convert not available or ${WEBPROJECT}-images missing; retaining SVG references."
fi

log "Rebuilding final HTML pass after image generation"
lwarpmk html -p "$WEBPROJECT"

log "Generating Axiomathic site config"
python3 web/generate-site-config.py

log "Combining CSS and post-processing HTML"
cat lwarp.css web/axiomathic.css > site.css
python3 web/postprocess.py

log "Rewriting lwarp image references to PNG fallbacks where available"
python3 - <<'PY'
from pathlib import Path
import re

image_dir = Path('Axiomathic_web-images')
if image_dir.exists():
    for html in Path('.').glob('*.html'):
        if html.name.endswith('_html.html'):
            continue
        text = html.read_text(encoding='utf-8')
        def repl(match):
            src = match.group(1)
            png = Path(src).with_suffix('.png')
            if png.exists():
                return f'src="{png.as_posix()}"'
            return match.group(0)
        text = re.sub(r'src="([^"]*Axiomathic_web-images/[^"]+?)\.svg"', repl, text)
        html.write_text(text, encoding='utf-8')
PY

log "Gathering deployable static files"
rm -rf site
mkdir -p site
for f in *.html; do
  case "$f" in
    *_html.html) ;;
    *) cp "$f" site/ ;;
  esac
done
cp site.css web/theme.js "${PROJECT}.pdf" site/

for d in assets figures images media; do
  if [[ -d "$d" ]]; then
    cp -R "$d" site/
  fi
done

# Copy lwarp-generated TikZ/LaTeX image directories exactly where the HTML
# expects them, e.g. site/Axiomathic_web-images/image-1.png.
for d in "${WEBPROJECT}-images" lateximages; do
  if [[ -d "$d" ]]; then
    cp -R "$d" site/
  fi
done

# Article-specific media may live beside a subfile. Copy only media folders,
# preserving their paths, rather than publishing the LaTeX sources themselves.
if [[ -d sections ]]; then
  while IFS= read -r -d '' f; do
    mkdir -p "site/$(dirname "$f")"
    cp "$f" "site/$f"
  done < <(find sections -type f \( -path '*/images/*' -o -path '*/figures/*' -o -path '*/media/*' \) -print0)
fi

touch site/.nojekyll

log "Files in deployed site relevant to lwarp images"
find site -maxdepth 4 \( -path "*${WEBPROJECT}-images*" -o -path "*lateximages*" \) -type f | sort || true

rm -f "${WEBPROJECT}.tex"

log "Built site/index.html and ${PROJECT}.pdf"
