# Axiomathic

A single-source mathematical publishing setup: write in LaTeX, then generate both a traditional PDF and a modern static website.

## Repository layout

```text
Axiomathic.tex          master book
preamble.tex            shared LaTeX + lwarp web settings
biblio.bib              shared bibliography
sections/               chapter subfiles
web/axiomathic.css      reusable site theme
web/theme.js            header, rails, search, dark mode
web/postprocess.py      injects the theme JS into generated HTML
build.sh                one-command PDF + HTML build
.github/workflows/      automatic GitHub Pages deployment
```

## Local build

On a machine with TeX Live, lwarp, BibTeX and Python 3:

```bash
./build.sh
```

Open `site/index.html`. The same build also creates `Axiomathic.pdf` and copies it into the site.

## How publishing works

1. Edit normal LaTeX files.
2. Commit and push to the `main` branch.
3. GitHub Actions installs TeX Live, compiles the PDF, converts the book to HTML, applies the Axiomathic theme and deploys `site/` to GitHub Pages.
4. Each `\chapter` becomes its own page. Sections populate the navigation automatically.

See `GITHUB-LAUNCH.md` for a first-time setup from a completely new GitHub account.
