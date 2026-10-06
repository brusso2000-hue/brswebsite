(function () {
  var d = document, root = d.documentElement;
  root.classList.add('js');

  // Header shadow
  var header = d.querySelector('.header');
  function onScroll() { if (header) header.classList.toggle('scrolled', window.scrollY > 8); }
  onScroll(); window.addEventListener('scroll', onScroll, { passive: true });

  // Mobile nav
  var nav = d.getElementById('nav'), burger = d.querySelector('.burger'), scrim = d.querySelector('.scrim');
  function setNav(open) {
    if (!nav) return;
    nav.classList.toggle('open', open);
    if (scrim) scrim.classList.toggle('on', open);
    if (burger) burger.setAttribute('aria-expanded', open ? 'true' : 'false');
  }
  if (burger) burger.addEventListener('click', function () { setNav(!nav.classList.contains('open')); });
  if (scrim) scrim.addEventListener('click', function () { setNav(false); });
  var close = d.querySelector('.nav-close'); if (close) close.addEventListener('click', function () { setNav(false); });

  // Services mega menu
  var menus = d.querySelectorAll('.has-menu');
  function closeMenus(except) {
    menus.forEach(function (m) {
      if (m !== except) { m.classList.remove('open'); var b = m.querySelector('button'); if (b) b.setAttribute('aria-expanded', 'false'); }
    });
  }
  menus.forEach(function (m) {
    var b = m.querySelector('button');
    b.addEventListener('click', function (e) {
      e.stopPropagation();
      var o = !m.classList.contains('open');
      closeMenus(m); m.classList.toggle('open', o); b.setAttribute('aria-expanded', o ? 'true' : 'false');
    });
    if (window.matchMedia('(hover:hover) and (min-width:961px)').matches) {
      m.addEventListener('mouseenter', function () { closeMenus(m); m.classList.add('open'); b.setAttribute('aria-expanded', 'true'); });
      m.addEventListener('mouseleave', function () { m.classList.remove('open'); b.setAttribute('aria-expanded', 'false'); });
    }
  });
  d.addEventListener('click', function () { closeMenus(); });
  d.addEventListener('keydown', function (e) { if (e.key === 'Escape') { closeMenus(); setNav(false); } });

  // Scroll reveal
  var items = d.querySelectorAll('.reveal');
  if ('IntersectionObserver' in window) {
    var io = new IntersectionObserver(function (es) {
      es.forEach(function (e) { if (e.isIntersecting) { e.target.classList.add('in'); io.unobserve(e.target); } });
    }, { rootMargin: '0px 0px -8% 0px' });
    items.forEach(function (el) { io.observe(el); });
  } else { items.forEach(function (el) { el.classList.add('in'); }); }

  // Forms: POST to the endpoint set in <meta name="form-endpoint"> when present,
  // otherwise fall back to opening the visitor's email client addressed to BRS.
  var epMeta = d.querySelector('meta[name="form-endpoint"]');
  var endpoint = epMeta ? epMeta.content : '';
  var mailTo = (d.querySelector('meta[name="form-mailto"]') || {}).content || 'info@brsmove.com';

  d.querySelectorAll('form[data-form]').forEach(function (form) {
    var status = form.querySelector('.form-status');
    function say(msg, err) { if (status) { status.textContent = msg; status.className = 'form-status' + (err ? ' err' : ''); } }
    form.addEventListener('submit', function (e) {
      e.preventDefault();
      if (form.querySelector('.hp input') && form.querySelector('.hp input').value) return; // honeypot
      if (!form.checkValidity()) { form.reportValidity(); return; }
      var fd = new FormData(form);
      var subject = form.getAttribute('data-subject') || 'Website enquiry';
      var thanks = form.getAttribute('data-thanks') || '/thank-you-contact-form/';
      var btn = form.querySelector('button[type=submit]');
      if (endpoint) {
        if (btn) { btn.disabled = true; }
        say('Sending…');
        fd.append('_subject', subject);
        fetch(endpoint, { method: 'POST', body: fd, headers: { Accept: 'application/json' } })
          .then(function (r) { if (!r.ok) throw new Error(r.status); window.location.href = thanks; })
          .catch(function () { if (btn) btn.disabled = false; say('Sorry, something went wrong. Please call 1-718-399-8000 or email ' + mailTo + '.', true); });
      } else {
        var lines = [], seen = {};
        fd.forEach(function (v, k) {
          if (k.charAt(0) === '_' || !String(v).trim()) return;
          var key = k.replace(/\[\]$/, '');
          if (seen[key] !== undefined) { lines[seen[key]] += ', ' + v; return; }
          seen[key] = lines.length; lines.push(key + ': ' + v);
        });
        window.location.href = 'mailto:' + mailTo + '?subject=' + encodeURIComponent(subject) + '&body=' + encodeURIComponent(lines.join('\n'));
        say('Opening your email app… if nothing happens, call 1-718-399-8000 or email ' + mailTo + '.');
      }
    });
  });
})();
