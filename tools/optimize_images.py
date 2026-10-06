#!/usr/bin/env python3
"""One-off asset prep (safe to re-run): trim client logos, make 800px variants, build the 1200x630 share image."""
import os
from PIL import Image, ImageChops
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
D = os.path.join(ROOT, 'assets/img')
LOGOS = ['ATT', 'Verizon', 'Comcast', 'n-b-c', 'Telemundo', 'Well-Fargo', 'Time-Warner-Cable', 'quest-diagnostics-logo',
         'NYC-Health-Hospitals-logo', 'Catholic-Charities-Archdiocese-of-New-York-logo', 'Lane-Office-Furniture-logo', 'Evenson-Best-logo']

for n in LOGOS:
    p = os.path.join(D, n + '.webp')
    im = Image.open(p).convert('RGBA')
    if im.height <= 96:
        continue  # already trimmed
    bg = Image.new('RGBA', im.size, (255, 255, 255, 255))
    flat = Image.alpha_composite(bg, im).convert('RGB')
    diff = ImageChops.difference(flat, Image.new('RGB', im.size, (255, 255, 255))).convert('L').point(lambda v: 255 if v > 18 else 0)
    box = diff.getbbox()
    if not box:
        continue
    pad = 6
    box = (max(0, box[0] - pad), max(0, box[1] - pad), min(im.width, box[2] + pad), min(im.height, box[3] + pad))
    c = flat.crop(box)
    s = min(1, 88 / c.height, 300 / c.width)
    c = c.resize((max(1, round(c.width * s)), max(1, round(c.height * s))), Image.LANCZOS)
    c.save(p, 'WEBP', quality=88, method=6)

for f in sorted(os.listdir(D)):
    b, e = os.path.splitext(f)
    if e != '.webp' or b.endswith('-800') or b in LOGOS:
        continue
    im = Image.open(os.path.join(D, f))
    if im.width > 900:
        out = os.path.join(D, b + '-800.webp')
        if not os.path.exists(out):
            im.convert('RGB').resize((800, round(im.height * 800 / im.width)), Image.LANCZOS).save(out, 'WEBP', quality=78, method=6)

# 1200x630 share image: trucks photo + white logo lockup
src = Image.open(os.path.join(D, 'Office-Movers-BRS-Warehouse-location-Secaucus-NJ.webp')).convert('RGB')
w, h = src.size
src = src.resize((1200, round(h * 1200 / w)), Image.LANCZOS)
top = max(0, (src.height - 630) // 2)
og = src.crop((0, top, 1200, top + 630))
logo = Image.open(os.path.join(ROOT, 'assets/logo.png')).convert('RGBA')
logo.thumbnail((300, 110))
box = Image.new('RGB', (logo.width + 40, logo.height + 30), 'white')
box.paste(logo, (20, 15), logo)
og.paste(box, (40, 630 - box.height - 40))
og.save(os.path.join(ROOT, 'assets/og-default.jpg'), 'JPEG', quality=85, optimize=True, progressive=True)
print('done')
