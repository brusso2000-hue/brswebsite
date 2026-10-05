#!/usr/bin/env python3
"""Static site generator for brsmove.com.

Reads tools/content.json (text scraped from the previous WordPress site, so every
original URL and paragraph carries over) and writes plain HTML into the repo root.

    python3 tools/build.py

To send quote-form submissions to a form service (Formspree, FormSubmit, Netlify...),
set FORM_ENDPOINT below. While empty, forms open the visitor's email app addressed
to FORM_MAILTO instead.
"""
import html, json, os, re, shutil, datetime
from PIL import Image

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SITE = 'https://brsmove.com'
FORM_ENDPOINT = ''            # e.g. 'https://formspree.io/f/xxxxxxx'
FORM_MAILTO = 'info@brsmove.com'
PHONE = '1-718-399-8000'
PHONE_TEL = '+17183998000'
EMAIL = 'info@brsmove.com'
TODAY = datetime.date.today().isoformat()
CONTENT = json.load(open(os.path.join(ROOT, 'tools/content.json')))
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
esc = html.escape

# ---------------------------------------------------------------- services
# slug, nav name, h1, one-line description, group
SERVICES = [
    ('office-movers', 'Office Movers', 'Office Movers in NYC, NJ & PA',
     'Professional commercial movers for offices of every size, with careful packing, loading and unloading.', 'Moving & Relocation'),
    ('moving-management', 'Moving Management', 'Move Management Services',
     'Dedicated project managers who plan, coordinate and monitor every detail of your relocation.', 'Moving & Relocation'),
    ('move-planner', 'Move Planner', 'Office Relocation Planner & Move Checklist',
     'A step-by-step planner and checklist so nothing is missed before, during or after moving day.', 'Moving & Relocation'),
    ('office-decommissioning', 'Office Decommissioning', 'Office Decommissioning Services',
     'Systematic removal of furniture, equipment and fixtures when you vacate a space.', 'Moving & Relocation'),
    ('school-moving-services', 'School Moving Services', 'School Moving Services',
     'Organized, stress-free relocations for public and private schools and educational facilities.', 'Moving & Relocation'),
    ('business-relocation-services-in-new-york', 'Relocation Services', 'Business Relocation Services in New York',
     'Complete relocation project management for offices, warehouses and commercial property.', 'Moving & Relocation'),
    ('furniture-installation', 'Furniture Installation', 'Office Furniture Installation',
     'Plan, organize and install new or reconfigured office furniture and workstations.', 'Furniture & Space'),
    ('furniture-liquidation', 'Furniture Liquidation', 'Office Furniture Liquidation',
     'Get the best value for used office furniture when you downsize, move or upgrade.', 'Furniture & Space'),
    ('space-planning', 'Space Planning', 'Office Space Planning',
     'Organize space, furniture and function for an efficient, productive workplace.', 'Furniture & Space'),
    ('inventory-control', 'Inventory Control', 'Inventory Control & Management',
     'Track and manage furniture and equipment inventory through every stage of a move.', 'Furniture & Space'),
    ('moving-it-equipment-in-new-york', 'Moving IT Equipment', 'Moving IT Equipment in New York',
     'Disconnect, reconnect, de/re-rack, package and securely transport your IT equipment.', 'IT & Technology'),
    ('computer-moving', 'Computer Moving', 'Computer Moving Services',
     'Precision computer and workstation moves handled by our experienced IT team.', 'IT & Technology'),
    ('server-moving-computer-relocation', 'Server Moving', 'Server Moving & Computer Relocation',
     'Specially trained server movers for secure, careful equipment relocation.', 'IT & Technology'),
    ('data-center-relocation', 'Data Center Relocation', 'Data Center Relocation Services',
     'Plan and execute data center moves and migrations with minimal downtime.', 'IT & Technology'),
    ('it-equipment-recycling', 'IT Equipment Recycling', 'IT Equipment Recycling',
     'Responsible IT hardware recycling with secure data destruction.', 'IT & Technology'),
    ('computer-recycling', 'Computer Recycling', 'Business Computer Recycling',
     'Recycle outdated business computers responsibly and reduce your environmental impact.', 'IT & Technology'),
    ('storage-facilities', 'Storage Facilities', 'Secure Storage Facilities',
     'Secure, professionally managed storage for furniture, equipment and records.', 'Storage & Rentals'),
    ('rent-moving-crates', 'Rent Moving Crates', 'Rent Moving Crates in New York',
     'Durable, eco-friendly plastic crates for offices, schools and entire corporate floors.', 'Storage & Rentals'),
    ('library-cart-rental', 'Library Cart Rental', 'Library Cart Rental in New York',
     'Library cart rental with guidance on the right solution for libraries, schools and archives.', 'Storage & Rentals'),
]
GROUPS = ['Moving & Relocation', 'Furniture & Space', 'IT & Technology', 'Storage & Rentals']
SV = {s[0]: s for s in SERVICES}

# Pages that are not in the mega menu but keep their URL
EXTRA = {
    'business-relocation': ('About BRS', 'About Business Relocation Services',
        'Facility relocation project management and moving services in one company, serving corporate and government clients since 1987.'),
    'relocation-services-in-new-york': ('Relocation Services', 'Relocation Services in New York, New Jersey & Pennsylvania',
        'Commercial relocation across the tri-state area, planned and managed from start to finish.'),
    'relocation-services-business-moving-services': ('Moving Services', 'Relocation & Moving Services in New York',
        'The most comprehensive relocation management and restock management services in the industry.'),
    'office-movers-in-new-york': ('Office Movers in New York', 'Business Office Movers in New York',
        'Experienced Manhattan and NYC office movers for businesses, agencies and non-profits.'),
    'office-decommission-new-york': ('Office Decommission', 'Office Decommission in New York',
        'What office decommissioning involves and how we handle it for tenants in New York.'),
    'mbe-minority-business-enterprise-certification': ('Certifications', 'Minority & Women-Owned Business Enterprise Certifications',
        'BRS is a certified MWBE, listed in the NYC Online Directory of Certified Businesses.'),
    'our-services': ('Our Services', 'Our Relocation Services',
        'Office moves, IT relocation, furniture, storage and more, all from one experienced project team.'),
}

POSTS = [u.strip('/').split('/')[-1] for u in CONTENT if CONTENT[u]['text'].startswith('post-content-inner')]

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
    b = re.sub(r'[-_]+', ' ', b).strip()
    return b


def img(name, alt=None, cls='', lazy=True, sizes=None, eager=False):
    fn = name if name.endswith(('.webp', '.png')) else name + '.webp'
    d = dims(fn)
    if not d:
        return ''
    a = esc(alt if alt is not None else alt_from(fn))
    attrs = f'src="/assets/img/{fn}" alt="{a}" width="{d[0]}" height="{d[1]}"'
    if cls:
        attrs += f' class="{cls}"'
    attrs += ' decoding="async"' + ('' if eager else ' loading="lazy"')
    return f'<img {attrs}>'


def local_img(url):
    fn = os.path.splitext(os.path.basename(url))[0] + '.webp'
    return fn if os.path.exists(os.path.join(IMG_DIR, fn)) else None


def caps_fix(t):
    t = t.strip().replace('\xa0', ' ')
    if t.isupper() and len(t) > 3:
        out = []
        for w in t.split():
            bare = re.sub(r'[^A-Z0-9-]', '', w)
            out.append(w if bare in ACR else w.capitalize())
        t = ' '.join(out)
    return t


def clip(t, n):
    t = re.sub(r'\s+', ' ', t).strip()
    if len(t) <= n:
        return t
    t = t[:n].rsplit(' ', 1)[0].rstrip(',;:-')
    return t + '…'


def slug_url(slug):
    return '/' if slug == '' else f'/{slug}/'


def short_title(raw):
    parts = [p.strip() for p in re.split(r'\s+[-–|]\s+', raw)]
    parts = [p for p in parts if p and 'BRSmove' not in p and 'Business Relocation Services in New York, New Jersey' not in p]
    t = parts[0] if parts else raw
    if len(parts) > 1 and len(t) + len(parts[1]) < 40:
        t = f'{t} - {parts[1]}'
    return t

