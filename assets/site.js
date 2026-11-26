/* Site-wide behaviour: theme, mobile menu, job tracker ("My jobs"), saved searches, skill profile ("For you").
   Everything is stored in the visitor's browser; there is no account and nothing is sent anywhere. */
(function () {
  var P = document.documentElement.getAttribute('data-base') || '';
  function get(k, d) { try { var v = JSON.parse(localStorage.getItem(k)); return v == null ? d : v; } catch (e) { return d; } }
  function set(k, v) {
    try { localStorage.setItem(k, JSON.stringify(v)); } catch (e) {}
    // saved jobs and a resume are the visitor's work: ask the browser not to clear them when it tidies up
    if ((k === 'hrn_jobs' || k === 'hrn_resume') && !set.asked && navigator.storage && navigator.storage.persist) { set.asked = true; try { navigator.storage.persist(); } catch (e) {} }
  }
  function esc(s) { return String(s == null ? '' : s).replace(/[&<>"]/g, function (c) { return { '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;' }[c]; }); }
  function dateInt(d) { return d.getFullYear() * 10000 + (d.getMonth() + 1) * 100 + d.getDate(); }
  function today() { return dateInt(new Date()); }
  function since(days) { var d = new Date(); d.setDate(d.getDate() - days); return dateInt(d); }
  function slugOf(s) { return String(s).toLowerCase().replace(/[^a-z0-9]+/g, '-').replace(/^-+|-+$/g, '').slice(0, 60).replace(/-+$/, ''); }
  // avatar markup: the company logo. Without a logo the square is not shown at all (the owner asked for no letter squares);
  // the letter stays in the markup only as a fallback for styles that are switched off
  function avatar(company, logo, guess) {
    var letter = (String(company).match(/[A-Za-z0-9]/) || ['?'])[0].toUpperCase();
    // the small copy of the logo (build.small_logos: 72 px, 1 to 2 KB) for these 28 to 42 px squares
    var img = logo ? '<img src="' + P + '/logos/s/' + logo + '.png" alt="' + esc(company) + ' logo" title="' + esc(company) + ' logo" width="72" height="72" loading="lazy">' : guess ? '<img src="' + P + '/logos/s/' + slugOf(company) + '.png" alt="' + esc(company) + ' logo" title="' + esc(company) + ' logo" width="72" height="72" loading="lazy" onerror="this.remove()">' : '';
    return '<span class="ava' + (logo || guess ? ' has' : '') + '" style="--h:' + hue(company) + '" aria-hidden="true">' + esc(letter) + img + '</span>';
  }
  function hue(name) { var h = 0; for (var i = 0; i < name.length; i++) h = (h * 31 + name.charCodeAt(i)) % 360; return h; }
  var $ = function (id) { return document.getElementById(id); };
  // a logo that fails to load must never leave an empty square: fall back to the company's initial
  function dropLogo(img) { var box = img.parentNode; if (box && box.classList && box.classList.contains('ava')) { box.classList.remove('has'); img.remove(); } }
  document.addEventListener('error', function (ev) { if (ev.target && ev.target.tagName === 'IMG') dropLogo(ev.target); }, true);
  Array.prototype.forEach.call(document.querySelectorAll('.ava img'), function (img) { if (img.complete && !img.naturalWidth) dropLogo(img); });
  var MONTHS = ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun', 'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec'];

  var hidden = get('hrn_hidden', {});   // jobs the visitor marked "Not interested"
  var mute = get('hrn_mute', {});       // what the visitor never wants in lists: { c: {company: 1}, w: [words in the title] }
  if (!mute.c) mute.c = {}; if (!mute.w) mute.w = [];

  /* ---------- job index: compact file expanded into rows ---------- */
  // row: [0 slug, 1 title, 2 company, 3 location, 4 remote, 5 cat, 6 level, 7 tags, 8 salary, 9 postedText, 10 entry, 11 featured, 12 hue,
  //       13 salaryHigh, 14 places, 15 crypto, 16 postedInt, 17 search text (lazy), 18 perks, 19 type, 20 anywhere, 21 logo, 22 talent pool,
  //       23 exact posting time in minutes since 1970 (0 when only the day is known or the job is over a week old),
  //       24 country codes of the places the job is in, for the flags, 25 hybrid, 26 "Urgently hiring" badge bought for the job]
  var cache, headCache;
  function expand(d) {
    var cslug = d.c.map(function (c) { return slugOf(c) || 'job'; });
    return d.r.map(function (r) {
        var c = d.c[r[2]], li = r[6], pi = r[9], s = r[0];
        if (typeof s !== 'string') { var b = (slugOf(r[1]) || 'job') + '-' + cslug[r[2]]; s = s ? b + '-' + s : b; }   // slug rebuilt from title and company
        return [s, r[1], c, r[3], r[4] & 1, d.k[r[5]], d.l[li], r[7].map(function (i) { return d.t[i]; }), r[8],
          pi ? MONTHS[Math.floor(pi / 100) % 100 - 1] + ' ' + (pi % 100) : '', li === 1 || li === 2 ? 1 : 0, r[4] & 2 ? 1 : 0, hue(c), r[10],
          r[11].map(function (i) { return d.p[i]; }), r[4] & 4 ? 1 : 0, pi, '',
          (r[12] || []).map(function (i) { return d.x[i]; }), d.e ? d.e[r[13] || 0] : '', r[4] & 8 ? 1 : 0, d.g && d.g[r[2]] ? slugOf(c) : '', r[4] & 16 ? 1 : 0, r[14] || 0,
          d.f ? r[11].map(function (i) { return d.f[i]; }).filter(function (c, i, a) { return c && a.indexOf(c) === i; }).slice(0, 3) : [], r[4] & 32 ? 1 : 0, r[4] & 64 ? 1 : 0];
    });
  }
  function load() {
    if (!cache) cache = fetch(P + '/data/index.json').then(function (r) { return r.json(); }).then(expand);
    return cache;
  }
  // the newest rows only (a small file), so a list can be painted before the full index arrives
  function loadHead() {
    if (!headCache) headCache = fetch(P + '/data/head.json').then(function (r) { return r.json(); }).then(function (d) { return { rows: expand(d), total: d.n }; });
    return headCache;
  }
  // A row as the server sends it (search_engine.row: /api/search?list=1, and the first page inside /jobs/) -> the row above:
  // [slug, title, company, place, flags, field, level, skills, pay, posted yyyymmdd, top of the pay in USD, places, perks, type,
  //  exact time in minutes, country codes, has a logo, other postings of the same role]
  function fromApi(a) {
    var f = a[4], pi = a[9];
    return [a[0], a[1], a[2], a[3], f & 1, a[5], a[6], a[7], a[8], pi ? MONTHS[Math.floor(pi / 100) % 100 - 1] + ' ' + (pi % 100) : '', a[6] === 'Intern' || a[6] === 'Junior' ? 1 : 0,
      f & 2 ? 1 : 0, hue(a[2]), a[10], a[11], f & 4 ? 1 : 0, pi, '', a[12], a[13], f & 8 ? 1 : 0, a[16] ? slugOf(a[2]) : '', f & 16 ? 1 : 0, a[14], a[15], f & 32 ? 1 : 0, f & 64 ? 1 : 0];
  }
  // The open jobs among these slugs, as rows, from the server (60 to a request): for a page that needs a few jobs, not every job.
  // A slug that is missing from the answer is a job that is closed (or never was).
  function rowsOf(slugs) {
    var parts = [];
    slugs = slugs.filter(function (s) { return /^[a-z0-9][a-z0-9-]*$/.test(s); });
    for (var i = 0; i < slugs.length; i += 60) parts.push(slugs.slice(i, i + 60).sort());
    return Promise.all(parts.map(function (part) {
      return fetch(P + '/api/search?list=1&ids=' + encodeURIComponent(part.join(','))).then(function (r) { if (!r.ok) throw new Error('search answered ' + r.status); return r.json(); })
        .then(function (d) { return d.jobs.map(fromApi); });
    })).then(function (all) { return [].concat.apply([], all); });
  }
  // One page of a list from the server (/api/search?list=1, search_engine.py), as rows: {total, rows, more, sum}. qs is written like the
  // search page's own address, plus np (no talent pools), onsite, sk (any of these skills), co (one company), after (yyyymmdd), count, sum.
  function listOf(qs) {
    return fetch(P + '/api/search?list=1' + (qs ? '&' + qs : '')).then(function (r) { if (!r.ok) throw new Error('search answered ' + r.status); return r.json(); })
      .then(function (d) { return { total: d.total, rows: (d.jobs || []).map(fromApi), more: !!d.more, sum: d.sum || null }; });
  }
  // the For you answers (hrn_profile) as a list's address: the jobs fitTest() keeps (null without answers)
  function fitQuery(p) {
    p = p || {};
    var cats = p.cats || [], skills = p.skills || [], pay = Number(p.pay) || 0, out = ['np=1'];
    if (!cats.length && !skills.length && !p.where && !pay) return null;
    if (cats.length) out.push('cat=' + encodeURIComponent(cats.slice().sort().join(',')));
    if (p.where === 'remote') out.push('remote=1'); else if (p.where === 'hybrid') out.push('hybrid=1'); else if (p.where === 'office') out.push('onsite=1');
    if (pay >= 1000) out.push('sal=' + pay, 'nosal=1');                  // a job that does not say its pay stays in, as in fitTest()
    if (skills.length) out.push('sk=' + encodeURIComponent(skills.slice().sort().join(',')));
    return out.join('&');
  }
  // The list of every open job (data/index.json: 22 MB to download, about 450 MB of memory once read) is fetched only where nothing
  // smaller can answer, and on a phone, a small device or a metered connection only when the visitor asks for it.
  function heavyOk() {
    var c = navigator.connection || {};
    if (c.saveData || /(^|-)2g$/.test(c.effectiveType || '') || (navigator.deviceMemory && navigator.deviceMemory < 4)) return false;
    return !(/Mobi|Android|iPhone|iPad|iPod/i.test(navigator.userAgent) || (window.matchMedia && window.matchMedia('(max-width: 760px)').matches));
  }
  function doneSet() {             // the jobs the visitor applied to (any status after "saved"), only when "leave out jobs I applied to" is on
    if (!get('hrn_hide_applied', false)) return null;
    var mine = get('hrn_jobs', {}), o = {};
    Object.keys(mine).forEach(function (k) { if (mine[k] && mine[k].st && mine[k].st !== 'saved') o[k] = 1; });
    return o;
  }
  function parse(qs) {
    var p = new URLSearchParams(qs || '');
    var sal = p.get('sal') ? Number(p.get('sal')) : (p.has('salary') ? 1 : 0), age = Number(p.get('age')) || 0;
    return {
      q: p.get('q') || '', words: (p.get('q') || '').toLowerCase().split(/\s+/).filter(Boolean),
      cat: p.get('cat') || '', lvl: p.get('lvl') || '', loc: p.get('loc') || '', sal: sal || 0, age: age, since: age ? since(age) : 0,
      rc: (p.get('rc') || '').toUpperCase(), city: (p.get('city') || '').trim(), cityRx: (p.get('city') || '').trim() ? new RegExp('(^|[^a-z])' + (p.get('city') || '').trim().toLowerCase().replace(/[.*+?^${}()|[\]\\]/g, '\\$&'), 'i') : null,
      remote: p.has('remote'), hybrid: p.has('hybrid'), xl: (p.get('xl') || '').split(',').filter(Boolean), entry: p.has('entry'), crypto: p.has('crypto'), any: p.has('any'), perk: p.get('perk') || '', etype: p.get('etype') || '',
      skills: (p.get('skills') || '').split(',').filter(Boolean), sort: p.get('sort') || 'new',
      titles: p.has('ti'), nosal: p.has('nosal'), real: p.has('real'), realSince: since(90),         // "fresh openings only": no talent pools, nothing open 90+ days
      done: doneSet()                                                                               // jobs already applied to, when the visitor hides them
    };
  }
  // words people type for the same thing: a query word also matches its other spellings ("js" finds JavaScript jobs)
  var SYN = { js: ['javascript', 'js'], javascript: ['javascript', 'js'], ts: ['typescript'], golang: ['go ', 'golang'], k8s: ['kubernetes', 'k8s'], kubernetes: ['kubernetes', 'k8s'],
    postgres: ['postgres'], postgresql: ['postgres'], py: ['python'], ml: ['machine learning', ' ml', 'ml '], ai: [' ai', 'ai ', 'artificial intelligence', 'llm'],
    frontend: ['frontend', 'front end', 'front-end'], 'front-end': ['frontend', 'front end', 'front-end'], backend: ['backend', 'back end', 'back-end'], 'back-end': ['backend', 'back end', 'back-end'],
    fullstack: ['fullstack', 'full stack', 'full-stack'], 'full-stack': ['fullstack', 'full stack', 'full-stack'], devops: ['devops', 'dev ops', 'site reliability', 'platform engineer'],
    sre: ['site reliability', 'sre'], swe: ['software engineer', 'swe'], pm: ['product manager', 'project manager', ' pm'], ux: ['ux', 'user experience'], ui: ['ui ', ' ui', 'user interface'],
    qa: ['qa', 'quality assurance', 'test engineer'], hr: ['hr ', ' hr', 'human resources', 'people partner'], cs: ['customer success', 'customer support'],
    dev: ['developer', 'engineer', 'dev'], developer: ['developer', 'engineer'], programmer: ['developer', 'engineer', 'programmer'], coder: ['developer', 'engineer'],
    ios: ['ios', 'swift'], android: ['android', 'kotlin'], web3: ['web3', 'crypto', 'blockchain', 'defi'], crypto: ['crypto', 'blockchain', 'web3', 'defi'], blockchain: ['blockchain', 'crypto', 'web3'],
    nurse: ['nurse', 'nursing', 'rn '], accountant: ['accountant', 'accounting'], lawyer: ['lawyer', 'counsel', 'attorney', 'legal'], attorney: ['attorney', 'counsel', 'lawyer'],
    copywriter: ['copywriter', 'writer'], sales: ['sales', 'account executive', 'business development'], bdr: ['business development', 'bdr'], sdr: ['sales development', 'sdr'] };
  var EXEC = /\b(director|vp|svp|evp|vice president|head of|chief|cto|ceo|cfo|coo|cmo|cpo|ciso|cro)\b/i;      // "Director and above" in the level list
  function match(j, f) {
    if (mute.c[j[2]]) return false;
    if (f.done && f.done[j[0]]) return false;
    if (f.real && (j[22] || !(j[16] >= f.realSince))) return false;
    if (mute.w.length) { var low = j[1].toLowerCase(); for (var w = 0; w < mute.w.length; w++) if (low.indexOf(mute.w[w]) >= 0) return false; }
    if (f.cat && j[5] !== f.cat) return false;
    if (f.lvl && (f.lvl === 'Exec' ? !EXEC.test(j[1]) : j[6] !== f.lvl)) return false;
    if (f.loc && j[14].indexOf(f.loc) < 0) return false;
    if (f.cityRx && !f.cityRx.test(j[3] || '')) return false;
    if (f.rc && j[4] && !j[20] && j[24] && j[24].length && j[24].indexOf(f.rc) < 0) return false;    // remote, but only for other countries                                        // a city typed by the visitor, matched in the posting's own place line
    if ((f.remote || f.hybrid) && !((f.remote && j[4]) || (f.hybrid && j[25]))) return false;     // both ticked: either kind
    if (f.xl && f.xl.length && f.xl.indexOf(j[6]) >= 0) return false;                             // levels the visitor leaves out
    if (f.entry && !j[10]) return false;
    if (f.crypto && !j[15]) return false;
    if (f.any && !(j[20] && j[4])) return false;
    if (f.perk && j[18].indexOf(f.perk) < 0) return false;
    if (f.etype && j[19] !== f.etype) return false;
    if (hidden[j[0]]) return false;
    if (f.since && !(j[16] >= f.since)) return false;
    if (f.sal === 1 && !j[8]) return false;
    if (f.sal > 1 && !(j[13] >= f.sal) && !(f.nosal && !j[8])) return false;      // "also show jobs that do not state pay" lets the unknowns through
    for (var i = 0; i < f.skills.length; i++) if (j[7].indexOf(f.skills[i]) < 0) return false;
    if (f.words.length) {
      var hay = f.titles ? j[1].toLowerCase() : j[17] || (j[17] = (j[1] + ' ' + j[2] + ' ' + j[3] + ' ' + j[7].join(' ')).toLowerCase());
      for (var k = 0; k < f.words.length; k++) {
        var alts = SYN[f.words[k]];
        if (!alts) { if (hay.indexOf(f.words[k]) < 0) return false; continue; }
        var hit = false;
        for (var a = 0; a < alts.length && !hit; a++) hit = (' ' + hay + ' ').indexOf(alts[a]) >= 0;
        if (!hit) return false;
      }
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
  function ageOf(pi) {            // [label, fresh] from a yyyymmdd number
    if (!pi) return ['', false];
    var d = new Date(Math.floor(pi / 10000), Math.floor(pi / 100) % 100 - 1, pi % 100), now = new Date();
    var days = Math.max(0, Math.round((new Date(now.getFullYear(), now.getMonth(), now.getDate()) - d) / 864e5));
    return [days === 0 ? 'Today' : days < 14 ? days + 'd' : days < 60 ? Math.floor(days / 7) + 'w' : Math.floor(days / 30) + 'mo', days <= 2];
  }
  // How long ago, in words, for an age in seconds under 24 hours; '' for anything older (the day label stays).
  // Short for list rows ("now", "20 min", "3 h": the age column is 44px wide), long for a sentence ("20 minutes ago").
  // An age below zero (a time in the future, a clock that is off) reads as "now", never as a negative number.
  function ago(sec, full) {
    if (!(sec < 86400)) return '';
    var m = Math.max(0, Math.floor(sec / 60)), h = Math.floor(m / 60);
    if (!m) return full ? 'just now' : 'now';
    if (!h) return full ? m + (m === 1 ? ' minute ago' : ' minutes ago') : m + ' min';
    return full ? h + (h === 1 ? ' hour ago' : ' hours ago') : h + ' h';
  }
  // Every <time data-t="seconds since 1970"> younger than 24 hours says how long ago that was and is marked new; data-long asks for the
  // sentence form. Runs on load, after every list a script renders (see decorate) and once a minute. What the page was built with stays
  // in data-day and comes back when the posting turns a day old while the page is open.
  function freshen(scope) {
    var now = Date.now() / 1000;
    Array.prototype.forEach.call((scope || document).querySelectorAll('time[data-t]'), function (el) {
      var label = ago(now - Number(el.getAttribute('data-t') || NaN), el.hasAttribute('data-long'));
      if (label) {
        if (!el.hasAttribute('data-day')) el.setAttribute('data-day', el.textContent);
        if (el.textContent !== label) el.textContent = label;
        el.classList.add('new');
      } else if (el.hasAttribute('data-day')) { el.textContent = el.getAttribute('data-day'); el.removeAttribute('data-day'); }
    });
  }
  /* ---------- flags: a country is never shown without one ---------- */
  // Chrome and Edge on Windows have no flag pictures and print the two letters instead; there the icon becomes a small badge with the code
  var flagsOk = (function () {
    // only Windows lacks flag pictures: elsewhere the canvas test (which loads the emoji font, about 260 ms of a phone's main thread
    // on the home page, Lighthouse 24 Nov 2026) is skipped
    if (!/Windows/.test(navigator.userAgent)) return true;
    try {
      var c = document.createElement('canvas').getContext('2d'); c.font = '16px sans-serif';
      return c.measureText('\uD83C\uDDFA\uD83C\uDDF8').width < c.measureText('\uD83C\uDDFA').width * 1.6;
    } catch (e) { return true; }
  })();
  function flag(code) {
    if (!flagsOk) return '<i class="fl cc">' + code + '</i>';
    return '<i class="fl">' + String.fromCodePoint(0x1F1E6 + code.charCodeAt(0) - 65, 0x1F1E6 + code.charCodeAt(1) - 65) + '</i>';
  }
  function flags(codes) { return (codes || []).map(flag).join(''); }
  if (!flagsOk) {
    var letters = function (t) { return t.replace(/[\uD83C][\uDDE6-\uDDFF]/g, function (m) { return String.fromCharCode(65 + m.charCodeAt(1) - 0xDDE6); }); };
    var plain = function (root) {
      Array.prototype.forEach.call((root || document).querySelectorAll('i.fl:not(.cc)'), function (el) {
        var t = letters(el.textContent); if (t === el.textContent) { el.remove(); return; }       // a globe has no letters: drop it
        el.textContent = t; el.className = 'fl cc';
      });
      Array.prototype.forEach.call((root || document).querySelectorAll('option'), function (o) { if (/[\uD83C][\uDDE6-\uDDFF]/.test(o.textContent)) o.textContent = o.textContent.replace(/[\uD83C][\uDDE6-\uDDFF]/g, '').trim(); });
    };
    plain(); document.addEventListener('DOMContentLoaded', function () { plain(); });
  }
  var mySkills = (get('hrn_profile', {}).skills || []).filter(function (s) { return typeof s === 'string'; });
  /* The skills a visitor has: the ones picked on "For you" and, when a resume was made in the builder here, every skill its text
     names (resumai shows a job's skills as "on your resume" and "to grow"). Read once per page; nothing leaves the browser.
     A name of one or two letters (Go, R, C) counts only when it is an item of the resume's skills line: "go" is also a word. */
  var cvSkillsLine = {}, cvText = (function () {
    var cv = get('hrn_resume', null), parts = [];
    if (!cv || typeof cv !== 'object') return '';
    String(cv.skills || '').split(',').forEach(function (x) { x = x.trim().toLowerCase(); if (x) cvSkillsLine[x] = 1; });
    parts.push(cv.title, cv.summary, cv.skills);
    ['exp', 'proj', 'cert'].forEach(function (k) { (Array.isArray(cv[k]) ? cv[k] : []).forEach(function (x) { if (x) parts.push(x.role, x.name, x.text); }); });
    var t = parts.filter(function (x) { return typeof x === 'string'; }).join('\n').toLowerCase();
    return t.replace(/\s/g, '').length > 40 ? t : '';
  })(), haveMemo = {};
  function have(t) {
    if (mySkills.indexOf(t) >= 0) return true;
    if (!cvText) return false;
    var k = t.toLowerCase();
    if (haveMemo[k] == null) haveMemo[k] = k.length <= 2 ? !!cvSkillsLine[k]
      : new RegExp('(^|[^a-z0-9+#])' + k.replace(/[.*+?^${}()|[\]\\]/g, '\\$&') + '(?![a-z0-9+#])').test(cvText);
    return haveMemo[k];
  }
  var knowsSkills = mySkills.length > 0 || !!cvText;
  function skillFit(j) {           // "2 of 3 skills": how many of the skills this job names the visitor has (only when the visitor named some)
    if (!knowsSkills || !j[7] || !j[7].length) return '';
    var hit = j[7].filter(have).length;
    return hit ? '<span class="pill fit" title="Skills you have, of the skills this job names">' + hit + ' of ' + j[7].length + ' skills</span>' : '';
  }
  function tagPills(tags) {        // a job's first three skills; with a resume or answers, the ones you have first (✓), the rest "to grow"
    if (!knowsSkills) return tags.slice(0, 3).map(function (t) { return '<span class="pill">' + esc(t) + '</span>'; }).join('');
    return tags.filter(have).concat(tags.filter(function (t) { return !have(t); })).slice(0, 3).map(function (t) {
      return have(t) ? '<span class="pill have" title="On your resume">✓ ' + esc(t) + '</span>' : '<span class="pill grow" title="To grow: not on your resume yet">' + esc(t) + '</span>';
    }).join('');
  }
  function card(j, more, badge) {
    var pills = (badge ? '<span class="pill acc">' + esc(badge) + '</span>' : '') + skillFit(j) + (j[11] ? '<span class="pill acc">Featured</span>' : '') + (j[26] ? '<span class="pill urg">Urgently hiring</span>' : '') +
      (j[4] ? '<span class="pill ok">' + (j[20] ? 'Remote, anywhere' : 'Remote') + '</span>' : j[25] ? '<span class="pill">Hybrid</span>' : '') + (j[6] ? '<span class="pill">' + esc(j[6] === 'Lead' ? 'Lead and above' : j[6]) + '</span>' : '') +
      tagPills(j[7]);
    var place = j[3].length > 60 ? j[3].slice(0, 57) + '…' : j[3];
    var ag = ageOf(j[16]);
    return '<li class="job' + (j[11] ? ' feat' : '') + '"><a href="' + P + '/job/' + j[0] + '/">' + avatar(j[2], j[21], false) +
      '<span><span class="jt">' + esc(j[1]) + '</span><span class="js">' + esc(j[2]) + (place ? ' · ' + flags(j[24]) + esc(place) : '') +
      (more ? ' · +' + more + ' more location' + (more > 1 ? 's' : '') : '') + '</span></span>' +
      '<span class="jr"><span class="jp' + (j[8] ? '' : ' none') + '">' + (j[8] ? esc(j[8].slice(0, 28)) : '—') + '</span><span class="pills">' + pills + '</span><time' + (j[23] ? ' data-t="' + j[23] * 60 + '"' : '') + (ag[1] ? ' class="new"' : '') + '>' + esc(ag[0]) + '</time></span></a></li>';
  }
  // mark cards of jobs the visitor already saved, applied to or opened (works for static and script-built lists)
  function decorate(scope) {
    freshen();                                              // whole page, not only `scope`: the search page fills its preview pane just before it calls this
    var mine = get('hrn_jobs', {}), seen = {};
    get('hrn_seen', []).forEach(function (x) { seen[x.s] = 1; });
    (scope || document).querySelectorAll('.job > a').forEach(function (a) {
      if (a.getAttribute('data-d')) return;
      var m = (a.getAttribute('href') || '').match(/\/job\/([^/]+)\/?$/);
      if (!m) return;
      a.setAttribute('data-d', '1');
      var sub = a.querySelector('.js');                       // rows of a company the visitor chose to hide disappear from ready-made lists too
      if (sub && mute.c[sub.textContent.split(' · ')[0]]) { a.parentNode.hidden = true; return; }
      var slug = decodeURIComponent(m[1]), rec = mine[slug], pills = a.querySelector('.pills');
      if (rec && pills) pills.insertAdjacentHTML('afterbegin', '<span class="pill acc">' + (rec.st === 'saved' ? 'Saved' : rec.st === 'closed' ? 'Closed out' : rec.st === 'offer' ? 'Offer' : rec.st === 'interview' ? 'Interviewing' : 'Applied') + '</span>');
      else if (seen[slug]) a.parentNode.classList.add('seen');
    });
  }
  /* "Are you sure?" drawn on the page, next to the button that was pressed. The browser's own confirm() and prompt() windows are
     switched off in some browsers and in-app views; there they answer "no" without showing anything, so a Delete button did
     nothing at all (the owner pressed Delete on a job on 18 Nov 2026 and no request ever left the page). sure() resolves to
     true or false; askText() to the text typed, or null. */
  function sureBox(btn, text, inner, pick) {
    return new Promise(function (done) {
      var old = document.querySelector('.sure-box'); if (old && old._end) old._end();
      var box = document.createElement('div'), inDom = btn && btn.parentNode && document.body.contains(btn);
      box.className = 'sure-box' + (inDom ? '' : ' float'); box.setAttribute('role', 'alertdialog'); box.setAttribute('aria-label', text);
      box.innerHTML = '<p class="sure-t">' + esc(text) + '</p>' + inner;
      var end = function (v) { if (!box.parentNode) return; box.parentNode.removeChild(box); if (inDom && btn.focus) { try { btn.focus(); } catch (e) {} } done(v); };
      box._end = function () { end(pick(box, false)); };
      box.addEventListener('click', function (ev) { var b = ev.target.closest ? ev.target.closest('[data-sure]') : null; if (b) { ev.preventDefault(); ev.stopPropagation(); end(pick(box, b.getAttribute('data-sure') === '1')); } });
      box.addEventListener('keydown', function (ev) { if (ev.key === 'Escape') end(pick(box, false)); else if (ev.key === 'Enter' && ev.target.tagName === 'INPUT') { ev.preventDefault(); end(pick(box, true)); } });
      if (inDom) btn.parentNode.insertBefore(box, btn.nextSibling); else document.body.appendChild(box);
      var first = box.querySelector('input') || box.querySelector('[data-sure="0"]'); if (first) { try { first.focus(); if (first.select) first.select(); } catch (e) {} }
    });
  }
  function sure(btn, text, yes) {
    return sureBox(btn, text, '<p class="sure-act"><button type="button" class="btn sm" data-sure="1">' + esc(yes || 'Yes') + '</button><button type="button" class="btn ghost sm" data-sure="0">Cancel</button></p>',
      function (box, ok) { return !!ok; });
  }
  function askText(btn, text, value, yes) {
    return sureBox(btn, text, '<p class="sure-act"><input type="text" maxlength="80" value="' + esc(value || '') + '" aria-label="' + esc(text) + '"><button type="button" class="btn sm" data-sure="1">' + esc(yes || 'Save') +
      '</button><button type="button" class="btn ghost sm" data-sure="0">Cancel</button></p>', function (box, ok) { return ok ? box.querySelector('input').value : null; });
  }
  /* A pasted posting -> the fields of the form, by plain rules (seen on hirehi.ru, 18 Nov 2026: "paste the text and the fields fill
     themselves"; there an AI does it, here nothing leaves the browser). What the rules do not find stays for the person to type. */
  function readPosting(text) {
    var lines = String(text || '').replace(/\r/g, '').split('\n').map(function (l) { return l.replace(/[​-‍﻿]/g, '').trim(); }), out = {}, used = {};
    var body = lines.filter(Boolean), all = body.join('\n');
    if (!body.length || all.length < 60) return out;           // a word or two is not a posting
    var label = function (names) {                              // "Location: Berlin", "Salary - $90K", "Company | Acme"
      for (var i = 0; i < body.length; i++) {
        var m = new RegExp('^(?:[^A-Za-z0-9]{0,4})(?:' + names + ')\\s*[:\\-–|]\\s*(.{2,140})$', 'i').exec(body[i]);
        if (m) { used[i] = 1; return m[1].trim(); }
      }
      return '';
    };
    var url = /https?:\/\/[^\s<>"')\]]+/g, links = all.match(url) || [];
    var apply = links.filter(function (u) { return /apply|career|jobs?[./-]|greenhouse|lever\.co|ashby|workable|workday|recruitee|personio|teamtailor|smartrecruiters/i.test(u); })[0] || links[0] || '';
    if (apply) out.apply_url = apply.replace(/[.,;]+$/, '');
    var t = label('job title|title|position|role|vacancy');
    if (!t) for (var i = 0; i < body.length; i++) {            // else the first line that reads like a title
      var l = body[i].replace(/#[\w-]+/g, '').replace(/^[^A-Za-z0-9(]+/, '').replace(/^(?:we(?:['’]| a)re hiring|hiring|now hiring|vacancy|job|open role|open position)\s*[:!\-–]\s*/i, '').trim();
      if (l.length >= 4 && l.length <= 120 && !/^https?:/i.test(l) && !/[.!?]$/.test(l) && l.split(' ').length <= 14) { t = l; used[i] = 1; break; }
    }
    if (t) {
      var at = /^(.{4,90}?)\s+(?:at|@)\s+([A-Z][\w&.,' -]{1,60})$/.exec(t);             // "Senior Engineer at Acme"
      if (at) { t = at[1].trim(); out.company = at[2].trim(); }
      out.title = t.replace(/\s*[(\[](?:m\/f\/d|f\/m\/d|m\/w\/d|all genders)[)\]]/i, '').replace(/\s{2,}/g, ' ').slice(0, 120);
    }
    var co = label('company|employer');
    if (co) out.company = co.slice(0, 80);
    var pay = label('salary|compensation|pay|rate');
    if (!pay) { var pm = /(?:[$€£]\s?\d[\d,.]*\s?[kK]?(?:\s?(?:-|–|—|to)\s?[$€£]?\s?\d[\d,.]*\s?[kK]?)?|\d{2,3}(?:[,.]\d{3})?\s?[kK]?\s?(?:-|–|—|to)\s?\d{2,3}(?:[,.]\d{3})?\s?[kK]?\s?(?:USD|EUR|GBP|usd|eur|gbp))(?:\s?(?:\/|per|a|an)\s?(?:year|yr|annum|month|mo|hour|hr))?/.exec(all); if (pm) pay = pm[0]; }
    if (pay) out.salary = pay.replace(/\s+/g, ' ').trim().slice(0, 60);
    var loc = label('location|where|based in|office|city');
    var remote = /\b(?:fully remote|100% remote|remote[- ]first|remote|work from home|work from anywhere|wfh|distributed team)\b/i.test(all) && !/\b(?:not remote|no remote|on-?site only)\b/i.test(all);
    var hybrid = /\bhybrid\b/i.test(all);
    if (!loc && remote) { var rg = /\bremote\s*(?:[,(–-]|in|within|from|across)\s*\(?((?:the )?(?:US|USA|United States|UK|United Kingdom|EU|Europe|EMEA|APAC|LATAM|Americas|Canada|Germany|worldwide|anywhere))\b/i.exec(all); loc = rg ? 'Remote, ' + rg[1].replace(/^the /i, '').trim() : 'Remote'; }
    if (loc) out.location = loc.replace(/\s+/g, ' ').slice(0, 120);
    if (remote && !hybrid) out.remote = true;
    var ty = label('employment type|job type|type|contract type|commitment') + ' ' + all.slice(0, 1500);
    out.etype = /\bintern(?:ship)?\b/i.test(ty) ? 'Internship' : /\bpart[- ]time\b/i.test(ty) ? 'Part-time' : /\b(?:contract(?:or)?|freelance|temporary|fixed[- ]term)\b/i.test(ty) ? 'Contract' : /\bfull[- ]time\b/i.test(ty) ? 'Full-time' : '';
    var rest = body.filter(function (l, i) { return !used[i] && !/^https?:\/\/\S+$/.test(l) && !/^(?:full[- ]time|part[- ]time|contract|internship|remote|hybrid|on-?site)$/i.test(l) && !/^(?:[^A-Za-z0-9]{0,4})(?:location|where|salary|compensation|pay|rate|company|employer|employment type|job type|type|apply|how to apply|contact)\s*[:\-–|]/i.test(l); }).join('\n').replace(url, '').replace(/[ \t]{2,}/g, ' ').trim();
    if (rest.length > 1500) { rest = rest.slice(0, 1500); rest = rest.slice(0, Math.max(rest.lastIndexOf('. '), rest.lastIndexOf('\n'), 1200) + 1).trim(); }
    if (rest.length >= 80) out.description = rest;
    return out;
  }
  // the jobs that fit the For you answers (hrn_profile), newest first: the home window's "For you" tab and the account's "Jobs that fit
  // you". null when no answer is given.
  function fitTest(p) {
    p = p || {};
    var cats = p.cats || [], skills = p.skills || [], pay = Number(p.pay) || 0;
    if (!cats.length && !skills.length && !p.where && !pay) return null;
    return function (j) {
      if (j[22] || (cats.length && cats.indexOf(j[5]) < 0)) return false;
      if ((p.where === 'remote' && !j[4]) || (p.where === 'hybrid' && !j[25]) || (p.where === 'office' && j[4])) return false;
      if (pay && j[13] && j[13] < pay) return false;
      return !skills.length || j[7].some(function (t) { return skills.indexOf(t) >= 0; });
    };
  }
  window.HRN = { fitTest: fitTest, readPosting: readPosting, sure: sure, askText: askText, mute: mute, saveMute: function () { set('hrn_mute', mute); }, parse: parse, match: match, load: load, loadHead: loadHead, fromApi: fromApi, rowsOf: rowsOf, listOf: listOf, fitQuery: fitQuery, heavyOk: heavyOk, collapse: collapse, card: card, decorate: decorate, get: get, set: set, esc: esc, today: today, base: P };

  /* ---------- "Save this list" on a list page: the list goes into My jobs as the search that gives the same jobs, and My jobs counts
     the jobs posted since the last look. A second press takes it out again. Nothing is sent anywhere. ---------- */
  Array.prototype.forEach.call(document.querySelectorAll('[data-save-list]'), function (btn) {
    var qs = btn.getAttribute('data-save-list'), label = btn.getAttribute('data-label') || document.title;
    var paint = function () {
      var on = get('hrn_searches', []).some(function (x) { return x.qs === qs; });
      btn.textContent = on ? 'Saved to My jobs ✓' : 'Save this list'; btn.setAttribute('aria-pressed', on ? 'true' : 'false');
    };
    paint();
    btn.addEventListener('click', function () {
      var all = get('hrn_searches', []), had = all.some(function (x) { return x.qs === qs; });
      all = had ? all.filter(function (x) { return x.qs !== qs; }) : [{ qs: qs, label: label, seen: today() }].concat(all);
      set('hrn_searches', all.slice(0, 30)); paint();
    });
  });

  /* ---------- live lists: the home "Latest jobs" window and the first page of /new/ take the newest jobs from /api/latest, on load
     and then once a minute while the tab is in view. A job the server found after the page was built slides in where its posting
     time puts it (for a new job, the top), one row at a time. Its row says when we found it ("Found 3 minutes ago") and, when the
     employer's date is more than a day earlier, that date too ("posted Aug 21"). Both come from the server unchanged; a job without a
     time we found it gets no such line. If the request fails, the list stays as the build wrote it. ---------- */
  (function () {
    var ul = document.querySelector('ul.jobs[data-live]');
    if (!ul || !window.fetch) return;
    var home = ul.getAttribute('data-live') === 'home', since = ul.getAttribute('data-since') || '';
    var cap = home ? ul.children.length : 0;                // the home window keeps its size: a row in, the bottom row out
    var calm = !!(window.matchMedia && matchMedia('(prefers-reduced-motion: reduce)').matches);
    // The jobs the first request brings go in at once, without the slide and the glow: they belong to the page as it opens, and a
    // window that keeps moving for three seconds after the first paint is what PageSpeed's Speed Index counts as a page still loading
    // (20 Nov 2026). Only the jobs found while the page stays open slide in.
    var still = true;
    var MON = ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun', 'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec'], thisYear = new Date().getFullYear();
    var dayName = function (y, m, d) { return MON[m - 1] + ' ' + d + (y !== thisYear ? ', ' + y : ''); };
    var isoDay = function (iso) { var m = /^(\d{4})-(\d\d)-(\d\d)/.exec(iso || ''); return m ? [+m[1], +m[2], +m[3]] : null; };
    // the time a row sorts by, in seconds: what the build sorts by too (the exact posting time, or the start of the posting day, UTC)
    var rowTs = function (li) {
      if (li.getAttribute('data-ts')) return +li.getAttribute('data-ts');
      var t = li.querySelector('time'); if (!t) return 0;
      if (t.getAttribute('data-t')) return +t.getAttribute('data-t');
      var d = isoDay(t.getAttribute('datetime')); return d ? Date.UTC(d[0], d[1] - 1, d[2]) / 1000 : 0;
    };
    var shown = function () {
      var slugs = {}, names = {}, cos = {};
      Array.prototype.forEach.call(ul.children, function (li) {
        var a = li.querySelector('a'), m = a && (a.getAttribute('href') || '').match(/\/job\/([^/]+)\/?$/);
        if (m) slugs[decodeURIComponent(m[1])] = 1;
        var jt = li.querySelector('.jt'), js = li.querySelector('.js'), co = js ? js.textContent.split(' · ')[0] : '';
        cos[co] = 1; if (jt) names[co + '\n' + jt.textContent] = 1;    // a job listed in several places is one row (+2 more locations)
      });
      return { slugs: slugs, names: names, cos: cos };
    };
    var foundText = function (o) {
      var f = Date.parse(o.found_at || ''); if (isNaN(f)) return '';
      f /= 1000;
      var age = Date.now() / 1000 - f, when = ago(age, true);
      if (!when) { var d = new Date(f * 1000); when = 'on ' + dayName(d.getFullYear(), d.getMonth() + 1, d.getDate()); }
      var p = isoDay(o.posted), pt = o.ts || (p ? Date.UTC(p[0], p[1] - 1, p[2]) / 1000 : 0);
      return 'Found ' + when + (p && pt && f - pt > 86400 ? ' · posted ' + dayName(p[0], p[1], p[2]) : '');
    };
    var row = function (o) {
      var p = isoDay(o.posted), j = [];                       // the same row as every list: card() reads these places of a job
      j[0] = o.slug; j[1] = o.title; j[2] = o.company; j[3] = o.location || ''; j[4] = o.remote ? 1 : 0; j[6] = o.level || '';
      j[7] = o.tags || []; j[8] = o.salary || ''; j[11] = o.featured ? 1 : 0; j[16] = p ? p[0] * 10000 + p[1] * 100 + p[2] : 0;
      j[20] = o.anywhere ? 1 : 0; j[25] = o.hybrid ? 1 : 0; j[26] = o.urgent ? 1 : 0;
      j[21] = o.logo || ''; j[23] = o.t && Date.now() / 1000 - o.t < 7 * 86400 ? Math.floor(o.t / 60) : 0; j[24] = o.cc || [];
      var box = document.createElement('ul'); box.innerHTML = card(j);
      var li = box.firstChild, ft = foundText(o);
      li.setAttribute('data-ts', o.ts || 0); if (!still) li.classList.add('lv');
      if (ft) {
        var s = document.createElement('span'); s.className = 'jf'; s.setAttribute('data-found', o.found_at); s.setAttribute('data-posted', o.posted || '');
        s.setAttribute('data-pts', o.ts || 0); s.textContent = ft;
        li.querySelector('.jt').parentNode.appendChild(s);
      }
      return li;
    };
    var say = (function () {                                  // a screen reader hears that rows were added; the page does not jump
      var r = document.createElement('p'); r.className = 'vh'; r.setAttribute('aria-live', 'polite'); ul.parentNode.insertBefore(r, ul);
      return function (t) { r.textContent = t; };
    })();
    var queue = [], busy = false;
    var drop = function (li) {
      if (calm || still) { li.remove(); return; }
      li.classList.add('lv-out'); setTimeout(function () { li.remove(); }, 420);
    };
    var next = function () {
      var it = queue.shift();
      if (!it) { busy = false; still = false; return; }
      busy = true;
      var have = shown();
      if (have.slugs[it.slug] || have.names[it.company + '\n' + it.title] || (home && have.cos[it.company])) return next();
      var li = row(it), ts = +li.getAttribute('data-ts'), rows = Array.prototype.slice.call(ul.children), at = null;
      for (var i = 0; i < rows.length; i++) { if (rows[i].classList.contains('feat') || rows[i].classList.contains('lv-out')) continue; if (rowTs(rows[i]) < ts) { at = rows[i]; break; } }
      var live = rows.filter(function (r_) { return !r_.classList.contains('lv-out'); }).length;
      if (!at && (!home || live >= cap)) return next();      // older than every row here: it belongs further down (or on a later page)
      if (!calm && !still) { li.classList.add('lv-in'); li.addEventListener('animationend', function (e) { if (e.target === li) li.classList.remove('lv-in'); }); }
      ul.insertBefore(li, at);
      if (home && live + 1 > cap) { var bottom = Array.prototype.filter.call(ul.children, function (r_) { return !r_.classList.contains('lv-out'); }).pop(); if (bottom && bottom !== li) drop(bottom); }
      try { decorate(li); } catch (e) {}
      added++;
      say(added === 1 ? 'A new job was added to the list.' : added + ' new jobs were added to the list.');
      if (calm || still) next(); else setTimeout(next, 450);
    };
    var added = 0, last = 0;
    var tick = function () {                                  // the "found" lines age while the page is open
      Array.prototype.forEach.call(ul.querySelectorAll('.jf[data-found]'), function (s) {
        var t = foundText({ found_at: s.getAttribute('data-found'), posted: s.getAttribute('data-posted'), ts: +s.getAttribute('data-pts') });
        if (t && s.textContent !== t) s.textContent = t;
      });
    };
    var pull = function () {
      if (document.visibilityState === 'hidden') return;
      last = Date.now();
      fetch(P + '/api/latest?limit=30', { cache: 'no-store' }).then(function (r) { if (!r.ok) throw r.status; return r.json(); }).then(function (d) {
        var jobs = (d && d.jobs) || [];
        jobs = jobs.filter(function (o) { return o && o.slug && o.title && o.company && !(home && o.pool) && !(since && (o.posted || '') < since); });
        jobs.sort(function (a, b) { return (a.ts || 0) - (b.ts || 0); });     // oldest first: each one goes in above the last, so the newest ends on top
        queue = queue.concat(jobs);
        tick();
        if (!busy) next();
      }).catch(function () {});                               // no feed (an old server, a static copy, offline): the built list stays
    };
    pull();
    setInterval(pull, 60000);
    document.addEventListener('visibilitychange', function () { if (document.visibilityState === 'visible' && Date.now() - last > 60000) pull(); });
  })();

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
  /* ---------- job page on a phone: the sticky Apply bar only while the page's own Apply button is out of view (24 Nov 2026: since the
     button moved to the top on phones, both showed at once on the first screen) ---------- */
  (function () {
    // v4: the same goes for the small Apply card that stays in view in the side column on wide screens (.jstick)
    var own = document.getElementById('apply'), bars = document.querySelectorAll('.mbar, .jstick');
    if (!own || !bars.length || !window.IntersectionObserver) return;
    new IntersectionObserver(function (en) { Array.prototype.forEach.call(bars, function (b) { b.classList.toggle('off', en[0].isIntersecting); }); }).observe(own);
  })();
  /* ---------- job page: where the posting comes from, and a ready question for an AI assistant ---------- */
  (function () {
    var apply = $('apply'), h1 = document.querySelector('.jhead h1'), co = document.querySelector('.jhead .js a');
    if (!apply || !h1) return;
    var host = ''; try { host = new URL(apply.href).hostname.replace(/^www\./, ''); } catch (e) {}
    var ats = /greenhouse\.io$/.test(host) ? 'Greenhouse' : /lever\.co$/.test(host) ? 'Lever' : /ashbyhq\.com$/.test(host) ? 'Ashby' : '';
    var pills = document.querySelector('.jhead .pills');
    var tg = host === 't.me';                 // a post read from a public Telegram channel: said plainly, no check mark
    if (pills && !pills.querySelector('.pill.src')) pills.insertAdjacentHTML('afterbegin', tg
      ? '<span class="pill src" title="Read from the public page of a Telegram job channel; not checked with the employer">From a Telegram channel</span>'
      : '<span class="pill ok src" title="Read from ' + (ats ? ats + ', the hiring system the employer itself uses' : 'the employer’s own careers site') + ', and re-checked every hour">✓ Employer’s own posting</span>');
    var title = h1.textContent.trim(), company = co ? co.textContent.trim() : '', url = location.href.split('#')[0].split('?')[0];
    var ask = 'I am looking at this job: "' + title + '"' + (company ? ' at ' + company : '') + ' (' + url + '). Explain in plain words what the role involves and what it requires, which interview questions I should prepare for, and what I should ask the employer. Then ask me about my experience and tell me how well I fit.';
    var q = encodeURIComponent(ask);
    var box = document.createElement('div');
    box.className = 'askai';
    box.innerHTML = '<p><b>Ask an AI assistant about this job</b><span>Opens with a ready question; what you type there goes to that service.</span></p>'
      + '<p class="askai-l"><a href="https://chatgpt.com/?q=' + q + '" target="_blank" rel="nofollow noopener">ChatGPT</a><a href="https://claude.ai/new?q=' + q + '" target="_blank" rel="nofollow noopener">Claude</a>'
      + '<a href="https://www.perplexity.ai/search?q=' + q + '" target="_blank" rel="nofollow noopener">Perplexity</a></p>';
    var after = document.querySelector('aside .rmbox') || apply;
    after.parentNode.insertBefore(box, after.nextSibling);
  })();

  /* ---------- interview questions: practise out loud. The browser reads each question, listens to the answer (where it can),
     and checks it the way the interview answer builder does: 60 to 90 seconds, a number, "I" more than "we". This site keeps nothing; the browser's own speech service turns the words into text. ---------- */
  (function () {
    var qs = Array.prototype.slice.call(document.querySelectorAll('ol.iq li h3'));
    if (!qs.length) return;
    var SR = window.SpeechRecognition || window.webkitSpeechRecognition, say = window.speechSynthesis;
    var box = document.createElement('section');
    box.className = 'sec voicepr'; box.id = 'practise';               // the "Practise out loud" button under the opening paragraph jumps here
    box.innerHTML = '<div class="vp-card"><p class="vp-h"><b>Practise out loud</b><span>' + (SR ? 'The page reads a question, listens to your answer and checks it. This site keeps nothing; your browser’s own speech service turns your words into text.' : 'The page reads a question; type your answer and it is checked. This browser cannot listen; Chrome and Edge can.') + '</span></p>'
      + '<p class="vp-q" id="vp-q"></p><div class="vp-row"><button class="btn primary sm" type="button" id="vp-start">Start question 1</button><button class="btn ghost sm" type="button" id="vp-stop" hidden>I have finished</button>'
      + '<button class="btn ghost sm" type="button" id="vp-next" hidden>Next question</button><span class="note" id="vp-time"></span></div>'
      + (SR ? '' : '<textarea id="vp-type" rows="4" placeholder="Type your answer here" hidden></textarea>') + '<p class="vp-said" id="vp-said"></p><ul class="vp-checks" id="vp-checks"></ul></div>';
    var first = document.querySelector('ol.iq'); first.parentNode.insertBefore(box, first);
    var i = 0, rec = null, said = '', t0 = 0, tick = 0;
    var el = function (id) { return document.getElementById(id); };
    var check = function () {
      var secs = Math.round((Date.now() - t0) / 1000), txt = SR ? said : (el('vp-type') || {}).value || '', w = txt.trim() ? txt.trim().split(/\s+/).length : 0;
      var I = (txt.match(/\bI\b|\bI'm\b|\bI've\b|\bmy\b/g) || []).length, we = (txt.match(/\bwe\b|\bour\b/gi) || []).length, num = /\d|\b(one|two|three|four|five|six|seven|eight|nine|ten|percent|half|double)\b/i.test(txt);
      var rows = [[secs >= 45 && secs <= 120, 'Length: ' + secs + ' seconds' + (secs < 45 ? ', short: add the result and what you did yourself.' : secs > 120 ? ', long: cut the background.' : ', a good length.')],
        [num, num ? 'You gave a number. Results with numbers are remembered.' : 'No number: say what changed, by how much.'],
        [I >= we, I >= we ? 'You said what you did yourself.' : 'More “we” than “I”: say which part was yours.'],
        [w >= 60, w + ' words' + (w < 60 ? ': give the situation, what you did and the result.' : '.')]];
      // spoken answers only: the pace (this page calls 110 to 170 words a minute easy to follow) and filler words the browser heard
      var wpm = SR && secs >= 15 && w >= 20 ? Math.round(w * 60 / secs) : 0;
      if (wpm) rows.push([wpm >= 110 && wpm <= 170, 'Pace: ' + wpm + ' words a minute' + (wpm > 170 ? ', fast: slow down and pause after the result.' : wpm < 110 ? ', slow: shorter sentences, fewer pauses.' : ', easy to follow.') + ' This page calls 110 to 170 comfortable.']);
      if (SR && w) {
        var fill = {}, nf = 0;
        (txt.toLowerCase().match(/\b(?:you know|basically|actually|kind of|sort of|literally|i mean|um+|uh+|erm)\b/g) || []).forEach(function (x) { fill[x] = (fill[x] || 0) + 1; nf++; });
        rows.push([nf <= 2, nf ? 'Filler words: ' + Object.keys(fill).map(function (k) { return '“' + k.replace(/^i /, 'I ') + '”' + (fill[k] > 1 ? ' ×' + fill[k] : ''); }).join(', ') + (nf > 2 ? '. Pause instead.' : '.') : 'No filler words heard.']);
      }
      el('vp-checks').innerHTML = rows.map(function (r) { return '<li class="' + (r[0] ? 'ok' : 'fix') + '">' + r[1] + '</li>'; }).join('');
    };
    var stop = function () {
      clearInterval(tick); if (rec) { try { rec.stop(); } catch (e) {} rec = null; }
      el('vp-stop').hidden = true; el('vp-next').hidden = i >= qs.length - 1; el('vp-start').hidden = false; el('vp-start').textContent = 'Try again'; check();
    };
    var start = function () {
      var q = qs[i].textContent.trim(); el('vp-q').textContent = (i + 1) + '. ' + q; said = ''; el('vp-said').textContent = ''; el('vp-checks').innerHTML = '';
      el('vp-start').hidden = true; el('vp-next').hidden = true; el('vp-stop').hidden = false;
      var listen = function () {
        t0 = Date.now(); tick = setInterval(function () { el('vp-time').textContent = Math.round((Date.now() - t0) / 1000) + ' s'; }, 500);
        if (!SR) { var ta = el('vp-type'); ta.hidden = false; ta.value = ''; ta.focus(); return; }
        rec = new SR(); rec.lang = 'en-US'; rec.continuous = true; rec.interimResults = true;
        rec.onresult = function (ev) { var t = ''; for (var k = 0; k < ev.results.length; k++) t += ev.results[k][0].transcript + ' '; said = t; el('vp-said').textContent = t; };
        rec.onerror = function () { el('vp-said').textContent = 'The microphone is not available: allow it in the browser, or type in another browser.'; };
        try { rec.start(); } catch (e) {}
      };
      if (say) { try { say.cancel(); var u = new SpeechSynthesisUtterance(q); u.lang = 'en-US'; u.onend = listen; say.speak(u); return; } catch (e) {} }
      listen();
    };
    el('vp-start').addEventListener('click', start);
    el('vp-stop').addEventListener('click', stop);
    el('vp-next').addEventListener('click', function () { i = Math.min(qs.length - 1, i + 1); start(); });
  })();

  /* ---------- job page: the chance the posting is still open in 7 days, from the closings we have seen (data/survival.json) ---------- */
  (function () {
    var meta = document.querySelector('aside dl.meta'), apply = $('apply');
    if (!meta || !apply || !window.fetch) return;
    var tm = meta.querySelector('time[datetime]'), crumb = document.querySelector('.crumbs a[href*="/jobs/"]');
    if (!tm) return;
    var posted = new Date(tm.getAttribute('datetime').slice(0, 10) + 'T00:00:00Z'), cat = crumb ? (crumb.getAttribute('href').match(/\/jobs\/([^/]+)\//) || [])[1] : '';
    fetch(P + '/data/survival.json').then(function (r) { return r.ok ? r.json() : null; }).then(function (S) {
      if (!S || !S.all) return;
      var h = (cat && S.cat && S.cat[cat]) || S.all, age = Math.max(0, Math.floor((Date.now() - posted) / 864e5)), p = 1;
      var hz = function (a) { var i = 0; while (i < S.bands.length && a > S.bands[i]) i++; var v = h[i]; return v == null ? S.all[i] : v; };
      for (var d = 0; d < 7; d++) { var v = hz(age + d); if (v == null) return; p *= 1 - v; }
      var pct = Math.round(p * 100);
      meta.insertAdjacentHTML('beforeend', '<dt>Still open in 7 days</dt><dd><b>About ' + pct + '% likely</b><br><span class="note">From how often postings of this age' + (cat && S.cat && S.cat[cat] ? ' in this field' : '') + ' closed since we started watching on ' +
        new Date(S.since + 'T00:00:00Z').toLocaleDateString('en-US', { month: 'short', day: 'numeric' }) + ' (' + S.closed.toLocaleString('en-US') + ' closings so far). More exact every day.</span></dd>');
    }).catch(function () {});
  })();

  /* ---------- job page: when Apply is pressed, how much of the posting's skills the resume in this browser names (hh.ru warns
     before an application that does not fit). It never blocks: the employer's page opens as usual. ---------- */
  (function () {
    var apply = $('apply'), tagsEl = document.querySelector('#match');
    if (!apply || !tagsEl) return;
    apply.addEventListener('click', function () {
      var cv = get('hrn_resume', null), tags = (tagsEl.getAttribute('data-tags') || '').split('|').filter(Boolean);
      if (!cv || !tags.length || document.querySelector('.applyfit')) return;
      var text = [cv.title, cv.summary, cv.skills].concat((cv.exp || []).map(function (x) { return (x.role || '') + ' ' + (x.text || ''); })).join(' ').toLowerCase();
      if (text.replace(/\s+/g, ' ').length < 60) return;
      var has = tags.filter(function (t) { return text.indexOf(t.toLowerCase()) >= 0; }), miss = tags.filter(function (t) { return has.indexOf(t) < 0; });
      var m = (location.pathname.match(/\/job\/([^/]+)\//) || [])[1];
      apply.insertAdjacentHTML('afterend', '<p class="applyfit note"><b>Your resume names ' + has.length + ' of the ' + tags.length + ' skills this job names.</b> '
        + (miss.length ? 'Missing: ' + miss.slice(0, 5).map(esc).join(', ') + '. ' : '') + (m ? '<a href="' + P + '/resume/?job=' + m + '">Tailor it to this job</a>' : '') + '</p>');
    });
  })();

  /* ---------- job page: "Tailor my resume to this job" next to "Check my resume for this job" ---------- */
  Array.prototype.forEach.call(document.querySelectorAll('a.rmbox'), function (a) {
    var m = (a.getAttribute('href') || '').match(/[?&]job=([a-z0-9-]+)/);
    if (!m || a.nextElementSibling && a.nextElementSibling.classList.contains('rmbox') || document.querySelector('.jtwo')) return;   // v4: the page has its own "Tailor my resume" button
    var b = document.createElement('a');
    b.className = 'rmbox'; b.href = P + '/resume/?job=' + m[1];
    b.innerHTML = '<b>Tailor my resume to this job</b><span>Open the resume builder with this posting as the target</span>';
    a.parentNode.insertBefore(b, a.nextSibling);
  });

  /* ---------- header menus (rebuilt 25 Nov 2026, the owner: "can the menu be better?"). Built here, so the pages carry no extra bytes.
     Each menu is its hub link plus a small button that opens a panel of grouped links (the disclosure pattern: Enter or Space on the
     button, ArrowDown on either opens it and moves into it, arrows move inside, Escape closes it and gives the focus back to the button).
     Wide screens: the panel spans the window under the header and also opens on mouse hover; the jobs panel has a search box and
     the count of open jobs the build wrote on the nav (data-n). Phones: the same panel is a section of the menu that opens in place.
     The section of the page is marked on its menu (the hub or any link of its panel), and the mark steps aside while a panel is open. */
  (function () {
    var nav = $('nav');
    if (!nav || !header) return;
    var I = {     // line icons, 24 x 24, drawn like the field icons of build.py (ICON)
      search: '<circle cx="11" cy="11" r="7"/><path d="M20 20l-3.5-3.5"/>',
      clock: '<circle cx="12" cy="12" r="9"/><path d="M12 7v5l3 2"/>',
      pin: '<path d="M12 21s-7-6.2-7-11a7 7 0 0 1 14 0c0 4.8-7 11-7 11z"/><circle cx="12" cy="10" r="2.5"/>',
      home: '<path d="M3 11l9-7 9 7"/><path d="M5 10v10h14V10M10 20v-5h4v5"/>',
      target: '<circle cx="12" cy="12" r="9"/><circle cx="12" cy="12" r="5"/><circle cx="12" cy="12" r="1"/>',
      mark: '<path d="M6 3h12v18l-6-4-6 4z"/>',
      bag: '<rect x="3" y="7" width="18" height="13" rx="2"/><path d="M9 7V5a2 2 0 0 1 2-2h2a2 2 0 0 1 2 2v2M3 13h18"/>',
      half: '<circle cx="12" cy="12" r="9"/><path d="M12 3v9h9"/>',
      swap: '<path d="M4 8h15l-3-3M20 16H5l3 3"/>',
      globe: '<circle cx="12" cy="12" r="9"/><path d="M3 12h18M12 3c3 3.2 3 14.8 0 18M12 3c-3 3.2-3 14.8 0 18"/>',
      doc: '<path d="M6 3h8l4 4v14H6z"/><path d="M14 3v4h4M9 12h6M9 16h4"/>',
      cal: '<rect x="3" y="5" width="18" height="16" rx="2"/><path d="M3 10h18M8 3v4M16 3v4"/>',
      moon: '<path d="M20 14.5A8 8 0 0 1 9.5 4a8 8 0 1 0 10.5 10.5z"/>',
      sun: '<circle cx="12" cy="12" r="4"/><path d="M12 2v2M12 20v2M2 12h2M20 12h2M4.9 4.9l1.4 1.4M17.7 17.7l1.4 1.4M4.9 19.1l1.4-1.4M17.7 6.3l1.4-1.4"/>',
      cap: '<path d="M2 9l10-5 10 5-10 5L2 9z"/><path d="M6 11.5V16c0 1.5 2.7 3 6 3s6-1.5 6-3v-4.5"/>',
      sprout: '<path d="M12 21v-9"/><path d="M12 12c0-3.5-2.5-6-7-6 0 3.5 2.5 6 7 6zM12 14c0-3 2.2-5 7-5 0 3-2.2 5-7 5z"/>',
      steps: '<path d="M3 20h5v-5h5v-5h5V5h3"/>',
      code: '<path d="M8 7l-5 5 5 5M16 7l5 5-5 5"/>',
      gov: '<path d="M3 21h18M5 21v-9M10 21v-9M14 21v-9M19 21v-9M2 10l10-6 10 6z"/>',
      grid: '<rect x="4" y="4" width="7" height="7" rx="1.5"/><rect x="13" y="4" width="7" height="7" rx="1.5"/><rect x="4" y="13" width="7" height="7" rx="1.5"/><rect x="13" y="13" width="7" height="7" rx="1.5"/>',
      coin: '<circle cx="12" cy="12" r="9"/><path d="M15 9.5c-.5-1-1.6-1.5-3-1.5-1.7 0-2.8.8-2.8 2s1.1 1.6 2.8 2 2.8.8 2.8 2-1.1 2-2.8 2c-1.4 0-2.5-.5-3-1.5M12 6v2M12 16v2"/>',
      pen: '<path d="M4 20l4-1L19 8l-3-3L5 16l-1 4z"/><path d="M14 7l3 3"/>',
      mail: '<rect x="3" y="5" width="18" height="14" rx="2"/><path d="M3 7l9 6 9-6"/>',
      text: '<path d="M4 6h16M4 11h16M4 16h9"/>',
      exit: '<path d="M10 4H5v16h5"/><path d="M14 8l4 4-4 4M18 12H9"/>',
      check: '<circle cx="12" cy="12" r="9"/><path d="M8.5 12l2.5 2.5 4.5-5"/>',
      cols: '<rect x="3" y="4" width="18" height="16" rx="2"/><path d="M12 4v16M6 9h3M6 13h3M15 9h3M15 13h3"/>',
      chat: '<path d="M4 5h16v11H9l-5 4z"/>',
      trend: '<path d="M3 17l6-6 4 4 8-8"/><path d="M15 7h6v6"/>',
      compass: '<circle cx="12" cy="12" r="9"/><path d="M15.5 8.5l-2 5-5 2 2-5z"/>',
      map: '<path d="M3 6l6-3 6 3 6-3v15l-6 3-6-3-6 3z"/><path d="M9 3v15M15 6v15"/>',
      plane: '<path d="M22 2L11 13"/><path d="M22 2l-7 20-4-9-9-4z"/>',
      book: '<path d="M5 4h11a3 3 0 0 1 3 3v13H8a3 3 0 0 1-3-3z"/><path d="M5 17a3 3 0 0 1 3-3h11"/>',
      spark: '<circle cx="12" cy="12" r="2.5"/><path d="M12 3v4M12 17v4M3 12h4M17 12h4M6 6l2.5 2.5M15.5 15.5L18 18M18 6l-2.5 2.5M8.5 15.5L6 18"/>',
      tool: '<path d="M14.7 6.3a4 4 0 0 0-5.4 5.4L3 18l3 3 6.3-6.3a4 4 0 0 0 5.4-5.4l-2.6 2.6-2.4-.6-.6-2.4z"/>',
      key: '<circle cx="8" cy="15" r="4"/><path d="M11 12l9-9M17 6l3 3"/>',
      plus: '<rect x="3" y="3" width="18" height="18" rx="3"/><path d="M12 8v8M8 12h8"/>',
      tag: '<path d="M3 12V4h8l10 10-8 8z"/><circle cx="7.5" cy="8.5" r="1.5"/>',
      users: '<circle cx="9" cy="8" r="3.5"/><path d="M2.5 20a6.5 6.5 0 0 1 13 0M16 4.6a3.5 3.5 0 0 1 0 6.8M18 14.5a6.5 6.5 0 0 1 3.5 5.5"/>',
      win: '<rect x="3" y="4" width="18" height="16" rx="2"/><path d="M3 9h18M7 6.5h.01M10 6.5h.01"/>'
    };
    // hub path: [card, columns]. A column is a list of groups [heading, links]; a link is [path, name, icon, one short line or nothing].
    // The card is the search box (jobs) or the menu's main action, which is also a link in a group for the phone menu.
    var M = {
      '/jobs/': [{ search: 1 }, [
        [['Search', [['/jobs/', 'All jobs', 'search', 'Every job, checked every hour'], ['/new/', 'New jobs', 'clock', 'Posted in the last 3 days'],
          ['/jobs-near-me/', 'Jobs near me', 'pin', 'Open jobs in your city'], ['/remote/', 'Remote jobs', 'home', 'Work from home, by country']]],
         ['For you', [['/for-you/', 'Jobs that fit you', 'target', 'Five questions, your matches'], ['/my-jobs/', 'My jobs', 'mark', 'Saved jobs and applications']]]],
        [['Schedule and type', [['/jobs/?etype=Full-time', 'Full-time', 'bag'], ['/part-time/', 'Part-time', 'half'], ['/hybrid/', 'Hybrid', 'swap'],
          ['/work-from-anywhere/', 'Work from anywhere', 'globe'], ['/contract/', 'Contract', 'doc'], ['/temporary/', 'Temporary, seasonal', 'cal'],
          ['/night-shift/', 'Night shift', 'moon'], ['/weekend/', 'Weekend', 'sun']]]],
        [['Experience', [['/internships/', 'Internships', 'cap'], ['/entry-level/', 'Entry-level', 'sprout'], ['/no-experience-jobs/', 'No experience', 'steps']]],
         ['By field', [['/tech/', 'Tech jobs', 'code'], ['/government-jobs/', 'Government jobs', 'gov'], ['/categories/', 'All categories', 'grid'], ['/salaries/', 'Salaries by title', 'coin']]]]]],
      '/resume/': [{ h: '/resume/', t: 'Resume builder', p: 'A one-page resume in your browser, no account.', a: 'Start a resume' }, [
        [['Write', [['/resume/', 'Resume builder', 'pen', 'A one-page resume, no account'], ['/resume/examples/', 'Resume examples', 'doc', 'A written example for each kind of work'],
          ['/cover-letter-examples/', 'Cover letter examples', 'mail', 'A letter for each kind of work, ready to copy'],
          ['/resignation-letters/', 'Resignation letters', 'exit', 'From two weeks notice to effective immediately'],
          ['/resume-words/', 'Resume words', 'text', 'What to write instead of “managed”']]]],
        [['Check', [['/tools/resume-review/', 'Resume review', 'check', 'A score out of 10 and what to fix first'],
          ['/tools/resume-match/', 'Resume match', 'cols', 'Your resume against a posting, word by word']]]]]],
      '/tools/': [{ h: '/tools/', t: 'Free tools', p: 'Offer check, raise calculator, letters and more. They run in your browser.', a: 'See all tools' }, [
        [['Prepare', [['/tools/', 'All free tools', 'tool', 'Offer check, raise calculator and more'], ['/interview-questions/', 'Interview questions', 'chat', 'What to prepare for each job'],
          ['/career-quiz/', 'Career quiz', 'compass', 'Seven plain questions, the fields that fit'], ['/how-to-become/', 'How to become…', 'trend', 'Skills, pay and first jobs, career by career'],
          ['/ahead/', 'Helpers in your browser', 'spark', 'Skill GPS, interview practice out loud']]]],
        [['Learn', [['/guides/', 'Guides', 'book', 'The job market with today’s numbers'], ['/relocate/', 'Relocation guides', 'plane', 'Jobs abroad with visa or relocation help'],
          ['/map/', 'Jobs map', 'map', 'Every city with open jobs on one map'], ['/glossary/', 'Glossary', 'text', 'Hiring words in plain English']]]]]],
      '/post-a-job/': [{ h: '/post-a-job/', t: 'Post a job', p: 'Free, with paid options to stand out.', a: 'Start posting' }, [
        [['Hire', [['/post-a-job/', 'Post a job', 'plus', 'Free, with paid options to stand out'], ['/account/?as=employer', 'Employer sign in', 'key', 'Your jobs, views, clicks and billing'],
          ['/pricing/#employers', 'Pricing for employers', 'tag', 'Every plan and what it includes']]]],
        [['Resources', [['/how-to-hire/', 'How to hire…', 'users', 'Who else hires each role, and the pay'], ['/job-descriptions/', 'Job description templates', 'doc', 'A template per role, with today’s figures'],
          ['/widgets/', 'Jobs for your website', 'win', 'A widget with your jobs or any list'], ['/api/', 'Data for developers', 'code', 'Every open job as free JSON']]]]]]
    };
    var here = location.pathname.slice(P.length) || '/';
    var svg = function (k) { return '<svg viewBox="0 0 24 24" aria-hidden="true">' + I[k] + '</svg>'; };
    var cardHtml = function (c) {
      if (c.search) {
        var n = +nav.getAttribute('data-n') || 0;
        return '<div class="np-card"><p class="np-k"><i></i>Checked every hour</p>' +
          // the count with commas by hand: toLocaleString here was the page's first use of the browser's number formatting, which loads
          // its locale data (about 60 ms of a phone's main thread at 4x slowdown, inside the script's first run; 26 Nov 2026)
          (n ? '<p class="np-n"><b>' + String(Math.round(n)).replace(/\B(?=(\d{3})+(?!\d))/g, ',') + '</b> open jobs</p>' : '<p class="np-n"><b>Every open job</b></p>') +
          '<form class="np-f" action="' + P + '/jobs/" method="get" role="search">' +
          '<input type="search" name="q" placeholder="Job title or skill" aria-label="What: job title, skill or company" autocomplete="off">' +
          '<input type="search" name="where" placeholder="City or remote" aria-label="Where: city, country or remote" autocomplete="off">' +
          '<button class="btn" type="submit">Search jobs</button></form></div>';
      }
      return '<div class="np-card"><p class="np-t">' + esc(c.t) + '</p><p class="np-p">' + esc(c.p) + '</p><a class="btn sm" href="' + P + c.h + '">' + esc(c.a) + '</a></div>';
    };
    var panel = function (m, id) {
      var p = document.createElement('div');
      p.className = 'np'; p.id = id; p.hidden = true;
      p.innerHTML = '<div class="np-in">' + cardHtml(m[0]) + '<div class="np-cols' + (m[1].length > 2 ? ' np-c3' : '') + '">' + m[1].map(function (col, ci) {
        return '<div class="np-col">' + col.map(function (g, gi) {
          var gid = id + '-' + ci + gi;
          return '<div class="np-g"><p class="np-h" id="' + gid + '">' + esc(g[0]) + '</p><ul aria-labelledby="' + gid + '">' + g[1].map(function (x) {
            return '<li' + (x[0] === m[0].h ? ' class="np-m"' : '') + '><a href="' + P + x[0] + '"' + (x[3] ? ' class="np-d"' : '') + (x[0] === here ? ' aria-current="page"' : '') + '>' +
              '<span class="np-i">' + svg(x[2]) + '</span><span class="np-x"><b>' + esc(x[1]) + '</b>' + (x[3] ? '<small>' + esc(x[3]) + '</small>' : '') + '</span></a></li>';
          }).join('') + '</ul></div>';
        }).join('') + '</div>';
      }).join('') + '</div></div>';
      return p;
    };
    var wideQ = window.matchMedia('(min-width: 1041px)'), cur = null, via = '', timer = 0, all = [];      // style.css: the drawer up to 1,040 px
    var later = function (f, ms) { clearTimeout(timer); timer = setTimeout(f, ms); };
    var close = function () {
      clearTimeout(timer);
      if (!cur) return;
      cur.b.setAttribute('aria-expanded', 'false'); cur.a.classList.remove('on'); cur.p.hidden = true; nav.classList.remove('np-on');
      cur = null; via = '';
    };
    var open = function (t, how) {
      clearTimeout(timer);
      if (cur === t) { if (how !== 'hover') via = how; return; }
      t.p.classList.toggle('np-sw', !!cur);        // from one open menu to the next: no fade, so the page never shows between them
      close();
      cur = t; via = how;
      t.p.hidden = false; t.b.setAttribute('aria-expanded', 'true'); t.a.classList.add('on'); nav.classList.add('np-on');
    };
    var links = function (t) { return Array.prototype.filter.call(t.p.querySelectorAll('a'), function (x) { return x.offsetParent !== null; }); };
    var mouse = function (ev) { return ev.pointerType === 'mouse' && wideQ.matches; };
    Array.prototype.forEach.call(nav.querySelectorAll('a.nl'), function (a) {
      var key = (a.getAttribute('href') || '').slice(P.length), m = M[key];
      if (!m || a.classList.contains('only-m')) return;
      var name = a.textContent.trim(), t = { a: a, p: panel(m, 'np-' + key.replace(/\W/g, '')), m: m }, b = t.b = document.createElement('button');
      b.type = 'button'; b.className = 'nlb'; b.setAttribute('aria-expanded', 'false'); b.setAttribute('aria-controls', t.p.id); b.setAttribute('aria-label', name + ' menu');
      b.innerHTML = '<span class="nlb-t">' + esc(name) + '</span>';
      a.classList.add('hasmenu');
      a.parentNode.insertBefore(b, a.nextSibling);
      b.parentNode.insertBefore(t.p, b.nextSibling);
      all.push(t);
      var enter = function (ev) { if (mouse(ev)) later(function () { open(t, 'hover'); }, cur ? 0 : 120); };
      var leave = function (ev) { if (mouse(ev) && (via === 'hover' || !cur)) later(close, 260); };
      [a, b].forEach(function (el) {
        el.addEventListener('pointerenter', enter);
        el.addEventListener('pointerleave', leave);
        el.addEventListener('keydown', function (ev) {
          if (ev.key !== 'ArrowDown') return;
          ev.preventDefault(); open(t, 'key');
          var l = links(t); if (l[0]) l[0].focus();
        });
      });
      t.p.addEventListener('pointerenter', function (ev) { if (mouse(ev)) clearTimeout(timer); });
      t.p.addEventListener('pointerleave', function (ev) { if (mouse(ev) && via === 'hover') later(close, 260); });
      t.p.addEventListener('focusin', function () { if (cur === t && via === 'hover') via = 'focus'; });      // typing in its search box: the panel stays when the mouse wanders off
      b.addEventListener('click', function () { if (cur === t && via !== 'hover') close(); else open(t, 'click'); });
      t.p.addEventListener('keydown', function (ev) {         // arrows move between the links of the open panel
        if ((ev.key !== 'ArrowDown' && ev.key !== 'ArrowUp') || ev.target.tagName !== 'A') return;
        var l = links(t), i = l.indexOf(ev.target);
        if (i < 0) return;
        ev.preventDefault();
        if (ev.key === 'ArrowUp' && i === 0) b.focus(); else if (l[i + (ev.key === 'ArrowDown' ? 1 : -1)]) l[i + (ev.key === 'ArrowDown' ? 1 : -1)].focus();
      });
      var inside = function (el) { return el && (el === a || el === b || t.p.contains(el)); };
      [a, b, t.p].forEach(function (el) {
        el.addEventListener('focusout', function (ev) {        // the focus left the menu (Tab past its last link): a wide panel closes
          if (cur !== t || !wideQ.matches || inside(ev.relatedTarget)) return;
          setTimeout(function () { if (cur === t && !inside(document.activeElement) && !t.p.matches(':hover') && !a.matches(':hover') && !b.matches(':hover')) close(); }, 0);
        });
      });
    });
    document.addEventListener('keydown', function (ev) {
      if (ev.key !== 'Escape') return;
      if (cur) { var t = cur; close(); t.b.focus(); return; }
      if (menuBtn && header.classList.contains('open')) { header.classList.remove('open'); menuBtn.setAttribute('aria-expanded', 'false'); menuBtn.focus(); }
    });
    document.addEventListener('click', function (ev) { if (cur && wideQ.matches && !nav.contains(ev.target)) close(); });
    if (menuBtn) menuBtn.addEventListener('click', function () { if (!header.classList.contains('open')) close(); });
    if (wideQ.addEventListener) wideQ.addEventListener('change', close);
    // the section of this page: the top link or panel link with the longest match (a top link wins a tie; ? and # links are not places)
    var best = null, len = 1;
    Array.prototype.forEach.call(nav.querySelectorAll('a.nl:not(.only-m)'), function (a) {
      var h = (a.getAttribute('href') || '').slice(P.length);
      if (h.length > len && here.indexOf(h) === 0) { best = a; len = h.length; }
    });
    all.forEach(function (t) {
      t.m[1].forEach(function (col) { col.forEach(function (g) { g[1].forEach(function (x) {
        if (!/[?#]/.test(x[0]) && x[0].length > len && here.indexOf(x[0]) === 0) { best = t.a; len = x[0].length; }
      }); }); });
    });
    if (best) best.setAttribute('aria-current', best.getAttribute('href') === location.pathname ? 'page' : 'true');
  })();
  document.addEventListener('keydown', function (ev) {
    if (ev.key === '/' && !/input|textarea|select/i.test((ev.target && ev.target.tagName) || '')) {
      var box = $('q') || document.querySelector('.searchbar input');
      if (box) { ev.preventDefault(); box.focus(); }
    }
  });

  /* ---------- home window: the tabs swap the list in place (each tab is also a plain link to its full list) ---------- */
  (function () {
    var tabs = $('shot-tabs'), box = $('shot-panels'), more = $('shot-more');
    if (!tabs || !box) return;
    // A visitor who answered For you gets a first tab of the newest jobs that fit the answers, open at once, as LinkedIn's jobs home
    // opens on "jobs based on your preferences" (checked 20 Nov 2026). Counted here from the jobs index; nothing is sent anywhere.
    // Without answers, the jobs saved here say it instead (LinkedIn picks jobs "based on your profile, preferences and activity such
    // as applies, searches and saves"): the kinds of work most saved, home or office as most of them, the newest jobs not saved yet.
    // The jobs are asked of the server (the list of every job, 22 MB, was downloaded for this until 25 Nov 2026)
    var fq = fitQuery(get('hrn_profile', null)), mine = get('hrn_jobs', {}), saved = Object.keys(mine), how = 'fit your answers', href = P + '/for-you/';
    (fq ? Promise.resolve(fq) : saved.length >= 2 ? rowsOf(saved).then(function (kept) {
      if (kept.length < 2) return null;
      var cats = {}; kept.forEach(function (j) { cats[j[5]] = (cats[j[5]] || 0) + 1; });
      var top = Object.keys(cats).sort(function (x, y) { return cats[y] - cats[x]; }).filter(function (c) { return cats[c] >= 2 || kept.length < 4; }).slice(0, 2);
      var rem = kept.filter(function (j) { return j[4]; }).length * 2 > kept.length;
      if (!top.length) return null;
      how = 'are like the jobs you saved'; href = P + '/jobs/?cat=' + encodeURIComponent(top[0]) + (rem ? '&remote=1' : '');
      return 'np=1&cat=' + encodeURIComponent(top.slice().sort().join(',')) + (rem ? '&remote=1' : '');
    }) : Promise.resolve(null)).then(function (qs) { return qs ? listOf(qs) : null; }).then(function (got) {
      if (!got) return;
      var fit = got.rows.filter(function (j) { return !mine[j[0]]; }).sort(function (a, b) { return (b[16] || 0) - (a[16] || 0); });
      if (fit.length < 3 || tabs.querySelector('[data-tab="fy"]')) return;
      var t = document.createElement('a'); t.href = href; t.setAttribute('data-tab', 'fy'); t.textContent = 'For you';
      t.setAttribute('data-more', 'See all ' + got.total.toLocaleString('en-US') + ' that ' + how);
      var ul = document.createElement('ul'); ul.className = 'jobs'; ul.setAttribute('data-panel', 'fy');
      ul.innerHTML = fit.slice(0, Math.max(5, (box.querySelector('[data-panel="0"]') || { children: [] }).children.length)).map(card).join('');
      var first = tabs.querySelector('a[data-tab]');
      tabs.insertBefore(t, first); box.insertBefore(ul, box.firstChild);
      if (window.HRN.decorate) window.HRN.decorate(ul);
      t.click();
    }).catch(function () {});
    tabs.addEventListener('click', function (ev) {
      var a = ev.target.closest ? ev.target.closest('a[data-tab]') : null;
      if (!a || ev.metaKey || ev.ctrlKey || ev.shiftKey) return;
      ev.preventDefault();
      var i = a.getAttribute('data-tab');
      [].forEach.call(tabs.querySelectorAll('a[data-tab]'), function (t) { t.classList.toggle('on', t === a); });
      [].forEach.call(box.querySelectorAll('[data-panel]'), function (u) { u.hidden = u.getAttribute('data-panel') !== i; });
      if (more) {
        if (!more.getAttribute('data-all')) more.setAttribute('data-all', more.textContent);
        more.href = a.href;
        more.textContent = i === '0' ? more.getAttribute('data-all') : a.getAttribute('data-more');
      }
    });
  })();

  /* ---------- voice search: say it instead of typing it (browsers with speech recognition) ---------- */
  var SR = window.SpeechRecognition || window.webkitSpeechRecognition;
  if (SR) Array.prototype.forEach.call(document.querySelectorAll('.searchbar'), function (bar) {
    var input = bar.querySelector('input[type=search]'); if (!input) return;
    var mic = document.createElement('button'); mic.type = 'button'; mic.className = 'mic'; mic.setAttribute('aria-label', 'Say what you are looking for');
    input.parentNode.insertBefore(mic, input.nextSibling);
    mic.addEventListener('click', function () {
      var rec = new SR(); rec.lang = 'en-US'; rec.interimResults = false; rec.maxAlternatives = 1;
      mic.classList.add('on');
      rec.onresult = function (ev) {
        input.value = ev.results[0][0].transcript.replace(/[.?!]$/, '');
        input.dispatchEvent(new Event('input', { bubbles: true }));
        var form = input.form; if (form && form.getAttribute('action')) form.submit(); else if (form) form.dispatchEvent(new Event('submit', { cancelable: true, bubbles: true }));
      };
      rec.onend = rec.onerror = function () { mic.classList.remove('on'); };
      try { rec.start(); } catch (e) { mic.classList.remove('on'); }
    });
  });

  /* ---------- follow a company ---------- */
  var followBtn = $('follow');
  if (followBtn) {
    var follows = get('hrn_follow', {}), fs = followBtn.getAttribute('data-slug'), fname = followBtn.getAttribute('data-name');
    var paintFollow = function () { followBtn.textContent = follows[fs] ? 'Following ✓' : 'Follow ' + fname; followBtn.setAttribute('aria-pressed', follows[fs] ? 'true' : 'false'); };
    if (follows[fs]) { follows[fs].seen = today(); set('hrn_follow', follows); }      // visiting the page counts as "seen"
    paintFollow();
    followBtn.addEventListener('click', function () {
      if (follows[fs]) delete follows[fs]; else follows[fs] = { name: fname, seen: today() };
      set('hrn_follow', follows); paintFollow();
    });
  }

  /* ---------- quick search: Ctrl/Cmd+K or the search icon ---------- */
  var pal;
  function palette() {
    if (!pal) {
      pal = document.createElement('div'); pal.className = 'pal'; pal.hidden = true;
      var recent = get('hrn_searches', []).slice(0, 4).map(function (x) { return '<a href="' + P + '/jobs/?' + esc(x.qs) + '">' + esc(x.label) + '<span>saved search</span></a>'; }).join('');
      pal.innerHTML = '<div class="pal-box" role="dialog" aria-label="Quick search"><form action="' + P + '/jobs/" method="get"><input type="search" name="q" placeholder="Search jobs, skills, companies…" aria-label="Search" autocomplete="off"></form>' +
        '<div class="pal-links">' + recent +
        '<a href="' + P + '/remote/">Remote jobs<span>list</span></a><a href="' + P + '/new/">New in the last 3 days<span>list</span></a><a href="' + P + '/for-you/">Jobs for you<span>match</span></a>' +
        '<a href="' + P + '/salaries/">Salaries<span>data</span></a><a href="' + P + '/tools/">Free tools<span>calculators</span></a><a href="' + P + '/companies/">Companies<span>directory</span></a><a href="' + P + '/my-jobs/">My jobs<span>tracker</span></a></div>' +
        '<p class="pal-hint">Enter to search · Esc to close</p></div>';
      document.body.appendChild(pal);
      pal.addEventListener('click', function (ev) { if (ev.target === pal) pal.hidden = true; });
    }
    pal.hidden = !pal.hidden;
    if (!pal.hidden) pal.querySelector('input').focus();
  }
  document.addEventListener('keydown', function (ev) {
    if ((ev.metaKey || ev.ctrlKey) && ev.key.toLowerCase() === 'k') { ev.preventDefault(); palette(); }
    else if (ev.key === 'Escape' && pal && !pal.hidden) pal.hidden = true;
  });
  var palBtn = $('palbtn'); if (palBtn) palBtn.addEventListener('click', palette);

  /* ---------- categories page: type a few letters, keep the kinds of work that contain them ---------- */
  var dirfilter = $('dirfilter');
  if (dirfilter) dirfilter.addEventListener('input', function () {
    var q = dirfilter.value.trim().toLowerCase(), shown = 0;
    document.querySelectorAll('#dir .dirb').forEach(function (b) {
      var any = 0, head = (b.querySelector('h2,h3') || b).textContent.toLowerCase(), whole = !q || head.indexOf(q) >= 0;
      b.querySelectorAll('li').forEach(function (li) {
        var n = li.getAttribute('data-n'), hit = whole || (n != null && n.indexOf(q) >= 0);
        li.hidden = !hit; if (hit) any++;
      });
      b.hidden = !any; if (any) shown++;
    });
    document.querySelectorAll('dl#dir > div').forEach(function (row) {      // the glossary index: one row per term
      var hit = !q || row.textContent.toLowerCase().indexOf(q) >= 0;
      row.hidden = !hit; if (hit) shown++;
    });
    document.querySelectorAll('#rolelist > li').forEach(function (li) {    // the A-to-Z list of roles: one tile per role
      var hit = !q || (li.getAttribute('data-n') || '').indexOf(q) >= 0;
      li.hidden = !hit; if (hit) shown++;
    });
    document.querySelectorAll('table.dirt tr[data-n]').forEach(function (tr) {    // a table with a row per name (salaries by job title)
      var hit = !q || tr.getAttribute('data-n').indexOf(q) >= 0;
      tr.hidden = !hit; if (hit) shown++;
    });
    document.querySelectorAll('[data-dirg]').forEach(function (g) {      // groups of named items (skills, tools, resume words): a group left empty steps aside
      var any = 0;
      g.querySelectorAll('[data-n]').forEach(function (el) {
        var hit = !q || el.getAttribute('data-n').indexOf(q) >= 0;
        el.hidden = !hit; if (hit) any++;
      });
      g.hidden = !!q && !any; if (any) shown++;
    });
    var none = $('dirnone'); if (none) none.hidden = shown > 0;
  });

  /* ---------- help page: type a word, keep the answers that contain it ---------- */
  var helpfilter = $('helpfilter');
  if (helpfilter) helpfilter.addEventListener('input', function () {
    var q = helpfilter.value.trim().toLowerCase(), shown = 0;
    document.querySelectorAll('#help .helpb').forEach(function (b) {
      var any = 0;
      b.querySelectorAll('dl > div').forEach(function (d) { var hit = !q || (d.getAttribute('data-n') || '').indexOf(q) >= 0; d.hidden = !hit; if (hit) any++; });
      b.hidden = !any; if (any) shown++;
    });
    var none = $('helpnone'); if (none) none.hidden = shown > 0;
  });

  /* ---------- compare two companies: bars from data/compare.json ---------- */
  var vsOut = $('vs-out'), vsA = $('vs-a'), vsB = $('vs-b');
  if (vsOut && vsA && vsB) {
    var qp = new URLSearchParams(location.search);
    vsA.value = qp.get('a') || vsOut.getAttribute('data-a'); vsB.value = qp.get('b') || vsOut.getAttribute('data-b');
    fetch(P + '/data/compare.json').then(function (r) { return r.json(); }).then(function (D) {
      var nf = function (x) { return Number(x).toLocaleString('en-US'); }, pc = function (a, b) { return Math.round(100 * a / Math.max(1, b)); };
      var money = function (v) { return v ? '$' + Math.round(v / 1000) + 'K' : 'too few postings'; };
      var draw = function () {
        var a = D[vsA.value], b = D[vsB.value]; if (!a || !b) return;
        var rows = [['Open jobs', a[1], b[1], nf(a[1]), nf(b[1])], ['Can be done from home', pc(a[2], a[1]), pc(b[2], b[1]), pc(a[2], a[1]) + '%', pc(b[2], b[1]) + '%'],
          ['State the pay', pc(a[3], a[1]), pc(b[3], b[1]), pc(a[3], a[1]) + '%', pc(b[3], b[1]) + '%'], ['Median advertised pay', a[4], b[4], money(a[4]), money(b[4])],
          ['Posted in the last 7 days', a[5], b[5], nf(a[5]), nf(b[5])], ['For beginners', a[6], b[6], nf(a[6]), nf(b[6])],
          ['Open ' + vsOut.getAttribute('data-long') + ' days or more', pc(a[7], a[1]), pc(b[7], b[1]), pc(a[7], a[1]) + '%', pc(b[7], b[1]) + '%']];
        var side = function (x, slug) { return '<div><p class="flabel">' + esc(x[0]) + ' hires most in</p><p>' + esc(x[8].join(', ')) + '</p>' + (x[9].length ? '<p class="flabel">Skills it asks for most</p><p>' + esc(x[9].join(', ')) + '</p>' : '') +
          '<p><a class="btn sm" href="' + P + '/companies/' + slug + '/">See ' + esc(x[0]) + ' jobs</a></p></div>'; };
        vsOut.innerHTML = '<div class="vsh"><a href="' + P + '/companies/' + vsA.value + '/"><b>' + esc(a[0]) + '</b></a><span>vs</span><a href="' + P + '/companies/' + vsB.value + '/"><b>' + esc(b[0]) + '</b></a></div><div class="vs">' +
          rows.map(function (r) { var mx = Math.max(r[1], r[2], 1); return '<div class="vsr"><span class="vl">' + r[0] + '</span><span class="va"><b>' + r[3] + '</b><i style="width:' + Math.round(100 * r[1] / mx) + '%"></i></span><span class="vb"><i style="width:' + Math.round(100 * r[2] / mx) + '%"></i><b>' + r[4] + '</b></span></div>'; }).join('') +
          '</div><div class="vsside">' + side(a, vsA.value) + side(b, vsB.value) + '</div>';
        try { history.replaceState(null, '', '?a=' + encodeURIComponent(vsA.value) + '&b=' + encodeURIComponent(vsB.value)); } catch (e) {}
      };
      vsA.addEventListener('change', draw); vsB.addEventListener('change', draw);
      if (qp.get('a') || qp.get('b')) draw();
    }).catch(function () {});
  }

  /* ---------- feeds page: pick a feed, copy its address ---------- */
  var feedpick = $('feedpick'), feedurl = $('feedurl'), feedcopy = $('feedcopy');
  if (feedpick && feedurl) {
    feedpick.addEventListener('change', function () { feedurl.value = feedpick.value; });
    feedurl.addEventListener('focus', function () { feedurl.select(); });
    if (feedcopy) feedcopy.addEventListener('click', function () {
      var done = function () { feedcopy.textContent = 'Copied'; setTimeout(function () { feedcopy.textContent = 'Copy the address'; }, 1600); };
      if (navigator.clipboard) navigator.clipboard.writeText(feedurl.value).then(done, function () { feedurl.select(); }); else { feedurl.select(); done(); }
    });
  }

  /* ---------- companies page: quick filter ---------- */
  var cfilter = $('cfilter'), cfield = $('cfield'), clist = $('clist'), cmore = $('cmore'), cmorebtn = $('cmorebtn');
  /* The page carries the employers with the most open roles; the rest are data/company-directory.json, added to the list the first time
     a visitor types, picks a field, sorts or presses the button. rows: [name, slug, open roles, posted in 7 days, field, has a logo, ([H-1B filings, fiscal year] when it files H-1B)]. */
  var cstate = cmore ? 'idle' : 'done', cwaiting = [];
  var cload = function (then) {
    if (cstate === 'done') { if (then) then(); return; }
    if (then) cwaiting.push(then);
    if (cstate === 'busy') return;
    cstate = 'busy';
    if (cmorebtn) { cmorebtn.disabled = true; cmorebtn.textContent = 'Loading the other employers…'; }
    fetch(P + '/data/company-directory.json').then(function (r) { if (!r.ok) throw 0; return r.json(); }).then(function (rows) {
      var frag = document.createDocumentFragment();
      rows.forEach(function (r) {
        var li = document.createElement('li'), a = document.createElement('a'), av = document.createElement('span'), nm = document.createElement('span'), c = document.createElement('span');
        li.setAttribute('data-n', r[0].toLowerCase()); li.setAttribute('data-o', r[2]); li.setAttribute('data-w', r[3]); li.setAttribute('data-f', r[4]);
        a.className = 'tile'; a.href = P + '/companies/' + r[1] + '/';
        av.className = 'ava sm' + (r[5] ? ' has' : ''); av.setAttribute('aria-hidden', 'true');
        av.appendChild(document.createTextNode((r[0].match(/[A-Za-z0-9\u00C0-\uFFFF]/) || ['?'])[0].toUpperCase()));
        if (r[5]) { var im = document.createElement('img'); im.src = P + '/logos/s/' + r[1] + '.png'; im.alt = im.title = r[0] + ' logo'; im.width = im.height = 72; im.loading = 'lazy'; av.appendChild(im); }
        nm.className = 'n'; nm.textContent = r[0];
        a.appendChild(av); a.appendChild(nm);
        if (r[6]) { var hb = document.createElement('span'); hb.className = 'h1bt'; hb.title = 'Files H-1B: ' + r[6][0].toLocaleString('en-US') + ' certified H-1B ' + (r[6][0] === 1 ? 'filing' : 'filings') + ' (LCAs) in fiscal year ' + r[6][1]; hb.textContent = 'H-1B'; a.appendChild(hb); li.setAttribute('data-h', '1'); }
        if (r[3]) { var up = document.createElement('span'); up.className = 'up'; up.title = r[3] + ' posted in the last 7 days'; up.textContent = '+' + r[3]; a.appendChild(up); }
        c.className = 'c'; c.textContent = r[2].toLocaleString('en-US'); a.appendChild(c);
        li.appendChild(a); frag.appendChild(li);
      });
      clist.appendChild(frag);
      cstate = 'done'; if (cmore) cmore.hidden = true;
      var q = cwaiting; cwaiting = []; q.forEach(function (f) { f(); });
    }).catch(function () {
      cstate = 'idle'; cwaiting = [];
      if (cmorebtn) { cmorebtn.disabled = false; cmorebtn.textContent = 'Could not load the other employers. Try again'; }
    });
  };
  if (cmorebtn) { cmorebtn.hidden = false; cmorebtn.addEventListener('click', function () { cload(); }); }
  var ch1b = $('ch1b'), h1bOnly = function () { return !!ch1b && ch1b.getAttribute('aria-pressed') === 'true'; };
  var cfiltered = function () {                       // by name, by the field a company hires for most, and "Files H-1B" (data-h)
    var q = cfilter.value.trim().toLowerCase(), f = cfield ? cfield.value : '', h = h1bOnly(), shown = 0;
    document.querySelectorAll('#clist li').forEach(function (li) {
      var hit = (!q || li.getAttribute('data-n').indexOf(q) >= 0) && (!f || li.getAttribute('data-f') === f) && (!h || li.hasAttribute('data-h'));
      li.hidden = !hit; if (hit) shown++;
    });
    var none = $('cnone'); if (none) none.hidden = shown > 0;
  };
  /* The directory shows its first tiles behind one "Show all N employers" button (the tiles block below); filtering or sorting opens the
     whole list, or a match past the first tiles would stay hidden (26 Nov 2026: two buttons stood in a row under the list). */
  var cuncut = function () {
    if (!clist || !clist.classList.contains('cut')) return;
    clist.classList.remove('cut');
    var nb = clist.nextElementSibling; if (nb && nb.classList.contains('tiles-more')) nb.remove();
    if (cmore && cstate !== 'done') cmore.hidden = false;
  };
  var cfilterNow = function () { cuncut(); cfiltered(); if (cstate !== 'done' && (cfilter.value.trim() || (cfield && cfield.value) || h1bOnly())) cload(cfiltered); };
  if (cfilter) cfilter.addEventListener('input', cfilterNow);
  if (cfilter && cfield) cfield.addEventListener('change', cfilterNow);
  if (cfilter && ch1b) { ch1b.hidden = false; ch1b.addEventListener('click', function () { ch1b.setAttribute('aria-pressed', h1bOnly() ? 'false' : 'true'); cfilterNow(); }); }
  /* companies page: sort by open roles, roles posted in the last 7 days, or name (buttons are hidden until this script runs) */
  var csort = $('csort');
  if (csort && clist) {
    csort.hidden = false;
    csort.addEventListener('click', function (ev) {
      var b = ev.target.closest('button'); if (!b) return;
      var k = b.getAttribute('data-s');
      csort.querySelectorAll('button').forEach(function (x) { x.setAttribute('aria-pressed', x === b ? 'true' : 'false'); });
      cuncut();
      cload(function () {
        if (csort.querySelector('[aria-pressed="true"]') !== b) return;      // another button was pressed while the list loaded
        var items = Array.prototype.slice.call(clist.children);
        items.sort(function (a, z) {
          if (k === 'n') return a.getAttribute('data-n').localeCompare(z.getAttribute('data-n'));
          return (+z.getAttribute('data-' + k) - +a.getAttribute('data-' + k)) || (+z.getAttribute('data-o') - +a.getAttribute('data-o'));
        });
        var frag = document.createDocumentFragment(); items.forEach(function (li) { frag.appendChild(li); }); clist.appendChild(frag);
      });
    });
  }

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

  /* job page controls; also used for the preview pane on the search page */
  /* ---------- near you: the country comes from the browser's time zone; nothing is asked and nothing is sent ---------- */
  function near() {
    var box = document.getElementById('near'); if (!box) return;
    fetch(P + '/data/geo.json').then(function (r) { return r.json(); }).then(function (G) {
      var tz = ''; try { tz = Intl.DateTimeFormat().resolvedOptions().timeZone || ''; } catch (e) {}
      var n = function (x) { return Number(x).toLocaleString('en-US'); };
      var draw = function () {
        var code = get('hrn_place', '') || G.tz[tz] || '', c = G.c[code], bits = [], label;
        if (c) {
          label = c[0];
          if (c[2] && c[1]) bits.push('<a href="' + P + '/locations/' + c[1] + '/">' + n(c[2]) + (c[2] === 1 ? ' job' : ' jobs') + ' in ' + flag(code) + esc(c[0]) + '</a>');
          if (c[3] && c[1]) bits.push('<a href="' + P + '/jobs/?remote&loc=' + c[1] + '">' + n(c[3]) + ' remote ' + (c[3] === 1 ? 'role names' : 'roles name') + ' it</a>');
          var reg = G.r[c[4]];
          if (reg && !(c[2] && c[1])) bits.push('<a href="' + P + '/locations/' + c[4] + '/">' + n(reg[1]) + ' jobs in ' + esc(reg[0]) + '</a>');
        } else {
          var key = /^Europe\//.test(tz) ? 'europe' : /^(Asia|Australia|Pacific|Indian)\//.test(tz) ? 'asia-pacific' : /^Africa\//.test(tz) ? 'africa' : /^America\//.test(tz) ? 'latin-america' : '';
          var rg = G.r[key];
          label = rg ? rg[0] : '';
          if (rg) bits.push('<a href="' + P + '/locations/' + key + '/">' + n(rg[1]) + ' jobs in ' + esc(rg[0]) + '</a>');
        }
        bits.push('<a href="' + P + '/jobs/?remote&any">' + n(G.w) + ' remote roles open worldwide</a>');
        var opts = Object.keys(G.c).sort(function (a, b) { return G.c[a][0] < G.c[b][0] ? -1 : 1; }).map(function (k) {
          return '<option value="' + k + '"' + (k === code ? ' selected' : '') + '>' + esc(G.c[k][0]) + '</option>';
        }).join('');
        box.innerHTML = '<span class="near-l">' + (label ? 'Near you, ' + esc(label) + ':' : 'From anywhere:') + '</span> ' + bits.join(' · ') +
          ' <label class="near-pick">Change place<select id="near-sel" aria-label="Your country"><option value="">Choose a country</option>' + opts + '</select></label>';
        box.hidden = false;
      };
      box.addEventListener('change', function (ev) { if (ev.target.id === 'near-sel' && ev.target.value) { set('hrn_place', ev.target.value); draw(); } });
      draw();
    }).catch(function () {});
  }

  function bindJob(root) {
    var q1 = function (sel) { return root.querySelector(sel); };
    var saveBtn = q1('#save'), appliedBtn = q1('#applied');
    if (!saveBtn) return;
    var shareRow = q1('#share');
    // The share row as round icon buttons (the owner, 18 Nov 2026: nine words in three lines "looked untidy, better as icons"); each
    // has its name for screen readers and as a tip. The two "do not show me this" actions stand under them as quiet words.
    var SHARE_ICON = {"copy": "<path d=\"M9 9h10v11H9zM5 15V4h10\" fill=\"none\" stroke=\"currentColor\" stroke-width=\"1.8\" stroke-linejoin=\"round\" stroke-linecap=\"round\"/>", "linkedin": "<path d=\"M4.98 3.5a2.5 2.5 0 1 1 0 5 2.5 2.5 0 0 1 0-5zM3 9.75h4V21H3zM10 9.75h3.8v1.6h.06c.53-1 1.83-1.95 3.76-1.95C21.2 9.4 22 11.6 22 14.6V21h-4v-5.7c0-1.4-.03-3.1-1.9-3.1s-2.2 1.5-2.2 3V21H10z\" fill=\"currentColor\"/>", "x": "<path d=\"M17.5 3h3.2l-7 8 8.2 10h-6.4l-5-6.1L4.8 21H1.6l7.5-8.6L1.2 3h6.6l4.5 5.6zm-1.1 16h1.8L7.7 4.9H5.8z\" fill=\"currentColor\"/>", "telegram": "<path d=\"M21.9 4.3 18.7 19.6c-.2 1-.9 1.3-1.8.8l-5-3.7-2.400 2.300c-.3.3-.5.5-1 .5l.4-5.100 9.300-8.400c.4-.4-.1-.6-.6-.200L6.100 13.300 1.200 11.700c-1.100-.3-1.100-1.100.2-1.600L20.500 2.700c.9-.3 1.700.2 1.400 1.600z\" fill=\"currentColor\"/>", "whatsapp": "<path d=\"M12 2.2a9.800 9.800 0 0 0-8.400 14.900L2.200 21.800l4.900-1.300A9.800 9.800 0 1 0 12 2.200zm0 1.800a8 8 0 1 1-4.100 14.900l-.300-.200-2.900.800.800-2.800-.200-.300A8 8 0 0 1 12 4zm-3.300 3.900c-.200 0-.500.100-.700.400-.300.300-1 .900-1 2.300s1 2.700 1.100 2.900c.200.200 2 3.100 4.900 4.200 2.400 1 2.900.800 3.400.700.500 0 1.700-.700 1.900-1.300.200-.700.200-1.200.200-1.300-.100-.200-.300-.200-.600-.400l-1.900-.900c-.300-.100-.500-.200-.700.100l-.900 1.100c-.200.200-.300.200-.600.100-.300-.200-1.200-.500-2.300-1.400-.800-.800-1.400-1.700-1.600-2-.100-.300 0-.400.100-.600l.500-.500c.100-.200.200-.300.300-.500.100-.200 0-.400 0-.500l-.900-2.100c-.200-.500-.400-.500-.600-.500z\" fill=\"currentColor\"/>", "reddit": "<path d=\"M22 12.100a2.200 2.200 0 0 0-3.700-1.600c-1.500-1-3.400-1.600-5.500-1.700l1-4.400 3.100.700a1.600 1.600 0 1 0 .200-.900l-3.600-.800a.500.500 0 0 0-.600.400l-1.100 5c-2.100.100-4 .700-5.500 1.700A2.200 2.200 0 1 0 3.900 14c0 .300-.100.500-.100.800 0 3.200 3.700 5.800 8.200 5.800s8.200-2.600 8.200-5.800c0-.300 0-.500-.100-.800.900-.400 1.500-1.200 1.500-2.200zM7.500 13.800a1.500 1.500 0 1 1 3 0 1.500 1.500 0 0 1-3 0zm8.200 3.900c-1 .900-2.900 1.100-3.700 1.100s-2.700-.100-3.700-1.100a.400.400 0 0 1 .600-.600c.600.600 2 .800 3.100.800s2.500-.200 3.100-.800a.400.400 0 0 1 .600.600zm-.200-2.400a1.500 1.500 0 1 1 0-3 1.500 1.500 0 0 1 0 3z\" fill=\"currentColor\"/>", "email": "<path d=\"M3 6h18v12H3zM3.500 6.500l8.500 7 8.500-7\" fill=\"none\" stroke=\"currentColor\" stroke-width=\"1.8\" stroke-linejoin=\"round\" stroke-linecap=\"round\"/>"};
    var shareIcon = function (k) { return '<svg viewBox="0 0 24 24" width="18" height="18" aria-hidden="true">' + SHARE_ICON[k] + '</svg>'; };
    if (shareRow && !shareRow.firstChild) shareRow.innerHTML = '<span class="share-l">Share</span><span class="share-i"><button class="shbtn" id="copy" type="button" aria-label="Copy the link" title="Copy the link">' + shareIcon('copy') + '</button>' +
      ['LinkedIn', 'X', 'Telegram', 'WhatsApp', 'Reddit', 'Email'].map(function (n) { return '<button class="shbtn" type="button" data-share="' + n.toLowerCase() + '" aria-label="Share on ' + n + '" title="' + n + '">' + shareIcon(n.toLowerCase()) + '</button>'; }).join('') +
      '</span><span class="share-say" id="copy-say" role="status"></span><span class="share-more"><button class="linkbtn" id="hide" type="button">Not interested</button><button class="linkbtn" id="mute" type="button">Hide this company</button></span>';
    var me = { s: saveBtn.getAttribute('data-slug'), t: saveBtn.getAttribute('data-title'), c: saveBtn.getAttribute('data-company'), l: root.querySelector('.jhead .ava.has') ? 1 : 0 };
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
      if (jobs[me.s]) delete jobs[me.s]; else jobs[me.s] = { t: me.t, c: me.c, l: me.l, st: 'saved', at: Date.now(), note: '' };
      store(); label();
    });
    if (appliedBtn) appliedBtn.addEventListener('click', function () {
      var rec = jobs[me.s];
      if (rec && rec.st !== 'saved') rec.st = 'saved';
      else jobs[me.s] = { t: me.t, c: me.c, l: me.l, st: 'applied', at: Date.now(), note: rec ? rec.note : '' };
      store(); label();
    });
    var applyLink = q1('#apply'), hint = q1('#apply-hint');
    if (applyLink && hint) applyLink.addEventListener('click', function () { hint.hidden = false; });
    var copy = q1('#copy');
    if (copy) copy.addEventListener('click', function () {
      var link = root === document ? location.href : location.origin + P + '/job/' + me.s + '/';
      var say = q1('#copy-say'), done = function () { if (say) say.textContent = 'Link copied'; copy.classList.add('ok'); setTimeout(function () { if (say) say.textContent = ''; copy.classList.remove('ok'); }, 1600); };
      if (navigator.clipboard) navigator.clipboard.writeText(link).then(done, function () {}); else done();
    });
    // share links are built on click, so pages do not carry five long addresses each
    Array.prototype.forEach.call(root.querySelectorAll('[data-share]'), function (btn) {
      btn.addEventListener('click', function () {
        var link = location.origin + P + '/job/' + me.s + '/', text = me.t + ' at ' + me.c, u = encodeURIComponent(link), t = encodeURIComponent(text);
        var to = { linkedin: 'https://www.linkedin.com/sharing/share-offsite/?url=' + u, x: 'https://x.com/intent/post?text=' + t + '&url=' + u,
          telegram: 'https://t.me/share/url?url=' + u + '&text=' + t, whatsapp: 'https://wa.me/?text=' + t + '%20' + u,
          reddit: 'https://www.reddit.com/submit?url=' + u + '&title=' + t, email: 'mailto:?subject=' + t + '&body=' + u }[btn.getAttribute('data-share')];
        if (to) window.open(to, '_blank', 'noopener');
      });
    });
    var markSeen = function () {
      var seen = get('hrn_seen', []).filter(function (x) { return x.s !== me.s; });
      seen.unshift(me); set('hrn_seen', seen.slice(0, 30));
    };
    if (document.prerendering) document.addEventListener('prerenderingchange', markSeen, { once: true }); else markSeen();
    var fit = q1('#match');
    if (fit && knowsSkills) {                        // on your resume / to grow, as soon as the page opens (resumai's job cards)
      var tags = (fit.getAttribute('data-tags') || '').split('|').filter(Boolean);
      var hit = tags.filter(have), miss = tags.filter(function (t) { return !have(t); });
      var slugM = (location.pathname.match(/\/job\/([^/]+)\//) || [])[1];
      if (tags.length) {
        fit.innerHTML = '<b>' + hit.length + ' of ' + tags.length + ' skills this job names are ' + (cvText ? 'on your resume' : 'in your answers') + '.</b> '
          + (hit.length ? '<span class="fit-have">✓ ' + hit.map(esc).join(', ✓ ') + '</span> ' : '')
          + (miss.length ? '<span class="fit-grow">To grow: ' + miss.map(esc).join(', ') + '</span> ' : '')
          + (cvText && slugM ? '<a href="' + P + '/resume/?job=' + slugM + '">Tailor your resume to it</a>' : '');
        fit.className = 'note fitline'; fit.hidden = false;
      }
    }
    var muteBtn = q1('#mute');
    if (muteBtn) {
      var paintMute = function () { muteBtn.textContent = mute.c[me.c] ? me.c + ' is hidden from your lists · undo' : 'Hide this company'; };
      paintMute();
      muteBtn.addEventListener('click', function () { if (mute.c[me.c]) delete mute.c[me.c]; else mute.c[me.c] = 1; set('hrn_mute', mute); paintMute(); });
    }
    var hideBtn = q1('#hide');
    if (hideBtn) {
      var paintHide = function () { hideBtn.textContent = hidden[me.s] ? 'Hidden from your searches · undo' : 'Not interested'; };
      paintHide();
      hideBtn.addEventListener('click', function () { if (hidden[me.s]) delete hidden[me.s]; else hidden[me.s] = 1; set('hrn_hidden', hidden); paintHide(); });
    }
  }
  /* Job page extras. Nothing here needs our server: the live check asks the employer's own hiring system from the visitor's
     browser, the voice is the browser's, the reminder is a calendar file made on the spot. */
  function jobExtras(root) {
    var q1 = function (sel) { return root.querySelector(sel); };
    var ap = q1('#apply'); if (!ap || ap.getAttribute('data-x')) return;
    ap.setAttribute('data-x', '1');
    var href = ap.getAttribute('href') || '', m, api = '', ashby = '';
    if ((m = /(?:job-boards|boards)(?:\.eu)?\.greenhouse\.io\/([^\/?#]+)\/jobs\/(\d+)/.exec(href))) api = 'https://boards-api.greenhouse.io/v1/boards/' + m[1] + '/jobs/' + m[2];
    else if ((m = /jobs(\.eu)?\.lever\.co\/([^\/?#]+)\/([0-9a-f-]{36})/.exec(href))) api = 'https://api' + (m[1] || '') + '.lever.co/v0/postings/' + m[2] + '/' + m[3];
    else if ((m = /jobs\.ashbyhq\.com\/([^\/?#]+)\/([0-9a-f-]{36})/.exec(href))) { api = 'https://api.ashbyhq.com/posting-api/job-board/' + m[1]; ashby = m[2]; }
    var h1 = q1('h1'), title = h1 ? h1.textContent : document.title, saveB = q1('#save'), company = saveB ? saveB.getAttribute('data-company') : '';
    var tagsEl = q1('#match'), tags = tagsEl ? (tagsEl.getAttribute('data-tags') || '').split('|').filter(Boolean) : [];
    var box = document.createElement('div'); box.className = 'jtools';
    box.innerHTML = (api ? '<button type="button" class="linkbtn" data-act="live">Check with the employer right now</button>' : '') +
      (window.speechSynthesis ? '<button type="button" class="linkbtn" data-act="listen">Listen to this posting</button>' : '') +
      '<button type="button" class="linkbtn" data-act="ics">Remind me to follow up in 7 days</button>' +
      (tags.length ? '<button type="button" class="linkbtn" data-act="plain">What these skills mean</button>' : '') + '<p class="jout" aria-live="polite" hidden></p>';
    var after = q1('.jhelp .jcard-h') || q1('#apply-hint') || q1('.note.goes') || ap;      // v4: the tools open the job page's "Before you apply" card
    after.parentNode.insertBefore(box, after.nextSibling);
    var out = box.querySelector('.jout'), say = function (html) { out.innerHTML = html; out.hidden = false; };
    var hhmm = function () { try { return new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' }); } catch (e) { return 'now'; } };
    box.addEventListener('click', function (ev) {
      var b = ev.target.closest('[data-act]'); if (!b) return;
      var act = b.getAttribute('data-act');
      if (act === 'live') {
        say('Asking the employer’s hiring system…');
        fetch(api, { cache: 'no-store' }).then(function (r) {
          if (ashby) return r.json().then(function (d) { return (d.jobs || []).some(function (x) { return x.id === ashby; }); });
          if (r.status === 404) return false;
          if (!r.ok) throw new Error('status');
          return true;
        }).then(function (open) {
          say(open ? '<b class="ok">Still open.</b> The employer’s hiring system confirmed it to your browser at ' + hhmm() + '. We were not asked.'
                   : '<b class="warn">Closed.</b> The employer’s hiring system no longer has this job (checked at ' + hhmm() + '). This page will say so after the next update.');
        }).catch(function () { say('The employer’s system did not answer. The “Apply” button opens its page, where you can see for yourself.'); });
      } else if (act === 'listen') {
        var synth = window.speechSynthesis;
        if (synth.speaking) { synth.cancel(); b.textContent = 'Listen to this posting'; return; }
        var prose = q1('.prose'), text = title + (company ? ', at ' + company : '') + '. ' + (prose ? prose.textContent : '');
        var u = new SpeechSynthesisUtterance(text.slice(0, 5000)); u.lang = 'en-US'; u.rate = 1;
        u.onend = function () { b.textContent = 'Listen to this posting'; };
        b.textContent = 'Stop reading'; synth.speak(u);
      } else if (act === 'ics') {
        var d = new Date(); d.setDate(d.getDate() + 7); d.setHours(9, 0, 0, 0);
        var p2 = function (n) { return (n < 10 ? '0' : '') + n; }, stamp = function (x) { return x.getFullYear() + p2(x.getMonth() + 1) + p2(x.getDate()) + 'T' + p2(x.getHours()) + p2(x.getMinutes()) + '00'; };
        var clean = function (t) { return String(t).replace(/[\\;,]/g, ' ').replace(/\s+/g, ' ').trim(); };
        var ics = ['BEGIN:VCALENDAR', 'VERSION:2.0', 'PRODID:-//Jobs Every Hour//EN', 'BEGIN:VEVENT', 'UID:' + Date.now() + '@hrn', 'DTSTAMP:' + stamp(new Date()), 'DTSTART:' + stamp(d),
          'DURATION:PT15M', 'SUMMARY:' + clean('Follow up: ' + title + (company ? ' at ' + company : '')), 'DESCRIPTION:' + clean('You applied a week ago. If there is no answer, write a short follow-up. ' + location.href),
          'BEGIN:VALARM', 'TRIGGER:PT0M', 'ACTION:DISPLAY', 'DESCRIPTION:Follow up on your application', 'END:VALARM', 'END:VEVENT', 'END:VCALENDAR'].join('\r\n');
        var a = document.createElement('a'); a.href = URL.createObjectURL(new Blob([ics], { type: 'text/calendar' })); a.download = 'follow-up.ics';
        document.body.appendChild(a); a.click(); a.remove();
        say('A calendar file was saved. Open it and your calendar adds a reminder for ' + d.toLocaleDateString('en-US', { weekday: 'long', month: 'short', day: 'numeric' }) + ', 9:00.');
      } else if (act === 'plain') {
        say('Loading…');
        fetch(P + '/data/skillinfo.json').then(function (r) { return r.json(); }).then(function (info) {
          var rows = tags.map(function (t) { return info[t] ? '<div><dt>' + esc(t) + '</dt><dd>' + esc(info[t]) + '</dd></div>' : ''; }).join('');
          say(rows ? '<dl class="qa one">' + rows + '</dl>' : 'No plain description for these skills yet.');
        }).catch(function () { say('Could not load the descriptions.'); });
      }
    });
  }
  HRN.jobExtras = jobExtras;
  var bindJob0 = bindJob;
  bindJob = function (root) { bindJob0(root); jobExtras(root); };
  HRN.bindJob = bindJob;
  bindJob(document);
  near();

  /* ---------- "jobs near me": the list for the visitor's place. Country from the time zone; nearest city only if the visitor allows location (worked out here, sent nowhere) ---------- */
  function nearMe() {
    var box = document.getElementById('nearme'); if (!box) return;
    var et = box.getAttribute('data-etype') || '', head = document.getElementById('nearme-h'), list = document.getElementById('nearme-list'), more = document.getElementById('nearme-more');
    var btn = document.getElementById('nearme-geo'), note = document.getElementById('nearme-note');
    var num = function (x) { return Number(x).toLocaleString('en-US'); };
    function tileOf(slug) { return document.querySelector('[data-place="' + slug + '"]'); }
    function show(slug, name, how, wider) {
      // the place's jobs and their summary from the server (the list of every job, 22 MB, was downloaded for this until 25 Nov 2026)
      listOf('loc=' + encodeURIComponent(slug) + (et ? '&etype=' + encodeURIComponent(et) : '') + '&np=1&sum=1').then(function (got) {
        var n = got.total, rows = got.rows;
        if (!n && wider) return wider();            // nothing in the country today: the part of the world it is in
        var codes = rows.length ? rows[0][24].slice(0, 1) : [];
        head.innerHTML = (et ? esc(et) + ' jobs in ' : 'Jobs in ') + (tileOf(slug) && tileOf(slug).querySelector('.fl') ? tileOf(slug).querySelector('.fl').outerHTML : flags(codes)) + esc(name) +
          ' <span class="pill">' + num(n) + '</span>';
        list.innerHTML = rows.slice(0, 20).map(function (j) { return card(j); }).join('') ||
          '<li class="job"><span class="js" style="padding:16px">No ' + (et ? esc(et.toLowerCase()) + ' ' : '') + 'jobs in ' + esc(name) + ' today. The lists below cover other places and work from home.</span></li>';
        more.innerHTML = n > 20 ? '<a href="' + P + '/jobs/?loc=' + slug + (et ? '&etype=' + encodeURIComponent(et) : '') + '">All ' + num(n) + ' in ' + esc(name) + '</a>' : '';
        // a short summary of the place (plan item 1.13, 20 Nov 2026: the page gave only a count and twenty jobs): counted by the server
        // over the same jobs as the list
        var sum = document.getElementById('nearme-sum');
        if (!sum) { sum = document.createElement('p'); sum.id = 'nearme-sum'; sum.className = 'note'; head.parentNode.insertBefore(sum, head.nextSibling); }
        sum.innerHTML = summary(got.sum, n); sum.hidden = !sum.innerHTML;
        if (how && note) note.textContent = how;
        box.hidden = false; freshen(list);
      }).catch(function () {});
    }
    function summary(S, n) {
      if (!S || n < 10) return '';
      var top = (S.top || []).filter(function (c) { return c[1] >= 2; });
      var pc = function (k) { return Math.round(100 * k / n) + '%'; };
      var parts = [S.remote ? num(S.remote) + ' can be done from home (' + pc(S.remote) + ')' : '', S.pay ? num(S.pay) + ' state the pay (' + pc(S.pay) + ')' : '', S.fresh ? num(S.fresh) + ' posted in the last 7 days' : '',
              top.length ? 'most from ' + top.map(function (c) { return esc(c[0]) + ' (' + num(c[1]) + ')'; }).join(', ') : ''].filter(Boolean);     // a nought says nothing
      return parts.length ? parts.join(' · ') + '.' : '';
    }
    function km(a, b, c, d) {
      var r = Math.PI / 180, x = Math.sin((c - a) * r / 2), y = Math.sin((d - b) * r / 2), h = x * x + Math.cos(a * r) * Math.cos(c * r) * y * y;
      return 12742 * Math.asin(Math.sqrt(h));
    }
    function byZone() {
      fetch(P + '/data/geo.json').then(function (r) { return r.json(); }).then(function (G) {
        var tz = ''; try { tz = Intl.DateTimeFormat().resolvedOptions().timeZone || ''; } catch (e) {}
        var code = get('hrn_place', '') || G.tz[tz] || '', c = G.c[code];
        if (c && c[1]) return show(c[1], c[0], '', function () {
          var reg = G.r[c[4]];
          if (reg) show(c[4], reg[0], 'Nothing in ' + c[0] + ' today, so this is the list for ' + reg[0] + '.'); else show(c[1], c[0]);
        });
        var key = (c && c[4]) || (/^Europe\//.test(tz) ? 'europe' : /^(Asia|Australia|Pacific|Indian)\//.test(tz) ? 'asia-pacific' : /^Africa\//.test(tz) ? 'africa' : /^America\//.test(tz) ? 'latin-america' : '');
        if (key && G.r[key]) show(key, G.r[key][0]);
      }).catch(function () {});
    }
    byZone();
    document.addEventListener('change', function (ev) { if (ev.target.id === 'near-sel' && ev.target.value) setTimeout(byZone, 0); });
    if (btn && navigator.geolocation) {
      btn.hidden = false;
      btn.addEventListener('click', function () {
        btn.disabled = true; btn.textContent = 'Asking your browser…';
        navigator.geolocation.getCurrentPosition(function (pos) {
          var best = null;
          Array.prototype.forEach.call(document.querySelectorAll('[data-ll]'), function (a) {
            var ll = a.getAttribute('data-ll').split(','), d = km(pos.coords.latitude, pos.coords.longitude, Number(ll[0]), Number(ll[1]));
            if (!best || d < best.d) best = { d: d, slug: a.getAttribute('data-place'), name: a.getAttribute('data-name') };
          });
          btn.disabled = false; btn.textContent = 'Use my location for the nearest city';
          if (best && best.d <= 150) show(best.slug, best.name, 'Nearest list: ' + best.name + ', about ' + Math.round(best.d) + ' km from you. Your location stayed on this device.');
          else if (note) note.textContent = 'No city list within 150 km of you yet, so the country list is shown. Your location stayed on this device.';
        }, function () { btn.disabled = false; btn.textContent = 'Use my location for the nearest city'; if (note) note.textContent = 'Location was not shared. The country is taken from your device’s time zone.'; },
        { maximumAge: 600000, timeout: 10000 });
      });
    }
  }
  nearMe();

  /* ---------- lists: saved / applied / viewed marks, faster navigation ---------- */
  decorate(document);
  setInterval(function () { freshen(); }, 60000);           // "20 min" becomes "21 min" while the page stays open
  /* instant navigation: the browser prepares a page while the pointer rests on its link (Chrome and Edge);
     other browsers fall back to fetching the job page on hover */
  var specOk = window.HTMLScriptElement && HTMLScriptElement.supports && HTMLScriptElement.supports('speculationrules');
  if (specOk) {
    var no = function (p) { return { not: { href_matches: P + p } }; };
    var spec = document.createElement('script'); spec.type = 'speculationrules';
    spec.textContent = JSON.stringify({
      prerender: [{ where: { and: [{ href_matches: P + '/*' }, no('/jobs/'), no('/for-you/'), no('/*.json'), no('/*.xml'), no('/*.csv'), no('/*.svg'), no('/*.txt'),
        { not: { selector_matches: '[target=_blank],[download],[rel~=nofollow]' } }] }, eagerness: 'moderate' }],
      prefetch: [{ where: { or: [{ href_matches: P + '/jobs/' }, { href_matches: P + '/for-you/' }] }, eagerness: 'moderate' }]
    });
    document.head.appendChild(spec);
  }
  // The worker is registered under the build's version, so a new build is a new address. Under the bare /sw.js the CDN kept the
  // copy of 14 Nov 2026 for 30 days (the address ends in .js) and no browser ever received a newer worker.
  var swVer = ((document.querySelector('script[src*="/site.js?v="]') || {}).src || '').match(/[?&]v=([a-f0-9]+)/);
  // Registered once the page has loaded (26 Nov 2026): installing it fetches the offline page and My jobs to keep, about 40 KB, which
  // came in while a phone was still loading the page's own fonts and scripts.
  if ('serviceWorker' in navigator && location.protocol === 'https:') {
    var swReg = function () { navigator.serviceWorker.register(P + '/sw.js' + (swVer ? '?v=' + swVer[1] : '')).catch(function () {}); };
    if (document.readyState === 'complete') swReg(); else window.addEventListener('load', swReg);
  }
  var warmed = {};
  if (!specOk) document.addEventListener('mouseover', function (ev) {
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
        return '<li class="job"><a href="' + P + '/job/' + encodeURIComponent(j.s) + '/">' + avatar(j.c, j.l ? slugOf(j.c) : '', false) + '<span><span class="jt">' + esc(j.t) + '</span><span class="js">' + esc(j.c) + ' · viewed recently</span></span></a></li>';
      }).join('');
      if (lastSearch) html += '<li class="job"><a href="' + P + '/jobs/?' + esc(lastSearch.qs) + '"><span class="ava keep" aria-hidden="true">⌕</span><span><span class="jt">' + esc(lastSearch.label) + '</span><span class="js">Your saved search</span></span></a></li>';
      $('home-recent-list').innerHTML = html; recent.hidden = false;
    }
  }

  /* ---------- For you: five plain questions; every open job is checked against the answers ---------- */
  var fy = $('fy-root');
  if (fy) {
    // the answers stay in this browser; an older profile (one category, a level name, "remote only") is carried over
    if (!profile.skills) profile.skills = [];
    if (!profile.cats) profile.cats = profile.cat ? [profile.cat] : [];
    if (!profile.roles) profile.roles = [];
    // exact job titles, picked by typing: the same patterns the role pages use
    var roleRx = {};
    try { JSON.parse(($('fy-role-data') || {}).textContent || '[]').forEach(function (r) { try { roleRx[r[0]] = new RegExp(r[1], 'i'); } catch (e) {} }); } catch (e) {}
    var roleHit = function (title, roles) { for (var i = 0; i < roles.length; i++) if (roleRx[roles[i]] && roleRx[roles[i]].test(title)) return roles[i]; return ''; };
    if (profile.exp == null) profile.exp = { Intern: '0', Junior: '0', Senior: '2', Lead: '3' }[profile.lvl] || '';
    if (profile.where == null) profile.where = profile.remote ? 'remote' : '';
    if (profile.pay == null) profile.pay = profile.sal > 1 ? profile.sal : 0;
    var chips = Array.prototype.slice.call(fy.querySelectorAll('#fy-skills .chipbtn'));
    var place = $('fy-place'), payIn = $('fy-pay-in'), noPay = $('fy-nopay'), list = $('fy-list'), count = $('fy-count'), more = $('fy-more'), jump = $('fy-jump');
    var payNote = $('fy-pay-note'), gap = $('fy-gap');
    var shown = 30, found = [], nFull = 0, extra = new Map(), why = new Map(), asked = 0, fromLink = false;
    // The personal radar (plan item 14, 20 Nov 2026): the day of the last visit is kept here, and on the next visit the jobs that fit
    // and were posted after it are counted in the heading and marked in the list. Nothing is sent anywhere.
    var td0 = new Date(), today8 = td0.getFullYear() * 10000 + (td0.getMonth() + 1) * 100 + td0.getDate(), seen0 = Number(get('hrn_fy_seen', 0)) || 0, fresh = {};
    var dayOf = function (n) { return ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun', 'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec'][Math.floor(n / 100) % 100 - 1] + ' ' + (n % 100); };
    // answers that arrived in a link are shown, and kept only once the visitor changes something
    try {
      if (location.hash.indexOf('#a=') === 0) {
        var got = JSON.parse(decodeURIComponent(escape(atob(location.hash.slice(3)))));
        profile = { skills: got.s || [], cats: got.c || [], exp: got.e == null ? '' : String(got.e), where: got.w || '', whereSet: !!got.w, place: got.p || '', placeSet: true, pay: got.y || 0, paySet: !!got.y, nopay: !!got.n };
        fromLink = true;
      }
    } catch (e) {}
    var LV = { Intern: -1, Junior: 0, '': 1, Senior: 2, Lead: 3 }, REG = { europe: 1, 'asia-pacific': 1, 'latin-america': 1, africa: 1 };
    var DROP = { work: 'Any kind of work', exp: 'Any experience', where: 'Home or office, any country', country: 'Any country', pay: 'Any pay', skills: 'Without the skills' };
    var nf = function (x) { return Number(x).toLocaleString('en-US'); };
    var kfmt = function (v) { return '$' + (v >= 1000 ? Math.round(v / 1000) + 'K' : v); };
    var jobsWord = function (k) { return nf(k) + (k === 1 ? ' job' : ' jobs'); };
    // the lower end of a yearly US-dollar range, read from the text of the posting's pay line; 0 when it cannot be read
    var lowOf = function (j) {
      var m = /(\d{1,3}(?:[ , ]\d{3})+|\d[\d.]*)\s?(k)?/i.exec(j[8] || ''); if (!m) return 0;
      var v = parseFloat(m[1].replace(/[ , ]/g, '')) * (m[2] ? 1000 : 1);
      return v >= 10000 && v <= j[13] ? v : 0;
    };
    var catName = {};
    Array.prototype.forEach.call(fy.querySelectorAll('#fy-work .opt'), function (b) { catName[b.getAttribute('data-v')] = b.querySelector('b').textContent; });
    var press = function (boxId, test) { Array.prototype.forEach.call(fy.querySelectorAll('#' + boxId + ' .opt'), function (b) { b.setAttribute('aria-pressed', test(b.getAttribute('data-v')) ? 'true' : 'false'); }); };
    var paint = function () {
      chips.forEach(function (c) { c.setAttribute('aria-pressed', profile.skills.indexOf(c.getAttribute('data-skill')) >= 0 ? 'true' : 'false'); });
      press('fy-work', function (v) { return profile.cats.indexOf(v) >= 0; });
      press('fy-exp', function (v) { return String(profile.exp) === v && v !== ''; });
      press('fy-where', function (v) { return (profile.where || '') === v && (v !== '' || profile.whereSet); });
      press('fy-pay', function (v) { return Number(v) === (profile.pay || 0) && (Number(v) > 0 || profile.paySet); });
      place.value = profile.place || '';
      noPay.checked = !!profile.nopay;
      if (document.activeElement !== payIn) payIn.value = profile.pay && !fy.querySelector('#fy-pay .opt[data-v="' + profile.pay + '"]') ? profile.pay : '';
    };
    // the answers in the shape the checks need; `skip` leaves one question out (used for "what if I drop this answer")
    var answers = function (skip) {
      var o = place.options[place.selectedIndex], set_ = {};
      if (o && profile.placeGuess && !profile.whereSet) o = null;          // a country guessed from the time zone counts only once question 3 is answered
      profile.skills.forEach(function (s) { set_[s] = 1; });
      var A = { cats: skip === 'work' ? [] : profile.cats, roles: skip === 'work' ? [] : (profile.roles || []), exp: skip === 'exp' || profile.exp === '' ? '' : Number(profile.exp),
        where: skip === 'where' ? '' : profile.where || '', slug: skip === 'where' || skip === 'country' || !o ? '' : o.getAttribute('data-s') || '', reg: o ? o.getAttribute('data-r') || '' : '',
        cname: o && o.value ? o.textContent : '', pay: skip === 'pay' ? 0 : profile.pay || 0, nopay: skip === 'pay' ? false : !!profile.nopay,
        skills: skip === 'skills' ? [] : profile.skills, set: set_ };
      A.n = (A.cats.length || A.roles.length ? 1 : 0) + (A.exp !== '' ? 1 : 0) + (A.where || A.slug ? 1 : 0) + (A.pay || A.nopay ? 1 : 0) + (A.skills.length ? 1 : 0);
      return A;
    };
    // one job against the answers: null when it contradicts one, otherwise ticks, question marks and the reasons to show
    var judge = function (j, A) {
      if (mute.c[j[2]] || hidden[j[0]]) return null;
      if (mute.w.length) { var low = j[1].toLowerCase(); for (var w = 0; w < mute.w.length; w++) if (low.indexOf(mute.w[w]) >= 0) return null; }
      var ok = 0, half = 0, bits = [], k = 0, edge = 0, i;
      if (A.cats.length || A.roles.length) {
        var byRole = A.roles.length ? roleHit(j[1], A.roles) : '';
        if (!byRole && A.cats.indexOf(j[5]) < 0) return null;
        ok++; bits.push([1, byRole || catName[j[5]] || j[5]]);
      }
      if (A.exp !== '') {
        var lv = LV[j[6]] == null ? 1 : LV[j[6]], d = A.exp === 0 && lv <= 0 ? 0 : Math.abs(A.exp - lv);
        if (d > 1) return null;
        if (!d) { ok++; bits.push([1, j[6] ? j[6] + ' level' : 'Mid-level title']); }
        else { half++; bits.push([0, j[6] ? j[6] + ' level, a step ' + (lv > A.exp ? 'above' : 'below') + ' yours' : 'Title does not name a level']); }
      }
      if (A.where || A.slug) {
        var pl = j[14], inC = A.slug && pl.indexOf(A.slug) >= 0, res;
        var fromHome = function () {
          if (!j[4]) return null;
          if (!A.slug) return [1, 'Remote'];
          if (j[20]) return [1, 'Remote, open to any country'];
          if (inC) return [1, 'Remote, names ' + A.cname];
          if (A.reg && pl.indexOf(A.reg) >= 0 && pl.every(function (p) { return REG[p]; })) return [1, 'Remote across your region'];
          return pl.length ? null : [0, 'Remote, does not say from which countries'];
        };
        var onSite = function () { return j[4] ? null : !A.slug ? [1, 'On site or hybrid'] : inC ? [1, 'In ' + A.cname] : null; };
        var hybrid = function () { return !j[25] ? null : !A.slug ? [1, 'Hybrid'] : inC ? [1, 'Hybrid, in ' + A.cname] : null; };
        res = A.where === 'remote' ? fromHome() : A.where === 'hybrid' ? hybrid() : A.where === 'office' ? onSite() : onSite() || fromHome();
        if (!res) return null;
        if (res[0]) ok++; else half++;
        bits.push(res);
      }
      if (A.pay || A.nopay) {
        if (j[13]) {
          if (A.pay && j[13] < A.pay) return null;
          var lo = lowOf(j);
          ok++;
          if (!A.pay) bits.push([1, 'States pay']);
          else if (lo >= A.pay) bits.push([1, 'Whole range is above ' + kfmt(A.pay)]);
          else { edge = 1; bits.push([1, 'Top of the range, ' + kfmt(j[13]) + ', reaches ' + kfmt(A.pay)]); }
        } else if (!j[8]) { if (A.nopay) return null; half++; bits.push([0, 'Does not state pay']); }
        else { half++; bits.push([0, 'Pay is given per hour or in another currency']); }
      }
      if (A.skills.length) {
        var hit = []; for (i = 0; i < j[7].length; i++) if (A.set[j[7][i]]) hit.push(j[7][i]);
        k = hit.length;
        if (k) { ok++; bits.push([1, (k === 1 ? 'Your skill: ' : k + ' of your skills: ') + hit.slice(0, 4).join(', ') + (k > 4 ? ' and more' : '')]); }
        else if (A.n === 1) return null;                                   // skills are the only answer: a job with none of them is no match
        else { half++; bits.push([0, j[7].length ? 'Asks for skills you did not pick' : 'Names no skills']); }
      }
      return { ok: ok, s: ok * 10 + half * 3 + Math.min(k, 5) - edge * 0.5, bits: bits };
    };
    var render = function () {
      var html = '', rows = found.slice(0, shown);
      rows.forEach(function (j, i) {
        var w = why.get(j[0]);
        if (asked && i === nFull && nFull > 0) html += '<li class="fy-div">Fit in part: at least one answer could not be checked</li>';
        var line = w ? '<p class="why"><b>' + w.ok + ' of ' + asked + '</b>' + w.bits.map(function (b) { return '<span class="' + (b[0] ? 'y' : 'q') + '">' + esc(b[1]) + '</span>'; }).join('') + '</p>' : '';
        if (fresh[j[0]]) line = line ? line.replace('<p class="why">', '<p class="why"><span class="y nw">New since your last visit</span>') : '<p class="why"><span class="y nw">New since your last visit</span></p>';
        html += card(j, extra.get(j[0]) || 0, '').replace(/<\/li>$/, line + '</li>');
      });
      list.innerHTML = html; more.hidden = found.length <= shown; decorate(list);
    };
    var roleBox = $('fy-roles'), roleIn = $('fy-role'), skillIn = $('fy-skill-q');
    var drawRoles = function () {
      if (!roleBox) return;
      roleBox.innerHTML = (profile.roles || []).map(function (r, i) { return '<button class="chipbtn" type="button" aria-pressed="true" data-role-i="' + i + '">' + esc(r) + ' <span aria-hidden="true">×</span></button>'; }).join('');
    };
    if (roleIn) roleIn.addEventListener('change', function () {
      var v = roleIn.value.trim(), name = Object.keys(roleRx).filter(function (k) { return k.toLowerCase() === v.toLowerCase(); })[0];
      if (name && profile.roles.indexOf(name) < 0) { profile.roles.push(name); drawRoles(); run(); }
      roleIn.value = '';
    });
    if (roleBox) roleBox.addEventListener('click', function (ev) {
      var b = ev.target.closest && ev.target.closest('[data-role-i]');
      if (!b) return;
      profile.roles.splice(Number(b.getAttribute('data-role-i')), 1); drawRoles(); run();
    });
    if (skillIn) skillIn.addEventListener('change', function () {
      var v = skillIn.value.trim().toLowerCase(), c = chips.filter(function (x) { return x.getAttribute('data-skill').toLowerCase() === v; })[0];
      if (c) { var s = c.getAttribute('data-skill'); if (profile.skills.indexOf(s) < 0) profile.skills.push(s); chips.forEach(function (x) { x.setAttribute('aria-pressed', profile.skills.indexOf(x.getAttribute('data-skill')) >= 0 ? 'true' : 'false'); }); run(); }
      skillIn.value = '';
    });
    var bigOk = false;                    // the visitor asked to score every job (a phone waits for this; see heavyOk)
    count.addEventListener('click', function (ev) { if (ev.target && ev.target.id === 'fy-all') { bigOk = true; run(); } });
    var run = function () {
      if (!profile.roles) profile.roles = [];
      drawRoles();
      if (!fromLink) set('hrn_profile', profile);
      paint();
      var A = answers(); asked = A.n;
      if (!asked) {
        payNote.textContent = ''; gap.hidden = true; gap.innerHTML = ''; why = new Map(); nFull = 0;
        count.innerHTML = '<p class="fy-n">Answer any question and the jobs that fit are listed here.</p><p class="note">Until then, these are the newest postings.</p>';
        if (jump) jump.hidden = true;
        loadHead().then(function (h) { if (asked) return; extra = new Map(); found = collapse(h.rows.filter(function (j) { return !mute.c[j[2]] && !hidden[j[0]]; }), extra).slice(0, 30); shown = 30; render(); }).catch(function () {});
        return;
      }
      if (!bigOk && !heavyOk()) {
        // a phone: scoring every job against every answer needs the list of every job (22 MB), so it waits for a tap; meanwhile the
        // server lists the newest jobs in the visitor's fields, place and pay (fitQuery)
        why = new Map(); nFull = 0; gap.hidden = true;
        count.innerHTML = '<p class="fy-n">Your answers are saved.</p><p class="note">Below: the newest jobs in your fields, place and pay. To score every open job against all your answers, ' +
          'this page downloads the whole list (about 22 MB), so on a phone it waits for you. <button class="btn sm" type="button" id="fy-all">Check every open job</button></p>';
        var fq = fitQuery(profile);
        (fq ? listOf(fq) : listOf('np=1')).then(function (g) {
          if (bigOk || answers().n !== asked) return;
          extra = new Map(); found = g.rows.filter(function (j) { return !mute.c[j[2]] && !hidden[j[0]]; }); shown = 30; render();
        }).catch(function () {});
        return;
      }
      count.innerHTML = '<p class="fy-n">Checking every open job…</p>';
      load().then(function (all) {
        if (answers().n !== asked) return;
        why = new Map();
        var rows = all.filter(function (j) { var w = judge(j, A); if (!w) return false; why.set(j[0], w); return true; });
        rows.sort(function (a, b) { return why.get(b[0]).s - why.get(a[0]).s || (A.pay ? b[13] - a[13] : 0) || b[16] - a[16]; });
        extra = new Map(); found = collapse(rows, extra); shown = 30;
        nFull = 0; found.forEach(function (j) { if (why.get(j[0]).ok === asked) nFull++; });
        // one employer with many similar roles must not fill the first screen: two rows per company, then the next two, and so on
        var spread = function (group) {
          var out = [], rest = group;
          while (rest.length) {
            var seen = {}, later = [];
            rest.forEach(function (j) { seen[j[2]] = (seen[j[2]] || 0) + 1; if (seen[j[2]] <= 2) out.push(j); else later.push(j); });
            rest = later;
          }
          return out;
        };
        found = spread(found.slice(0, nFull)).concat(spread(found.slice(nFull)));
        var part = found.length - nFull, qs = asked === 1 ? 'your answer' : (asked === 2 ? 'both' : 'all ' + asked) + ' of your answers';
        var head = nFull ? '<b class="hl">' + nf(nFull) + '</b> ' + (nFull === 1 ? 'job fits ' : 'jobs fit ') + qs : 'No open job fits ' + qs;
        var mark = ' A tick is an answer the job agrees with; a question mark is something the posting does not say.';
        var sub = part && nFull ? nf(part) + ' more ' + (part === 1 ? 'fits' : 'fit') + ' in part and ' + (part === 1 ? 'comes' : 'come') + ' after them.' + mark
          : part ? jobsWord(part) + (part === 1 ? ' fits' : ' fit') + ' in part and ' + (part === 1 ? 'is' : 'are') + ' listed below.' + mark
          : nFull ? 'A tick is an answer the job agrees with.' : 'Try one of the changes below, or clear an answer.';
        // which single answer, if dropped, opens the most jobs: shown when the full matches are few
        var tips = '';
        if (nFull < 10 && asked > 1) {
          var opts = [];
          ['work', 'exp', 'country', 'where', 'pay', 'skills'].forEach(function (q) {
            var B = answers(q); if (q === 'country' ? !(A.slug && A.where) : B.n === asked) return;
            var c = 0; all.forEach(function (j) { var w = judge(j, B); if (w && w.ok === B.n) c++; });
            if (c > nFull) opts.push([q, c]);
          });
          opts.sort(function (a, b) { return b[1] - a[1]; });
          if (opts.length) tips = '<p class="flabel">Change one answer and more jobs fit</p><p class="fy-tips">' + opts.slice(0, 3).map(function (o) { return '<button class="chipbtn" type="button" data-drop="' + o[0] + '">' + DROP[o[0]] + ': ' + jobsWord(o[1]) + '</button>'; }).join('') + '</p>';
        }
        var full = profile.cats.length <= 1 && !profile.skills.length ? '<a href="' + P + '/jobs/?' + [profile.cats[0] ? 'cat=' + profile.cats[0] : '', profile.where === 'remote' ? 'remote' : profile.where === 'hybrid' ? 'hybrid=1' : '', A.slug ? 'loc=' + A.slug : '', A.pay ? 'sal=' + A.pay + (A.nopay ? '' : '&nosal') : ''].filter(Boolean).join('&') + '">Open the same in the full search</a>' : '';
        fresh = {}; var nNew = 0;
        if (seen0 && seen0 < today8 && !fromLink) found.slice(0, nFull).forEach(function (j) { if ((j[16] || 0) > seen0) { fresh[j[0]] = 1; nNew++; } });
        if (nNew) head += ' · <b>' + nf(nNew) + ' new</b> since your last visit on ' + dayOf(seen0);
        if (!fromLink && asked) set('hrn_fy_seen', today8);
        count.innerHTML = '<p class="fy-n">' + head + '</p>' + (sub ? '<p class="note">' + sub + '</p>' : '') + tips + (full ? '<p class="note">' + full + '</p>' : '');
        if (jump) { jump.hidden = false; jump.textContent = (nFull ? jobsWord(nFull) + ' fit' : jobsWord(found.length) + ' fit in part') + ' · show the list'; }
        render();
        // question 4: what the jobs that fit the other answers pay, so the figure asked for can be a realistic one
        var hi = []; var B4 = answers('pay'), fitOther = 0;
        all.forEach(function (j) { var w = judge(j, B4); if (w && w.ok === B4.n) { fitOther++; if (j[13]) hi.push(j[13]); } });
        hi.sort(function (a, b) { return a - b; });
        payNote.textContent = hi.length >= 15 ? 'Of the ' + jobsWord(fitOther) + ' that fit your other answers, ' + nf(hi.length) + ' state pay in US dollars. Half of those go up to ' + kfmt(hi[Math.floor(hi.length / 2)]) + ' or more.' : '';
        // question 5: which single skill would add the most jobs you do not match yet
        var gain = {};
        if (profile.skills.length) all.forEach(function (j) {
          var w = why.get(j[0]); if (!w || w.ok === asked) return;
          j[7].forEach(function (t) { if (!A.set[t]) gain[t] = (gain[t] || 0) + 1; });
        });
        var best = Object.keys(gain).sort(function (a, b) { return gain[b] - gain[a]; }).slice(0, 5);
        gap.hidden = !best.length;
        gap.innerHTML = best.length ? '<p class="flabel">Skills asked for most by the jobs that fit you only in part</p><div class="skillbar">' + best.map(function (t) {
          return '<button class="chipbtn gapbtn" type="button" data-add="' + esc(t) + '">+ ' + esc(t) + ' · ' + nf(gain[t]) + '</button>';
        }).join('') + '</div>' : '';
      }).catch(function () { count.innerHTML = '<p class="fy-n">Could not load the jobs. Please reload the page.</p>'; });
    };
    var fyNote = $('fy-note'), tell = function (msg) { if (fyNote) { fyNote.textContent = msg; fyNote.hidden = !msg; } };
    if (fromLink) tell('These answers came from a link. They replace your own only if you change something here.');
    fy.addEventListener('click', function (ev) {
      var t = ev.target, opt = t.closest && t.closest('.opt'), c = t.closest && t.closest('#fy-skills .chipbtn');
      if (t.id !== 'fy-share' && t.id !== 'fy-pic' && t.id !== 'fy-alert' && t.id !== 'fy-more') fromLink = false;
      if (t.id === 'fy-share') {
        var o = { c: profile.cats, e: profile.exp, w: profile.where, p: profile.place, y: profile.pay, n: profile.nopay ? 1 : 0, s: profile.skills };
        var url = location.origin + P + '/for-you/#a=' + btoa(unescape(encodeURIComponent(JSON.stringify(o))));
        var ok = function () { tell('Link copied. Whoever opens it sees today’s jobs for the same answers: a friend, a recruiter, or you on another device.'); };
        if (navigator.clipboard) navigator.clipboard.writeText(url).then(ok, function () { tell(url); }); else tell(url);
        return;
      }
      if (t.id === 'fy-pic') {
        if (!asked || !found.length) { tell('Answer a question first: the picture is drawn from your result.'); return; }
        var cv = document.createElement('canvas'); cv.width = 1200; cv.height = 630;
        var g = cv.getContext('2d'), full = found.slice(0, nFull || found.length), paid = full.filter(function (j) { return j[13]; }).map(function (j) { return j[13]; }).sort(function (a, b) { return a - b; });
        var cos = {}; full.forEach(function (j) { cos[j[2]] = (cos[j[2]] || 0) + 1; });
        var top = Object.keys(cos).sort(function (a, b) { return cos[b] - cos[a]; }).slice(0, 3);
        g.fillStyle = '#ffffff'; g.fillRect(0, 0, 1200, 630); g.fillStyle = '#1f9d55'; g.fillRect(0, 0, 1200, 14);
        g.fillStyle = '#121110'; g.font = '600 30px system-ui, sans-serif'; g.fillText('My job market · ' + new Date().toLocaleDateString('en-US', { month: 'long', day: 'numeric', year: 'numeric' }), 70, 96);
        g.font = '800 150px system-ui, sans-serif'; g.fillText(nf(nFull || found.length), 70, 270);
        g.font = '500 36px system-ui, sans-serif'; g.fillText((nFull ? 'open jobs fit all ' + asked + ' of my answers' : 'open jobs fit my answers in part'), 76, 326);
        g.fillStyle = '#55534c'; g.font = '500 28px system-ui, sans-serif';
        var lines = [profile.cats.length ? 'Work: ' + profile.cats.map(function (c) { return catName[c] || c; }).join(', ') : '', profile.where === 'remote' ? 'From home' : profile.where === 'hybrid' ? 'Hybrid' : profile.where === 'office' ? 'At an office' : '',
          profile.pay ? 'Pay from ' + kfmt(profile.pay) + ' a year' : '', profile.skills.length ? 'Skills: ' + profile.skills.slice(0, 5).join(', ') : ''].filter(Boolean);
        lines.forEach(function (ln, i) { g.fillText(ln.slice(0, 70), 76, 392 + i * 40); });
        g.fillStyle = '#121110'; g.font = '600 28px system-ui, sans-serif';
        if (paid.length >= 5) g.fillText('Half of them pay up to ' + kfmt(paid[Math.floor(paid.length / 2)]) + ' or more', 700, 392);
        if (top.length) g.fillText('Hiring most: ' + top.join(', ').slice(0, 34), 700, 432);
        g.fillStyle = '#1f9d55'; g.fillRect(70, 560, 60, 6); g.fillStyle = '#121110'; g.font = '700 26px system-ui, sans-serif'; g.fillText('Jobs Every Hour', 146, 572);
        g.fillStyle = '#6c6a62'; g.font = '500 22px system-ui, sans-serif'; g.fillText(location.host + P + '/for-you/', 380, 572);
        cv.toBlob(function (blob) { var a = document.createElement('a'); a.href = URL.createObjectURL(blob); a.download = 'my-job-market.png'; document.body.appendChild(a); a.click(); a.remove(); tell('The picture was saved to your downloads.'); });
        return;
      }
      if (t.id === 'fy-alert') {
        if (!('Notification' in window)) { tell('This browser cannot show notifications.'); return; }
        if (!asked) { tell('Answer a question first, so there is something to watch for.'); return; }
        Notification.requestPermission().then(function (perm) {
          if (perm !== 'granted') { tell('Notifications are switched off for this site in your browser settings.'); return; }
          profile.alert = Date.now(); set('hrn_profile', profile); keepForWorker();
          tell('Done. This browser will tell you when new jobs fit these answers. No email, no account: it works while this site is open in a tab, and in the background where the browser allows it (the site installed as an app).');
          if (navigator.serviceWorker && navigator.serviceWorker.ready) navigator.serviceWorker.ready.then(function (reg) {
            if (reg.periodicSync) reg.periodicSync.register('hrn-fit', { minInterval: 3 * 3600 * 1000 }).catch(function () {});
          });
        });
        return;
      }
      if (opt) {
        var box = opt.parentNode.id, v = opt.getAttribute('data-v'), on = opt.getAttribute('aria-pressed') === 'true';
        if (box === 'fy-work') { var i = profile.cats.indexOf(v); if (i >= 0) profile.cats.splice(i, 1); else profile.cats.push(v); }
        else if (box === 'fy-exp') profile.exp = on ? '' : v;
        else if (box === 'fy-where') { profile.where = on ? '' : v; profile.whereSet = !on; }
        else if (box === 'fy-pay') { profile.pay = on ? 0 : Number(v); profile.paySet = !on; }
        run(); return;
      }
      if (c) { var s = c.getAttribute('data-skill'), k = profile.skills.indexOf(s); if (k >= 0) profile.skills.splice(k, 1); else profile.skills.push(s); run(); return; }
      if (t.id === 'fy-more') { shown += 30; render(); return; }
      if (t.getAttribute('data-add')) { var add = t.getAttribute('data-add'); if (profile.skills.indexOf(add) < 0) profile.skills.push(add); run(); return; }
      if (t.getAttribute('data-drop')) {
        var q = t.getAttribute('data-drop');
        if (q === 'work') profile.cats = []; else if (q === 'exp') profile.exp = ''; else if (q === 'country') { profile.place = ''; profile.placeSet = true; profile.placeGuess = false; } else if (q === 'where') { profile.where = ''; profile.whereSet = false; profile.place = ''; profile.placeSet = true; profile.placeGuess = false; }
        else if (q === 'pay') { profile.pay = 0; profile.paySet = false; profile.nopay = false; } else profile.skills = [];
        run(); return;
      }
      if (t.id === 'fy-clear' || t.id === 'fy-example') {
        var txt = $('fy-text'), sn = $('fy-scan-note');
        profile = { skills: [], cats: [], roles: [], exp: '', where: '', place: '', pay: 0, nopay: false };
        if (t.id === 'fy-example') profile = { skills: ['Python', 'SQL'].filter(function (s) { return chips.some(function (c) { return c.getAttribute('data-skill') === s; }); }), cats: ['data-research'], exp: '1', where: 'remote', whereSet: true, place: '', pay: 100000, paySet: true, nopay: false };
        if (txt) txt.value = ''; if (sn) sn.textContent = '';
        run(); return;
      }
      if (t.id === 'fy-scan') {
        var text = $('fy-text').value, note = $('fy-scan-note');
        if (text.trim().length < 40) { note.textContent = 'Paste a bit more text first.'; return; }
        note.textContent = 'Reading…';
        fetch(P + '/data/skills.json').then(function (r) { return r.json(); }).then(function (pats) {
          var got = [];
          pats.forEach(function (p) { try { if (new RegExp(p[1], 'i').test(text)) got.push(p[0]); } catch (e) {} });
          var known = chips.map(function (c) { return c.getAttribute('data-skill'); });
          got = got.filter(function (s) { return known.indexOf(s) >= 0; });
          got.forEach(function (s) { if (profile.skills.indexOf(s) < 0) profile.skills.push(s); });
          note.textContent = got.length ? 'Found ' + got.length + (got.length === 1 ? ' skill: ' : ' skills: ') + got.join(', ') + '.' : 'No known skills found. Pick them by hand above.';
          run();
        }).catch(function () { note.textContent = 'Could not read the skills list. Pick skills by hand above.'; });
      }
    });
    // alerts without an account: the answers are kept where the service worker can read them, and an open tab checks every 20 minutes
    var keepForWorker = function () {
      if (!window.caches) return;
      caches.open('hrn-profile').then(function (c) { return c.put(P + '/__profile', new Response(JSON.stringify({ A: { cats: profile.cats, where: profile.where, pay: profile.pay, exp: profile.exp }, seen: profile.alert || Date.now() }))); }).catch(function () {});
    };
    var watch = function () {
      if (!profile.alert || !('Notification' in window) || Notification.permission !== 'granted') return;
      loadHead().then(function (h) {
        var A = answers(), fresh = h.rows.filter(function (j) { if (!j[23] || j[23] * 60000 <= profile.alert) return false; var w = judge(j, A); return w && w.ok === A.n; });
        if (!fresh.length) return;
        profile.alert = Date.now(); set('hrn_profile', profile); keepForWorker();
        var title = fresh.length + (fresh.length === 1 ? ' new job fits' : ' new jobs fit') + ' your answers', body = fresh[0][1] + ' at ' + fresh[0][2] + (fresh.length > 1 ? ' and ' + (fresh.length - 1) + ' more' : '');
        if (navigator.serviceWorker && navigator.serviceWorker.controller) navigator.serviceWorker.ready.then(function (reg) { reg.showNotification(title, { body: body, tag: 'hrn-fit', data: P + '/for-you/' }); });
        else try { new Notification(title, { body: body }); } catch (e) {}
      }).catch(function () {});
    };
    if (profile.alert) { keepForWorker(); setTimeout(watch, 8000); setInterval(function () { headCache = null; watch(); }, 20 * 60 * 1000); }
    place.addEventListener('change', function () { profile.place = place.value; profile.placeSet = true; profile.placeGuess = false; run(); });
    noPay.addEventListener('change', function () { profile.nopay = noPay.checked; run(); });
    var payTimer;
    payIn.addEventListener('input', function () {
      clearTimeout(payTimer);
      payTimer = setTimeout(function () { var v = Math.round(Number(payIn.value)) || 0; profile.pay = v >= 1000 ? v : 0; profile.paySet = profile.pay > 0; run(); }, 350);
    });
    // on a phone the list is below the form: a bar at the bottom says how many jobs fit and jumps to them
    if (jump && 'IntersectionObserver' in window) new IntersectionObserver(function (en) { jump.classList.toggle('off', en[0].isIntersecting); }, { rootMargin: '0px 0px -30% 0px' }).observe($('fy-out'));
    run();
    // the country is filled in from the browser's time zone the first time; it can be changed or cleared
    if (!profile.placeSet && !profile.place) fetch(P + '/data/geo.json').then(function (r) { return r.json(); }).then(function (G) {
      var tz = ''; try { tz = Intl.DateTimeFormat().resolvedOptions().timeZone || ''; } catch (e) {}
      var code = get('hrn_place', '') || G.tz[tz] || '';
      if (code && !profile.placeSet && place.querySelector('option[value="' + code + '"]')) {
        place.value = code; var nt = $('fy-place-note');
        if (nt) nt.textContent = 'Set from your device’s time zone. It only counts once you pick how you want to work, and you can change it.';
        profile.place = code; profile.placeGuess = true; set('hrn_profile', profile);
      }
    }).catch(function () {});
  }

  /* ---------- My jobs page ---------- */
  var root = $('mj-root');
  if (root) {
    var tab = 'all', openSet = null;
    var daysSince = function (ts) { return Math.floor((Date.now() - ts) / 864e5); };
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
        var r = jobs[k], d = daysSince(r.sa || r.at);
        var since = r.st === 'applied' ? ' · applied ' + (d < 1 ? 'today' : d + (d === 1 ? ' day ago' : ' days ago')) : '';
        var gone = openSet && !openSet[k] ? ' <span class="pill warn">Closed by the employer</span>' : '';
        return '<li class="trow" data-s="' + esc(k) + '">' + avatar(r.c, r.l ? slugOf(r.c) : '', false) +
          '<div class="main"><a class="tt" href="' + P + '/job/' + encodeURIComponent(k) + '/">' + esc(r.t) + '</a>' + gone + '<span class="js">' + esc(r.c) + ' · added ' + esc(when(r.at)) + since + '</span>' +
          '<input class="nt" type="text" placeholder="Add a note: contact, next step, salary discussed…" value="' + esc(r.note || '') + '" aria-label="Note"></div>' +
          '<div class="ctl"><select aria-label="Status">' + STATUS.map(function (s) { return '<option value="' + s[0] + '"' + (r.st === s[0] ? ' selected' : '') + '>' + s[1] + '</option>'; }).join('') +
          '</select><button class="unsave" type="button">Remove</button></div></li>';
      }).join('');
      $('mj-empty').hidden = shownKeys.length > 0;
      // the board: one column per stage, as on Indeed's tracker; a card moves by its menu or by dragging it to another column
      var board = $('mj-board'), list = $('mj-list'), boardOn = get('hrn_mj_view', '') === 'board';
      if (board) {
        board.hidden = !boardOn; list.hidden = boardOn; $('mj-tabs').hidden = boardOn;
        var vb = $('mj-view'); if (vb) { vb.setAttribute('aria-pressed', String(boardOn)); vb.textContent = boardOn ? 'List view' : 'Board view'; }
        if (boardOn) board.innerHTML = STATUS.filter(function (s) { return s[0] !== 'closed'; }).map(function (s) {
          var ks = keys.filter(function (k) { return jobs[k].st === s[0]; });
          return '<section class="mj-col" data-col="' + s[0] + '"><h3>' + s[1] + ' <i>' + ks.length + '</i></h3>' + ks.map(function (k) {
            var r = jobs[k], gone = openSet && !openSet[k];
            return '<div class="mj-card" draggable="true" data-s="' + esc(k) + '"><a class="tt" href="' + P + '/job/' + encodeURIComponent(k) + '/">' + esc(r.t) + '</a><span class="js">' + esc(r.c) + (gone ? ' · closed by the employer' : '') + '</span>' +
              '<select aria-label="Move to">' + STATUS.map(function (x) { return '<option value="' + x[0] + '"' + (r.st === x[0] ? ' selected' : '') + '>' + x[1] + '</option>'; }).join('') + '</select></div>';
          }).join('') + (ks.length ? '' : '<p class="note">Nothing here yet.</p>') + '</section>';
        }).join('') + (counts.closed ? '<p class="note mj-closed">' + counts.closed + ' marked “Not moving forward”: switch to the list view to see them.</p>' : '');
        if (boardOn) $('mj-empty').hidden = keys.length > 0;
      }
      var quiet = keys.filter(function (k) { return jobs[k].st === 'applied' && daysSince(jobs[k].sa || jobs[k].at) >= 10 && !(openSet && !openSet[k]); }).length, nudge = $('mj-nudge');
      if (nudge) {
        nudge.hidden = !quiet;
        nudge.textContent = quiet ? quiet + (quiet === 1 ? ' application has' : ' applications have') + ' had no reply for 10 days or more. One short, polite follow-up is reasonable. After about three weeks of silence, treat it as a no and move on.' : '';
      }
      var seen = get('hrn_seen', []);
      $('seen-list').innerHTML = seen.map(function (j) {
        return '<li class="job"><a href="' + P + '/job/' + encodeURIComponent(j.s) + '/">' + avatar(j.c, j.l ? slugOf(j.c) : '', false) + '<span><span class="jt">' + esc(j.t) + '</span><span class="js">' + esc(j.c) + '</span></span></a></li>';
      }).join('');
      $('seen-empty').hidden = seen.length > 0;
    };
    root.addEventListener('click', function (ev) {
      var t = ev.target;
      if (t.id === 'mj-view') { set('hrn_mj_view', get('hrn_mj_view', '') === 'board' ? '' : 'board'); draw(); return; }
      if (t.closest && t.closest('.tab')) { tab = t.closest('.tab').getAttribute('data-tab'); draw(); return; }
      if (t.classList.contains('unsave') && t.closest('.trow') && t.closest('#mj-list')) { delete jobs[t.closest('.trow').getAttribute('data-s')]; store(); draw(); return; }
      if (t.id === 'mj-export') {
        var rows = [['Title', 'Company', 'Status', 'Added', 'Note', 'Link']].concat(Object.keys(jobs).map(function (k) {
          var r = jobs[k], d = new Date(r.at);
          var day = d.getFullYear() + '-' + ('0' + (d.getMonth() + 1)).slice(-2) + '-' + ('0' + d.getDate()).slice(-2);
          return [r.t, r.c, r.st, day, r.note || '', location.origin + P + '/job/' + k + '/'];
        }));
        if (rows.length < 2) return;
        var cell = function (c) { c = String(c); if (/^[=+\-@]/.test(c)) c = "'" + c; return '"' + c.replace(/"/g, '""') + '"'; };   // a title starting with "=" must not run as a formula
        var csv = '\ufeff' + rows.map(function (r) { return r.map(cell).join(','); }).join('\n');
        var a = document.createElement('a');
        a.href = URL.createObjectURL(new Blob([csv], { type: 'text/csv' })); a.download = 'my-jobs.csv';
        document.body.appendChild(a); a.click(); a.remove();
      }
    });
    var dragKey = null;
    root.addEventListener('dragstart', function (ev) { var c = ev.target.closest && ev.target.closest('.mj-card'); if (!c) return; dragKey = c.getAttribute('data-s'); try { ev.dataTransfer.setData('text/plain', dragKey); } catch (e) {} });
    root.addEventListener('dragover', function (ev) { if (dragKey && ev.target.closest && ev.target.closest('.mj-col')) ev.preventDefault(); });
    root.addEventListener('drop', function (ev) {
      var col = ev.target.closest && ev.target.closest('.mj-col'); if (!col || !dragKey || !jobs[dragKey]) return;
      ev.preventDefault(); var st = col.getAttribute('data-col');
      if (jobs[dragKey].st !== st) { jobs[dragKey].st = st; jobs[dragKey].sa = Date.now(); store(); }
      dragKey = null; draw();
    });
    root.addEventListener('change', function (ev) {
      var row = ev.target.closest && (ev.target.closest('.trow') || ev.target.closest('.mj-card')); if (!row) return;
      var rec = jobs[row.getAttribute('data-s')]; if (!rec) return;
      if (ev.target.tagName === 'SELECT') { rec.st = ev.target.value; rec.sa = Date.now(); store(); draw(); }
      else if (ev.target.classList.contains('nt')) { rec.note = ev.target.value; store(); }
    });
    draw();
    // which saved jobs are still open: asked of the server by slug (the list of every job, 22 MB, was downloaded for this until 25 Nov 2026)
    if (Object.keys(jobs).length) rowsOf(Object.keys(jobs)).then(function (rows) { openSet = {}; rows.forEach(function (j) { openSet[j[0]] = 1; }); draw(); }).catch(function () {});
    var hiddenNote = $('mj-hidden'), hiddenCount = Object.keys(hidden).length, mutedCos = Object.keys(mute.c);
    if (hiddenNote && (hiddenCount || mutedCos.length || mute.w.length)) {
      hiddenNote.innerHTML = [hiddenCount ? hiddenCount + (hiddenCount === 1 ? ' job' : ' jobs') : '', mutedCos.length ? 'these companies: ' + mutedCos.map(esc).join(', ') : '',
        mute.w.length ? 'titles with: ' + mute.w.map(esc).join(', ') : ''].filter(Boolean).join('; ') + ' — hidden from your lists. <button class="linkbtn" id="mj-unhide" type="button">Show everything again</button>';
      hiddenNote.hidden = false;
      $('mj-unhide').addEventListener('click', function () { hidden = {}; set('hrn_hidden', hidden); mute.c = {}; mute.w = []; set('hrn_mute', mute); hiddenNote.hidden = true; });
    }
    // your data: a copy to keep, a way to move it to another device, and a way to wipe it
    var KEYS = ['hrn_jobs', 'hrn_searches', 'hrn_follow', 'hrn_profile', 'hrn_mute', 'hrn_hidden', 'hrn_seen', 'hrn_resume', 'hrn_resume_set'], dataNote = $('mj-data-note'), fileIn = $('mj-file');
    if ($('mj-backup')) {
      $('mj-backup').addEventListener('click', function () {
        var data = {}; KEYS.forEach(function (k) { var v = get(k, null); if (v != null) data[k] = v; });
        var a = document.createElement('a');
        a.href = URL.createObjectURL(new Blob([JSON.stringify({ app: 'hiring-right-now', version: 1, saved: new Date().toISOString(), data: data })], { type: 'application/json' }));
        a.download = 'my-jobs-backup.json'; document.body.appendChild(a); a.click(); a.remove();
        dataNote.textContent = 'Backup downloaded. Keep the file somewhere safe: it holds your notes.';
      });
      $('mj-restore').addEventListener('click', function () { fileIn.click(); });
      fileIn.addEventListener('change', function () {
        var file = fileIn.files && fileIn.files[0]; if (!file) return;
        var reader = new FileReader();
        reader.onload = function () {
          try {
            var b = JSON.parse(String(reader.result));
            if (!b || b.app !== 'hiring-right-now' || !b.data || typeof b.data !== 'object') throw new Error('not a backup');
            var LISTS = { hrn_searches: 1, hrn_seen: 1 };
            KEYS.forEach(function (k) {
              var v = b.data[k];
              if (v == null || typeof v !== 'object' || Array.isArray(v) !== !!LISTS[k]) return;      // wrong shape: leave what is there
              set(k, v);
            });
            location.reload();
          } catch (e) { dataNote.textContent = 'That file is not a backup from this site.'; }
        };
        reader.readAsText(file);
      });
      $('mj-erase').addEventListener('click', function () {
       sure($('mj-erase'), 'Erase everything this site keeps in this browser: saved jobs, applications, notes, searches, hidden items, your skill profile, your resume and what you typed into the tools? This cannot be undone.', 'Erase everything').then(function (ok) {
        if (!ok) return;
        try {
          Object.keys(localStorage).forEach(function (k) { if (KEYS.indexOf(k) >= 0 || k.indexOf('hrn_tool_') === 0) localStorage.removeItem(k); });
        } catch (e) {}
        location.reload();
       });
      });
    }

    var searches = get('hrn_searches', []);
    var drawSearches = function (counts) {           // counts: the new jobs of each saved search, as the server counted them
      $('ss-empty').hidden = searches.length > 0;
      $('ss-list').innerHTML = searches.map(function (s, i) {
        var fresh = '', n = counts ? counts[i] : null;
        if (n != null) fresh = n ? '<span class="pill ok">' + n.toLocaleString('en-US') + ' new</span>' : '<span class="pill">No new jobs</span>';
        return '<li class="trow" data-i="' + i + '"><span class="ava keep" aria-hidden="true">⌕</span><div class="main"><a class="tt ss-open" href="' + P + '/jobs/?' + esc(s.qs) + '">' + esc(s.label) + '</a>' +
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
    var follows = get('hrn_follow', {}), fkeys = Object.keys(follows);
    var drawFollows = function (counts) {           // counts: company -> [new, open], as the server counted them
      $('fc-empty').hidden = fkeys.length > 0;
      $('fc-list').innerHTML = fkeys.map(function (k) {
        var fresh = '', c = counts && counts[k];
        if (c) fresh = (c[0] ? '<span class="pill ok">' + c[0].toLocaleString('en-US') + ' new</span>' : '') + '<span class="pill">' + c[1].toLocaleString('en-US') + ' open</span>';
        return '<li class="trow" data-k="' + esc(k) + '">' + avatar(follows[k].name, '', true) + '<div class="main"><a class="tt" href="' + P + '/companies/' + esc(k) + '/">' + esc(follows[k].name) + '</a>' +
          '<span class="js">Company you follow</span></div><div class="ctl">' + fresh + '<button class="unsave fc-del" type="button">Unfollow</button></div></li>';
      }).join('');
    };
    drawFollows(null);
    $('fc-list').addEventListener('click', function (ev) {
      if (!ev.target.classList.contains('fc-del')) return;
      var k = ev.target.closest('.trow').getAttribute('data-k');
      delete follows[k]; fkeys = Object.keys(follows); set('hrn_follow', follows); drawFollows(null);
    });
    // the counts come from the server, one small request each (the list of every job, 22 MB, was downloaded for them until 25 Nov 2026)
    var countOf = function (qs) { return listOf(qs + '&count=1').then(function (g) { return g.total; }, function () { return null; }); };
    if (searches.length) Promise.all(searches.map(function (s) {
      var qs = (s.qs || '').split('&').filter(function (x) { return x && !/^(?:sort|after|count)=/.test(x); }).join('&');
      return countOf((qs ? qs + '&' : '') + 'after=' + Number(s.seen || 0));
    })).then(drawSearches);
    if (fkeys.length) Promise.all(fkeys.slice(0, 40).map(function (k) {
      var co = 'co=' + encodeURIComponent(follows[k].name || '');
      return Promise.all([countOf(co + '&after=' + Number(follows[k].seen || 0)), countOf(co)]);
    })).then(function (all) { var out = {}; all.forEach(function (c, i) { if (c[1] != null) out[fkeys[i]] = [c[0] || 0, c[1]]; }); drawFollows(out); });
  }
})();

/* Pricing: one table for people looking for work, another for employers. Without this script both are shown, one after the other. */
(function () {
  var sw = document.getElementById('pswitch'); if (!sw) return;
  var a = document.getElementById('for-seekers'), b = document.getElementById('for-employers');
  function show(emp) {
    a.hidden = emp; b.hidden = !emp;
    [].forEach.call(sw.querySelectorAll('button'), function (x) { x.setAttribute('aria-pressed', String((x.getAttribute('data-v') === 'e') === emp)); });
  }
  sw.hidden = false;
  sw.addEventListener('click', function (ev) {
    var t = ev.target.closest('button'); if (!t) return;
    var emp = t.getAttribute('data-v') === 'e'; show(emp);
    try { history.replaceState(null, '', emp ? '#employers' : location.pathname); } catch (e) {}
  });
  window.addEventListener('hashchange', function () { show(location.hash === '#employers'); });
  show(location.hash === '#employers');
})();

/* a resume read from a file, in the browser: <input type="file" data-into="id of a textarea">. A .docx is unzipped here (its
   word/document.xml), a PDF is read with pdf.js, fetched only when someone picks a PDF; a .txt is read as it is. The file never
   leaves the device; only the text is put into the box, where the person can check it before running the tool. */
(function () {
  var u16 = function (b, o) { return b[o] | (b[o + 1] << 8); };
  var u32 = function (b, o) { return (b[o] | (b[o + 1] << 8) | (b[o + 2] << 16)) + b[o + 3] * 16777216; };
  var inflate = async function (bytes) {
    var s = new Blob([bytes]).stream().pipeThrough(new DecompressionStream('deflate-raw'));
    return new Uint8Array(await new Response(s).arrayBuffer());
  };
  var docx = async function (buf) {
    var b = new Uint8Array(buf), end = -1, i, k;
    for (i = b.length - 22; i >= Math.max(0, b.length - 66000); i--) if (u32(b, i) === 0x06054b50) { end = i; break; }
    if (end < 0) throw new Error('not a zip');
    var n = u16(b, end + 10), off = u32(b, end + 16);
    for (k = 0; k < n && u32(b, off) === 0x02014b50; k++) {
      var method = u16(b, off + 10), size = u32(b, off + 20), nl = u16(b, off + 28), xl = u16(b, off + 30), cl = u16(b, off + 32), lho = u32(b, off + 42);
      if (new TextDecoder().decode(b.subarray(off + 46, off + 46 + nl)) === 'word/document.xml') {
        var start = lho + 30 + u16(b, lho + 26) + u16(b, lho + 28), data = b.subarray(start, start + size);
        var xml = new TextDecoder().decode(method === 8 ? await inflate(data) : data);
        return xml.replace(/<w:tab\/>/g, '\t').replace(/<w:br[^>]*\/>/g, '\n').replace(/<\/w:p>/g, '\n').replace(/<[^>]+>/g, '')
          .replace(/&lt;/g, '<').replace(/&gt;/g, '>').replace(/&quot;/g, '"').replace(/&apos;/g, "'").replace(/&amp;/g, '&').replace(/\n{3,}/g, '\n\n').trim();
      }
      off += 46 + nl + xl + cl;
    }
    throw new Error('no document.xml');
  };
  var PDFJS = 'https://cdnjs.cloudflare.com/ajax/libs/pdf.js/3.11.174/';
  var pdfjs = function () {
    return new Promise(function (ok, no) {
      if (window.pdfjsLib) return ok(window.pdfjsLib);
      var s = document.createElement('script'); s.src = PDFJS + 'pdf.min.js';
      s.onload = function () { window.pdfjsLib.GlobalWorkerOptions.workerSrc = PDFJS + 'pdf.worker.min.js'; ok(window.pdfjsLib); };
      s.onerror = no; document.head.appendChild(s);
    });
  };
  var pdf = async function (buf) {
    var lib = await pdfjs(), doc = await lib.getDocument({ data: buf }).promise, out = [], p;
    for (p = 1; p <= doc.numPages; p++) {
      var items = (await (await doc.getPage(p)).getTextContent()).items, line = '', lastY = null;
      items.forEach(function (it) {
        var y = it.transform[5];
        if (lastY !== null && Math.abs(y - lastY) > 2) { out.push(line); line = ''; }
        line += (line && !/\s$/.test(line) && !/^\s/.test(it.str) ? ' ' : '') + it.str; lastY = y;
        if (it.hasEOL) { out.push(line); line = ''; lastY = null; }
      });
      if (line) out.push(line);
      out.push('');
    }
    return out.join('\n').replace(/[ \t]+\n/g, '\n').replace(/\n{3,}/g, '\n\n').trim();
  };
  document.addEventListener('change', async function (ev) {
    var inp = ev.target;
    if (!inp.matches || !inp.matches('input[type=file][data-into]')) return;
    var f = inp.files && inp.files[0], box = document.getElementById(inp.getAttribute('data-into')), wrap = inp.closest('.tl-file'), msg = wrap && wrap.querySelector('.tl-fmsg');
    if (!f || !box) return;
    var say = function (t) { if (msg) msg.textContent = t; };
    say('Reading ' + f.name + '…');
    try {
      var buf = await f.arrayBuffer(), nm = f.name.toLowerCase(), text;
      if (/\.docx$/.test(nm)) text = await docx(buf);
      else if (/\.pdf$/.test(nm)) text = await pdf(buf);
      else text = new TextDecoder().decode(buf);
      if (!text || text.length < 20) throw new Error('no text');
      box.value = text; box.dispatchEvent(new Event('input', { bubbles: true }));
      say('Read ' + f.name + ' in your browser; nothing was uploaded. Check the text below, then run the check.');
    } catch (e) { say('This file could not be read here (a scanned PDF has no text to read). Copy the text from it and paste it below.'); }
    inp.value = '';
  });
})();

/* a letter template as a file: <button data-doc="id of the element" data-name="file name"> downloads a Word file made in the browser,
   <button data-pdf="id"> opens the letter alone in a print window, where "Save as PDF" is a printer. Nothing is sent anywhere. */
(function () {
  var esc = function (x) { return x.replace(/[&<>]/g, function (c) { return { '&': '&amp;', '<': '&lt;', '>': '&gt;' }[c]; }); };
  var body = function (text) {
    return text.replace(/\r/g, '').split(/\n{2,}/).map(function (p) { return '<p>' + esc(p).replace(/\n/g, '<br>') + '</p>'; }).join('');
  };
  var css = 'body{font-family:Calibri,Arial,sans-serif;font-size:11pt;line-height:1.45;max-width:640px;margin:40px auto;color:#111}p{margin:0 0 12pt}';
  document.addEventListener('click', function (ev) {
    var b = ev.target.closest ? ev.target.closest('[data-doc],[data-pdf]') : null; if (!b) return;
    var src = document.getElementById(b.getAttribute('data-doc') || b.getAttribute('data-pdf')); if (!src) return;
    var text = src.textContent, name = (b.getAttribute('data-name') || 'letter').replace(/[^a-z0-9-]+/gi, '-');
    if (b.hasAttribute('data-doc')) {
      var html = '<html xmlns:o="urn:schemas-microsoft-com:office:office" xmlns:w="urn:schemas-microsoft-com:office:word"><head><meta charset="utf-8"><title>' + esc(name) + '</title><style>' + css + '</style></head><body>' + body(text) + '</body></html>';
      var a = document.createElement('a');
      a.href = URL.createObjectURL(new Blob(['\ufeff' + html], { type: 'application/msword' }));
      a.download = name + '.doc'; document.body.appendChild(a); a.click();
      setTimeout(function () { URL.revokeObjectURL(a.href); a.remove(); }, 1000);
    } else {
      var w = window.open('', '_blank'); if (!w) return;
      w.document.write('<!doctype html><html><head><meta charset="utf-8"><title>' + esc(name) + '</title><style>' + css + '@media print{body{margin:0 auto}}</style></head><body>' + body(text) + '</body></html>');
      w.document.close(); w.focus(); setTimeout(function () { w.print(); }, 250);
    }
  });
})();

/* a "copy" button for a sentence or a block of text on the page: <button data-clip="id of the element"> */
(function () {
  document.addEventListener('click', function (ev) {
    var b = ev.target.closest ? ev.target.closest('[data-clip]') : null; if (!b) return;
    var src = document.getElementById(b.getAttribute('data-clip')); if (!src) return;
    var text = 'value' in src ? src.value : src.textContent, old = b.textContent;
    if (!b.hasAttribute('data-raw')) text = text.replace(/\s+/g, ' ').trim();
    var done = function () { b.textContent = 'Copied'; setTimeout(function () { b.textContent = old; }, 1600); };
    var pick = function () { var r = document.createRange(); r.selectNodeContents(src); var sel = window.getSelection(); sel.removeAllRanges(); sel.addRange(r); };
    if (navigator.clipboard) navigator.clipboard.writeText(text).then(done, pick); else pick();
  });
})();

/* job page: how this job fits the visitor's "For you" answers (kept in this browser as hrn_profile), the way Hirify scores a job.
   Without answers it invites the visitor to give them once. The answers are never sent anywhere; only this job's row is asked of our server. */
(function () {
  var H = window.HRN, save = document.getElementById('save'), anchor = document.querySelector('.rmbox') || document.getElementById('apply');
  if (!H || !save || !anchor) return;
  var p = H.get('hrn_profile', null) || {}, slug = save.getAttribute('data-slug'), P = H.base;
  var cats = p.cats || [], skills = p.skills || [], exp = p.exp === '' || p.exp == null ? null : Number(p.exp), pay = Number(p.pay) || 0;
  var box = document.createElement('div');
  box.className = 'fitbox';
  if (!cats.length && !skills.length && exp === null && !p.where && !pay) {
    box.innerHTML = '<a href="' + P + '/for-you/"><b>How well does this job fit you?</b><span>Answer five questions once: every job page then shows it.</span></a>';
    anchor.parentNode.insertBefore(box, anchor.nextSibling);
    return;
  }
  H.rowsOf([slug]).then(function (rows) {          // this one job's row from the server (it was found in the list of every job, 22 MB)
    var j = rows[0] || null;
    if (!j) return;
    var bits = [], ok = 0, n = 0, k = function (v) { return '$' + Math.round(v / 1000) + 'K'; };
    if (cats.length) { n++; if (cats.indexOf(j[5]) >= 0) { ok++; bits.push([1, 'Your kind of work']); } else bits.push([0, 'Another kind of work than you chose']); }
    if (exp !== null) {
      var LV = { Intern: -1, Junior: 0, '': 1, Senior: 2, Lead: 3 }, lv = LV[j[6]] == null ? 1 : LV[j[6]], d = exp === 0 && lv <= 0 ? 0 : Math.abs(exp - lv);
      n++;
      if (!d) { ok++; bits.push([1, (j[6] || 'Mid') + ' level, like yours']); } else bits.push([0, (j[6] || 'Mid-level') + ' title, ' + (lv > exp ? 'above' : 'below') + ' your level']);
    }
    if (p.where === 'hybrid') {
      n++;
      if (j[25]) { ok++; bits.push([1, 'Hybrid, as you want']); } else bits.push([0, j[4] ? 'Remote, you chose hybrid' : 'On site, you chose hybrid']);
    }
    if (p.where === 'remote' || p.where === 'office') {
      n++;
      var rem = !!j[4];
      if ((p.where === 'remote') === rem) { ok++; bits.push([1, rem ? 'Remote, as you want' : 'On site or hybrid, as you want']); } else bits.push([0, rem ? 'Remote, you chose an office' : 'On site, you chose remote']);
    }
    if (pay) {
      n++;
      if (j[13] && j[13] >= pay) { ok++; bits.push([1, 'Pay reaches ' + k(pay)]); } else bits.push([0, j[13] ? 'Pay tops out at ' + k(j[13]) : 'Does not state pay']);
    }
    if (skills.length) {
      n++;
      var hit = j[7].filter(function (t) { return skills.indexOf(t) >= 0; });
      if (hit.length) { ok++; bits.push([1, (hit.length === 1 ? 'Your skill: ' : hit.length + ' of your skills: ') + hit.slice(0, 3).join(', ')]); }
      else bits.push([0, j[7].length ? 'Names none of your skills' : 'Names no skills']);
    }
    if (!n) return;
    box.innerHTML = '<p class="fit-h"><b>' + ok + ' of ' + n + '</b> of your answers fit this job</p><ul>' +
      bits.map(function (b) { return '<li class="' + (b[0] ? 'y' : 'q') + '">' + H.esc(b[1]) + '</li>'; }).join('') + '</ul><a href="' + P + '/for-you/">Change your answers</a>';
    anchor.parentNode.insertBefore(box, anchor.nextSibling);
  }).catch(function () {});
})();


/* ---------- job alerts: "Email me new jobs like these" (alert_form in build.py, server/src/alerts.js) ----------
   Sends the form as JSON and writes the answer under it; without this script the form posts itself and the API answers with a page.
   On the search page the current search is copied into the form first, so the alert is the search the visitor is looking at. */
(function () {
  var forms = document.querySelectorAll('form[data-alert]');
  for (var i = 0; i < forms.length; i++) (function (f) {
    f.addEventListener('submit', function (ev) {
      ev.preventDefault();
      if (f.hasAttribute('data-alert-search')) {
        var p = new URLSearchParams(location.search), set = function (k, v) { var el = f.elements[k]; if (el) el.value = v; };
        set('q', p.get('q') || ''); set('cat', p.get('cat') || ''); set('loc', p.get('loc') || ''); set('remote', p.has('remote') ? '1' : ''); set('sal', p.get('sal') || '');
      }
      var out = f.querySelector('[data-alert-out]'), btn = f.querySelector('button[type=submit]'), data = {};
      new FormData(f).forEach(function (v, k) { data[k] = String(v); });
      btn.disabled = true; out.textContent = 'Sending…';
      fetch(f.action, { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(data) })
        .then(function (r) { return r.json().catch(function () { return {}; }).then(function (d) { return { ok: r.ok, d: d }; }); })
        .then(function (x) {
          out.textContent = x.d.message || (x.ok ? 'Done.' : 'The alert was not saved. Please try again.');
          if (x.ok && f.elements.email) f.elements.email.value = '';
        })
        .catch(function () { out.textContent = 'The alert could not be sent. Check the connection and try again.'; })
        .then(function () { btn.disabled = false; });
    });
  })(forms[i]);
})();

// "On this page": mark the section being read (long article pages, wide screens only)
(function () {
  var toc = document.querySelector('.toc');
  if (!toc || !('IntersectionObserver' in window)) return;
  var links = [].slice.call(toc.querySelectorAll('li a')), byId = {};
  links.forEach(function (a) { byId[a.getAttribute('href').slice(1)] = a; });
  var io = new IntersectionObserver(function (es) {
    es.forEach(function (en) {
      if (!en.isIntersecting) return;
      links.forEach(function (a) { a.classList.remove('on'); });
      var a = byId[en.target.id]; if (a) a.classList.add('on');
    });
  }, { rootMargin: '-90px 0px -65% 0px' });
  Object.keys(byId).forEach(function (id) { var el = document.getElementById(id); if (el) io.observe(el); });
})();

// the account in the header: "Sign in" for everyone, and once signed in a round button with the first letter and a menu.
// The menu follows the side the person uses (hrn_role: a job seeker sees resumes, saved jobs and alerts; an employer sees their jobs,
// posting, promotion and billing). It is drawn again whenever the sign-in or the side changes: the account page says so with the event
// "hrn:auth", another tab of the site through the "storage" event. Signing out puts "Sign in" back at once, without loading a page.
(function () {
  var a = document.getElementById('hsign');
  if (!a) return;
  var api = (a.getAttribute('data-api') || '').replace(/\/+$/, ''), base = (window.HRN && window.HRN.base) || '';
  if (window.HRN) window.HRN.api = api;                 // for the pages that keep something in the account (the resume builder)
  var get = function (k) { try { return JSON.parse(localStorage.getItem(k)); } catch (e) { return null; } };
  var acc = base + '/account/', wrap = null;
  var MENU = {
    seeker: [[acc + '#overview', 'Your account'], [acc + '#resumes', 'Resumes'], [base + '/my-jobs/', 'Saved jobs and applications'], [acc + '#alerts', 'Job alerts'], [acc + '#settings', 'Settings']],
    employer: [[acc + '#overview', 'Your account'], [acc + '#jobs', 'Your jobs'], [acc + '#post', 'Post a job'], [acc + '#promote', 'Promote a job'], [acc + '#company', 'Company page'], [acc + '#billing', 'Billing'], [acc + '#settings', 'Settings']]
  };
  var close = function () { if (!wrap) return; wrap.querySelector('.hacc-m').hidden = true; wrap.querySelector('.hacc-b').setAttribute('aria-expanded', 'false'); };
  function paint() {
    var token = get('hrn_token'), email = get('hrn_me_email') || '', role = get('hrn_role') === 'employer' ? 'employer' : 'seeker';
    if (!token) { if (wrap) { wrap.replaceWith(a); wrap = null; } return; }      // signed out: the link "Sign in" is back as it was
    var w = document.createElement('div'); w.className = 'hacc';
    w.innerHTML = '<button class="hacc-b" type="button" aria-haspopup="true" aria-expanded="false" aria-label="Your account">' +
      (email ? email.charAt(0).toUpperCase() : '•') + '</button><div class="hacc-m" role="menu" hidden>' +
      '<p class="hacc-e">' + (email ? '<b>' + email.replace(/[<>&"]/g, '') + '</b>' : '') + '<span>' + (role === 'employer' ? 'Employer account' : 'Job seeker account') + '</span></p>' +
      MENU[role].map(function (x) { return '<a role="menuitem" href="' + x[0] + '">' + x[1] + '</a>'; }).join('') +
      '<button role="menuitem" type="button" class="hacc-out">Sign out</button></div>';
    (wrap || a).replaceWith(w); wrap = w;
    var b = w.querySelector('.hacc-b'), m = w.querySelector('.hacc-m');
    b.addEventListener('click', function (ev) { ev.stopPropagation(); m.hidden = !m.hidden; b.setAttribute('aria-expanded', String(!m.hidden)); });
    m.addEventListener('click', function (ev) { if (ev.target.tagName === 'A') close(); });      // a part of the account page that is open already: the menu must not stay over it
    w.querySelector('.hacc-out').addEventListener('click', function () {
      if (document.getElementById('acc')) { close(); document.dispatchEvent(new CustomEvent('hrn:signout')); return; }      // on the account page the page itself signs out and shows the form
      fetch(api + '/api/auth/logout', { method: 'POST', headers: { Authorization: 'Bearer ' + token } }).catch(function () {});
      try { localStorage.setItem('hrn_token', '""'); localStorage.setItem('hrn_me_email', '""'); } catch (e) {}
      paint();
      try { document.dispatchEvent(new CustomEvent('hrn:auth')); } catch (e) {}
    });
  }
  document.addEventListener('click', function (ev) { if (wrap && !wrap.contains(ev.target)) close(); });
  document.addEventListener('keydown', function (ev) { if (ev.key === 'Escape' && wrap && !wrap.querySelector('.hacc-m').hidden) { close(); wrap.querySelector('.hacc-b').focus(); } });
  document.addEventListener('hrn:auth', paint);
  window.addEventListener('storage', function (ev) { if (!ev.key || ev.key === 'hrn_token' || ev.key === 'hrn_role' || ev.key === 'hrn_me_email') paint(); });
  paint();
})();

/* Swipe through jobs (/swipe/, plan item 4.30, 20 Nov 2026): one card at a time, newest first; the visitor's field first when For you
   has their answers, with how many of them fit. Save puts the job in My jobs (hrn_jobs), Pass keeps it out of this page (hrn_swiped).
   Touch: drag the card right or left; keys: → and ←. Nothing is sent anywhere. */
(function () {
  var H = window.HRN, box = document.getElementById('swipe');
  if (!H || !box) return;
  var P = H.base, esc = H.esc, prof = H.get('hrn_profile', null) || {}, cats = prof.cats || [], skills = prof.skills || [], pay = Number(prof.pay) || 0;
  var exp = prof.exp === '' || prof.exp == null ? null : Number(prof.exp), LV = { Intern: -1, Junior: 0, '': 1, Senior: 2, Lead: 3 };
  var queue = [], i = 0, done = 0;
  function fit(j) {
    var n = 0, ok = 0;
    if (cats.length) { n++; if (cats.indexOf(j[5]) >= 0) ok++; }
    if (exp !== null) { n++; var lv = LV[j[6]] == null ? 1 : LV[j[6]]; if (Math.abs(exp - lv) <= (exp === 0 && lv <= 0 ? 1 : 0)) ok++; }
    if (prof.where === 'remote' || prof.where === 'hybrid' || prof.where === 'office') { n++; if (prof.where === 'remote' ? j[4] : prof.where === 'hybrid' ? j[25] : !j[4]) ok++; }
    if (pay) { n++; if (j[13] && j[13] >= pay) ok++; }
    if (skills.length) { n++; if (j[7].some(function (t) { return skills.indexOf(t) >= 0; })) ok++; }
    return [ok, n];
  }
  function draw() {
    var j = queue[i];
    if (!j) { box.innerHTML = '<div class="swcard end"><p><b>That is all for now.</b> ' + done + ' looked at. New jobs arrive every hour.</p><p><a class="btn primary" href="' + P + '/my-jobs/">Open My jobs</a></p></div>'; return; }
    var f = fit(j), pills = (j[4] ? '<span class="pill ok">Remote</span>' : j[25] ? '<span class="pill">Hybrid</span>' : '') + (j[6] ? '<span class="pill">' + esc(j[6]) + '</span>' : '');
    box.innerHTML = '<div class="swcard" id="swcard" tabindex="0">' +
      (f[1] ? '<p class="swfit"><b>' + f[0] + ' of ' + f[1] + '</b> of your answers fit</p>' : '') +
      '<h2><a href="' + P + '/job/' + j[0] + '/">' + esc(j[1]) + '</a></h2><p class="swco">' + esc(j[2]) + (j[3] ? ' · ' + esc(j[3]) : '') + '</p>' +
      '<p class="swpay">' + (j[8] ? esc(j[8]) : 'Pay not stated') + '</p><p class="pills">' + pills + '</p>' +
      (j[7].length ? '<p class="swtags">' + j[7].slice(0, 8).map(function (t) { return '<span>' + esc(t) + '</span>'; }).join('') + '</p>' : '') +
      '<p class="swact"><button class="btn ghost" type="button" data-sw="pass">← Pass</button><a class="btn ghost" href="' + P + '/job/' + j[0] + '/">Open</a><button class="btn primary" type="button" data-sw="save">Save →</button></p>' +
      '<p class="note">' + (queue.length - i - 1).toLocaleString('en-US') + ' more after this one.</p></div>';
    var card = document.getElementById('swcard'), x0 = null, dx = 0;
    card.addEventListener('pointerdown', function (ev) { if (ev.target.closest('a,button')) return; x0 = ev.clientX; dx = 0; card.setPointerCapture(ev.pointerId); });
    card.addEventListener('pointermove', function (ev) { if (x0 === null) return; dx = ev.clientX - x0; card.style.transform = 'translateX(' + dx + 'px) rotate(' + dx / 30 + 'deg)'; });
    card.addEventListener('pointerup', function () { if (x0 === null) return; x0 = null; if (Math.abs(dx) > 90) act(dx > 0 ? 'save' : 'pass'); else card.style.transform = ''; });
  }
  function act(what) {
    var j = queue[i]; if (!j) return;
    if (what === 'save') { var mine = H.get('hrn_jobs', {}) || {}; if (!mine[j[0]]) mine[j[0]] = { t: j[1], c: j[2], st: 'saved', at: Date.now(), note: '' }; H.set('hrn_jobs', mine); }
    var sw = H.get('hrn_swiped', {}) || {}; sw[j[0]] = 1; var ks = Object.keys(sw); if (ks.length > 5000) ks.slice(0, ks.length - 5000).forEach(function (k) { delete sw[k]; }); H.set('hrn_swiped', sw);
    i++; done++; draw();
  }
  box.addEventListener('click', function (ev) { var b = ev.target.closest('[data-sw]'); if (b) act(b.getAttribute('data-sw')); });
  document.addEventListener('keydown', function (ev) { if (ev.target.closest && ev.target.closest('input,textarea,select')) return; if (ev.key === 'ArrowRight') act('save'); else if (ev.key === 'ArrowLeft') act('pass'); });
  var reset = document.getElementById('swipe-reset');
  if (reset) reset.addEventListener('click', function () { H.set('hrn_swiped', {}); location.reload(); });
  H.load().then(function (rows) {
    var mine = H.get('hrn_jobs', {}) || {}, sw = H.get('hrn_swiped', {}) || {}, hid = H.get('hrn_hidden', {}) || {};
    var once = {};          // one card for a role a company posts in many places, as the lists show it
    queue = rows.filter(function (j) { var k = (j[1] + '|' + j[2]).toLowerCase(); if (once[k]) return false; once[k] = 1; return !j[22] && !mine[j[0]] && !sw[j[0]] && !hid[j[0]]; })
      .map(function (j) { var f = fit(j); return [j, f[1] ? f[0] / f[1] : 0]; })
      .sort(function (a, b) { return (b[1] >= 0.6) - (a[1] >= 0.6) || (b[0][16] || 0) - (a[0][16] || 0); })
      .map(function (x) { return x[0]; }).slice(0, 500);
    draw();
  }).catch(function () { box.innerHTML = '<p class="note">The jobs could not be loaded. Try again in a minute.</p>'; });
})();

/* A salary in the visitor's own currency (plan item 4.25, 20 Nov 2026): an element with data-usd gets "about €148K a year", from the
   ECB euro reference rates in /data/fx.json and the country of the device's time zone (/data/geo.json, as "near you" uses). Nothing
   is shown for a visitor in the United States, or when either file is missing. */
(function () {
  var els = document.querySelectorAll('[data-usd]'); if (!els.length || !window.fetch) return;
  var P = (window.HRN && window.HRN.base) || '';
  var EUR = 'AT BE HR CY EE FI FR DE GR IE IT LV LT LU MT NL PT SK SI ES BG'.split(' ');
  var CUR = { GB: 'GBP', CH: 'CHF', SE: 'SEK', NO: 'NOK', DK: 'DKK', PL: 'PLN', CZ: 'CZK', HU: 'HUF', RO: 'RON', IS: 'ISK', TR: 'TRY', AU: 'AUD', CA: 'CAD', NZ: 'NZD', JP: 'JPY',
              CN: 'CNY', HK: 'HKD', SG: 'SGD', KR: 'KRW', IN: 'INR', ID: 'IDR', MY: 'MYR', PH: 'PHP', TH: 'THB', IL: 'ILS', MX: 'MXN', BR: 'BRL', ZA: 'ZAR' };
  Promise.all([fetch(P + '/data/fx.json').then(function (r) { return r.ok ? r.json() : null; }), fetch(P + '/data/geo.json').then(function (r) { return r.ok ? r.json() : null; })]).then(function (a) {
    var fx = a[0], G = a[1]; if (!fx || !G) return;
    var tz = ''; try { tz = Intl.DateTimeFormat().resolvedOptions().timeZone || ''; } catch (e) {}
    var code = (window.HRN && window.HRN.get('hrn_place', '')) || G.tz[tz] || '', cur = EUR.indexOf(code) >= 0 ? 'EUR' : CUR[code];
    var rate = cur && fx.per_usd[cur]; if (!rate) return;
    // the page is in English: €197K, not 197 тыс. €
    var fmt = function (v) { try { return new Intl.NumberFormat('en-US', { style: 'currency', currency: cur, notation: 'compact', maximumFractionDigits: 0 }).format(v); } catch (e) { return Math.round(v / 1000) + 'K ' + cur; } };
    Array.prototype.forEach.call(els, function (el) {
      var usd = Number(el.getAttribute('data-usd')); if (!usd) return;
      el.textContent = 'In your currency: about ' + fmt(usd * rate) + ' a year at the median (European Central Bank reference rate of ' + fx.date + '; employers set pay in their own currency, so read it as a guide).';
      el.hidden = false;
    });
  }).catch(function () {});
})();

/* Placeholders that do not fit a narrow field ("Type a word, for example vesting or…") are cut by the browser mid-word.
   Where the text is wider than the field, use the longest shorter wording that fits: "…, e.g. vesting", then the part before the example,
   then the list cut at a comma. The full text comes back on a wide screen. */
(function () {
  // Sizes come from a ResizeObserver, which reports them after the browser's own layout. Reading clientWidth on load forced a layout
  // of the whole page: about 250 ms of a phone's main thread on the home page (24 Nov 2026).
  if (!window.ResizeObserver) return;
  var cv = null;            // made on first need: most placeholders fit
  function variants(t) {
    var out = [t], m = t.match(/^(.*?)[,:]?\s+(?:for example|e\.g\.)\s+(.+)$/i);
    if (m) {
      var first = m[2].split(/\s+or\s+|,\s*/)[0];
      out.push(m[1] + ', e.g. ' + first, m[1]);
    }
    var parts = t.replace(/…$/, '').split(', ');
    for (var i = parts.length - 1; i >= 1; i--) out.push(parts.slice(0, i).join(', ') + '…');
    var w = parts[0].split(' ');
    for (var k = w.length - 1; k >= 2; k--) out.push(w.slice(0, k).join(' ') + '…');
    return out;
  }
  function fitOne(inp, room) {
    var full = inp.getAttribute('data-ph') || inp.getAttribute('placeholder');
    if (!full || room < 60) return;
    if (!inp.getAttribute('data-ph')) inp.setAttribute('data-ph', full);
    var cs = getComputedStyle(inp), pick = full;
    if (full.length * parseFloat(cs.fontSize) * 0.62 > room) {        // may not fit: measure the wordings
      if (!cv) cv = document.createElement('canvas').getContext('2d');
      cv.font = cs.font;
      var v = variants(full); pick = v[v.length - 1];
      for (var i = 0; i < v.length; i++) if (cv.measureText(v[i]).width <= room) { pick = v[i]; break; }
    }
    if (inp.getAttribute('placeholder') !== pick) inp.setAttribute('placeholder', pick);
  }
  var ro = new ResizeObserver(function (entries) { entries.forEach(function (en) { fitOne(en.target, en.contentRect.width); }); });
  function watch() {
    Array.prototype.forEach.call(document.querySelectorAll('input[placeholder],input[data-ph]'), function (inp) {
      if (!inp.hasAttribute('data-ph-w')) { inp.setAttribute('data-ph-w', ''); ro.observe(inp); }
    });
  }
  watch();
  window.addEventListener('load', watch);
  if (document.fonts && document.fonts.ready) document.fonts.ready.then(function () {     // the web font changes the widths: measure again
    Array.prototype.forEach.call(document.querySelectorAll('input[data-ph-w]'), function (inp) { ro.unobserve(inp); ro.observe(inp); });
  });
})();

/* ---------- the site's own visit statistics (POST /api/public/ev in server/src/worker.js; the owner's page /stats/) ----------
   Anonymous and without cookies: a random id for this tab in sessionStorage (gone when the tab closes), nothing else. A visit is
   reported only after the first move of the mouse, scroll, key, touch, or 15 seconds with the tab in view, so scripts that load pages
   without a person mostly never start one. Reported: the page, where the visit came from (the referring site and utm), the language,
   clicks on Apply (company and the employer's host), searches and the result opened, buttons, links to other sites, job alerts asked
   for, resumes downloaded. Never what is typed into a form or a tool. The owner's browser leaves itself out once it opens /stats/.
   What it means for visitors is on the privacy page ("Counting visits"). */
(function () {
  var a = document.getElementById('hsign'), api = a ? (a.getAttribute('data-api') || '').replace(/\/+$/, '') : '';
  if (!api || !navigator.sendBeacon || /bot|crawl|spider|headless|lighthouse|pagespeed/i.test(navigator.userAgent) || navigator.webdriver) return;
  var ss, v, started;
  try { if (localStorage.getItem('hrn_nostats') === '1') return; ss = window.sessionStorage; v = ss.getItem('hrn_v'); started = ss.getItem('hrn_vs') === '1'; } catch (e) { return; }
  if (!v || !/^[a-z0-9]{8,32}$/.test(v)) {
    v = ''; var r = new Uint8Array(10); (window.crypto || window.msCrypto).getRandomValues(r);
    for (var i = 0; i < r.length; i++) v += ('0' + r[i].toString(16)).slice(-2);
    try { ss.setItem('hrn_v', v); ss.setItem('hrn_vs', ''); } catch (e) {}
    started = false;
  }
  var path = location.pathname, queue = [], q = new URLSearchParams(location.search), words = (q.get('q') || '').trim().slice(0, 100);
  function beacon(d) { try { navigator.sendBeacon(api + '/api/public/ev', JSON.stringify(d)); } catch (e) {} }
  function send(k, extra) {
    var d = { v: v, k: k, p: path };
    for (var x in extra) if (extra[x]) d[x] = String(extra[x]).slice(0, 200);
    if (started) beacon(d); else queue.push(d);
  }
  function start() {
    if (started) return;
    started = true;
    try { ss.setItem('hrn_vs', '1'); } catch (e) {}
    var u = {}; ['source', 'medium', 'campaign'].forEach(function (n) { var x = q.get('utm_' + n); if (x) u[n] = x.slice(0, 60); });
    var app = (window.matchMedia && matchMedia('(display-mode: standalone)').matches) || navigator.standalone ? 'app' : 'browser';
    beacon({ v: v, k: 'visit', p: path, r: document.referrer || '', u: u, l: navigator.language || '', m: app });
    setTimeout(function () { queue.forEach(beacon); queue = []; }, 400);       // the visit first, then what happened before it began
    ['mousemove', 'scroll', 'wheel', 'keydown', 'touchstart', 'pointerdown'].forEach(function (n) { removeEventListener(n, start, true); });
  }
  if (started) beacon({ v: v, k: 'pv', p: path });
  else {
    ['mousemove', 'scroll', 'wheel', 'keydown', 'touchstart', 'pointerdown'].forEach(function (n) { addEventListener(n, start, { capture: true, passive: true }); });
    var timer = null, arm = function () { if (!document.hidden && !timer && !started) timer = setTimeout(start, 15000); };
    document.addEventListener('visibilitychange', function () { if (document.hidden && timer) { clearTimeout(timer); timer = null; } else arm(); });
    arm();
  }
  if (words) send('search', { a: words });
  document.addEventListener('submit', function (e) { if (e.target && e.target.matches && e.target.matches('form.alertf')) send('alert'); }, true);
  document.addEventListener('click', function (e) {
    var t = e.target && e.target.closest ? e.target.closest('a, button, [role="button"], [data-ev]') : null;
    if (!t) return;
    var co = document.querySelector('.jhead .js a');
    if (t.id === 'apply' || t.hasAttribute('data-apply')) {
      var h = ''; try { h = new URL(t.href).hostname.replace(/^www\./, ''); } catch (x) {}
      return send('apply', { a: t.getAttribute('data-company') || (co ? co.textContent.trim() : ''), b: h });
    }
    if (/^rb-(print2?|doc2?)$/.test(t.id || '')) return send('resume', { a: t.id });
    if (t.tagName === 'A' && t.href) {
      var url; try { url = new URL(t.href, location.href); } catch (x) { return; }
      if (url.host && url.host !== location.host && /^https?:$/.test(url.protocol)) return send('out', { a: url.hostname.replace(/^www\./, '') });
      if (words && /\/job\/[^/]+\/?$/.test(url.pathname)) send('pick', { a: words, b: url.pathname });
      if (!t.hasAttribute('data-ev') && !/\bbtn\b/.test(t.className || '')) return;
    }
    var name = t.getAttribute('data-ev') || t.getAttribute('aria-label') || (t.textContent || '').replace(/\s+/g, ' ').trim() || t.id;
    if (name) send('btn', { a: name.slice(0, 60) });
  }, true);
})();

/* ---------- long grids of tiles (companies, places, fields): the first 12 shown, the rest behind "Show all N" (the links stay in the page) ---------- */
(function () {
  [].forEach.call(document.querySelectorAll('ul.tiles'), function (ul) {
    var items = ul.children;
    if (items.length <= 15 || ul.closest('[data-dirg]') || ul.classList.contains('cut')) return;
    ul.classList.add('cut');
    for (var i = 12; i < items.length; i++) items[i].classList.add('cut-x');
    var b = document.createElement('button');
    /* The companies directory carries the first employers in the page and loads the rest on demand (#cmore): one button opens both. */
    var cm = ul.id === 'clist' ? document.getElementById('cmore') : null;
    var total = items.length + (cm && !cm.hidden ? +(cm.getAttribute('data-n') || '0').replace(/,/g, '') : 0);
    if (cm) cm.hidden = true;
    b.type = 'button'; b.className = 'tiles-more'; b.textContent = 'Show all ' + String(total).replace(/\B(?=(\d{3})+(?!\d))/g, ',') + (cm ? ' employers' : '');      // commas by hand, as in the menu's count
    b.addEventListener('click', function () {
      ul.classList.remove('cut'); b.remove();
      if (cm && total > items.length) { cm.hidden = false; var mb = document.getElementById('cmorebtn'); if (mb) mb.click(); }
    });
    ul.parentNode.insertBefore(b, ul.nextSibling);
  });
})();

/* ---------- chart tooltips (26 Nov 2026): one small card for every bar, column and tick, on hover, tap or keyboard focus.
   A column or a tick carries data-tip "label · value · more"; a bar row (.hbars) gives its name and figure, a table bar
   (td.salbar) its row's name and figure. The figure leads, the label follows; text only (textContent), never markup.
   Every figure here is also on the page (labels, rows, a table), so the card adds nothing a reader cannot get without it. ---------- */
(function () {
  var tip, cur = null, root = document.documentElement;
  root.classList.add('vt');                                   // style.css then hides the CSS-only fallback tooltip
  function text(el) { return el ? (el.textContent || '').replace(/\s+/g, ' ').trim() : ''; }
  function target(n) {
    if (!n || !n.closest) return null;
    var t = n.closest('[data-tip],.hbars>a,.hbars>div,td');
    if (!t) return null;
    if (t.matches('.hbars>a,.hbars>div') && !t.querySelector('.hb')) return null;
    if (t.tagName === 'TD' && !t.querySelector(':scope>span.bar')) return null;
    return t;
  }
  function parts(t) {                                          // [figure, label, notes]
    if (t.hasAttribute('data-tip')) {
      var p = t.getAttribute('data-tip').split(' · ');
      return p.length > 1 ? [p[1], p[0], p.slice(2).join(' · ')] : [p[0], '', ''];
    }
    if (t.tagName === 'TD') {                                  // a bar in a table cell: the cell's figure, the row's name and the column's
      var row = t.parentNode, th = t.closest('table') && t.closest('table').querySelector('tr th:nth-child(' + (t.cellIndex + 1) + ')'), name = '';
      for (var i = 0; i < row.cells.length && !name; i++) if (!/^[#\d\s.]*$/.test(text(row.cells[i]))) name = text(row.cells[i]);      // the rank column is not the name
      return [text(t), name + (th ? ' · ' + text(th).toLowerCase() : ''), ''];
    }
    return [text(t.querySelector('.hc')), text(t.querySelector('.hn')), ''];
  }
  function mark(t) { return t.matches('.vc-c,.va,.vb') ? t.querySelector('i') : t.matches('.hbars>a,.hbars>div') ? t.querySelector('.hb i') : t.tagName === 'TD' ? t.querySelector('span.bar i') : t; }
  function show(t) {
    var p = parts(t);
    if (!p[0]) return hide();
    if (!tip) {
      tip = document.createElement('div'); tip.className = 'vtip'; tip.setAttribute('role', 'tooltip'); tip.id = 'vtip';
      document.body.appendChild(tip);
    }
    tip.textContent = '';
    var m = mark(t) || t, col = getComputedStyle(m).backgroundColor;
    if (!m.getClientRects().length || !m.offsetParent) return hide();          // the bar is not drawn here (a phone hides bars in tables)
    tip.style.setProperty('--k', col && col !== 'rgba(0, 0, 0, 0)' && col !== 'transparent' ? col : 'var(--viz-1)');
    var b = document.createElement('b'); b.textContent = p[0]; tip.appendChild(b);
    if (p[1]) { var s = document.createElement('span'); s.textContent = p[1]; tip.appendChild(s); }
    if (p[2]) { var n = document.createElement('em'); n.textContent = p[2]; tip.appendChild(n); }
    cur = t;
    var r = m.getBoundingClientRect(), horiz = t.matches('.hbars>a,.hbars>div,td,.va,.vb'), w = tip.offsetWidth, h = tip.offsetHeight;
    var lab = t.matches('.vc-c') && t.querySelector('b'), top0 = lab ? Math.min(r.top, lab.getBoundingClientRect().top) : r.top;      // above the column's own figure
    var x = horiz ? (t.matches('.va') ? r.left : r.right) : r.left + r.width / 2, y = top0 - 8;
    var left = Math.max(8, Math.min(innerWidth - w - 8, x - w / 2)), top = y - h;
    if (top < 8) top = r.bottom + 10;                          // no room above the mark: under it
    tip.style.left = Math.round(left) + 'px'; tip.style.top = Math.round(top) + 'px';
    tip.classList.add('on');
  }
  function hide() { cur = null; if (tip) tip.classList.remove('on'); }
  document.addEventListener('pointermove', function (ev) { var t = target(ev.target); if (t && t !== cur) show(t); else if (!t && cur) hide(); }, { passive: true });      // move, not over: after a scroll hid it, the next move shows it again
  document.addEventListener('pointerleave', hide, { passive: true });
  document.addEventListener('pointerdown', function (ev) { var t = target(ev.target); if (t) show(t); else hide(); }, { passive: true });
  document.addEventListener('focusin', function (ev) { var t = target(ev.target); if (t) show(t); else hide(); });
  document.addEventListener('focusout', function () { hide(); });
  document.addEventListener('keydown', function (ev) { if (ev.key === 'Escape') hide(); });
  addEventListener('scroll', function () { if (cur) hide(); }, { passive: true });
})();
