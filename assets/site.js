/* Site-wide behaviour: theme, mobile menu, job tracker ("My jobs"), saved searches, skill profile ("For you").
   Everything is stored in the visitor's browser; there is no account and nothing is sent anywhere. */
(function () {
  var P = document.documentElement.getAttribute('data-base') || '';
  function get(k, d) { try { var v = JSON.parse(localStorage.getItem(k)); return v == null ? d : v; } catch (e) { return d; } }
  function set(k, v) { try { localStorage.setItem(k, JSON.stringify(v)); } catch (e) {} }
  function esc(s) { return String(s == null ? '' : s).replace(/[&<>"]/g, function (c) { return { '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;' }[c]; }); }
  function dateInt(d) { return d.getFullYear() * 10000 + (d.getMonth() + 1) * 100 + d.getDate(); }
  function today() { return dateInt(new Date()); }
  function since(days) { var d = new Date(); d.setDate(d.getDate() - days); return dateInt(d); }
  function hue(name) { var h = 0; for (var i = 0; i < name.length; i++) h = (h * 31 + name.charCodeAt(i)) % 360; return h; }
  var $ = function (id) { return document.getElementById(id); };
  var MONTHS = ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun', 'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec'];

  var hidden = get('hrn_hidden', {});   // jobs the visitor marked "Not interested"

  /* ---------- job index: compact file expanded into rows ---------- */
  // row: [0 slug, 1 title, 2 company, 3 location, 4 remote, 5 cat, 6 level, 7 tags, 8 salary, 9 postedText, 10 entry, 11 featured, 12 hue,
  //       13 salaryHigh, 14 places, 15 crypto, 16 postedInt, 17 search text (lazy), 18 perks, 19 type, 20 anywhere]
  var cache;
  function load() {
    if (!cache) cache = fetch(P + '/data/index.json').then(function (r) { return r.json(); }).then(function (d) {
      return d.r.map(function (r) {
        var c = d.c[r[2]], li = r[6], pi = r[9];
        return [r[0], r[1], c, r[3], r[4] & 1, d.k[r[5]], d.l[li], r[7].map(function (i) { return d.t[i]; }), r[8],
          pi ? MONTHS[Math.floor(pi / 100) % 100 - 1] + ' ' + (pi % 100) : '', li === 1 || li === 2 ? 1 : 0, r[4] & 2 ? 1 : 0, hue(c), r[10],
          r[11].map(function (i) { return d.p[i]; }), r[4] & 4 ? 1 : 0, pi, '',
          (r[12] || []).map(function (i) { return d.x[i]; }), d.e ? d.e[r[13] || 0] : '', r[4] & 8 ? 1 : 0];
      });
    });
    return cache;
  }
  function parse(qs) {
    var p = new URLSearchParams(qs || '');
    var sal = p.get('sal') ? Number(p.get('sal')) : (p.has('salary') ? 1 : 0), age = Number(p.get('age')) || 0;
    return {
      q: p.get('q') || '', words: (p.get('q') || '').toLowerCase().split(/\s+/).filter(Boolean),
      cat: p.get('cat') || '', lvl: p.get('lvl') || '', loc: p.get('loc') || '', sal: sal || 0, age: age, since: age ? since(age) : 0,
      remote: p.has('remote'), entry: p.has('entry'), crypto: p.has('crypto'), any: p.has('any'), perk: p.get('perk') || '', etype: p.get('etype') || '',
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
    if (f.any && !(j[20] && j[4])) return false;
    if (f.perk && j[18].indexOf(f.perk) < 0) return false;
    if (f.etype && j[19] !== f.etype) return false;
    if (hidden[j[0]]) return false;
    if (f.since && !(j[16] >= f.since)) return false;
    if (f.sal === 1 && !j[8]) return false;
    if (f.sal > 1 && !(j[13] >= f.sal)) return false;
    for (var i = 0; i < f.skills.length; i++) if (j[7].indexOf(f.skills[i]) < 0) return false;
    if (f.words.length) {
      var hay = j[17] || (j[17] = (j[1] + ' ' + j[2] + ' ' + j[3] + ' ' + j[7].join(' ')).toLowerCase());
      for (var k = 0; k < f.words.length; k++) if (hay.indexOf(f.words[k]) < 0) return false;
    }
    return true;
  }
  // collapse the same role posted once per city: returns rows, fills `extra` (slug -> number of extra postings)
  function collapse(rows, extra) {
    var first = new Map(), out = [];
    rows.forEach(function (j) {
      var k = j[2] + '|' + j[1];
      if (first.has(k)) extra.set(first.get(k), (extra.get(first.get(k)) || 0) + 1);
      else { first.set(k, j[0]); out.push(j); }
    });
    return out;
  }
  function card(j, more, badge) {
    var pills = (badge ? '<span class="pill acc">' + esc(badge) + '</span>' : '') + (j[11] ? '<span class="pill acc">Featured</span>' : '') + (j[4] ? '<span class="pill ok">Remote</span>' : '') +
      (j[8] ? '<span class="pill sal">' + esc(j[8].slice(0, 28)) + '</span>' : '') + (j[6] ? '<span class="pill">' + esc(j[6]) + '</span>' : '') +
      j[7].slice(0, 3).map(function (t) { return '<span class="pill">' + esc(t) + '</span>'; }).join('');
    var place = j[3].length > 60 ? j[3].slice(0, 57) + '…' : j[3];
    var letter = (j[2].match(/[A-Za-z0-9]/) || ['?'])[0].toUpperCase();
    return '<li class="job' + (j[11] ? ' feat' : '') + '"><a href="' + P + '/job/' + j[0] + '/"><span class="ava" style="--h:' + j[12] + '" aria-hidden="true">' + esc(letter) + '</span>' +
      '<span><span class="jt">' + esc(j[1]) + '</span><span class="js">' + esc(j[2]) + (place ? ' · ' + esc(place) : '') +
      (more ? ' · +' + more + ' more location' + (more > 1 ? 's' : '') : '') + '</span></span>' +
      '<span class="jr"><span class="pills">' + pills + '</span><time>' + esc(j[9]) + '</time></span></a></li>';
  }
  // mark cards of jobs the visitor already saved, applied to or opened (works for static and script-built lists)
  function decorate(scope) {
    var mine = get('hrn_jobs', {}), seen = {};
    get('hrn_seen', []).forEach(function (x) { seen[x.s] = 1; });
    (scope || document).querySelectorAll('.job > a').forEach(function (a) {
      if (a.getAttribute('data-d')) return;
      var m = (a.getAttribute('href') || '').match(/\/job\/([^/]+)\/?$/);
      if (!m) return;
      a.setAttribute('data-d', '1');
      var slug = decodeURIComponent(m[1]), rec = mine[slug], pills = a.querySelector('.pills');
      if (rec && pills) pills.insertAdjacentHTML('afterbegin', '<span class="pill acc">' + (rec.st === 'saved' ? 'Saved' : rec.st === 'closed' ? 'Closed out' : rec.st === 'offer' ? 'Offer' : rec.st === 'interview' ? 'Interviewing' : 'Applied') + '</span>');
      else if (seen[slug]) a.parentNode.classList.add('seen');
    });
  }
  window.HRN = { parse: parse, match: match, load: load, collapse: collapse, card: card, decorate: decorate, get: get, set: set, esc: esc, today: today, base: P };

  /* ---------- theme + mobile menu + shortcuts ---------- */
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

  /* ---------- companies page: quick filter ---------- */
  var cfilter = $('cfilter');
  if (cfilter) cfilter.addEventListener('input', function () {
    var q = cfilter.value.trim().toLowerCase(), shown = 0;
    document.querySelectorAll('#clist li').forEach(function (li) {
      var hit = !q || li.getAttribute('data-n').indexOf(q) >= 0;
      li.hidden = !hit; if (hit) shown++;
    });
    var none = $('cnone'); if (none) none.hidden = shown > 0;
  });

  /* ---------- job tracker ---------- */
  var STATUS = [['saved', 'Saved'], ['applied', 'Applied'], ['interview', 'Interviewing'], ['offer', 'Offer'], ['closed', 'Not moving forward']];
  var jobs = get('hrn_jobs', null);
  if (!jobs) {
    jobs = {};
    get('hrn_saved', []).forEach(function (x) { jobs[x.s] = { t: x.t, c: x.c, st: 'saved', at: Date.now(), note: '' }; });
    set('hrn_jobs', jobs);
  }
  var badge = $('saved-n');
  function paint() { if (badge) { var n = Object.keys(jobs).length; badge.textContent = n ? n : ''; } }
  function store() { set('hrn_jobs', jobs); paint(); }
  paint();
  var profile = get('hrn_profile', { skills: [], lvl: '', cat: '', sal: 0, remote: false });

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
  /* how this job fits the visitor's saved skills */
  var fit = $('match');
  if (fit && profile.skills.length) {
    var tags = (fit.getAttribute('data-tags') || '').split('|').filter(Boolean);
    var hit = tags.filter(function (t) { return profile.skills.indexOf(t) >= 0; });
    if (tags.length) {
      fit.textContent = hit.length ? 'You match ' + hit.length + ' of ' + tags.length + ' listed skills: ' + hit.join(', ') + '.' : 'None of your saved skills are listed for this role.';
      fit.hidden = false;
    }
  }

  var hideBtn = $('hide');
  if (hideBtn && saveBtn) {
    var slugH = saveBtn.getAttribute('data-slug');
    var paintHide = function () { hideBtn.textContent = hidden[slugH] ? 'Hidden from your searches · undo' : 'Not interested'; };
    paintHide();
    hideBtn.addEventListener('click', function () { if (hidden[slugH]) delete hidden[slugH]; else hidden[slugH] = 1; set('hrn_hidden', hidden); paintHide(); });
  }

  /* ---------- lists: saved / applied / viewed marks, faster navigation ---------- */
  decorate(document);
  var warmed = {};
  document.addEventListener('mouseover', function (ev) {
    var a = ev.target.closest && ev.target.closest('.job > a');
    if (!a || warmed[a.href] || !a.href || a.href.indexOf('/job/') < 0) return;
    warmed[a.href] = 1;
    var l = document.createElement('link'); l.rel = 'prefetch'; l.href = a.href; document.head.appendChild(l);
  });

  /* ---------- home: pick up where you left off ---------- */
  var recent = $('home-recent');
  if (recent) {
    var seenList = get('hrn_seen', []).slice(0, 3), lastSearch = get('hrn_searches', [])[0];
    if (seenList.length || lastSearch) {
      var html = seenList.map(function (j) {
        return '<li class="job"><a href="' + P + '/job/' + encodeURIComponent(j.s) + '/"><span class="ava" style="--h:' + hue(j.c) + '" aria-hidden="true">' +
          esc((String(j.c).match(/[A-Za-z0-9]/) || ['?'])[0].toUpperCase()) + '</span><span><span class="jt">' + esc(j.t) + '</span><span class="js">' + esc(j.c) + ' · viewed recently</span></span></a></li>';
      }).join('');
      if (lastSearch) html += '<li class="job"><a href="' + P + '/jobs/?' + esc(lastSearch.qs) + '"><span class="ava" aria-hidden="true">⌕</span><span><span class="jt">' + esc(lastSearch.label) + '</span><span class="js">Your saved search</span></span></a></li>';
      $('home-recent-list').innerHTML = html; recent.hidden = false;
    }
  }

  /* ---------- For you: skill profile and résumé scan ---------- */
  var fy = $('fy-root');
  if (fy) {
    var chips = Array.prototype.slice.call(fy.querySelectorAll('#fy-skills .chipbtn'));
    var lvl = $('fy-lvl'), cat = $('fy-cat'), sal = $('fy-sal'), rem = $('fy-remote'), list = $('fy-list'), count = $('fy-count'), more = $('fy-more');
    var shown = 40, found = [], extra = new Map(), scores = new Map();
    lvl.value = profile.lvl || ''; cat.value = profile.cat || ''; sal.value = profile.sal ? String(profile.sal) : ''; rem.checked = !!profile.remote;
    var paintChips = function () { chips.forEach(function (c) { c.setAttribute('aria-pressed', profile.skills.indexOf(c.getAttribute('data-skill')) >= 0 ? 'true' : 'false'); }); };
    var render = function () {
      list.innerHTML = found.slice(0, shown).map(function (j) {
        var k = scores.get(j[0]);
        return card(j, extra.get(j[0]) || 0, k ? k + (k === 1 ? ' skill match' : ' skill matches') : '');
      }).join('');
      more.hidden = found.length <= shown; decorate(list);
    };
    var run = function () {
      profile.lvl = lvl.value; profile.cat = cat.value; profile.sal = Number(sal.value) || 0; profile.remote = rem.checked;
      set('hrn_profile', profile); paintChips();
      if (!profile.skills.length) { list.innerHTML = ''; more.hidden = true; count.textContent = 'Pick at least one skill to see matching jobs.'; return; }
      count.textContent = 'Matching…';
      load().then(function (all) {
        var f = { cat: profile.cat, lvl: profile.lvl, loc: '', remote: profile.remote, entry: false, crypto: false, any: false, perk: '', etype: '', since: 0, sal: profile.sal, skills: [], words: [] };
        scores = new Map();
        var rows = all.filter(function (j) {
          if (!match(j, f)) return false;
          var k = 0; for (var i = 0; i < j[7].length; i++) if (profile.skills.indexOf(j[7][i]) >= 0) k++;
          if (!k) return false;
          scores.set(j[0], k); return true;
        });
        rows.sort(function (a, b) { return scores.get(b[0]) - scores.get(a[0]) || b[16] - a[16]; });
        extra = new Map(); found = collapse(rows, extra); shown = 40;
        count.textContent = rows.length.toLocaleString('en-US') + (rows.length === 1 ? ' job matches' : ' jobs match') + ' your skills, best matches first.';
        render();
      }).catch(function () { count.textContent = 'Could not load jobs. Please reload the page.'; });
    };
    fy.addEventListener('click', function (ev) {
      var c = ev.target.closest && ev.target.closest('#fy-skills .chipbtn');
      if (c) { var s = c.getAttribute('data-skill'), i = profile.skills.indexOf(s); if (i >= 0) profile.skills.splice(i, 1); else profile.skills.push(s); run(); return; }
      if (ev.target.id === 'fy-more') { shown += 40; render(); return; }
      if (ev.target.id === 'fy-clear') { profile = { skills: [], lvl: '', cat: '', sal: 0, remote: false }; lvl.value = cat.value = sal.value = ''; rem.checked = false; run(); return; }
      if (ev.target.id === 'fy-scan') {
        var text = $('fy-text').value, note = $('fy-scan-note');
        if (text.trim().length < 40) { note.textContent = 'Paste a bit more text first.'; return; }
        note.textContent = 'Reading…';
        fetch(P + '/data/skills.json').then(function (r) { return r.json(); }).then(function (pats) {
          var got = [];
          pats.forEach(function (p) { try { if (new RegExp(p[1], 'i').test(text)) got.push(p[0]); } catch (e) {} });
          var known = chips.map(function (c) { return c.getAttribute('data-skill'); });
          got = got.filter(function (s) { return known.indexOf(s) >= 0; });
          got.forEach(function (s) { if (profile.skills.indexOf(s) < 0) profile.skills.push(s); });
          note.textContent = got.length ? 'Found ' + got.length + ' skills: ' + got.join(', ') + '.' : 'No known skills found. Pick them by hand above.';
          run();
        }).catch(function () { note.textContent = 'Could not read the skills list. Pick skills by hand above.'; });
      }
    });
    [lvl, cat, sal, rem].forEach(function (el) { el.addEventListener('change', run); });
    run();
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
      var shownKeys = keys.filter(function (k) { return tab === 'all' || jobs[k].st === tab; });
      $('mj-list').innerHTML = shownKeys.map(function (k) {
        var r = jobs[k];
        return '<li class="trow" data-s="' + esc(k) + '"><span class="ava" style="--h:' + hue(r.c) + '" aria-hidden="true">' + esc(letter(r.c)) + '</span>' +
          '<div class="main"><a class="tt" href="' + P + '/job/' + encodeURIComponent(k) + '/">' + esc(r.t) + '</a><span class="js">' + esc(r.c) + ' · added ' + esc(when(r.at)) + '</span>' +
          '<input class="nt" type="text" placeholder="Add a note: contact, next step, salary discussed…" value="' + esc(r.note || '') + '" aria-label="Note"></div>' +
          '<div class="ctl"><select aria-label="Status">' + STATUS.map(function (s) { return '<option value="' + s[0] + '"' + (r.st === s[0] ? ' selected' : '') + '>' + s[1] + '</option>'; }).join('') +
          '</select><button class="unsave" type="button">Remove</button></div></li>';
      }).join('');
      $('mj-empty').hidden = shownKeys.length > 0;
      var seen = get('hrn_seen', []);
      $('seen-list').innerHTML = seen.map(function (j) {
        return '<li class="job"><a href="' + P + '/job/' + encodeURIComponent(j.s) + '/"><span class="ava" style="--h:' + hue(j.c) + '" aria-hidden="true">' + esc(letter(j.c)) + '</span><span><span class="jt">' + esc(j.t) + '</span><span class="js">' + esc(j.c) + '</span></span></a></li>';
      }).join('');
      $('seen-empty').hidden = seen.length > 0;
    };
    root.addEventListener('click', function (ev) {
      var t = ev.target;
      if (t.closest && t.closest('.tab')) { tab = t.closest('.tab').getAttribute('data-tab'); draw(); return; }
      if (t.classList.contains('unsave') && t.closest('.trow') && t.closest('#mj-list')) { delete jobs[t.closest('.trow').getAttribute('data-s')]; store(); draw(); return; }
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
    var hiddenNote = $('mj-hidden'), hiddenCount = Object.keys(hidden).length;
    if (hiddenNote && hiddenCount) {
      hiddenNote.innerHTML = hiddenCount + (hiddenCount === 1 ? ' job is' : ' jobs are') + ' hidden from your searches. <button class="linkbtn" id="mj-unhide" type="button">Show them again</button>';
      hiddenNote.hidden = false;
      $('mj-unhide').addEventListener('click', function () { hidden = {}; set('hrn_hidden', hidden); hiddenNote.hidden = true; });
    }

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
    if (searches.length) load().then(drawSearches).catch(function () {});
  }
})();
