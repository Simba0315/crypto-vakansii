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
  function slugOf(s) { return String(s).toLowerCase().replace(/[^a-z0-9]+/g, '-').replace(/^-+|-+$/g, '').slice(0, 60).replace(/-+$/, ''); }
  // avatar markup: initial on a tinted square, with the company logo on top when there is one
  function avatar(company, logo, guess) {
    var letter = (String(company).match(/[A-Za-z0-9]/) || ['?'])[0].toUpperCase();
    var img = logo ? '<img src="' + P + '/logos/' + logo + '.png" alt="" loading="lazy">' : guess ? '<img src="' + P + '/logos/' + slugOf(company) + '.png" alt="" loading="lazy" onerror="this.remove()">' : '';
    return '<span class="ava' + (logo ? ' has' : '') + '" style="--h:' + hue(company) + '" aria-hidden="true">' + esc(letter) + img + '</span>';
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
  //       13 salaryHigh, 14 places, 15 crypto, 16 postedInt, 17 search text (lazy), 18 perks, 19 type, 20 anywhere]
  var cache, headCache;
  function expand(d) {
    var cslug = d.c.map(function (c) { return slugOf(c) || 'job'; });
    return d.r.map(function (r) {
        var c = d.c[r[2]], li = r[6], pi = r[9], s = r[0];
        if (typeof s !== 'string') { var b = (slugOf(r[1]) || 'job') + '-' + cslug[r[2]]; s = s ? b + '-' + s : b; }   // slug rebuilt from title and company
        return [s, r[1], c, r[3], r[4] & 1, d.k[r[5]], d.l[li], r[7].map(function (i) { return d.t[i]; }), r[8],
          pi ? MONTHS[Math.floor(pi / 100) % 100 - 1] + ' ' + (pi % 100) : '', li === 1 || li === 2 ? 1 : 0, r[4] & 2 ? 1 : 0, hue(c), r[10],
          r[11].map(function (i) { return d.p[i]; }), r[4] & 4 ? 1 : 0, pi, '',
          (r[12] || []).map(function (i) { return d.x[i]; }), d.e ? d.e[r[13] || 0] : '', r[4] & 8 ? 1 : 0, d.g && d.g[r[2]] ? slugOf(c) : '', r[4] & 16 ? 1 : 0];
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
      real: p.has('real'), realSince: since(90)          // "fresh openings only": no talent pools, nothing open 90+ days
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
  function ageOf(pi) {            // [label, fresh] from a yyyymmdd number
    if (!pi) return ['', false];
    var d = new Date(Math.floor(pi / 10000), Math.floor(pi / 100) % 100 - 1, pi % 100), now = new Date();
    var days = Math.max(0, Math.round((new Date(now.getFullYear(), now.getMonth(), now.getDate()) - d) / 864e5));
    return [days === 0 ? 'Today' : days < 14 ? days + 'd' : days < 60 ? Math.floor(days / 7) + 'w' : Math.floor(days / 30) + 'mo', days <= 2];
  }
  function card(j, more, badge) {
    var pills = (badge ? '<span class="pill acc">' + esc(badge) + '</span>' : '') + (j[11] ? '<span class="pill acc">Featured</span>' : '') +
      (j[8] ? '<span class="pill sal">' + esc(j[8].slice(0, 28)) + '</span>' : '') + (j[4] ? '<span class="pill ok">Remote</span>' : '') + (j[6] ? '<span class="pill">' + esc(j[6]) + '</span>' : '') +
      j[7].slice(0, 3).map(function (t) { return '<span class="pill">' + esc(t) + '</span>'; }).join('');
    var place = j[3].length > 60 ? j[3].slice(0, 57) + '…' : j[3];
    var ag = ageOf(j[16]);
    return '<li class="job' + (j[11] ? ' feat' : '') + '"><a href="' + P + '/job/' + j[0] + '/">' + avatar(j[2], j[21], false) +
      '<span><span class="jt">' + esc(j[1]) + '</span><span class="js">' + esc(j[2]) + (place ? ' · ' + esc(place) : '') +
      (more ? ' · +' + more + ' more location' + (more > 1 ? 's' : '') : '') + '</span></span>' +
      '<span class="jr"><span class="pills">' + pills + '</span><time' + (ag[1] ? ' class="new"' : '') + '>' + esc(ag[0]) + '</time></span></a></li>';
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
  HRN.bindJob = bindJob;
  bindJob(document);

  /* ---------- lists: saved / applied / viewed marks, faster navigation ---------- */
  decorate(document);
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
      if (lastSearch) html += '<li class="job"><a href="' + P + '/jobs/?' + esc(lastSearch.qs) + '"><span class="ava" aria-hidden="true">⌕</span><span><span class="jt">' + esc(lastSearch.label) + '</span><span class="js">Your saved search</span></span></a></li>';
      $('home-recent-list').innerHTML = html; recent.hidden = false;
    }
  }

  /* ---------- For you: skill profile and resume scan ---------- */
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
        // which single skill would open up the most roles you do not match yet
        var gain = {}, gap = $('fy-gap');
        all.forEach(function (j) {
          if (scores.has(j[0]) || !match(j, f)) return;
          j[7].forEach(function (t) { if (profile.skills.indexOf(t) < 0) gain[t] = (gain[t] || 0) + 1; });
        });
        var best = Object.keys(gain).sort(function (a, b) { return gain[b] - gain[a]; }).slice(0, 6);
        if (gap) {
          gap.hidden = !best.length;
          gap.innerHTML = best.length ? '<p class="flabel" style="margin:16px 0 8px">One more skill would open up</p><div class="skillbar">' + best.map(function (t) {
            return '<button class="chipbtn gapbtn" type="button" data-add="' + esc(t) + '">+ ' + esc(t) + ' · ' + gain[t].toLocaleString('en-US') + ' more roles</button>';
          }).join('') + '</div>' : '';
        }
      }).catch(function () { count.textContent = 'Could not load jobs. Please reload the page.'; });
    };
    fy.addEventListener('click', function (ev) {
      var c = ev.target.closest && ev.target.closest('#fy-skills .chipbtn');
      if (c) { var s = c.getAttribute('data-skill'), i = profile.skills.indexOf(s); if (i >= 0) profile.skills.splice(i, 1); else profile.skills.push(s); run(); return; }
      if (ev.target.id === 'fy-more') { shown += 40; render(); return; }
      if (ev.target.getAttribute('data-add')) { var add = ev.target.getAttribute('data-add'); if (profile.skills.indexOf(add) < 0) profile.skills.push(add); run(); return; }
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
