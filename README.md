# brsmove.com — Business Relocation Services

Static, framework-free site. Every legacy URL is kept, except four near-duplicate pages that now 301 to the page that owns the topic (see `_redirects`).

## Layout
- `index.html`, `*/index.html` — generated pages. Deploy the repo root as-is.
- `assets/` — CSS, JS, self-hosted fonts, logo, WebP images
- `tools/build.py` — generator. `tools/content.json` (legacy blog/careers text) and `tools/services/*.json` (service-page copy) are its inputs. Edit those, then:
  `python3 tools/build.py` (needs Pillow)
- `tools/optimize_images.py` — one-off asset prep (logo trim, 800px variants, share image)
- `sitemap.xml`, `robots.txt`, `_redirects` — written by the build

## Quote forms (Netlify Forms)
All forms POST to Netlify (`data-netlify`, honeypot, `form-name`). Netlify detects them on deploy. To receive leads, open
**Site configuration → Forms → Form notifications** and add an email notification for `quote`, `quote-quick`, `contact` and `careers`.
Forms are `POST`-only: on a plain static server (or before the first Netlify deploy) a submit shows the "could not send" message and keeps the visitor's answers.

## Indexing
`tools/netlify-build.sh` adds `X-Robots-Tag: noindex, nofollow` on any `*.netlify.app` URL and on non-production contexts, and removes it on a custom production domain.
No manual change is needed when `brsmove.com` is attached.

## Tests
```
python3 -m http.server 8123 &
python3 tools/check.py        # static: H1, titles, descriptions, canonicals, schema, links, forms, banned phrases
node tools/e2e.js             # browser: menus, focus trap, forms, 3-step flow, overflow, image sizing (needs playwright)
```
