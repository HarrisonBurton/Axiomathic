#!/usr/bin/env python3
"""
Repair and verify lwarp-generated image assets.

Why this exists
---------------
lwarp sometimes emits SVG placeholders for TikZ/LaTeX image fragments. In the
failure mode we have seen, the HTML points to e.g.
Axiomathic_web-images/image-1.svg, the file exists, but the SVG is empty and
therefore the browser cannot render the diagram.

This script makes the image step deterministic:
  1. Inspect generated HTML and find references to <project>-images/*.svg/png.
  2. Validate referenced SVG files.
  3. For invalid/empty SVG files, look for a same-stem PDF produced by lwarp and
     convert that PDF to a PNG fallback using pdftocairo or pdftoppm.
  4. Patch HTML references from .svg to .png when a fallback is created.
  5. Write machine-readable and human-readable reports into site/build-reports.
  6. Fail loudly if any referenced image cannot be made usable.

The script deliberately does not silently pass empty images: a broken diagram is
worse than a failed build.
"""

from __future__ import annotations

import argparse
import html
import json
import os
import re
import shutil
import subprocess
import sys
import xml.etree.ElementTree as ET
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Iterable

VISIBLE_SVG_TAGS = {
    "circle",
    "ellipse",
    "image",
    "line",
    "path",
    "polygon",
    "polyline",
    "rect",
    "text",
    "use",
}


@dataclass
class ImageCheck:
    reference: str
    source_path: str
    status: str
    detail: str
    fallback_path: str | None = None


def strip_ns(tag: str) -> str:
    if "}" in tag:
        return tag.rsplit("}", 1)[1]
    return tag


def is_valid_nonempty_svg(path: Path) -> tuple[bool, str]:
    if not path.exists():
        return False, "missing file"
    if path.stat().st_size == 0:
        return False, "zero byte file"

    text = path.read_text(encoding="utf-8", errors="replace").strip()
    if not text:
        return False, "empty text file"
    if "<svg" not in text[:1000].lower():
        return False, "file does not begin like an SVG document"

    try:
        root = ET.fromstring(text)
    except ET.ParseError as exc:
        return False, f"XML parse error: {exc}"

    if strip_ns(root.tag).lower() != "svg":
        return False, f"root element is {strip_ns(root.tag)!r}, not 'svg'"

    # Browser-valid SVGs can be quite minimal, but lwarp TikZ output should
    # contain at least one visible primitive, text node, image, or <use>.
    visible_nodes = []
    for element in root.iter():
        tag = strip_ns(element.tag).lower()
        if tag in VISIBLE_SVG_TAGS:
            if tag == "text" and not "".join(element.itertext()).strip():
                continue
            visible_nodes.append(tag)

    if not visible_nodes:
        return False, "empty SVG file: no visible drawing/text elements found"

    # If width/height/viewBox are all absent, the browser may render nothing.
    has_dimensions = any(root.attrib.get(k) for k in ("width", "height", "viewBox"))
    if not has_dimensions:
        return False, "SVG has no width, height, or viewBox"

    return True, f"valid SVG with visible elements: {', '.join(sorted(set(visible_nodes)))[:120]}"


def run(cmd: list[str]) -> subprocess.CompletedProcess[str]:
    return subprocess.run(cmd, text=True, stdout=subprocess.PIPE, stderr=subprocess.STDOUT)


def convert_pdf_to_png(pdf_path: Path, png_path: Path, dpi: int) -> tuple[bool, str]:
    png_path.parent.mkdir(parents=True, exist_ok=True)

    if shutil.which("pdftocairo"):
        out_prefix = png_path.with_suffix("")
        proc = run(["pdftocairo", "-singlefile", "-png", "-r", str(dpi), str(pdf_path), str(out_prefix)])
        if proc.returncode == 0 and png_path.exists() and png_path.stat().st_size > 0:
            return True, "converted PDF to PNG using pdftocairo"
        return False, f"pdftocairo failed or produced no PNG:\n{proc.stdout[-3000:]}"

    if shutil.which("pdftoppm"):
        out_prefix = png_path.with_suffix("")
        proc = run(["pdftoppm", "-singlefile", "-png", "-r", str(dpi), str(pdf_path), str(out_prefix)])
        if proc.returncode == 0 and png_path.exists() and png_path.stat().st_size > 0:
            return True, "converted PDF to PNG using pdftoppm"
        return False, f"pdftoppm failed or produced no PNG:\n{proc.stdout[-3000:]}"

    return False, "neither pdftocairo nor pdftoppm is installed"


