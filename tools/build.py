#!/usr/bin/env python3
"""Static site generator for brsmove.com.

Inputs
  tools/content.json     legacy page text scraped from the old WordPress site (blog posts, careers, etc.)
  tools/services/*.json  rewritten service-page copy (one file per service) + _typos.json sweep list
Output
  Plain HTML in the repo root (index.html, <slug>/index.html), sitemap.xml, robots.txt, _redirects.

    python3 tools/build.py

Quote forms are Netlify Forms (POST to "/" with data-netlify). Notifications are configured
in the Netlify dashboard: Site configuration -> Forms -> Form notifications.
"""
import datetime, glob, hashlib, html, json, os, re, shutil
from urllib.parse import quote
from PIL import Image

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SITE = 'https://brsmove.com'
PHONE = '1-718-399-8000'
PHONE_TEL = '+17183998000'
EMAIL = 'info@brsmove.com'
TODAY = datetime.date.today().isoformat()
CONTENT = json.load(open(os.path.join(ROOT, 'tools/content.json')))
esc = html.escape

SOCIAL = {
    'LinkedIn': 'https://www.linkedin.com/company/business-relocation-services',
    'Instagram': 'https://instagram.com/brsmove',
    'YouTube': 'https://www.youtube.com/watch?v=aDcoYp0tAaY',
}
BBB = 'https://www.bbb.org/us/nj/secaucus/profile/relocation-services/business-relocation-services-inc-0221-90224076/'
ADDR = [
    ('Secaucus, NJ', '20 Aquarium Dr', 'Secaucus', 'NJ', '07094'),
    ('New York, NY', '425 East 13th Street', 'New York', 'NY', '10009'),
]

# ---------------------------------------------------------------- services
# slug, nav name, group.  Titles, blurbs, copy come from tools/services/<slug>.json
SERVICE_META = [
    ('office-movers', 'Office Movers', 'Moving & Relocation'),
    ('moving-management', 'Moving Management', 'Moving & Relocation'),
    ('move-planner', 'Move Planner', 'Moving & Relocation'),
    ('office-decommissioning', 'Office Decommissioning', 'Moving & Relocation'),
    ('school-moving-services', 'School Moving Services', 'Moving & Relocation'),
    ('business-relocation-services-in-new-york', 'Business Relocation', 'Moving & Relocation'),
    ('furniture-installation', 'Furniture Installation', 'Furniture & Space'),
    ('furniture-liquidation', 'Furniture Liquidation', 'Furniture & Space'),
    ('space-planning', 'Space Planning', 'Furniture & Space'),
    ('inventory-control', 'Inventory Control', 'Furniture & Space'),
    ('moving-it-equipment-in-new-york', 'Moving IT Equipment', 'IT & Technology'),
    ('computer-moving', 'Computer Moving', 'IT & Technology'),
    ('server-moving-computer-relocation', 'Server Moving', 'IT & Technology'),
    ('data-center-relocation', 'Data Center Relocation', 'IT & Technology'),
    ('it-equipment-recycling', 'IT Equipment Recycling', 'IT & Technology'),
    ('computer-recycling', 'Computer Recycling', 'IT & Technology'),
    ('storage-facilities', 'Storage Facilities', 'Storage & Rentals'),
    ('rent-moving-crates', 'Rent Moving Crates', 'Storage & Rentals'),
    ('library-cart-rental', 'Library Cart Rental', 'Storage & Rentals'),
]
GROUPS = ['Moving & Relocation', 'Furniture & Space', 'IT & Technology', 'Storage & Rentals']
SVC_DATA = {}
for _p in glob.glob(os.path.join(ROOT, 'tools/services/*.json')):
    _n = os.path.basename(_p)[:-5]
    if not _n.startswith('_') and not _n.startswith('mbe'):
        SVC_DATA[_n] = json.load(open(_p))
MBE_DATA = json.load(open(os.path.join(ROOT, 'tools/services/mbe-minority-business-enterprise-certification.json')))
TYPOS = json.load(open(os.path.join(ROOT, 'tools/services/_typos.json')))
TYPO_KEYS = sorted(TYPOS, key=len, reverse=True)
# (slug, nav, h1, blurb, group)
SERVICES = [(s, n, SVC_DATA[s]['h1'], SVC_DATA[s]['card_blurb'], g) for s, n, g in SERVICE_META]
SV = {s[0]: s for s in SERVICES}

# Near-duplicate legacy URLs that now permanently redirect to the page that owns the topic.
REDIRECTS = {
    'relocation-services-in-new-york': 'business-relocation-services-in-new-york',
    'relocation-services-business-moving-services': 'business-relocation-services-in-new-york',
    'office-movers-in-new-york': 'office-movers',
    'office-decommission-new-york': 'office-decommissioning',
}
POSTS = [u.strip('/').split('/')[-1] for u in CONTENT if CONTENT[u]['text'].startswith('post-content-inner')]
ABOUT = 'business-relocation'

# ---------------------------------------------------------------- helpers
ACR = {'IT', 'BRS', 'MWBE', 'NYC', 'NJ', 'NY', 'PA', 'MBE', 'RFP', 'RFQ', 'US', 'CT', 'ROI', 'RPMS', 'COVID-19', 'II', 'FAQ'}
IMG_DIR = os.path.join(ROOT, 'assets/img')
_dims = {}


def dims(fn):
    if fn not in _dims:
        try:
            _dims[fn] = Image.open(os.path.join(IMG_DIR, fn)).size
        except Exception:
            _dims[fn] = None
    return _dims[fn]


def alt_from(fn):
    b = os.path.splitext(fn)[0]
    b = re.sub(r'^cropped-', '', b)
    b = re.sub(r'-\d+x\d+$', '', b)
    return re.sub(r'[-_]+', ' ', b).strip()


def img(name, alt=None, cls='', eager=False, sizes='(max-width: 760px) 100vw, 600px', cap=False):
    """<img> with intrinsic size, srcset when an 800w variant exists, lazy by default. alt='' marks decorative."""
    fn = name if name.endswith(('.webp', '.png')) else name + '.webp'
    d = dims(fn)
    if not d:
        return ''
    a = esc(alt_from(fn) if alt is None else alt)
    attrs = f'src="/assets/img/{fn}" alt="{a}" width="{d[0]}" height="{d[1]}"'
    v = fn[:-5] + '-800.webp'
    if d[0] > 900 and os.path.exists(os.path.join(IMG_DIR, v)):
        attrs += f' srcset="/assets/img/{v} 800w, /assets/img/{fn} {d[0]}w" sizes="{sizes}"'
    if cls:
        attrs += f' class="{cls}"'
    if cap:
        attrs += f' style="max-width:{d[0]}px"'
    attrs += ' decoding="async"' + ('' if eager else ' loading="lazy"')
    return f'<img {attrs}>'


def local_img(url):
    fn = os.path.splitext(os.path.basename(url))[0] + '.webp'
    return fn if os.path.exists(os.path.join(IMG_DIR, fn)) else None


def caps_fix(t):
    t = t.strip().replace('\xa0', ' ')
    if t.isupper() and len(t) > 3:
        t = ' '.join(w if re.sub(r'[^A-Z0-9-]', '', w) in ACR else w.capitalize() for w in t.split())
    return t


def sweep(t):
    for k in TYPO_KEYS:
        t = t.replace(k, TYPOS[k])
    return t


def clip(t, n):
    t = re.sub(r'\s+', ' ', t).strip()
    if len(t) <= n:
        return t
    return t[:n].rsplit(' ', 1)[0].rstrip(',;:-') + '…'


def short_title(raw):
    parts = [p.strip() for p in re.split(r'\s+[-–|]\s+', raw)]
    parts = [p for p in parts if p and 'BRSmove' not in p and 'Business Relocation Services in New York, New Jersey' not in p]
    t = parts[0] if parts else raw
    if len(parts) > 1 and len(t) + len(parts[1]) < 40:
        t = f'{t} - {parts[1]}'
    return t


SOCIAL_SVG = {
    'LinkedIn': '<path d="M6.9 8.6H3.7V20h3.2zM5.3 3.5a1.9 1.9 0 1 0 0 3.8 1.9 1.9 0 0 0 0-3.8zM20.3 20v-6.3c0-3.1-1.7-4.6-3.9-4.6-1.8 0-2.6 1-3 1.7V8.6h-3.2V20h3.2v-6.2c0-1.6.3-3.1 2.3-3.1s2 1.8 2 3.2V20z"/>',
    'Instagram': '<rect x="3" y="3" width="18" height="18" rx="5" fill="none" stroke="currentColor" stroke-width="2"/><circle cx="12" cy="12" r="4" fill="none" stroke="currentColor" stroke-width="2"/><circle cx="17.5" cy="6.5" r="1.2"/>',
    'YouTube': '<path d="M21.6 7.2a2.5 2.5 0 0 0-1.8-1.8C18.2 5 12 5 12 5s-6.2 0-7.8.4A2.5 2.5 0 0 0 2.4 7.2C2 8.8 2 12 2 12s0 3.2.4 4.8a2.5 2.5 0 0 0 1.8 1.8C5.8 19 12 19 12 19s6.2 0 7.8-.4a2.5 2.5 0 0 0 1.8-1.8c.4-1.6.4-4.8.4-4.8s0-3.2-.4-4.8zM10 15V9l5.2 3z"/>',
}


def social_links():
    return '<div class="social">' + ''.join(
        f'<a href="{u}" target="_blank" rel="noopener noreferrer" aria-label="{n} (opens in a new tab)"><svg viewBox="0 0 24 24" fill="currentColor" aria-hidden="true" focusable="false">{SOCIAL_SVG[n]}</svg></a>'
        for n, u in SOCIAL.items()) + '</div>'


