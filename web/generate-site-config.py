from pathlib import Path
import json, re, html

ROOT=Path('.')
BASE=json.loads(Path('web/site-config.base.json').read_text(encoding='utf-8'))
MASTER=Path('Axiomathic.tex').read_text(encoding='utf-8')

def generated_html_title_map():
    mapping={}
    for hp in Path('.').glob('*.html'):
        if hp.name.endswith('_html.html'):
            continue
        txt=hp.read_text(encoding='utf-8', errors='ignore')
        m=re.search(r'<title>\s*Axiomathic\s+—\s+([^<]+)</title>', txt)
        if m:
            mapping[html.unescape(m.group(1)).strip()] = hp.name
        else:
            h=re.search(r'<h3[^>]*>(.*?)</h3>', txt, re.S)
            if h:
                title=html.unescape(re.sub(r'\s+', ' ', re.sub(r'<[^>]+>', '', h.group(1)))).strip()
                if title:
                    mapping[title]=hp.name
    return mapping

HTML_BY_TITLE = generated_html_title_map()

# Preserve the order in the master document.
SUBFILES=[m.group(1).strip() for m in re.finditer(r'\\subfile\{([^}]+)\}', MASTER)]

def strip_tex(s):
    s=re.sub(r'%.*','',s)
    s=re.sub(r'\\(?:textit|textbf|emph|mathrm|mathbf|mathit)\{([^{}]*)\}',r'\1',s)
    s=re.sub(r'\\[A-Za-z@]+(?:\[[^\]]*\])?\{([^{}]*)\}',r'\1',s)
    s=re.sub(r'\\[A-Za-z@]+','',s)
    s=s.replace('~',' ').replace('\\',' ')
    s=re.sub(r'\$([^$]+)\$',r'\1',s)
    s=re.sub(r'\s+',' ',s).strip(' ,.;:-')
    return html.unescape(s)

def chapter_title(text, fallback):
    m=re.search(r'\\chapter(?:\[[^\]]*\])?\{([^{}]+)\}',text,re.S)
    return strip_tex(m.group(1)) if m else fallback

def first_paragraph(text):
    m=re.search(r'\\chapter(?:\[[^\]]*\])?\{[^{}]+\}',text,re.S)
    body=text[m.end():] if m else text
    # Prefer prose before the first section.  If the chapter opens immediately
    # with a section heading, look just after that heading instead.
    leading=re.split(r'\\section\b|\\begin\{|\\subsection\b',body,maxsplit=1)[0]
    paras=[strip_tex(p) for p in re.split(r'\n\s*\n',leading) if strip_tex(p)]
    if not paras:
        sec=re.search(r'\\section(?:\[[^\]]*\])?\{[^{}]+\}',body,re.S)
        if sec:
            after=body[sec.end():]
            after=re.split(r'\\subsection\b|\\section\b|\\begin\{',after,maxsplit=1)[0]
            paras=[strip_tex(p) for p in re.split(r'\n\s*\n',after) if strip_tex(p)]
    if not paras: return ''
    p=paras[0]
    return p[:220].rstrip()+('…' if len(p)>220 else '')

def slug(title):
    # Mirrors lwarp's ordinary filename convention for simple chapter titles.
    s=re.sub(r'[^A-Za-z0-9]+','-',title).strip('-')
    return s+'.html'

def explicit_filename(text):
    m=re.search(r'\\FileName\{([^{}]+)\}', text)
    if not m:
        return None
    name=m.group(1).strip()
    return name if name.endswith('.html') else name + '.html'

def entry_for(path, eyebrow=None):
    p=Path(path if path.endswith('.tex') else path+'.tex')
    text=p.read_text(encoding='utf-8',errors='ignore')
    title=chapter_title(text,p.stem)
    filename=HTML_BY_TITLE.get(title) or explicit_filename(text) or slug(title)
    return {'file':filename,'title':title,'eyebrow':eyebrow or 'PAGE','description':first_paragraph(text),'source':str(p).replace('\\','/')}

sections=[]
for cat in BASE.get('categories',[]):
    prefix=f"sections/{cat['folder']}/"
    ordered=[]
    for sf in SUBFILES:
        sf_norm=sf.replace('\\','/')
        if sf_norm.startswith(prefix):
            ordered.append(entry_for(sf_norm,cat.get('eyebrow')))
    sections.append({
        'id':cat['id'],'label':cat['label'],'description':cat.get('description',''),'pages':ordered
    })

utility=[]
for cat in BASE.get('utilityCategories',[]):
    prefix=f"sections/{cat['folder']}/"
    for sf in SUBFILES:
        sf_norm=sf.replace('\\','/')
        if sf_norm.startswith(prefix):
            item=entry_for(sf_norm,cat.get('label','PAGE').upper())
            utility.append({'file':item['file'],'title':item['title'],'label':cat.get('label',item['title']),'source':item['source']})

out={
  'siteTitle':BASE.get('siteTitle','Axiomathic'),
  'tagline':BASE.get('tagline',''),
  'intro':BASE.get('intro',''),
  'sections':sections,
  'utilityPages':utility,
  'about':BASE.get('about','')
}
Path('web/site-config.json').write_text(json.dumps(out,indent=2,ensure_ascii=False),encoding='utf-8')
print('Generated web/site-config.json')
for s in sections:
    print(f"  {s['label']}: {len(s['pages'])} page(s)")
for u in utility:
    print(f"  Utility: {u['title']}")
