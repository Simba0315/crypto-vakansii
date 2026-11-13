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
    var img = logo ? '<img src="' + P + '/logos/' + logo + '.png" alt="" loading="lazy">' : guess ? '<img src="' + P + '/logos/' + slugOf(company) + '.png" alt="" loading="lazy" onerror="this.remove()">' : '';
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
  //       23 exact posting time in minutes since 1970 (0 when only the day is known or the job is over a week old)]
  var cache, headCache;
  function expand(d) {
    var cslug = d.c.map(function (c) { return slugOf(c) || 'job'; });
    return d.r.map(function (r) {
        var c = d.c[r[2]], li = r[6], pi = r[9], s = r[0];
        if (typeof s !== 'string') { var b = (slugOf(r[1]) || 'job') + '-' + cslug[r[2]]; s = s ? b + '-' + s : b; }   // slug rebuilt from title and company
        return [s, r[1], c, r[3], r[4] & 1, d.k[r[5]], d.l[li], r[7].map(function (i) { return d.t[i]; }), r[8],
          pi ? MONTHS[Math.floor(pi / 100) % 100 - 1] + ' ' + (pi % 100) : '', li === 1 || li === 2 ? 1 : 0, r[4] & 2 ? 1 : 0, hue(c), r[10],
          r[11].map(function (i) { return d.p[i]; }), r[4] & 4 ? 1 : 0, pi, '',
          (r[12] || []).map(function (i) { return d.x[i]; }), d.e ? d.e[r[13] || 0] : '', r[4] & 8 ? 1 : 0, d.g && d.g[r[2]] ? slugOf(c) : '', r[4] & 16 ? 1 : 0, r[14] || 0];
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
  function parse(qs) {
    var p = new URLSearchParams(qs || '');
    var sal = p.get('sal') ? Number(p.get('sal')) : (p.has('salary') ? 1 : 0), age = Number(p.get('age')) || 0;
    return {
      q: p.get('q') || '', words: (p.get('q') || '').toLowerCase().split(/\s+/).filter(Boolean),
      cat: p.get('cat') || '', lvl: p.get('lvl') || '', loc: p.get('loc') || '', sal: sal || 0, age: age, since: age ? since(age) : 0,
      remote: p.has('remote'), entry: p.has('entry'), crypto: p.has('crypto'), any: p.has('any'), perk: p.get('perk') || '', etype: p.get('etype') || '',
      skills: (p.get('skills') || '').split(',').filter(Boolean), sort: p.get('sort') || 'new',
      titles: p.has('ti'), nosal: p.has('nosal'), real: p.has('real'), realSince: since(90)          // "fresh openings only": no talent pools, nothing open 90+ days
    };
  }
  function match(j, f) {
    if (mute.c[j[2]]) return false;
    if (f.real && (j[22] || !(j[16] >= f.realSince))) return false;
    if (mute.w.length) { var low = j[1].toLowerCase(); for (var w = 0; w < mute.w.length; w++) if (low.indexOf(mute.w[w]) >= 0) return false; }
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
    if (f.sal > 1 && !(j[13] >= f.sal) && !(f.nosal && !j[8])) return false;      // "also show jobs that do not state pay" lets the unknowns through
    for (var i = 0; i < f.skills.length; i++) if (j[7].indexOf(f.skills[i]) < 0) return false;
    if (f.words.length) {
      var hay = f.titles ? j[1].toLowerCase() : j[17] || (j[17] = (j[1] + ' ' + j[2] + ' ' + j[3] + ' ' + j[7].join(' ')).toLowerCase());
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
  function card(j, more, badge) {
    var pills = (badge ? '<span class="pill acc">' + esc(badge) + '</span>' : '') + (j[11] ? '<span class="pill acc">Featured</span>' : '') +
      (j[4] ? '<span class="pill ok">Remote</span>' : '') + (j[6] ? '<span class="pill">' + esc(j[6]) + '</span>' : '') +
      j[7].slice(0, 3).map(function (t) { return '<span class="pill">' + esc(t) + '</span>'; }).join('');
    var place = j[3].length > 60 ? j[3].slice(0, 57) + '…' : j[3];
    var ag = ageOf(j[16]);
    return '<li class="job' + (j[11] ? ' feat' : '') + '"><a href="' + P + '/job/' + j[0] + '/">' + avatar(j[2], j[21], false) +
      '<span><span class="jt">' + esc(j[1]) + '</span><span class="js">' + esc(j[2]) + (place ? ' · ' + esc(place) : '') +
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
  window.HRN = { mute: mute, saveMute: function () { set('hrn_mute', mute); }, parse: parse, match: match, load: load, loadHead: loadHead, collapse: collapse, card: card, decorate: decorate, get: get, set: set, esc: esc, today: today, base: P };

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

  /* ---------- current section in the menu ---------- */
  var here = location.pathname.replace(P, '');
  document.querySelectorAll('#nav a.nl').forEach(function (a) {
    var path = (a.getAttribute('href') || '').replace(P, '');
    if (path.length > 1 && here.indexOf(path) === 0) a.setAttribute('aria-current', 'page');
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
      var any = 0, head = (b.querySelector('h2') || b).textContent.toLowerCase(), whole = !q || head.indexOf(q) >= 0;
      b.querySelectorAll('li').forEach(function (li) {
        var n = li.getAttribute('data-n'), hit = whole || (n != null && n.indexOf(q) >= 0);
        li.hidden = !hit; if (hit) any++;
      });
      b.hidden = !any; if (any) shown++;
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
  var cfilter = $('cfilter');
  if (cfilter) cfilter.addEventListener('input', function () {
    var q = cfilter.value.trim().toLowerCase(), shown = 0;
    document.querySelectorAll('#clist li').forEach(function (li) {
      var hit = !q || li.getAttribute('data-n').indexOf(q) >= 0;
      li.hidden = !hit; if (hit) shown++;
    });
    var none = $('cnone'); if (none) none.hidden = shown > 0;
  });
  /* companies page: sort by open roles, roles posted in the last 7 days, or name (buttons are hidden until this script runs) */
  var csort = $('csort'), clist = $('clist');
  if (csort && clist) {
    csort.hidden = false;
    csort.addEventListener('click', function (ev) {
      var b = ev.target.closest('button'); if (!b) return;
      var k = b.getAttribute('data-s'), items = Array.prototype.slice.call(clist.children);
      items.sort(function (a, z) {
        if (k === 'n') return a.getAttribute('data-n').localeCompare(z.getAttribute('data-n'));
        return (+z.getAttribute('data-' + k) - +a.getAttribute('data-' + k)) || (+z.getAttribute('data-o') - +a.getAttribute('data-o'));
      });
      var frag = document.createDocumentFragment(); items.forEach(function (li) { frag.appendChild(li); }); clist.appendChild(frag);
      csort.querySelectorAll('button').forEach(function (x) { x.setAttribute('aria-pressed', x === b ? 'true' : 'false'); });
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
          if (c[2] && c[1]) bits.push('<a href="' + P + '/locations/' + c[1] + '/">' + n(c[2]) + (c[2] === 1 ? ' job' : ' jobs') + ' in ' + esc(c[0]) + '</a>');
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
    if (shareRow && !shareRow.firstChild) shareRow.innerHTML = '<span>Share:</span><button class="linkbtn" id="copy" type="button">Copy link</button>' +
      ['LinkedIn', 'X', 'Telegram', 'WhatsApp', 'Reddit', 'Email'].map(function (n) { return '<button class="linkbtn" type="button" data-share="' + n.toLowerCase() + '">' + n + '</button>'; }).join('') +
      '<button class="linkbtn" id="hide" type="button">Not interested</button><button class="linkbtn" id="mute" type="button">Hide this company</button>';
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
      var done = function () { copy.textContent = 'Link copied'; setTimeout(function () { copy.textContent = 'Copy link'; }, 1600); };
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
    if (fit && profile.skills.length) {
      var tags = (fit.getAttribute('data-tags') || '').split('|').filter(Boolean);
      var hit = tags.filter(function (t) { return profile.skills.indexOf(t) >= 0; });
      if (tags.length) {
        fit.textContent = hit.length ? 'You match ' + hit.length + ' of ' + tags.length + ' listed skills: ' + hit.join(', ') + '.' : 'None of your saved skills are listed for this role.';
        fit.hidden = false;
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
    var after = q1('#apply-hint') || q1('.note.goes') || ap;
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
        var ics = ['BEGIN:VCALENDAR', 'VERSION:2.0', 'PRODID:-//Hiring Right Now//EN', 'BEGIN:VEVENT', 'UID:' + Date.now() + '@hrn', 'DTSTAMP:' + stamp(new Date()), 'DTSTART:' + stamp(d),
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
  if ('serviceWorker' in navigator && location.protocol === 'https:') navigator.serviceWorker.register(P + '/sw.js').catch(function () {});
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
    if (profile.exp == null) profile.exp = { Intern: '0', Junior: '0', Senior: '2', Lead: '3' }[profile.lvl] || '';
    if (profile.where == null) profile.where = profile.remote ? 'remote' : '';
    if (profile.pay == null) profile.pay = profile.sal > 1 ? profile.sal : 0;
    var chips = Array.prototype.slice.call(fy.querySelectorAll('#fy-skills .chipbtn'));
    var place = $('fy-place'), payIn = $('fy-pay-in'), noPay = $('fy-nopay'), list = $('fy-list'), count = $('fy-count'), more = $('fy-more'), jump = $('fy-jump');
    var payNote = $('fy-pay-note'), gap = $('fy-gap');
    var shown = 30, found = [], nFull = 0, extra = new Map(), why = new Map(), asked = 0, fromLink = false;
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
      var A = { cats: skip === 'work' ? [] : profile.cats, exp: skip === 'exp' || profile.exp === '' ? '' : Number(profile.exp),
        where: skip === 'where' ? '' : profile.where || '', slug: skip === 'where' || skip === 'country' || !o ? '' : o.getAttribute('data-s') || '', reg: o ? o.getAttribute('data-r') || '' : '',
        cname: o && o.value ? o.textContent : '', pay: skip === 'pay' ? 0 : profile.pay || 0, nopay: skip === 'pay' ? false : !!profile.nopay,
        skills: skip === 'skills' ? [] : profile.skills, set: set_ };
      A.n = (A.cats.length ? 1 : 0) + (A.exp !== '' ? 1 : 0) + (A.where || A.slug ? 1 : 0) + (A.pay || A.nopay ? 1 : 0) + (A.skills.length ? 1 : 0);
      return A;
    };
    // one job against the answers: null when it contradicts one, otherwise ticks, question marks and the reasons to show
    var judge = function (j, A) {
      if (mute.c[j[2]] || hidden[j[0]]) return null;
      if (mute.w.length) { var low = j[1].toLowerCase(); for (var w = 0; w < mute.w.length; w++) if (low.indexOf(mute.w[w]) >= 0) return null; }
      var ok = 0, half = 0, bits = [], k = 0, edge = 0, i;
      if (A.cats.length) { if (A.cats.indexOf(j[5]) < 0) return null; ok++; bits.push([1, catName[j[5]] || j[5]]); }
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
        res = A.where === 'remote' ? fromHome() : A.where === 'office' ? onSite() : onSite() || fromHome();
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
        html += card(j, extra.get(j[0]) || 0, '').replace(/<\/li>$/, line + '</li>');
      });
      list.innerHTML = html; more.hidden = found.length <= shown; decorate(list);
    };
    var run = function () {
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
        var full = profile.cats.length <= 1 && !profile.skills.length ? '<a href="' + P + '/jobs/?' + [profile.cats[0] ? 'cat=' + profile.cats[0] : '', profile.where === 'remote' ? 'remote' : '', A.slug ? 'loc=' + A.slug : '', A.pay ? 'sal=' + A.pay + (A.nopay ? '' : '&nosal') : ''].filter(Boolean).join('&') + '">Open the same in the full search</a>' : '';
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
        g.fillStyle = '#f6f5f0'; g.fillRect(0, 0, 1200, 630); g.fillStyle = '#b7eec3'; g.fillRect(0, 0, 1200, 14);
        g.fillStyle = '#0e0e0c'; g.font = '600 30px system-ui, sans-serif'; g.fillText('My job market · ' + new Date().toLocaleDateString('en-US', { month: 'long', day: 'numeric', year: 'numeric' }), 70, 96);
        g.font = '800 150px system-ui, sans-serif'; g.fillText(nf(nFull || found.length), 70, 270);
        g.font = '500 36px system-ui, sans-serif'; g.fillText((nFull ? 'open jobs fit all ' + asked + ' of my answers' : 'open jobs fit my answers in part'), 76, 326);
        g.fillStyle = '#55534c'; g.font = '500 28px system-ui, sans-serif';
        var lines = [profile.cats.length ? 'Work: ' + profile.cats.map(function (c) { return catName[c] || c; }).join(', ') : '', profile.where === 'remote' ? 'From home' : profile.where === 'office' ? 'At an office' : '',
          profile.pay ? 'Pay from ' + kfmt(profile.pay) + ' a year' : '', profile.skills.length ? 'Skills: ' + profile.skills.slice(0, 5).join(', ') : ''].filter(Boolean);
        lines.forEach(function (ln, i) { g.fillText(ln.slice(0, 70), 76, 392 + i * 40); });
        g.fillStyle = '#0e0e0c'; g.font = '600 28px system-ui, sans-serif';
        if (paid.length >= 5) g.fillText('Half of them pay up to ' + kfmt(paid[Math.floor(paid.length / 2)]) + ' or more', 700, 392);
        if (top.length) g.fillText('Hiring most: ' + top.join(', ').slice(0, 34), 700, 432);
        g.fillStyle = '#1f9d55'; g.fillRect(70, 560, 60, 6); g.fillStyle = '#0e0e0c'; g.font = '700 26px system-ui, sans-serif'; g.fillText('Hiring Right Now', 146, 572);
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
        profile = { skills: [], cats: [], exp: '', where: '', place: '', pay: 0, nopay: false };
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
    root.addEventListener('change', function (ev) {
      var row = ev.target.closest && ev.target.closest('.trow'); if (!row) return;
      var rec = jobs[row.getAttribute('data-s')]; if (!rec) return;
      if (ev.target.tagName === 'SELECT') { rec.st = ev.target.value; rec.sa = Date.now(); store(); draw(); }
      else if (ev.target.classList.contains('nt')) { rec.note = ev.target.value; store(); }
    });
    draw();
    if (Object.keys(jobs).length) load().then(function (index) { openSet = {}; index.forEach(function (j) { openSet[j[0]] = 1; }); draw(); }).catch(function () {});
    var hiddenNote = $('mj-hidden'), hiddenCount = Object.keys(hidden).length, mutedCos = Object.keys(mute.c);
    if (hiddenNote && (hiddenCount || mutedCos.length || mute.w.length)) {
      hiddenNote.innerHTML = [hiddenCount ? hiddenCount + (hiddenCount === 1 ? ' job' : ' jobs') : '', mutedCos.length ? 'these companies: ' + mutedCos.map(esc).join(', ') : '',
        mute.w.length ? 'titles with: ' + mute.w.map(esc).join(', ') : ''].filter(Boolean).join('; ') + ' — hidden from your lists. <button class="linkbtn" id="mj-unhide" type="button">Show everything again</button>';
      hiddenNote.hidden = false;
      $('mj-unhide').addEventListener('click', function () { hidden = {}; set('hrn_hidden', hidden); mute.c = {}; mute.w = []; set('hrn_mute', mute); hiddenNote.hidden = true; });
    }
    // your data: a copy to keep, a way to move it to another device, and a way to wipe it
    var KEYS = ['hrn_jobs', 'hrn_searches', 'hrn_follow', 'hrn_profile', 'hrn_mute', 'hrn_hidden', 'hrn_seen', 'hrn_resume'], dataNote = $('mj-data-note'), fileIn = $('mj-file');
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
        if (!window.confirm('Erase everything this site keeps in this browser: saved jobs, applications, notes, searches, hidden items, your skill profile, your resume and what you typed into the tools? This cannot be undone.')) return;
        try {
          Object.keys(localStorage).forEach(function (k) { if (KEYS.indexOf(k) >= 0 || k.indexOf('hrn_tool_') === 0) localStorage.removeItem(k); });
        } catch (e) {}
        location.reload();
      });
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
    var drawFollows = function (index) {
      $('fc-empty').hidden = fkeys.length > 0;
      $('fc-list').innerHTML = fkeys.map(function (k) {
        var fresh = '';
        if (index) {
          var n = 0, total = 0;
          for (var i = 0; i < index.length; i++) if (slugOf(index[i][2]) === k) { total++; if (index[i][16] > follows[k].seen) n++; }
          fresh = (n ? '<span class="pill ok">' + n + ' new</span>' : '') + '<span class="pill">' + total + ' open</span>';
        }
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
    if (searches.length || fkeys.length) load().then(function (index) { if (searches.length) drawSearches(index); if (fkeys.length) drawFollows(index); }).catch(function () {});
  }
})();