CERT_IMGS = [
    ('New-York-State-Minority-and-Women-Owned-Business-Enterprise-Certification-Business-Relocation-Services', 'New York State Minority and Women-Owned Business Enterprise (MWBE) certification'),
    ('MBE-NYC-Small-Business-Cert-2025-2030-Business-Relocation-Services', 'NYC Small Business Services MBE certification, 2025 to 2030'),
    ('NMSDC-Certificate-9-26-25-9-30-26-Business-Relocation-Services', 'NMSDC Minority Business Enterprise certificate'),
]

# ---------------------------------------------------------------- global layout
def nav_html(current):
    mega = ''
    for g in GROUPS:
        links = ''.join(f'<a href="/{s[0]}/">{esc(s[1])}</a>' for s in SERVICES if s[4] == g)
        mega += f'<div><p class="mega-title">{g}</p>{links}</div>'
    cur = lambda p: ' aria-current="page"' if current == p else ''
    return f'''<nav class="nav" id="nav" aria-label="Main">
<button class="nav-close" type="button">Close <span aria-hidden="true">&times;</span><span class="sr-only"> menu</span></button>
<ul>
<li class="has-menu"><button class="nl" type="button" aria-expanded="false" aria-controls="mega-services">Services <svg width="12" height="12" viewBox="0 0 12 12" aria-hidden="true" focusable="false"><path d="M2 4l4 4 4-4" fill="none" stroke="currentColor" stroke-width="1.8"/></svg></button>
<div class="mega" id="mega-services" role="group" aria-label="Services">{mega}<div class="mega-foot"><a href="/our-services/"><b>View all services</b></a><a class="btn btn-cta" href="/request-a-quote/">Request a Free Quote</a></div></div></li>
<li><a class="nl" href="/{ABOUT}/"{cur('about')}>About</a></li>
<li><a class="nl" href="/blog/"{cur('blog')}>Blog</a></li>
<li><a class="nl" href="/careers/"{cur('careers')}>Careers</a></li>
<li><a class="nl" href="/contact-brs-business-relocation-services-new-york-new-jersey/"{cur('contact')}>Contact</a></li>
</ul></nav>'''


def header(current=''):
    return f'''<a class="skip" href="#main">Skip to main content</a>
<header class="header"><div class="wrap">
<a class="logo" href="/" aria-label="Business Relocation Services, home"><img src="/assets/logo.png" alt="BRS Business Relocation Services" width="140" height="50"></a>
{nav_html(current)}
<div class="head-cta"><a class="head-phone" href="tel:{PHONE_TEL}"><small>Call us</small>{PHONE}</a><a class="btn btn-cta" href="/request-a-quote/">Request a Free Quote</a>
<button class="burger" type="button" aria-expanded="false" aria-controls="nav"><span>Menu</span><svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" aria-hidden="true" focusable="false"><path d="M4 7h16M4 12h16M4 17h16"/></svg></button></div>
</div></header><div class="scrim"></div>'''


def footer():
    foot = ['office-movers', 'moving-management', 'office-decommissioning', 'school-moving-services', 'furniture-installation',
            'moving-it-equipment-in-new-york', 'data-center-relocation', 'storage-facilities', 'rent-moving-crates']
    svc = ''.join(f'<li><a href="/{s}/">{esc(SV[s][1])}</a></li>' for s in foot) + '<li><a href="/our-services/"><b>All services</b></a></li>'
    return f'''<footer class="footer"><div class="wrap">
<div class="cols">
<div><a class="flogo" href="/" aria-label="Business Relocation Services, home"><img src="/assets/logo.png" alt="" width="126" height="45" loading="lazy"></a>
<p>Commercial moving and relocation project management for New York, New Jersey and Pennsylvania. Serving clients since 1987. Certified MWBE.</p>
<p><a href="tel:{PHONE_TEL}"><b>{PHONE}</b></a><br><a href="mailto:{EMAIL}">{EMAIL}</a></p>{social_links()}
<p style="margin-top:18px"><a class="btn btn-cta" href="/request-a-quote/">Request a Free Quote</a></p></div>
<div><h2 class="foot-title">Services</h2><ul>{svc}</ul></div>
<div><h2 class="foot-title">Company</h2><ul><li><a href="/{ABOUT}/">About BRS</a></li><li><a href="/mbe-minority-business-enterprise-certification/">Certifications</a></li><li><a href="/blog/">Blog</a></li><li><a href="/careers/">Careers</a></li><li><a href="/contact-brs-business-relocation-services-new-york-new-jersey/">Contact us</a></li><li><a href="{BBB}" target="_blank" rel="noopener noreferrer">BBB profile<span class="sr-only"> (opens in a new tab)</span></a></li></ul></div>
<div><h2 class="foot-title">Locations</h2>
<address>20 Aquarium Dr<br>Secaucus, NJ 07094</address><address>425 East 13th Street<br>New York, NY 10009</address></div>
</div>
<div class="legal"><span>&copy; {datetime.date.today().year} Business Relocation Services Inc. All rights reserved.</span><span>Serving clients since 1987</span></div>
</div></footer>
<nav class="mbar" aria-label="Quick actions"><a class="btn btn-outline" href="tel:{PHONE_TEL}">Call now</a><a class="btn btn-cta" href="/request-a-quote/">Get a Quote</a></nav>'''


def ver(rel):
    """Short content hash so a changed stylesheet/script gets a new URL (browsers never keep a stale copy)."""
    return hashlib.md5(open(os.path.join(ROOT, rel), 'rb').read()).hexdigest()[:8]


def head(title, desc, path, og_img=None, schema=None, noindex=False, extra=''):
    url = SITE + (path if path.startswith('/') else '/' + path)
    og = og_img or '/assets/og-default.jpg'
    ogdim = '<meta property="og:image:width" content="1200"><meta property="og:image:height" content="630">' if og == '/assets/og-default.jpg' else ''
    robots = 'noindex, follow' if noindex else 'index, follow, max-snippet:-1, max-image-preview:large, max-video-preview:-1'
    schema_html = '<script type="application/ld+json">' + json.dumps(schema, separators=(',', ':'), ensure_ascii=False) + '</script>' if schema else ''
    return f'''<!doctype html>
<html lang="en-US"><head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>{esc(title)}</title>
<meta name="description" content="{esc(desc)}">
<meta name="robots" content="{robots}">
<link rel="canonical" href="{url}">
<meta name="theme-color" content="#1f3a4d">
<meta property="og:locale" content="en_US"><meta property="og:type" content="website">
<meta property="og:title" content="{esc(title)}"><meta property="og:description" content="{esc(desc)}">
<meta property="og:url" content="{url}"><meta property="og:site_name" content="Business Relocation Services">
<meta property="og:image" content="{SITE}{og}">{ogdim}
<meta name="twitter:card" content="summary_large_image"><meta name="twitter:title" content="{esc(title)}"><meta name="twitter:description" content="{esc(desc)}"><meta name="twitter:image" content="{SITE}{og}">
<link rel="icon" type="image/png" sizes="32x32" href="/assets/favicon-32.png">
<link rel="apple-touch-icon" href="/assets/apple-touch-icon.png">
<link rel="preload" href="/assets/fonts/inter-latin.woff2" as="font" type="font/woff2" crossorigin>
<link rel="preload" href="/assets/fonts/source-serif-4-latin.woff2" as="font" type="font/woff2" crossorigin>
<link rel="stylesheet" href="/assets/css/style.css?v={ver("assets/css/style.css")}">
{extra}{schema_html}
</head>'''


def page(path, title, desc, body, current='', og_img=None, schema=None, noindex=False, extra=''):
    out = head(title, desc, path, og_img, schema, noindex, extra) + '<body>' + header(current) + '<main id="main" tabindex="-1">' + body + '</main>' + footer() + '<script src="/assets/js/main.js?v=' + ver("assets/js/main.js") + '" defer></script></body></html>'
    # analytics hooks (consumed by main.js only if a dataLayer exists; no personal data)
    out = out.replace('href="/request-a-quote/"', 'href="/request-a-quote/" data-track="quote-cta"')
    out = re.sub(r'href="tel:([^"]+)"', r'href="tel:\1" data-track="phone-click"', out)
    fp = os.path.join(ROOT, path.strip('/'), 'index.html') if path != '/' else os.path.join(ROOT, 'index.html')
    os.makedirs(os.path.dirname(fp), exist_ok=True)
    open(fp, 'w', encoding='utf8').write(out)
    return fp


ORG_ID = SITE + '/#organization'


def org_schema():
    return {
        '@type': ['MovingCompany', 'LocalBusiness'], '@id': ORG_ID, 'name': 'Business Relocation Services Inc. (BRS)',
        'alternateName': 'BRS', 'url': SITE + '/', 'logo': SITE + '/assets/logo.png', 'image': SITE + '/assets/og-default.jpg',
        'description': 'Commercial moving and relocation project management company serving New York, New Jersey and Pennsylvania since 1987.',
        'telephone': '+1-718-399-8000', 'email': EMAIL, 'foundingDate': '1987',
        'address': {'@type': 'PostalAddress', 'streetAddress': '20 Aquarium Dr', 'addressLocality': 'Secaucus', 'addressRegion': 'NJ', 'postalCode': '07094', 'addressCountry': 'US'},
        'location': [{'@type': 'Place', 'name': 'BRS - ' + a[0], 'address': {'@type': 'PostalAddress', 'streetAddress': a[1], 'addressLocality': a[2], 'addressRegion': a[3], 'postalCode': a[4], 'addressCountry': 'US'}} for a in ADDR],
        'areaServed': [{'@type': 'State', 'name': 'New York'}, {'@type': 'State', 'name': 'New Jersey'}, {'@type': 'State', 'name': 'Pennsylvania'}],
        'sameAs': list(SOCIAL.values()) + [BBB],
    }


