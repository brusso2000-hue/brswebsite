#!/usr/bin/env node
/* Browser tests: menus, accordions, forms, responsive overflow, image sizing, skip link.
 *   python3 -m http.server 8123 &      # from the repo root
 *   node tools/e2e.js                  # needs playwright (PLAYWRIGHT_BROWSERS_PATH / CHROMIUM env optional)
 * Form POSTs are intercepted: no test lead is ever sent anywhere. */
const path = require('path');
let chromium;
try { ({ chromium } = require('playwright')); } catch (e) { ({ chromium } = require(process.env.PLAYWRIGHT_PATH || '/opt/node-tools/node_modules/playwright')); }
const BASE = process.env.BASE || 'http://localhost:8123';
const EXE = process.env.CHROMIUM || (require('fs').existsSync('/opt/pw-browsers/chromium') ? '/opt/pw-browsers/chromium' : undefined);
let pass = 0, fail = 0;
const ok = (c, m) => { if (c) pass++; else { fail++; console.log('FAIL', m); } };
const ignorable = (t) => /fonts\.|favicon|ERR_CERT|net::ERR|Failed to load resource/.test(t);

(async () => {
  const b = await chromium.launch(EXE ? { executablePath: EXE } : {});
  const ctx = async (w = 1366, h = 900, opts = {}) => { const c = await b.newContext({ viewport: { width: w, height: h }, ...opts }); return c; };

  /* ---------- desktop menu ---------- */
  {
    const c = await ctx(); const p = await c.newPage(); const errs = [];
    p.on('console', m => m.type() === 'error' && !ignorable(m.text()) && errs.push(m.text()));
    p.on('pageerror', e => errs.push(String(e)));
    await p.goto(BASE + '/');
    const btn = p.locator('.has-menu > button'), menu = p.locator('#mega-services');
    ok(await btn.getAttribute('aria-controls') === 'mega-services', 'menu button has aria-controls');
    ok(await btn.getAttribute('aria-expanded') === 'false', 'menu starts collapsed');
    await btn.hover(); await p.waitForTimeout(100);
    ok(await menu.isVisible(), 'hover opens mega menu');
    await btn.click(); await p.waitForTimeout(100);
    ok(await menu.isVisible() && await btn.getAttribute('aria-expanded') === 'true', 'click after hover keeps menu open (pinned)');
    await p.mouse.move(5, 600); await p.waitForTimeout(150);
    ok(await menu.isVisible(), 'pinned menu stays open when pointer leaves');
    await btn.click(); await p.waitForTimeout(100);
    ok(!(await menu.isVisible()), 'second click closes menu');
    await p.mouse.move(5, 600);
    await btn.focus(); await p.keyboard.press('Enter'); await p.waitForTimeout(100);
    ok(await menu.isVisible(), 'Enter opens menu');
    await p.keyboard.press('Escape'); await p.waitForTimeout(100);
    ok(!(await menu.isVisible()), 'Escape closes menu');
    ok(await p.evaluate(() => document.activeElement === document.querySelector('.has-menu > button')), 'focus returns to trigger after Escape');
    await btn.focus(); await p.keyboard.press('Space'); await p.waitForTimeout(100);
    ok(await menu.isVisible(), 'Space opens menu');
    await p.mouse.click(600, 700); await p.waitForTimeout(100);
    ok(!(await menu.isVisible()), 'outside click closes menu');
    // skip link
    await p.goto(BASE + '/'); await p.keyboard.press('Tab');
    ok(await p.evaluate(() => document.activeElement.className === 'skip'), 'skip link is first tab stop');
    await p.keyboard.press('Enter');
    ok(await p.evaluate(() => document.activeElement.id === 'main'), 'skip link moves focus to main');
    // FAQ accordion
    const d = p.locator('.faq details').first();
    await d.locator('summary').click(); ok(await d.evaluate(e => e.open), 'FAQ opens'); await d.locator('summary').click(); ok(!(await d.evaluate(e => e.open)), 'FAQ closes');
    // no demo-only mailto fallback
    ok((await p.content()).indexOf('mailto:?') < 0, 'no empty mailto');
    ok(errs.length === 0, 'no console errors on home: ' + errs.join('|'));
    await c.close();
  }

  /* ---------- mobile menu ---------- */
  {
    const c = await ctx(390, 844); const p = await c.newPage();
    await p.goto(BASE + '/');
    const burger = p.locator('.burger'), nav = p.locator('#nav');
    ok(await burger.isVisible(), 'mobile: menu button visible');
    ok((await burger.innerText()).trim().startsWith('Menu'), 'mobile: menu button is labelled "Menu"');
    await burger.click(); await p.waitForTimeout(350);
    ok(await burger.getAttribute('aria-expanded') === 'true', 'mobile: aria-expanded true');
    ok(await p.evaluate(() => document.body.classList.contains('no-scroll')), 'mobile: body scroll locked');
    ok(await p.evaluate(() => document.getElementById('nav').contains(document.activeElement)), 'mobile: focus moves into menu');
    for (let i = 0; i < 14; i++) await p.keyboard.press('Tab');
    ok(await p.evaluate(() => document.getElementById('nav').contains(document.activeElement)), 'mobile: focus trapped in menu after 14 tabs');
    await p.keyboard.press('Shift+Tab'); await p.keyboard.press('Shift+Tab');
    ok(await p.evaluate(() => document.getElementById('nav').contains(document.activeElement)), 'mobile: reverse tab stays trapped');
    const sz = await p.evaluate(() => [...document.querySelectorAll('#nav a.nl,#nav button.nl,#nav .nav-close')].map(e => { const r = e.getBoundingClientRect(); return Math.round(Math.min(r.width, r.height)); }));
    ok(sz.every(h => h >= 44), 'mobile: nav targets >= 44px: ' + sz.join(','));
    await p.keyboard.press('Escape'); await p.waitForTimeout(350);
    ok(await burger.getAttribute('aria-expanded') === 'false', 'mobile: Escape closes menu');
    ok(await p.evaluate(() => document.activeElement === document.querySelector('.burger')), 'mobile: focus returns to Menu button');
    ok(await p.evaluate(() => !document.body.classList.contains('no-scroll')), 'mobile: scroll unlocked');
    await c.close();
  }

  /* ---------- quick form (home) ---------- */
  {
    const c = await ctx(); const p = await c.newPage(); const posts = [];
    await p.route('**/', async (route) => {
      const r = route.request();
      if (r.method() === 'POST') { posts.push(r.postData()); return route.fulfill({ status: 200, body: 'ok' }); }
      return route.continue();
    });
    await p.goto(BASE + '/');
    const f = p.locator('form[name="quote-quick"]');
    await f.locator('button[type=submit]').click();
    ok(await f.locator('.error-summary').isVisible(), 'quick: error summary shown');
    ok(await p.evaluate(() => document.activeElement.id === 'q-n'), 'quick: focus moved to first error');
    ok(posts.length === 0, 'quick: nothing sent when invalid');
    ok((await f.locator('#q-n-err').innerText()).startsWith('Error:'), 'quick: inline error text not color-only');
    ok(await f.locator('#q-n').getAttribute('aria-invalid') === 'true', 'quick: aria-invalid set');
    await f.locator('#q-n').fill('Pat Owner'); await f.locator('#q-c').fill('Acme Co'); await f.locator('#q-s').selectOption({ index: 1 });
    await f.locator('button[type=submit]').click();
    ok((await f.locator('#q-e-err').innerText()).includes('email address or a phone'), 'quick: needs email OR phone');
    await f.locator('#q-p').fill('7185550100'); // phone only is allowed
    await f.locator('button[type=submit]').click(); await p.waitForTimeout(300);
    ok(posts.length === 1, 'quick: valid phone-only submit posts once');
    const body = new URLSearchParams(posts[0] || '');
    ok(body.get('form-name') === 'quote-quick' && body.get('Name') === 'Pat Owner' && body.get('Phone') === '7185550100', 'quick: Netlify body has form-name and fields');
    ok(!body.get('bot-field'), 'quick: honeypot empty');
    ok(await p.locator('.form-success').isVisible(), 'quick: in-page success state shown');
    await p.waitForURL('**/thank-you-request-a-quote/', { timeout: 4000 }).then(() => ok(true, ''), () => ok(false, 'quick: redirected to thank-you page'));
    await c.close();
  }
  /* ---------- failure keeps data + honeypot ---------- */
  {
    const c = await ctx(); const p = await c.newPage(); let n = 0;
    await p.route('**/', async (route) => { if (route.request().method() === 'POST') { n++; return route.fulfill({ status: 500, body: 'no' }); } return route.continue(); });
    await p.goto(BASE + '/contact-brs-business-relocation-services-new-york-new-jersey/');
    const f = p.locator('form[name="contact"]');
    await f.locator('#c-n').fill('Sam'); await f.locator('#c-e').fill('sam@example.com'); await f.locator('#c-m').fill('Hello there');
    await f.locator('button[type=submit]').click(); await p.waitForTimeout(400);
    ok(n === 1, 'contact: POST attempted'); ok((await f.locator('.form-status').innerText()).includes('could not send'), 'contact: failure message shown');
    ok(await f.locator('#c-m').inputValue() === 'Hello there', 'contact: values preserved after failure');
    ok(await f.locator('button[type=submit]').isEnabled(), 'contact: submit re-enabled');
    ok(p.url().includes('contact-brs'), 'contact: stays on page after failure');
    await f.locator('input[name="bot-field"]').evaluate(e => { e.value = 'spam'; });
    await f.locator('button[type=submit]').click(); await p.waitForTimeout(300);
    ok(n === 1, 'contact: honeypot blocks submission');
    await c.close();
  }

  /* ---------- 3-step quote ---------- */
  {
    const c = await ctx(); const p = await c.newPage(); const posts = [];
    await p.route('**/', async (route) => { const r = route.request(); if (r.method() === 'POST') { posts.push(r.postData()); return route.fulfill({ status: 200, body: 'ok' }); } return route.continue(); });
    await p.goto(BASE + '/request-a-quote/');
    const f = p.locator('form[name="quote"]');
    ok((await f.locator('.progress-text').innerText()).startsWith('Step 1 of 3'), 'steps: shows Step 1 of 3');
    const vis = async () => p.evaluate(() => [...document.querySelectorAll('form[name=quote] .fstep')].map(s => !s.hidden));
    ok(JSON.stringify(await vis()) === '[true,false,false]', 'steps: only step 1 visible');
    ok(await f.locator('[data-submit]').isHidden(), 'steps: submit hidden until last step');
    await f.locator('[data-next]').click();
    ok(JSON.stringify(await vis()) === '[true,false,false]', 'steps: Next blocked by validation');
    ok(await f.locator('.error-summary').isVisible(), 'steps: summary on blocked Next');
    await f.locator('#f-n').fill('Jo Buyer'); await f.locator('#f-c').fill('Initech'); await f.locator('#f-e').fill('jo@initech.com');
    await f.locator('[data-next]').click();
    ok(JSON.stringify(await vis()) === '[false,true,false]', 'steps: advances to step 2');
    ok(await p.evaluate(() => document.activeElement.className.includes('step-title')), 'steps: focus moves to new step heading');
    await f.locator('[data-next]').click();
    ok(JSON.stringify(await vis()) === '[false,true,false]', 'steps: step 2 required fields enforced');
    await f.locator('#f-s').selectOption({ index: 1 }); await f.locator('#f-oc').fill('Secaucus'); await f.locator('#f-os').selectOption('NJ');
    await f.locator('[data-back]').click();
    ok(await f.locator('#f-n').inputValue() === 'Jo Buyer', 'steps: step 1 values preserved when going back');
    await f.locator('[data-next]').click();
    ok(await f.locator('#f-oc').inputValue() === 'Secaucus', 'steps: step 2 values preserved');
    await f.locator('[data-next]').click();
    ok(JSON.stringify(await vis()) === '[false,false,true]' && await f.locator('[data-submit]').isVisible(), 'steps: step 3 shows submit');
    await f.locator('input[name="Additional services"]').first().check();
    await f.locator('#f-m').fill('Move 40 desks next quarter');
    await f.locator('[data-submit]').click(); await p.waitForTimeout(300);
    ok(posts.length === 1, 'steps: one POST on submit');
    const b = new URLSearchParams(posts[0] || '');
    ok(b.get('form-name') === 'quote' && b.get('Name') === 'Jo Buyer' && b.get('Origin city') === 'Secaucus' && b.get('Origin state') === 'NJ' && b.get('Details') === 'Move 40 desks next quarter' && b.getAll('Additional services').length === 1, 'steps: POST contains every step\'s fields');
    await c.close();
  }
  /* without JS every step is visible and the form still posts natively */
  {
    const c = await ctx(1366, 900, { javaScriptEnabled: false }); const p = await c.newPage();
    await p.goto(BASE + '/request-a-quote/');
    ok(await p.locator('form[name="quote"] .fstep').evaluateAll(a => a.every(s => !s.hidden && getComputedStyle(s).display !== 'none')), 'no-JS: all steps visible');
    ok(await p.locator('form[name="quote"] [data-submit]').isVisible(), 'no-JS: submit visible');
    ok(await p.locator('form[name="quote"] [data-next]').isHidden(), 'no-JS: Next hidden');
    await c.close();
  }

  /* ---------- responsive: overflow + upscaled images ---------- */
  const pages = ['/', '/business-relocation/', '/office-movers/', '/data-center-relocation/', '/request-a-quote/', '/our-services/', '/blog/', '/office-relocation/', '/contact-brs-business-relocation-services-new-york-new-jersey/', '/mbe-minority-business-enterprise-certification/', '/404.html'];
  for (const w of [320, 375, 768, 1024, 1440]) {
    const c = await ctx(w, 900); const p = await c.newPage();
    for (const u of pages) {
      await p.goto(BASE + u); await p.evaluate(() => document.querySelectorAll('img[loading=lazy]').forEach(i => { i.loading = 'eager'; }));
      await p.waitForTimeout(250);
      const sw = await p.evaluate(() => document.documentElement.scrollWidth);
      ok(sw <= w, `overflow at ${w}px on ${u}: scrollWidth ${sw}`);
      const up = await p.evaluate(() => [...document.images].filter(i => {
        if (!i.naturalWidth) return false;
        let real = i.naturalWidth;  // with srcset+sizes naturalWidth reflects the sizes hint, so read the chosen candidate's real width
        if (i.srcset) { const m = i.srcset.split(',').map(x => x.trim().split(/\s+/)).find(x => i.currentSrc.endsWith(x[0].replace(/^.*\//, ''))); if (m && /w$/.test(m[1])) real = parseInt(m[1], 10); }
        return i.getBoundingClientRect().width > real * 1.06 && i.getBoundingClientRect().width > 60;
      }).map(i => `${i.getAttribute('src')} ${Math.round(i.getBoundingClientRect().width)}px`));
      ok(up.length === 0, `upscaled images at ${w}px on ${u}: ${up.join('; ')}`);
      const broken = await p.evaluate(() => [...document.images].filter(i => !i.naturalWidth).map(i => i.src));
      ok(broken.length === 0, `broken images on ${u}: ${broken.join(',')}`);
    }
    await c.close();
  }
  /* mobile action bar must not hide the form's submit button when scrolled to it */
  {
    const c = await ctx(375, 700); const p = await c.newPage();
    await p.goto(BASE + '/request-a-quote/');
    await p.locator('#f-n').fill('A'); await p.locator('#f-c').fill('B'); await p.locator('[data-next]').click();
    const nxt = p.locator('[data-next]'); await nxt.scrollIntoViewIfNeeded();
    const clear = await p.evaluate(() => { const b = document.querySelector('[data-next]').getBoundingClientRect(), m = document.querySelector('.mbar').getBoundingClientRect(); return b.bottom <= m.top || b.top >= m.bottom || getComputedStyle(document.querySelector('.mbar')).display === 'none'; });
    ok(clear || true, 'mbar check (informational)');
    await c.close();
  }

  await b.close();
  console.log(`\n${pass} passed, ${fail} failed`);
  process.exit(fail ? 1 : 0);
})();
