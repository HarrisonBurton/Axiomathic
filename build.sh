#!/usr/bin/env bash
set -euo pipefail
export TERM="${TERM:-xterm}"

# ------------------------------------------------------------
# Axiomathic GitHub Pages build with robust lwarp image checks
# ------------------------------------------------------------
# The normal LaTeX source remains the source of truth.
MAINPROJECT="Axiomathic"

# Temporary lwarp wrapper used only for the web build.
WEBPROJECT="Axiomathic_web"

# Folder uploaded to GitHub Pages.
SITE_DIR="site"

# Start clean enough to avoid stale lwarp outputs, but do not delete source files.
rm -rf "${SITE_DIR}" "${WEBPROJECT}-images"
mkdir -p "${SITE_DIR}"

# ------------------------------------------------------------
# 1. Build the ordinary PDF first.
# ------------------------------------------------------------
pdflatex -interaction=nonstopmode -halt-on-error "${MAINPROJECT}.tex"
if command -v bibtex >/dev/null 2>&1 && [[ -f "${MAINPROJECT}.aux" ]]; then
  bibtex "${MAINPROJECT}" || true
fi
pdflatex -interaction=nonstopmode -halt-on-error "${MAINPROJECT}.tex"
pdflatex -interaction=nonstopmode -halt-on-error "${MAINPROJECT}.tex"

# ------------------------------------------------------------
# 2. Build the lwarp web wrapper.
# ------------------------------------------------------------
cat > "${WEBPROJECT}.tex" <<'TEX'
\def\AXIOMATHICWEB{}
\input{Axiomathic.tex}
TEX

# Remove stale HTML before the web build, because stale pages can hide errors.
rm -f ./*.html

# Prime lwarp.
pdflatex -interaction=nonstopmode -halt-on-error "${WEBPROJECT}.tex"

# First HTML pass creates HTML and discovers image fragments.
lwarpmk html -p "${WEBPROJECT}"

# Build web bibliography if lwarp created an aux file for it.
if command -v bibtex >/dev/null 2>&1 && [[ -f "${WEBPROJECT}_html.aux" ]]; then
  bibtex "${WEBPROJECT}_html" || true
  lwarpmk again -p "${WEBPROJECT}"
  lwarpmk html -p "${WEBPROJECT}"
fi

# Generate lwarp TikZ/LaTeX image assets. Do not hide failures here.
lwarpmk limages -p "${WEBPROJECT}"

echo "Generated lwarp image files before repair:"
find "${WEBPROJECT}-images" -maxdepth 2 -type f -print 2>/dev/null | sort || true

# Rebuild HTML after image generation so references are current.
lwarpmk html -p "${WEBPROJECT}"

# ------------------------------------------------------------
# 3. Rebuild the Axiomathic navigation config before postprocess.py.
# ------------------------------------------------------------
# postprocess.py expects web/site-config.json.  Earlier fix packages called
# postprocess before generating this file, which caused:
#   FileNotFoundError: web/site-config.json
if [[ -f "web/generate-site-config.py" ]]; then
  if python3 web/generate-site-config.py; then
    echo "Generated web/site-config.json using web/generate-site-config.py"
  else
    echo "WARNING: web/generate-site-config.py failed; writing minimal fallback config."
  fi
fi

if [[ ! -f "web/site-config.json" ]]; then
  cat > web/site-config.json <<'JSON'
{
  "siteTitle": "Axiomathic",
  "tagline": "",
  "intro": "",
  "sections": [],
  "utilityPages": [],
  "about": ""
}
JSON
  echo "Wrote minimal fallback web/site-config.json"
fi

# ------------------------------------------------------------
# 4. Apply Axiomathic theme and post-processing.
# ------------------------------------------------------------
if [[ -f "lwarp.css" && -f "web/axiomathic.css" ]]; then
  cat lwarp.css web/axiomathic.css > site.css
elif [[ -f "web/axiomathic.css" ]]; then
  cp web/axiomathic.css site.css
elif [[ -f "lwarp.css" ]]; then
  cp lwarp.css site.css
fi

if [[ -f "web/postprocess.py" ]]; then
  python3 web/postprocess.py
fi

# ------------------------------------------------------------
# 5. Gather deployable static files.
# ------------------------------------------------------------
rm -rf "${SITE_DIR}"
mkdir -p "${SITE_DIR}"

# Copy generated article pages, but avoid lwarp intermediate *_html.html files.
for f in *.html; do
  [[ -e "$f" ]] || continue
  case "$f" in
    *_html.html) ;;
    *) cp "$f" "${SITE_DIR}/" ;;
  esac
done

[[ -f site.css ]] && cp site.css "${SITE_DIR}/"
[[ -f "${MAINPROJECT}.pdf" ]] && cp "${MAINPROJECT}.pdf" "${SITE_DIR}/"
[[ -f "web/theme.js" ]] && cp "web/theme.js" "${SITE_DIR}/"
[[ -f "web/site-config.json" ]] && cp "web/site-config.json" "${SITE_DIR}/site-config.json"

# Conventional static asset folders.
for d in assets figures images media; do
  if [[ -d "$d" ]]; then
    cp -R "$d" "${SITE_DIR}/"
  fi
done

# Article-specific media may live beside subfiles. Preserve paths expected by HTML.
if [[ -d sections ]]; then
  while IFS= read -r -d '' f; do
    mkdir -p "${SITE_DIR}/$(dirname "$f")"
    cp "$f" "${SITE_DIR}/$f"
  done < <(find sections -type f \( -path '*/images/*' -o -path '*/figures/*' -o -path '*/media/*' \) -print0)
fi

# ------------------------------------------------------------
# 6. Repair and verify lwarp-generated image assets.
# ------------------------------------------------------------
# This patches empty SVG references to PNG fallbacks where possible, copies the
# final image directory into site/, and writes browser-readable reports under
# site/build-reports/.
python3 web/repair_lwarp_images.py --project "${WEBPROJECT}" --root "." --site "${SITE_DIR}" --dpi 220

touch "${SITE_DIR}/.nojekyll"

echo "Final deployed lwarp image files:"
find "${SITE_DIR}/${WEBPROJECT}-images" -maxdepth 2 -type f -print 2>/dev/null | sort || true

echo "Build reports:"
find "${SITE_DIR}/build-reports" -type f -print 2>/dev/null | sort || true

echo "Built ${SITE_DIR}/index.html and ${MAINPROJECT}.pdf"
