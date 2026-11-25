/* Job search page: filters, sorting, shareable URLs and saved searches. Uses the shared helpers from site.js.
   The list comes from the server: the page sends its own address to /api/search?list=1 (Lucene on our server, search_engine.py) and
   gets 50 rows back, best or newest first, one row per role; "Show more" asks for the next 50. With no filter the first screen is in
   the page itself (#srch-first), so nothing is waited for. Until 25 Nov 2026 the page downloaded every open job (22 MB, 450 MB of a
   browser's memory) and filtered here; a phone took seconds or closed the tab. */
(function () {
  var root = document.getElementById('search');
  if (!root || !window.HRN) return;
  var H = window.HRN;
  var $ = function (id) { return document.getElementById(id); };
  var q = $('q'), cat = $('cat'), lvl = $('lvl'), loc = $('loc'), sal = $('sal'), age = $('age'), sort = $('sort');
  var city = $('city') || { value: '', addEventListener: function () {} };      // a city typed by the visitor (any city in a posting's place line)
  var fRemote = $('f-remote'), fEntry = $('f-entry'), fCrypto = $('f-crypto'), fAny = $('f-any'), perk = $('perk'), etype = $('etype');
  var fHa = $('f-ha'); if (fHa) { fHa.checked = !!H.get('hrn_hide_applied', false); fHa.addEventListener('change', function () { H.set('hrn_hide_applied', fHa.checked); run(); }); }
  var fRc = $('f-rc'), rcCC = (new URLSearchParams(location.search).get('rc') || '').toUpperCase();
  if (fRc) { fRc.checked = !!rcCC; if (rcCC) $('f-rc-w').hidden = false; }
  var lastQ = H.get('hrn_lastq', null);
  if (lastQ && lastQ.qs && !location.search) {          // back on the search page with no filters: one tap brings the last search back
    var lq = document.createElement('p'); lq.className = 'lastq note';
    lq.innerHTML = 'Continue your last search: <a href="?' + H.esc(lastQ.qs) + '">' + H.esc(lastQ.label || 'your filters') + '</a>';
    var cnt0 = $('count'); if (cnt0 && cnt0.parentNode) cnt0.parentNode.insertBefore(lq, cnt0);
  }
  var fReal = $('f-real'), fTi = $('f-ti'), fNosal = $('f-nosal'), xwords = $('xwords'), xcos = $('xcos'), fHybrid = $('f-hybrid');
  var xlBoxes = Array.prototype.slice.call(document.querySelectorAll('.f-xl'));
  var xlOf = function () { return xlBoxes.filter(function (b) { return b.checked; }).map(function (b) { return b.value; }); };
  var list = $('results'), count = $('count'), more = $('more'), skillbar = $('skills'), saveBtn = $('save-search'), down = $('srch-down');
  list.setAttribute('aria-busy', 'true');      // until the first results the empty list is drawn as rows still loading (style.css, main.srch); show() takes the mark off
  var ftoggle = $('ftoggle'), fwrap = $('fwrap');
  if (ftoggle && fwrap) ftoggle.addEventListener('click', function () {
    var open = fwrap.classList.toggle('open'); ftoggle.setAttribute('aria-expanded', open ? 'true' : 'false');
  });

  var f0 = H.parse(location.search.slice(1));
  q.value = f0.q; cat.value = f0.cat; lvl.value = f0.lvl; loc.value = f0.loc; city.value = f0.city || ''; sal.value = f0.sal ? String(f0.sal) : ''; age.value = f0.age ? String(f0.age) : ''; sort.value = f0.sort;
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

  // The first page with no filter came with the page: the newest roles, in the rows the server answers with (search_engine.row)
  var first = null;
  try { first = JSON.parse(($('srch-first') || {}).textContent || 'null'); } catch (e) {}
  if (first && first.jobs) { first.more = first.jobs.length >= 50; first.without = {}; } else first = null;
  var found = [], extra = new Map(), total = 0, got = 0, asked = 0, ctl = null, slow;
  var query = function () {
    var p = new URLSearchParams();
    if (q.value.trim()) p.set('q', q.value.trim());
    if (cat.value) p.set('cat', cat.value);
    if (lvl.value) p.set('lvl', lvl.value);
    if (loc.value) p.set('loc', loc.value);
    if (city.value.trim()) p.set('city', city.value.trim());
    if (fRc && fRc.checked && rcCC) p.set('rc', rcCC);
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
    if (city.value.trim()) parts.push('in ' + city.value.trim());
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
  // what the visitor keeps out of every list, in this browser: companies and title words go to the server with the search; jobs marked
  // "Not interested" and, when asked, jobs already applied to are taken out of the rows here
  var muted = function () { return Object.keys(H.mute.c).length > 0 || H.mute.w.length > 0; };
  var hid = {}, done = null;          // read once per answer (show)
  var keep = function (j) {
    if (hid[j[0]] || (done && done[j[0]]) || H.mute.c[j[2]]) return false;
    var low = j[1].toLowerCase();
    for (var w = 0; w < H.mute.w.length; w++) if (low.indexOf(H.mute.w[w]) >= 0) return false;
    return true;
  };
  // The address asked of the server: the page's own, keys in one order and the words in lower case, so one search is one answer
  // in the caches (nginx keeps each answer 2 minutes, serve.py one minute)
  var apiUrl = function (qs, offset) {
    var p = new URLSearchParams(qs), out = new URLSearchParams(), keys = [];
    out.set('list', '1');
    p.forEach(function (_, k) { if (keys.indexOf(k) < 0) keys.push(k); });
    keys.sort().forEach(function (k) { var v = p.get(k); out.set(k, k === 'q' ? v.toLowerCase().replace(/\s+/g, ' ').trim() : v); });
    Object.keys(H.mute.c).sort().forEach(function (c) { out.append('xc', c); });
    H.mute.w.slice().sort().forEach(function (w) { out.append('xw', w); });
    if (offset) out.set('offset', String(offset));
    return H.base + '/api/search?' + out.toString();
  };
  var ask = function (qs, offset) {
    if (ctl) try { ctl.abort(); } catch (e) {}
    ctl = window.AbortController ? new AbortController() : null;
    var my = ++asked;
    return fetch(apiUrl(qs, offset), ctl ? { signal: ctl.signal } : {}).then(function (r) {
      if (!r.ok) throw new Error('search answered ' + r.status);
      return r.json();
    }).then(function (d) {
      if (my !== asked) throw { stale: true };
      if (!d || !Array.isArray(d.jobs)) throw new Error('search answered without jobs');
      return d;
    }, function (err) { if (my !== asked) throw { stale: true }; throw err; });
  };
  var paintCount = function () {
    count.textContent = total ? total.toLocaleString('en-US') + (total === 1 ? ' job' : ' jobs') : 'No jobs match. Try removing a filter.';
  };
  // rows of an answer into the list: a new list, or the next page under the rows already there ("Show more")
  var show = function (d, append) {
    clearTimeout(slow);
    var rows = [], fresh = [];
    hid = H.get('hrn_hidden', {}); done = H.parse('').done;
    if (!append) { found = []; got = 0; extra = new Map(); }
    d.jobs.forEach(function (a) { var j = H.fromApi(a); rows.push(j); if (keep(j)) { fresh.push(j); if (a[17]) extra.set(j[0], a[17]); } });
    found = found.concat(fresh); got += rows.length; total = d.total;
    var html = fresh.map(function (j) { return H.card(j, extra.get(j[0]) || 0); }).join('');
    if (append) list.insertAdjacentHTML('beforeend', html); else list.innerHTML = html;
    list.removeAttribute('aria-busy'); if (down) down.hidden = true; more.disabled = false; more.textContent = 'Show more';
    paintCount();
    more.hidden = !d.more; H.decorate(list);
    if (append) return;
    if (pane && wide.matches) {                      // show the first result next to the list
      var firstRow = list.querySelector('.job > a');
      current = '';
      if (firstRow) preview(firstRow); else pane.innerHTML = '<p class="pane-empty">No job selected.</p>';
    }
    relax(d);
  };
  // The search did not answer (the server is down or busy, or the connection dropped): say so, keep the filters, and offer the lists
  // that need no search. Never the list of every job instead: that was 22 MB.
  var fail = function (err) {
    if (err && (err.stale || err.name === 'AbortError')) return;
    clearTimeout(slow);
    found = []; got = 0; list.innerHTML = ''; list.removeAttribute('aria-busy'); more.hidden = true; more.disabled = false; hint.hidden = true;
    count.textContent = navigator.onLine === false ? 'You are offline.' : 'Search is not answering right now.';
    if (down) {
      $('srch-down-t').innerHTML = (navigator.onLine === false ? 'No connection, so this search cannot be listed. ' : 'Our search is not answering for a moment, so this search cannot be listed. ') +
        '<button class="linkbtn" type="button" data-retry="1">Try again</button> or browse the lists below.';
      down.hidden = false;
    }
    if (pane) pane.innerHTML = '<p class="pane-empty">No job selected.</p>';
  };
  if (down) down.addEventListener('click', function (ev) { if (ev.target.getAttribute && ev.target.getAttribute('data-retry')) run(); });
  var run = function () {
    var qs = query();
    var active = [cat, lvl, loc, city, sal, age, perk, etype].filter(function (el) { return el.value; }).length + [fRemote, fHybrid, fEntry, fCrypto, fAny, fReal].filter(function (el) { return el && el.checked; }).length + (xlOf().length ? 1 : 0) + skills.length;
    if (ftoggle) ftoggle.textContent = 'Filters' + (active ? ' (' + active + ')' : '');
    if (fwrap) {                                  // the filter bar: a chosen filter is a filled pill, "Clear all" shows only when one is chosen,
      fwrap.classList.toggle('has-on', active > 0);  // and "All filters" counts the chosen ones it hides
      [cat, lvl, loc, city, sal, age, perk, etype].forEach(function (el) { el.classList.toggle('on', !!el.value); });
      var mfs = fwrap.querySelector('.morefilters summary');
      var hid = [perk, etype].filter(function (el) { return el.value; }).length + [fReal, fTi].filter(function (el) { return el && el.checked; }).length + (xlOf().length ? 1 : 0) + skills.length;
      if (mfs) mfs.setAttribute('data-n', hid ? String(hid) : '');
    }
    history.replaceState(null, '', location.pathname + (qs ? '?' + qs : ''));
    if (qs) H.set('hrn_lastq', { qs: qs, label: describe() });
    saveBtn.textContent = 'Save this search'; saveBtn.disabled = false;
    paintApplied();
    hint.hidden = true; hint.innerHTML = '';
    if (!qs && first && !muted()) {                  // nothing chosen: the first page that came with the page, no request at all
      if (ctl) try { ctl.abort(); } catch (e) {}
      asked++; show(first, false); return;
    }
    list.setAttribute('aria-busy', 'true'); more.hidden = true;
    clearTimeout(slow); slow = setTimeout(function () { count.textContent = 'Searching…'; }, 400);
    ask(qs, 0).then(function (d) { show(d, false); }, fail);
  };
  // Nothing found: say which single filter stands in the way and how many jobs appear without it, one click each (the server counts them).
  var hint = document.createElement('p'); hint.className = 'relax'; hint.hidden = true; list.parentNode.insertBefore(hint, list);
  // Applied filters as chips: one click on a chip removes that filter; "Clear all" removes every one.
  var applied = document.createElement('p'); applied.className = 'applied'; applied.hidden = true; list.parentNode.insertBefore(applied, hint);
  var paintApplied = function () {
    var items = [];
    if (q.value.trim()) items.push(['q', '“' + q.value.trim() + '”']);
    [['cat', cat], ['lvl', lvl], ['loc', loc], ['sal', sal], ['age', age], ['perk', perk], ['etype', etype]].forEach(function (x) { if (x[1].value) items.push([x[0], text(x[1])]); });
    if (city.value.trim()) items.push(['city', city.value.trim()]);
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
    var boxes = { remote: fRemote, hybrid: fHybrid, entry: fEntry, crypto: fCrypto, any: fAny, real: fReal }, sels = { cat: cat, lvl: lvl, loc: loc, city: city, sal: sal, age: age, perk: perk, etype: etype };
    if (k === 'xl' || k === '*') xlBoxes.forEach(function (x) { x.checked = false; });
    if (k === '*') { q.value = ''; skills = []; Object.keys(boxes).forEach(function (n) { if (boxes[n]) boxes[n].checked = false; }); Object.keys(sels).forEach(function (n) { sels[n].value = ''; }); if (!sortTouched) sort.value = 'new'; }
    else if (k === 'q') { q.value = ''; if (!sortTouched) sort.value = 'new'; }
    else if (k.indexOf('skill:') === 0) skills = skills.filter(function (s) { return s !== k.slice(6); });
    else if (boxes[k]) boxes[k].checked = false; else if (sels[k]) sels[k].value = '';
    paintChips(); run();
  });
  // A typo: the server found nothing (or only a few) for the words as typed and listed the closest spelling instead; nothing at all:
  // the filters that stand in the way, with what is left without each.
  var relax = function (d) {
    var words = q.value.trim();
    if (d.fuzzy && total) {
      hint.innerHTML = (d.exact ? 'Only ' + d.exact + (d.exact === 1 ? ' job matches “' : ' jobs match “') + H.esc(words) + '” as typed' : 'Nothing for “' + H.esc(words) + '” as typed') +
        ': showing jobs for the closest spelling.';
      hint.hidden = false; return;
    }
    if (total || !d.without) return;
    var names = { q: 'the words “' + words + '”', cat: text(cat), lvl: text(lvl), loc: text(loc), city: city.value.trim(), sal: text(sal), age: text(age), perk: text(perk), etype: text(etype),
      remote: 'Remote', hybrid: 'Hybrid', xl: 'the levels left out', entry: 'Entry-level', crypto: 'Crypto', any: 'Work from anywhere', real: 'Fresh openings only', skills: skills.join(' + ') };
    var out = Object.keys(d.without).filter(function (k) { return names[k] && d.without[k] > 0; }).map(function (k) { return [d.without[k], k, names[k]]; });
    if (!out.length) return;
    out.sort(function (a, b) { return b[0] - a[0]; });
    hint.innerHTML = 'Nothing fits all of that. ' + out.slice(0, 4).map(function (x) {
      return '<button class="linkbtn" type="button" data-drop="' + x[1] + '">Without ' + H.esc(x[2]) + ': ' + x[0].toLocaleString('en-US') + (x[0] === 1 ? ' job' : ' jobs') + '</button>';
    }).join(' ');
    hint.hidden = false;
  };
  hint.addEventListener('click', function (ev) {
    var fixQ = ev.target.getAttribute && ev.target.getAttribute('data-q');
    if (fixQ) { q.value = fixQ; run(); return; }
    var k = ev.target.getAttribute && ev.target.getAttribute('data-drop'); if (!k) return;
    var boxes = { remote: fRemote, hybrid: fHybrid, entry: fEntry, crypto: fCrypto, any: fAny, real: fReal }, sels = { cat: cat, lvl: lvl, loc: loc, city: city, sal: sal, age: age, perk: perk, etype: etype };
    if (k === 'xl') xlBoxes.forEach(function (x) { x.checked = false; });
    if (k === 'q') q.value = ''; else if (k === 'skills') { skills = []; paintChips(); } else if (boxes[k]) boxes[k].checked = false; else if (sels[k]) sels[k].value = '';
    run();
  });
  var timer;
  // typing a query switches to "best match" unless the visitor picked a sort order themselves; the server is asked once typing pauses
  q.addEventListener('input', function () { if (!sortTouched) sort.value = q.value.trim() ? 'rel' : 'new'; clearTimeout(timer); timer = setTimeout(run, 300); });
  sort.addEventListener('change', function () { sortTouched = true; });
  var ctimer; city.addEventListener('input', function () { clearTimeout(ctimer); ctimer = setTimeout(run, 400); });
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
    }, 400);
  });
  skillbar.addEventListener('click', function (ev) {
    var c = ev.target.closest('.chipbtn'); if (!c) return;
    var s = c.getAttribute('data-skill'), i = skills.indexOf(s);
    if (i >= 0) skills.splice(i, 1); else skills.push(s);
    paintChips(); run();
  });
  more.addEventListener('click', function () {                // the next 50 rows of the same search
    more.disabled = true;
    ask(query(), got).then(function (d) { show(d, true); }, function (err) {
      if (err && (err.stale || err.name === 'AbortError')) return;
      more.disabled = false; more.textContent = 'Could not load more. Try again';
    });
  });
  var clearBtn = $('fclear');
  if (clearBtn) clearBtn.addEventListener('click', function () {
    [cat, lvl, loc, city, sal, age, perk, etype].forEach(function (el) { el.value = ''; });
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
      Array.prototype.forEach.call(main.querySelectorAll('h1'), function (h) {       // one H1 per page: the job's title becomes an H2 in the preview
        var h2 = main.ownerDocument.createElement('h2'); h2.className = 'pane-h'; h2.innerHTML = h.innerHTML; h.replaceWith(h2);
      });
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
    var t = o.text.replace(/^[\u{1F1E6}-\u{1F1FF}]{2}\s*/u, '').toLowerCase(), names = [t];
    t.split(' & ').forEach(function (part) { names.push(part.replace(/^the /, '')); });
    if (/, [a-z]{2}$/.test(t)) names.push(t.replace(/, [a-z]{2}$/, ''));         // "New York, NY" is typed "new york"
    ({ 'united-states': ['usa', 'united states', 'the us', 'america'], 'united-kingdom': ['uk', 'britain', 'england', 'united kingdom'], 'san-francisco': ['san francisco', 'bay area', 'sf'],
       'new-york': ['nyc', 'new york city'], 'washington-dc': ['washington dc', 'dc'], 'uae': ['dubai', 'uae', 'emirates'] }[o.value] || []).forEach(function (a) { names.push(a); });
    return { v: o.value, names: names.filter(function (x, i, a) { return x.length > 1 && a.indexOf(x) === i; }) };
  });
  var rxEsc = function (x) { return x.replace(/[.*+?^${}()|[\]\\]/g, '\\$&'); };
  // the cities in today's postings (the build counts them into the City box's suggestions)
  var cityNames = Array.prototype.map.call(($('city-list') || { options: [] }).options, function (o) { return o.value.toLowerCase(); });
  var smart = function () {
    var text = ' ' + q.value + ' ', took = false;
    var take = function (rx, fn) { if (rx.test(text)) { text = text.replace(rx, ' '); fn(); took = true; } };
    take(/\b(?:work(?:ing)? from anywhere|anywhere in the world|worldwide)\b/i, function () { fAny.checked = true; fRemote.checked = true; });
    take(/\b(?:fully[- ])?remote(?:ly)?\b/i, function () { fRemote.checked = true; });
    if (fHybrid) take(/\bhybrid\b/i, function () { fHybrid.checked = true; });
    take(/\b(?:entry[- ]level|new[- ]grad(?:uate)?s?|graduate|no experience(?: needed| required)?)\b/i, function () { fEntry.checked = true; });
    // LinkedIn's search reads a plain sentence ("entry level design jobs in the US", 20 Nov 2026): the same here for the type of work,
    // how recent, the perks and "pay listed", each only when its filter is still empty
    if (!etype.value) {
      take(/\bpart[- ]?time\b/i, function () { etype.value = 'Part-time'; });
      take(/\bfull[- ]?time\b/i, function () { etype.value = 'Full-time'; });
      take(/\b(?:contract|freelance|contractor)(?=\s+(?:jobs?|roles?|work|gigs?|positions?)\b|\s*$)/i, function () { etype.value = 'Contract'; });
    }
    if (!age.value) {
      take(/\b(?:posted\s+)?(?:today|in the (?:last|past) 24 hours|(?:last|past) 24 hours)\b/i, function () { age.value = '1'; });
      take(/\b(?:posted\s+)?(?:in the )?(?:last|past) (?:3|three) days\b/i, function () { age.value = '3'; });
      take(/\b(?:posted\s+)?(?:this|in the (?:last|past)|(?:last|past)) week\b|\b(?:posted\s+)?(?:in the )?(?:last|past) 7 days\b/i, function () { age.value = '7'; });
      take(/\b(?:posted\s+)?(?:this|in the (?:last|past)|(?:last|past)) month\b|\b(?:posted\s+)?(?:in the )?(?:last|past) 30 days\b/i, function () { age.value = '30'; });
    }
    if (!perk.value) {
      take(/\b(?:with |offering )?(?:visa sponsorship|sponsor(?:s|ing)? (?:a |your )?(?:visa|h-?1b)s?|h-?1b sponsorship)\b/i, function () { perk.value = 'Visa sponsorship'; });
      take(/\b(?:with |offering )?relocation(?: support| assistance| package| help)?\b/i, function () { perk.value = 'Relocation support'; });
      take(/\b(?:with (?:a )?)?(?:4|four)[- ]day (?:work ?)?weeks?\b/i, function () { perk.value = '4-day week'; });
      take(/\b(?:with )?unlimited (?:pto|vacation|paid time off)\b/i, function () { perk.value = 'Unlimited PTO'; });
      take(/\b(?:no (?:college )?degree(?: required| needed)?|without (?:a )?(?:college )?degree)\b/i, function () { perk.value = 'No degree required'; });
      take(/\b(?:with )?(?:paid )?parental leave\b/i, function () { perk.value = 'Parental leave'; });
      take(/\b(?:with |offering )?tuition (?:reimbursement|assistance|support|benefits?)\b/i, function () { perk.value = 'Tuition assistance'; });
      take(/\b(?:with |offering )?student loan (?:repayment|assistance|help|support|benefits?)\b/i, function () { perk.value = 'Student loan help'; });
    }
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
    take(/\b(?:with|showing|that (?:show|list|state)s?)\s+(?:the\s+)?(?:salary|salaries|pay)(?:\s+(?:listed|stated|shown|included))?\b|\b(?:salary|pay)\s+(?:listed|stated|shown|included)\b/i, function () { if (!sal.value) sal.value = '1'; });
    if (!loc.value) {
      var hit = null;
      places.forEach(function (p) { p.names.forEach(function (nm) {
        var rx = new RegExp('(?:\\b(?:in|near|at)\\s+)?\\b' + rxEsc(nm) + '\\b', 'i'), mm = text.match(rx);
        if (mm && (!hit || mm[0].length > hit.len)) hit = { v: p.v, rx: rx, len: mm[0].length };
      }); });
      if (hit) { loc.value = hit.v; text = text.replace(hit.rx, ' '); took = true; }
    }
    if (!loc.value && !city.value.trim() && cityNames.length) {
      var cm = text.match(/\b(?:in|near|at)\s+([a-z][a-z .'-]{1,38}?)\s*$/i);
      if (cm && cityNames.indexOf(cm[1].trim().toLowerCase()) >= 0) { city.value = cm[1].trim(); text = text.replace(cm[0], ' '); took = true; }
    }
    if (took || /\b(?:jobs?|roles|positions?|vacanc(?:y|ies)|openings?)\b/i.test(text)) {
      text = text.replace(/\b(?:jobs?|roles|positions?|vacanc(?:y|ies)|openings?)\b/gi, ' ').replace(/\s+(?:in|at|near|for|with|and|paying|that pay)\s*$/i, ' ').replace(/^\s*(?:in|at|near|for|with|and)\s+/i, ' ');
      q.value = text.replace(/\s+/g, ' ').trim();
    }
    return took;
  };
  var form = $('qform'); if (form) form.addEventListener('submit', function (ev) { ev.preventDefault(); clearTimeout(timer); smart(); run(); });
  q.addEventListener('change', function () { if (smart()) { clearTimeout(timer); run(); } });
  saveBtn.addEventListener('click', function () {
    var all = H.get('hrn_searches', []), qs = query();
    if (!all.some(function (s) { return s.qs === qs; })) all.unshift({ qs: qs, label: describe(), seen: H.today() });
    H.set('hrn_searches', all.slice(0, 30));
    saveBtn.textContent = 'Saved to My jobs ✓'; saveBtn.disabled = true;
  });
  if (!sortTouched && q.value.trim()) sort.value = 'rel';
  // Near you: one click narrows the list to the visitor's country (taken from the time zone, or the place they picked on the home page)
  fetch(H.base + '/data/geo.json').then(function (r) { return r.json(); }).then(function (G) {
    var tz = ''; try { tz = Intl.DateTimeFormat().resolvedOptions().timeZone || ''; } catch (e) {}
    var cc0 = H.get('hrn_place', '') || G.tz[tz] || '', c = G.c[cc0];
    if (fRc && cc0 && G.c[cc0]) {        // "hide remote jobs closed to my country": the label names the country
      if (!rcCC) rcCC = cc0;
      $('f-rc-l').textContent = 'Remote open to ' + (G.c[rcCC] || G.c[cc0])[0]; $('f-rc-w').title = 'Hide remote jobs that are closed to this country';
      $('f-rc-w').hidden = false;
      fRc.addEventListener('change', run);
    }
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
  run();
})();
