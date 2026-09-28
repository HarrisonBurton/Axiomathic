# Image import guide

Article-specific images should live beside the article that uses them, normally in an `images/` folder.

Examples:

```text
sections/style/images/                 # images used by the theorem/style test page
sections/summary-notes/my-note/images/  # images used by one summary note
sections/projects/my-project/images/    # images used by one project
```

The top-level `assets/` folder is reserved for website-wide assets such as the Axiomathic logo.

Use repository-relative graphic paths via `subfiles`, for example:

```latex
\graphicspath{{\subfix{images/}}}
```

Then include ordinary LaTeX figures:

```latex
\begin{figure}[htbp]
  \centering
  \includegraphics[width=0.8\textwidth]{example.jpg}
  \caption{Example figure.}
\end{figure}
```
