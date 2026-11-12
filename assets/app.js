/* Job search page: filters, sorting, shareable URLs and saved searches. Uses the shared helpers from site.js. */
(async function () {
  var root = document.getElementById('search');
  if (!root || !window.HRN) return;
  var H = window.HRN;
  var $ = function (id) { return document.getElementById(id); };
  var q = $('q'), cat = $('cat'), lvl = $('lvl'), loc = $('loc'), sal = $('sal'), age = $('age'), sort = $('sort');
  var fRemote = $('f-remote'), fEntry = $('f-entry'), fCrypto = $('f-crypto'), fAny = $('f-any'), perk = $('perk'), etype = $('etype');
  var fReal = $('f-real'), xwords = $('xwords'), xcos = $('xcos');
  var list = $('results'), count = $('count'), more = $('more'), skillbar = $('skills'), saveBtn = $('save-search');
  var ftoggle = $('ftoggle'), fwrap = $('fwrap'), keepShown = false;
  if (ftoggle && fwrap) ftoggle.addEventListener('click', function () {
    var open = fwrap.classList.toggle('open'); ftoggle.setAttribute('aria-expanded', open ? 'true' : 'false');
  });

  var f0 = H.parse(location.search.slice(1));
  q.value = f0.q; cat.value = f0.cat; lvl.value = f0.lvl; loc.value = f0.loc; sal.value = f0.sal ? String(f0.sal) : ''; age.value = f0.age ? String(f0.age) : ''; sort.value = f0.sort;
  fRemote.checked = f0.remote; fEntry.checked = f0.entry; fCrypto.checked = f0.crypto; fAny.checked = f0.any; perk.value = f0.perk; etype.value = f0.etype;
  if (fReal) fReal.checked = f0.real;
  if (xwords) xwords.value = H.mute.w.join(', ');
  var sortTouched = new URLSearchParams(location.search).has('sort');
  var skills = f0.skills.slice();
  var chips = Array.prototype.slice.call(skillbar.querySelectorAll('.chipbtn'));
  var paintChips = function () { chips.forEach(function (c) { c.setAttribute('aria-pressed', skills.indexOf(c.getAttribute('data-skill')) >= 0 ? 'true' : 'false'); }); };
  paintChips();

  // First paint comes from a small file with the newest jobs; the full index replaces it as soon as it has arrived.
  var jobs = [], full = false, allTotal = 0, waiting = false;
  var shown = 50, found = [], extra = new Map(), total = 0;
  var query = function () {
    var p = new URLSearchParams();
    if (q.value.trim()) p.set('q', q.value.trim());
    if (cat.value) p.set('cat', cat.value);
    if (lvl.value) p.set('lvl', lvl.value);
    if (loc.value) p.set('loc', loc.value);
    if (sal.value) p.set('sal', sal.value);
    if (age.value) p.set('age', age.value);
    if (fRemote.checked) p.set('remote', '1');
    if (fEntry.checked) p.set('entry', '1');
    if (fCrypto.checked) p.set('crypto', '1');
    if (fAny.checked) p.set('any', '1');
    if (fReal && fReal.checked) p.set('real', '1');
    if (perk.value) p.set('perk', perk.value);
    if (etype.value) p.set('etype', etype.value);
    if (skills.length) p.set('skills', skills.join(','));
    if (sort.value !== 'new') p.set('sort', sort.value);
    return p.toString();
  };
  var text = function (el) { return el.options[el.selectedIndex].text; };
  var describe = function () {
    var parts = [];
    if (q.value.trim()) parts.push('“' + q.value.trim() + '”');
    [cat, lvl, loc, age, sal, perk, etype].forEach(function (el) { if (el.value) parts.push(text(el)); });
    if (fAny.checked) parts.push('Work from anywhere');
    if (fReal && fReal.checked) parts.push('Fresh openings only');
    if (fRemote.checked) parts.push('Remote');
    if (fEntry.checked) parts.push('Entry-level');
    if (fCrypto.checked) parts.push('Crypto');
    if (skills.length) parts.push(skills.join(' + '));
    return parts.join(' · ') || 'All jobs';
  };
  var render = function () {
    list.innerHTML = found.slice(0, shown).map(function (j) { return H.card(j, extra.get(j[0]) || 0); }).join('');
    count.textContent = total ? total.toLocaleString('en-US') + (total === 1 ? ' job' : ' jobs') : 'No jobs match. Try removing a filter.';
    more.hidden = found.length <= shown; H.decorate(list);
  };
  var run = function () {
    var qs = query(), f = H.parse(qs);
    if (!full && qs) { waiting = true; count.textContent = 'Searching all jobs…'; return; }   // filters need the whole index
    var rows = jobs.filter(function (j) { return H.match(j, f); });
    if (f.sort === 'sal') rows = rows.slice().sort(function (a, b) { return (b[13] || 0) - (a[13] || 0); });
    else if (f.sort === 'rel' && f.words.length) {                 // title matches first, then the rest, newest first inside each group
      var score = function (j) { var t = j[1].toLowerCase(), n = 0; f.words.forEach(function (w) { if (t.indexOf(w) >= 0) n++; }); return n === f.words.length ? 2 : n ? 1 : 0; };
      rows = rows.map(function (j, i) { return [score(j), i, j]; }).sort(function (a, b) { return b[0] - a[0] || a[1] - b[1]; }).map(function (x) { return x[2]; });
    }
    total = full ? rows.length : Math.max(allTotal, rows.length); extra = new Map(); found = H.collapse(rows, extra);
    var active = [cat, lvl, loc, sal, age, perk, etype].filter(function (el) { return el.value; }).length + [fRemote, fEntry, fCrypto, fAny, fReal].filter(function (el) { return el && el.checked; }).length + skills.length;
    if (ftoggle) ftoggle.textContent = 'Filters' + (active ? ' (' + active + ')' : '');
    if (!keepShown) shown = 50;
    render();
    if (pane && wide.matches) {                      // show the first result next to the list
      var open = keepShown && current ? Array.prototype.filter.call(list.querySelectorAll('.job > a'), function (a) { return a.getAttribute('href') === current; })[0] : null;
      if (open) open.parentNode.classList.add('sel');   // the full index arrived: leave the job the visitor is reading alone
      else {
        var firstRow = list.querySelector('.job > a');
        current = '';
        if (firstRow) preview(firstRow); else pane.innerHTML = '<p class="pane-empty">No job selected.</p>';
      }
    }
    history.replaceState(null, '', location.pathname + (qs ? '?' + qs : ''));
    saveBtn.textContent = 'Save this search'; saveBtn.disabled = false;
  };
  var timer;
  // typing a query switches to "best match" unless the visitor picked a sort order themselves
  q.addEventListener('input', function () { if (!sortTouched) sort.value = q.value.trim() ? 'rel' : 'new'; clearTimeout(timer); timer = setTimeout(run, 140); });
  sort.addEventListener('change', function () { sortTouched = true; });
  [cat, lvl, loc, sal, age, perk, etype, sort, fRemote, fEntry, fCrypto, fAny, fReal].forEach(function (el) { if (el) el.addEventListener('change', run); });
  // words and companies the visitor never wants to see: remembered in this browser, applied to every list
  var drawMuted = function () {
    if (!xcos) return;
    var cos = Object.keys(H.mute.c);
    xcos.innerHTML = cos.length ? '<span class="flabel">Hidden companies</span>' + cos.map(function (c) { return '<button class="xchip" type="button" data-c="' + H.esc(c) + '" aria-label="Show ' + H.esc(c) + ' again">' + H.esc(c) + ' ×</button>'; }).join('') : '';
  };
  drawMuted();
  if (xcos) xcos.addEventListener('click', function (ev) {
    var b = ev.target.closest('.xchip'); if (!b) return;
    delete H.mute.c[b.getAttribute('data-c')]; H.saveMute(); drawMuted(); run();
  });
  var xtimer;
  if (xwords) xwords.addEventListener('input', function () {
    clearTimeout(xtimer);
    xtimer = setTimeout(function () {
      H.mute.w = xwords.value.toLowerCase().split(',').map(function (s) { return s.trim(); }).filter(function (s) { return s.length > 1; }).slice(0, 20);
      H.saveMute(); run();
    }, 250);
  });
  skillbar.addEventListener('click', function (ev) {
    var c = ev.target.closest('.chipbtn'); if (!c) return;
    var s = c.getAttribute('data-skill'), i = skills.indexOf(s);
    if (i >= 0) skills.splice(i, 1); else skills.push(s);
    paintChips(); run();
  });
  more.addEventListener('click', function () { shown += 50; render(); });
  var clearBtn = $('fclear');
  if (clearBtn) clearBtn.addEventListener('click', function () {
    [cat, lvl, loc, sal, age, perk, etype].forEach(function (el) { el.value = ''; });
    [fRemote, fEntry, fCrypto, fAny, fReal].forEach(function (el) { if (el) el.checked = false; });
    skills = []; paintChips(); run();
  });

  /* preview pane: on wide screens a click shows the job next to the list instead of leaving the page */
  var pane = $('pane'), wide = window.matchMedia('(min-width: 1240px)'), current = '';
  var preview = function (a) {
    var href = a.getAttribute('href');
    if (!pane || !href || href === current) return;
    current = href;
    list.querySelectorAll('.job.sel').forEach(function (li) { li.classList.remove('sel'); });
    a.parentNode.classList.add('sel');
    fetch(href).then(function (r) { return r.text(); }).then(function (html) {
      if (current !== href) return;
      var main = new DOMParser().parseFromString(html, 'text/html').querySelector('main');
      if (!main) return;
      pane.innerHTML = '<p><a class="pane-open" href="' + href + '">Open full page ↗</a></p>' + main.innerHTML;
      pane.scrollTop = 0; H.bindJob(pane); H.decorate(list);
    }).catch(function () { pane.innerHTML = '<p class="pane-empty">Could not load this job. <a href="' + href + '">Open it in a new page</a>.</p>'; });
  };
  list.addEventListener('click', function (ev) {
    var a = ev.target.closest('.job > a');
    if (!a || !wide.matches || ev.metaKey || ev.ctrlKey || ev.shiftKey || ev.button) return;
    ev.preventDefault(); preview(a);
  });
  var form = $('qform'); if (form) form.addEventListener('submit', function (ev) { ev.preventDefault(); run(); });
  saveBtn.addEventListener('click', function () {
    var all = H.get('hrn_searches', []), qs = query();
    if (!all.some(function (s) { return s.qs === qs; })) all.unshift({ qs: qs, label: describe(), seen: H.today() });
    H.set('hrn_searches', all.slice(0, 30));
    saveBtn.textContent = 'Saved to My jobs ✓'; saveBtn.disabled = true;
  });
  if (!sortTouched && q.value.trim()) sort.value = 'rel';
  var whole = H.load();
  whole.catch(function () {});
  var headP = H.loadHead();
  headP.catch(function () {});
  if (!query()) {
    try { var hd = await headP; if (!full) { jobs = hd.rows; allTotal = hd.total; run(); } } catch (e) {}
  } else count.textContent = 'Searching all jobs…';
  try { jobs = await whole; }
  catch (e) { if (!jobs.length) count.textContent = 'Could not load the list. Please reload the page.'; return; }
  full = true;
  // keep the visitor's place: same order, same number of rows, unless they were waiting for results
  keepShown = !waiting && !query(); run(); keepShown = false;
})();