def org_ref():
    return {'@id': ORG_ID}


def crumbs(items):
    return {'@type': 'BreadcrumbList', 'itemListElement': [{'@type': 'ListItem', 'position': i + 1, 'name': n, 'item': SITE + u} for i, (n, u) in enumerate(items)]}


def crumbs_html(items):
    parts = [f'<li><a href="{u}">{esc(n)}</a></li>' for n, u in items[:-1]] + [f'<li aria-current="page">{esc(items[-1][0])}</li>']
    return '<nav class="crumbs" aria-label="Breadcrumb"><ol>' + ''.join(parts) + '</ol></nav>'


def faq_schema(faq):
    return {'@type': 'FAQPage', 'mainEntity': [{'@type': 'Question', 'name': f['q'], 'acceptedAnswer': {'@type': 'Answer', 'text': f['a']}} for f in faq]}


def graph(*nodes):
    return {'@context': 'https://schema.org', '@graph': list(nodes)}

# ---------------------------------------------------------------- forms (Netlify Forms)
STATES = 'AL AK AZ AR CA CO CT DE DC FL GA HI ID IL IN IA KS KY LA ME MD MA MI MN MS MO MT NE NV NH NJ NM NY NC ND OH OK OR PA RI SC SD TN TX UT VT VA WA WV WI WY'.split()
SERVICE_CHOICES = ['Office moving', 'Business or corporate relocation', 'IT equipment, server or data center move', 'School or library move',
                   'Furniture installation or liquidation', 'Storage', 'Moving crate or library cart rental', 'Office decommissioning', 'Other / not sure yet']
ADDON_OPTS = ['Packing and unpacking', 'Furniture installation', 'Furniture storage', 'Warehouse storage', 'IT or server relocation', 'Moving crate rental', 'Library cart rental', 'Office decommissioning']


def form_open(name, thanks, subject, cls='qcard', extra=''):
    return (f'<form class="{cls}" name="{name}" method="POST" action="{thanks}" data-netlify="true" netlify-honeypot="bot-field" data-form data-thanks="{thanks}" novalidate {extra}>'
            f'<input type="hidden" name="form-name" value="{name}"><input type="hidden" name="subject" value="BRS website: {esc(subject)}">'
            '<p class="hp" aria-hidden="true"><label>Do not fill this out <input name="bot-field" tabindex="-1" autocomplete="off"></label></p>'
            '<div class="error-summary" tabindex="-1" role="alert" hidden><p class="es-title">Please fix the following</p><ul></ul></div>')


FORM_TAIL = '<div class="form-status" role="status" aria-live="polite"></div></form>'
CONSENT = '<p class="form-note">By submitting, you agree that BRS may contact you about your request.</p>'


def fld(i, label, name, typ='text', req=False, ac=None, hint=None, group=False, inputmode=None, ph=None):
    r = ' <span class="req" aria-hidden="true">*</span><span class="sr-only"> (required)</span>' if req else ''
    a = f' autocomplete="{ac}"' if ac else ''
    a += ' required aria-required="true"' if req else ''
    a += ' data-contact="1"' if group else ''
    a += f' inputmode="{inputmode}"' if inputmode else ''
    a += f' placeholder="{esc(ph)}"' if ph else ''
    h = f'<p class="hint" id="{i}-hint">{hint}</p>' if hint else ''
    d = f'{i}-err' + (f' {i}-hint' if hint else '')
    return f'<div class="field"><label for="{i}" data-label="{esc(label)}">{esc(label)}{r}</label>{h}<input id="{i}" name="{name}" type="{typ}"{a} aria-describedby="{d}"><p class="field-error" id="{i}-err" hidden></p></div>'


def sel(i, label, name, opts, req=False, blank='Select one', ac=None):
    r = ' <span class="req" aria-hidden="true">*</span><span class="sr-only"> (required)</span>' if req else ''
    o = f'<option value="">{blank}</option>' + ''.join(f'<option>{esc(x)}</option>' for x in opts)
    a = ' required aria-required="true"' if req else ''
    a += f' autocomplete="{ac}"' if ac else ''
    return f'<div class="field"><label for="{i}" data-label="{esc(label)}">{esc(label)}{r}</label><select id="{i}" name="{name}"{a} aria-describedby="{i}-err">{o}</select><p class="field-error" id="{i}-err" hidden></p></div>'


def contact_pair(p, hint='Provide an email address, a phone number, or both.'):
    return (f'<fieldset class="fieldset contact-group"><legend>How should we reach you?</legend><p class="hint">{hint}</p>'
            f'<div class="row2">{fld(p + "-e", "Email", "Email", "email", ac="email", group=True)}{fld(p + "-p", "Phone", "Phone", "tel", ac="tel", group=True, inputmode="tel")}</div></fieldset>')


def quick_form():
    return (form_open('quote-quick', '/thank-you-request-a-quote/', 'Quote request (homepage)', cls='qform')
            + f'<div class="row2">{fld("q-n", "Name", "Name", req=True, ac="name")}{fld("q-c", "Company or organization", "Company", req=True, ac="organization")}</div>'
            + contact_pair('q')
            + f'<div class="row2">{sel("q-s", "Service needed", "Service", SERVICE_CHOICES, req=True)}{fld("q-t", "Move date or timeframe", "Timeframe", ph="e.g. March, next quarter")}</div>'
            + '<button class="btn btn-cta btn-block btn-lg" type="submit">Request a Free Quote</button>'
            + CONSENT + f'<p class="form-note">Prefer to talk? Call <a href="tel:{PHONE_TEL}"><b>{PHONE}</b></a></p>' + FORM_TAIL)


def full_quote_form():
    addons = ''.join(f'<label><input type="checkbox" name="Additional services" value="{esc(o)}"> {esc(o)}</label>' for o in ADDON_OPTS)
    states = lambda i, n, lab: sel(i, lab, n, STATES, blank='State', ac='address-level1')
    return (form_open('quote', '/thank-you-request-a-quote/', 'Quote request', extra='data-steps')
            + '<h2>Tell us about your move</h2><p class="sub">Three short steps. We follow up by email or phone, whichever you prefer. Fields marked <span aria-hidden="true">*</span><span class="sr-only">with an asterisk</span> are required.</p>'
            + '<div class="progress"><ol class="progress-list" aria-hidden="true"><li>Contact</li><li>Project</li><li>Details</li></ol><p class="progress-text" aria-live="polite"></p></div>'
            + f'<fieldset class="fstep" data-step="1" data-title="Contact"><legend><span class="step-title" tabindex="-1">Your contact details</span></legend>'
              f'<div class="row2">{fld("f-n", "Full name", "Name", req=True, ac="name")}{fld("f-c", "Company or organization", "Company", req=True, ac="organization")}</div>{contact_pair("f")}</fieldset>'
            + f'<fieldset class="fstep" data-step="2" data-title="Project basics"><legend><span class="step-title" tabindex="-1">Project basics</span></legend>'
              f'{sel("f-s", "Service needed", "Service", SERVICE_CHOICES, req=True)}'
              f'<div class="row3">{fld("f-oc", "Moving from (city)", "Origin city", req=True)}{states("f-os", "Origin state", "Moving from (state)")}</div>'
              f'<div class="row3">{fld("f-dc", "Moving to (city)", "Destination city")}{states("f-ds", "Destination state", "Moving to (state)")}</div>'
              f'{fld("f-t", "Target move date or timeframe", "Timeframe", ph="e.g. March 15, or next quarter")}</fieldset>'
            + f'<fieldset class="fstep" data-step="3" data-title="Details"><legend><span class="step-title" tabindex="-1">A few details</span></legend>'
              f'{fld("f-z", "Approximate size", "Size", hint="Optional. For example, number of employees, floors or square feet.")}'
              f'<fieldset class="fieldset"><legend class="plain">Additional services (optional)</legend><div class="checks">{addons}</div></fieldset>'
              '<div class="field"><label for="f-m" data-label="Details">Anything else we should know? (optional)</label><textarea id="f-m" name="Details" aria-describedby="f-m-err"></textarea><p class="field-error" id="f-m-err" hidden></p></div>'
              f'<details class="optional"><summary>Add street addresses and building details (optional)</summary>'
              f'{fld("f-a1", "Current street address", "Current address", ac="off")}{fld("f-a2", "Destination street address", "Destination address", ac="off")}'
              '<fieldset class="fieldset"><legend class="plain">Elevator access</legend><div class="radios"><label><input type="radio" name="Elevator at current location" value="Yes"> Current location: yes</label><label><input type="radio" name="Elevator at current location" value="No"> Current: no</label>'
              '<label><input type="radio" name="Elevator at destination" value="Yes"> Destination: yes</label><label><input type="radio" name="Elevator at destination" value="No"> Destination: no</label></div></fieldset></details></fieldset>'
            + '<div class="step-nav"><button class="btn btn-outline" type="button" data-back hidden>Back</button><button class="btn btn-cta" type="button" data-next>Next step</button>'
              '<button class="btn btn-cta btn-lg" type="submit" data-submit>Request a Free Quote</button></div>'
            + CONSENT + FORM_TAIL)


