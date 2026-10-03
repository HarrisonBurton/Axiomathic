#!/usr/bin/env python3
"""
Rebuild lwarp lateximage/TikZ SVGs from lwarp's own image manifest.

Why this exists
---------------
lwarpmk limages creates <PROJECT>-images/image-N.svg by extracting one page from
<PROJECT>_html.pdf, cropping it, converting it to SVG, and then deleting the
intermediate PDF. If the SVG is empty, there is no remaining same-stem PDF to use
as a fallback.

This script reproduces the lwarp image pipeline directly, but keeps diagnostics
and creates PNG fallbacks when SVG output is invalid. It is intended for CI where
we need a deterministic pass/fail and an inspectable report.

Inputs expected in the repository root after lwarpmk html:
  - <PROJECT>-images.txt
  - <PROJECT>_html.pdf

Outputs:
  - <PROJECT>-images/image-N.svg where valid
  - <PROJECT>-images/image-N.pdf retained for diagnostics/fallback conversion
  - <PROJECT>-images/image-N.png where SVG is invalid but PDF can be rasterised
  - build-reports/lwarp-images-rebuild-report.txt
  - build-reports/lwarp-images-html-reference-report.txt

Exit code:
  0 if every image has either a valid SVG or a PNG fallback and HTML references
    can be patched accordingly.
  1 otherwise.
"""

from __future__ import annotations

import argparse
import html
import os
from pathlib import Path
import re
import shutil
import subprocess
import sys
from typing import Iterable, List, Tuple


