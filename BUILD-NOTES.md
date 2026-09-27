# Build notes

## Current source audit

The master document is `Axiomathic.tex`. It inputs `preamble.tex`, then includes the two current chapter subfiles:

- `sections/Shuffling Cards.tex`
- `sections/Easier Waring_part 1.tex`

The web build compiles the master document, not the chapter files individually. This is deliberate: chapter numbering, the contents tree, cross-references and bibliography all stay global. The chapter files remain independently compilable through the `subfiles` package.

## Web additions to preamble.tex

The web-specific block added near the top of the shared preamble is:

```tex
\makeatletter
\@ifclassloaded{subfiles}{}{%%
  \usepackage[mathjax,HomeHTMLFilename=index]{lwarp}
  \setcounter{FileDepth}{0}
  \setcounter{SideTOCDepth}{1}
  \CSSFilename{site.css}
  \providecommand{\cs}[1]{\texttt{\textbackslash#1}}
}
\makeatother
```

The small class check matters: lwarp is loaded for the master `book` build, but deliberately skipped when a `subfiles` chapter is compiled standalone. That preserves the convenient standalone-PDF workflow. `FileDepth=0` means a `book` document gets one HTML file per `\chapter`. `SideTOCDepth=1` allows the left rail to contain chapters and sections. All modern visual styling is in `web/axiomathic.css` and `web/theme.js` rather than in the mathematical source.

I also removed redundant package/macro declarations from the two chapter preambles, because those dependencies already live in the shared `preamble.tex`. The mathematical prose, equations, labels and chapter structure are unchanged. In `Shuffling Cards.tex`, the chapter-specific title page is now wrapped so it appears only when that subfile is compiled on its own, not inside the master book/site.

## Bibliography gap to fix

`sections/Easier Waring_part 1.tex` currently cites these six keys:

- `Wright1934`
- `FuchsWright1939`
- `Borwein2002`
- `Vavilov2022`
- `Revoy1991`
- `BukhMO`

None of those keys is currently present in the uploaded `biblio.bib`. The build therefore succeeds, but those citations will remain unresolved until the entries are added. I have intentionally **not invented or silently replaced bibliography entries**.

## Future images and TikZ

For ordinary images, put files under `assets/`, `figures/` or `images/`; the build copies those directories into the deployed site. TikZ can stay in the LaTeX. `lwarpmk limages` is included in the build so lwarp can generate web images when required.