def small_form(name, thanks, subject, extra_fields='', label='Send message', ident='c'):
    return (form_open(name, thanks, subject)
            + f'<div class="row2">{fld(ident + "-n", "Name", "Name", req=True, ac="name")}{fld(ident + "-o", "Company or organization", "Company", ac="organization")}</div>'
            + contact_pair(ident) + extra_fields
            + f'<div class="field"><label for="{ident}-m" data-label="Message">Message <span class="req" aria-hidden="true">*</span><span class="sr-only"> (required)</span></label><textarea id="{ident}-m" name="Message" required aria-required="true" aria-describedby="{ident}-m-err"></textarea><p class="field-error" id="{ident}-m-err" hidden></p></div>'
            + f'<button class="btn btn-cta btn-block btn-lg" type="submit">{label}</button>' + CONSENT + FORM_TAIL)

# ---------------------------------------------------------------- legacy prose (blog posts)
SKIP = {'request a quote', 'get started', 'get started today', 'learn more', 'read more', 'request a free quote', 'ask for a free consultation today!', 'join us! it will only take a minute'}


def clean_lines(text):
    text = sweep(text.split('##### Menu')[0].replace('post-content-inner">', ''))
    # drop WordPress leftovers that trail the real content (post navigation, comment form, sidebar lists)
    text = re.split(r'\n#+\s*(?:Post navigation|Leave a Reply|Recent Posts|Contact Form)\b', text)[0]
    lines = []
    for ln in text.split('\n'):
        s = ln.replace('\xa0', ' ').replace('﻿', '').strip()
        if not s or s.lower().strip(' .') in SKIP or (s.lower().startswith(('learn more about', 'more about')) and len(s) < 60) or s.startswith('<div') or s.startswith('[]'):
            continue
        lines.append(s)
    return lines


def parse_blocks(lines):
    blocks, cur_h, cur, pending = [], None, [], []

    def flush():
        nonlocal pending
        if len(pending) >= 3:
            cur.append(('ul', pending))
        else:
            cur.extend(('p', p) for p in pending)
        pending = []

    for s in lines:
        m = re.match(r'^(#{1,6})\s*(.*)$', s)
        if m:
            flush()
            h = caps_fix(m.group(2))
            if not h:
                continue
            if cur_h is not None or cur:
                blocks.append((cur_h, cur))
            cur_h, cur = h, []
            continue
        if len(s) <= 90 and not re.search(r'[.!?:]$', s):
            pending.append(s)
        else:
            flush()
            cur.append(('p', s))
    flush()
    if cur_h is not None or cur:
        blocks.append((cur_h, cur))
    return blocks


def linkify(t):
    t = esc(t)
    t = re.sub(r'(1-718-399-8000|\(718\) 399-8000)', f'<a href="tel:{PHONE_TEL}">\\1</a>', t)
    return re.sub(r'([\w.+-]+@brsmove\.com)', r'<a href="mailto:\1">\1</a>', t)


def render_nodes(nodes):
    return ''.join(f'<p>{linkify(v)}</p>' if k == 'p' else '<ul>' + ''.join(f'<li>{linkify(i)}</li>' for i in v) + '</ul>' for k, v in nodes)


def inline_cta(text='Planning a move? Talk to our team.'):
    return f'<div class="inline-cta"><p>{text}</p><a class="btn btn-cta" href="/request-a-quote/">Request a Free Quote</a></div>'


def render_prose(blocks, images, cta_after=3, drop_first_heading=None):
    out, imgs, n, seen = '', list(images), 0, set()
    for h, nodes in blocks:
        if h and (h.lower() == (drop_first_heading or '').lower() or h.lower() in seen):
            h = None
        if h:
            seen.add(h.lower())
        if not nodes:
            continue
        out += (f'<h2>{esc(h)}</h2>' if h else '') + render_nodes(nodes)
        n += 1
        if imgs and n % 2 == 1:
            out += f'<figure>{img(imgs.pop(0), alt="", cap=True)}</figure>'
        if n == cta_after:
            out += inline_cta()
    return out


def cta_band(h='Planning a move? Bring BRS in early.', p='Tell us what is moving, where it is going and when it needs to happen. Our team will help you define the next step.', primary='Request a Free Quote'):
    return f'''<section class="sec" style="padding:20px 0 70px"><div class="wrap"><div class="cta-band"><div><h2>{h}</h2><p>{p}</p></div>
<div class="actions"><a class="btn btn-cta btn-lg" href="/request-a-quote/">{primary}</a><a class="btn btn-ghost btn-lg" href="tel:{PHONE_TEL}">Call {PHONE}</a></div></div></div></section>'''

# ---------------------------------------------------------------- shared data
TESTIMONIALS = [
    ('BRS provided service that was nothing short of amazing for all of my moves. The movers have always been attentive and extremely careful with all items that had to be carried down 3 flights of stairs and put onto a truck. Nothing was damaged and they handled themselves professionally. I would highly recommend!', 'Tom Lanzetta', 'Intent Media'),
    ('We have used BRS several times and all of their employees are friendly, professional and go above and beyond to make the moving experience stress free. We will always come back for their services. Highly recommended!', 'Jeff Russo', 'AT&T'),
    ('Customer service was excellent – over the phone very pleasant to deal with and understand my requests. The hand laborers were on time, friendly, and respectful. Will definitely recommend them!', 'Phil Alessi', 'NBC Universal'),
    ('I had the opportunity to solicit service from the BRS team in June 2020. Despite being in the middle of a pandemic, the BRS team made my move as easy and painless as possible, all while adhering to Covid-19 related restrictions. The company employs the best in the business that will treat everything they touch with respect. Lived up to their motto of ‘Consider It Done!’', 'Chris Blandy', 'PNC Bank'),
    ('BRS is professional, efficient, and trustworthy! Our needs were met in a polite and professional manner … from the owners to the staff. The team arrived on time, and worked quickly and smoothly. BRS provides a consistently positive attitude, attention to detail, and applies their expertise gained from years experience!', 'Megan Rochelle', 'SONY'),
    ('The movers at BRS are the definition of efficiency. Each of them more respectful and hardworking than the next. They tirelessly moved my entire office out East during the pandemic. All of them showed up in masks eager to get the job done. The organizational skill of this crew are second to NONE. One employee specifically, I think his name was Kyle anticipated every need and want I had. The staff and management were the key to my seamless transition. Consider. It. Done.', 'Caroline Strehle', 'Memorial Sloan Kettering Cancer Center'),
]
PROOF_IDX = [0, 1, 2, 4]  # testimonials that read well on any service page
TEAM = [
    ('Jesus Linares', 'President', 'cropped-Jesus-Linares-President-Business-Relocation-Services-Inc-1'),
    ('Matthew Linares', 'Vice President', 'cropped-Matthew-Linares-Vice-President'),
    ('Mark Lavin', 'Senior Project Manager', 'cropped-Mark-Lavin-Project-Manager-BRS-Business-Relocation-Services'),
    ('Jim Gargano', 'Senior Project Manager', 'cropped-Jim-Gargano-Project-Manager-BRS-Business-Relocation-Services'),
    ('Ann Roness', 'Controller, Accounting', 'Ann-Roness-BRS-Controller-Accounting'),
    ('Anthony Taranto', 'Director of Project Management', 'Anthony-Taranto-Director-of-Project-Management-BRS-Business-Relocation-Services-NYC'),
    ('Eric Miller', 'Senior Sales Manager', 'Eric-Miller-Senior-Sales-Manager-Business-Relocation-Services-BRS'),
]
CLIENT_LOGOS = [('ATT', 'AT&T'), ('Verizon', 'Verizon'), ('Comcast', 'Comcast'), ('n-b-c', 'NBC'), ('Telemundo', 'Telemundo'), ('Well-Fargo', 'Wells Fargo'),
                ('Time-Warner-Cable', 'Time Warner Cable'), ('quest-diagnostics-logo', 'Quest Diagnostics'), ('NYC-Health-Hospitals-logo', 'NYC Health + Hospitals'),
                ('Catholic-Charities-Archdiocese-of-New-York-logo', 'Catholic Charities Archdiocese of New York'), ('Lane-Office-Furniture-logo', 'Lane Office Furniture'), ('Evenson-Best-logo', 'Evenson Best')]
FAQ = [
    ('What areas do you serve?', 'Business Relocation Services moves companies throughout New York, New Jersey and Pennsylvania from our offices in Secaucus, NJ and New York, NY. Our corporate relocation project management services are available to clients anywhere in the US.'),
    ('What types of moves do you handle?', 'We handle all types of commercial relocation projects, including offices, warehouses and other commercial property, as well as schools, libraries, IT equipment, servers and data centers. Any move type and size, from planning through completion.'),
    ('How do I get a moving quote?', f'Use the online quote form (it takes about a minute) or call us at {PHONE}. Tell us about your current and destination locations, move date and the services you need, and we will follow up with your quote.'),
    ('Can you move IT equipment and data centers?', 'Yes. Our IT team can disconnect, reconnect, de/re-rack, package and provide direct secure transport for servers, computers and other electronics, and we plan and execute data center relocations and migrations.'),
    ('Do you offer storage, furniture installation and liquidation?', 'Yes. In addition to moving, we offer secure storage facilities, new office furniture installation and reconfiguration, furniture liquidation, space planning, office decommissioning and inventory control.'),
    ('How long has BRS been in business, and are you certified?', 'Business Relocation Services was established in 1987 and is well known in both corporate and government circles. BRS is a certified Minority and Women-Owned Business Enterprise (MWBE) and a member of the National Hispanic Business Group, IFMA and CoreNet.'),
]


def faq_html(faq):
    return '<div class="faq">' + ''.join(f'<details><summary>{esc(f["q"])}</summary><p>{esc(f["a"])}</p></details>' for f in faq) + '</div>'


