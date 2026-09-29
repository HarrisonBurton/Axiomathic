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


## Axiomathic v2 refinements

The web layer now uses a smaller typographic scale, an all-white alpha/arrow wordmark, a purpose-built landing page, MathJax definitions for the custom Axiomathic maths commands, and an explicit theorem colour system. `sections/Theorem Style Guide.tex` is a disposable visual test fixture for reviewing all theorem environments in one page.


## Everyday website edits

Most site-level changes now live in `web/site-config.json`.

### Change the homepage tagline

Edit:

```json
"tagline": "Mathematics, carefully written."
```

No LaTeX change is required.

### Move a page between website sections

Website categorisation is intentionally independent of the LaTeX book structure.
For example, to move `Shuffling Cards` from **Summary Notes** to **Projects**,
move its page object in `web/site-config.json` from the `notes.pages` array to
the `projects.pages` array.

You do **not** need to move the `.tex` file on disk.

If you physically move a `.tex` file to another folder, update the corresponding
`\subfile{...}` path in `Axiomathic.tex`; that affects LaTeX compilation, not
the website category.

### Add a new page

1. Add its `\subfile{...}` line to `Axiomathic.tex`.
2. Add a page entry to the appropriate `pages` array in `web/site-config.json`.
3. Commit and push. GitHub Actions rebuilds the site.


## Automatic website categorisation (v4)

The website page lists are now rebuilt on every build. You do **not** manually add
individual pages to `web/site-config.json`.

Place source files under:

```text
sections/
  summary-notes/   -> Summary Notes
  projects/        -> Projects
  style/           -> utility/style pages
```

Then add the corresponding `\\subfile{...}` line to `Axiomathic.tex`.
`web/generate-site-config.py` scans the ordered `\\subfile` entries and the folder
name, reads the first `\\chapter{...}` as the web title, and generates
`web/site-config.json` automatically during `build.sh`.

For example:

```text
sections/projects/Sums of 4 cubes.tex
```

plus

```latex
\\subfile{sections/projects/Sums of 4 cubes}
```

is enough for **Sums of 4 Cubes** to appear automatically under **Projects** on
the next GitHub Actions build.

Site-wide wording such as the homepage tagline remains in
`web/site-config.base.json`.

## v5 web-publication behaviour

### Page-local numbering

The combined PDF keeps the normal master-book chapter numbering. During HTML
post-processing, each standalone webpage remaps its leading chapter component
to `1`. For example, a master section numbered `3.1` is displayed online as
`1.1`, and theorem `3.4` is displayed as `1.4`. The LaTeX counters themselves
are not changed.

### Print geometry

The shared `preamble.tex` only loads `geometry`; it no longer fixes A5 paper
size for every Axiomathic document. Print-specific geometry belongs in a
separate print master. A starter is provided at
`print/PlayingCardsBook.template.tex`.

### Article images

Keep site branding in `assets/`. Keep article-specific images beside the
article, conventionally in an `images/` folder. The deployment build copies
nested `images/`, `figures/`, and `media/` folders without publishing `.tex`
sources.

For the future Playing Cards note, use:

```text
sections/summary-notes/playing-cards/
  Playing Cards.tex
  images/
```

See `IMAGE-IMPORT-GUIDE.md` for what to upload next.


## v6 note

Axiomathic v6 removes the experimental Playing Cards page. Image-heavy rendering is now tested in the Theorem Style Guide instead.