def html_files(root: Path) -> list[Path]:
    return sorted(p for p in root.glob("*.html") if p.is_file())


def find_image_references(html_paths: Iterable[Path], image_dir_name: str) -> dict[str, set[Path]]:
    # Capture quoted and unquoted references to the lwarp image directory.
    pattern = re.compile(rf"(?P<ref>{re.escape(image_dir_name)}/[^\"'<>\s)]+\.(?:svg|png|jpg|jpeg))", re.I)
    refs: dict[str, set[Path]] = {}
    for hp in html_paths:
        text = hp.read_text(encoding="utf-8", errors="replace")
        text = html.unescape(text)
        for match in pattern.finditer(text):
            ref = match.group("ref")
            refs.setdefault(ref, set()).add(hp)
    return refs


def patch_html_reference(html_paths: Iterable[Path], old_ref: str, new_ref: str) -> None:
    for hp in html_paths:
        text = hp.read_text(encoding="utf-8", errors="replace")
        if old_ref in text:
            text = text.replace(old_ref, new_ref)
            hp.write_text(text, encoding="utf-8")


def write_reports(report_dir: Path, checks: list[ImageCheck], html_refs: dict[str, set[Path]], project: str, image_dir: Path) -> None:
    report_dir.mkdir(parents=True, exist_ok=True)

    summary_lines = []
    summary_lines.append(f"lwarp image repair report for project: {project}")
    summary_lines.append(f"image directory: {image_dir}")
    summary_lines.append("")
    summary_lines.append("Referenced lwarp image assets:")
    if html_refs:
        for ref, sources in sorted(html_refs.items()):
            pages = ", ".join(sorted(p.name for p in sources))
            summary_lines.append(f"- {ref}  [referenced by: {pages}]")
    else:
        summary_lines.append("- none found")
    summary_lines.append("")
    summary_lines.append("Checks:")
    for check in checks:
        extra = f" -> fallback: {check.fallback_path}" if check.fallback_path else ""
        summary_lines.append(f"- {check.status}: {check.reference} :: {check.detail}{extra}")

    failures = [c for c in checks if c.status == "FAIL"]
    repaired = [c for c in checks if c.status == "REPAIRED"]
    ok = [c for c in checks if c.status == "OK"]
    summary_lines.append("")
    summary_lines.append(f"Totals: OK={len(ok)}, REPAIRED={len(repaired)}, FAIL={len(failures)}")
    summary_lines.append("RESULT: " + ("FAIL" if failures else "PASS"))

    (report_dir / "lwarp-images-deployed-report.txt").write_text("\n".join(summary_lines) + "\n", encoding="utf-8")
    (report_dir / "lwarp-images-html-reference-report.json").write_text(
        json.dumps(
            {
                "project": project,
                "image_dir": str(image_dir),
                "references": {k: sorted(p.name for p in v) for k, v in sorted(html_refs.items())},
                "checks": [asdict(c) for c in checks],
                "result": "FAIL" if failures else "PASS",
            },
            indent=2,
        )
        + "\n",
        encoding="utf-8",
    )


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--project", required=True, help="lwarp project name, e.g. Axiomathic_web")
    parser.add_argument("--root", default=".", help="build working directory containing generated HTML")
    parser.add_argument("--site", default="site", help="site output directory")
    parser.add_argument("--dpi", type=int, default=220, help="PNG fallback DPI")
    args = parser.parse_args()

    root = Path(args.root).resolve()
    site = Path(args.site).resolve()
    project = args.project
    image_dir_name = f"{project}-images"
    image_dir = root / image_dir_name
    report_dir = site / "build-reports"

    html_paths = html_files(root)
    html_refs = find_image_references(html_paths, image_dir_name)
    checks: list[ImageCheck] = []

    if html_refs and not image_dir.exists():
        for ref in sorted(html_refs):
            checks.append(ImageCheck(ref, str(root / ref), "FAIL", f"{image_dir_name}/ does not exist"))
        write_reports(report_dir, checks, html_refs, project, image_dir)
        print((report_dir / "lwarp-images-deployed-report.txt").read_text(encoding="utf-8"))
        return 1

    for ref in sorted(html_refs):
        src = root / ref
        suffix = src.suffix.lower()

        if suffix == ".svg":
            valid, detail = is_valid_nonempty_svg(src)
            if valid:
                checks.append(ImageCheck(ref, str(src), "OK", detail))
                continue

            pdf_candidate = src.with_suffix(".pdf")
            png_candidate = src.with_suffix(".png")
            if pdf_candidate.exists() and pdf_candidate.stat().st_size > 0:
                ok, convert_detail = convert_pdf_to_png(pdf_candidate, png_candidate, args.dpi)
                if ok:
                    new_ref = ref[:-4] + ".png"
                    patch_html_reference(html_paths, ref, new_ref)
                    checks.append(
                        ImageCheck(
                            ref,
                            str(src),
                            "REPAIRED",
                            f"{detail}; {convert_detail}; patched HTML to {new_ref}",
                            fallback_path=str(png_candidate),
                        )
                    )
                    continue
                checks.append(
                    ImageCheck(
                        ref,
                        str(src),
                        "FAIL",
                        f"{detail}; found {pdf_candidate.name} but conversion failed: {convert_detail}",
                    )
                )
                continue

            # Sometimes a PNG may already exist from a prior run even when the SVG is empty.
            if png_candidate.exists() and png_candidate.stat().st_size > 0:
                new_ref = ref[:-4] + ".png"
                patch_html_reference(html_paths, ref, new_ref)
                checks.append(
                    ImageCheck(
                        ref,
                        str(src),
                        "REPAIRED",
                        f"{detail}; used existing PNG fallback and patched HTML to {new_ref}",
                        fallback_path=str(png_candidate),
                    )
                )
                continue

            nearby = sorted(p.name for p in src.parent.glob(src.stem + ".*")) if src.parent.exists() else []
            checks.append(
                ImageCheck(
                    ref,
                    str(src),
                    "FAIL",
                    f"{detail}; no usable same-stem PDF or PNG fallback found; nearby files: {nearby}",
                )
            )

        else:
            if src.exists() and src.stat().st_size > 0:
                checks.append(ImageCheck(ref, str(src), "OK", f"{suffix} file exists and is non-empty"))
            else:
                checks.append(ImageCheck(ref, str(src), "FAIL", f"{suffix} file missing or empty"))

    # If the HTML did not reference any generated images, still report the directory contents.
    if not html_refs:
        checks.append(ImageCheck("<none>", str(image_dir), "OK", "no lwarp image references found in generated HTML"))

    # Ensure patched HTML is copied to site if the caller already copied old HTML too early.
    site.mkdir(parents=True, exist_ok=True)
    for hp in html_paths:
        shutil.copy2(hp, site / hp.name)

    # Copy the image directory after repairs/fallback creation.
    if image_dir.exists():
        dest = site / image_dir.name
        if dest.exists():
            shutil.rmtree(dest)
        shutil.copytree(image_dir, dest)

    write_reports(report_dir, checks, html_refs, project, image_dir)
    report_text = (report_dir / "lwarp-images-deployed-report.txt").read_text(encoding="utf-8")
    print(report_text)

    return 1 if any(c.status == "FAIL" for c in checks) else 0


if __name__ == "__main__":
    sys.exit(main())