ICONS = {
    'truck': '<path d="M3 7h11v9H3zM14 10h4l3 3v3h-7z"/><circle cx="7" cy="17.5" r="1.8"/><circle cx="17" cy="17.5" r="1.8"/>',
    'build': '<path d="M4 21V5l9-2v18M13 9h7v12M4 21h16M8 8h2M8 12h2M8 16h2M16 13h1M16 17h1"/>',
    'sofa': '<path d="M5 11V8a2 2 0 0 1 2-2h10a2 2 0 0 1 2 2v3M3 13a2 2 0 0 1 4 0v2h10v-2a2 2 0 0 1 4 0v5H3zM6 18v2M18 18v2"/>',
    'box': '<path d="M21 8 12 3 3 8v8l9 5 9-5zM3 8l9 5 9-5M12 13v8"/>',
    'chip': '<rect x="7" y="7" width="10" height="10" rx="1.5"/><path d="M9 3v4M15 3v4M9 17v4M15 17v4M3 9h4M3 15h4M17 9h4M17 15h4"/>',
    'check': '<path d="M12 3 4 6v6c0 5 3.5 8 8 9 4.5-1 8-4 8-9V6zM8.5 12l2.5 2.5L16 9.5"/>',
    'layout': '<rect x="3" y="3" width="18" height="18" rx="2"/><path d="M3 9h18M9 9v12"/>',
    'recycle': '<path d="M7 19H4l3-5M17 5h3l-3 5M12 3 9 8h6zM12 21l3-5H9zM4 14l3 5M20 10l-3-5"/>',
}


def icon(k):
    return f'<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true">{ICONS[k]}</svg>'


SOCIAL_SVG = {
    'LinkedIn': '<path d="M6.9 8.6H3.7V20h3.2zM5.3 3.5a1.9 1.9 0 1 0 0 3.8 1.9 1.9 0 0 0 0-3.8zM20.3 20v-6.3c0-3.1-1.7-4.6-3.9-4.6-1.8 0-2.6 1-3 1.7V8.6h-3.2V20h3.2v-6.2c0-1.6.3-3.1 2.3-3.1s2 1.8 2 3.2V20z"/>',
    'Instagram': '<rect x="3" y="3" width="18" height="18" rx="5" fill="none" stroke="currentColor" stroke-width="2"/><circle cx="12" cy="12" r="4" fill="none" stroke="currentColor" stroke-width="2"/><circle cx="17.5" cy="6.5" r="1.2"/>',
    'YouTube': '<path d="M21.6 7.2a2.5 2.5 0 0 0-1.8-1.8C18.2 5 12 5 12 5s-6.2 0-7.8.4A2.5 2.5 0 0 0 2.4 7.2C2 8.8 2 12 2 12s0 3.2.4 4.8a2.5 2.5 0 0 0 1.8 1.8C5.8 19 12 19 12 19s6.2 0 7.8-.4a2.5 2.5 0 0 0 1.8-1.8c.4-1.6.4-4.8.4-4.8s0-3.2-.4-4.8zM10 15V9l5.2 3z"/>',
}

def social_links():
    out = []
    for n, u in SOCIAL.items():
        out.append(f'<a href="{u}" target="_blank" rel="noopener noreferrer" aria-label="{n}"><svg viewBox="0 0 24 24" fill="currentColor" aria-hidden="true">{SOCIAL_SVG[n]}</svg></a>')
    return '<div class="social">' + ''.join(out) + '</div>'

# ---------------------------------------------------------------- shared layout
CERT_IMGS = [
    ('New-York-State-Minority-and-Women-Owned-Business-Enterprise-Certification-Business-Relocation-Services', 'New York State Minority and Women-Owned Business Enterprise (MWBE) certification'),
    ('MBE-NYC-Small-Business-Cert-2025-2030-Business-Relocation-Services', 'NYC Small Business Services MBE certification 2025-2030'),
    ('NMSDC-Certificate-9-26-25-9-30-26-Business-Relocation-Services', 'NMSDC Minority Business Enterprise certificate'),
]


def nav_html(current):
    mega = ''
    for g in GROUPS:
        links = ''.join(f'<a href="/{s[0]}/">{esc(s[1])}</a>' for s in SERVICES if s[4] == g)
        mega += f'<div><h4>{g}</h4>{links}</div>'
    cur = lambda p: ' aria-current="page"' if current == p else ''
    return f'''<nav class="nav" id="nav" aria-label="Main">
<button class="nav-close" type="button" aria-label="Close menu">&times;</button>
<ul>
<li class="has-menu"><button class="nl" type="button" aria-expanded="false" aria-haspopup="true">Services <svg width="12" height="12" viewBox="0 0 12 12" aria-hidden="true"><path d="M2 4l4 4 4-4" fill="none" stroke="currentColor" stroke-width="1.8"/></svg></button>
<div class="mega" role="group" aria-label="Services">{mega}<div class="mega-foot"><a href="/our-services/"><b>View all services →</b></a><a class="btn btn-cta" href="/request-a-quote/">Get a Free Quote</a></div></div></li>
<li><a class="nl" href="/business-relocation/"{cur('business-relocation')}>About</a></li>
<li><a class="nl" href="/blog/"{cur('blog')}>Blog</a></li>
<li><a class="nl" href="/careers/"{cur('careers')}>Careers</a></li>
<li><a class="nl" href="/contact-brs-business-relocation-services-new-york-new-jersey/"{cur('contact')}>Contact</a></li>
</ul></nav>'''


def header(current=''):
    return f'''<a class="skip" href="#main">Skip to content</a>
<div class="topbar"><div class="wrap"><div class="tb-left"><span>Serving New York, New Jersey &amp; Pennsylvania since 1987</span><a href="mailto:{EMAIL}">{EMAIL}</a></div><a href="tel:{PHONE_TEL}">Call {PHONE}</a></div></div>
<header class="header"><div class="wrap">
<a class="logo" href="/" aria-label="Business Relocation Services - home"><img src="/assets/logo.png" alt="BRS Business Relocation Services" width="140" height="50"></a>
{nav_html(current)}
<div class="head-cta"><a class="head-phone" href="tel:{PHONE_TEL}"><small>CALL US</small>{PHONE}</a><a class="btn btn-cta" href="/request-a-quote/">Get a Free Quote</a>
<button class="burger" type="button" aria-label="Open menu" aria-expanded="false" aria-controls="nav"><svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round"><path d="M4 7h16M4 12h16M4 17h16"/></svg></button></div>
</div></header><div class="scrim"></div>'''


def footer():
    svc = ''.join(f'<li><a href="/{s[0]}/">{esc(s[1])}</a></li>' for s in SERVICES[:10])
    svc2 = ''.join(f'<li><a href="/{s[0]}/">{esc(s[1])}</a></li>' for s in SERVICES[10:])
    return f'''<footer class="footer"><div class="wrap">
<div class="cols">
<div><a class="flogo" href="/"><img src="/assets/logo.png" alt="BRS Business Relocation Services" width="126" height="45" loading="lazy"></a>
<p>Business Relocation Services in New York, New Jersey and Pennsylvania for over 40 years. A certified MWBE.</p>
<p><a href="tel:{PHONE_TEL}"><b>{PHONE}</b></a><br><a href="mailto:{EMAIL}">{EMAIL}</a></p>{social_links()}
<p style="margin-top:18px"><a class="btn btn-cta" href="/request-a-quote/">Get a Free Quote</a></p></div>
<div><h4>Services</h4><ul>{svc}</ul></div>
<div><h4>More Services</h4><ul>{svc2}<li><a href="/our-services/">All services</a></li></ul></div>
<div><h4>Company</h4><ul><li><a href="/business-relocation/">About BRS</a></li><li><a href="/mbe-minority-business-enterprise-certification/">MWBE Certifications</a></li><li><a href="/relocation-services-in-new-york/">Relocation Services NY, NJ &amp; PA</a></li><li><a href="/office-movers-in-new-york/">Office Movers in New York</a></li><li><a href="/blog/">Blog</a></li><li><a href="/careers/">Careers</a></li><li><a href="/contact-brs-business-relocation-services-new-york-new-jersey/">Contact Us</a></li><li><a href="{BBB}" target="_blank" rel="noopener noreferrer">BBB Profile</a></li></ul>
<h4 style="margin-top:22px">Locations</h4>
<address>20 Aquarium Dr<br>Secaucus, NJ 07094</address><address>425 East 13th Street<br>New York, NY 10009</address></div>
</div>
<div class="legal"><span>&copy; {datetime.date.today().year} Business Relocation Services Inc. All rights reserved.</span><span>Office movers &amp; commercial relocation in NYC, NJ &amp; PA</span></div>
</div></footer>
<div class="mbar"><a class="btn btn-outline" href="tel:{PHONE_TEL}">Call Now</a><a class="btn btn-cta" href="/request-a-quote/">Get a Free Quote</a></div>'''


