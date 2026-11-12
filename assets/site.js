/* Site-wide behaviour: theme, mobile menu, job tracker ("My jobs"), saved searches.
   Everything is stored in the visitor's browser; there is no account and nothing is sent anywhere. */
(function () {
  var P = document.documentElement.getAttribute('data-base') || '';
  function get(k, d) { try { var v = JSON.parse(localStorage.getItem(k)); return v == null ? d : v; } catch (e) { return d; } }
  function set(k, v) { try { localStorage.setItem(k, JSON.stringify(v)); } catch (e) {} }
  function esc(s) { return String(s == null ? '' : s).replace(/[&<>"]/g, function (c) { return { '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;' }[c]; }); }
  function today() { var d = new Date(); return d.getFullYear() * 10000 + (d.getMonth() + 1) * 100 + d.getDate(); }
  var $ = function (id) { return document.getElementById(id); };

  /* ---------- search matching, shared with the search page ---------- */
  // index row: [slug, title, company, location, remote, cat, level, tags, salary, postedText, entry, featured, hue, salaryHigh, places, crypto, postedInt]
  function parse(qs) {
    var p = new URLSearchParams(qs || '');
    var sal = p.get('sal') ? Number(p.get('sal')) : (p.has('salary') ? 1 : 0);
    return {
      q: p.get('q') || '', words: (p.get('q') || '').toLowerCase().split(/\s+/).filter(Boolean),
      cat: p.get('cat') || '', lvl: p.get('lvl') || '', loc: p.get('loc') || '', sal: sal || 0,
      remote: p.has('remote'), entry: p.has('entry'), crypto: p.has('crypto'),
      skills: (p.get('skills') || '').split(',').filter(Boolean), sort: p.get('sort') || 'new'
    };
  }
  function match(j, f) {
    if (f.cat && j[5] !== f.cat) return false;
    if (f.lvl && j[6] !== f.lvl) return false;
    if (f.loc && j[14].indexOf(f.loc) < 0) return false;
    if (f.remote && !j[4]) return false;
    if (f.entry && !j[10]) return false;
    if (f.crypto && !j[15]) return false;
    if (f.sal === 1 && !j[8]) return false;
    if (f.sal > 1 && !(j[13] >= f.sal)) return false;
    for (var i = 0; i < f.skills.length; i++) if (j[7].indexOf(f.skills[i]) < 0) return false;
    if (f.words.length) {
      var hay = j[17] || (j[17] = (j[1] + ' ' + j[2] + ' ' + j[3] + ' ' + j[7].join(' ')).toLowerCase());
      for (var k = 0; k < f.words.length; k++) if (hay.indexOf(f.words[k]) < 0) return false;
    }
    return true;
  }
  window.HRN = { parse: parse, match: match, get: get, set: set, esc: esc, today: today, base: P };

  /* ---------- theme + mobile menu ---------- */
  var themeBtn = $('theme');
  if (themeBtn) themeBtn.addEventListener('click', function () {
    var root = document.documentElement, cur = root.getAttribute('data-theme');
    var dark = cur ? cur === 'dark' : window.matchMedia('(prefers-color-scheme: dark)').matches;
    var next = dark ? 'light' : 'dark';
    root.setAttribute('data-theme', next);
    try { localStorage.setItem('hrn_theme', next); } catch (e) {}
  });
  var menuBtn = $('menu'), header = document.querySelector('header.site');
  if (menuBtn && header) menuBtn.addEventListener('click', function () {
    var open = header.classList.toggle('open');
    menuBtn.setAttribute('aria-expanded', open ? 'true' : 'false');
  });
  document.addEventListener('keydown', function (ev) {
    if (ev.key === '/' && !/input|textarea|select/i.test((ev.target && ev.target.tagName) || '')) {
      var box = $('q') || document.querySelector('.searchbar input');
      if (box) { ev.preventDefault(); box.focus(); }
    }
  });

  /* ---------- job tracker ---------- */
  var STATUS = [['saved', 'Saved'], ['applied', 'Applied'], ['interview', 'Interviewing'], ['offer', 'Offer'], ['closed', 'Not moving forward']];
  var jobs = get('hrn_jobs', null);
  if (!jobs) {                                   // migrate the first version of the saved list
    jobs = {};
    get('hrn_saved', []).forEach(function (x) { jobs[x.s] = { t: x.t, c: x.c, st: 'saved', at: Date.now(), note: '' }; });
    set('hrn_jobs', jobs);
  }
  var badge = $('saved-n');
  function paint() { if (badge) { var n = Object.keys(jobs).length; badge.textContent = n ? n : ''; } }
  function store() { set('hrn_jobs', jobs); paint(); }
  paint();

  var saveBtn = $('save'), appliedBtn = $('applied');
  if (saveBtn) {
    var me = { s: saveBtn.getAttribute('data-slug'), t: saveBtn.getAttribute('data-title'), c: saveBtn.getAttribute('data-company') };
    var label = function () {
      var rec = jobs[me.s];
      saveBtn.textContent = rec ? 'Saved ✓' : 'Save job';
      saveBtn.setAttribute('aria-pressed', rec ? 'true' : 'false');
      if (appliedBtn) {
        var done = rec && rec.st !== 'saved';
        appliedBtn.textContent = done ? 'Applied ✓' : 'Mark as applied';
        appliedBtn.setAttribute('aria-pressed', done ? 'true' : 'false');
      }
    };
    label();
    saveBtn.addEventListener('click', function () {
      if (jobs[me.s]) delete jobs[me.s]; else jobs[me.s] = { t: me.t, c: me.c, st: 'saved', at: Date.now(), note: '' };
      store(); label();
    });
    if (appliedBtn) appliedBtn.addEventListener('click', function () {
      var rec = jobs[me.s];
      if (rec && rec.st !== 'saved') rec.st = 'saved';
      else jobs[me.s] = { t: me.t, c: me.c, st: 'applied', at: Date.now(), note: rec ? rec.note : '' };
      store(); label();
    });
    var applyLink = $('apply'), hint = $('apply-hint');
    if (applyLink && hint) applyLink.addEventListener('click', function () { hint.hidden = false; });
    var copy = $('copy');
    if (copy) copy.addEventListener('click', function () {
      var done = function () { copy.textContent = 'Link copied'; setTimeout(function () { copy.textContent = 'Copy link'; }, 1600); };
      if (navigator.clipboard) navigator.clipboard.writeText(location.href).then(done, function () {}); else done();
    });
    var seen = get('hrn_seen', []).filter(function (x) { return x.s !== me.s; });
    seen.unshift(me); set('hrn_seen', seen.slice(0, 30));
  }

  /* ---------- My jobs page ---------- */
  var root = $('mj-root');
  if (root) {
    var tab = 'all';
    var letter = function (c) { return (String(c).match(/[A-Za-z0-9]/) || ['?'])[0].toUpperCase(); };
    var when = function (ts) { try { return new Date(ts).toLocaleDateString('en-US', { month: 'short', day: 'numeric' }); } catch (e) { return ''; } };
    var draw = function () {
      var keys = Object.keys(jobs).sort(function (a, b) { return jobs[b].at - jobs[a].at; });
      var counts = { all: keys.length };
      STATUS.forEach(function (s) { counts[s[0]] = 0; });
      keys.forEach(function (k) { counts[jobs[k].st] = (counts[jobs[k].st] || 0) + 1; });
      $('mj-tabs').innerHTML = [['all', 'All']].concat(STATUS).map(function (s) {
        return '<button class="tab" type="button" data-tab="' + s[0] + '" aria-selected="' + (tab === s[0]) + '">' + s[1] + '<i>' + (counts[s[0]] || 0) + '</i></button>';
      }).join('');
      var shown = keys.filter(function (k) { return tab === 'all' || jobs[k].st === tab; });
      $('mj-list').innerHTML = shown.map(function (k) {
        var r = jobs[k];
        return '<li class="trow" data-s="' + esc(k) + '"><span class="ava" aria-hidden="true">' + esc(letter(r.c)) + '</span>' +
          '<div class="main"><a class="tt" href="' + P + '/job/' + encodeURIComponent(k) + '/">' + esc(r.t) + '</a><span class="js">' + esc(r.c) + ' · added ' + esc(when(r.at)) + '</span>' +
          '<input class="nt" type="text" placeholder="Add a note: contact, next step, salary discussed…" value="' + esc(r.note || '') + '" aria-label="Note"></div>' +
          '<div class="ctl"><select aria-label="Status">' + STATUS.map(function (s) { return '<option value="' + s[0] + '"' + (r.st === s[0] ? ' selected' : '') + '>' + s[1] + '</option>'; }).join('') +
          '</select><button class="unsave" type="button">Remove</button></div></li>';
      }).join('');
      $('mj-empty').hidden = shown.length > 0;
      var seen = get('hrn_seen', []);
      $('seen-list').innerHTML = seen.map(function (j) {
        return '<li class="job"><a href="' + P + '/job/' + encodeURIComponent(j.s) + '/"><span class="ava" aria-hidden="true">' + esc(letter(j.c)) + '</span><span><span class="jt">' + esc(j.t) + '</span><span class="js">' + esc(j.c) + '</span></span></a></li>';
      }).join('');
      $('seen-empty').hidden = seen.length > 0;
    };
    root.addEventListener('click', function (ev) {
      var t = ev.target;
      if (t.closest && t.closest('.tab')) { tab = t.closest('.tab').getAttribute('data-tab'); draw(); return; }
      if (t.classList.contains('unsave') && t.closest('.trow')) { delete jobs[t.closest('.trow').getAttribute('data-s')]; store(); draw(); return; }
      if (t.id === 'mj-export') {
        var rows = [['Title', 'Company', 'Status', 'Added', 'Note', 'Link']].concat(Object.keys(jobs).map(function (k) {
          var r = jobs[k]; return [r.t, r.c, r.st, new Date(r.at).toISOString().slice(0, 10), r.note || '', location.origin + P + '/job/' + k + '/'];
        }));
        var csv = rows.map(function (r) { return r.map(function (c) { return '"' + String(c).replace(/"/g, '""') + '"'; }).join(','); }).join('\n');
        var a = document.createElement('a');
        a.href = URL.createObjectURL(new Blob([csv], { type: 'text/csv' })); a.download = 'my-jobs.csv';
        document.body.appendChild(a); a.click(); a.remove();
      }
    });
    root.addEventListener('change', function (ev) {
      var row = ev.target.closest && ev.target.closest('.trow'); if (!row) return;
      var rec = jobs[row.getAttribute('data-s')]; if (!rec) return;
      if (ev.target.tagName === 'SELECT') { rec.st = ev.target.value; store(); draw(); }
      else if (ev.target.classList.contains('nt')) { rec.note = ev.target.value; store(); }
    });
    draw();

    /* saved searches with "new since last visit" counts */
    var searches = get('hrn_searches', []);
    var drawSearches = function (index) {
      $('ss-empty').hidden = searches.length > 0;
      $('ss-list').innerHTML = searches.map(function (s, i) {
        var fresh = '';
        if (index) {
          var f = parse(s.qs), n = 0;
          for (var k = 0; k < index.length; k++) if (index[k][16] > s.seen && match(index[k], f)) n++;
          fresh = n ? '<span class="pill ok">' + n + ' new</span>' : '<span class="pill">No new jobs</span>';
        }
        return '<li class="trow" data-i="' + i + '"><span class="ava" aria-hidden="true">⌕</span><div class="main"><a class="tt ss-open" href="' + P + '/jobs/?' + esc(s.qs) + '">' + esc(s.label) + '</a>' +
          '<span class="js">Saved search</span></div><div class="ctl">' + fresh + '<button class="unsave ss-del" type="button">Remove</button></div></li>';
      }).join('');
    };
    drawSearches(null);
    $('ss-list').addEventListener('click', function (ev) {
      var row = ev.target.closest('.trow'); if (!row) return;
      var i = Number(row.getAttribute('data-i'));
      if (ev.target.classList.contains('ss-del')) { searches.splice(i, 1); set('hrn_searches', searches); drawSearches(null); }
      else if (ev.target.classList.contains('ss-open')) { searches[i].seen = today(); set('hrn_searches', searches); }
    });
    if (searches.length) fetch(P + '/data/index.json').then(function (r) { return r.json(); }).then(drawSearches).catch(function () {});
  }
})();
