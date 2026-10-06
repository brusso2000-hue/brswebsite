#!/usr/bin/env python3
"""Static QA for the generated site. Exit code 1 if any check fails.   python3 tools/check.py"""
import glob, json, os, re, sys, html
from html.parser import HTMLParser

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SITE = 'https://brsmove.com'
fails, warns = [], []


def fail(page, msg): fails.append(f'{page}: {msg}')
def warn(page, msg): warns.append(f'{page}: {msg}')


class P(HTMLParser):
    def __init__(s):
        super().__init__(); s.t = []; s.h1 = 0; s.title = ''; s.meta = {}; s.links = []; s.imgs = []; s.ld = []; s.forms = []
        s.in_title = False; s.in_ld = False; s.ctrls = []; s.labels_for = set(); s.canon = None; s.cur_form = None
        s.headings = []; s.cur_h = None; s.a_stack = []; s.anchors = []; s.skip_text = 0

    def handle_starttag(s, tag, a):
        a = dict(a)
        if tag == 'h1': s.h1 += 1
        if tag in ('h1', 'h2', 'h3', 'h4'): s.headings.append(int(tag[1]))
        if tag == 'title': s.in_title = True
        if tag == 'meta' and a.get('name'): s.meta[a['name']] = a.get('content', '')
        if tag == 'meta' and a.get('property'): s.meta[a['property']] = a.get('content', '')
        if tag == 'link' and a.get('rel') == 'canonical': s.canon = a.get('href')
        if tag == 'script' and a.get('type') == 'application/ld+json': s.in_ld = True; s.ld.append('')
        if tag == 'script' or tag == 'style': s.skip_text += 1
        if tag == 'a' and a.get('href'): s.links.append(a['href']); s.a_stack.append({'href': a['href'], 'text': '', 'aria': a.get('aria-label', '')})
        if tag in ('link', 'script', 'source') and (a.get('href') or a.get('src')): s.links.append(a.get('href') or a.get('src'))
        if tag == 'img': s.imgs.append(a); s.links.append(a.get('src', ''))
        if tag == 'form': s.cur_form = {'a': a, 'hidden': [], 'hp': False}; s.forms.append(s.cur_form)
        if s.cur_form is not None and tag == 'input':
            if a.get('type') == 'hidden': s.cur_form['hidden'].append(a.get('name'))
            if a.get('name') == 'bot-field': s.cur_form['hp'] = True
        if tag in ('input', 'select', 'textarea') and a.get('type') not in ('hidden',) and a.get('name') != 'bot-field':
            s.ctrls.append(a)
        if tag == 'label' and a.get('for'): s.labels_for.add(a['for'])

    def handle_endtag(s, tag):
        if tag == 'title': s.in_title = False
        if tag == 'script': s.in_ld = False
        if tag in ('script', 'style'): s.skip_text -= 1
        if tag == 'form': s.cur_form = None
        if tag == 'a' and s.a_stack: s.anchors.append(s.a_stack.pop())

    def handle_data(s, d):
        if s.in_title: s.title += d
        if s.in_ld: s.ld[-1] += d
        if not s.skip_text: s.t.append(d)
        for a in s.a_stack: a['text'] += d


pages = [f for f in glob.glob(os.path.join(ROOT, '**/*.html'), recursive=True) if '/tools/' not in f]
redirects = {}
rp = os.path.join(ROOT, '_redirects')
if os.path.exists(rp):
    for ln in open(rp):
        p = ln.split()
        if len(p) >= 2 and not ln.startswith('#'): redirects[p[0].rstrip('/') or '/'] = p[1]
titles, descs = {}, {}
BANNED = ['over 40 years', 'Fortune 500', 'Get a Free Quote', 'Get My Free Quote', 'Submit My Quote', 'Request a free quote', 'Get a free quote',
          'Best in the industry', 'a office', 'mailto:?', 'Decommisioning', 'accomodate', 'Professional Teamwork', 'include but not limited', 'Busibess', 'Akismet', 'Leave a Reply', 'Post navigation', 'Recent Posts', 'centraloized', 'Infrastrucrure']
GENERIC = {'learn more', 'read more', 'click here', 'more'}


def exists(url):
    u = url.split('#')[0].split('?')[0]
    if not u or u == '/': return True
    p = u.lstrip('/')
    return os.path.isfile(os.path.join(ROOT, p)) or os.path.isfile(os.path.join(ROOT, p, 'index.html')) or os.path.isdir(os.path.join(ROOT, p))