def head(title, desc, path, og_img=None, schema=None, noindex=False, extra=''):
    url = SITE + (path if path.startswith('/') else '/' + path)
    og = og_img or '/assets/img/BRS-Business-Relocation-Services.webp'
    robots = 'noindex, follow' if noindex else 'index, follow, max-snippet:-1, max-image-preview:large, max-video-preview:-1'
    schema_html = ''
    if schema:
        schema_html = '<script type="application/ld+json">' + json.dumps(schema, separators=(',', ':'), ensure_ascii=False) + '</script>'
    return f'''<!doctype html>
<html lang="en-US"><head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>{esc(title)}</title>
<meta name="description" content="{esc(desc)}">
<meta name="robots" content="{robots}">
<link rel="canonical" href="{url}">
<meta name="theme-color" content="#0e1b4d">
<meta property="og:locale" content="en_US"><meta property="og:type" content="website">
<meta property="og:title" content="{esc(title)}"><meta property="og:description" content="{esc(desc)}">
<meta property="og:url" content="{url}"><meta property="og:site_name" content="Business Relocation Services">
<meta property="og:image" content="{SITE}{og}">
<meta name="twitter:card" content="summary_large_image">
<meta name="form-endpoint" content="{esc(FORM_ENDPOINT)}"><meta name="form-mailto" content="{FORM_MAILTO}">
<link rel="icon" type="image/png" sizes="32x32" href="/assets/favicon-32.png">
<link rel="apple-touch-icon" href="/assets/apple-touch-icon.png">
<link rel="preconnect" href="https://fonts.googleapis.com"><link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
<link rel="stylesheet" href="https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700;800&display=swap">
<link rel="stylesheet" href="/assets/css/style.css">
{extra}{schema_html}
</head>'''


def page(path, title, desc, body, current='', og_img=None, schema=None, noindex=False, extra=''):
    out = head(title, desc, path, og_img, schema, noindex, extra) + '<body>' + header(current) + '<main id="main">' + body + '</main>' + footer() + '<script src="/assets/js/main.js" defer></script></body></html>'
    fp = os.path.join(ROOT, path.strip('/'), 'index.html') if path != '/' else os.path.join(ROOT, 'index.html')
    os.makedirs(os.path.dirname(fp), exist_ok=True)
    open(fp, 'w', encoding='utf8').write(out)
    return fp


ORG_ID = SITE + '/#organization'


def org_schema():
    return {
        '@type': ['MovingCompany', 'LocalBusiness'], '@id': ORG_ID, 'name': 'Business Relocation Services Inc. (BRS)',
        'alternateName': 'BRS', 'url': SITE + '/', 'logo': SITE + '/assets/logo.png', 'image': SITE + '/assets/img/BRS-Business-Relocation-Services.webp',
        'description': 'Facility relocation project management and commercial moving company serving New York, New Jersey and Pennsylvania since 1987.',
        'telephone': '+1-718-399-8000', 'email': EMAIL, 'foundingDate': '1987',
        'address': {'@type': 'PostalAddress', 'streetAddress': '20 Aquarium Dr', 'addressLocality': 'Secaucus', 'addressRegion': 'NJ', 'postalCode': '07094', 'addressCountry': 'US'},
        'location': [{'@type': 'Place', 'name': 'BRS - ' + a[0], 'address': {'@type': 'PostalAddress', 'streetAddress': a[1], 'addressLocality': a[2], 'addressRegion': a[3], 'postalCode': a[4], 'addressCountry': 'US'}} for a in ADDR],
        'areaServed': [{'@type': 'State', 'name': 'New York'}, {'@type': 'State', 'name': 'New Jersey'}, {'@type': 'State', 'name': 'Pennsylvania'}, {'@type': 'Country', 'name': 'United States'}],
        'sameAs': list(SOCIAL.values()) + [BBB],
        'knowsAbout': ['Office relocation', 'Commercial moving', 'IT equipment moving', 'Data center relocation', 'Office furniture installation', 'IT equipment recycling'],
    }


def crumbs(items):
    return {'@type': 'BreadcrumbList', 'itemListElement': [{'@type': 'ListItem', 'position': i + 1, 'name': n, 'item': SITE + u} for i, (n, u) in enumerate(items)]}


def crumbs_html(items):
    parts = [f'<a href="{u}">{esc(n)}</a>' for n, u in items[:-1]] + [f'<span style="margin:0;opacity:1">{esc(items[-1][0])}</span>']
    return '<nav class="crumbs" aria-label="Breadcrumb">' + '<span>/</span>'.join(parts) + '</nav>'

# ---------------------------------------------------------------- forms
STATES = 'AL AK AZ AR CA CO CT DE DC FL GA HI ID IL IN IA KS KY LA ME MD MA MI MN MS MO MT NE NV NH NJ NM NY NC ND OH OK OR PA RI SC SD TN TX UT VT VA WA WV WI WY'.split()
SERVICE_OPTS = ['Local Moving', 'Interstate Moving', 'Packing & Unpacking', 'Office Moving', 'Furniture Storage', 'Warehouse', 'Storage', 'Rent Moving Crates', 'Library Cart Rental', 'School Moving Services', 'Other']
HP = '<div class="hp" aria-hidden="true"><label>Leave blank <input type="text" name="_gotcha" tabindex="-1" autocomplete="off"></label></div>'


def state_select(name, default='NY'):
    o = ''.join(f'<option{" selected" if s == default else ""}>{s}</option>' for s in STATES)
    return f'<select name="{name}" aria-label="State">{o}</select>'


def quick_form(idp='q'):
    opts = ''.join(f'<option>{esc(o)}</option>' for o in ['Office Moving', 'IT / Data Center Moving', 'School Moving', 'Furniture Installation', 'Storage', 'Moving Crates / Library Carts', 'Other'])
    return f'''<form class="qform" data-form data-subject="Quote request (homepage)" data-thanks="/thank-you-request-a-quote/" novalidate>
<div class="row2"><div class="field"><label for="{idp}-n">Name <span class="req">*</span></label><input id="{idp}-n" name="Name" type="text" autocomplete="name" required></div>
<div class="field"><label for="{idp}-p">Phone <span class="req">*</span></label><input id="{idp}-p" name="Phone" type="tel" autocomplete="tel" required></div></div>
<div class="row2"><div class="field"><label for="{idp}-e">Email <span class="req">*</span></label><input id="{idp}-e" name="Email" type="email" autocomplete="email" required></div>
<div class="field"><label for="{idp}-c">Business / Organization <span class="req">*</span></label><input id="{idp}-c" name="Business" type="text" autocomplete="organization" required></div></div>
<div class="row2"><div class="field"><label for="{idp}-d">Move date</label><input id="{idp}-d" name="Move Date" type="date"></div>
<div class="field"><label for="{idp}-s">Service needed</label><select id="{idp}-s" name="Service Needed">{opts}</select></div></div>
{HP}
<button class="btn btn-cta btn-block btn-lg" type="submit">Get My Free Quote</button>
<p class="form-note">No obligation. Prefer to talk? Call <a href="tel:{PHONE_TEL}"><b>{PHONE}</b></a></p>
<div class="form-status" role="status" aria-live="polite"></div></form>'''


def full_quote_form():
    def addr(prefix, label):
        return f'''<fieldset class="fieldset"><legend class="form-section-title">{label}</legend>
<div class="field"><label>Address Line 1</label><input type="text" name="{prefix} Address 1" autocomplete="off"></div>
<div class="field"><label>Address Line 2</label><input type="text" name="{prefix} Address 2" autocomplete="off"></div>
<div class="row3"><div class="field"><label>City</label><input type="text" name="{prefix} City"></div>
<div class="field"><label>State</label>{state_select(prefix + ' State')}</div>
<div class="field"><label>Zip Code</label><input type="text" name="{prefix} Zip" inputmode="numeric" autocomplete="postal-code"></div></div>
<div class="field"><span class="fieldset"><legend>Elevator?</legend></span><div class="radios"><label><input type="radio" name="{prefix} Elevator" value="Yes"> Yes</label><label><input type="radio" name="{prefix} Elevator" value="No"> No</label></div></div></fieldset>'''
    checks = ''.join(f'<label><input type="checkbox" name="Services Needed[]" value="{esc(o)}"> {esc(o)}</label>' for o in SERVICE_OPTS)
    return f'''<form class="qcard" data-form data-subject="Quote request" data-thanks="/thank-you-request-a-quote/" novalidate>
<h2>Request a Quote Form</h2><p class="sub">Fill out the form below and hit submit. We'll email you about the quote you requested as soon as possible.</p>
<div class="row2"><div class="field"><label for="f-fn">First name <span class="req">*</span></label><input id="f-fn" name="First Name" type="text" autocomplete="given-name" required></div>
<div class="field"><label for="f-ln">Last name <span class="req">*</span></label><input id="f-ln" name="Last Name" type="text" autocomplete="family-name" required></div></div>
<div class="row2"><div class="field"><label for="f-e">Email <span class="req">*</span></label><input id="f-e" name="Email" type="email" autocomplete="email" required></div>
<div class="field"><label for="f-p">Phone <span class="req">*</span></label><input id="f-p" name="Phone" type="tel" autocomplete="tel" required></div></div>
<div class="row2"><div class="field"><label for="f-b">Business / Organization <span class="req">*</span></label><input id="f-b" name="Business" type="text" autocomplete="organization" required></div>
<div class="field"><label for="f-d">Move date</label><input id="f-d" name="Move Date" type="date"></div></div>
{addr('Current', 'Current Address')}
{addr('Destination', 'Destination Address')}
<fieldset class="fieldset"><legend class="form-section-title">Services Needed <span class="req">*</span></legend><div class="checks">{checks}</div></fieldset>
<div class="field"><label for="f-c">Comments (more details) <span class="req">*</span></label><textarea id="f-c" name="Comments" required></textarea></div>
{HP}
<button class="btn btn-cta btn-block btn-lg" type="submit">Submit My Quote Request</button>
<p class="form-note">We respect your privacy and only use your details to respond to your request.</p>
<div class="form-status" role="status" aria-live="polite"></div></form>'''


