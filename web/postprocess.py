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

def strip_book_chapter_label(text: str) -> str:
    # Keep chapter semantics in LaTeX/PDF, but make each generated webpage read
    # as a standalone article.
    pattern = re.compile(
        r'(<h3\b[^>]*>)\s*Chapter(?:&nbsp;|\s)*'
        r'<span class="sectionnumber">.*?</span>\s*',
        flags=re.I | re.S,
    )
    return pattern.sub(r'\1', text)

for path in ROOT.glob("*.html"):
    if path.name.endswith("_html.html"):
        continue

    text = path.read_text(encoding="utf-8")
    text = strip_book_chapter_label(text)
    text = add_type_classes(text)

    config_tag = f"<script>{CONFIG_JS}</script>"
    script_tag = '<script src="theme.js" defer></script>'

    # Remove older injected theme/config tags before adding the current ones.
    text = re.sub(r'<script>window\.AXIOMATHIC_SITE\s*=.*?</script>\s*', '', text, flags=re.S)
    text = text.replace(script_tag, "")
    text = text.replace("</head>", f"{config_tag}\n{script_tag}\n</head>")

    path.write_text(text, encoding="utf-8")