def run(cmd: List[str], report: List[str]) -> subprocess.CompletedProcess[str]:
    report.append("$ " + " ".join(cmd))
    proc = subprocess.run(cmd, text=True, stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
    if proc.stdout:
        report.append(proc.stdout.rstrip())
    report.append(f"exit={proc.returncode}")
    return proc


def svg_has_visible_content(path: Path) -> Tuple[bool, str]:
    if not path.exists():
        return False, "missing"
    try:
        text = path.read_text(encoding="utf-8", errors="replace")
    except Exception as exc:
        return False, f"unreadable: {exc}"
    if not text.strip():
        return False, "empty file"
    lower = text.lower()
    if "<svg" not in lower:
        return False, "not an SVG document"
    # Exclude wrapper-only SVGs with no visible drawing primitives or image/text content.
    visible_markers = ["<path", "<use", "<g", "<line", "<polyline", "<polygon", "<rect", "<circle", "<ellipse", "<text", "<image"]
    if not any(marker in lower for marker in visible_markers):
        return False, "empty SVG: no visible drawing markers"
    # A <g> alone can still be empty, so also require some size beyond a tiny wrapper.
    if path.stat().st_size < 200:
        return False, f"suspiciously small SVG ({path.stat().st_size} bytes)"
    return True, "valid SVG"


def png_ok(path: Path) -> Tuple[bool, str]:
    if not path.exists():
        return False, "missing"
    if path.stat().st_size < 1000:
        return False, f"too small ({path.stat().st_size} bytes)"
    return True, "valid PNG fallback"


def parse_manifest(manifest: Path) -> List[Tuple[int, str, str]]:
    entries: List[Tuple[int, str, str]] = []
    for raw in manifest.read_text(encoding="utf-8", errors="replace").splitlines():
        raw = raw.strip()
        if not raw or raw == "|end|end|end|":
            continue
        m = re.fullmatch(r"\|(.*?)\|(.*?)\|(.*?)\|", raw)
        if not m:
            continue
        page_s, hashed, name = m.groups()
        if page_s == "0" or page_s == "end":
            continue
        try:
            page = int(page_s)
        except ValueError:
            continue
        if name:
            entries.append((page, hashed, name))
    return entries


def patch_html(project: str, replacements: dict[str, str], report: List[str]) -> None:
    if not replacements:
        return
    html_files = sorted(Path(".").glob("*.html"))
    for html_file in html_files:
        text = html_file.read_text(encoding="utf-8", errors="replace")
        original = text
        for old, new in replacements.items():
            text = text.replace(old, new)
            text = text.replace(html.escape(old), html.escape(new))
        if text != original:
            html_file.write_text(text, encoding="utf-8")
            report.append(f"patched HTML references in {html_file}")


def write_html_reference_report(project: str, report_dir: Path) -> None:
    images_dir = Path(f"{project}-images")
    lines: List[str] = []
    lines.append("Lwarp image HTML reference check")
    lines.append("=================================")
    lines.append("")
    pattern = re.compile(re.escape(f"{project}-images/") + r"[^\"'<> )]+")
    refs: set[str] = set()
    for html_file in sorted(Path(".").glob("*.html")):
        text = html_file.read_text(encoding="utf-8", errors="replace")
        for match in pattern.findall(text):
            refs.add(match)
            target = Path(match)
            status = "OK" if target.exists() and target.stat().st_size > 0 else "MISSING_OR_EMPTY"
            lines.append(f"{html_file}: {match} -> {status}")
    if not refs:
        lines.append("No lwarp image references found in root HTML files.")
    report_dir.mkdir(parents=True, exist_ok=True)
    (report_dir / "lwarp-images-html-reference-report.txt").write_text("\n".join(lines) + "\n", encoding="utf-8")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--project", default="Axiomathic_web")
    parser.add_argument("--dpi", default="192")
    parser.add_argument("--strict", action="store_true", help="Fail if PNG fallback is needed. By default PNG fallback is accepted.")
    args = parser.parse_args()

    project = args.project
    images_dir = Path(f"{project}-images")
    manifest = Path(f"{project}-images.txt")
    html_pdf = Path(f"{project}_html.pdf")
    report_dir = Path("build-reports")
    report_dir.mkdir(parents=True, exist_ok=True)
    report: List[str] = []
    replacements: dict[str, str] = {}
    failures: List[str] = []

    report.append("Lwarp image rebuild report")
    report.append("==========================")
    report.append(f"project={project}")
    report.append(f"manifest={manifest}")
    report.append(f"html_pdf={html_pdf}")
    report.append("")

    for tool in ["pdfseparate", "pdfcrop", "pdftocairo"]:
        path = shutil.which(tool)
        report.append(f"tool {tool}: {path or 'MISSING'}")
        if path is None:
            failures.append(f"Required tool missing: {tool}")
    report.append("")

    if not manifest.exists():
        failures.append(f"Missing lwarp image manifest: {manifest}")
    if not html_pdf.exists():
        failures.append(f"Missing lwarp HTML PDF: {html_pdf}")

    if failures:
        report.append("RESULT: FAIL")
        report.extend("- " + f for f in failures)
        (report_dir / "lwarp-images-rebuild-report.txt").write_text("\n".join(report) + "\n", encoding="utf-8")
        return 1

    entries = parse_manifest(manifest)
    report.append(f"manifest entries={len(entries)}")
    if not entries:
        report.append("No lwarp image entries found. This is OK if the document has no TikZ/lateximage output.")
        report.append("RESULT: PASS")
        (report_dir / "lwarp-images-rebuild-report.txt").write_text("\n".join(report) + "\n", encoding="utf-8")
        write_html_reference_report(project, report_dir)
        return 0

    images_dir.mkdir(exist_ok=True)

    for page, hashed, name in entries:
        report.append("")
        report.append(f"image {name}: page={page} hashed={hashed}")
        temp_pdf = images_dir / f"lateximagetemp-{page}.pdf"
        cropped_pdf = images_dir / f"{name}.pdf"
        svg = images_dir / f"{name}.svg"
        png = images_dir / f"{name}.png"

        # Always regenerate non-hashed image files; hashed inline math can be reused if valid.
        existing_ok, existing_reason = svg_has_visible_content(svg)
        if hashed == "true" and existing_ok:
            report.append(f"reuse existing hashed SVG: {svg} ({existing_reason})")
            continue

        # Step 1: extract the relevant PDF page.
        for p in [temp_pdf, cropped_pdf, svg, png]:
            if p.exists():
                try:
                    p.unlink()
                except Exception:
                    pass

        proc = run(["pdfseparate", "-f", str(page), "-l", str(page), str(html_pdf), str(temp_pdf)], report)
        if proc.returncode != 0 or not temp_pdf.exists() or temp_pdf.stat().st_size == 0:
            failures.append(f"{name}: pdfseparate failed or produced no temp PDF for page {page}")
            continue

        # Step 2: crop it to the image bounding box. If crop fails, keep trying with the raw page.
        proc = run(["pdfcrop", "--hires", "--margins", "0 1 0 0", str(temp_pdf), str(cropped_pdf)], report)
        if proc.returncode != 0 or not cropped_pdf.exists() or cropped_pdf.stat().st_size == 0:
            report.append(f"pdfcrop failed for {name}; using uncropped temp PDF as fallback source")
            shutil.copyfile(temp_pdf, cropped_pdf)

        # Step 3: create SVG.
        proc = run(["pdftocairo", "-svg", "-noshrink", str(cropped_pdf), str(svg)], report)
        ok_svg, reason_svg = svg_has_visible_content(svg)
        report.append(f"SVG check: {svg} -> {reason_svg}")

        if ok_svg:
            report.append(f"image {name}: PASS via SVG")
            continue

        # Step 4: create PNG fallback and patch root HTML to use it.
        proc = run(["pdftocairo", "-png", "-singlefile", "-r", str(args.dpi), str(cropped_pdf), str(images_dir / name)], report)
        ok_png, reason_png = png_ok(png)
        report.append(f"PNG check: {png} -> {reason_png}")
        if ok_png:
            replacements[f"{project}-images/{name}.svg"] = f"{project}-images/{name}.png"
            if args.strict:
                failures.append(f"{name}: SVG invalid ({reason_svg}); PNG fallback produced but strict mode enabled")
            else:
                report.append(f"image {name}: PASS via PNG fallback")
        else:
            failures.append(f"{name}: SVG invalid ({reason_svg}) and PNG fallback invalid ({reason_png})")

    patch_html(project, replacements, report)
    write_html_reference_report(project, report_dir)

    # Summarise actual generated files for quick inspection.
    report.append("")
    report.append("Generated files:")
    for p in sorted(images_dir.glob("*")):
        if p.is_file():
            report.append(f"- {p} ({p.stat().st_size} bytes)")

    if failures:
        report.append("")
        report.append("RESULT: FAIL")
        report.extend("- " + f for f in failures)
        (report_dir / "lwarp-images-rebuild-report.txt").write_text("\n".join(report) + "\n", encoding="utf-8")
        return 1

    report.append("")
    report.append("RESULT: PASS")
    if replacements:
        report.append("HTML was patched to use PNG fallback for:")
        for old, new in replacements.items():
            report.append(f"- {old} -> {new}")
    (report_dir / "lwarp-images-rebuild-report.txt").write_text("\n".join(report) + "\n", encoding="utf-8")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