def small_form(subject, thanks, extra_fields='', label='Send Message', ident='c'):
    return f'''<form class="qcard" data-form data-subject="{subject}" data-thanks="{thanks}" novalidate>
<div class="row2"><div class="field"><label for="{ident}-n">Name <span class="req">*</span></label><input id="{ident}-n" name="Name" type="text" autocomplete="name" required></div>
<div class="field"><label for="{ident}-p">Phone</label><input id="{ident}-p" name="Phone" type="tel" autocomplete="tel"></div></div>
<div class="field"><label for="{ident}-e">Email <span class="req">*</span></label><input id="{ident}-e" name="Email" type="email" autocomplete="email" required></div>
{extra_fields}
<div class="field"><label for="{ident}-m">Message <span class="req">*</span></label><textarea id="{ident}-m" name="Message" required></textarea></div>
{HP}
<button class="btn btn-cta btn-block btn-lg" type="submit">{label}</button>
<div class="form-status" role="status" aria-live="polite"></div></form>'''

# ---------------------------------------------------------------- prose
SKIP = {'request a quote', 'get started', 'get started today', 'learn more', 'read more', 'request a free quote', 'ask for a free consultation today!', 'join us! it will only take a minute'}


def clean_lines(text):
    text = text.split('##### Menu')[0]
    text = re.sub(r'post-content-inner">', '', text)
    lines = []
    for ln in text.split('\n'):
        s = ln.replace('\xa0', ' ').replace('﻿', '').strip()
        if not s or s.lower().strip(' .') in SKIP or s.lower().startswith('learn more about') and len(s) < 60 or s.startswith('<div') or s.startswith('[]'):
            continue
        if s.lower().startswith('more about') and len(s) < 60:
            continue
        lines.append(s)
    return lines


def parse_blocks(lines):
    """-> list of (heading|None, [nodes]) where node is ('p', text) or ('ul', [items])."""
    blocks, cur_h, cur = [], None, []
    pending = []

    def flush_list():
        nonlocal pending
        if len(pending) >= 3:
            cur.append(('ul', pending))
        else:
            for p in pending:
                cur.append(('p', p))
        pending = []

    for s in lines:
        m = re.match(r'^(#{1,6})\s*(.*)$', s)
        if m:
            flush_list()
            h = caps_fix(m.group(2))
            if not h:
                continue
            if cur_h is not None or cur:
                blocks.append((cur_h, cur))
            cur_h, cur = h, []
            continue
        short = len(s) <= 90 and not re.search(r'[.!?:]$', s)
        if short:
            pending.append(s)
        else:
            flush_list()
            cur.append(('p', s))
    flush_list()
    if cur_h is not None or cur:
        blocks.append((cur_h, cur))
    return blocks


def linkify(t):
    t = esc(t)
    t = re.sub(r'(1-718-399-8000|\(718\) 399-8000)', f'<a href="tel:{PHONE_TEL}">\\1</a>', t)
    t = re.sub(r'([\w.+-]+@brsmove\.com)', r'<a href="mailto:\1">\1</a>', t)
    return t


def render_nodes(nodes):
    out = ''
    for k, v in nodes:
        if k == 'p':
            out += f'<p>{linkify(v)}</p>'
        else:
            out += '<ul>' + ''.join(f'<li>{linkify(i)}</li>' for i in v) + '</ul>'
    return out


def inline_cta(text='Ready to get started?'):
    return f'<div class="inline-cta"><p>{text}</p><a class="btn btn-cta" href="/request-a-quote/">Get a Free Quote</a></div>'


def render_prose(blocks, images, cta_after=2, drop_first_heading=None):
    html_out, imgs, n = '', list(images), 0
    seen_h = set()
    for h, nodes in blocks:
        if h and h.lower() == (drop_first_heading or '').lower():
            h = None
        if h and h.lower() in seen_h:
            h = None
        if h:
            seen_h.add(h.lower())
        if not nodes:
            continue
        html_out += (f'<h2>{esc(h)}</h2>' if h else '') + render_nodes(nodes)
        n += 1
        if imgs and n % 2 == 1:
            fn = imgs.pop(0)
            html_out += f'<figure>{img(fn)}</figure>'
        if n == cta_after:
            html_out += inline_cta('Have questions or ready for pricing? Talk to our team.')
    for fn in imgs[:2]:
        html_out += f'<figure>{img(fn)}</figure>'
    return html_out


def related(slug, n=4):
    me = SV.get(slug)
    pool = [s for s in SERVICES if s[0] != slug]
    if me:
        pool.sort(key=lambda s: s[4] != me[4])
    return pool[:n]


def side(slug=''):
    cur = ' aria-current="page"'
    links = ''.join(f'<a href="/{s[0]}/"{cur if s[0] == slug else ""}>{esc(s[1])}</a>' for s in SERVICES)
    return f'''<aside class="side"><div class="qcard"><h3>Get a free quote</h3><p class="sub">Tell us about your move and we'll get back to you with a quote.</p>
<a class="btn btn-cta btn-block btn-lg" href="/request-a-quote/">Request a Free Quote</a>
<p style="margin:1em 0 .2em;text-align:center;font-size:.85rem;color:var(--muted)">or call us</p><a class="phone-big" style="text-align:center" href="tel:{PHONE_TEL}">{PHONE}</a>
<ul class="ticks" style="color:var(--ink);gap:6px 18px;font-size:.88rem"><li>Since 1987</li><li>Certified MWBE</li><li>NY &bull; NJ &bull; PA</li></ul></div>
<div class="side-list"><h3>Our services</h3>{links}</div></aside>'''


def cta_band(h='Ready to get moving?', p='Get your free quote today. It only takes a minute.'):
    return f'''<section class="sec" style="padding:20px 0 70px"><div class="wrap"><div class="cta-band reveal"><div><h2>{h}</h2><p>{p}</p></div>
<div class="actions"><a class="btn btn-cta btn-lg" href="/request-a-quote/">Request a Free Quote</a><a class="btn btn-ghost btn-lg" href="tel:{PHONE_TEL}">Call {PHONE}</a></div></div></div></section>'''