def quote_block(i):
    q, n, c = TESTIMONIALS[i]
    return f'<figure class="quote"><blockquote><p>“{esc(q)}”</p></blockquote><figcaption><cite>{esc(n)}<span>{esc(c)}</span></cite></figcaption></figure>'


def loc_card(a):
    q = f'Business Relocation Services {a[1]}, {a[2]}, {a[3]} {a[4]}'
    return f'''<div class="loc"><h3>{a[0]}</h3><address>{a[1]}<br>{a[2]}, {a[3]} {a[4]}</address><p style="margin:0"><a class="btn btn-outline" href="https://www.google.com/maps/search/?api=1&amp;query={quote(q)}" target="_blank" rel="noopener noreferrer">Get directions<span class="sr-only"> to the {a[0]} office (opens in a new tab)</span></a></p></div>'''


def logos_row():
    return ''.join(img(i, alt=a, sizes='120px') for i, a in CLIENT_LOGOS)

# ---------------------------------------------------------------- pages
built = []


def build_home():
    svcs = [
        ('Office movers', 'With so few organizations taking on the additional projects that arise during office relocations, why not work with skilled professionals who do it all? BRS brings you detail-oriented management for all needs associated with moving your commercial space.', '/office-movers/', 'Explore office moving services'),
        ('Corporate relocation', 'Whether it’s assisting, coordinating with your voice and data providers, compiling furniture and equipment inventories, or the myriad other details that surface when moving a work space, we work to ensure a successful project. These services are available to clients anywhere in the US.', '/business-relocation-services-in-new-york/', 'Explore business relocation services'),
        ('Moving IT equipment', 'BRS can disconnect, reconnect, de/re-rack, package and provide direct secure transport services. Our IT team carefully and efficiently moves all of your electronics, always putting precision first.', '/moving-it-equipment-in-new-york/', 'Explore IT equipment moving'),
        ('Office furniture installation', 'Furniture installation is one of the most important parts of your office furniture project. We help you plan and organize new installations or reconfigure your current office space.', '/furniture-installation/', 'Explore furniture installation'),
        ('Secure storage facilities', 'Security is one of the most important factors in a storage facility. Our years of experience in moving and storage are focused on giving you confidence in the way your belongings are handled.', '/storage-facilities/', 'Explore storage facilities'),
        ('Nationwide relocation specialist', 'BRS goes far beyond basic relocation services. From new furniture purchasing to liquidation, project management and the move itself, one team can handle the whole project.', f'/{ABOUT}/', 'About how BRS works'),
    ]
    svc_html = ''.join(f'<article class="svc"><h3>{t}</h3><p>{d}</p><a class="more" href="{u}">{l}</a></article>' for t, d, u, l in svcs)
    feat = [
        ('Rent-Moving-Crates-in-New-York-Business-Relocation-Services', 'Rent eco-friendly crates', 'Whether you’re moving a small office, classrooms or an entire corporate floor, rented moving crates keep your items protected from start to finish. They suit short-term in-house projects such as renovations, clean-outs, re-stacks and staff shifts.', '/rent-moving-crates/', 'Explore moving crate rentals'),
        ('Business-Relocation-Services-Team', 'School moving services', 'Relocating a school takes careful planning, experienced coordination and specialized equipment. We help educational institutions of all sizes make a smooth, organized transition.', '/school-moving-services/', 'Explore school moving services'),
        ('Library-Cart-Rental-for-Libraries-and-Institutions-Business-relocation-Services-New-York', 'Library cart rental', 'If your library, school or archive needs reliable library cart rental in New York, our team will guide you through the rental process and recommend the right solution.', '/library-cart-rental/', 'Explore library cart rental'),
    ]
    feat_html = ''.join(f'<article class="feature">{img(i, alt="", sizes="(max-width: 760px) 100vw, 380px")}<h3>{t}</h3><p>{d}</p><a class="more" href="{u}">{l}</a></article>' for i, t, d, u, l in feat)
    tests = ''.join(quote_block(i) for i in range(len(TESTIMONIALS)))
    team = ''.join(f'<div class="person">{img(i, alt=f"{n}, {r}", sizes="220px")}<b>{n}</b><span>{r}</span></div>' for n, r, i in TEAM)
    certs = ''.join(f'<figure>{img(i, alt=a, sizes="230px")}<figcaption>{a.split(" certif")[0]}</figcaption></figure>' for i, a in CERT_IMGS)
    latest = [p for p in ['office-relocation', 'moving-and-storage-company', 'office-it-relocation-services'] if p in POSTS]
    steps = [('Assess', 'A seasoned project manager evaluates your space, inventory, IT and timeline to scope the move.'),
             ('Plan', 'We build a detailed move plan with schedules, floor plans and coordination with building management and vendors.'),
             ('Coordinate', 'We work with your voice and data providers, furniture vendors and your staff so your team can keep doing their day jobs.'),
             ('Execute', 'Our trained crews move, install and set up, with monitoring through completion. “Consider it done!”')]
    steps_html = ''.join(f'<li class="step"><h3>{t}</h3><p>{d}</p></li>' for t, d in steps)
    body = f'''
<section class="hero"><div class="wrap">
<div><p class="eyebrow">Commercial moving and relocation since 1987</p>
<h1>Office movers and business relocation specialists in NYC</h1>
<p class="lead">BRS is a facility relocation project management and moving services company, all in one. From the smallest details to the most complex changes, we move offices, warehouses and commercial property while your business keeps running.</p>
<div class="hero-actions"><a class="btn btn-cta btn-lg" href="/request-a-quote/">Request a Free Quote</a><a class="btn btn-outline btn-lg" href="tel:{PHONE_TEL}">Call {PHONE}</a></div>
<ul class="ticks"><li>Free quote and moving consultation</li><li>Trusted by corporate and government clients</li><li>Certified Minority and Women-Owned Business (MWBE)</li></ul></div>
<div class="qcard" id="quote"><h2>Get your free quote</h2><p class="sub">Tell us about your move and we’ll follow up. Fields marked <span aria-hidden="true">*</span><span class="sr-only">with an asterisk</span> are required.</p>{quick_form()}</div>
</div>
<div class="wrap hero-photo">{img('BRS-Business-Relocation-Services', alt='View over Manhattan from an empty office floor, ready for a move', eager=True, sizes='(max-width: 1200px) 100vw, 1160px')}</div></section>
<section class="trust" aria-label="Clients"><div class="wrap"><p>Trusted by corporations, city agencies and non-profits</p><div class="logos">{logos_row()}</div></div></section>
<div class="wrap"><div class="facts">
<div class="fact"><b>1987</b><span>Established; more than 35 years of experience</span></div>
<div class="fact"><b>3 states</b><span>New York, New Jersey and Pennsylvania</span></div>
<div class="fact"><b>MWBE</b><span>Certified Minority and Women-Owned Business Enterprise</span></div>
<div class="fact"><b>1 team</b><span>Project management and moving under one roof</span></div></div></div>

<section class="sec" id="services"><div class="wrap"><div class="sec-head"><h2>Business Relocation Services specializes in all types of relocation projects</h2>
<p>We help with the transfer of your business from the smallest details to the most complex changes: offices, warehouses or any type of commercial property.</p></div>
<div class="svc-list">{svc_html}</div>
<div class="feature-row">{feat_html}</div>
</div></section>

<section class="sec soft"><div class="wrap split"><div><h2>A project manager who keeps your business moving</h2>
<p>The basic requirement is the knowledge of a seasoned project manager who knows how to assess, plan, coordinate, monitor and execute. The benefit is a return on investment: the project manager’s experience lets your staff do their daily duties and your company operate without interruption.</p>
<ul class="checklist"><li>Detail-oriented management for everything associated with moving your commercial space</li><li>Coordination with voice and data providers, furniture vendors and building management</li><li>Furniture purchasing, liquidation, installation and storage under one roof</li><li>Well known in both corporate and government circles since 1987</li></ul>
<p><a class="more" href="/{ABOUT}/">About how BRS works</a></p></div>
<div>{img('BRS-Business-Relocation-Services_Moment-04', alt='Aerial view of warehouses with the New York skyline in the distance', sizes='(max-width: 760px) 100vw, 560px')}</div></div></section>

<section class="sec"><div class="wrap"><div class="sec-head"><h2>How a move works with BRS</h2><p>Our process is built around a seasoned project manager who assesses, plans, coordinates and executes your relocation.</p></div>
<ol class="steps">{steps_html}</ol></div></section>

<section class="sec soft"><div class="wrap"><div class="sec-head"><h2>Don’t take our word for it</h2><p>Here’s what our clients say.</p></div>
<div class="reviews">{tests}</div></div></section>

<section class="sec" style="padding-bottom:0"><div class="wrap"><div class="cta-band"><div><h2>Do you need help with your business move?</h2><p>We are a full-service moving company. Request a quote and a moving consultation.</p></div>
<div class="actions"><a class="btn btn-cta btn-lg" href="/request-a-quote/">Talk to a relocation specialist</a><a class="btn btn-ghost btn-lg" href="tel:{PHONE_TEL}">Call {PHONE}</a></div></div></div></section>

<section class="sec"><div class="wrap"><div class="sec-head"><h2>Our executive team</h2><p>Each member of our team is a specialist in their field: highly qualified, experienced and knowledgeable professionals who are dedicated to our clients.</p></div>
<div class="team">{team}</div></div></section>

<section class="sec soft"><div class="wrap"><div class="sec-head center"><h2>Certified Minority and Women-Owned Business</h2>
<p>BRS is a certified MWBE and a member of the National Hispanic Business Group, International Facility Managers Association (IFMA) and CoreNet.</p></div>
<div class="certs">{certs}</div><p class="members"><span>National Hispanic Business Group</span><span>IFMA</span><span>CoreNet</span></p>
<p style="text-align:center;margin-top:30px"><a class="btn btn-outline" href="/mbe-minority-business-enterprise-certification/">About our certifications</a></p></div></section>

<section class="sec"><div class="wrap"><div class="sec-head"><h2>Questions about moving your business</h2></div>{faq_html([{"q": q, "a": a} for q, a in FAQ])}</div></section>

<section class="sec soft"><div class="wrap"><div class="sec-head"><h2>Latest from our blog</h2><p>Office relocation advice from the pros.</p></div>
<div class="grid g3">{''.join(post_card(p) for p in latest)}</div><p style="margin-top:36px"><a class="btn btn-outline" href="/blog/">Read all articles</a></p></div></section>

<section class="sec"><div class="wrap"><div class="sec-head"><h2>Two locations to serve you</h2><p>Serving New York, New Jersey and Pennsylvania since 1987.</p></div>
<div class="grid g2">{''.join(loc_card(a) for a in ADDR)}</div></div></section>
{cta_band()}'''
    schema = graph(
        org_schema(),
        {'@type': 'WebSite', '@id': SITE + '/#website', 'url': SITE + '/', 'name': 'Business Relocation Services', 'publisher': org_ref(), 'inLanguage': 'en-US'},
        {'@type': 'WebPage', '@id': SITE + '/#webpage', 'url': SITE + '/', 'name': 'Office Movers & Business Relocation Services in NYC | BRS', 'isPartOf': {'@id': SITE + '/#website'}, 'about': org_ref()},
        faq_schema([{'q': q, 'a': a} for q, a in FAQ]))
    built.append(page('/', 'Office Movers & Business Relocation Services in NYC | BRS',
                      'Commercial office movers and business relocation specialists serving NYC, New Jersey and Pennsylvania since 1987. IT moves, furniture and storage. Free quotes.',
                      body, current='home', schema=schema))


