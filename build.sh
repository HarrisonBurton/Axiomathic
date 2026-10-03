#!/usr/bin/env bash
set -euo pipefail

# ------------------------------------------------------------
# Axiomathic GitHub Pages build
# ------------------------------------------------------------
# Main local/PDF source file.
MAINPROJECT="Axiomathic"

# Temporary lwarp wrapper used only in CI/web builds.
WEBPROJECT="Axiomathic_web"

# Output folder uploaded by GitHub Pages.
SITE_DIR="site"

# Keep a clean deploy folder.
rm -rf "${SITE_DIR}"
mkdir -p "${SITE_DIR}"

# Build a normal PDF first. This is useful because it catches ordinary LaTeX
# errors before the web conversion step.
pdflatex -interaction=nonstopmode -halt-on-error "${MAINPROJECT}.tex"
bibtex "${MAINPROJECT}" || true
pdflatex -interaction=nonstopmode -halt-on-error "${MAINPROJECT}.tex"
pdflatex -interaction=nonstopmode -halt-on-error "${MAINPROJECT}.tex"
cp "${MAINPROJECT}.pdf" "${SITE_DIR}/" || true

# Create the web wrapper. The main document/preamble should use
# \ifdefined\AXIOMATHICWEB to load lwarp-only configuration.
cat > "${WEBPROJECT}.tex" <<'TEX'
\def\AXIOMATHICWEB{}
\input{Axiomathic.tex}
TEX

# Prime lwarp.
pdflatex -interaction=nonstopmode -halt-on-error "${WEBPROJECT}.tex"

# First HTML pass creates HTML and discovers image fragments.
lwarpmk html -p "${WEBPROJECT}"

# Generate lwarp image assets. Do not hide failures here.
lwarpmk limages -p "${WEBPROJECT}"

echo "Generated lwarp image files before repair:"
find "${WEBPROJECT}-images" -maxdepth 2 -type f -print 2>/dev/null | sort || true

# Rebuild HTML after lwarp image generation.
lwarpmk html -p "${WEBPROJECT}"

# Run existing site postprocessor if present.
if [ -f "web/postprocess.py" ]; then
  python3 web/postprocess.py
fi

# Copy core site assets. The repair script below will recopy patched HTML and
# generated image assets into the site folder, so it is safe if this initial
# copy happens before repair.
cp ./*.html "${SITE_DIR}/" 2>/dev/null || true
cp ./*.css "${SITE_DIR}/" 2>/dev/null || true

if [ -f "site.css" ]; then
  cp "site.css" "${SITE_DIR}/"
fi

if [ -d "web" ]; then
  find web -maxdepth 1 -type f \( -name "*.css" -o -name "*.js" -o -name "*.json" \) -exec cp {} "${SITE_DIR}/" \;
fi

if [ -d "assets" ]; then
  cp -r assets "${SITE_DIR}/"
fi

# Copy article-owned static images, preserving paths expected by HTML.
if [ -d "sections" ]; then
  find sections -type f \( -name "*.png" -o -name "*.jpg" -o -name "*.jpeg" -o -name "*.svg" -o -name "*.webp" \) \
    -exec cp --parents {} "${SITE_DIR}/" \;
fi

# Repair/verify lwarp-generated image assets. This handles the known failure
# mode where lwarp emits empty SVG files by converting same-stem PDFs to PNGs
# and patching the generated HTML to point at the PNG fallback.
python3 web/repair_lwarp_images.py --project "${WEBPROJECT}" --root "." --site "${SITE_DIR}" --dpi 220

echo "Final deployed lwarp image files:"
find "${SITE_DIR}/${WEBPROJECT}-images" -maxdepth 2 -type f -print 2>/dev/null | sort || true

echo "Build reports:"
find "${SITE_DIR}/build-reports" -type f -print 2>/dev/null | sort || true