# ---------------------------------------------------------------- testimonials / team / faq data
TESTIMONIALS = [
    ('BRS provided service that was nothing short of amazing for all of my moves. The movers have always been attentive and extremely careful with all items that had to be carried down 3 flights of stairs and put onto a truck. Nothing was damaged and they handled themselves professionally. I would highly recommend!', 'Tom Lanzetta', 'Intent Media'),
    ('We have used BRS several times and all of their employees are friendly, professional and go above and beyond to make the moving experience stress free. We will always come back for their services. Highly recommended!', 'Jeff Russo', 'AT&T'),
    ('Customer service was excellent – over the phone very pleasant to deal with and understand my requests. The hand laborers were on time, friendly, and respectful. Will definitely recommend them!', 'Phil Alessi', 'NBC Universal'),
    ('I had the opportunity to solicit service from the BRS team in June 2020. Despite being in the middle of a pandemic, the BRS team made my move as easy and painless as possible, all while adhering to Covid-19 related restrictions. The company employs the best in the business that will treat everything they touch with respect. Lived up to their motto of ‘Consider It Done!’', 'Chris Blandy', 'PNC Bank'),
    ('BRS is professional, efficient, and trustworthy! Our needs were met in a polite and professional manner … from the owners to the staff. The team arrived on time, and worked quickly and smoothly. BRS provides a consistently positive attitude, attention to detail, and applies their expertise gained from years experience!', 'Megan Rochelle', 'SONY'),
    ('The movers at BRS are the definition of efficiency. Each of them more respectful and hardworking than the next. They tirelessly moved my entire office out East during the pandemic. All of them showed up in masks eager to get the job done. The organizational skill of this crew are second to NONE. One employee specifically, I think his name was Kyle anticipated every need and want I had. The staff and management were the key to my seamless transition. Consider. It. Done.', 'Caroline Strehle', 'Memorial Sloan Kettering Cancer Center'),
]
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
    ('What types of moves do you handle?', 'We handle all types of commercial relocation projects, including offices, warehouses and any type of commercial property, as well as schools, libraries, IT equipment, servers and data centers. Any move type and size, from relocation planning to completion.'),
    ('How do I get a moving quote?', f'Request a free quote online in about a minute, or call us at {PHONE}. Tell us about your current and destination locations, move date and the services you need, and we will follow up by email with your quote.'),
    ('Can you move IT equipment and data centers?', 'Yes. Our IT team can disconnect, reconnect, de/re-rack, package and provide direct secure transport for servers, computers and other electronics, and we plan and execute data center relocations and migrations.'),
    ('Do you offer storage, furniture installation and liquidation?', 'Yes. In addition to moving, we offer secure storage facilities, new office furniture installation and reconfiguration, furniture liquidation, space planning, office decommissioning and inventory control.'),
    ('How long has BRS been in business, and are you certified?', 'Business Relocation Services was established in 1987 and is well known in both corporate and government circles. BRS is a certified Minority and Women-Owned Business Enterprise (MWBE) and a member of the National Hispanic Business Group, IFMA and CoreNet.'),
]

# ---------------------------------------------------------------- pages
built = []


def build_home():
    cards = [
        ('truck', 'Office Movers & Moving Services', 'With so few organizations taking on the additional projects that arise during office relocations, why not work with skilled professionals who do it all? BRS brings you detail-oriented management for all needs associated with moving your commercial space.', '/office-movers/'),
        ('build', 'Corporate Relocation', 'Whether it’s assisting, coordinating with your voice and data providers, compiling furniture and equipment inventories, or the myriad other details that surface when moving a work space, we work to ensure a successful project. These services are made available to clients anywhere in the US.', '/business-relocation-services-in-new-york/'),
        ('chip', 'Moving IT Equipment', 'BRS can disconnect, reconnect, de/re-rack, package and provide direct secure transport services. Our IT team carefully and efficiently moves all of your electronics, always putting precision first.', '/moving-it-equipment-in-new-york/'),
        ('sofa', 'Office Furniture Installation', 'Furniture installation is one of the most important parts of your office furniture project. We help you plan and organize new installations or reconfigure your current office space to provide you with the quality environment you want.', '/furniture-installation/'),
        ('box', 'Secure Storage Facilities', 'One of the most important factors in a storage facility is security. It is for this reason that our focus throughout the years of experience in moving and storage is to give you confidence and our professionalism in what we do best.', '/storage-facilities/'),
        ('check', 'Nationwide Relocation Specialist', 'BRS is a nationwide office relocation specialist that goes far beyond basic relocation services. From new furniture purchasing, to liquidation, to project management to the actual transfer, BRS is your best choice.', '/business-relocation/'),
    ]
    cards_html = ''.join(f'<article class="card reveal"><div class="ico">{icon(i)}</div><h3>{t}</h3><p>{d}</p><a class="more" href="{u}">Learn more</a></article>' for i, t, d, u in cards)
    feat = [
        ('Rent-Moving-Crates-in-New-York-Business-Relocation-Services', 'Rent Eco-Friendly Crates', 'Whether you’re moving a small office, faculty, classrooms or an entire corporate floor, our rent moving crates service ensures your items stay protected from start to finish. Ideal for short term in-house projects such as office renovations, clean outs, re-stacks or staff shifts.', '/rent-moving-crates/', 'More about moving crates'),
        ('Business-Relocation-Services-Team', 'School Moving Services', 'Relocating a school is a complex process that requires careful planning, experienced coordination, and specialized equipment. We provide professional school moving services designed to ensure a smooth, organized, and stress-free transition for educational institutions of all sizes.', '/school-moving-services/', 'More about school moving'),
        ('Library-Cart-Rental-for-Libraries-and-Institutions-Business-relocation-Services-New-York', 'Library Cart Rental in New York', 'If your library, school, or archive needs reliable library cart rental in New York, Business Relocation Services is here to help. Our team will guide you through the rental process, recommend the right solution, and ensure your project runs smoothly from start to finish.', '/library-cart-rental/', 'More about library carts'),
    ]
    feat_html = ''.join(f'<article class="card card-img reveal">{img(i)}<div class="body"><h3>{t}</h3><p>{d}</p><a class="more" href="{u}">{l}</a></div></article>' for i, t, d, u, l in feat)
    tests = ''.join(f'<figure class="quote reveal"><p>“{esc(q)}”</p><figcaption><cite>{esc(n)}<span>{esc(c)}</span></cite></figcaption></figure>' for q, n, c in TESTIMONIALS)
    team = ''.join(f'<div class="person reveal">{img(i, alt=n + ", " + r + " at Business Relocation Services")}<b>{n}</b><span>{r}</span></div>' for n, r, i in TEAM)
    logos = ''.join(img(i, alt=a, lazy=True) for i, a in CLIENT_LOGOS)
    certs = ''.join(f'<figure>{img(i, alt=a)}<figcaption>{a.split(" certif")[0]}</figcaption></figure>' for i, a in CERT_IMGS)
    faq = ''.join(f'<details><summary>{esc(q)}</summary><p>{esc(a)}</p></details>' for q, a in FAQ)
    latest = [p for p in ['office-relocation', 'moving-and-storage-company', 'office-it-relocation-services'] if p in POSTS]
    post_cards = ''.join(post_card(p) for p in latest)
    steps = [('Assess', 'A seasoned project manager evaluates your space, inventory, IT and timeline to scope the move.'),
             ('Plan', 'We build a detailed move plan with schedules, floor plans and coordination with building management and vendors.'),
             ('Coordinate', 'We work with your voice and data providers, furniture vendors and your staff so your team can keep doing their day jobs.'),
             ('Execute', 'Our trained crews move, install and set up, with monitoring through completion. “Consider it done!”')]
    steps_html = ''.join(f'<div class="step reveal"><h3>{t}</h3><p>{d}</p></div>' for t, d in steps)
    body = f'''
<section class="hero" style="--hero-img:url('/assets/img/BRS-Business-Relocation-Services.webp')"><div class="wrap">
<div><span class="eyebrow">Established 1987 &bull; Certified MWBE &bull; NY, NJ &amp; PA</span>
<h1>Office Movers &amp; Business Relocation Services in NYC</h1>
<p class="lead">BRS is a facility relocation project management and moving services company, all in one. From the smallest details to the most complex changes, offices, warehouses and commercial property, we keep your business running through the move.</p>
<div class="hero-actions"><a class="btn btn-cta btn-lg" href="/request-a-quote/">Get a Free Quote</a><a class="btn btn-ghost btn-lg" href="tel:{PHONE_TEL}">Call {PHONE}</a></div>
<ul class="ticks"><li>Free quote &amp; consultation</li><li>Trusted by corporate &amp; government clients</li><li>Full-service moving &amp; project management</li></ul></div>
<div class="qcard" id="quote"><h2>Get your free quote</h2><p class="sub">Tell us about your move. It only takes a minute.</p>{quick_form()}</div>
</div></section>
<section class="trust" aria-label="Clients"><div class="wrap"><p>Trusted by corporations, city agencies &amp; non-profits</p><div class="logos">{logos}</div></div></section>
<div class="wrap"><div class="stats" style="margin-top:40px">
<div class="stat reveal"><b>1987</b><span>Established &mdash; 35+ years of expertise</span></div>
<div class="stat reveal"><b>3 States</b><span>New York, New Jersey &amp; Pennsylvania</span></div>
<div class="stat reveal"><b>MWBE</b><span>Certified Minority &amp; Women-Owned</span></div>
<div class="stat reveal"><b>1 Team</b><span>Project management + moving, together</span></div></div></div>

<section class="sec" id="services"><div class="wrap"><div class="sec-head"><span class="kicker">Our services</span><h2>Business Relocation Services specializes in all types of relocation projects</h2>
<p>We help with the transfer of your business from the smallest details to the most complex changes: offices, warehouses or any type of commercial property.</p></div>
<div class="grid g3">{cards_html}</div>
<div class="grid g3" style="margin-top:24px">{feat_html}</div>
<div class="pill-links">{''.join(f'<a href="/{s[0]}/">{esc(s[1])}</a>' for s in SERVICES)}</div></div></section>

<section class="sec soft"><div class="wrap split"><div class="reveal"><span class="kicker" style="color:var(--blue);font-weight:800;font-size:.8rem;letter-spacing:.14em;text-transform:uppercase">Why BRS</span><h2>A project manager who keeps your business moving</h2>
<p>The basic requirement is the knowledge of a seasoned Project Manager well versed in how to assess, plan, coordinate, monitor and execute. The benefit is a return on investment (ROI): the experience of a project manager lets your staff do their daily duties and your company operate without interruption.</p>
<ul class="checklist"><li>Detail-oriented management for everything associated with moving your commercial space</li><li>Coordination with voice &amp; data providers, furniture vendors and building management</li><li>Furniture purchasing, liquidation, installation and storage under one roof</li><li>Well known in both corporate and government circles since 1987</li></ul>
<a class="btn btn-cta btn-lg" href="/request-a-quote/">Request a Free Quote</a></div>
<div class="reveal">{img('Office-Movers-BRS-Warehouse-location-Secaucus-NJ', alt='BRS warehouse in Secaucus, NJ')}</div></div></section>

<section class="sec dark"><div class="wrap"><div class="sec-head"><span class="kicker">How it works</span><h2>From first call to last box</h2><p>Our process is built around a seasoned project manager who assesses, plans, coordinates and executes your relocation.</p></div>
<div class="steps">{steps_html}</div><p style="text-align:center;margin:40px 0 0"><a class="btn btn-cta btn-lg" href="/request-a-quote/">Start your free quote</a></p></div></section>

<section class="sec"><div class="wrap"><div class="sec-head"><span class="kicker">Client testimonials</span><h2>Don’t take our word for it</h2><p>Here’s what our clients say.</p></div>
<div class="reviews">{tests}</div></div></section>

<section class="sec soft"><div class="wrap"><div class="cta-band reveal"><div><h2>Do you need help with your business move?</h2><p>We are a full-service moving company. Get a free quote and moving consultation.</p></div>
<div class="actions"><a class="btn btn-cta btn-lg" href="/request-a-quote/">Request a Free Quote</a><a class="btn btn-ghost btn-lg" href="tel:{PHONE_TEL}">Call {PHONE}</a></div></div></div></section>

<section class="sec"><div class="wrap"><div class="sec-head"><span class="kicker">Our executive team</span><h2>Specialists in their field</h2><p>Highly qualified, experienced and knowledgeable industry professionals who are passionate and dedicated to our clients.</p></div>
<div class="team">{team}</div></div></section>

<section class="sec soft"><div class="wrap"><div class="sec-head"><span class="kicker">Certified &amp; recognized</span><h2>Minority &amp; Women-Owned Business Enterprise</h2>
<p>BRS is a certified MWBE and a member of the National Hispanic Business Group, International Facility Managers Association (IFMA) and CoreNet.</p></div>
<div class="certs">{certs}</div><div class="members"><span>National Hispanic Business Group</span><span>IFMA</span><span>CoreNet</span><span>Certified MWBE</span></div>
<p style="text-align:center;margin-top:30px"><a class="btn btn-outline" href="/mbe-minority-business-enterprise-certification/">About our certifications</a></p></div></section>

<section class="sec"><div class="wrap"><div class="sec-head"><span class="kicker">FAQ</span><h2>Questions about moving your business</h2></div><div class="faq">{faq}</div></div></section>

<section class="sec soft"><div class="wrap"><div class="sec-head"><span class="kicker">Latest news</span><h2>Office relocation advice from the pros</h2></div>
<div class="grid g3">{post_cards}</div><p style="text-align:center;margin-top:30px"><a class="btn btn-outline" href="/blog/">Read all articles</a></p></div></section>

<section class="sec"><div class="wrap"><div class="sec-head"><span class="kicker">Visit us</span><h2>Two locations to serve you</h2><p>Business Relocation Services in New York, New Jersey and Pennsylvania for over 40 years.</p></div>
<div class="grid g2">{''.join(loc_card(a) for a in ADDR)}</div></div></section>
{cta_band('Start your free quote now', f'For immediate assistance call {PHONE}. Let’s start moving!')}'''
    schema = {'@context': 'https://schema.org', '@graph': [
        org_schema(),
        {'@type': 'WebSite', '@id': SITE + '/#website', 'url': SITE + '/', 'name': 'Business Relocation Services', 'publisher': {'@id': ORG_ID}, 'inLanguage': 'en-US'},
        {'@type': 'WebPage', '@id': SITE + '/#webpage', 'url': SITE + '/', 'name': 'Office Movers & Business Relocation Services in NYC | BRS', 'isPartOf': {'@id': SITE + '/#website'}, 'about': {'@id': ORG_ID}, 'primaryImageOfPage': SITE + '/assets/img/BRS-Business-Relocation-Services.webp'},
        {'@type': 'FAQPage', 'mainEntity': [{'@type': 'Question', 'name': q, 'acceptedAnswer': {'@type': 'Answer', 'text': a}} for q, a in FAQ]},
        {'@type': 'ItemList', 'name': 'BRS services', 'itemListElement': [{'@type': 'ListItem', 'position': i + 1, 'name': s[2], 'url': f'{SITE}/{s[0]}/'} for i, s in enumerate(SERVICES)]},
    ]}
    built.append(page('/', 'Office Movers & Business Relocation Services in NYC | BRS',
                      'Commercial office movers and business relocation specialists serving NYC, New Jersey & Pennsylvania since 1987. IT moves, furniture, storage. Get a free quote.',
                      body, current='home', schema=schema,
                      extra='<link rel="preload" as="image" href="/assets/img/BRS-Business-Relocation-Services.webp" fetchpriority="high">'))


