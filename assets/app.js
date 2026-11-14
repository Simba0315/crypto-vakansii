/* Job search page: filters, sorting, shareable URLs and saved searches. Uses the shared helpers from site.js. */
(async function () {
  var root = document.getElementById('search');
  if (!root || !window.HRN) return;
  var H = window.HRN;
  var $ = function (id) { return document.getElementById(id); };
  var q = $('q'), cat = $('cat'), lvl = $('lvl'), loc = $('loc'), sal = $('sal'), age = $('age'), sort = $('sort');
  var fRemote = $('f-remote'), fEntry = $('f-entry'), fCrypto = $('f-crypto'), fAny = $('f-any'), perk = $('perk'), etype = $('etype');
  var fReal = $('f-real'), fTi = $('f-ti'), fNosal = $('f-nosal'), xwords = $('xwords'), xcos = $('xcos'), fHybrid = $('f-hybrid');
  var xlBoxes = Array.prototype.slice.call(document.querySelectorAll('.f-xl'));
  var xlOf = function () { return xlBoxes.filter(function (b) { return b.checked; }).map(function (b) { return b.value; }); };
  var list = $('results'), count = $('count'), more = $('more'), skillbar = $('skills'), saveBtn = $('save-search');
  var ftoggle = $('ftoggle'), fwrap = $('fwrap'), keepShown = false;
  if (ftoggle && fwrap) ftoggle.addEventListener('click', function () {
    var open = fwrap.classList.toggle('open'); ftoggle.setAttribute('aria-expanded', open ? 'true' : 'false');
  });

  var f0 = H.parse(location.search.slice(1));
  q.value = f0.q; cat.value = f0.cat; lvl.value = f0.lvl; loc.value = f0.loc; sal.value = f0.sal ? String(f0.sal) : ''; age.value = f0.age ? String(f0.age) : ''; sort.value = f0.sort;
  fRemote.checked = f0.remote; fEntry.checked = f0.entry; fCrypto.checked = f0.crypto; fAny.checked = f0.any; perk.value = f0.perk; etype.value = f0.etype;
  if (fReal) fReal.checked = f0.real;
  if (fHybrid) fHybrid.checked = f0.hybrid;
  xlBoxes.forEach(function (b) { b.checked = f0.xl.indexOf(b.value) >= 0; });
  if (fTi) fTi.checked = f0.titles;
  if (fNosal) { fNosal.checked = f0.nosal; fNosal.parentNode.hidden = !(Number(sal.value) > 1); sal.addEventListener('change', function () { fNosal.parentNode.hidden = !(Number(sal.value) > 1); }); }
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
    if (fHybrid && fHybrid.checked) p.set('hybrid', '1');
    if (xlOf().length) p.set('xl', xlOf().join(','));
    if (fEntry.checked) p.set('entry', '1');
    if (fCrypto.checked) p.set('crypto', '1');
    if (fAny.checked) p.set('any', '1');
    if (fReal && fReal.checked) p.set('real', '1');
    if (fTi && fTi.checked) p.set('ti', '1');
    if (fNosal && fNosal.checked && Number(sal.value) > 1) p.set('nosal', '1');
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
    if (fHybrid && fHybrid.checked) parts.push('Hybrid');
    if (xlOf().length) parts.push('No ' + xlOf().join(', ').toLowerCase());
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
  // Words go to the site's search engine (Lucene, on our server) when it is there: it reads the whole text of each posting, forgives a
  // typo and knows synonyms, and sends back every match, best first. The filters on this page then apply to those matches as before.
  // Until it answers, and wherever it is not (offline, an old copy of the site), the words are matched here, in titles and tags.
  var LUC = { q: '', ranks: null, capped: false, fuzzy: false }, lucOK = !!window.fetch, lucAsked = '';
  var lucFor = function (text_) {
    if (!lucOK || !text_) return null;
    if (LUC.q === text_ && LUC.ranks) return LUC;
    if (lucAsked !== text_) {
      lucAsked = text_;
      fetch(H.base + '/api/search?all=1&q=' + encodeURIComponent(text_)).then(function (r) { if (!r.ok) throw 0; return r.json(); }).then(function (d) {
        if (!d || !Array.isArray(d.slugs)) throw 0;
        var ranks = new Map(); d.slugs.forEach(function (s_, i) { ranks.set(s_, i); });
        LUC = { q: text_, ranks: ranks, capped: d.total > d.slugs.length, fuzzy: !!d.fuzzy };
        if (q.value.trim() === text_) { keepShown = false; run(); }
      }).catch(function () { lucOK = false; });
    }
    return null;
  };
  var run = function () {
    var qs = query(), f = H.parse(qs);
    if (!full && qs) { paintApplied(); waiting = true; count.textContent = 'Searching all jobs…'; return; }   // filters need the whole index
    var L = f.words.length && !f.titles ? lucFor(q.value.trim()) : null;
    if (L && L.capped && !L.fuzzy) L = null;         // a word in thousands of jobs: the titles and tags here find them as well; a typo
                                                     // they cannot find, so the engine's 5,000 best matches for the closest spelling stay
    var rows;
    if (L) {
      var fw = Object.assign({}, f, { words: [] });
      rows = jobs.filter(function (j) { return L.ranks.has(j[0]) && H.match(j, fw); });
    } else rows = jobs.filter(function (j) { return H.match(j, f); });
    if (f.sort === 'sal') rows = rows.slice().sort(function (a, b) { return (b[13] || 0) - (a[13] || 0); });
    else if (L && f.sort === 'rel') rows = rows.slice().sort(function (a, b) { return L.ranks.get(a[0]) - L.ranks.get(b[0]); });
    else if (f.sort === 'rel' && f.words.length) {                 // title matches first, then the rest, newest first inside each group
      var score = function (j) { var t = j[1].toLowerCase(), n = 0; f.words.forEach(function (w) { if (t.indexOf(w) >= 0) n++; }); return n === f.words.length ? 2 : n ? 1 : 0; };
      rows = rows.map(function (j, i) { return [score(j), i, j]; }).sort(function (a, b) { return b[0] - a[0] || a[1] - b[1]; }).map(function (x) { return x[2]; });
    }
    total = full ? rows.length : Math.max(allTotal, rows.length); extra = new Map(); found = H.collapse(rows, extra);
    var active = [cat, lvl, loc, sal, age, perk, etype].filter(function (el) { return el.value; }).length + [fRemote, fHybrid, fEntry, fCrypto, fAny, fReal].filter(function (el) { return el && el.checked; }).length + (xlOf().length ? 1 : 0) + skills.length;
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
    paintApplied();
    relax(rows.length, qs);
    if (L && L.fuzzy && rows.length) {               // the engine found nothing for the words as typed and forgave a typo
      hint.innerHTML = 'Nothing for “' + H.esc(q.value.trim()) + '” as typed: showing ' + (L.capped ? 'the ' + L.ranks.size.toLocaleString('en-US') + ' best matches' : 'jobs') + ' for the closest spelling.'; hint.hidden = false;
    }
  };
  // Nothing found: say which single filter stands in the way and how many jobs appear without it, one click each.
  var hint = document.createElement('p'); hint.className = 'relax'; hint.hidden = true; list.parentNode.insertBefore(hint, list);
  // Applied filters as chips: one click on a chip removes that filter; "Clear all" removes every one.
  var applied = document.createElement('p'); applied.className = 'applied'; applied.hidden = true; list.parentNode.insertBefore(applied, hint);
  var paintApplied = function () {
    var items = [];
    if (q.value.trim()) items.push(['q', '“' + q.value.trim() + '”']);
    [['cat', cat], ['lvl', lvl], ['loc', loc], ['sal', sal], ['age', age], ['perk', perk], ['etype', etype]].forEach(function (x) { if (x[1].value) items.push([x[0], text(x[1])]); });
    [['remote', fRemote, 'Remote'], ['hybrid', fHybrid, 'Hybrid'], ['entry', fEntry, 'Entry-level'], ['crypto', fCrypto, 'Crypto'], ['any', fAny, 'Work from anywhere'], ['real', fReal, 'Fresh openings only']].forEach(function (x) { if (x[1] && x[1].checked) items.push([x[0], x[2]]); });
    if (xlOf().length) items.push(['xl', 'No ' + xlOf().join(', ').toLowerCase()]);
    skills.forEach(function (s) { items.push(['skill:' + s, s]); });
    applied.innerHTML = items.map(function (x) { return '<button class="achip" type="button" data-rm="' + H.esc(x[0]) + '" aria-label="Remove filter: ' + H.esc(x[1]) + '">' + H.esc(x[1]) + '<span aria-hidden="true">×</span></button>'; }).join('') +
      (items.length > 1 ? '<button class="linkbtn" type="button" data-rm="*">Clear all</button>' : '');
    applied.hidden = !items.length;
  };
  applied.addEventListener('click', function (ev) {
    var b = ev.target.closest && ev.target.closest('[data-rm]'); if (!b) return;
    var k = b.getAttribute('data-rm');
    var boxes = { remote: fRemote, hybrid: fHybrid, entry: fEntry, crypto: fCrypto, any: fAny, real: fReal }, sels = { cat: cat, lvl: lvl, loc: loc, sal: sal, age: age, perk: perk, etype: etype };
    if (k === 'xl' || k === '*') xlBoxes.forEach(function (x) { x.checked = false; });
    if (k === '*') { q.value = ''; skills = []; Object.keys(boxes).forEach(function (n) { if (boxes[n]) boxes[n].checked = false; }); Object.keys(sels).forEach(function (n) { sels[n].value = ''; }); if (!sortTouched) sort.value = 'new'; }
    else if (k === 'q') { q.value = ''; if (!sortTouched) sort.value = 'new'; }
    else if (k.indexOf('skill:') === 0) skills = skills.filter(function (s) { return s !== k.slice(6); });
    else if (boxes[k]) boxes[k].checked = false; else if (sels[k]) sels[k].value = '';
    paintChips(); run();
  });
  // "Did you mean": a word of the query that no job contains is swapped for the closest word that jobs do contain (one typo for
  // short words, two for long ones; the more common word wins a tie). Shown only when the corrected search finds something.
  var vocab = null, autoFixed = '';
  var dist = function (a, b, lim) {               // edit distance with swapped neighbours counted as one edit, stops early past `lim`
    var m = a.length, n = b.length, d = [], i, k;
    for (i = 0; i <= m; i++) { d[i] = [i]; }
    for (k = 1; k <= n; k++) d[0][k] = k;
    for (i = 1; i <= m; i++) {
      var low = 99;
      for (k = 1; k <= n; k++) {
        var c = a[i - 1] === b[k - 1] ? 0 : 1;
        d[i][k] = Math.min(d[i - 1][k] + 1, d[i][k - 1] + 1, d[i - 1][k - 1] + c);
        if (i > 1 && k > 1 && a[i - 1] === b[k - 2] && a[i - 2] === b[k - 1]) d[i][k] = Math.min(d[i][k], d[i - 2][k - 2] + 1);
        if (d[i][k] < low) low = d[i][k];
      }
      if (low > lim) return lim + 1;
    }
    return d[m][n];
  };
  var suggest = function (words) {
    if (!vocab) {
      vocab = new Map();
      jobs.forEach(function (j) { (j[1] + ' ' + j[2] + ' ' + j[7].join(' ')).toLowerCase().split(/[^a-z0-9+#.]+/).forEach(function (w) { if (w.length > 2) vocab.set(w, (vocab.get(w) || 0) + 1); }); });
    }
    var hays = jobs.map(function (j) { return j[17] || (j[17] = (j[1] + ' ' + j[2] + ' ' + j[3] + ' ' + j[7].join(' ')).toLowerCase()); }), changed = false;
    var out = words.map(function (w) {
      if (w.length < 4 || hays.some(function (h) { return h.indexOf(w) >= 0; })) return w;
      var lim = w.length > 6 ? 2 : 1, best = '', bd = lim + 1, bn = 0;
      vocab.forEach(function (n, v) {
        if (Math.abs(v.length - w.length) > lim) return;
        var x = dist(w, v, lim);
        if (x < bd || (x === bd && n > bn)) { best = v; bd = x; bn = n; }
      });
      if (best && bd <= lim) { changed = true; return best; }
      return w;
    });
    return changed ? out.join(' ') : '';
  };
  var relax = function (n, qs) {
    hint.hidden = true; hint.innerHTML = '';
    if (n || !full || !qs) return;
    var mean = '', p0 = H.parse(qs);
    if (p0.words.length) {
      var fix = suggest(p0.words);
      if (fix) {
        var p1 = new URLSearchParams(qs); p1.set('q', fix);
        var f1 = H.parse(p1.toString()), c1 = 0;
        for (var i1 = 0; i1 < jobs.length; i1++) if (H.match(jobs[i1], f1)) c1++;
        if (c1 && !autoFixed) {                       // show the corrected search right away, and say so
          autoFixed = q.value.trim(); q.value = fix; run();
          hint.innerHTML = 'Showing jobs for “' + H.esc(fix) + '”. <button class="linkbtn" type="button" data-orig="1">Search for “' + H.esc(autoFixed) + '” instead</button>';
          hint.hidden = false; return;
        }
      }
    }
    var p = new URLSearchParams(qs), names = { q: 'the words “' + q.value.trim() + '”', cat: text(cat), lvl: text(lvl), loc: text(loc), sal: text(sal), age: text(age), perk: text(perk), etype: text(etype),
      remote: 'Remote', hybrid: 'Hybrid', xl: 'the levels left out', entry: 'Entry-level', crypto: 'Crypto', any: 'Work from anywhere', real: 'Fresh openings only', skills: skills.join(' + ') }, out = [];
    p.forEach(function (_, k) {
      if (!names[k] || (k === 'q' && mean)) return;           // a spelling fix is the better way out than dropping the words
      var p2 = new URLSearchParams(qs); p2.delete(k);
      var f2 = H.parse(p2.toString()), c = 0;
      for (var i = 0; i < jobs.length; i++) if (H.match(jobs[i], f2)) c++;
      if (c) out.push([c, k, names[k]]);
    });
    if (!out.length && !mean) return;
    out.sort(function (a, b) { return b[0] - a[0]; });
    hint.innerHTML = mean + (out.length ? 'Nothing fits all of that. ' : '') + out.slice(0, 4).map(function (x) {
      return '<button class="linkbtn" type="button" data-drop="' + x[1] + '">Without ' + H.esc(x[2]) + ': ' + x[0].toLocaleString('en-US') + (x[0] === 1 ? ' job' : ' jobs') + '</button>';
    }).join(' ');
    hint.hidden = false;
  };
  hint.addEventListener('click', function (ev) {
    if (ev.target.getAttribute && ev.target.getAttribute('data-orig')) { q.value = autoFixed; autoFixed = '\u0000'; run(); return; }   // keep the visitor's own spelling this time
    var fixQ = ev.target.getAttribute && ev.target.getAttribute('data-q');
    if (fixQ) { q.value = fixQ; run(); return; }
    var k = ev.target.getAttribute && ev.target.getAttribute('data-drop'); if (!k) return;
    var boxes = { remote: fRemote, hybrid: fHybrid, entry: fEntry, crypto: fCrypto, any: fAny, real: fReal }, sels = { cat: cat, lvl: lvl, loc: loc, sal: sal, age: age, perk: perk, etype: etype };
    if (k === 'xl') xlBoxes.forEach(function (x) { x.checked = false; });
    if (k === 'q') q.value = ''; else if (k === 'skills') { skills = []; paintChips(); } else if (boxes[k]) boxes[k].checked = false; else if (sels[k]) sels[k].value = '';
    run();
  });
  var timer;
  // typing a query switches to "best match" unless the visitor picked a sort order themselves
  q.addEventListener('input', function () { autoFixed = ''; if (!sortTouched) sort.value = q.value.trim() ? 'rel' : 'new'; clearTimeout(timer); timer = setTimeout(run, 140); });
  sort.addEventListener('change', function () { sortTouched = true; });
  [cat, lvl, loc, sal, age, perk, etype, sort, fRemote, fHybrid, fEntry, fCrypto, fAny, fReal, fTi, fNosal].concat(xlBoxes).forEach(function (el) { if (el) el.addEventListener('change', run); });
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
    [fRemote, fHybrid, fEntry, fCrypto, fAny, fReal].concat(xlBoxes).forEach(function (el) { if (el) el.checked = false; });
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
  // Smart search: words that are really filters move out of the text box and into the filters, where the visitor can see and undo them.
  // "remote senior python jobs in berlin 150k" becomes: text "python", Remote, Senior, Berlin, $150K+.
  var places = Array.prototype.slice.call(loc.options).filter(function (o) { return o.value; }).map(function (o) {
    var t = o.text.toLowerCase(), names = [t];
    t.split(' & ').forEach(function (part) { names.push(part.replace(/^the /, '')); });
    ({ 'united-states': ['usa', 'united states', 'the us', 'america'], 'united-kingdom': ['uk', 'britain', 'england', 'london'], 'san-francisco': ['san francisco', 'bay area', 'sf'],
       'new-york': ['nyc', 'new york city'], 'washington-dc': ['washington dc', 'dc'], 'uae': ['dubai', 'uae', 'emirates'] }[o.value] || []).forEach(function (a) { names.push(a); });
    return { v: o.value, names: names.filter(function (x, i, a) { return x.length > 1 && a.indexOf(x) === i; }) };
  });
  var rxEsc = function (x) { return x.replace(/[.*+?^${}()|[\]\\]/g, '\\$&'); };
  var smart = function () {
    var text = ' ' + q.value + ' ', took = false;
    var take = function (rx, fn) { if (rx.test(text)) { text = text.replace(rx, ' '); fn(); took = true; } };
    take(/\b(?:work(?:ing)? from anywhere|anywhere in the world|worldwide)\b/i, function () { fAny.checked = true; fRemote.checked = true; });
    take(/\b(?:fully[- ])?remote(?:ly)?\b/i, function () { fRemote.checked = true; });
    take(/\b(?:entry[- ]level|new[- ]grad(?:uate)?s?|graduate)\b/i, function () { fEntry.checked = true; });
    if (!lvl.value) {
      take(/\b(?:internships?|interns?)\b/i, function () { lvl.value = 'Intern'; });
      take(/\b(?:junior|jr\.?)(?=\s)/i, function () { lvl.value = 'Junior'; });
      take(/\b(?:senior|sr\.?)(?=\s)/i, function () { lvl.value = 'Senior'; });
    }
    if (!sal.value) {
      var m = text.match(/(?:\b(?:over|above|from|min(?:imum)?|at least)\s+)?\$?\s?(\d{2,3})\s?k\b\+?|\$\s?(\d{2,3}),?000\b\+?/i);
      if (m) {
        var want = Number(m[1] || m[2]) * 1000, best = '';
        Array.prototype.forEach.call(sal.options, function (o) { var v = Number(o.value); if (v >= 1000 && v <= want) best = o.value; });
        if (best) { sal.value = best; text = text.replace(m[0], ' '); took = true; }
      }
    }
    if (!loc.value) {
      var hit = null;
      places.forEach(function (p) { p.names.forEach(function (nm) {
        var rx = new RegExp('(?:\\b(?:in|near|at)\\s+)?\\b' + rxEsc(nm) + '\\b', 'i'), mm = text.match(rx);
        if (mm && (!hit || mm[0].length > hit.len)) hit = { v: p.v, rx: rx, len: mm[0].length };
      }); });
      if (hit) { loc.value = hit.v; text = text.replace(hit.rx, ' '); took = true; }
    }
    if (took || /\b(?:jobs?|roles|positions?|vacanc(?:y|ies)|openings?)\b/i.test(text)) {
      text = text.replace(/\b(?:jobs?|roles|positions?|vacanc(?:y|ies)|openings?)\b/gi, ' ').replace(/\s+(?:in|at|near|for|with|and|paying|that pay)\s*$/i, ' ').replace(/^\s*(?:in|at|near|for|with|and)\s+/i, ' ');
      q.value = text.replace(/\s+/g, ' ').trim();
    }
    return took;
  };
  var form = $('qform'); if (form) form.addEventListener('submit', function (ev) { ev.preventDefault(); smart(); run(); });
  q.addEventListener('change', function () { if (smart()) run(); });
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
  // Near you: one click narrows the list to the visitor's country (taken from the time zone, or the place they picked on the home page)
  fetch(H.base + '/data/geo.json').then(function (r) { return r.json(); }).then(function (G) {
    var tz = ''; try { tz = Intl.DateTimeFormat().resolvedOptions().timeZone || ''; } catch (e) {}
    var c = G.c[H.get('hrn_place', '') || G.tz[tz] || ''];
    if (!c || !c[1] || !c[2] || !Array.prototype.some.call(loc.options, function (o) { return o.value === c[1]; })) return;
    var b = document.createElement('button'); b.type = 'button'; b.className = 'linkbtn nearbtn';
    b.textContent = 'Near you: only ' + c[0] + ' (' + Number(c[2]).toLocaleString('en-US') + ')';
    b.addEventListener('click', function () { loc.value = c[1]; run(); b.hidden = true; });
    b.hidden = !!loc.value;
    loc.addEventListener('change', function () { b.hidden = !!loc.value; });
    count.parentNode.insertBefore(b, count.nextSibling);
  }).catch(function () {});
  var wh = new URLSearchParams(location.search).get('where');          // the "where" field of the home page search
  if (wh) q.value = (q.value + ' in ' + wh).trim();
  if (q.value) smart();              // a query typed on the home page arrives here as text: read the filters out of it
  keepShown = !waiting && !query(); run(); keepShown = false;
})();
