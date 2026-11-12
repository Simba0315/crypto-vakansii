/* Job search page: filters, sorting, shareable URLs and saved searches. Uses HRN.match from site.js. */
(async function () {
  var root = document.getElementById('search');
  if (!root || !window.HRN) return;
  var H = window.HRN, P = H.base, esc = H.esc;
  var $ = function (id) { return document.getElementById(id); };
  var q = $('q'), cat = $('cat'), lvl = $('lvl'), loc = $('loc'), sal = $('sal'), sort = $('sort');
  var fRemote = $('f-remote'), fEntry = $('f-entry'), fCrypto = $('f-crypto');
  var list = $('results'), count = $('count'), more = $('more'), skillbar = $('skills'), saveBtn = $('save-search');

  // restore the state from the URL
  var f0 = H.parse(location.search.slice(1));
  q.value = f0.q; cat.value = f0.cat; lvl.value = f0.lvl; loc.value = f0.loc; sal.value = f0.sal ? String(f0.sal) : ''; sort.value = f0.sort;
  fRemote.checked = f0.remote; fEntry.checked = f0.entry; fCrypto.checked = f0.crypto;
  var skills = f0.skills.slice();
  var chips = Array.prototype.slice.call(skillbar.querySelectorAll('.chipbtn'));
  var paintChips = function () { chips.forEach(function (c) { c.setAttribute('aria-pressed', skills.indexOf(c.getAttribute('data-skill')) >= 0 ? 'true' : 'false'); }); };
  paintChips();

  var jobs = [];
  try { jobs = await (await fetch(P + '/data/index.json')).json(); }
  catch (e) { count.textContent = 'Could not load the list. Please reload the page.'; return; }

  var shown = 50, found = [];
  var card = function (j) {
    var pills = (j[11] ? '<span class="pill acc">Featured</span>' : '') + (j[4] ? '<span class="pill ok">Remote</span>' : '') +
      (j[8] ? '<span class="pill sal">' + esc(j[8].slice(0, 28)) + '</span>' : '') + (j[6] ? '<span class="pill">' + esc(j[6]) + '</span>' : '') +
      j[7].slice(0, 3).map(function (t) { return '<span class="pill">' + esc(t) + '</span>'; }).join('');
    var place = j[3].length > 60 ? j[3].slice(0, 57) + '…' : j[3];
    var letter = (j[2].match(/[A-Za-z0-9]/) || ['?'])[0].toUpperCase();
    return '<li class="job' + (j[11] ? ' feat' : '') + '"><a href="' + P + '/job/' + j[0] + '/"><span class="ava" style="--h:' + j[12] + '" aria-hidden="true">' + esc(letter) + '</span>' +
      '<span><span class="jt">' + esc(j[1]) + '</span><span class="js">' + esc(j[2]) + (place ? ' · ' + esc(place) : '') + '</span></span>' +
      '<span class="jr"><span class="pills">' + pills + '</span><time>' + esc(j[9]) + '</time></span></a></li>';
  };
  var query = function () {
    var p = new URLSearchParams();
    if (q.value.trim()) p.set('q', q.value.trim());
    if (cat.value) p.set('cat', cat.value);
    if (lvl.value) p.set('lvl', lvl.value);
    if (loc.value) p.set('loc', loc.value);
    if (sal.value) p.set('sal', sal.value);
    if (fRemote.checked) p.set('remote', '1');
    if (fEntry.checked) p.set('entry', '1');
    if (fCrypto.checked) p.set('crypto', '1');
    if (skills.length) p.set('skills', skills.join(','));
    if (sort.value !== 'new') p.set('sort', sort.value);
    return p.toString();
  };
  var text = function (el) { return el.options[el.selectedIndex].text; };
  var describe = function () {
    var parts = [];
    if (q.value.trim()) parts.push('“' + q.value.trim() + '”');
    if (cat.value) parts.push(text(cat));
    if (lvl.value) parts.push(text(lvl));
    if (loc.value) parts.push(text(loc));
    if (fRemote.checked) parts.push('Remote');
    if (fEntry.checked) parts.push('Entry-level');
    if (fCrypto.checked) parts.push('Crypto');
    if (sal.value) parts.push(text(sal));
    if (skills.length) parts.push(skills.join(' + '));
    return parts.join(' · ') || 'All jobs';
  };
  var render = function () {
    list.innerHTML = found.slice(0, shown).map(card).join('');
    count.textContent = found.length ? found.length.toLocaleString('en-US') + (found.length === 1 ? ' job' : ' jobs') : 'No jobs match. Try removing a filter.';
    more.hidden = found.length <= shown;
  };
  var run = function () {
    var qs = query(), f = H.parse(qs);
    found = jobs.filter(function (j) { return H.match(j, f); });
    if (f.sort === 'sal') found = found.slice().sort(function (a, b) { return (b[13] || 0) - (a[13] || 0); });
    shown = 50; render();
    history.replaceState(null, '', location.pathname + (qs ? '?' + qs : ''));
    saveBtn.textContent = 'Save this search'; saveBtn.disabled = false;
  };
  var timer;
  q.addEventListener('input', function () { clearTimeout(timer); timer = setTimeout(run, 140); });
  [cat, lvl, loc, sal, sort, fRemote, fEntry, fCrypto].forEach(function (el) { el.addEventListener('change', run); });
  skillbar.addEventListener('click', function (ev) {
    var c = ev.target.closest('.chipbtn'); if (!c) return;
    var s = c.getAttribute('data-skill'), i = skills.indexOf(s);
    if (i >= 0) skills.splice(i, 1); else skills.push(s);
    paintChips(); run();
  });
  more.addEventListener('click', function () { shown += 50; render(); });
  var form = $('qform'); if (form) form.addEventListener('submit', function (ev) { ev.preventDefault(); run(); });
  saveBtn.addEventListener('click', function () {
    var all = H.get('hrn_searches', []), qs = query();
    if (!all.some(function (s) { return s.qs === qs; })) all.unshift({ qs: qs, label: describe(), seen: H.today() });
    H.set('hrn_searches', all.slice(0, 30));
    saveBtn.textContent = 'Saved to My jobs ✓'; saveBtn.disabled = true;
  });
  run();
})();
