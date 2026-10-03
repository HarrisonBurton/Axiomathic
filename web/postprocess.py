from pathlib import Path
import json
import re

ROOT = Path(".")
CONFIG = json.loads(Path("web/site-config.json").read_text(encoding="utf-8"))
CONFIG_JS = "window.AXIOMATHIC_SITE = " + json.dumps(CONFIG, ensure_ascii=False) + ";"

TYPE_MAP = {
    "theorem": "theorem",
    "lemma": "lemma",
    "proposition": "proposition",
    "corollary": "corollary",
    "definition": "definition",
    "notation": "notation",
    "conjecture": "conjecture",
    "example": "example",
    "remark": "remark",
    "caution": "warning",
    "warning": "warning",
}

def add_type_classes(text: str) -> str:
    # Classify each lwarp shadebox by the theorem name close to its opening tag.
    starts = list(re.finditer(r'<div\s+class="shadebox"[^>]*>', text, flags=re.I))
    offset = 0
    for m in starts:
        start = m.start() + offset
        end = m.end() + offset
        current = text[start:end]
        lookahead = text[end:end+2200]
        nm = re.search(r'amsthmname(?:plain|definition|remark)">\s*([^<]+)', lookahead, flags=re.I)
        if not nm:
            continue
        theorem_name = re.sub(r'\s+', ' ', nm.group(1)).strip().lower()
        kind = next((v for k, v in TYPE_MAP.items() if k in theorem_name), None)
        if not kind:
            continue
        replacement = re.sub(r'class="shadebox"', f'class="shadebox ax-{kind}"', current, count=1)
        text = text[:start] + replacement + text[end:]
        offset += len(replacement) - len(current)

    # Caution/warning is currently an amsthm environment without shadebox.
    # Add a class to its body so it still receives the web styling.
    body_pattern = re.compile(r'<div\s+class="amsthmbodyplain"[^>]*>', flags=re.I)
    starts = list(body_pattern.finditer(text))
    offset = 0
    for m in starts:
        start = m.start() + offset
        end = m.end() + offset
        current = text[start:end]
        lookahead = text[end:end+1400]
        nm = re.search(r'amsthmname(?:plain|definition|remark)">\s*([^<]+)', lookahead, flags=re.I)
        if not nm:
            continue
        theorem_name = re.sub(r'\s+', ' ', nm.group(1)).strip().lower()
        if "caution" not in theorem_name and "warning" not in theorem_name:
            continue
        replacement = re.sub(r'class="amsthmbodyplain"', 'class="amsthmbodyplain ax-warning"', current, count=1)
        text = text[:start] + replacement + text[end:]
        offset += len(replacement) - len(current)

    return text



def renumber_page_locally(text: str) -> str:
    """Make each generated chapter-page read as an independent publication.

    lwarp numbers headings/theorems using the master book chapter number.  For
    the web edition we remap the leading chapter component to 1 on each page,
    while leaving the PDF/master counters untouched.
    """
    start = text.find('<section class="textbody">')
    if start < 0:
        return text
    end = text.find('</section>', start)
    if end < 0:
        end = len(text)
    block = text[start:end]

    # Infer the master chapter number from the first numbered section or theorem.
    candidates = []
    for pat in (
        r'<span class="sectionnumber">\s*(\d+)\.(\d+)',
        r'amsthmnumber(?:plain|definition|remark)">.*?<span class="textup">\s*(\d+)\.(\d+)',
    ):
        m = re.search(pat, block, flags=re.I | re.S)
        if m:
            candidates.append(int(m.group(1)))
    if not candidates:
        return text
    chapter = candidates[0]

    def remap_number(num: str) -> str:
        # Only touch hierarchical numbers whose first component is this page's
        # master chapter number.  This avoids altering unrelated integers.
        if re.match(rf'^{chapter}(?:\.|$)', num):
            return re.sub(rf'^{chapter}(?=\.|$)', '1', num, count=1)
        return num

    def repl_section(m):
        inner = m.group(1)
        mm = re.match(r'(\s*)(\d+(?:\.\d+)*)(.*)', inner, flags=re.S)
        if not mm:
            return m.group(0)
        return '<span class="sectionnumber">' + mm.group(1) + remap_number(mm.group(2)) + mm.group(3) + '</span>'

    block = re.sub(r'<span class="sectionnumber">(.*?)</span>', repl_section, block, flags=re.I | re.S)

    # Theorem-like counters are emitted inside span.textup within amsthmnumber.
    def repl_theorem(m):
        prefix, num, suffix = m.group(1), m.group(2), m.group(3)
        return prefix + remap_number(num) + suffix

    block = re.sub(
        r'((?:amsthmnumber(?:plain|definition|remark)"[^>]*>).*?<span class="textup">\s*)(\d+(?:\.\d+)*)(\s*</span>)',
        repl_theorem,
        block,
        flags=re.I | re.S,
    )

    # Figure/table captions use the same master chapter component.
    def repl_caption(m):
        return m.group(1) + remap_number(m.group(2))

    block = re.sub(r'((?:Figure|Table)&nbsp;)(\d+(?:\.\d+)*)', repl_caption, block)

    return text[:start] + block + text[end:]

def strip_book_chapter_label(text: str) -> str:
    # Keep chapter semantics in LaTeX/PDF, but make each generated webpage read
    # as a standalone article.
    pattern = re.compile(
        r'(<h3\b[^>]*>)\s*Chapter(?:&nbsp;|\s)*'
        r'<span class="sectionnumber">.*?</span>\s*',
        flags=re.I | re.S,
    )
    return pattern.sub(r'\1', text)




def ensure_mobile_viewport(text: str) -> str:
    """Ensure phones use their actual viewport width instead of a desktop canvas."""
    if 'name="viewport"' in text or "name='viewport'" in text:
        return text
    return text.replace(
        '<head>',
        '<head>\n<meta name="viewport" content="width=device-width, initial-scale=1">',
        1,
    )

def fix_mathjax_environment_spacing(text: str) -> str:
    """MathJax is stricter than TeX about lwarp's `\begin {cases}` form.
    Normalise common environment delimiters before publishing.
    """
    return re.sub(r'\\(begin|end)\s+\{([A-Za-z*]+)\}', r'\\\1{\2}', text)

for path in ROOT.glob("*.html"):
    if path.name.endswith("_html.html"):
        continue

    text = path.read_text(encoding="utf-8")
    text = renumber_page_locally(text)
    text = strip_book_chapter_label(text)
    text = add_type_classes(text)
    text = fix_mathjax_environment_spacing(text)
    text = ensure_mobile_viewport(text)

    config_tag = f"<script>{CONFIG_JS}</script>"
    script_tag = '<script src="theme.js" defer></script>'

    # Remove older injected theme/config tags before adding the current ones.
    text = re.sub(r'<script>window\.AXIOMATHIC_SITE\s*=.*?</script>\s*', '', text, flags=re.S)
    text = text.replace(script_tag, "")
    text = text.replace("</head>", f"{config_tag}\n{script_tag}\n</head>")

    path.write_text(text, encoding="utf-8")