def post_meta(slug):
    c = CONTENT[f'{SITE}/{slug}/']
    lines = clean_lines(c['text'])
    first_h = None
    for ln in lines:
        m = re.match(r'^#{1,6}\s*(.*)$', ln)
        if m and m.group(1).strip():
            first_h = caps_fix(m.group(1))
        break
    title = first_h or sweep(short_title(c['title']))
    paras = [l for l in lines if not l.startswith('#') and len(l) > 80]
    return dict(slug=slug, title=title, excerpt=clip(paras[0] if paras else c['desc'], 170),
                img=local_img(c['imgs'][0]) if c['imgs'] else None, date=c['date'][:10], first_h=first_h)


def fmt_date(d):
    return datetime.date.fromisoformat(d).strftime('%B %-d, %Y')


def post_card(slug):
    m = post_meta(slug)
    im = img(m['img'], alt='', sizes='(max-width: 760px) 100vw, 380px') if m['img'] else ''
    return f'''<article class="card card-img post-card">{im}<div class="body"><div class="meta"><time datetime="{m['date']}">{fmt_date(m['date'])}</time></div><h3><a href="/{slug}/">{esc(m['title'])}</a></h3><p>{esc(m['excerpt'])}</p><a class="more" href="/{slug}/" aria-label="Read the article: {esc(m['title'])}">Read the article</a></div></article>'''


def svc_card(s):
    d = SVC_DATA[s]
    return f'<article class="card"><h3><a href="/{s}/">{esc(SV[s][1])}</a></h3><p>{esc(d["card_blurb"])}</p><a class="more" href="/{s}/">{esc(d["link_text"])}</a></article>'


def side_card():
    return f'''<aside class="side"><div class="qcard"><h2 class="side-h">Plan your move</h2><p class="sub">Tell us what is moving, where and when.</p>
<a class="btn btn-cta btn-block btn-lg" href="/request-a-quote/">Request a Free Quote</a>
<p style="margin:1em 0 .2em;text-align:center;font-size:.9rem;color:var(--muted)">or call us</p><a class="phone-big" style="text-align:center" href="tel:{PHONE_TEL}">{PHONE}</a>
<ul class="ticks"><li>Serving clients since 1987</li><li>Certified MWBE</li><li>New York, New Jersey and Pennsylvania</li></ul></div></aside>'''


def build_service(slug):
    d = SVC_DATA[slug]
    nav = SV[slug][1]
    crumb = [('Home', '/'), ('Services', '/our-services/'), (nav, f'/{slug}/')]
    src = CONTENT[f'{SITE}/{slug}/']
    fig = next((i for i in (local_img(u) for u in src['imgs']) if i and (dims(i) or (0, 0))[0] >= 640 and not any(k in i.lower() for k in ('logo', 'staff', 'employ'))), None)
    benefits = ''.join(f'<li><h3>{esc(b["title"])}</h3><p>{esc(b["text"])}</p></li>' for b in d['benefits'])
    included = ''.join(f'<li>{esc(x)}</li>' for x in d['included'])
    steps = ''.join(f'<li class="step"><h3>{esc(s["title"])}</h3><p>{esc(s["text"])}</p></li>' for s in d['process'])
    who = ''.join(f'<li>{esc(x)}</li>' for x in d['who_for'])
    overview = ''.join(f'<p>{esc(p)}</p>' for p in d['overview'])
    figure = f'<figure>{img(fig, alt="", cap=True, sizes="(max-width: 760px) 100vw, 700px")}</figure>' if fig else ''
    proof = quote_block(PROOF_IDX[sum(map(ord, slug)) % len(PROOF_IDX)])
    related = ''.join(svc_card(r) for r in d['related'][:3])
    body = f'''<section class="page-hero"><div class="wrap">{crumbs_html(crumb)}<h1>{esc(d['h1'])}</h1><p class="lead">{esc(d['lead'])}</p>
<div class="hero-actions"><a class="btn btn-cta btn-lg" href="/request-a-quote/">Request a Free Quote</a><a class="btn btn-outline btn-lg" href="tel:{PHONE_TEL}">Call {PHONE}</a></div></div></section>
<div class="wrap layout"><div class="prose">
{overview}{figure}
<h2>Why choose BRS</h2><ul class="benefits">{benefits}</ul>
<h2>What is included</h2><ul>{included}</ul>
<h2>How it works</h2><ol class="steps steps-compact">{steps}</ol>
{inline_cta('Talk to a relocation specialist about your project.')}
<h2>Who this is for</h2><ul>{who}</ul>
<h2>What clients say</h2>{proof}
<h2>Frequently asked questions</h2>{faq_html(d['faq'])}
</div>{side_card()}</div>
<section class="sec soft"><div class="wrap"><div class="sec-head"><h2>Related services</h2></div><div class="grid g3">{related}</div></div></section>
{cta_band()}'''
    schema = graph(crumbs(crumb),
                   {'@type': 'WebPage', '@id': f'{SITE}/{slug}/#webpage', 'url': f'{SITE}/{slug}/', 'name': d['meta_title'], 'isPartOf': {'@id': SITE + '/#website'}},
                   {'@type': 'Service', 'name': d['h1'], 'description': d['lead'], 'url': f'{SITE}/{slug}/', 'serviceType': nav, 'provider': org_ref(),
                    'areaServed': [{'@type': 'State', 'name': n} for n in ('New York', 'New Jersey', 'Pennsylvania')]},
                   faq_schema(d['faq']), org_schema())
    built.append(page(f'/{slug}/', d['meta_title'], d['meta_description'], body, current='services', schema=schema))


