#!/usr/bin/env python3
"""Validate lwarp-generated image assets for Axiomathic.

The failure mode we want to catch is subtle: lwarp may emit an .svg file that
exists, but is empty, contains an XML/HTML error page, or is not copied to the
path referenced by the generated HTML. This script makes those failures explicit
in GitHub Actions and writes a small report that can be deployed with the site.
"""

from __future__ import annotations

import argparse
import re
import sys
from dataclasses import dataclass
from pathlib import Path
import xml.etree.ElementTree as ET


@dataclass
class ImageStatus:
    path: Path
    ok: bool
    reason: str
    size: int


def is_valid_svg(path: Path) -> tuple[bool, str]:
    try:
        text = path.read_text(encoding="utf-8", errors="replace").strip()
    except Exception as exc:  # pragma: no cover - diagnostic path
        return False, f"could not read SVG: {exc}"

    if not text:
        return False, "empty SVG file"

    # A common bad case is an XML stylesheet warning/error or an HTML/XML page
    # saved with .svg extension. Valid SVG can start with XML declaration,
    # comments, doctype, then <svg>. Parse and check the root element.
    try:
        root = ET.fromstring(text)
    except ET.ParseError as exc:
        return False, f"not parseable XML/SVG: {exc}"

    tag = root.tag.lower()
    if tag.endswith("svg"):
        # Guard against a blank but syntactically valid SVG.
        if len(text) < 120:
            return False, "SVG is suspiciously small"
        return True, "valid SVG"

    return False, f"XML root is not <svg>: {root.tag}"


def is_valid_raster(path: Path) -> tuple[bool, str]:
    size = path.stat().st_size
    if size == 0:
        return False, "empty raster image file"
    suffix = path.suffix.lower()
    try:
        data = path.read_bytes()[:16]
    except Exception as exc:  # pragma: no cover
        return False, f"could not read raster header: {exc}"

    signatures = {
        ".png": b"\x89PNG\r\n\x1a\n",
        ".jpg": b"\xff\xd8\xff",
        ".jpeg": b"\xff\xd8\xff",
        ".webp": b"RIFF",
        ".pdf": b"%PDF-",
    }
    expected = signatures.get(suffix)
    if expected and not data.startswith(expected):
        return False, f"unexpected {suffix} header"
    return True, f"valid {suffix} image"


def validate_image(path: Path) -> ImageStatus:
    size = path.stat().st_size
    if path.suffix.lower() == ".svg":
        ok, reason = is_valid_svg(path)
    else:
        ok, reason = is_valid_raster(path)
    return ImageStatus(path=path, ok=ok, reason=reason, size=size)


def extract_image_refs(site_dir: Path, image_dir_name: str) -> list[tuple[Path, str]]:
    refs: list[tuple[Path, str]] = []
    pattern = re.compile(r'''<img\s+[^>]*src=["']([^"']+)["']''', re.IGNORECASE)
    for html in sorted(site_dir.rglob("*.html")):
        text = html.read_text(encoding="utf-8", errors="replace")
        for src in pattern.findall(text):
            if image_dir_name in src:
                refs.append((html, src))
    return refs


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--image-dir", required=True, type=Path)
    parser.add_argument("--site-dir", type=Path)
    parser.add_argument("--report", required=True, type=Path)
    parser.add_argument("--require-images", action="store_true")
    parser.add_argument("--check-html-refs", action="store_true")
    args = parser.parse_args()

    args.report.parent.mkdir(parents=True, exist_ok=True)
    lines: list[str] = []
    failures: list[str] = []

    lines.append(f"Image directory: {args.image_dir}")
    if not args.image_dir.exists():
        failures.append(f"Image directory does not exist: {args.image_dir}")
        images: list[Path] = []
    else:
        images = sorted(
            p for p in args.image_dir.rglob("*")
            if p.is_file() and p.suffix.lower() in {".svg", ".png", ".jpg", ".jpeg", ".webp", ".pdf"}
        )

    lines.append(f"Image count: {len(images)}")
    if args.require_images and not images:
        failures.append("No lwarp image files were found.")

    for path in images:
        status = validate_image(path)
        rel = path.as_posix()
        marker = "OK" if status.ok else "FAIL"
        lines.append(f"{marker}: {rel} ({status.size} bytes) - {status.reason}")
        if not status.ok:
            failures.append(f"Invalid image: {rel} - {status.reason}")

    if args.check_html_refs:
        if not args.site_dir:
            failures.append("--check-html-refs requires --site-dir")
        else:
            image_dir_name = args.image_dir.name
            refs = extract_image_refs(args.site_dir, image_dir_name)
            lines.append("")
            lines.append(f"HTML references to {image_dir_name}: {len(refs)}")
            if args.require_images and not refs:
                failures.append(f"No generated HTML references {image_dir_name}.")
            for html, src in refs:
                # src is normally relative to the HTML file. Axiomathic uses root-level HTML,
                # but resolve relative paths robustly anyway.
                candidate = (html.parent / src).resolve()
                ok = candidate.exists() and candidate.is_file() and candidate.stat().st_size > 0
                marker = "OK" if ok else "FAIL"
                lines.append(f"{marker}: {html.name} -> {src}")
                if not ok:
                    failures.append(f"HTML references missing image: {html.name} -> {src}")

    lines.append("")
    if failures:
        lines.append("RESULT: FAIL")
        lines.extend(f"- {failure}" for failure in failures)
    else:
        lines.append("RESULT: OK")

    report_text = "\n".join(lines) + "\n"
    args.report.write_text(report_text, encoding="utf-8")
    print(report_text)
    return 1 if failures else 0


if __name__ == "__main__":
    sys.exit(main())