def loc_card(a):
    q = f'{a[1]}, {a[2]}, {a[3]} {a[4]}'
    from urllib.parse import quote
    return f'''<div class="loc reveal"><h3>{a[0]}</h3><address>{a[1]}<br>{a[2]}, {a[3]} {a[4]}</address><p style="margin:0"><a class="btn btn-outline" href="https://www.google.com/maps/search/?api=1&query={quote("Business Relocation Services " + q)}" target="_blank" rel="noopener noreferrer">Get directions</a></p></div>'''


def post_meta(slug):
    c = CONTENT[f'{SITE}/{slug}/']
    lines = clean_lines(c['text'])
    first_h = None
    for ln in lines:
        m = re.match(r'^#{1,6}\s*(.*)$', ln)
        if m and m.group(1).strip():
            first_h = caps_fix(m.group(1))
        break
    title = first_h or short_title(c['title'])
    paras = [l for l in lines if not l.startswith('#') and len(l) > 80]
    excerpt = clip(paras[0] if paras else c['desc'], 170)
    im = local_img(c['imgs'][0]) if c['imgs'] else None
    d = c['date'][:10]
    return dict(slug=slug, title=title, excerpt=excerpt, img=im, date=d, first_h=first_h)


def fmt_date(d):
    return datetime.date.fromisoformat(d).strftime('%B %-d, %Y')


def post_card(slug):
    m = post_meta(slug)
    return f'''<article class="card card-img post-card reveal">{img(m['img']) if m['img'] else ''}<div class="body"><div class="meta"><time datetime="{m['date']}">{fmt_date(m['date'])}</time></div><h3><a href="/{slug}/">{esc(m['title'])}</a></h3><p>{esc(m['excerpt'])}</p><a class="more" href="/{slug}/">Read more</a></div></article>'''


