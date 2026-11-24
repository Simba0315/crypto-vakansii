/* The search filters as menus of our own (owner, 24 Nov 2026: "фильтры не модные а уебищные и местоположение уебищное").
   The native <select> lists opened the system's grey list (a hundred countries with flags in one column). Each filter pill now opens a
   small panel in the site's style: the choices with a tick, a search box where the list is long, and one "Location" control for the
   place (country or region from #loc, or any city typed into #city) instead of two fields side by side.
   The native controls stay in the page (hidden) and keep their ids: a choice here sets their value and fires the same "change" or
   "input" event app.js already listens to, so the search itself is untouched. Labels follow the controls every half second, so a reset
   by app.js ("Clear all", a saved search, the address) shows at once. Keyboard: Enter or Space opens, arrows move, Enter picks, Esc closes. */
(function () {
  var wrap = document.getElementById('fwrap');
  if (!wrap || !document.querySelector('main.srch')) return;
  var esc = function (s) { return String(s).replace(/[&<>"]/g, function (c) { return { '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;' }[c]; }); };
  var open = null;                                   // the panel that is open: { pop, btn, close }

  function closeOpen() { if (open) open.close(); }
  document.addEventListener('click', function (e) { if (open && !open.pop.contains(e.target) && !open.btn.contains(e.target)) closeOpen(); });
  window.addEventListener('resize', closeOpen);
  window.addEventListener('scroll', function () { if (open && !open.sheet) place(open.pop, open.btn); }, { passive: true });

  function place(pop, btn) {
    var r = btn.getBoundingClientRect(), w = Math.max(r.width, pop.offsetWidth), left = Math.min(Math.max(8, r.left), window.innerWidth - w - 8);
    pop.style.top = Math.round(r.bottom + 6) + 'px'; pop.style.left = Math.round(left) + 'px';
  }
  function makePop(btn, label) {
    var pop = document.createElement('div');
    pop.className = 'fx-pop'; pop.setAttribute('role', 'dialog'); pop.setAttribute('aria-label', label);
    document.body.appendChild(pop);
    return pop;
  }
  function show(btn, pop, onOpen) {
    closeOpen();
    var sheet = window.innerWidth < 600;
    pop.classList.toggle('sheet', sheet); pop.hidden = false; btn.setAttribute('aria-expanded', 'true');
    if (!sheet) place(pop, btn);
    open = { pop: pop, btn: btn, sheet: sheet, close: function () { pop.hidden = true; btn.setAttribute('aria-expanded', 'false'); open = null; } };
    if (onOpen) onOpen();
  }
  // arrows, Enter and Esc inside a panel of .fx-o rows
  function keys(pop, btn, pick) {
    pop.addEventListener('keydown', function (e) {
      var rows = [].slice.call(pop.querySelectorAll('.fx-o:not([hidden])')), i = rows.indexOf(document.activeElement);
      if (e.key === 'Escape') { e.preventDefault(); closeOpen(); btn.focus(); }
      else if (e.key === 'ArrowDown') { e.preventDefault(); (rows[i + 1] || rows[0] || {}).focus && (rows[i + 1] || rows[0]).focus(); }
      else if (e.key === 'ArrowUp') { e.preventDefault(); if (i > 0) rows[i - 1].focus(); else { var q = pop.querySelector('.fx-q'); (q || rows[rows.length - 1]).focus(); } }
      else if (e.key === 'Enter' && document.activeElement.classList.contains('fx-o')) { e.preventDefault(); pick(document.activeElement); }
    });
  }
  function rowsHtml(sel) {
    var out = '';
    [].forEach.call(sel.children, function (c) {
      if (c.tagName === 'OPTGROUP') {
        out += '<p class="fx-g">' + esc(c.label) + '</p>';
        [].forEach.call(c.children, function (o) { out += '<button type="button" class="fx-o" role="option" data-v="' + esc(o.value) + '">' + esc(o.textContent) + '</button>'; });
      } else out += '<button type="button" class="fx-o" role="option" data-v="' + esc(c.value) + '">' + esc(c.textContent) + '</button>';
    });
    return out;
  }
  function filterRows(pop, text) {
    var t = text.trim().toLowerCase(), any = false;
    [].forEach.call(pop.querySelectorAll('.fx-o[data-v]'), function (b) { var hit = !t || b.textContent.toLowerCase().indexOf(t) > -1; b.hidden = !hit; if (hit) any = true; });
    [].forEach.call(pop.querySelectorAll('.fx-g'), function (g) {                 // a group title only over rows that are left
      var n = g.nextElementSibling, keep = false;
      while (n && !n.classList.contains('fx-g')) { if (n.classList.contains('fx-o') && !n.hidden) keep = true; n = n.nextElementSibling; }
      g.hidden = !keep;
    });
    return any;
  }
  function mark(pop, v) { [].forEach.call(pop.querySelectorAll('.fx-o[data-v]'), function (b) { var on = b.getAttribute('data-v') === v; b.classList.toggle('sel', on); b.setAttribute('aria-selected', on ? 'true' : 'false'); }); }

  /* one select -> one pill and its panel */
  function menu(sel, searchable) {
    if (!sel || sel.dataset.fx) return null;
    sel.dataset.fx = '1'; sel.classList.add('fx-n');
    var btn = document.createElement('button'), name = sel.getAttribute('aria-label') || '';
    btn.type = 'button'; btn.className = 'fx'; btn.setAttribute('aria-haspopup', 'dialog'); btn.setAttribute('aria-expanded', 'false');
    btn.innerHTML = '<span class="fx-k">' + esc(name) + '</span><span class="fx-v"></span>';
    sel.parentNode.insertBefore(btn, sel);
    var pop = makePop(btn, name);
    pop.hidden = true;
    pop.innerHTML = (searchable ? '<input class="fx-q" type="search" placeholder="Search ' + esc(name.toLowerCase()) + '" aria-label="Search ' + esc(name.toLowerCase()) + '" autocomplete="off">' : '') + '<div class="fx-l" role="listbox" aria-label="' + esc(name) + '">' + rowsHtml(sel) + '</div>';
    var q = pop.querySelector('.fx-q');
    function pick(b) { sel.value = b.getAttribute('data-v'); sel.dispatchEvent(new Event('change', { bubbles: true })); sync(); closeOpen(); btn.focus(); }
    pop.addEventListener('click', function (e) { var b = e.target.closest('.fx-o'); if (b) pick(b); });
    if (q) q.addEventListener('input', function () { filterRows(pop, q.value); });
    keys(pop, btn, pick);
    btn.addEventListener('click', function () {
      if (open && open.pop === pop) return closeOpen();
      show(btn, pop, function () { mark(pop, sel.value); if (q) { q.value = ''; filterRows(pop, ''); q.focus(); } else { var s = pop.querySelector('.fx-o.sel') || pop.querySelector('.fx-o'); if (s) s.focus(); } });
    });
    function sync() {
      var o = sel.options[sel.selectedIndex], on = !!sel.value;
      var t = o ? o.textContent.replace(/^[\u{1F1E6}-\u{1F1FF}]{2}\s*/u, '') : name;
      var v = btn.querySelector('.fx-v'); if (v.textContent !== t) v.textContent = t;
      btn.classList.toggle('on', on);
    }
    sync();
    return sync;
  }

  /* the place: #loc (countries and regions) and #city (any city) as one "Location" pill */
  function placeMenu() {
    var loc = document.getElementById('loc'), city = document.getElementById('city');
    if (!loc || loc.dataset.fx) return null;
    loc.dataset.fx = '1'; loc.classList.add('fx-n'); if (city) city.classList.add('fx-n');
    var cities = [];
    if (city && city.list) [].forEach.call(city.list.options, function (o) { if (o.value) cities.push(o.value); });
    var btn = document.createElement('button');
    btn.type = 'button'; btn.className = 'fx fx-loc'; btn.setAttribute('aria-haspopup', 'dialog'); btn.setAttribute('aria-expanded', 'false');
    btn.innerHTML = '<span class="fx-k">Location</span><span class="fx-v"></span>';
    loc.parentNode.insertBefore(btn, loc);
    var pop = makePop(btn, 'Location');
    pop.hidden = true; pop.classList.add('fx-wide');
    pop.innerHTML = '<input class="fx-q" type="search" placeholder="City, state or country" aria-label="City, state or country" autocomplete="off">'
      + '<button type="button" class="fx-o fx-city" hidden></button>'
      + '<div class="fx-l" role="listbox" aria-label="Location">' + rowsHtml(loc)
      + (cities.length ? '<p class="fx-g">Cities</p>' + cities.map(function (c) { return '<button type="button" class="fx-o" role="option" data-c="' + esc(c) + '" hidden>' + esc(c) + '</button>'; }).join('') : '') + '</div>';
    var q = pop.querySelector('.fx-q'), typed = pop.querySelector('.fx-city'), cityRows = pop.querySelectorAll('.fx-o[data-c]');
    function setCity(v) { if (!city) return; city.value = v; city.dispatchEvent(new Event('input', { bubbles: true })); city.dispatchEvent(new Event('change', { bubbles: true })); }
    function pick(b) {
      if (b.hasAttribute('data-v')) {
        if (city && city.value) setCity('');
        loc.value = b.getAttribute('data-v'); loc.dispatchEvent(new Event('change', { bubbles: true }));
      } else {
        var c = b.getAttribute('data-c') || q.value.trim();
        if (loc.value) { loc.value = ''; loc.dispatchEvent(new Event('change', { bubbles: true })); }
        setCity(c);
      }
      sync(); closeOpen(); btn.focus();
    }
    pop.addEventListener('click', function (e) { var b = e.target.closest('.fx-o'); if (b) pick(b); });
    q.addEventListener('input', function () {
      var t = q.value.trim();
      filterRows(pop, t);
      var n = 0;
      [].forEach.call(cityRows, function (b) { var hit = t.length > 1 && n < 8 && b.textContent.toLowerCase().indexOf(t.toLowerCase()) > -1; b.hidden = !hit; if (hit) n++; });
      var g = pop.querySelector('.fx-l .fx-g:last-of-type'); if (g && cities.length) g.hidden = !n;
      typed.hidden = t.length < 2;
      typed.textContent = 'Jobs in “' + t + '”';
    });
    q.addEventListener('keydown', function (e) { if (e.key === 'Enter' && q.value.trim().length > 1) { e.preventDefault(); pick(typed); } });
    keys(pop, btn, pick);
    btn.addEventListener('click', function () {
      if (open && open.pop === pop) return closeOpen();
      show(btn, pop, function () { mark(pop, loc.value); q.value = ''; q.dispatchEvent(new Event('input')); q.focus(); });
    });
    function sync() {
      var c = city ? city.value.trim() : '', o = loc.options[loc.selectedIndex];
      var t = c || (loc.value && o ? o.textContent.replace(/^[\u{1F1E6}-\u{1F1FF}]{2}\s*/u, '') : 'Anywhere');
      var v = btn.querySelector('.fx-v'); if (v.textContent !== t) v.textContent = t;
      btn.classList.toggle('on', !!(c || loc.value));
    }
    sync();
    return sync;
  }

  var syncs = [placeMenu(), menu(document.getElementById('age')), menu(document.getElementById('cat'), true), menu(document.getElementById('lvl')),
    menu(document.getElementById('sal'))].filter(Boolean);
  // one bar for the five menus (owner, 24 Nov 2026: the row of separate pills still looked cheap): Location, Category, Level, Salary,
  // Posted, each a label over its value, divided by thin lines; the groups are moved, the controls and their ids stay the same
  var bar = document.createElement('div'); bar.className = 'fx-bar'; bar.setAttribute('role', 'group'); bar.setAttribute('aria-label', 'Filters');
  ['loc', 'cat', 'lvl', 'sal', 'age'].forEach(function (id) {
    var c = document.getElementById(id), g = c && c.closest('.fgroup');
    if (g && g.parentNode === wrap) bar.appendChild(g);
  });
  if (bar.children.length) wrap.insertBefore(bar, wrap.firstChild);
  // the on/off chips ("Remote open to <country>", Remote, Hybrid …) in one row under the bar: it wraps on a computer and scrolls sideways on a phone
  var chips = document.createElement('div'), rc = document.getElementById('f-rc-w'), work = wrap.querySelector(':scope > .f-work');
  chips.className = 'fx-chips';
  if (rc) chips.appendChild(rc);
  if (work) chips.appendChild(work);
  if (chips.children.length) wrap.insertBefore(chips, bar.nextSibling);
  // a row that scrolls sideways on a phone fades at its right edge while there is more to the right (style.css); at the end, no fade
  [bar, chips].forEach(function (row) {
    function edge() { row.classList.toggle('at-end', row.scrollLeft + row.clientWidth >= row.scrollWidth - 4); }
    row.addEventListener('scroll', edge, { passive: true });
    window.addEventListener('resize', edge);
    edge();
  });
  setInterval(function () { syncs.forEach(function (f) { f(); }); }, 500);
})();