for f in sorted(pages):
    rel = os.path.relpath(f, ROOT)
    src = open(f, encoding='utf8').read()
    p = P(); p.feed(src)
    text = html.unescape(re.sub(r'\s+', ' ', ' '.join(p.t)))
    noindex = 'noindex' in p.meta.get('robots', '')
    if p.h1 != 1: fail(rel, f'{p.h1} h1 elements')
    # heading order: never skip a level downward
    last = 1
    for h in p.headings:
        if h > last + 1: warn(rel, f'heading jumps h{last} -> h{h}')
        last = h
    t = p.title.strip()
    if not t: fail(rel, 'no <title>')
    if len(t) > 65: fail(rel, f'title {len(t)} chars: {t}')
    d = p.meta.get('description', '')
    if not noindex:
        if not 70 <= len(d) <= 165: fail(rel, f'meta description {len(d)} chars')
        if t in titles: fail(rel, f'duplicate title with {titles[t]}')
        if d in descs: fail(rel, f'duplicate description with {descs[d]}')
        titles[t] = rel; descs[d] = rel
        want = SITE + ('/' if rel == 'index.html' else '/' + rel[:-len('index.html')])
        if p.canon != want and rel != '404.html': fail(rel, f'canonical {p.canon} != {want}')
        img = p.meta.get('og:image', '')
        if not img.startswith(SITE) or not exists(img[len(SITE):]): fail(rel, f'og:image does not resolve: {img}')
    for i, block in enumerate(p.ld):
        try: j = json.loads(block)
        except Exception as e: fail(rel, f'JSON-LD #{i} invalid: {e}'); continue
        nodes = j.get('@graph', [j])
        types = [n.get('@type') for n in nodes]
        flat = [x for t_ in types for x in (t_ if isinstance(t_, list) else [t_])]
        if rel == 'business-relocation/index.html' and 'Service' in flat: fail(rel, 'About page must not use Service schema')
        if rel == 'business-relocation/index.html' and 'AboutPage' not in flat: fail(rel, 'About page missing AboutPage schema')
        for n in nodes:
            if n.get('@type') == 'FAQPage':
                for q in n['mainEntity']:
                    if q['name'] not in text or q['acceptedAnswer']['text'] not in text: fail(rel, f'FAQ schema not visible on page: {q["name"]}')
    for b in BANNED:
        if b in text or b in src: fail(rel, f'banned phrase present: {b!r}')
    for a in p.anchors:
        label = (a['text'].strip() or a['aria']).lower()
        if label in GENERIC: fail(rel, f'generic link text {label!r} -> {a["href"]}')
    eager = 0
    for im in p.imgs:
        if 'alt' not in im: fail(rel, f'img without alt attribute: {im.get("src")}')
        if not im.get('width') or not im.get('height'): fail(rel, f'img without dimensions: {im.get("src")}')
        if im.get('loading') != 'lazy': eager += 1
        elif im.get('alt') is None: pass
    if eager > 3: warn(rel, f'{eager} non-lazy images')
    for u in set(p.links):
        if u.startswith(('http', 'mailto:', 'tel:', '#', 'data:', '//')) or not u: continue
        base = u.split('#')[0].split('?')[0].rstrip('/') or '/'
        if base in redirects: fail(rel, f'internal link to redirected URL {u}')
        elif not exists(u): fail(rel, f'broken internal link {u}')
    for fm in p.forms:
        a = fm['a']
        if a.get('data-netlify') != 'true' or not a.get('name') or a.get('method', '').lower() != 'post': fail(rel, 'form not wired for Netlify Forms (POST + data-netlify + name)')
        if 'form-name' not in fm['hidden']: fail(rel, 'form missing hidden form-name')
        if not fm['hp']: fail(rel, 'form missing honeypot')
        if a.get('action', '').startswith('mailto'): fail(rel, 'mailto form action')
    for c in p.ctrls:
        if not (c.get('id') in p.labels_for or c.get('aria-label') or c.get('aria-labelledby') or c.get('type') in ('checkbox', 'radio')):
            fail(rel, f'form control without label: {c.get("name")}')
    for needle in ('Learn more', 'Read more'):
        pass
    if not noindex and not any(h in ('/request-a-quote/', '/request-a-quote') for h in p.links) and rel not in ('request-a-quote/index.html',):
        fail(rel, 'page has no quote CTA')

# sitemap
sm = open(os.path.join(ROOT, 'sitemap.xml')).read()
urls = re.findall(r'<loc>([^<]+)</loc>', sm)
for u in urls:
    path = u[len(SITE):]
    if not exists(path): fail('sitemap.xml', f'url does not exist: {u}')
    if base_redirect := redirects.get(path.rstrip('/') or '/'): fail('sitemap.xml', f'redirected URL in sitemap: {u}')
if len(set(urls)) != len(urls): fail('sitemap.xml', 'duplicate urls')
for r, tgt in redirects.items():
    if not exists(tgt): fail('_redirects', f'target missing: {tgt}')
    if os.path.exists(os.path.join(ROOT, r.lstrip('/'), 'index.html')): fail('_redirects', f'redirected page still exists: {r}')

print(f'{len(pages)} pages checked, {len(urls)} sitemap URLs, {len(redirects)//1} redirect rules')
for w in warns: print('WARN', w)
for x in fails: print('FAIL', x)
print('PASS' if not fails else f'{len(fails)} FAILURES')
sys.exit(1 if fails else 0)