def build_about():
    crumb = [('Home', '/'), ('About', f'/{ABOUT}/')]
    steps = [('Assess and scope', 'Walk the space, document inventory, confirm building requirements and identify risks.'),
             ('Plan and schedule', 'Build the move plan, phasing, staffing, equipment needs and communication timeline.'),
             ('Coordinate every party', 'Align facilities, building management, IT, furniture vendors and internal teams.'),
             ('Move, install and close out', 'Execute the move, complete installation, resolve the punch list and confirm completion.')]
    caps = [('Office and commercial moving', 'Planned office, warehouse and facility moves with packing, inventory reports and installation.', '/office-movers/', 'Explore office moving services'),
            ('IT and data center relocation', 'Disconnect, de/re-rack, transport and reconnect servers, computers and data center equipment.', '/data-center-relocation/', 'Explore data center relocation'),
            ('Furniture installation, liquidation and decommissioning', 'Install new or reconfigured workspaces, and clear out or liquidate furniture when you leave a space.', '/furniture-installation/', 'Explore furniture installation'),
            ('Storage, crates and inventory control', 'Secure storage, rented moving crates and inventory tracking for projects of any size.', '/storage-facilities/', 'Explore storage and inventory services')]
    team = ''.join(f'<div class="person">{img(i, alt=f"{n}, {r}", sizes="220px")}<b>{n}</b><span>{r}</span></div>' for n, r, i in TEAM)
    certs = ''.join(f'<figure>{img(i, alt=a, sizes="230px")}<figcaption>{a.split(" certif")[0]}</figcaption></figure>' for i, a in CERT_IMGS)
    body = f'''<section class="page-hero about-hero"><div class="wrap split">
<div>{crumbs_html(crumb)}<p class="eyebrow">Commercial moving and relocation since 1987</p>
<h1>Commercial relocation, managed from first walkthrough to final setup</h1>
<p class="lead">BRS plans and executes office, warehouse, school, furniture and technology moves across New York, New Jersey and Pennsylvania. One experienced team manages the schedule, vendors, equipment and installation so your business can keep moving.</p>
<div class="hero-actions"><a class="btn btn-cta btn-lg" href="/request-a-quote/">Request a Free Quote</a><a class="btn btn-outline btn-lg" href="tel:{PHONE_TEL}">Call {PHONE}</a></div>
<ul class="ticks inline"><li>Established 1987</li><li>Certified MWBE</li><li>NY, NJ and PA</li><li>Corporate and government experience</li></ul></div>
<div>{img('Office-Movers-BRS-Warehouse-location-Secaucus-NJ', alt='BRS moving trucks at the company’s warehouse', eager=True, sizes='(max-width: 760px) 100vw, 560px')}</div></div></section>
<section class="trust flush" aria-label="Clients"><div class="wrap"><p>Trusted by corporations, city agencies and non-profits</p><div class="logos">{logos_row()}</div></div></section>

<section class="sec"><div class="wrap split"><div><h2>One accountable team for the entire move</h2>
<p>Business relocation is more than trucks and boxes. It requires facilities planning, building coordination, IT sequencing, furniture installation, inventory control and a team that can adapt on moving day. BRS brings those disciplines together under one project manager, from initial scope through final closeout.</p>
<p>BRS was established in 1987 and is well known in both corporate and government circles. Our clients include corporations, small to large businesses, city agencies and non-profits.</p></div>
<div>{img('BRS-Business-Relocation-Services_Moment-04', alt='Aerial view of warehouses with the New York skyline in the distance', sizes='(max-width: 760px) 100vw, 560px')}</div></div></section>

<section class="sec soft"><div class="wrap"><div class="sec-head"><h2>How BRS manages a relocation</h2></div>
<ol class="steps">{''.join(f'<li class="step"><h3>{t}</h3><p>{x}</p></li>' for t, x in steps)}</ol></div></section>

<section class="sec"><div class="wrap"><div class="sec-head"><h2>Specialized support for complex commercial moves</h2></div>
<div class="grid g2">{''.join(f'<article class="card"><h3>{t}</h3><p>{x}</p><a class="more" href="{u}">{l}</a></article>' for t, x, u, l in caps)}</div></div></section>

<section class="sec soft"><div class="wrap"><div class="sec-head"><h2>Trusted when downtime is not an option</h2></div>
<div style="max-width:760px">{quote_block(4)}</div></div></section>

<section class="sec"><div class="wrap"><div class="sec-head"><h2>Leadership</h2><p>Each member of our team is a specialist in their field: highly qualified, experienced professionals who are dedicated to our clients.</p></div><div class="team">{team}</div></div></section>

<section class="sec soft"><div class="wrap"><div class="sec-head center"><h2>Certifications and memberships</h2>
<p>BRS is a certified MWBE and a member of the National Hispanic Business Group, International Facility Managers Association (IFMA) and CoreNet.</p></div>
<div class="certs">{certs}</div><p style="text-align:center;margin-top:30px"><a class="btn btn-outline" href="/mbe-minority-business-enterprise-certification/">About our certifications</a></p></div></section>

<section class="sec"><div class="wrap"><div class="sec-head"><h2>Two locations</h2><p>Offices in New Jersey and New York serve clients across the tri-state area.</p></div><div class="grid g2">{''.join(loc_card(a) for a in ADDR)}</div></div></section>
{cta_band()}'''
    schema = graph(crumbs(crumb),
                   {'@type': 'AboutPage', '@id': f'{SITE}/{ABOUT}/#webpage', 'url': f'{SITE}/{ABOUT}/', 'name': 'About BRS', 'isPartOf': {'@id': SITE + '/#website'}, 'about': org_ref(), 'mainEntity': org_ref()},
                   org_schema())
    built.append(page(f'/{ABOUT}/', 'About BRS | Commercial Relocation Experts Since 1987',
                      'Meet Business Relocation Services, a certified MWBE providing project-managed office, furniture and technology moves across NY, NJ and PA since 1987.',
                      body, current='about', schema=schema))


def build_hub():
    crumb = [('Home', '/'), ('Services', '/our-services/')]
    groups = ''.join(f'<h2 class="group-h">{g}</h2><div class="grid g3">{"".join(svc_card(s[0]) for s in SERVICES if s[4] == g)}</div>' for g in GROUPS)
    body = f'''<section class="page-hero"><div class="wrap">{crumbs_html(crumb)}<h1>Commercial moving and relocation services</h1>
<p class="lead">We move companies. With the experience, resources and a central location serving New York, New Jersey and Pennsylvania, we manage relocations of any type and size from planning to completion. We also offer furniture decommissioning, warehousing, delivery and installation.</p>
<div class="hero-actions"><a class="btn btn-cta btn-lg" href="/request-a-quote/">Request a Free Quote</a><a class="btn btn-outline btn-lg" href="tel:{PHONE_TEL}">Call {PHONE}</a></div></div></section>
<section class="sec"><div class="wrap">{groups}</div></section>{cta_band()}'''
    schema = graph(crumbs(crumb), {'@type': 'CollectionPage', 'name': 'BRS services', 'url': SITE + '/our-services/', 'isPartOf': {'@id': SITE + '/#website'}, 'about': org_ref()},
                   {'@type': 'ItemList', 'itemListElement': [{'@type': 'ListItem', 'position': i + 1, 'name': s[1], 'url': f'{SITE}/{s[0]}/'} for i, s in enumerate(SERVICES)]}, org_schema())
    built.append(page('/our-services/', 'Commercial Moving & Relocation Services | BRS',
                      'Office moving, IT and data center relocation, furniture installation, storage and more from one project-managed team serving NY, NJ and PA.',
                      body, current='services', schema=schema))


def build_mbe():
    slug = 'mbe-minority-business-enterprise-certification'
    d = MBE_DATA
    crumb = [('Home', '/'), ('About', f'/{ABOUT}/'), ('Certifications', f'/{slug}/')]
    secs = ''.join(f'<h2>{esc(s["h2"])}</h2>' + ''.join(f'<p>{esc(p)}</p>' for p in s['paras']) for s in d['sections'])
    figs = ''.join(f'<figure>{img(i, alt=a, sizes="230px")}<figcaption>{a}</figcaption></figure>' for i, a in CERT_IMGS)
    body = f'''<section class="page-hero"><div class="wrap">{crumbs_html(crumb)}<h1>{esc(d['h1'])}</h1><p class="lead">{esc(d['lead'])}</p></div></section>
<div class="wrap layout"><div class="prose">{secs}<h2>Our certificates</h2><div class="certs left">{figs}</div>
<p><a href="https://sbsconnect.nyc.gov/certification-directory-search/" target="_blank" rel="noopener noreferrer">Search the NYC Online Directory of Certified Businesses<span class="sr-only"> (opens in a new tab)</span></a></p></div>{side_card()}</div>{cta_band()}'''
    built.append(page(f'/{slug}/', d['meta_title'], d['meta_description'], body, current='about',
                      schema=graph(crumbs(crumb), {'@type': 'WebPage', 'name': d['h1'], 'url': f'{SITE}/{slug}/', 'isPartOf': {'@id': SITE + '/#website'}, 'about': org_ref()}, org_schema())))


def build_post(slug):
    c = CONTENT[f'{SITE}/{slug}/']
    m = post_meta(slug)
    blocks = parse_blocks(clean_lines(c['text']))
    imgs = [i for i in (local_img(u) for u in c['imgs'][1:]) if i and (dims(i) or (0, 0))[0] >= 640 and not any(k in i.lower() for k in ('logo', 'staff', 'employ'))]
    prose = render_prose(blocks, imgs[:3], cta_after=3, drop_first_heading=m['first_h'])
    crumb = [('Home', '/'), ('Blog', '/blog/'), (m['title'], f'/{slug}/')]
    more = ''.join(post_card(p) for p in [p for p in POSTS if p != slug][:3])
    feat = img(m['img'], alt='', eager=True, cls='feature', cap=True, sizes='(max-width: 840px) 100vw, 780px') if m['img'] else ''
    body = f'''<section class="page-hero"><div class="wrap">{crumbs_html(crumb)}<h1>{esc(m['title'])}</h1><p class="lead"><time datetime="{m['date']}">{fmt_date(m['date'])}</time> &middot; Business Relocation Services</p></div></section>
<div class="wrap"><article class="article prose">{feat}{prose}{inline_cta('Planning a move? Talk to our relocation team.')}</article></div>
<section class="sec soft"><div class="wrap"><div class="sec-head"><h2>More from the BRS blog</h2></div><div class="grid g3">{more}</div></div></section>'''
    title = (m['title'] if len(m['title']) <= 56 else sweep(short_title(c['title']))) + ' | BRS'
    desc = sweep(c['desc']) if 70 <= len(c['desc']) <= 160 else m['excerpt']
    schema = graph(crumbs(crumb), {'@type': 'BlogPosting', 'headline': m['title'][:110], 'description': m['excerpt'], 'datePublished': m['date'], 'dateModified': m['date'],
                                   'image': f"{SITE}/assets/img/{m['img']}" if m['img'] else SITE + '/assets/og-default.jpg',
                                   'author': org_ref(), 'publisher': org_ref(), 'mainEntityOfPage': f'{SITE}/{slug}/'}, org_schema())
    og = f"/assets/img/{m['img']}" if m['img'] and dims(m['img'])[0] >= 1200 else None
    built.append(page(f'/{slug}/', title, desc, body, current='blog', og_img=og, schema=schema))


