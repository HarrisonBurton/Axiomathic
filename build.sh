#!/usr/bin/env bash
set -euo pipefail
export TERM="${TERM:-xterm}"

PROJECT="Axiomathic"
WEBPROJECT="${PROJECT}_web"

# 1. Traditional PDF from the ordinary LaTeX source.
# This deliberately does not load lwarp.
pdflatex -interaction=nonstopmode -halt-on-error "${PROJECT}.tex"
if command -v bibtex >/dev/null 2>&1 && [[ -f "${PROJECT}.aux" ]]; then
  bibtex "$PROJECT" || true
fi
pdflatex -interaction=nonstopmode -halt-on-error "${PROJECT}.tex"
pdflatex -interaction=nonstopmode -halt-on-error "${PROJECT}.tex"

# 2. HTML build through a temporary web wrapper.  The wrapper defines
# AXIOMATHICWEB before inputting the normal master file, so lwarp is loaded for
# the web build but not for ordinary local PDF compilation.
cat > "${WEBPROJECT}.tex" <<'TEX'
\def\AXIOMATHICWEB{}
\input{Axiomathic.tex}
TEX

rm -f ./*.html
# Prime lwarp: the first LaTeX pass writes the .lwarpmkconf file that lwarpmk needs.
pdflatex -interaction=nonstopmode -halt-on-error "${WEBPROJECT}.tex"
lwarpmk html -p "$WEBPROJECT"


# Render any TikZ/LaTeX image fragments requested by lwarp.
rm -rf "${WEBPROJECT}-images" lateximages
lwarpmk limages -p "$WEBPROJECT"

#Rebuild html now image files exist
lwarpmk html -p "$WEBPROJECT"

# If BibTeX is available, build the HTML bibliography too.
if command -v bibtex >/dev/null 2>&1 && [[ -f "${WEBPROJECT}_html.aux" ]]; then
  bibtex "${WEBPROJECT}_html" || true
  lwarpmk again -p "$WEBPROJECT"
  lwarpmk html -p "$WEBPROJECT"
fi

#Rebuild html again
lwarpmk html -p "$WEBPROJECT"
# 3. Rebuild website navigation from the LaTeX source-folder structure.
python3 web/generate-site-config.py

# 4. Layer the reusable Axiomathic theme on top of lwarp's structural CSS.
cat lwarp.css web/axiomathic.css > site.css
python3 web/postprocess.py

# 5. Gather only deployable static files.
rm -rf site
mkdir -p site
for f in *.html; do
  case "$f" in
    *_html.html) ;;
    *) cp "$f" site/ ;;
  esac
done
cp site.css web/theme.js "${PROJECT}.pdf" site/

# Copy lwarp-generated TikZ/LaTeX image assets into the deployed site.
find . -maxdepth 3 \( -name "*.svg" -o -name "*.png" -o -name "*.jpg" -o -name "*.jpeg" \) \
! -path "./site/*" \
! -path "./assets/*" \
-exec cp --parents {} site/ \;

# Conventional asset folders are copied verbatim when present.
for d in assets figures images media; do
  if [[ -d "$d" ]]; then
    cp -R "$d" site/
  fi
done
if [[ -d lateximages ]]; then
  cp -R lateximages site/
fi

# Article-specific media may live beside a subfile. Copy only media folders,
# preserving their paths, rather than publishing the LaTeX sources themselves.
if [[ -d sections ]]; then
  while IFS= read -r -d '' f; do
    mkdir -p "site/$(dirname "$f")"
    cp "$f" "site/$f"
  done < <(find sections -type f \( -path '*/images/*' -o -path '*/figures/*' -o -path '*/media/*' \) -print0)
fi

touch site/.nojekyll

# Remove the generated wrapper source; auxiliary files are ignored/cleanable.
rm -f "${WEBPROJECT}.tex"

echo "Built site/index.html and ${PROJECT}.pdf"
