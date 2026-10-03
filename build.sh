#!/usr/bin/env bash
set -Eeuo pipefail

# Robust Axiomathic build for GitHub Pages + lwarp TikZ images.
# This script deliberately fails if lwarp-generated images are missing,
# empty, or invalid, so TikZ failures are visible in GitHub Actions.

ROOT_DIR="$(pwd)"
MAIN_TEX="${MAIN_TEX:-Axiomathic.tex}"
WEBPROJECT="${WEBPROJECT:-Axiomathic_web}"
SITE_DIR="${SITE_DIR:-site}"
IMAGE_DIR="${WEBPROJECT}-images"
REPORT_DIR="build-reports"
REPORT_FILE="${REPORT_DIR}/lwarp-images-report.txt"

log() {
  printf '\n---- %s ----\n' "$1"
}

run_pdflatex() {
  local texfile="$1"
  pdflatex -interaction=nonstopmode -halt-on-error "$texfile"
}

log "Clean previous generated outputs"
rm -rf "$SITE_DIR" "$REPORT_DIR"
mkdir -p "$REPORT_DIR"
# Do not delete source-owned image folders. Only remove lwarp-generated wrappers/images.
rm -rf "$IMAGE_DIR"
rm -f "${WEBPROJECT}.tex" "${WEBPROJECT}.aux" "${WEBPROJECT}.log" "${WEBPROJECT}.toc" \
      "${WEBPROJECT}.out" "${WEBPROJECT}.idx" "${WEBPROJECT}.ind" "${WEBPROJECT}.ilg" \
      "${WEBPROJECT}.xwm" "${WEBPROJECT}.html" "${WEBPROJECT}.css" lwarp_*.*

log "Create temporary lwarp wrapper"
cat > "${WEBPROJECT}.tex" <<'TEX'
\def\AXIOMATHICWEB{}
\input{Axiomathic.tex}
TEX

log "Build normal PDF from ${MAIN_TEX}"
# PDF failures should fail the build. Run twice for references/TOC where possible.
run_pdflatex "$MAIN_TEX"
run_pdflatex "$MAIN_TEX" || true

log "Prime lwarp wrapper"
run_pdflatex "${WEBPROJECT}.tex"

log "First lwarp HTML pass"
lwarpmk html -p "$WEBPROJECT"

log "Generate lwarp image assets from TikZ/LaTeX fragments"
# Do not suppress errors here. If lwarp/dvisvgm fails, GitHub Actions should be red.
lwarpmk limages -p "$WEBPROJECT"

log "Validate generated lwarp images before final HTML"
python3 web/verify_lwarp_images.py \
  --image-dir "$IMAGE_DIR" \
  --report "$REPORT_FILE" \
  --require-images

log "Second lwarp HTML pass after images exist"
lwarpmk html -p "$WEBPROJECT"

log "Run site post-processing if present"
# Keep compatibility with previous Axiomathic builds. These scripts may either mutate
# the generated HTML in place or create config used by the theme.
if [ -f web/build_site_config.py ]; then
  python3 web/build_site_config.py || true
fi
if [ -f web/generate-site-config.py ]; then
  python3 web/generate-site-config.py || true
fi
if [ -f web/postprocess.py ]; then
  python3 web/postprocess.py || true
fi

log "Assemble GitHub Pages site directory"
mkdir -p "$SITE_DIR"

# Copy generated HTML/CSS from the repository root.
find . -maxdepth 1 -type f \( -name "*.html" -o -name "*.css" \) -exec cp {} "$SITE_DIR/" \;

# Copy the final PDF if available.
if [ -f "${MAIN_TEX%.tex}.pdf" ]; then
  cp "${MAIN_TEX%.tex}.pdf" "$SITE_DIR/"
fi

# Copy web theme assets expected by the postprocessor/theme.
if [ -f web/axiomathic.css ]; then
  cp web/axiomathic.css "$SITE_DIR/axiomathic.css"
fi
if [ -f web/theme.js ]; then
  cp web/theme.js "$SITE_DIR/theme.js"
fi
if [ -f web/site-config.json ]; then
  cp web/site-config.json "$SITE_DIR/site-config.json"
fi
if [ -f site-config.json ]; then
  cp site-config.json "$SITE_DIR/site-config.json"
fi

# Copy static assets.
if [ -d assets ]; then
  cp -R assets "$SITE_DIR/"
fi

# Copy source-owned article images, preserving paths referenced by HTML.
if [ -d sections ]; then
  find sections -type f \( -name "*.png" -o -name "*.jpg" -o -name "*.jpeg" -o -name "*.svg" -o -name "*.webp" \) \
    -exec cp --parents {} "$SITE_DIR/" \;
fi

# Copy lwarp-generated TikZ/LaTeX image directory exactly where HTML expects it.
if [ -d "$IMAGE_DIR" ]; then
  cp -R "$IMAGE_DIR" "$SITE_DIR/"
else
  echo "ERROR: expected lwarp image directory '$IMAGE_DIR' was not created." | tee -a "$REPORT_FILE"
  exit 1
fi

# Copy build diagnostics into deployed site as a quick browser-accessible check.
mkdir -p "$SITE_DIR/$REPORT_DIR"
cp "$REPORT_FILE" "$SITE_DIR/$REPORT_FILE"

log "Validate deployed lwarp images in site directory"
python3 web/verify_lwarp_images.py \
  --image-dir "$SITE_DIR/$IMAGE_DIR" \
  --report "$SITE_DIR/$REPORT_DIR/lwarp-images-deployed-report.txt" \
  --require-images

log "Check generated HTML references are satisfiable"
python3 web/verify_lwarp_images.py \
  --image-dir "$SITE_DIR/$IMAGE_DIR" \
  --site-dir "$SITE_DIR" \
  --report "$SITE_DIR/$REPORT_DIR/lwarp-images-html-reference-report.txt" \
  --require-images \
  --check-html-refs

log "Final site file summary"
find "$SITE_DIR" -maxdepth 3 -type f | sort | sed 's#^#  #'

log "Build completed successfully"
