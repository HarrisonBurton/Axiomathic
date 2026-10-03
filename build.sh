#!/usr/bin/env bash
set -euo pipefail

PROJECT="Axiomathic"
WEBPROJECT="Axiomathic_web"

printf '\n== Axiomathic build ==\n'
printf 'PROJECT=%s\n' "$PROJECT"
printf 'WEBPROJECT=%s\n\n' "$WEBPROJECT"

# Start from a clean lwarp image state. Stale image-number mappings are a common
# source of wrong/empty SVGs after TikZ content changes.
rm -rf "${WEBPROJECT}-images" build-reports site
rm -f "${WEBPROJECT}-images.txt" "${WEBPROJECT}_html.pdf" "${WEBPROJECT}.tex"
mkdir -p build-reports

# Build the ordinary PDF if the source compiles in normal mode. This is useful as
# a control: if this fails, the issue is not lwarp/TikZ image extraction.
printf '\n== Build normal PDF ==\n'
pdflatex -interaction=nonstopmode -halt-on-error "${PROJECT}.tex"
pdflatex -interaction=nonstopmode -halt-on-error "${PROJECT}.tex"

# Build a temporary lwarp wrapper. The repository should keep Axiomathic.tex as
# the source of truth; the wrapper only defines the web flag and inputs it.
printf '\n== Create lwarp wrapper ==\n'
cat > "${WEBPROJECT}.tex" <<'TEX'
\def\AXIOMATHICWEB{}
\input{Axiomathic.tex}
TEX

# lwarp needs a PDF pass to write its config files, then HTML. Run html twice to
# stabilise internal image page references before rebuilding images.
printf '\n== Build lwarp HTML/PDF inputs ==\n'
pdflatex -interaction=nonstopmode -halt-on-error "${WEBPROJECT}.tex"
lwarpmk html -p "${WEBPROJECT}"
lwarpmk html -p "${WEBPROJECT}"

# Rebuild lwarp lateximage/TikZ images ourselves from the manifest and *_html.pdf.
# This deliberately does not depend on lwarpmk limages retaining any intermediate
# PDF. It keeps PDFs, creates SVGs, creates PNG fallbacks if SVG conversion is
# empty, and patches HTML references where needed.
printf '\n== Rebuild lwarp TikZ/lateximage assets ==\n'
python3 web/rebuild_lwarp_images.py --project "${WEBPROJECT}"

# Re-run HTML once more after image rebuilding/HTML patching, then patch again in
# case lwarpmk regenerated root HTML references to SVG.
printf '\n== Final lwarp HTML pass and image reference repair ==\n'
lwarpmk html -p "${WEBPROJECT}"
python3 web/rebuild_lwarp_images.py --project "${WEBPROJECT}"

# Generate navigation config before postprocess. If the generator is absent, use
# a minimal config so postprocess.py does not crash on a missing file.
printf '\n== Generate site config ==\n'
if [ -f web/generate-site-config.py ]; then
  python3 web/generate-site-config.py || {
    echo 'generate-site-config.py failed; writing minimal web/site-config.json'
    printf '{"sections": []}\n' > web/site-config.json
  }
elif [ -f web/build_site_config.py ]; then
  python3 web/build_site_config.py || {
    echo 'build_site_config.py failed; writing minimal web/site-config.json'
    printf '{"sections": []}\n' > web/site-config.json
  }
else
  echo 'No site-config generator found; writing minimal web/site-config.json'
  printf '{"sections": []}\n' > web/site-config.json
fi

printf '\n== Build combined site stylesheet ==\n'
if [ ! -s lwarp.css ]; then
  echo 'ERROR: lwarp.css is missing or empty. The generated HTML cannot be styled.' >&2
  exit 1
fi
if [ ! -s web/axiomathic.css ]; then
  echo 'ERROR: web/axiomathic.css is missing or empty.' >&2
  exit 1
fi
cat lwarp.css web/axiomathic.css > site.css
if [ ! -s site.css ]; then
  echo 'ERROR: combined site.css was not created correctly.' >&2
  exit 1
fi
printf 'Created site.css (%s bytes) from lwarp.css + web/axiomathic.css\n' "$(wc -c < site.css)"

printf '\n== Postprocess HTML ==\n'
if [ -f web/postprocess.py ]; then
  python3 web/postprocess.py
fi

printf '\n== Assemble site directory ==\n'
rm -rf site
mkdir -p site

# Root HTML produced by lwarp.
find . -maxdepth 1 -type f -name '*.html' -exec cp {} site/ \;

#Remove lwarp's internal HTML artefact.
rm -f "site/${WEBPROJECT}_html.html"

# CSS/JS/theme assets. site.css is the combined lwarp structural CSS +
# Axiomathic theme. postprocess.py ensures every page references it.
cp site.css site/
if [ -f web/theme.js ]; then cp web/theme.js site/; fi
if [ -f web/site-config.json ]; then mkdir -p site/web && cp web/site-config.json site/web/site-config.json; fi
if [ -d assets ]; then cp -r assets site/; fi
if [ -s "${PROJECT}.pdf" ]; then cp "${PROJECT}.pdf" site/; fi

# lwarp-generated image directory. This is the path used by HTML img src values.
if [ -d "${WEBPROJECT}-images" ]; then
  cp -r "${WEBPROJECT}-images" site/
fi

# User/article-owned images referenced by relative paths under sections/.
if [ -d sections ]; then
  find sections -type f \( -name '*.png' -o -name '*.jpg' -o -name '*.jpeg' -o -name '*.svg' -o -name '*.webp' \) \
    -exec cp --parents {} site/ \;
fi

# Build reports are deliberately deployed so they can be checked quickly in the
# browser after a successful build.
if [ -d build-reports ]; then
  cp -r build-reports site/
fi

touch site/.nojekyll

printf '\n== Verify deployed theme assets ==\n'
THEME_REPORT='build-reports/site-theme-report.txt'
{
  echo 'Axiomathic deployed-theme verification'
  echo '======================================'
  echo "site.css bytes: $(wc -c < site/site.css)"
  echo "theme.js bytes: $(wc -c < site/theme.js 2>/dev/null || echo 0)"
  echo
  failures=0
  for html in site/*.html; do
    [ -e "$html" ] || continue
    if grep -Fq 'href="site.css"' "$html"; then
      echo "PASS stylesheet reference: $html"
    else
      echo "FAIL stylesheet reference: $html"
      failures=$((failures + 1))
    fi
    if grep -Fq 'src="theme.js"' "$html"; then
      echo "PASS theme script reference: $html"
    else
      echo "FAIL theme script reference: $html"
      failures=$((failures + 1))
    fi
  done
  echo
  if [ "$failures" -eq 0 ]; then
    echo 'RESULT: PASS'
  else
    echo "RESULT: FAIL - $failures missing theme reference(s)"
  fi
} | tee "$THEME_REPORT"

if grep -q '^RESULT: FAIL' "$THEME_REPORT"; then
  echo 'ERROR: deployed HTML is missing required theme references.' >&2
  exit 1
fi

# Refresh the deployable report folder after the verification report exists.
rm -rf site/build-reports
cp -r build-reports site/

printf '\n== Final deployed image/report summary ==\n'
find site -maxdepth 4 -type f \( -path '*Axiomathic_web-images*' -o -path '*build-reports*' \) | sort

printf '\nBuild complete.\n'