def build_service(slug):
    c = CONTENT[f'{SITE}/{slug}/']
    if slug in SV:
        _, nav, h1, blurb, grp = SV[slug]
        crumb = [('Home', '/'), ('Services', '/our-services/'), (nav, f'/{slug}/')]
    else:
        nav, h1, blurb = EXTRA[slug]
        crumb = [('Home', '/'), (nav, f'/{slug}/')] if slug != 'our-services' else [('Home', '/'), ('Our Services', '/our-services/')]
    lines = clean_lines(c['text'])
    blocks = parse_blocks(lines)
    imgs = [i for i in (local_img(u) for u in c['imgs']) if i and not any(k in i.lower() for k in ('logo', 'staff', 'employ'))]
    hero_img = imgs[0] if imgs else None
    body_imgs = imgs[1:] if hero_img else []
    extra_top = ''
    if slug == 'our-services':
        groups = ''
        for g in GROUPS:
            items = ''.join(f'<article class="card reveal"><h3><a href="/{s[0]}/" style="text-decoration:none;color:inherit">{esc(s[1])}</a></h3><p>{esc(s[3])}</p><a class="more" href="/{s[0]}/">Learn more</a></article>' for s in SERVICES if s[4] == g)
            groups += f'<h2 style="margin:1.6em 0 .7em">{g}</h2><div class="grid g3">{items}</div>'
        extra_top = f'<div class="wrap" style="padding-top:56px">{groups}</div>'
    prose = render_prose(blocks, body_imgs, drop_first_heading=h1)
    if slug == 'mbe-minority-business-enterprise-certification':
        figs = ''.join(f'<figure>{img(i, alt=a)}<figcaption style="font-size:.88rem;color:var(--muted);margin-top:.5em">{esc(a)}</figcaption></figure>' for i, a in CERT_IMGS)
        prose += f'<h2>Our certifications</h2><div class="certs">{figs}</div><p style="margin-top:1.6em"><a href="https://sbsconnect.nyc.gov/certification-directory-search/" target="_blank" rel="noopener noreferrer">Search the NYC Online Directory of Certified Businesses →</a></p>'
    hero_style = f' style="--hero-img:url(\'/assets/img/{hero_img}\')"' if hero_img else ''
    hero = f'''<section class="page-hero{' has-img' if hero_img else ''}"{hero_style}><div class="wrap">{crumbs_html(crumb)}<h1>{esc(h1)}</h1><p class="lead">{esc(blurb)}</p>
<div class="hero-actions" style="margin-bottom:0"><a class="btn btn-cta btn-lg" href="/request-a-quote/">Get a Free Quote</a><a class="btn btn-ghost btn-lg" href="tel:{PHONE_TEL}">Call {PHONE}</a></div></div></section>'''
    rel = ''
    if slug in SV:
        rel = '<section class="sec soft"><div class="wrap"><div class="sec-head"><h2>Related services</h2></div><div class="grid g4">' + ''.join(
            f'<article class="card reveal"><h3>{esc(s[1])}</h3><p>{esc(s[3])}</p><a class="more" href="/{s[0]}/">Learn more</a></article>' for s in related(slug)) + '</div></div></section>'
    layout = '' if slug == 'our-services' else f'<div class="wrap layout"><div class="prose">{prose}</div>{side(slug)}</div>'
    if slug == 'our-services':
        layout = f'{extra_top}<div class="wrap" style="padding:30px 0 40px"><div class="prose" style="max-width:860px">{prose}</div></div>'
    body = hero + layout + rel + cta_band()
    title = TITLES.get(slug) or (short_title(c['title']) + ' | BRS')
    if len(title) > 62:
        title = short_title(c['title'])[:58] + ' | BRS' if len(short_title(c['title'])) < 56 else short_title(c['title'])
    desc = c['desc'].strip()
    if not (70 <= len(desc) <= 165):
        desc = clip(blurb + ' ' + ' '.join(l for l in lines if not l.startswith('#'))[:200], 158)
    schema = {'@context': 'https://schema.org', '@graph': [
        crumbs(crumb),
        {'@type': 'Service', 'name': h1, 'description': blurb, 'url': f'{SITE}/{slug}/', 'provider': {'@id': ORG_ID}, 'areaServed': ['New York', 'New Jersey', 'Pennsylvania'], 'serviceType': nav},
        {**org_schema()},
    ]}
    built.append(page(f'/{slug}/', title, desc, body, current='services', og_img=f'/assets/img/{hero_img}' if hero_img else None, schema=schema))


TITLES = {
    'office-movers': 'Office Movers in NYC, NJ & PA | Commercial Movers | BRS',
    'our-services': 'Commercial Moving & Relocation Services | BRS',
    'business-relocation': 'About BRS | Business Relocation Services Since 1987',
    'rent-moving-crates': 'Rent Moving Crates in New York | BRS',
    'library-cart-rental': 'Library Cart Rental in New York | BRS',
    'school-moving-services': 'School Moving Services in NYC, NJ & PA | BRS',
    'data-center-relocation': 'Data Center Relocation Services | BRS',
    'server-moving-computer-relocation': 'Server Moving & Computer Relocation | BRS',
    'moving-it-equipment-in-new-york': 'Moving IT Equipment in New York | BRS',
    'office-decommissioning': 'Office Decommissioning Services | BRS',
    'office-movers-in-new-york': 'Office Movers in New York City | BRS',
    'relocation-services-in-new-york': 'Relocation Services in NY, NJ & PA | BRS',
    'mbe-minority-business-enterprise-certification': 'MWBE & MBE Certified Movers | BRS',
    'furniture-installation': 'Office Furniture Installation | BRS',
    'storage-facilities': 'Secure Storage Facilities for Business | BRS',
}


def build_post(slug):
    c = CONTENT[f'{SITE}/{slug}/']
    m = post_meta(slug)
    lines = clean_lines(c['text'])
    blocks = parse_blocks(lines)
    imgs = [i for i in (local_img(u) for u in c['imgs'][1:]) if i and not any(k in i.lower() for k in ('logo', 'staff', 'employ'))]
    prose = render_prose(blocks, imgs[:3], cta_after=3, drop_first_heading=m['first_h'])
    crumb = [('Home', '/'), ('Blog', '/blog/'), (m['title'], f'/{slug}/')]
    others = [p for p in POSTS if p != slug and p != 'blog'][:3]
    more = ''.join(post_card(p) for p in others)
    feat = img(m['img'], eager=True, cls='feature') if m['img'] else ''
    body = f'''<section class="page-hero"><div class="wrap">{crumbs_html(crumb)}<h1>{esc(m['title'])}</h1><p class="lead"><time datetime="{m['date']}">{fmt_date(m['date'])}</time> &middot; Business Relocation Services</p></div></section>
<div class="wrap"><article class="article prose">{feat}{prose}
<div class="inline-cta"><p>Planning a move? Get a free quote from NYC’s office relocation specialists.</p><a class="btn btn-cta" href="/request-a-quote/">Get a Free Quote</a></div></article></div>
<section class="sec soft"><div class="wrap"><div class="sec-head"><h2>More from the BRS blog</h2></div><div class="grid g3">{more}</div></div></section>'''
    title = short_title(c['title'])
    title = (m['title'] if len(m['title']) <= 56 else title) + ' | BRS'
    schema = {'@context': 'https://schema.org', '@graph': [crumbs(crumb), {
        '@type': 'BlogPosting', 'headline': m['title'][:110], 'description': m['excerpt'], 'datePublished': m['date'], 'dateModified': m['date'],
        'image': f"{SITE}/assets/img/{m['img']}" if m['img'] else SITE + '/assets/img/BRS-Business-Relocation-Services.webp',
        'author': {'@type': 'Organization', 'name': 'Business Relocation Services', 'url': SITE + '/'}, 'publisher': {'@id': ORG_ID},
        'mainEntityOfPage': f'{SITE}/{slug}/'}, org_schema()]}
    built.append(page(f'/{slug}/', title, c['desc'] if 70 <= len(c['desc']) <= 165 else m['excerpt'], body, current='blog',
                      og_img=f"/assets/img/{m['img']}" if m['img'] else None, schema=schema))


def build_blog_index():
    ps = sorted((post_meta(p) for p in POSTS if p != 'blog'), key=lambda m: m['date'], reverse=True)
    cards = ''.join(post_card(m['slug']) for m in ps)
    crumb = [('Home', '/'), ('Blog', '/blog/')]
    body = f'''<section class="page-hero"><div class="wrap">{crumbs_html(crumb)}<h1>BRS Blog: Office Relocation &amp; Moving Advice</h1><p class="lead">Tips, checklists and insight on office moves, IT relocation, furniture and recycling from the team at Business Relocation Services.</p></div></section>
<section class="sec"><div class="wrap"><div class="grid g3">{cards}</div></div></section>{cta_band()}'''
    built.append(page('/blog/', 'Blog | Office Relocation & Moving Tips | BRS',
                      'Office relocation tips, move checklists and commercial moving advice for NYC, NJ and PA businesses from Business Relocation Services.',
                      body, current='blog', schema={'@context': 'https://schema.org', '@graph': [crumbs(crumb), {'@type': 'Blog', 'name': 'BRS Blog', 'url': SITE + '/blog/', 'publisher': {'@id': ORG_ID}}]}))


