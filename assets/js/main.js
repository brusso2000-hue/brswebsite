(function () {
  'use strict';
  var d = document, root = d.documentElement;
  root.classList.add('js');

  var FOCUSABLE = 'a[href],button:not([disabled]),input:not([disabled]):not([type=hidden]),select:not([disabled]),textarea:not([disabled]),summary,[tabindex]:not([tabindex="-1"])';
  var mqMobile = window.matchMedia('(max-width: 960px)');

  /* analytics hooks: only if a dataLayer exists; never sends form values */
  function track(event, detail) {
    try { if (window.dataLayer && window.dataLayer.push) window.dataLayer.push({ event: event, detail: detail || '' }); } catch (e) { /* ignore */ }
  }
  d.addEventListener('click', function (e) {
    var a = e.target.closest && e.target.closest('[data-track]');
    if (a) track(a.getAttribute('data-track'), a.getAttribute('href'));
  });

  /* ---------- mobile menu ---------- */
  var nav = d.getElementById('nav'), burger = d.querySelector('.burger'), scrim = d.querySelector('.scrim');
  function menuOpen() { return nav && nav.classList.contains('open'); }
  function setNav(open) {
    if (!nav || !burger) return;
    nav.classList.toggle('open', open);
    if (scrim) scrim.classList.toggle('on', open);
    burger.setAttribute('aria-expanded', open ? 'true' : 'false');
    d.body.classList.toggle('no-scroll', open);
    if (open) {
      var first = nav.querySelector('.nav-close') || nav.querySelector(FOCUSABLE);
      if (first) first.focus();
    } else {
      closeMenus();
      burger.focus();
    }
  }
  if (burger) burger.addEventListener('click', function () { setNav(!menuOpen()); });
  if (scrim) scrim.addEventListener('click', function () { setNav(false); });
  var closeBtn = d.querySelector('.nav-close');
  if (closeBtn) closeBtn.addEventListener('click', function () { setNav(false); });
  // trap focus inside the open mobile menu
  d.addEventListener('keydown', function (e) {
    if (e.key !== 'Tab' || !menuOpen() || !mqMobile.matches) return;
    var items = Array.prototype.filter.call(nav.querySelectorAll(FOCUSABLE), function (el) { return el.offsetParent !== null; });
    if (!items.length) return;
    var first = items[0], last = items[items.length - 1];
    if (e.shiftKey && d.activeElement === first) { e.preventDefault(); last.focus(); }
    else if (!e.shiftKey && d.activeElement === last) { e.preventDefault(); first.focus(); }
  });
  function onBreakpoint() { if (!mqMobile.matches && menuOpen()) { nav.classList.remove('open'); if (scrim) scrim.classList.remove('on'); d.body.classList.remove('no-scroll'); if (burger) burger.setAttribute('aria-expanded', 'false'); } }
  if (mqMobile.addEventListener) mqMobile.addEventListener('change', onBreakpoint);

  /* ---------- services menu (click, keyboard and hover) ---------- */
  var menus = Array.prototype.slice.call(d.querySelectorAll('.has-menu'));
  function setMenu(m, open, pinned) {
    m.classList.toggle('open', open);
    m.setAttribute('data-pinned', open && pinned ? '1' : '');
    var b = m.querySelector('button');
    if (b) b.setAttribute('aria-expanded', open ? 'true' : 'false');
  }
  function closeMenus(except, returnFocus) {
    menus.forEach(function (m) {
      if (m !== except && m.classList.contains('open')) {
        setMenu(m, false);
        if (returnFocus) { var b = m.querySelector('button'); if (b) b.focus(); }
      }
    });
  }
  var hoverCapable = window.matchMedia('(hover: hover) and (min-width: 961px)').matches;
  menus.forEach(function (m) {
    var b = m.querySelector('button');
    b.addEventListener('click', function (e) {
      e.stopPropagation();
      var open = m.classList.contains('open'), pinned = m.getAttribute('data-pinned') === '1';
      if (open && !pinned) { setMenu(m, true, true); return; }  // opened by hover: a click pins it open
      closeMenus(m);
      setMenu(m, !open, true);
    });
    if (hoverCapable) {
      m.addEventListener('mouseenter', function () { closeMenus(m); if (!m.classList.contains('open')) setMenu(m, true, false); });
      m.addEventListener('mouseleave', function () { if (m.getAttribute('data-pinned') !== '1') setMenu(m, false); });
    }
    m.addEventListener('keydown', function (e) {
      if (e.key === 'Escape' && m.classList.contains('open')) { e.stopPropagation(); setMenu(m, false); b.focus(); }
    });
    m.addEventListener('focusout', function (e) {
      if (!e.relatedTarget || m.contains(e.relatedTarget)) return;
      if (!mqMobile.matches) setMenu(m, false);
    });
  });
  d.addEventListener('click', function (e) { menus.forEach(function (m) { if (!m.contains(e.target)) setMenu(m, false); }); });
  d.addEventListener('keydown', function (e) { if (e.key === 'Escape' && menuOpen()) setNav(false); });

  /* ---------- forms ---------- */
  function labelOf(el) {
    var l = el.id && d.querySelector('label[for="' + el.id + '"]');
    return (l && l.getAttribute('data-label')) || el.name || 'this field';
  }
  function errEl(el) { return el.id && d.getElementById(el.id + '-err'); }
  function setError(el, msg) {
    var e = errEl(el);
    el.setAttribute('aria-invalid', 'true');
    if (e) { e.textContent = 'Error: ' + msg; e.hidden = false; }
  }
  function clearError(el) {
    var e = errEl(el);
    el.removeAttribute('aria-invalid');
    if (e) { e.textContent = ''; e.hidden = true; }
  }
  function isBlank(v) { return !String(v).trim(); }

  // returns [{el, msg}] for the given container
  function validate(scope, form) {
    var errs = [];
    Array.prototype.forEach.call(scope.querySelectorAll('input,select,textarea'), function (el) {
      if (el.type === 'hidden' || el.name === 'bot-field') return;
      clearError(el);
      if (el.required && isBlank(el.value)) {
        errs.push({ el: el, msg: (el.tagName === 'SELECT' ? 'Choose ' : 'Enter ') + labelOf(el).toLowerCase() + '.' });
      } else if (el.type === 'email' && !isBlank(el.value) && !/^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(el.value.trim())) {
        errs.push({ el: el, msg: 'Enter a valid email address, such as name@company.com.' });
      } else if (el.type === 'tel' && !isBlank(el.value) && el.value.replace(/\D/g, '').length < 7) {
        errs.push({ el: el, msg: 'Enter a valid phone number.' });
      }
    });
    // at least one way to reach the visitor
    var group = scope.querySelectorAll('[data-contact]');
    if (group.length) {
      var any = Array.prototype.some.call(group, function (el) { return !isBlank(el.value); });
      if (!any) errs.unshift({ el: group[0], msg: 'Enter an email address or a phone number so we can reach you.' });
    }
    // report in page order so focus lands on the first problem the visitor sees
    errs.sort(function (a, b) { return a.el.compareDocumentPosition(b.el) & 4 ? -1 : 1; });
    errs.forEach(function (x) { setError(x.el, x.msg); });
    return errs;
  }

  function showSummary(form, errs) {
    var box = form.querySelector('.error-summary');
    if (!box) return;
    var ul = box.querySelector('ul');
    ul.innerHTML = '';
    errs.forEach(function (x) {
      var li = d.createElement('li'), a = d.createElement('a');
      a.href = '#' + x.el.id; a.textContent = x.msg;
      a.addEventListener('click', function (ev) { ev.preventDefault(); goTo(form, x.el); });
      li.appendChild(a); ul.appendChild(li);
    });
    box.hidden = !errs.length;
  }
  function goTo(form, el) {
    var step = el.closest && el.closest('.fstep');
    if (step && step.hidden) showStep(form, parseInt(step.getAttribute('data-step'), 10) - 1);
    el.focus();
  }

  /* multi-step state lives on the form element */
  function steps(form) { return Array.prototype.slice.call(form.querySelectorAll('.fstep')); }
  function showStep(form, i, focusTitle) {
    var s = steps(form);
    if (!s.length) return;
    i = Math.max(0, Math.min(s.length - 1, i));
    form._step = i;
    s.forEach(function (el, n) { el.hidden = n !== i; });
    var items = form.querySelectorAll('.progress-list li');
    Array.prototype.forEach.call(items, function (li, n) {
      li.classList.toggle('is-done', n < i);
      li.classList.toggle('is-current', n === i);
      if (n === i) li.setAttribute('aria-current', 'step'); else li.removeAttribute('aria-current');
    });
    var pt = form.querySelector('.progress-text');
    if (pt) pt.textContent = 'Step ' + (i + 1) + ' of ' + s.length + ': ' + s[i].getAttribute('data-title');
    var back = form.querySelector('[data-back]'), next = form.querySelector('[data-next]'), sub = form.querySelector('[data-submit]');
    if (back) back.hidden = i === 0;
    if (next) next.hidden = i === s.length - 1;
    if (sub) sub.hidden = i !== s.length - 1;
    if (focusTitle) { var t = s[i].querySelector('.step-title'); if (t) t.focus(); }
  }

  Array.prototype.forEach.call(d.querySelectorAll('form[data-form]'), function (form) {
    var status = form.querySelector('.form-status'), started = false;
    function say(msg, err) { if (status) { status.textContent = msg; status.className = 'form-status' + (err ? ' err' : ''); } }

    if (form.hasAttribute('data-steps')) {
      showStep(form, 0);
      form.querySelector('[data-next]').addEventListener('click', function () {
        var cur = steps(form)[form._step], errs = validate(cur, form);
        showSummary(form, errs);
        if (errs.length) { errs[0].el.focus(); track('form_validation_error', form.name); return; }
        showSummary(form, []);
        showStep(form, form._step + 1, true);
      });
      form.querySelector('[data-back]').addEventListener('click', function () { showSummary(form, []); showStep(form, form._step - 1, true); });
    }

    form.addEventListener('input', function (e) {
      if (!started) { started = true; track('form_start', form.name); }
      var el = e.target;
      if (el.getAttribute && el.getAttribute('aria-invalid') === 'true') clearError(el);
    });
    form.addEventListener('change', function (e) { if (e.target.getAttribute && e.target.getAttribute('aria-invalid') === 'true') clearError(e.target); });

    form.addEventListener('submit', function (e) {
      e.preventDefault();
      var hp = form.querySelector('[name="bot-field"]');
      if (hp && hp.value) return; // honeypot tripped: silently drop
      var errs = validate(form, form);
      showSummary(form, errs);
      if (errs.length) { goTo(form, errs[0].el); track('form_validation_error', form.name); return; }
      var btn = form.querySelector('[type=submit]');
      if (btn) btn.disabled = true;
      say('Sending your request…');
      var body = new URLSearchParams(new FormData(form)).toString();
      fetch('/', { method: 'POST', headers: { 'Content-Type': 'application/x-www-form-urlencoded' }, body: body })
        .then(function (r) {
          if (!r.ok) throw new Error('status ' + r.status);
          track('form_submit_success', form.name);
          var thanks = form.getAttribute('data-thanks') || '/thank-you-contact-form/';
          var box = d.createElement('div');
          box.className = 'form-success'; box.tabIndex = -1; box.setAttribute('role', 'status');
          box.innerHTML = '<h3>Thank you, your request was sent</h3><p>We will follow up as soon as possible. Redirecting…</p>';
          form.hidden = true; form.parentNode.insertBefore(box, form); box.focus();
          setTimeout(function () { window.location.href = thanks; }, 900);
        })
        .catch(function () {
          if (btn) btn.disabled = false;
          track('form_submit_error', form.name);
          say('Sorry, we could not send your request. Your answers are still here. Please try again, or call 1-718-399-8000 or email info@brsmove.com.', true);
        });
    });
  });
})();
