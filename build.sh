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
# itself fails, the GitHub Actions log should show the real error rather than
# shipping broken <img> references.
lwarpmk limages -p "$WEBPROJECT"

log "Generated lwarp image files"
find "${WEBPROJECT}-images" lateximages -maxdepth 2 -type f 2>/dev/null | sort || true

log "Converting valid generated SVGs to PNG fallback images when rsvg-convert is available"
# Some lwarp-generated SVG files can be empty or malformed if the underlying
# TikZ fragment failed. Do not let one bad SVG kill the whole GitHub build.
if command -v rsvg-convert >/dev/null 2>&1; then
  for image_dir in "${WEBPROJECT}-images" lateximages; do
    if [[ -d "$image_dir" ]]; then
      while IFS= read -r -d '' svg; do
        png="${svg%.svg}.png"

        if [[ ! -s "$svg" ]]; then
          echo "WARNING: Skipping empty SVG: $svg"
          continue
        fi

        if ! head -c 500 "$svg" | grep -qi "<svg"; then
          echo "WARNING: Skipping non-SVG or malformed SVG: $svg"
          echo "First few lines of $svg:"
          sed -n '1,10p' "$svg" || true
          continue
        fi

        if rsvg-convert "$svg" -o "$png"; then
          echo "Converted $svg -> $png"
        else
          echo "WARNING: Failed to convert $svg to PNG; leaving SVG in place."
          rm -f "$png"
        fi
      done < <(find "$image_dir" -type f -name '*.svg' -print0)
    fi
  done
else
  echo "rsvg-convert not available; retaining SVG references."
fi

log "Rebuilding final HTML pass after image generation"
lwarpmk html -p "$WEBPROJECT"

log "Generating Axiomathic site config"
python3 web/generate-site-config.py

log "Combining CSS and post-processing HTML"
cat lwarp.css web/axiomathic.css > site.css
python3 web/postprocess.py

log "Rewriting HTML image references to PNG only where PNG fallbacks exist"
python3 - "$WEBPROJECT" <<'PY'
from pathlib import Path
import re
import sys

webproject = sys.argv[1]
image_dirs = [Path(f"{webproject}-images"), Path("lateximages")]

existing_pngs = set()
for image_dir in image_dirs:
    if image_dir.exists():
        for png in image_dir.rglob("*.png"):
            existing_pngs.add(png.as_posix())

if existing_pngs:
    pattern = re.compile(r'src="([^"]+?\.svg)"')
    for html in Path('.').glob('*.html'):
        if html.name.endswith('_html.html'):
            continue
        text = html.read_text(encoding='utf-8')

        def repl(match):
            svg_ref = match.group(1)
            png_ref = str(Path(svg_ref).with_suffix('.png')).replace('\\', '/')
            if png_ref in existing_pngs:
                return f'src="{png_ref}"'
            return match.group(0)

        html.write_text(pattern.sub(repl, text), encoding='utf-8')
else:
    print("No PNG fallbacks found; retaining SVG references.")
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
