# TikZ / lwarp image debugging

lwarp does not render TikZ through MathJax. TikZ pictures become image files referenced from the generated HTML.

For this repository the expected path is usually:

```text
Axiomathic_web-images/image-1.svg
```

or, after v6.3's PNG fallback conversion:

```text
Axiomathic_web-images/image-1.png
```

## If a TikZ image is broken

Check the GitHub Actions log under **Build PDF and website**.

### 1. Was the image generated?

Look for:

```text
==> Generated lwarp image files
```

You should see something like:

```text
Axiomathic_web-images/image-1.svg
```

If nothing appears here, the issue is TikZ/lwarp image generation.

### 2. Was a PNG fallback created?

Look for:

```text
==> Converting generated SVGs to PNG fallback images when rsvg-convert is available
```

On GitHub Actions, `rsvg-convert` should be available via `librsvg2-bin`.

### 3. Was the image copied into the deployed site?

Look for:

```text
==> Files in deployed site relevant to lwarp images
```

You should see:

```text
site/Axiomathic_web-images/image-1.png
```

or at least:

```text
site/Axiomathic_web-images/image-1.svg
```

### 4. Does the HTML point to the same path?

Use browser developer tools to inspect the broken `<img>` and compare its `src` to the deployed file path above.

If the HTML says:

```text
Axiomathic_web-images/image-1.png
```

then the deployed site must contain:

```text
site/Axiomathic_web-images/image-1.png
```

## Why PNG fallback exists

SVG should normally be preferable for diagrams, but lwarp-generated SVGs can be served or interpreted inconsistently across environments. PNG fallback is less elegant but more robust for GitHub Pages.
