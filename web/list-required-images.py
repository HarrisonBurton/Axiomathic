from pathlib import Path
import re

ROOT = Path('.')
commands = [
    ('includegraphics', re.compile(r'\\includegraphics(?:\[[^\]]*\])?\{([^}]+)\}')),
    ('includepdf', re.compile(r'\\includepdf(?:\[[^\]]*\])?\{([^}]+)\}')),
]

for tex in sorted(ROOT.glob('sections/**/*.tex')):
    text = tex.read_text(encoding='utf-8', errors='ignore')
    refs=[]
    for name, pattern in commands:
        refs.extend((name, m.group(1).strip()) for m in pattern.finditer(text))
    if not refs:
        continue
    print(f'\n{tex}:')
    for name, ref in refs:
        print(f'  {name}: {ref}')