def build_quote():
    crumb = [('Home', '/'), ('Request a Quote', '/request-a-quote/')]
    body = f'''<section class="page-hero"><div class="wrap">{crumbs_html(crumb)}<h1>Request a Free Moving Quote</h1><p class="lead">Commercial moving quotes for your business. Fill out the form and we will email you about the quote you request as soon as possible.</p></div></section>
<div class="wrap layout"><div>{full_quote_form()}</div>
<aside class="side"><div class="qcard"><h3>Prefer to talk?</h3><p class="sub">Call us and speak with our team directly.</p><a class="phone-big" href="tel:{PHONE_TEL}">{PHONE}</a>
<p style="margin:0"><a href="mailto:{EMAIL}">{EMAIL}</a></p></div>
<div class="side-list"><h3>Why businesses choose BRS</h3><ul class="checklist" style="margin:.6em 0 0"><li>Serving NY, NJ &amp; PA since 1987</li><li>Certified MWBE</li><li>Moving, IT, furniture &amp; storage under one roof</li><li>Project managers on every move</li></ul></div>
<figure class="quote" style="margin:0"><p>“{esc(TESTIMONIALS[1][0])}”</p><figcaption><cite>{TESTIMONIALS[1][1]}<span>{TESTIMONIALS[1][2]}</span></cite></figcaption></figure></aside></div>'''
    built.append(page('/request-a-quote/', 'Request a Free Moving Quote | Business Relocation Services',
                      'Request a free commercial moving quote from Business Relocation Services. Office, IT, school and warehouse moves across NYC, NJ & PA. Call 1-718-399-8000.',
                      body, current='quote', schema={'@context': 'https://schema.org', '@graph': [crumbs(crumb), {'@type': 'WebPage', 'name': 'Request a Quote', 'url': SITE + '/request-a-quote/', 'about': {'@id': ORG_ID}}, org_schema()]}))


def build_contact():
    slug = 'contact-brs-business-relocation-services-new-york-new-jersey'
    crumb = [('Home', '/'), ('Contact Us', f'/{slug}/')]
    locs = ''.join(loc_card(a) for a in ADDR)
    body = f'''<section class="page-hero"><div class="wrap">{crumbs_html(crumb)}<h1>Contact Business Relocation Services</h1><p class="lead">We provide quality relocation services in New York, New Jersey and Pennsylvania. Whether it’s offices, warehouses or any type of commercial property, please don’t hesitate to call with any questions. Contact us to help with your relocation process!</p></div></section>
<div class="wrap layout"><div><h2 style="margin-bottom:.5em">Send us a message</h2>{small_form('Contact form', '/thank-you-contact-form/')}</div>
<aside class="side"><div class="qcard"><h3>Call us</h3><a class="phone-big" href="tel:{PHONE_TEL}">{PHONE}</a><h3 style="margin-top:.8em">Send us an e-mail</h3><p style="margin:0"><a href="mailto:{EMAIL}">{EMAIL}</a></p></div>
<div class="qcard" style="background:var(--navy);color:#dbe4ff"><h3 style="color:#fff">Need pricing?</h3><p>Skip the back-and-forth. Tell us about your move and get a free quote.</p><a class="btn btn-cta btn-block" href="/request-a-quote/">Request a Free Quote</a></div></aside></div>
<section class="sec soft"><div class="wrap"><div class="sec-head"><h2>Visit us</h2></div><div class="grid g2">{locs}</div></div></section>'''
    built.append(page(f'/{slug}/', 'Contact BRS | Office Movers in NYC, NJ & PA',
                      'Contact Business Relocation Services: call 1-718-399-8000 or email info@brsmove.com. Offices in Secaucus, NJ and New York, NY.',
                      body, current='contact', schema={'@context': 'https://schema.org', '@graph': [crumbs(crumb), {'@type': 'ContactPage', 'name': 'Contact BRS', 'url': f'{SITE}/{slug}/', 'about': {'@id': ORG_ID}}, org_schema()]}))


def build_careers():
    c = CONTENT[SITE + '/careers/']
    crumb = [('Home', '/'), ('Careers', '/careers/')]
    extra = '<div class="field"><label for="cr-pos">Position of interest</label><input id="cr-pos" name="Position" type="text"></div>'
    body = f'''<section class="page-hero"><div class="wrap">{crumbs_html(crumb)}<h1>Career Opportunities at BRS</h1><p class="lead">BRS is a family of movers, project managers, office members, truck drivers, mechanics, consultants, supervisors and foremen who all have one common goal: to get the job done as safely, as quickly and as professionally as possible.</p></div></section>
<div class="wrap layout"><div class="prose"><h2>Interested in joining our team?</h2><p>Looking for a job with career potential? Apply to join our family. Send us a note with your details and the role you’re interested in, and our team will follow up with next steps. You can also email your resume to <a href="mailto:{EMAIL}">{EMAIL}</a>.</p>
<p><em>Business Relocation Services is an equal opportunity employer, as the company does not and shall not discriminate on the basis of race, color, religion (creed), gender, gender expression, age, national origin (ancestry), disability, marital status, sexual orientation, or military status, in any of its activities or operations.</em></p>
<div style="margin-top:2em">{small_form('Job application inquiry', '/thank-you-job-application/', extra, 'Send Application Inquiry', 'cr')}</div></div>{side()}</div>'''
    built.append(page('/careers/', 'Careers at BRS | Movers & Project Manager Jobs NJ/NY',
                      'Join the BRS family of movers, project managers, drivers and supervisors. Apply for career opportunities with Business Relocation Services.',
                      body, current='careers', schema={'@context': 'https://schema.org', '@graph': [crumbs(crumb), org_schema()]}))


def build_thanks():
    for slug in ['thank-you-contact-form', 'thank-you-request-a-quote', 'thank-you-job-application']:
        body = f'''<section class="sec"><div class="wrap" style="max-width:720px;text-align:center"><h1>Thank you!</h1>
<p style="font-size:1.2rem">Your message has been successfully sent. We appreciate you contacting Business Relocation Services and will get back to you as soon as possible.</p>
<p>Need immediate assistance? Call <a href="tel:{PHONE_TEL}"><b>{PHONE}</b></a>.</p>
<p style="margin-top:2em"><a class="btn btn-cta btn-lg" href="/">Back to home</a> <a class="btn btn-outline btn-lg" href="/our-services/">Explore our services</a></p></div></section>'''
        built.append(page(f'/{slug}/', 'Thank You | Business Relocation Services', 'Thank you for contacting Business Relocation Services.', body, noindex=True))


def build_404():
    body = f'''<section class="sec"><div class="wrap" style="max-width:720px;text-align:center"><h1>Page not found</h1><p style="font-size:1.15rem">Sorry, we couldn’t find that page. Try one of these instead:</p>
<p><a class="btn btn-cta btn-lg" href="/request-a-quote/">Get a Free Quote</a> <a class="btn btn-outline btn-lg" href="/our-services/">Our Services</a> <a class="btn btn-outline btn-lg" href="/">Home</a></p></div></section>'''
    fp = page('/404/', 'Page Not Found | Business Relocation Services', 'Page not found.', body, noindex=True)
    shutil.move(fp, os.path.join(ROOT, '404.html'))
    shutil.rmtree(os.path.join(ROOT, '404'))


def build_seo_files():
    urls = ['/'] + [f'/{s}/' for s in sorted(set(list(SV) + list(EXTRA)))] + ['/request-a-quote/', '/blog/', '/careers/', '/contact-brs-business-relocation-services-new-york-new-jersey/'] + [f'/{p}/' for p in POSTS if p != 'blog']
    seen, out = set(), []
    for u in urls:
        if u not in seen:
            seen.add(u); out.append(u)
    prio = lambda u: '1.0' if u == '/' else '0.9' if u in ('/request-a-quote/', '/office-movers/', '/our-services/') else '0.8' if u.count('/') == 2 and u[1:-1] in SV else '0.6'
    xml = '<?xml version="1.0" encoding="UTF-8"?>\n<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">\n' + ''.join(
        f'<url><loc>{SITE}{u}</loc><lastmod>{TODAY}</lastmod><priority>{prio(u)}</priority></url>\n' for u in out) + '</urlset>\n'
    open(os.path.join(ROOT, 'sitemap.xml'), 'w').write(xml)
    open(os.path.join(ROOT, 'robots.txt'), 'w').write(f'User-agent: *\nAllow: /\nDisallow: /thank-you-\n\nSitemap: {SITE}/sitemap.xml\n')
    return len(out)


def main():
    build_home()
    for s in list(SV) + list(EXTRA):
        build_service(s)
    for p in POSTS:
        if p != 'blog':
            build_post(p)
    build_blog_index(); build_quote(); build_contact(); build_careers(); build_thanks(); build_404()
    n = build_seo_files()
    print(f'built {len(built)} pages, {n} sitemap urls')


if __name__ == '__main__':
    main()
