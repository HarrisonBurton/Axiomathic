from pathlib import Path

for path in Path('.').glob('*.html'):
    if path.name.endswith('_html.html'):
        continue
    text = path.read_text(encoding='utf-8')
    script = '<script src="theme.js" defer></script>'
    if script not in text:
        text = text.replace('</head>', f'{script}\n</head>')
    path.write_text(text, encoding='utf-8')