def build_blog_index():
    ps = sorted((post_meta(p) for p in POSTS), key=lambda m: m['date'], reverse=True)
    crumb = [('Home', '/'), ('Blog', '/blog/')]
    body = f'''<section class="page-hero"><div class="wrap">{crumbs_html(crumb)}<h1>Office relocation and moving advice</h1><p class="lead">Tips, checklists and insight on office moves, IT relocation, furniture and recycling from the team at Business Relocation Services.</p></div></section>
<section class="sec"><div class="wrap"><h2 class="sr-only">All articles</h2><div class="grid g3">{''.join(post_card(m['slug']) for m in ps)}</div></div></section>{cta_band()}'''
    built.append(page('/blog/', 'Blog | Office Relocation & Moving Tips | BRS',
                      'Office relocation tips, move checklists and commercial moving advice for NYC, NJ and PA businesses from Business Relocation Services.',
                      body, current='blog', schema=graph(crumbs(crumb), {'@type': 'Blog', 'name': 'BRS blog', 'url': SITE + '/blog/', 'publisher': org_ref()})))


def build_quote():
    crumb = [('Home', '/'), ('Request a Quote', '/request-a-quote/')]
    body = f'''<section class="page-hero"><div class="wrap">{crumbs_html(crumb)}<h1>Request a free moving quote</h1><p class="lead">Tell us what is moving, where it is going and when. We will follow up with your quote as soon as possible.</p></div></section>
<div class="wrap layout"><div>{full_quote_form()}</div>
<aside class="side"><div class="qcard"><h2 class="side-h">Prefer to talk?</h2><p class="sub">Call us and speak with our team directly.</p><a class="phone-big" href="tel:{PHONE_TEL}">{PHONE}</a>
<p style="margin:0"><a href="mailto:{EMAIL}">{EMAIL}</a></p></div>
<div class="side-list"><h2 class="side-h">Why businesses choose BRS</h2><ul class="checklist" style="margin:.6em 0 0"><li>Serving clients since 1987</li><li>Certified MWBE</li><li>Moving, IT, furniture and storage under one roof</li><li>A project manager on every move</li></ul></div>
{quote_block(1)}</aside></div>'''
    built.append(page('/request-a-quote/', 'Request a Free Moving Quote | Business Relocation Services',
                      'Request a free commercial moving quote from Business Relocation Services. Office, IT, school and warehouse moves across NYC, NJ and PA. Call 1-718-399-8000.',
                      body, current='quote', schema=graph(crumbs(crumb), {'@type': 'WebPage', 'name': 'Request a quote', 'url': SITE + '/request-a-quote/', 'about': org_ref()}, org_schema())))


def build_contact():
    slug = 'contact-brs-business-relocation-services-new-york-new-jersey'
    crumb = [('Home', '/'), ('Contact', f'/{slug}/')]
    body = f'''<section class="page-hero"><div class="wrap">{crumbs_html(crumb)}<h1>Contact Business Relocation Services</h1><p class="lead">Questions about a relocation? Call, email or send a message and our team will get back to you. For pricing, the quote form is the fastest route.</p></div></section>
<div class="wrap layout"><div><h2>Send us a message</h2><p class="sub">Fields marked <span aria-hidden="true">*</span><span class="sr-only">with an asterisk</span> are required.</p>{small_form('contact', '/thank-you-contact-form/', 'Contact form')}</div>
<aside class="side"><div class="qcard"><h2 class="side-h">Call us</h2><a class="phone-big" href="tel:{PHONE_TEL}">{PHONE}</a><h2 class="side-h">Email</h2><p style="margin:0"><a href="mailto:{EMAIL}">{EMAIL}</a></p></div>
<div class="qcard"><h2 class="side-h">Need pricing?</h2><p class="sub">Tell us about your move and request a free quote.</p><a class="btn btn-cta btn-block" href="/request-a-quote/">Request a Free Quote</a></div></aside></div>
<section class="sec soft"><div class="wrap"><div class="sec-head"><h2>Visit us</h2></div><div class="grid g2">{''.join(loc_card(a) for a in ADDR)}</div></div></section>'''
    built.append(page(f'/{slug}/', 'Contact BRS | Office Movers in NYC, NJ & PA',
                      'Contact Business Relocation Services: call 1-718-399-8000 or email info@brsmove.com. Offices in Secaucus, NJ and New York, NY.',
                      body, current='contact', schema=graph(crumbs(crumb), {'@type': 'ContactPage', 'name': 'Contact BRS', 'url': f'{SITE}/{slug}/', 'about': org_ref()}, org_schema())))


def build_careers():
    crumb = [('Home', '/'), ('Careers', '/careers/')]
    extra = fld('cr-pos', 'Position of interest', 'Position')
    body = f'''<section class="page-hero"><div class="wrap">{crumbs_html(crumb)}<h1>Career opportunities at BRS</h1><p class="lead">BRS is a family of movers, project managers, office staff, truck drivers, mechanics, consultants, supervisors and foremen who share one goal: to get the job done as safely, as quickly and as professionally as possible.</p></div></section>
<div class="wrap layout"><div class="prose"><h2>Interested in joining our team?</h2><p>Looking for a job with career potential? Send us a note with your details and the role you are interested in, and our team will follow up with next steps. You can also email your resume to <a href="mailto:{EMAIL}">{EMAIL}</a>.</p>
<p><em>Business Relocation Services is an equal opportunity employer and does not discriminate on the basis of race, color, religion (creed), gender, gender expression, age, national origin (ancestry), disability, marital status, sexual orientation or military status in any of its activities or operations.</em></p>
<div style="margin-top:2em">{small_form('careers', '/thank-you-job-application/', 'Job inquiry', extra, 'Send application inquiry', 'cr')}</div></div>{side_card()}</div>'''
    built.append(page('/careers/', 'Careers at BRS | Movers & Project Manager Jobs NJ/NY',
                      'Join the BRS family of movers, project managers, drivers and supervisors. Apply for career opportunities with Business Relocation Services.',
                      body, current='careers', schema=graph(crumbs(crumb), org_schema())))


def build_thanks():
    for slug in ['thank-you-contact-form', 'thank-you-request-a-quote', 'thank-you-job-application']:
        body = f'''<section class="sec"><div class="wrap" style="max-width:720px"><h1>Thank you</h1>
<p style="font-size:1.2rem">Your message has been sent. We appreciate you contacting Business Relocation Services and will get back to you as soon as possible.</p>
<p>Need immediate assistance? Call <a href="tel:{PHONE_TEL}"><b>{PHONE}</b></a>.</p>
<p style="margin-top:2em"><a class="btn btn-cta btn-lg" href="/">Back to home</a> <a class="btn btn-outline btn-lg" href="/our-services/">Explore our services</a></p></div></section>'''
        built.append(page(f'/{slug}/', 'Thank You | Business Relocation Services', 'Thank you for contacting Business Relocation Services.', body, noindex=True))


def build_404():
    links = ''.join(f'<li><a href="/{s[0]}/">{esc(s[1])}</a></li>' for s in SERVICES[:8])
    body = f'''<section class="sec"><div class="wrap" style="max-width:720px"><h1>Page not found</h1><p style="font-size:1.15rem">Sorry, we couldn’t find that page. The page may have moved, or the link may be mistyped. Try one of these instead:</p>
<p><a class="btn btn-cta btn-lg" href="/request-a-quote/">Request a Free Quote</a> <a class="btn btn-outline btn-lg" href="/our-services/">All services</a> <a class="btn btn-outline btn-lg" href="/">Home</a></p>
<h2 style="margin-top:1.6em">Popular services</h2><ul class="plain-list">{links}</ul></div></section>'''
    fp = page('/404/', 'Page Not Found | Business Relocation Services', 'Page not found.', body, noindex=True)
    shutil.move(fp, os.path.join(ROOT, '404.html'))
    shutil.rmtree(os.path.join(ROOT, '404'))


def build_seo_files():
    urls = ['/', '/our-services/', '/request-a-quote/', f'/{ABOUT}/', '/blog/', '/careers/', '/contact-brs-business-relocation-services-new-york-new-jersey/',
            '/mbe-minority-business-enterprise-certification/'] + [f'/{s[0]}/' for s in SERVICES] + [f'/{p}/' for p in POSTS]
    prio = lambda u: '1.0' if u == '/' else '0.9' if u in ('/request-a-quote/', '/office-movers/', '/our-services/', f'/{ABOUT}/') else '0.8' if u[1:-1] in SV else '0.6'
    open(os.path.join(ROOT, 'sitemap.xml'), 'w').write('<?xml version="1.0" encoding="UTF-8"?>\n<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">\n' + ''.join(
        f'<url><loc>{SITE}{u}</loc><lastmod>{TODAY}</lastmod><priority>{prio(u)}</priority></url>\n' for u in urls) + '</urlset>\n')
    open(os.path.join(ROOT, 'robots.txt'), 'w').write(f'User-agent: *\nAllow: /\nDisallow: /thank-you-\n\nSitemap: {SITE}/sitemap.xml\n')
    red = '# Permanent redirects for near-duplicate legacy URLs (consolidated into the page that owns the topic)\n'
    for old, new in REDIRECTS.items():
        red += f'/{old}/  /{new}/  301!\n/{old}  /{new}/  301!\n'
    open(os.path.join(ROOT, '_redirects'), 'w').write(red)
    return len(urls)


def main():
    for old in REDIRECTS:
        shutil.rmtree(os.path.join(ROOT, old), ignore_errors=True)
    build_home(); build_about(); build_hub(); build_mbe()
    for s in SERVICES:
        build_service(s[0])
    for p in POSTS:
        build_post(p)
    build_blog_index(); build_quote(); build_contact(); build_careers(); build_thanks(); build_404()
    print(f'built {len(built)} pages, {build_seo_files()} sitemap urls')


if __name__ == '__main__':
    main()
