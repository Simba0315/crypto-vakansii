/* Free tools (/tools/…): calculators, text checkers and template writers that run entirely in the visitor's browser.
   Part 1 is pure logic (the same code is loaded by the Node tests). Part 2 wires each tool page.
   Nothing typed here is sent anywhere; form state lives in localStorage under hrn_tool_* keys. */
(function () {
  'use strict';
  var T = {};

  /* ================================================================ part 1: logic ================================================================ */

  /* ---------- numbers ---------- */
  // "85,000", "$85k", "1.2m", "12,5", "5%" -> number; anything else -> NaN
  function num(v) {
    if (typeof v === 'number') return isFinite(v) ? v : NaN;
    var s = String(v == null ? '' : v).toLowerCase().replace(/[\s$€£₹¥%_]/g, '').replace(/usd|eur|gbp|cad|aud|chf|inr/g, '');
    if (!s) return NaN;
    var mult = 1, m = s.match(/^(.*?\d)(k|m|mm|b|bn)$/);
    if (m) { s = m[1]; mult = m[2] === 'k' ? 1e3 : m[2] === 'b' || m[2] === 'bn' ? 1e9 : 1e6; }
    if (/^-?\d{1,3}(,\d{3})+(\.\d+)?$/.test(s)) s = s.replace(/,/g, '');
    else if (/^-?\d{1,3}(\.\d{3})+(,\d+)?$/.test(s)) s = s.replace(/\./g, '').replace(',', '.');
    else if (/^-?\d+,\d{1,2}$/.test(s)) s = s.replace(',', '.');
    else s = s.replace(/,/g, '');
    if (!/^-?(\d+\.?\d*|\.\d+)$/.test(s)) return NaN;
    return parseFloat(s) * mult;
  }
  function pos(v) { var n = num(v); return n > 0 ? n : 0; }          // a missing or negative amount counts as zero
  function roundTo(x, d) {                                            // half away from zero, without binary noise (1.005 -> 1.01)
    var m = Math.pow(10, d || 0), r = Math.round(parseFloat((Math.abs(x) * m).toPrecision(12))) / m;
    return r === 0 ? 0 : (x < 0 ? -r : r);
  }
  function fmt(x, d) {
    if (typeof x !== 'number' || !isFinite(x)) return '—';
    return roundTo(x, d || 0).toLocaleString('en-US', { minimumFractionDigits: 0, maximumFractionDigits: d || 0 });
  }
  function money(x, sym, d) {
    if (typeof x !== 'number' || !isFinite(x)) return '—';
    var r = roundTo(x, d || 0);
    return (r < 0 ? '−' : '') + (sym || '') + Math.abs(r).toLocaleString('en-US', { minimumFractionDigits: d || 0, maximumFractionDigits: d || 0 });
  }
  function plain(x, d) { return String(roundTo(x, d == null ? 2 : d)); }   // value for an input box: no separators
  function mod(a, n) { return ((a % n) + n) % n; }
  function clean(s) { return String(s == null ? '' : s).replace(/\s+/g, ' ').trim(); }
  T.num = num; T.pos = pos; T.roundTo = roundTo; T.fmt = fmt; T.money = money; T.plain = plain;

  /* ---------- pay converter ---------- */
  // One figure in any unit -> all units. A year is hoursWeek × weeksYear paid hours; a month is a twelfth of the year.
  T.convertPay = function (amount, period, hoursWeek, weeksYear, daysWeek) {
    var a = num(amount), h = num(hoursWeek), w = num(weeksYear), d = num(daysWeek);
    if (!(a >= 0) || !(h > 0 && h <= 168) || !(w > 0 && w <= 52) || !(d > 0 && d <= 7)) return null;
    var hoursYear = h * w, daysYear = d * w;
    var year = period === 'hour' ? a * hoursYear : period === 'day' ? a * daysYear : period === 'week' ? a * w : period === 'month' ? a * 12 : a;
    return { hour: year / hoursYear, day: year / daysYear, week: year / w, month: year / 12, year: year, hoursYear: hoursYear, daysYear: daysYear };
  };

  /* ---------- pay raise ---------- */
  // o.by says which figure the visitor typed last: 'pct', 'amount' or 'next' (the new salary); the other two follow from it.
  T.raise = function (o) {
    var cur = num(o.current); if (!(cur > 0)) return null;
    var pct, amt, next;
    if (o.by === 'amount') { amt = num(o.amount); if (isNaN(amt)) return null; next = cur + amt; pct = amt / cur * 100; }
    else if (o.by === 'next') { next = num(o.next); if (isNaN(next)) return null; amt = next - cur; pct = amt / cur * 100; }
    else { pct = num(o.pct); if (isNaN(pct)) return null; amt = cur * pct / 100; next = cur + amt; }
    if (next < 0) return null;
    var per = num(o.periods); if (!(per > 0)) per = 12;
    var r = { current: cur, pct: pct, amount: amt, next: next, periods: per, payBefore: cur / per, payAfter: next / per, payDiff: amt / per, monthDiff: amt / 12 };
    var inf = num(o.inflation);
    if (!isNaN(inf) && inf > -100) {            // what the new salary buys in old money
      r.inflation = inf;
      r.realPct = ((1 + pct / 100) / (1 + inf / 100) - 1) * 100;
      r.realAmount = next / (1 + inf / 100) - cur;
    }
    return r;
  };

  /* ---------- job offers ---------- */
  // Yearly value = base + bonus + equity vesting per year + retirement match + other benefits − commute cost.
  // 260 working days (52 × 5) minus paid days off; commute is paid on the weeks actually worked.
  T.offer = function (o) {
    var base = pos(o.base), b = String(o.bonus == null ? '' : o.bonus);
    var bonus = /%\s*$/.test(b) ? base * pos(b) / 100 : pos(b);
    var equity = pos(o.equity), sign = pos(o.signon), other = pos(o.other);
    var match = base * Math.min(pos(o.match), 100) / 100;
    var pto = Math.min(pos(o.pto), 260), workDays = 260 - pto;
    var commute = Math.min(pos(o.cdays), 5) * pos(o.ccost) * workDays / 5;
    var yearly = base + bonus + equity + match + other - commute;
    return { name: clean(o.name), base: base, bonus: bonus, equity: equity, match: match, other: other, commute: commute, signon: sign, pto: pto, workDays: workDays,
      yearly: yearly, first: yearly + sign, perDay: workDays > 0 ? yearly / workDays : 0, filled: base > 0 || bonus > 0 || equity > 0 || other > 0 };
  };
  T.compareOffers = function (list) {
    var offers = list.map(T.offer), best = -1, bestFirst = -1, bestDay = -1;
    offers.forEach(function (o, i) {
      if (!o.filled) return;
      if (best < 0 || o.yearly > offers[best].yearly) best = i;
      if (bestFirst < 0 || o.first > offers[bestFirst].first) bestFirst = i;
      if (bestDay < 0 || o.perDay > offers[bestDay].perDay) bestDay = i;
    });
    var filled = offers.filter(function (o) { return o.filled; });
    var second = null;
    filled.forEach(function (o) { if (o !== offers[best] && (!second || o.yearly > second.yearly)) second = o; });
    return { offers: offers, best: best, bestFirst: bestFirst, bestDay: bestDay, count: filled.length,
      lead: second ? offers[best].yearly - second.yearly : 0, leadPct: second && second.yearly > 0 ? (offers[best].yearly - second.yearly) / second.yearly * 100 : null, second: second };
  };

  /* ---------- stock options ---------- */
  // Vesting with a cliff: nothing before the cliff, then a straight line by whole months (rounded down) until the end.
  T.vested = function (n, months, total, cliff) {
    n = Math.max(0, n);
    if (!(total > 0)) return n;
    months = Math.max(0, months);
    if (months < (cliff || 0)) return 0;
    if (months >= total) return n;
    return Math.floor(n * Math.floor(months) / total);
  };
  // Each future round that sells a fraction d of the company leaves old holders with (1 − d) of their stake.
  // Exit price per share = today's price × exit multiple × (1 − d)^rounds. Value = options × max(0, exit price − strike).
  T.equity = function (o) {
    var n = pos(o.options), strike = pos(o.strike), fd = pos(o.fdShares), val = pos(o.valuation), price = pos(o.price);
    if (o.mode === 'valuation') price = fd > 0 && val > 0 ? val / fd : 0;
    else val = fd > 0 && price > 0 ? price * fd : 0;
    if (!(n > 0) || !(price > 0)) return null;
    var rounds = Math.min(Math.floor(pos(o.rounds)), 20), dil = Math.min(pos(o.dilution), 99) / 100;
    var retained = Math.pow(1 - dil, rounds), spread = Math.max(0, price - strike), own = fd > 0 && n <= fd ? n / fd : null;
    var vestMonths = pos(o.vestYears) * 12, monthsIn = num(o.monthsIn), vest = null;
    if (!isNaN(monthsIn) && monthsIn >= 0) {
      var vn = T.vested(n, monthsIn, vestMonths, pos(o.cliffMonths));
      vest = { options: vn, value: vn * spread, cost: vn * strike, pct: vn / n * 100 };
    }
    var scenarios = (o.multiples || []).map(num).filter(function (m) { return m >= 0; }).map(function (m) {
      var p = price * m * retained;
      return { multiple: m, exitValuation: val > 0 ? val * m : null, price: p, gross: n * p, net: n * Math.max(0, p - strike), ownership: own == null ? null : own * retained };
    });
    return { options: n, strike: strike, price: price, valuation: val || null, ownership: own, retained: retained, rounds: rounds, spread: spread, paper: n * spread, cost: n * strike,
      vest: vest, scenarios: scenarios, breakEven: retained > 0 ? strike / (price * retained) : null, perYear: vestMonths > 0 ? n * spread / (vestMonths / 12) : null };
  };

  /* ---------- time zones ---------- */
  // Minutes east of UTC for an IANA zone at a given moment, read from the browser's own time zone database.
  T.tzOffset = function (tz, date) {
    var d = date || new Date(), p = {};
    new Intl.DateTimeFormat('en-US', { timeZone: tz, hourCycle: 'h23', year: 'numeric', month: 'numeric', day: 'numeric', hour: 'numeric', minute: 'numeric', second: 'numeric' })
      .formatToParts(d).forEach(function (x) { p[x.type] = x.value; });
    return Math.round((Date.UTC(+p.year, +p.month - 1, +p.day, +p.hour % 24, +p.minute, +p.second) - d.getTime()) / 60000);
  };
  // A working day given in local minutes (end before start = overnight shift) as one or two stretches of the UTC day.
  T.dayIntervals = function (start, end, off) {
    if (!(isFinite(start) && isFinite(end) && isFinite(off))) return [];
    if (end - start >= 1440) return [[0, 1440]];
    var len = mod(end - start, 1440);
    if (!len) return [];
    var a = mod(start - off, 1440), b = a + len;
    return b <= 1440 ? [[a, b]] : [[a, 1440], [0, b - 1440]];
  };
  T.intersect = function (A, B) {
    var out = [];
    A.forEach(function (a) { B.forEach(function (b) { var lo = Math.max(a[0], b[0]), hi = Math.min(a[1], b[1]); if (lo < hi) out.push([lo, hi]); }); });
    return out.sort(function (x, y) { return x[0] - y[0]; });
  };
  // people: [{start, end, off}] in minutes. Returns the shared time in UTC minutes; `blocks` joins a stretch that runs through midnight UTC.
  T.overlap = function (people) {
    var cur = [[0, 1440]];
    people.forEach(function (p) { cur = T.intersect(cur, T.dayIntervals(p.start, p.end, p.off)); });
    var minutes = cur.reduce(function (s, x) { return s + x[1] - x[0]; }, 0);
    var blocks = cur.map(function (x) { return { start: x[0], len: x[1] - x[0] }; });
    if (blocks.length > 1 && cur[0][0] === 0 && cur[cur.length - 1][1] === 1440) { var last = blocks.pop(); blocks[0] = { start: last.start, len: last.len + blocks[0].len }; }
    return { utc: cur, minutes: minutes, blocks: blocks };
  };
  // UTC stretches moved into a zone's local day (split again where they pass local midnight): used to draw the 24-hour bar.
  T.shift = function (ints, off) {
    var out = [];
    ints.forEach(function (x) {
      var a = mod(x[0] + off, 1440), b = a + (x[1] - x[0]);
      if (b <= 1440) out.push([a, b]); else { out.push([a, 1440]); out.push([0, b - 1440]); }
    });
    return out.sort(function (x, y) { return x[0] - y[0]; });
  };
  T.hm = function (m, h12) {
    m = mod(Math.round(m), 1440);
    var h = Math.floor(m / 60), mm = m % 60, z = (mm < 10 ? '0' : '') + mm;
    if (!h12) return (h < 10 ? '0' : '') + h + ':' + z;
    return (h % 12 || 12) + (mm ? ':' + z : '') + (h < 12 ? ' am' : ' pm');
  };
  T.dur = function (m) {
    m = Math.round(m); var h = Math.floor(m / 60), mm = m % 60;
    return h && mm ? h + ' h ' + mm + ' min' : h ? h + (h === 1 ? ' hour' : ' hours') : mm + ' min';
  };
  T.utcLabel = function (off) {
    var a = Math.abs(off), h = Math.floor(a / 60), m = a % 60;
    return 'UTC' + (off < 0 ? '−' : '+') + h + (m ? ':' + (m < 10 ? '0' : '') + m : '');
  };

  /* ---------- text helpers shared by the resume and job description checkers ---------- */
  var STOP = {};
  ('a about above across after again against all also am an and any are as at be because been before being below between both but by can could did do does doing don doesn ' +
   'down during each either else ever every few for from further get got had has have having he her here hers him his how i if in into is isn it its just may me might more most ' +
   'much must my no nor not of off on once only or other our ours out over own per same she should so some such than that the their theirs them then there these they this those ' +
   'through to too under until up upon us very via was we were what when where which while who whom why will with within without would won you your yours ' +
   // words that almost every job posting uses: they say nothing about a particular role
   'ability able applicant applicants apply based benefits best candidate candidates company day days environment equal employer employment etc experience experienced fast good ' +
   'great help helping high highly ideal ideally include includes including job join key knowledge level like looking make making need needs new opportunity opportunities part ' +
   'people plus position preferred proven qualifications related relevant required requirement requirements responsibilities responsible role roles skill skills strong team teams ' +
   'time understanding use using well work working world year years').split(' ').forEach(function (w) { STOP[w] = 1; });

  // Light stemming so that "manage", "managed" and "managing" count as one word. Not linguistics, just enough for matching.
  function stem(w) {
    w = w.replace(/[-.]/g, '');
    if (!/^[a-z]+$/.test(w)) return w;
    if (w.length > 3) {
      if (/ies$/.test(w)) w = w.slice(0, -3) + 'y';
      else if (/sses$/.test(w)) w = w.slice(0, -2);
      else if (/[^s]s$/.test(w) && !/(us|sis)$/.test(w)) w = w.slice(0, -1);
    }
    if (w.length > 5) {
      var cut = /ing$/.test(w) ? 3 : /ed$/.test(w) ? 2 : 0;
      if (cut) { w = w.slice(0, -cut); if (/([^aeiouylsz])\1$/.test(w)) w = w.slice(0, -1); }
    }
    if (w.length > 4 && /e$/.test(w)) w = w.slice(0, -1);
    return w;
  }
  Object.keys(STOP).forEach(function (w) { STOP[stem(w)] = 1; });
  function segments(text) {
    return String(text || '').toLowerCase().replace(/([a-z])[’'][a-z]*/g, '$1').replace(/\bend to end\b/g, 'end-to-end')
      .split(/[\n\r]+|[;:!?()\[\]{}•·|,"“”‘’'/]+|\.(?=\s|$)|\s[-–—]+\s/)
      .map(function (s) { return s.match(/[a-z0-9][a-z0-9+#.\-]*[a-z0-9+#]|[a-z0-9]/g) || []; })
      .filter(function (a) { return a.length; });
  }
  function wordCount(text) { return (String(text || '').match(/[A-Za-z0-9À-ɏ][A-Za-z0-9À-ɏ'’+#.\-]*/g) || []).length; }
  // Counts of single words and of neighbouring word pairs, keyed by stem; remembers the spelling seen most often.
  function grams(text) {
    var uni = {}, bi = {}, order = 0;
    function add(map, k, surface) { var x = map[k] || (map[k] = { n: 0, forms: {}, at: order++ }); x.n++; x.forms[surface] = (x.forms[surface] || 0) + 1; }
    segments(text).forEach(function (seg) {
      var prev = null;
      seg.forEach(function (t) {
        var k = stem(t);
        if (/^[0-9.+\-]+$/.test(t) || STOP[t] || STOP[k] || k.length < 2) { prev = null; return; }
        add(uni, k, t);
        if (prev) add(bi, prev.k + ' ' + k, prev.t + ' ' + t);
        prev = { k: k, t: t };
      });
    });
    return { uni: uni, bi: bi };
  }
  function topForm(x) { return Object.keys(x.forms).sort(function (a, b) { return x.forms[b] - x.forms[a] || a.length - b.length; })[0]; }
  T.stem = stem; T.wordCount = wordCount;

  /* ---------- resume vs job description ---------- */
  T.compilePats = function (list) {       // [[name, regexSource], …] from /data/skills.json -> [[name, RegExp], …]
    var out = [];
    (list || []).forEach(function (p) { try { out.push([p[0], new RegExp(p[1], 'i')]); } catch (e) {} });
    return out;
  };
  T.findSkills = function (text, pats) { return pats.filter(function (p) { return p[1].test(text); }).map(function (p) { return p[0]; }); };
  // Words and two-word phrases the posting repeats (twice or more), minus anything already covered by the skills list.
  T.keyTerms = function (text, pats, limit) {
    var g = grams(text), out = [], used = {};
    Object.keys(g.bi).forEach(function (k) {
      var x = g.bi[k]; if (x.n < 2) return;
      out.push({ key: k, term: topForm(x), n: x.n, at: x.at });
      k.split(' ').forEach(function (p) { used[p] = (used[p] || 0) + x.n; });
    });
    Object.keys(g.uni).forEach(function (k) {
      var x = g.uni[k], n = x.n - (used[k] || 0);
      if (n >= 2) out.push({ key: k, term: topForm(x), n: n, at: x.at });
    });
    out = out.filter(function (t) { return !(pats || []).some(function (p) { return p[1].test(t.term) || p[1].test(' ' + t.term + ' '); }); });
    out.sort(function (a, b) { return b.n - a.n || a.at - b.at; });
    return out.slice(0, limit || 20);
  };
  T.matchResume = function (resume, jd, pats, title) {
    pats = pats || [];
    var rw = wordCount(resume), jw = wordCount(jd);
    if (rw < 30 || jw < 30) return { error: rw < 30 ? 'resume' : 'jd', resumeWords: rw, jdWords: jw };
    var jdSkills = T.findSkills(jd, pats), cvSkills = T.findSkills(resume, pats);
    var matched = jdSkills.filter(function (s) { return cvSkills.indexOf(s) >= 0; }), missing = jdSkills.filter(function (s) { return cvSkills.indexOf(s) < 0; });
    var rg = grams(resume), has = {};
    Object.keys(rg.uni).forEach(function (k) { has[k] = 1; });
    Object.keys(rg.bi).forEach(function (k) { has[k.replace(' ', '')] = 1; });
    var terms = T.keyTerms(jd, pats, 20), wAll = 0, wHit = 0;
    terms.forEach(function (t) {
      var parts = t.key.split(' ');
      t.found = parts.length > 1 ? !!((has[parts[0]] && has[parts[1]]) || has[parts.join('')]) : !!has[t.key];
      var w = Math.min(t.n, 5); wAll += w; if (t.found) wHit += w;
    });
    var sPart = jdSkills.length ? matched.length / jdSkills.length : null, tPart = wAll ? wHit / wAll : null;
    var score = sPart != null && tPart != null ? 0.6 * sPart + 0.4 * tPart : sPart != null ? sPart : tPart;
    if (score == null) return { error: 'thin', resumeWords: rw, jdWords: jw };
    score = Math.round(score * 100);
    var fixes = [], missTerms = terms.filter(function (t) { return !t.found; });
    if (missing.length) fixes.push({ t: 'Name the missing skills, if you have them', d: 'The posting asks for ' + andList(missing.slice(0, 8)) + (missing.length > 8 ? ' and ' + (missing.length - 8) + ' more' : '') +
      ', and your resume never mentions ' + (missing.length === 1 ? 'it' : 'them') + '. If you have used ' + (missing.length === 1 ? 'it' : 'any of them') + ', write the exact word in your skills line and in the job where you used it. If you have not, leave it out.' });
    if (missTerms.length) fixes.push({ t: 'Use the posting’s own words', d: 'These terms are repeated in the posting and absent from your resume: ' + missTerms.slice(0, 6).map(function (t) { return '“' + t.term + '”'; }).join(', ') +
      '. Where they describe work you really did, say it in the same words.' });
    var ttl = clean(title);
    if (ttl) {
      var lack = [];
      segments(ttl).forEach(function (seg) { seg.forEach(function (t) { var k = stem(t); if (!STOP[t] && !STOP[k] && k.length > 1 && !has[k] && lack.indexOf(t) < 0) lack.push(t); }); });
      if (lack.length) fixes.push({ t: 'Echo the job title', d: 'The title “' + ttl + '” is not in your resume (missing: ' + lack.join(', ') + '). If it describes your work honestly, use the same title in your headline or summary.' });
    }
    var figures = (String(resume).match(/[$€£]\s?\d[\d,.]*\s?[kmb]?\b|\d[\d,.]*\s?(?:%|percent\b|[xkm]\b)|\b\d{1,3}(?:,\d{3})+\b|\b\d+\+?\s(?:users|customers|clients|people|engineers|developers|members|reports|projects|services|teams|countries|requests|transactions|hours|days|weeks|ms|seconds|minutes)\b/gi) || []).length;
    if (figures < 3) fixes.push({ t: 'Put numbers on your results', d: 'We found ' + (figures ? 'only ' + figures : 'no') + ' measurable result' + (figures === 1 ? '' : 's') + ' in your resume (percentages, money, counts). Say how much faster, how many users, how large the budget or the team.' });
    if (rw < 200) fixes.push({ t: 'Your resume text is short', d: 'It has ' + rw + ' words. Check that the whole text was pasted, or describe each job in more detail: what you built, with what, and what changed.' });
    else if (rw > 1200) fixes.push({ t: 'Your resume text is long', d: 'It has ' + fmt(rw) + ' words, more than two pages in most layouts. Cut older roles down to a line each and keep the detail for work that matches this posting.' });
    if (!fixes.length) fixes.push({ t: 'Nothing important is missing', d: 'Every skill and repeated term we found in the posting is in your resume. Spend the remaining time on the first lines of the page: that is what gets read.', ok: true });
    return { score: score, label: score >= 75 ? 'Strong match' : score >= 50 ? 'Partial match' : 'Weak match', matched: matched, missing: missing, jdSkills: jdSkills.length,
      terms: terms, termsFound: terms.length - missTerms.length, fixes: fixes, resumeWords: rw, jdWords: jw, figures: figures };
  };

  /* ---------- letters: shared wording helpers ---------- */
  function sentence(s) { s = clean(s); if (!s) return ''; s = s.charAt(0).toUpperCase() + s.slice(1); return /[.!?]$/.test(s) ? s : s + '.'; }
  function andList(a) { return a.length <= 1 ? (a[0] || '') : a.slice(0, -1).join(', ') + ' and ' + a[a.length - 1]; }
  function article(w) {
    var f = String(w).split(/\s+/)[0] || '';
    if (/^[A-Z]{2,}$/.test(f)) return /^[AEFHILMNORSX]/.test(f) ? 'an' : 'a';       // an SRE, a UX designer
    return /^[aeiou]/i.test(f) && !/^(uni|use|user|usab|one\b|euro)/i.test(f) ? 'an' : 'a';
  }
  function yearsText(y) { y = clean(y).replace(/\s*(years?|yrs?)\.?$/i, ''); return y ? y + (y === '1' ? ' year' : ' years') : ''; }
  T.andList = andList; T.article = article;

  /* ---------- cover letter (fill-in template, three tones) ---------- */
  T.coverLetter = function (f) {
    f = f || {};
    var tone = f.tone === 'warm' || f.tone === 'formal' ? f.tone : 'direct';
    var name = clean(f.name) || '[Your name]', title = clean(f.title) || '[job title]', company = clean(f.company) || '[company]';
    var manager = clean(f.manager), source = clean(f.source), current = clean(f.current), years = yearsText(f.years), contact = clean(f.contact);
    var skills = clean(f.skills).split(/\s*[,;]\s*/).filter(Boolean).slice(0, 5), ach = sentence(f.achievement), why = sentence(f.why);
    var pick = function (direct, warm, formal) { return tone === 'warm' ? warm : tone === 'formal' ? formal : direct; };
    var greet = manager ? pick('Dear ', 'Hello ', 'Dear ') + manager + ',' : pick('Dear Hiring Manager,', clean(f.company) ? 'Hello ' + company + ' team,' : 'Hello,', 'Dear Hiring Manager,');
    var open = pick('I am applying for the ' + title + ' role at ' + company + '.' + (source ? ' I found the opening on ' + source + '.' : ''),
      'I was glad to see the ' + title + ' opening at ' + company + (source ? ' on ' + source : '') + ', and I would love to be considered for it.',
      'I am writing to apply for the position of ' + title + ' at ' + company + (source ? ', as advertised on ' + source : '') + '.');
    var bg = [], role = current ? article(current) + ' ' + current : '';
    if (current && years) bg.push(pick('I am ' + role + ' with ' + years + ' of experience.', 'I have spent ' + years + ' in this field and currently work as ' + role + '.', 'I am ' + role + ' with ' + years + ' of professional experience.'));
    else if (current) bg.push(pick('I work as ' + role + '.', 'I currently work as ' + role + '.', 'I am currently employed as ' + role + '.'));
    else if (years) bg.push(pick('I have ' + years + ' of relevant experience.', 'I have spent ' + years + ' doing this kind of work.', 'I bring ' + years + ' of relevant professional experience.'));
    if (skills.length) bg.push(pick('My strongest skills are ', 'The work I enjoy most draws on ', 'My principal areas of expertise are ') + andList(skills) + '.');
    var paras = [greet, open];
    if (bg.length) paras.push(bg.join(' '));
    if (ach) paras.push(pick('One result that shows how I work: ', 'A piece of work I am proud of: ', 'A representative example of my work: ') + ach);
    if (why) paras.push(pick('Why ' + company + '? ', company + ' stands out to me. ', 'My interest in ' + company + ' is specific. ') + why);
    paras.push(pick('I would be glad to walk you through my work in a short call.' + (contact ? ' You can reach me at ' + contact + '.' : '') + ' Thank you for your time.',
      'I would really enjoy talking about how I could contribute to the team.' + (contact ? ' The best way to reach me is ' + contact + '.' : '') + ' Thank you for reading, and I hope to hear from you.',
      'I would welcome the opportunity to discuss my application at your convenience.' + (contact ? ' I can be reached at ' + contact + '.' : '') + ' Thank you for your consideration.'));
    paras.push(pick('Best regards,', 'Warm regards,', 'Yours sincerely,') + '\n' + name);
    return paras.join('\n\n').replace(/([^.])\.\.(?!\.)/g, '$1.');      // "Acme Inc." at the end of a sentence must not give "Inc.."
  };

  /* ---------- salary negotiation email (fill-in template) ---------- */
  T.negotiationEmail = function (f) {
    f = f || {};
    var sc = f.scenario === 'raise' || f.scenario === 'time' ? f.scenario : 'counter', tone = f.tone === 'firm' || f.tone === 'brief' ? f.tone : 'collaborative';
    var sym = f.cur == null ? '$' : f.cur, name = clean(f.name) || '[Your name]', to = clean(f.to), company = clean(f.company) || '[company]', title = clean(f.title) || '[job title]';
    var offer = num(f.offer), target = num(f.target), deadline = clean(f.deadline);
    var offerT = offer > 0 ? money(offer, sym, 0) : sc === 'raise' ? '[current salary]' : '[offered salary]', targetT = target > 0 ? money(target, sym, 0) : '[the figure you want]';
    var pct = offer > 0 && target > 0 ? (target - offer) / offer * 100 : null;
    var reasons = String(f.reasons || '').split(/\n+/).map(function (l) { return clean(l.replace(/^\s*(?:[-•*]\s*|\d{1,2}[.)]\s+)/, '')); }).filter(Boolean).slice(0, 5);
    var extras = (f.extras || []).filter(Boolean), ex = extras.length ? (extras.length > 1 ? extras.slice(0, -1).join(', ') + ' or ' + extras[extras.length - 1] : extras[0]) : '';
    var bullets = reasons.length ? reasons.map(function (r) { return '- ' + r; }).join('\n') : '- [Add one or two reasons: results you delivered, the scope of the role, pay data for similar roles, another offer]';
    var pick = function (collab, firm, brief) { return tone === 'firm' ? firm : tone === 'brief' ? brief : collab; };
    var greet = to ? 'Hi ' + to + ',' : 'Hello,', subject, p = [greet];
    if (sc === 'counter') {
      subject = title + ' offer: a question about the salary';
      p.push(pick('Thank you for the offer to join ' + company + ' as ' + title + '. I am excited about the role and I would like to find a way to say yes.',
        'Thank you for the offer to join ' + company + ' as ' + title + '. I want to accept, and there is one point to settle first.',
        'Thank you for the offer for the ' + title + ' role at ' + company + '. I would like to accept.'));
      if (tone === 'brief') p.push('Could you raise the base salary from ' + offerT + ' to ' + targetT + '?' + (reasons.length ? ' My reasons: ' + reasons.map(function (r) { return r.replace(/[.;]+$/, ''); }).join('; ') + '.' : ''));
      else p.push(pick('The one point I would like to discuss is the base salary. The offer is ' + offerT + ', and I was hoping for ' + targetT + '. Here is what that figure is based on:',
        'The base salary of ' + offerT + ' is below what I can accept for this role. I would be ready to sign at ' + targetT + '. My reasons:', '') + '\n\n' + bullets);
      if (ex) p.push(pick('If the base salary cannot move that far, I am open to closing the gap another way, for example with ' + ex + '.',
        'If the base salary is fixed, I would consider ' + ex + ' to make up the difference.', 'If the base cannot move, I am open to ' + ex + ' instead.'));
      p.push(pick('Is there room to adjust the offer? I am happy to talk it through on a call' + (deadline ? ', and I can give you my answer by ' + deadline : '') + '.',
        'Please let me know whether you can meet this' + (deadline ? ' by ' + deadline : '') + '. I am ready to move quickly once we agree.',
        deadline ? 'I can give you my final answer by ' + deadline + '.' : 'I can decide quickly once I hear back.'));
      p.push(pick('Thank you again,', 'Best regards,', 'Thanks,') + '\n' + name);
    } else if (sc === 'raise') {
      subject = 'Request to review my salary';
      var inc = pct != null && pct > 0 ? ', an increase of ' + plain(pct, 1) + '%' : '';
      p.push(pick('I would like to ask for a review of my salary. I enjoy my work as ' + title + ' at ' + company + ', and I want my pay to reflect what the role has become.',
        'I am writing to ask for an adjustment to my salary as ' + title + ' at ' + company + '.', 'I would like to ask for a salary review.'));
      if (tone === 'brief') p.push('My salary is ' + offerT + ' and I am asking for ' + targetT + inc + '.' + (reasons.length ? ' My reasons: ' + reasons.map(function (r) { return r.replace(/[.;]+$/, ''); }).join('; ') + '.' : ''));
      else p.push(pick('My current salary is ' + offerT + '. I am asking for ' + targetT + inc + '. This is based on:', 'My salary is ' + offerT + '. I am asking for it to be raised to ' + targetT + inc + '. The case for it:', '') + '\n\n' + bullets);
      if (ex) p.push(pick('If that is not possible in this cycle, I would like to discuss other options, such as ' + ex + '.', 'If the budget does not allow the full figure now, I expect us to agree on an alternative, such as ' + ex + '.', 'If the full figure is not possible now, I am open to ' + ex + '.'));
      p.push(pick('Could we find a time to talk about it' + (deadline ? ' before ' + deadline : '') + '?', 'Please let me know when we can meet to settle this' + (deadline ? ', ideally before ' + deadline : '') + '.', 'Can we talk' + (deadline ? ' before ' + deadline : ' this week') + '?'));
      p.push(pick('Thank you,', 'Best regards,', 'Thanks,') + '\n' + name);
    } else {
      subject = title + ' offer: time to decide';
      var until = deadline || '[date]';
      p.push(pick('Thank you for the offer to join ' + company + ' as ' + title + '. I am glad to have it, and I want to give it the careful thought it deserves.',
        'Thank you for the offer to join ' + company + ' as ' + title + '.', 'Thank you for the offer for the ' + title + ' role at ' + company + '.'));
      p.push(pick('Would it be possible to have until ' + until + ' to give you my answer?', 'I will need until ' + until + ' to give you a considered answer.', 'Could I have until ' + until + ' to decide?') +
        (reasons.length ? (tone === 'brief' ? ' The reason: ' + reasons[0].replace(/[.;]+$/, '') + '.' : ' The reason I ask:\n\n' + reasons.map(function (r) { return '- ' + r; }).join('\n')) : ''));
      p.push(pick('If you need anything from me in the meantime, I am happy to provide it.', 'Please confirm that this date works for you.', 'Let me know if that works.'));
      p.push(pick('Thank you,', 'Best regards,', 'Thanks,') + '\n' + name);
    }
    var body = p.filter(Boolean).join('\n\n');
    return { subject: subject, body: body, text: 'Subject: ' + subject + '\n\n' + body, pct: pct, gap: offer > 0 && target > 0 ? target - offer : null };
  };

  /* ---------- job description checker ---------- */
  function syllables(w) {
    w = String(w).toLowerCase().replace(/[^a-z]/g, '');
    if (!w) return 1;
    if (w.length <= 3) return 1;
    w = w.replace(/(?:[^laeiouy]es|ed|[^laeiouy]e)$/, '').replace(/^y/, '');
    var m = w.match(/[aeiouy]{1,2}/g);
    return m ? m.length : 1;
  }
  T.syllables = syllables;
  // Flesch reading ease and Flesch–Kincaid grade (public formulas). Every line break also ends a sentence, so bullet points count one each.
  T.readability = function (text) {
    var sent = [];
    String(text || '').split(/[\n\r]+/).forEach(function (ln) { ln.split(/[.!?]+(?=\s|$)/).forEach(function (s) { var n = wordCount(s); if (n) sent.push(n); }); });
    var words = String(text || '').match(/[A-Za-z0-9À-ɏ][A-Za-z0-9À-ɏ'’+#.\-]*/g) || [], syl = 0;
    words.forEach(function (w) { syl += syllables(w); });
    if (!words.length || !sent.length) return { words: 0, sentences: 0, avg: 0, ease: null, grade: null, long: 0, longest: 0 };
    var wps = words.length / sent.length, spw = syl / words.length;
    return { words: words.length, sentences: sent.length, avg: wps, ease: 206.835 - 1.015 * wps - 84.6 * spw, grade: 0.39 * wps + 11.8 * spw - 15.59,
      long: sent.filter(function (n) { return n > 30; }).length, longest: Math.max.apply(null, sent) };
  };
  var MASC = 'aggressive aggressively ambitious ambition assertive assertiveness competitive decisive determined determination dominant dominate dominating driven fearless forceful headstrong independent independently outspoken relentless relentlessly ruthless self-reliant self-sufficient strong-willed stubborn superior confident confidently hero heroes heroic'.split(' ');
  var FEM = 'nurture nurturing compassion compassionate empathy empathetic empathic sympathy sympathetic supportive warm warmth gentle pleasant polite considerate cooperative cooperate cooperation interpersonal loyal loyalty modest cheerful honest honesty caring collaborative collaborate collaboration together inclusive enthusiastic enthusiasm'.split(' ');
  var EXCLUDE = [
    ['rockstar', 'name the skill level you need instead of a persona'], ['rock star', 'name the skill level you need instead of a persona'], ['ninja', 'name the skill level you need instead of a persona'],
    ['guru', 'say “expert in …” and name the subject'], ['wizard', 'name the skill you mean'], ['superhero', 'describe the real scope of the job'], ['superstar', 'describe the real scope of the job'],
    ['brogrammer', 'remove it'], ['digital native', 'age-coded: list the tools the person must know'], ['youthful', 'age-coded: describe the team’s way of working instead'],
    ['young team', 'age-coded: describe the team’s way of working instead'], ['young and', 'age-coded: describe the team’s way of working instead'], ['recent graduate', 'age-coded: write “entry-level” if you mean experience'],
    ['native english', 'shuts out fluent non-native speakers: write “fluent English”'], ['native speaker', 'shuts out fluent non-native speakers: write “fluent in …”'], ['mother tongue', 'write “fluent in …”'],
    ['manpower', 'write “staff” or “workforce”'], ['man-hours', 'write “hours of work”'], ['man hours', 'write “hours of work”'], ['chairman', 'write “chair”'], ['salesman', 'write “salesperson”'],
    ['guys', 'write “team” or “everyone”'], ['he/she', 'write “they”'], ['his/her', 'write “their”'], ['him/her', 'write “them”'], ['able-bodied', 'state the physical task itself, if there is one'],
    ['clean-shaven', 'remove it unless a safety rule requires it, and then cite the rule'], ['thick skin', 'describe the actual pressure in the role'], ['work hard play hard', 'reads as long hours and a party culture: say what the hours are'],
    ['work hard, play hard', 'reads as long hours and a party culture: say what the hours are'], ['killer instinct', 'describe the result you expect'], ['crush it', 'describe the result you expect']
  ];
  var JARGON = ['synergy', 'synergies', 'leveraging', 'best-in-class', 'best of breed', 'world-class', 'cutting-edge', 'bleeding-edge', 'disruptive', 'paradigm', 'move the needle', 'low-hanging fruit',
    'circle back', 'outside the box', 'results-driven', 'self-starter', 'go-getter', 'hit the ground running', 'fast-paced', 'wear many hats', 'passionate', 'game-changer', 'game-changing',
    'value-add', 'mission-critical', 'thought leader', 'team player', '10x', 'rock-solid', 'next-generation', 'holistic'];
  function phraseRx(p) { return new RegExp('(^|[^a-z0-9-])(' + p.replace(/[.*+?^${}()|[\]\\\/]/g, '\\$&').replace(/[\s-]+/g, '[\\s-]+') + ')(?![a-z0-9-])', 'gi'); }
  function findPhrases(text, list) {       // unique phrases from `list` that occur in `text`, with how often
    var out = [];
    list.forEach(function (item) {
      var p = typeof item === 'string' ? item : item[0], m = text.match(phraseRx(p));
      if (m) out.push({ term: p, n: m.length, tip: typeof item === 'string' ? '' : item[1] });
    });
    return out;
  }
  var H_NICE = /\b(nice[- ]to[- ]haves?|bonus|preferred|a plus|pluses|desirable|desired|good to have|extra credit|ideally|not required|optional|would be great)\b/i;
  var H_REQ = /\b(requirements?|qualifications?|must[- ]haves?|what you(?:['’]ll| will)? (?:need|bring|have)|what we(?:['’]re| are) looking for|who you are|about you|you (?:have|bring|are|should have|will have|must have)|your (?:profile|background|experience|skills)|skills (?:and|&) experience|experience (?:and|&) skills|minimum|essential|we expect|what it takes)\b/i;
  var H_OTHER = /\b(responsibilit\w*|what you(?:['’]ll| will) (?:do|be doing|work on|own)|the role|the job|about (?:us|the|our)|who we are|benefits|perks|what we offer|we offer|compensation|salary|pay|location|how to apply|hiring process|interview process|our (?:stack|team|values|mission)|why (?:join|us|you)|equal opportunity|diversity|day[- ]to[- ]day|in this role|your (?:role|mission|impact|responsibilities))\b/i;
  var BULLET = /^\s*(?:[-*•·▪◦‣–—>]|\d{1,2}[.)])\s+\S/;
  var PAYWORD = /salary|salaries|compensation|\bpay\b|\bbase\b|\bote\b|per annum|\/\s?(?:year|yr|hour|hr)|per hour|hourly|day rate|\bp\.a\.|remuneration|wage/i;
  var NOTPAY = /budget|stipend|allowance|bonus|revenue|funding|raised|valuation|\barr\b|turnover|customers|users|volume|assets|\baum\b|transactions/i;
  var AMOUNT = /(?:[$€£₹¥]|\b(?:USD|EUR|GBP|CAD|AUD|CHF|SGD|INR)\b)\s?\d[\d,.]*\s?[kKmM]?\b|\b\d[\d,.]*\s?[kK]?\s?(?:USD|EUR|GBP|CAD|AUD|CHF|SGD|INR|dollars|euros|pounds)\b/g;
  T.checkJD = function (text) {
    text = String(text || '');
    var rd = T.readability(text), words = rd.words;
    if (words < 40) return { error: 'short', words: words };
    var items = [], penalty = 0, lower = text.toLowerCase();
    var add = function (level, title, body, cost) { items.push({ level: level, t: title, d: body }); penalty += cost || 0; };

    // length
    if (words < 150) add('fix', 'Too short: ' + words + ' words', 'A reader cannot tell what the job is, who it suits or what it pays. As a rule of thumb, aim for 300 to 700 words.', 15);
    else if (words < 300) add('warn', 'On the short side: ' + words + ' words', 'Check that the text covers the work itself, the must-haves, pay, location and the hiring steps.', 5);
    else if (words <= 900) add('ok', 'Length is fine: ' + fmt(words) + ' words', 'Long enough to answer a candidate’s questions, short enough to be read.');
    else if (words <= 1300) add('warn', 'Long: ' + fmt(words) + ' words', 'People skim long postings. Cut company boilerplate and merge bullet points that say the same thing.', 8);
    else add('fix', 'Very long: ' + fmt(words) + ' words', 'Few candidates read this much. Keep what the person will do, what they must bring and what they get; move the rest to your careers page.', 12);

    // salary: money figures that sit near a pay word, or a clear range of two money figures
    // a figure counts as pay when a pay word is close by and the words just before it are not about a budget, revenue or funding; millions never count
    var amounts = [], m, near = function (i, len) { return PAYWORD.test(lower.slice(Math.max(0, i - 70), i + len + 40)) && !NOTPAY.test(lower.slice(Math.max(0, i - 40), i)); };
    AMOUNT.lastIndex = 0;
    while ((m = AMOUNT.exec(text))) amounts.push({ s: m[0], near: near(m.index, m[0].length) && !/\d\s?m$/i.test(m[0].trim()) });
    var range = null, RANGE = /(?:[$€£₹¥]\s?\d[\d,.]*\s?[kKmM]?|\b\d[\d,.]*\s?[kK])\s?(?:[-–—]|to)\s?[$€£₹¥]?\s?\d[\d,.]*\s?[kKmM]?\b/g;
    while (!range && (m = RANGE.exec(text))) {          // …or when it is a range that looks like a salary on its own ($120k–$150k)
      if (/\d\s?m\b/i.test(m[0]) || NOTPAY.test(lower.slice(Math.max(0, m.index - 40), m.index))) continue;
      if (near(m.index, m[0].length) || (/[$€£₹¥]/.test(m[0]) && /k|\d{2,3}[,.]?\d{3}/i.test(m[0]))) range = m;
    }
    var pay = amounts.filter(function (a) { return a.near; });
    if (range) add('ok', 'Salary range is stated', 'Found: ' + clean(range[0]) + '. Say whether it is per year or per hour and what it depends on.');
    else if (pay.length >= 2) add('ok', 'Pay figures are stated', 'Found: ' + pay.slice(0, 2).map(function (a) { return clean(a.s); }).join(' and ') + '. Make sure it reads as a range, with the period (per year, per hour).');
    else if (pay.length === 1) add('warn', 'One pay figure, no range', 'Found: ' + clean(pay[0].s) + '. Give the lower and the upper end, so people can tell whether the job is in their bracket.', 6);
    else if (/competitive\s+(?:salary|compensation|pay|package|remuneration)/i.test(text)) add('fix', '“Competitive salary” is not a salary', 'There is no figure in the text. Add the range, the currency and the period (per year or per hour).', 20);
    else add('fix', 'No salary range', 'There is no pay figure in the text. Add the range, the currency and the period (per year or per hour).', 20);

    // must-have requirements: bullet points (or plain lines) under a requirements heading
    var section = '', req = 0, nice = 0, sawReq = false, sawNice = false;
    text.split(/\r?\n/).forEach(function (ln) {
      var s = ln.trim(); if (!s) return;
      var isBullet = BULLET.test(ln), wc = s.split(/\s+/).length;
      if (!isBullet && wc <= 9 && !/[.!?]$/.test(s)) {
        if (H_NICE.test(s)) { section = 'nice'; sawNice = true; return; }
        if (H_REQ.test(s) || /^(?:experience|skills|profile|background)\s*:?$/i.test(s)) { section = 'req'; sawReq = true; return; }
        if (H_OTHER.test(s) || /:$/.test(s)) { section = 'other'; return; }
      }
      if (section === 'req') req++; else if (section === 'nice') nice++;
    });
    if (!sawReq) {
      text.split(/\r?\n|[.!?]+(?=\s|$)/).forEach(function (s) { if (/\b(must|required|requires?|minimum|at least|essential|mandatory)\b|\b\d{1,2}\s*\+?\s*(?:years|yrs)\b/i.test(s)) req++; });
    }
    var how = sawReq ? ' under your requirements heading' : ' (lines that say “must”, “required”, “minimum” or ask for years of experience)';
    if (req > 12) add('fix', req + ' must-have requirements', 'We counted ' + req + how + '. A list this long reads as “do not apply”. Keep the five to seven you would really reject someone for' + (sawNice ? '.' : ' and move the rest under a “Nice to have” heading.'), 14);
    else if (req > 8) add('warn', req + ' must-have requirements', 'We counted ' + req + how + '. Check each one: would you turn down a good candidate who lacks it? If not, ' + (sawNice ? 'move it to your nice-to-have list.' : 'move it under a “Nice to have” heading.'), 8);
    else if (req > 0) add('ok', req + ' must-have requirement' + (req === 1 ? '' : 's'), 'We counted ' + req + how + (nice ? ', plus ' + nice + ' marked as nice to have' : '') + '. A short list makes it clear who should apply.');
    else add('warn', 'No requirements list found', 'We could not find a requirements or qualifications heading, or any “must” lines. Say plainly what a person needs in order to do this job.', 5);

    // years of experience
    var yrs = [], ym, YR = /(\d{1,2})\s*\+?\s*(?:[-–]\s*\d{1,2}\s*)?(?:years|yrs)\b(?!\s+(?:ago|old|in business|running))/gi;
    while ((ym = YR.exec(text))) yrs.push(+ym[1]);
    var maxY = yrs.length ? Math.max.apply(null, yrs) : 0;
    if (maxY >= 8) add('warn', 'Asks for ' + maxY + '+ years of experience', 'Years are a rough stand-in for ability and screen out people who learned faster. Say what the person must be able to do on day one.', 3);
    else if (maxY > 0) add('info', 'Asks for ' + maxY + '+ years of experience', 'Fine if it is a real minimum. Consider describing what the person must be able to do instead.');

    // gender-coded wording ("competitive salary" is about pay, not about the person)
    var scan = text.replace(/competitive\s+(?:salary|salaries|compensation|pay|benefits|package|packages|rates?|base|equity|wages?|remuneration)/gi, ' ');
    var masc = findPhrases(scan, MASC), fem = findPhrases(scan, FEM), names = function (l) { return l.map(function (x) { return x.term; }).join(', '); };
    if (masc.length - fem.length >= 2) add('warn', 'Wording leans masculine-coded', 'Masculine-coded: ' + names(masc) + (fem.length ? '. Feminine-coded: ' + names(fem) : '') + '. Swap some for neutral words that describe the work (for example “sets clear goals” instead of “ambitious”).', 6);
    else if (fem.length - masc.length >= 2) add('info', 'Wording leans feminine-coded', 'Feminine-coded: ' + names(fem) + (masc.length ? '. Masculine-coded: ' + names(masc) : '') + '. Nothing to fix unless the tone does not match the job.');
    else if (masc.length || fem.length) add('ok', 'Gender-coded wording is balanced', (masc.length ? 'Masculine-coded: ' + names(masc) + '. ' : '') + (fem.length ? 'Feminine-coded: ' + names(fem) + '.' : ''));
    else add('ok', 'No gender-coded wording found', 'None of the words on our list appear in the text.');

    // exclusionary wording
    var exc = findPhrases(text, EXCLUDE);
    if (exc.length) add('fix', exc.length + ' exclusionary term' + (exc.length === 1 ? '' : 's'), exc.map(function (x) { return '“' + x.term + '”: ' + x.tip; }).join('. ') + '.', Math.min(15, exc.length * 5));
    else add('ok', 'No exclusionary terms found', 'No age-coded, gendered or persona words (“ninja”, “digital native”, “native speaker”) from our list.');

    // jargon
    var jar = findPhrases(text, JARGON);
    if (jar.length) add(jar.length > 2 ? 'warn' : 'info', jar.length + ' buzzword' + (jar.length === 1 ? '' : 's'), 'Found: ' + names(jar) + '. Replace each with the plain fact behind it: what the team ships, how fast, for whom.', Math.min(10, jar.length * 2));
    else add('ok', 'No buzzwords found', 'The text describes the job in plain words.');

    // what candidates look for
    if (!/\b(remote|hybrid|on-?site|in[- ]office|in the office|relocat\w*|work from home|wfh|time ?zones?|located in|based in|office in|offices in)\b/i.test(text))
      add('warn', 'No word on where the work happens', 'Say whether the job is remote, hybrid or on site, and in which city, country or time zones.', 6);
    else add('ok', 'Work location is covered', 'The text says where or how the work happens.');
    if (!/\b(benefits?|perks?|pto|paid time off|vacation|holidays?|health|insurance|401\(?k\)?|pension|equity|stock options?|bonus|parental|stipend|learning budget|days off)\b/i.test(text))
      add('warn', 'No benefits mentioned', 'List what comes with the salary: time off, health cover, equity, bonus, learning budget.', 5);
    else add('ok', 'Benefits are mentioned', 'Make sure they are concrete (how many days off, what kind of cover).');
    if (!/\b(interviews?|hiring process|how to apply|application process|next steps|what to expect|apply (?:by|via|through|here|now|with))\b/i.test(text))
      add('info', 'Hiring steps are not described', 'Say how to apply and what happens next: how many interviews, with whom, how long it usually takes.', 4);
    else add('ok', 'Hiring steps are described', 'Candidates can see what happens after they apply.');

    // who the text talks about
    var you = (lower.match(/\b(?:you|your|you['’]ll|you['’]re)\b/g) || []).length, we = (lower.match(/\b(?:we|our|us|we['’]re|we['’]ll)\b/g) || []).length;
    if (we >= 6 && we > you * 1.5) add('info', 'More about the company than the candidate', '“We / our” appears ' + we + ' times, “you / your” ' + you + '. Turn some sentences around: what will the person do, learn and get?', 3);

    // readability
    if (rd.long >= 2) add('warn', rd.long + ' sentences longer than 30 words', 'The longest has ' + rd.longest + ' words. Split them: one idea per sentence.', 6);
    if (rd.grade > 13) add('warn', 'Hard to read: grade ' + plain(rd.grade, 1), 'Flesch reading ease ' + plain(rd.ease, 0) + ' (higher is easier). Shorter sentences and shorter words would help.', 4);
    else add('ok', 'Readable: grade ' + plain(Math.max(rd.grade, 0), 1), 'Flesch reading ease ' + plain(rd.ease, 0) + ' (higher is easier), ' + plain(rd.avg, 1) + ' words per sentence or bullet point on average.');

    var score = Math.max(0, 100 - penalty), rank = { fix: 0, warn: 1, info: 2, ok: 3 };
    items.sort(function (a, b) { return rank[a.level] - rank[b.level]; });
    return { score: score, label: score >= 85 ? 'Ready to post' : score >= 65 ? 'Good, with a few fixes' : 'Needs work', items: items, words: words, readability: rd, mustHaves: req, niceToHaves: nice,
      masculine: masc, feminine: fem, exclusionary: exc, jargon: jar, fixes: items.filter(function (i) { return i.level === 'fix' || i.level === 'warn'; }).length };
  };

  /* ---------- JobPosting structured data ---------- */
  function escH(s) { return String(s).replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;'); }
  // Plain text -> simple HTML: blank line = new paragraph, lines starting with a bullet mark = list.
  T.descHtml = function (text) {
    var out = [];
    String(text || '').replace(/\r/g, '').split(/\n{2,}/).forEach(function (block) {
      var buf = [], list = [];
      var flushP = function () { if (buf.length) { out.push('<p>' + buf.map(escH).join('<br>') + '</p>'); buf = []; } };
      var flushL = function () { if (list.length) { out.push('<ul>' + list.map(function (l) { return '<li>' + escH(l) + '</li>'; }).join('') + '</ul>'); list = []; } };
      block.split('\n').forEach(function (l) {
        l = l.trim(); if (!l) return;
        var m = l.match(/^(?:[-*•·▪◦‣–—]|\d{1,2}[.)])\s+(.*)$/);
        if (m) { flushP(); list.push(m[1]); } else { flushL(); buf.push(l); }
      });
      flushP(); flushL();
    });
    return out.join('');
  };
  function isDate(s) { var m = /^(\d{4})-(\d{2})-(\d{2})$/.exec(s || ''); if (!m) return false; var d = new Date(Date.UTC(+m[1], +m[2] - 1, +m[3])); return d.getUTCMonth() === +m[2] - 1 && d.getUTCDate() === +m[3]; }
  function isUrl(s) { return /^https?:\/\/[^\s.]+\.[^\s]+$/i.test(s || ''); }
  T.jobPosting = function (f, today) {
    f = f || {};
    var err = [], warn = [], v = function (k) { return clean(f[k]); };
    var o = { '@context': 'https://schema.org/', '@type': 'JobPosting' };
    var title = v('title'), desc = String(f.description || '').trim(), posted = v('datePosted'), through = v('validThrough'), org = v('orgName');
    if (title) { o.title = title; if (/[!*$€£]|\b(urgent|apply now|now hiring)\b/i.test(title) || /\d{4,}/.test(title)) warn.push('title: keep it to the job title only, without pay, job codes, dates or calls to apply.'); }
    else err.push('title: required. The name of the job, for example “Senior Backend Engineer”.');
    if (desc) { o.description = T.descHtml(desc); if (wordCount(desc) < 50) warn.push('description: Google expects the full job description (duties, qualifications, hours). This one has under 50 words.'); if (title && clean(desc).toLowerCase() === title.toLowerCase()) err.push('description: must not just repeat the title.'); }
    else err.push('description: required. The full text of the job; it is turned into HTML for you.');
    if (posted) { if (isDate(posted)) o.datePosted = posted; else err.push('datePosted: must be a date in the form YYYY-MM-DD.'); }
    else err.push('datePosted: required. The day the job was first published.');
    if (through) {
      if (!isDate(through)) err.push('validThrough: must be a date in the form YYYY-MM-DD.');
      else { o.validThrough = through; if (isDate(posted) && through < posted) err.push('validThrough: this date is earlier than datePosted.'); else if (today && through < today) warn.push('validThrough: this date is in the past, so Google treats the job as expired.'); }
    } else warn.push('validThrough: recommended. The last day to apply; leave it out only if the job has no closing date.');
    var types = (f.employmentType || []).filter(Boolean);
    if (types.length) o.employmentType = types.length === 1 ? types[0] : types; else warn.push('employmentType: recommended. Tick full-time, part-time, contractor or another type.');
    if (org) {
      o.hiringOrganization = { '@type': 'Organization', name: org };
      var url = v('orgUrl'), logo = v('orgLogo');
      if (url) { if (isUrl(url)) o.hiringOrganization.sameAs = url; else warn.push('hiringOrganization: the company website should be a full address starting with https://.'); }
      if (logo) { if (isUrl(logo)) o.hiringOrganization.logo = logo; else warn.push('hiringOrganization: the logo should be a full image address starting with https://.'); }
    } else err.push('hiringOrganization: required. The name of the company that is hiring, not the agency or the job board.');
    var country = v('country'), addr = {};
    [['streetAddress', 'street'], ['addressLocality', 'city'], ['addressRegion', 'region'], ['postalCode', 'postal'], ['addressCountry', 'country']].forEach(function (p) { if (v(p[1])) addr[p[0]] = v(p[1]); });
    var hasAddr = Object.keys(addr).length > 0, place = function () { o.jobLocation = { '@type': 'Place', address: Object.assign({ '@type': 'PostalAddress' }, addr) }; };
    if (f.locType === 'remote') {
      o.jobLocationType = 'TELECOMMUTE';
      var lands = String(f.remoteCountries || '').split(/[,;\n]+/).map(clean).filter(Boolean);
      if (lands.length) o.applicantLocationRequirements = lands.length === 1 ? { '@type': 'Country', name: lands[0] } : lands.map(function (c) { return { '@type': 'Country', name: c }; });
      if (hasAddr) place();
      if (!lands.length && !country) err.push('applicantLocationRequirements: required for a fully remote job. Name at least one country where applicants may be located.');
    } else {
      if (hasAddr) place();
      if (!hasAddr) err.push('jobLocation: required. The address where the person reports to work. For a fully remote job, choose “Fully remote”.');
      else {
        if (!country) err.push('jobLocation: needs addressCountry, for example US, GB or DE.');
        if (!v('city')) warn.push('jobLocation: add the city (addressLocality) so the job shows up in local searches.');
        if (!v('region') && /^(us|usa|united states|ca|canada|au|australia)$/i.test(country)) warn.push('jobLocation: add the state or province (addressRegion).');
      }
    }
    var smin = num(f.salaryMin), smax = num(f.salaryMax), cur = v('salaryCurrency').toUpperCase();
    if (smin > 0 || smax > 0) {
      var val = { '@type': 'QuantitativeValue' };
      if (smin > 0 && smax > 0 && smin !== smax) { val.minValue = smin; val.maxValue = smax; if (smin > smax) err.push('baseSalary: the minimum is higher than the maximum.'); }
      else val.value = smin > 0 ? smin : smax;
      val.unitText = /^(HOUR|DAY|WEEK|MONTH|YEAR)$/.test(f.salaryUnit) ? f.salaryUnit : 'YEAR';
      if (!/^[A-Z]{3}$/.test(cur)) err.push('baseSalary: needs a three-letter currency code such as USD, EUR or GBP.');
      o.baseSalary = { '@type': 'MonetaryAmount', currency: cur || 'USD', value: val };
    } else warn.push('baseSalary: recommended. The pay range offered by the employer, not an estimate.');
    var ident = v('identifier');
    if (ident) o.identifier = { '@type': 'PropertyValue', name: org || undefined, value: ident }; else warn.push('identifier: recommended. Your own reference number for the job.');
    if (f.directApply === 'true' || f.directApply === 'false') o.directApply = f.directApply === 'true';
    else warn.push('directApply: recommended. Say whether people can apply on this page without being sent to another site.');
    var json = JSON.stringify(o, null, 2).replace(/</g, '\\u003c');
    return { data: o, json: json, script: '<script type="application/ld+json">\n' + json + '\n</' + 'script>', errors: err, warnings: warn, valid: !err.length };
  };

  /* ---------- Boolean search strings ---------- */
  function termList(s) {
    var seen = {}, out = [];
    String(s || '').split(/[,;\n]+/).forEach(function (t) {
      t = clean(t.replace(/["“”]/g, '')); var k = t.toLowerCase();
      if (t && !seen[k]) { seen[k] = 1; out.push(t); }
    });
    return out;
  }
  function quote(t) { return /^[A-Za-z0-9]+$/.test(t) ? t : '"' + t + '"'; }
  function orGroup(list) { return list.length > 1 ? '(' + list.map(quote).join(' OR ') + ')' : list.length ? quote(list[0]) : ''; }
  // Common spellings of the same title: engineer / developer, front-end / frontend / front end.
  T.titleVariants = function (title) {
    var t = clean(title), set = [t], push = function (x) { if (set.map(function (s) { return s.toLowerCase(); }).indexOf(x.toLowerCase()) < 0) set.push(x); };
    var spell = function (s) {
      var m = s.match(/\b(front|back|full)[\s-]?(end|stack)\b/i);
      return m ? [m[1] + m[2].toLowerCase(), m[1] + '-' + m[2], m[1] + ' ' + m[2]].map(function (x) { return s.replace(m[0], x); }) : [s];
    };
    var swap = function (s) {
      if (/\bengineer\b/i.test(s)) return [s, s.replace(/\bengineer\b/i, function (w) { return w.charAt(0) === 'E' ? 'Developer' : 'developer'; })];
      if (/\bdeveloper\b/i.test(s)) return [s, s.replace(/\bdeveloper\b/i, function (w) { return w.charAt(0) === 'D' ? 'Engineer' : 'engineer'; })];
      return [s];
    };
    swap(t).forEach(function (a) { spell(a).forEach(push); });
    return set;
  };
  T.booleanSearch = function (f) {
    f = f || {};
    var titles = termList(f.titles), must = termList(f.must), any = termList(f.any), not = termList(f.not), place = clean(String(f.place || '').replace(/["“”]/g, ''));
    if (f.variants) { var all = []; titles.forEach(function (t) { T.titleVariants(t).forEach(function (x) { if (all.map(function (s) { return s.toLowerCase(); }).indexOf(x.toLowerCase()) < 0) all.push(x); }); }); titles = all; }
    if (!titles.length && !must.length && !any.length) return { empty: true, boolean: '', linkedin: '', github: '', words: 0 };
    var parts = [];
    if (titles.length) parts.push(orGroup(titles));
    must.forEach(function (t) { parts.push(quote(t)); });
    if (any.length) parts.push(orGroup(any));
    var bool = parts.join(' AND ') + (not.length ? ' NOT ' + orGroup(not) : '');
    var minus = not.map(function (t) { return '-' + quote(t); });
    var g = function (site, withTitles) {
      var p = [site];
      if (withTitles && titles.length) p.push(orGroup(titles));
      must.forEach(function (t) { p.push(quote(t)); });
      if (any.length) p.push(orGroup(any));
      if (place) p.push('"' + place + '"');
      return p.concat(minus).join(' ');
    };
    var linkedin = g('site:linkedin.com/in', true), github = must.length || any.length ? g('site:github.com', false) : '';
    var count = function (s) { return s ? s.replace(/[()"]/g, ' ').split(/\s+/).filter(function (w) { return w && w !== 'OR' && w !== 'AND' && w !== 'NOT'; }).length : 0; };
    return { boolean: bool, linkedin: linkedin, github: github, titles: titles, words: count(linkedin), wordsGithub: count(github), length: bool.length };
  };

  /* ---------- contractor rate ---------- */
  // Revenue needed = income × (1 + extra costs %) + business costs. Billable days = (260 − days off) × billable share.
  T.contractorRate = function (o) {
    var income = pos(o.income); if (!(income > 0)) return null;
    var share = num(o.billable); share = isNaN(share) ? 100 : Math.min(Math.max(share, 0), 100);
    var hours = pos(o.hours) || 8, workDays = 260 - Math.min(pos(o.daysOff), 260), days = workDays * share / 100;
    if (!(days > 0) || hours > 24) return null;
    var revenue = income * (1 + pos(o.overhead) / 100) + pos(o.costs), day = revenue / days, hour = day / hours, salaried = income / 2080;
    return { revenue: revenue, workDays: workDays, days: days, day: day, hour: hour, month: revenue / 12, salariedHour: salaried, upliftPct: (hour / salaried - 1) * 100 };
  };

  /* ---------- salary checker ---------- */
  // qs: percent points (0…100), vals: the salary at each point. Returns the share of postings below x, 0–100.
  T.percentile = function (qs, vals, x) {
    if (!(x >= vals[0])) return 0;
    var i = 0;
    for (var k = 0; k < vals.length; k++) if (vals[k] <= x) i = k;
    if (i >= vals.length - 1) return 100;
    return qs[i] + (qs[i + 1] - qs[i]) * (x - vals[i]) / (vals[i + 1] - vals[i]);
  };
  T.quantile = function (qs, vals, q) { var i = qs.indexOf(q); return i < 0 ? null : vals[i]; };
  // data.g maps "category|level|skill" to [postings counted, median range low, median range high, value at each data.q point] in $K.
  T.salaryGroup = function (data, cat, lvl, skill) {
    var row = data && data.g ? data.g[(cat || '') + '|' + (lvl || '') + '|' + (skill || '')] : null;
    if (!row) return null;
    var vals = row.slice(3).map(function (v) { return v * 1000; });
    return { n: row[0], low: row[1] * 1000, high: row[2] * 1000, vals: vals, median: T.quantile(data.q, vals, 50), p10: T.quantile(data.q, vals, 10), p25: T.quantile(data.q, vals, 25),
      p75: T.quantile(data.q, vals, 75), p90: T.quantile(data.q, vals, 90), min: vals[0], max: vals[vals.length - 1] };
  };

  /* ================================================================ letters, builders and calculators added 2026-11-13 ================================================================ */

  /* ---------- calendar dates: whole days, no clock and no time zone ---------- */
  var MONTH_NAMES = ['January', 'February', 'March', 'April', 'May', 'June', 'July', 'August', 'September', 'October', 'November', 'December'];
  var DAY_NAMES = ['Sunday', 'Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday'];
  function dayNum(s) {                                    // "2026-11-16" -> days since 1 January 1970; NaN when it is not a real date
    var m = /^(\d{4})-(\d{2})-(\d{2})$/.exec(clean(s));
    if (!m || +m[1] < 1900 || +m[1] > 2200 || !isDate(m[0])) return NaN;
    return Date.UTC(+m[1], +m[2] - 1, +m[3]) / 864e5;
  }
  function dayIso(n) { return new Date(n * 864e5).toISOString().slice(0, 10); }
  function weekday(n) { return mod(n + 4, 7); }           // 1 January 1970 was a Thursday; 0 = Sunday
  function isWork(n) { var w = weekday(n); return w !== 0 && w !== 6; }
  function workdaysBetween(a, b) {                        // Mondays to Fridays from day a to day b, both counted
    if (b < a) return 0;
    var full = Math.floor((b - a + 1) / 7), c = full * 5;
    for (var d = a + full * 7; d <= b; d++) if (isWork(d)) c++;
    return c;
  }
  function addMonths(n, k) {                              // the same day of the month k months later; the 31st becomes the last day of a shorter month
    var d = new Date(n * 864e5), y = d.getUTCFullYear(), m = d.getUTCMonth() + k;
    return Date.UTC(y, m, Math.min(d.getUTCDate(), new Date(Date.UTC(y, m + 1, 0)).getUTCDate())) / 864e5;
  }
  // "2026-11-30" -> "November 30, 2026", or "Monday, November 30, 2026" with the day name; '' when it is not a date
  T.longDate = function (s, withDay) {
    var n = dayNum(s); if (isNaN(n)) return '';
    var d = new Date(n * 864e5);
    return (withDay ? DAY_NAMES[weekday(n)] + ', ' : '') + MONTH_NAMES[d.getUTCMonth()] + ' ' + d.getUTCDate() + ', ' + d.getUTCFullYear();
  };
  T.dayName = function (s) { var n = dayNum(s); return isNaN(n) ? '' : DAY_NAMES[weekday(n)]; };
  T.addDays = function (s, k) { var n = dayNum(s); return isNaN(n) ? '' : dayIso(n + k); };

  /* ---------- last working day ---------- */
  // o.date: the day notice is given; o.amount + o.unit ('weeks', 'workdays', 'months', 'days'): the notice period;
  // o.from: 'next' when the period starts the day after notice is given (the default), 'same' when that day is day one.
  // Weeks, months and calendar days give the date the notice ends; the last working day is the last Monday-to-Friday on or before it.
  // Working days are counted one by one, skipping Saturdays and Sundays. Public holidays are not known and not removed.
  var NOTICE_MAX = { weeks: 520, workdays: 2600, months: 120, days: 3650 };
  T.lastDay = function (o) {
    o = o || {};
    var start = dayNum(o.date), n = num(o.amount), unit = NOTICE_MAX[o.unit] ? o.unit : 'weeks', same = o.from === 'same';
    if (isNaN(start) || !(n >= 0) || n > NOTICE_MAX[unit]) return null;
    var first = same ? start : start + 1, k = unit === 'weeks' ? Math.round(n * 7) : Math.round(n), end;
    if (!k) end = start;                                  // no notice: the job ends the day notice is given
    else if (unit === 'workdays') { for (var d = first, left = k; left > 0; d++) if (isWork(d)) { left--; end = d; } }
    else if (unit === 'months') end = addMonths(start, k) - (same ? 1 : 0);
    else end = first + k - 1;
    var last = end; while (!isWork(last)) last--;
    return { date: dayIso(start), first: dayIso(first), end: dayIso(end), last: dayIso(last), endsOnWeekend: last !== end, givenOnWeekend: !isWork(start),
      workDays: k ? workdaysBetween(first, last) : 0, calendarDays: end - start, unit: unit, count: unit === 'weeks' ? k / 7 : k, from: same ? 'same' : 'next' };
  };

  /* ---------- job search funnel ---------- */
  // A rate typed as a percent ("8", "7,5%") or as the person's own count ("3 of 40", "3/40", "3 out of 40").
  T.rate = function (v) {
    var s = clean(v).toLowerCase(), m = /^(.+?)\s*(?:\/|out of|of|from)\s*(.+)$/.exec(s);
    if (m) { var a = num(m[1]), b = num(m[2]); return a >= 0 && b > 0 && a <= b ? { pct: a / b * 100, got: a, from: b } : { pct: NaN, from: null }; }
    var p = num(s);
    return { pct: p >= 0 && p <= 100 ? p : NaN, from: null };
  };
  // interviews = applications × reply rate; offers = interviews × offer rate; applications per offer = 1 ÷ (reply rate × offer rate).
  // "chance" is the probability of at least one offer if every application has the same, independent odds: 1 − (1 − p)^applications.
  T.funnel = function (o) {
    o = o || {};
    var perWeek = num(o.perWeek), weeks = num(o.weeks), a = T.rate(o.reply), b = T.rate(o.offer);
    if (!(perWeek > 0) || !(weeks > 0) || isNaN(a.pct) || isNaN(b.pct) || perWeek > 1e6 || weeks > 5200) return null;
    var apps = perWeek * weeks, p = a.pct / 100 * b.pct / 100;
    return { perWeek: perWeek, weeks: weeks, applications: apps, replyPct: a.pct, offerPct: b.pct, replyFrom: a.from, offerFrom: b.from, interviews: apps * a.pct / 100, offers: apps * p,
      perInterview: a.pct > 0 ? 100 / a.pct : null, perOffer: p > 0 ? 1 / p : null, weeksToOffer: p > 0 ? 1 / p / perWeek : null, chance: p > 0 ? (1 - Math.pow(1 - p, apps)) * 100 : 0 };
  };

  /* ---------- remote work savings ---------- */
  // Office days avoided in a year = (office days a week now − office days a week after) × working weeks.
  // Time = days × minutes one way × 2. Money = days × (travel + lunch bought out − lunch at home − extra cost of a day at home).
  // A negative result means more office days than now: the same arithmetic then shows what the change costs.
  T.remoteSavings = function (o) {
    o = o || {};
    var mins = pos(o.minutes), cost = pos(o.cost), lunch = pos(o.lunch), lunchHome = pos(o.lunchHome), home = pos(o.home), hourly = pos(o.hourly);
    var now = num(o.daysNow), next = num(o.daysNew), weeks = num(o.weeks);
    if (isNaN(now)) now = 5; if (isNaN(next)) next = 0; if (isNaN(weeks)) weeks = 46;
    if (!(now >= 0 && now <= 7) || !(next >= 0 && next <= 7) || !(weeks > 0 && weeks <= 52) || mins > 720) return null;
    if (!mins && !cost && !lunch && !lunchHome && !home) return null;
    var days = (now - next) * weeks, hours = days * mins * 2 / 60, travel = days * cost, food = days * (lunch - lunchHome), homeCost = days * home, money = travel + food - homeCost;
    return { days: days, hours: hours, workWeeks: hours / 40, travel: travel, food: food, homeCost: homeCost, money: money, month: money / 12, perDay: cost + lunch - lunchHome - home,
      minutesPerDay: mins * 2, timeValue: hourly > 0 ? hours * hourly : null, total: hourly > 0 ? money + hours * hourly : null, weeks: weeks, daysNow: now, daysNew: next };
  };

  /* ---------- cost per hire ---------- */
  // Cost per hire = (advertising + agency fees + recruiter hours × hourly cost + interviewer hours × hourly cost + tools + other) ÷ hires.
  T.costPerHire = function (o) {
    o = o || {};
    var hires = num(o.hires), recH = pos(o.recHours), intH = pos(o.intHours), recR = pos(o.recRate), intR = pos(o.intRate);
    var parts = [['Job advertising', pos(o.ads), 'out'], ['Agency and recruiter fees', pos(o.agency), 'out'], ['Recruiters’ time', recH * recR, 'time'], ['Interviewers’ time', intH * intR, 'time'],
      ['Tools and software', pos(o.tools), 'out'], ['Other costs', pos(o.other), 'out']];
    var total = parts.reduce(function (s, p) { return s + p[1]; }, 0);
    if (!(total > 0)) return null;
    var ok = hires >= 1, top = null;
    var rows = parts.map(function (p) {
      var r = { name: p[0], amount: p[1], kind: p[2], share: p[1] / total * 100, perHire: ok ? p[1] / hires : null };
      if (p[1] > 0 && (!top || p[1] > top.amount)) top = r;
      return r;
    });
    var sum = function (kind) { return rows.reduce(function (s, r) { return s + (r.kind === kind ? r.amount : 0); }, 0); };
    return { total: total, hires: ok ? hires : null, perHire: ok ? total / hires : null, parts: rows, top: top, outside: sum('out'), time: sum('time'), hours: recH + intH,
      hoursPerHire: ok ? (recH + intH) / hires : null, unpriced: (recH > 0 && !recR) || (intH > 0 && !intR) };
  };

  /* ---------- interview scorecard ---------- */
  // Weighted score = sum of (rating × weight) ÷ sum of weights, over the criteria that have a rating. Weights need not add up to 100:
  // each one counts as its share of the total. When no weight is typed at all, every criterion counts the same.
  T.scorecard = function (o) {
    o = o || {};
    var max = [4, 5, 10].indexOf(+o.max) >= 0 ? +o.max : 5, role = clean(o.role), crit = [];
    (o.criteria || []).forEach(function (c, i) { var name = clean(c && c.name); if (name) crit.push({ i: i, name: name, weight: pos(c.weight) }); });
    var total = crit.reduce(function (s, c) { return s + c.weight; }, 0), equal = crit.length > 0 && !total;
    if (equal) { crit.forEach(function (c) { c.weight = 1; }); total = crit.length; }
    crit.forEach(function (c) { c.share = total ? c.weight / total * 100 : 0; });
    var cands = (o.candidates || []).map(function (cd, ci) {
      cd = cd || {};
      var ratings = cd.ratings || [], sum = 0, w = 0, rated = 0, bad = 0, of = 0;
      var rows = crit.map(function (c) {
        if (!(c.weight > 0)) return null;
        of++;
        var raw = clean(ratings[c.i]), r = num(raw);
        if (!raw) return null;
        if (!(r >= 1 && r <= max)) { bad++; return null; }
        rated++; sum += r * c.weight; w += c.weight;
        return { rating: r, points: r * c.share / 100 };
      });
      return { name: clean(cd.name) || 'Candidate ' + 'ABCDEFGH'.charAt(ci), rated: rated, of: of, bad: bad, complete: of > 0 && rated === of, score: w > 0 ? sum / w : null,
        pct: w > 0 ? sum / w / max * 100 : null, rows: rows };
    });
    var best = -1, tie = false;
    cands.forEach(function (c, i) {
      if (!c.complete) return;
      if (best < 0 || c.score > cands[best].score + 1e-9) { best = i; tie = false; }
      else if (Math.abs(c.score - cands[best].score) <= 1e-9) tie = true;
    });
    var legend = '1 = well below what the role needs' + (max % 2 ? ', ' + (max + 1) / 2 + ' = meets it' : '') + ', ' + max + ' = well above';
    var text = ['Interview scorecard' + (role ? ': ' + role : ''), 'Candidate: ____________________   Interviewer: ____________________   Date: ____________', '',
      'Rate each criterion from 1 to ' + max + '. ' + legend + '.', '']
      .concat(crit.map(function (c, i) { return (i + 1) + '. ' + c.name + ' (weight ' + plain(c.share, 1) + '%)\n   Rating: ____   Notes:'; }))
      .concat(['', 'Weighted score = sum of (rating × weight) ÷ sum of weights = ____ out of ' + max, 'Overall notes:']).join('\n');
    return { role: role, max: max, criteria: crit, total: total, equal: equal, sum100: Math.abs(total - 100) < 1e-9, unweighted: crit.filter(function (c) { return !(c.weight > 0); }).map(function (c) { return c.name; }),
      candidates: cands, best: best, tie: tie, legend: legend, text: crit.length ? text : '' };
  };

  /* ---------- letters: more shared helpers ---------- */
  function phrase(s) { return clean(s).replace(/[.!?;,:]+$/, ''); }                 // a few words that go inside a sentence
  function mid(s) {                                                                // …and that must not start with a capital "The" or "Our" there
    return phrase(s).replace(/^(The|A|An|Our|Your|My|Their|How|What|Why|When|Where|That|This|You|We|It|Some|All|On|In|At|By|Before|After)\b/, function (w) { return w.toLowerCase(); });
  }
  function cap(s) { return s ? s.charAt(0).toUpperCase() + s.slice(1) : ''; }
  function lines(s, max) {                                                         // one item per line; bullet marks and numbering are dropped
    return String(s || '').split(/\n+/).map(function (l) { return clean(l.replace(/^\s*(?:[-•*]\s*|\d{1,2}[.)]\s+)/, '')); }).filter(Boolean).slice(0, max || 5);
  }
  function mail(subject, paras) {
    var body = paras.filter(Boolean).join('\n\n').replace(/([^.])\.\.(?!\.)/g, '$1.');
    return { subject: subject, body: body, text: 'Subject: ' + subject + '\n\n' + body };
  }

  /* ---------- thank-you email after an interview (fill-in template, three tones) ---------- */
  T.thankYou = function (f) {
    f = f || {};
    var tone = f.tone === 'warm' || f.tone === 'formal' ? f.tone : 'short';
    var name = clean(f.name) || '[Your name]', to = clean(f.to), role = clean(f.role) || '[job title]', company = clean(f.company), when = mid(f.when);
    var topic = mid(f.topic) || '[one thing you discussed]', add = sentence(f.add), at = company ? ' at ' + company : '', w = when ? ' ' + when : '';
    var p = [to ? (tone === 'formal' ? 'Dear ' : 'Hi ') + to + ',' : tone === 'formal' ? 'Dear Hiring Manager,' : 'Hello,'];
    if (tone === 'warm') {
      p.push('Thank you for taking the time to talk with me' + w + '. I really enjoyed our conversation about the ' + role + ' role' + at + '.');
      p.push('What stayed with me most was ' + topic + '.' + (add ? ' ' + add : ''));
      p.push('I came away even more interested in the job. If there is anything else you need from me, just let me know.');
      p.push('Thanks again,\n' + name);
    } else if (tone === 'formal') {
      p.push('Thank you for the opportunity to interview for the position of ' + role + at + w + '.');
      p.push('I appreciated learning about ' + topic + '.' + (add ? ' ' + add : ''));
      p.push('I remain very interested in the position and would be glad to provide any further information you need.');
      p.push('Yours sincerely,\n' + name);
    } else {
      p.push('Thank you for talking with me' + w + ' about the ' + role + ' role' + at + '. I enjoyed hearing about ' + topic + ', and I am still very interested in the job.' + (add ? ' ' + add : ''));
      p.push('I look forward to hearing about the next steps.');
      p.push('Best regards,\n' + name);
    }
    return mail(clean(f.role) ? 'Thank you for the ' + role + ' interview' : 'Thank you for the interview', p);
  };

  /* ---------- resignation letter (fill-in template: the facts, optional thanks, optional handover) ---------- */
  T.resignation = function (f) {
    f = f || {};
    var letter = f.format === 'letter', name = clean(f.name) || '[Your name]', to = clean(f.to) || '[manager’s name]', title = clean(f.title) || '[job title]', company = clean(f.company) || '[company]';
    var last = T.longDate(f.lastDay, true) || '[last working day]', written = T.longDate(f.date);
    var notice = phrase(f.notice).replace(/\s*(?:of\s+)?notice$/i, '').replace(/[’']s?$/, ''), thanksFor = mid(f.thanksFor), can = mid(f.handoverWhat);
    var p = [letter && written ? written : '', 'Dear ' + to + ','];
    p.push('Please accept this ' + (letter ? 'letter' : 'email') + ' as formal notice that I am resigning from my position as ' + title + ' at ' + company + '. My last working day will be ' + last +
      (notice ? ', which gives ' + notice + ' of notice' : '') + '.');
    if (f.thanks) p.push('Thank you for the opportunities I have had here' + (thanksFor ? ', and in particular for ' + thanksFor : '') + '.');
    if (f.handover) p.push('I want to make the handover as smooth as possible. ' + (can ? 'Before my last day I can ' + can + '.' : 'I am happy to hand over my work and brief whoever takes it on.'));
    else p.push('Please let me know what you need from me before I leave.');
    p.push((letter ? 'Sincerely,' : 'Best regards,') + '\n' + name);
    var m = mail('Resignation: ' + name, p), a = dayNum(f.date), b = dayNum(f.lastDay);
    if (letter) m.text = m.body;                           // a printed letter carries a date, not a subject line
    m.days = !isNaN(a) && !isNaN(b) ? b - a : null;        // calendar days between the letter and the last day, to compare with the contract
    return m;
  };

  /* ---------- raise request email (fill-in template; the percent and the monthly difference are plain arithmetic) ---------- */
  T.raiseRequest = function (f) {
    f = f || {};
    var sym = f.cur == null ? '$' : f.cur, per = f.period === 'month' ? 'month' : 'year';
    var name = clean(f.name) || '[Your name]', to = clean(f.to), title = clean(f.title), since = mid(f.since), cur = num(f.current), want = num(f.target);
    var curT = cur > 0 ? money(cur, sym, 0) : '[current pay]', wantT = want > 0 ? money(want, sym, 0) : '[the pay you are asking for]';
    var diff = cur > 0 && want > 0 ? want - cur : null, pct = diff != null ? diff / cur * 100 : null, wins = lines(f.achievements, 5);
    var market = clean(f.market), mNum = num(market), source = phrase(f.source);
    var p = [to ? 'Hi ' + to + ',' : 'Hello,'];
    p.push('I would like to ask you to review my pay' + (title ? ' as ' + title : '') + '.' + (since ? ' It last changed ' + since + '.' : ''));
    p.push('Here is what I have delivered' + (since ? ' since then' : '') + ':\n\n' +
      (wins.length ? wins.map(function (x) { return '- ' + x; }).join('\n') : '- [Add two or three results, each with a number if you have one]'));
    p.push('My pay is ' + curT + ' a ' + per + '. I am asking for ' + wantT + (pct > 0 ? ', an increase of ' + plain(pct, 1) + '%' : '') + '.' +
      (market ? ' For comparison, the market figure I found for this role is ' + (mNum > 0 ? money(mNum, sym, 0) : phrase(market)) + (source ? ' (source: ' + source + ')' : '') + '.' : ''));
    p.push('Could we set up a time to talk about it?');
    p.push('Thank you,\n' + name);
    var m = mail('Request to review my pay', p);
    m.pct = pct; m.diff = diff; m.perYear = diff == null ? null : per === 'month' ? diff * 12 : diff; m.perMonth = diff == null ? null : per === 'month' ? diff : diff / 12;
    return m;
  };

  /* ---------- reference request email (fill-in template, three tones) ---------- */
  T.referenceRequest = function (f) {
    f = f || {};
    var tone = f.tone === 'formal' || f.tone === 'short' ? f.tone : 'warm', how = ['call', 'letter', 'form', 'linkedin'].indexOf(f.how) >= 0 ? f.how : 'call';
    var name = clean(f.name) || '[Your name]', to = clean(f.to), role = clean(f.role), company = clean(f.company), by = mid(f.by), rel = mid(f.relation), points = lines(f.points, 4);
    var job = role ? article(role) + ' ' + role + ' role' + (company ? ' at ' + company : '') : company ? 'a role at ' + company : 'a new role';
    var pick = function (warm, formal, short) { return tone === 'formal' ? formal : tone === 'short' ? short : warm; };
    var p = [to ? pick('Hi ', 'Dear ', 'Hi ') + to + ',' : 'Hello,'];
    p.push(pick('I hope you are well. I am applying for ' + job + ', and I would be very grateful if you would be a reference for me.',
      'I am applying for ' + job + ' and am writing to ask whether you would be willing to act as a reference for me.',
      'I am applying for ' + job + '. Would you be willing to be a reference for me?') +
      (rel ? ' We worked together when ' + rel + pick(', so you know my work well.', '.', '.') : ''));
    p.push(how === 'letter' ? 'The employer asks for a short written reference' + (by ? ', and I would need it by ' + by : '') + '.'
      : how === 'form' ? 'The employer will send you a short online form' + (by ? ' to fill in by ' + by : '') + '.'
      : how === 'linkedin' ? pick('A short recommendation on my LinkedIn profile would help a lot', 'A brief recommendation on my LinkedIn profile would be most helpful', 'A short LinkedIn recommendation would help') + (by ? ', if possible by ' + by : '') + '.'
      : pick('The employer may contact you by phone or email', 'The employer may contact you by telephone or email', 'They may call or email you') + (by ? ', most likely before ' + by : '') + '.');
    if (points.length) p.push(pick('If it helps, these are the points that matter most for this role:', 'The points most relevant to this role are:', 'What matters most for this role:') + '\n\n' + points.map(function (x) { return '- ' + x; }).join('\n'));
    if (f.attach) p.push(pick('I have attached my current resume and the job description so you have the details to hand.', 'I have attached my current resume and the job description for your reference.', 'My resume and the job description are attached.'));
    p.push(pick('If you would rather not, or the timing is bad, I completely understand. Just let me know either way.', 'I fully understand if you are not able to do this. Please let me know either way.', 'No problem at all if you cannot. Please let me know either way.'));
    p.push(pick('Thank you,', 'Yours sincerely,', 'Thanks,') + '\n' + name);
    return mail(pick('Could you be a reference for me?', 'Request for a reference', 'Reference request'), p);
  };

  /* ---------- LinkedIn headline and About (fill-in templates; the limits are LinkedIn's own field lengths) ---------- */
  T.HEADLINE_MAX = 220; T.ABOUT_MAX = 2600;
  T.linkedin = function (f) {
    f = f || {};
    var role = clean(f.role) || '[Your job title]', years = yearsText(f.years), next = mid(f.next), result = sentence(f.result);
    var st = String(f.strengths || '').split(/[,;\n]+/).map(clean).filter(Boolean).slice(0, 4);
    var fit = function (make) {                            // leave strengths off the end until the line fits; cut at a word only as the last resort
      for (var k = st.length; k >= 0; k--) { var s = make(st.slice(0, k)); if (s.length <= T.HEADLINE_MAX) return s; }
      var cut = make([]).slice(0, T.HEADLINE_MAX + 1);
      return (/\s/.test(cut) ? cut.replace(/\s+\S*$/, '') : cut.slice(0, T.HEADLINE_MAX)).replace(/[\s|,·]+$/, '');
    };
    var made = [
      ['Keywords', fit(function (a) { return [role].concat(a).join(' | '); })],
      ['One sentence', fit(function (a) { return role + (years ? ' with ' + years + ' of experience' : '') + (a.length ? (years ? ' in ' : ' focused on ') + andList(a) : ''); })],
      ['What you want next', fit(function (a) { return role + (a.length ? ' | ' + a.join(', ') : '') + (next ? ' | Open to ' + next : years ? ' | ' + years : ''); })]
    ], seen = {}, headlines = [];
    made.forEach(function (h) { if (!seen[h[1]]) { seen[h[1]] = 1; headlines.push({ kind: h[0], text: h[1], length: h[1].length, left: T.HEADLINE_MAX - h[1].length }); } });
    var a = [years ? 'I am ' + article(role) + ' ' + role + ' with ' + years + ' of experience.' : 'I work as ' + article(role) + ' ' + role + '.'];
    if (st.length) a.push((st.length === 1 ? 'My strongest area is ' : 'My strongest areas are ') + andList(st) + '.');
    if (result) a.push(result);
    if (next) a.push('I am now looking for ' + next + '.');
    a.push('The best way to reach me is a message here on LinkedIn.');
    var about = a.join(' ').replace(/([^.])\.\.(?!\.)/g, '$1.');
    return { headlines: headlines, about: about, aboutLength: about.length, strengths: st, empty: !clean(f.role) && !st.length && !years && !next && !result };
  };

  /* ---------- interview answer: situation, task, action, result ---------- */
  var NUMBER = /\d|\b(?:one|two|three|four|five|six|seven|eight|nine|ten|eleven|twelve|twenty|thirty|forty|fifty|hundred|thousand|million|billion|half|halved|double|doubled|twice|triple|tripled|third|quarter|dozen|percent)\b/i;
  T.WPM = 140;                                             // a calm speaking pace, in words a minute
  T.speak = function (sec) { sec = Math.max(0, Math.round(sec)); var m = Math.floor(sec / 60), s = sec % 60; return m ? m + ' min' + (s ? ' ' + s + ' s' : '') : s + ' s'; };
  T.star = function (f) {
    f = f || {};
    var PARTS = [['situation', 'The situation', 'Where and when it happened, in one or two sentences.'], ['task', 'The task', 'What you were asked to do, or the problem that was yours to solve.'],
      ['action', 'The action', 'The steps you took yourself, in order.'], ['result', 'The result', 'What changed because of it, with a number if you have one.']];
    var txt = {}, n = {}, body = [], items = [], add = function (level, t, d) { items.push({ level: level, t: t, d: d }); };
    PARTS.forEach(function (p) { txt[p[0]] = sentence(f[p[0]]); n[p[0]] = wordCount(txt[p[0]]); if (txt[p[0]]) body.push(txt[p[0]]); });
    var learned = sentence(f.learned); if (learned) body.push(learned);
    var text = body.join('\n\n'), words = wordCount(text), sec = Math.round(words / T.WPM * 60), time = T.speak(sec);
    if (!words) return { empty: true, text: '', words: 0, seconds: 0, time: T.speak(0), checks: [], fixes: 0, complete: false, parts: n };
    PARTS.forEach(function (p) { if (!txt[p[0]]) add('fix', p[1] + ' is missing', p[2]); });
    var basis = words + ' words at ' + T.WPM + ' words a minute. ';
    if (sec < 45) add('fix', 'Too short: about ' + time, basis + 'That leaves little room for what you did. Add the steps you took, one sentence each.');
    else if (sec < 60) add('warn', 'A little short: about ' + time, basis + 'Aim for 60 to 90 seconds: add one more step to the action.');
    else if (sec <= 90) add('ok', 'Good length: about ' + time, basis + 'That is inside the 60 to 90 seconds this page aims for.');
    else if (sec <= 120) add('warn', 'A little long: about ' + time, basis + 'Aim for 60 to 90 seconds: shorten the situation first.');
    else add('fix', 'Too long: about ' + time, basis + 'Keep one situation, your two or three main steps and the result.');
    if (txt.result) {
      if (NUMBER.test(txt.result)) add('ok', 'The result has a number', 'A figure makes the outcome easy to remember and easy to check.');
      else add('warn', 'No number in the result', 'Say how much, how many or how fast: a percent, an amount of money, a count, a date met. If nothing was measured, say what people could do afterwards that they could not do before.');
    }
    if (txt.action) {
      var me = (txt.action.match(/\bi\b(?!\.e)/gi) || []).length, we = (txt.action.match(/\bwe\b/gi) || []).length;
      if (!me) add('fix', 'The action never says “I”', (we ? '“We” appears ' + we + ' time' + (we === 1 ? '' : 's') + '. ' : '') + 'The answer is about your part. Say what you did yourself: “I proposed…”, “I wrote…”, “I persuaded…”.');
      else if (we > me) add('warn', 'More “we” than “I” in the action', '“We” appears ' + we + ' times and “I” ' + me + '. Keep the team in the situation and make the action about your own steps.');
      else add('ok', 'The action is about what you did', '“I” appears ' + me + ' time' + (me === 1 ? '' : 's') + (we ? ', “we” ' + we : '') + '.');
      if (n.situation + n.task > n.action) add('warn', 'The setup is longer than the action', 'The situation and the task take ' + (n.situation + n.task) + ' words, the action ' + n.action + '. Cut the background to two or three sentences and spend the time on what you did.');
      else if (txt.situation || txt.task) add('ok', 'The action gets more room than the setup', 'The action takes ' + n.action + ' words, the situation and the task ' + (n.situation + n.task) + '.');
    }
    var rank = { fix: 0, warn: 1, info: 2, ok: 3 };
    items.sort(function (a, b) { return rank[a.level] - rank[b.level]; });
    return { text: text, words: words, seconds: sec, time: time, checks: items, fixes: items.filter(function (i) { return i.level !== 'ok'; }).length,
      complete: PARTS.every(function (p) { return !!txt[p[0]]; }), parts: n };
  };

  /* ---------- resume bullet point: verb + what you did + result ---------- */
  var STRONG = ('accelerated achieved analyzed audited automated boosted built captured championed closed coached consolidated converted created cut debugged decreased delivered deployed designed developed ' +
    'directed doubled drafted drove earned edited eliminated engineered established exceeded expanded fixed formed founded generated grew guided halved hired identified implemented improved increased ' +
    'integrated introduced launched led lifted lowered managed mapped measured mentored merged migrated modernized negotiated onboarded opened optimized organized overhauled owned piloted planned presented ' +
    'prevented produced published raised ran rebuilt recovered recruited redesigned reduced refactored replaced researched resolved restructured retained rewrote saved scaled secured set shipped shortened ' +
    'simplified sold solved standardized started streamlined taught tested trained translated tripled unified won wrote').split(' ');
  var STRONG_SET = {}; STRONG.forEach(function (w) { STRONG_SET[w] = 1; });
  var ING = { built: 'building', cut: 'cutting', drove: 'driving', grew: 'growing', led: 'leading', ran: 'running', rebuilt: 'rebuilding', rewrote: 'rewriting', set: 'setting', sold: 'selling', taught: 'teaching',
    won: 'winning', wrote: 'writing', made: 'making', took: 'taking', brought: 'bringing', kept: 'keeping', got: 'getting', gave: 'giving', held: 'holding', met: 'meeting', paid: 'paying', sent: 'sending',
    spent: 'spending', found: 'finding', began: 'beginning', beat: 'beating', hit: 'hitting', put: 'putting', saw: 'seeing', oversaw: 'overseeing', spoke: 'speaking', split: 'splitting', shut: 'shutting' };
  var WEAK = { responsible: 'Replace “Responsible for” with the action itself: Led, Ran, Managed, Built.', helped: 'Say what your own part was: Built, Wrote, Trained, Fixed.', assisted: 'Say what your own part was: Built, Wrote, Trained, Fixed.',
    worked: 'Say what you made or changed: Built, Wrote, Designed, Fixed.', participated: 'Say what you contributed: Presented, Tested, Organized.', involved: 'Say what you contributed: Presented, Tested, Organized.',
    tasked: 'Say what you did, not what you were told to do.', duties: 'Name one thing you got done instead of a list of duties.', was: 'Start with the action: Led, Built, Cut, Launched.', were: 'Start with the action: Led, Built, Cut, Launched.',
    did: 'Name the action: Built, Wrote, Tested, Sold.', tried: 'Say what you finished, and what it changed.', attempted: 'Say what you finished, and what it changed.', had: 'Start with the action: Led, Built, Cut, Launched.' };
  var DULL = [['responsible for', 'start with what you did: Led, Ran, Built'], ['duties included', 'name one result instead of a list of duties'], ['tasked with', 'say what you did, not what you were told to do'],
    ['in charge of', 'write “Led” or “Managed” and add the size of the thing'], ['helped with', 'name the part that was yours'], ['helped to', 'name the part that was yours'], ['worked on', 'say what you built, wrote or changed'],
    ['assisted with', 'name the part that was yours'], ['assisted in', 'name the part that was yours'], ['participated in', 'say what you contributed'], ['involved in', 'say what you contributed'], ['was part of', 'say what you contributed']];
  T.STRONG = STRONG; T.LINE = 100;                          // about 100 characters fit on one line of a one-column resume: an estimate, not a rule
  // "Rebuilt" -> "rebuilding": from the list for irregular verbs, by rule for -ed verbs, '' when the form is not known
  T.gerund = function (verb) {
    var bits = clean(verb).split(' '), w = (bits[0] || '').toLowerCase(), g = ING[w] || (/ied$/.test(w) ? w.slice(0, -3) + 'ying' : /eed$/.test(w) ? w.slice(0, -1) + 'ing' : /[a-z]{2,}ed$/.test(w) ? w.slice(0, -2) + 'ing' : '');
    return g ? [g].concat(bits.slice(1)).join(' ') : '';
  };
  function pastVerb(w) { return !!(STRONG_SET[w] || ING[w] || (/[a-z]{2,}ed$/.test(w) && !/eed$/.test(w) && w !== 'hundred')); }
  T.bullet = function (f) {
    f = f || {};
    var verb = cap(phrase(f.verb)), what = mid(f.what), result = phrase(f.result), items = [], add = function (level, t, d) { items.push({ level: level, t: t, d: d }); };
    if (!verb && !what && !result) return { empty: true, variants: [], checks: [], passed: 0, of: 0 };
    var first = (verb.split(' ')[0] || '').toLowerCase(), r0 = (result.split(' ')[0] || '').toLowerCase(), base = [verb, what].filter(Boolean).join(' ');
    var kind = !result ? 'none' : pastVerb(r0) ? 'verb' : /[a-z]{3,}ing$/.test(r0) ? 'ing' : 'other';
    var r = kind === 'other' ? result : result.charAt(0).toLowerCase() + result.slice(1), g = what ? T.gerund(verb) : '', v = [];
    if (kind === 'verb') { v.push(['Action first', base + ', which ' + r], ['Short', base + ' and ' + r]); if (g) v.push(['Result first', cap(r) + ' by ' + g + ' ' + what]); }
    else if (kind === 'ing') v.push(['Action first', base + ', ' + r]);
    else if (kind === 'other') { v.push(['Action first', base + ': ' + result], ['Short', base + '; ' + result]); if (g) v.push(['Result first', cap(result) + ' after ' + g + ' ' + what]); }
    else v.push(['Action only', base]);
    var variants = v.map(function (x) { return { kind: x[0], text: x[1], length: x[1].length, lines: Math.max(1, Math.ceil(x[1].length / T.LINE)) }; }), main = variants[0], all = [verb, what, result].join(' ');
    if (!verb) add('fix', 'No action verb', 'Start the line with what you did, in one word: Built, Led, Cut, Launched, Negotiated.');
    else if (WEAK[first]) add('fix', '“' + cap(first) + '” is a weak way to start', WEAK[first]);
    else if (STRONG_SET[first]) add('ok', 'Starts with a strong verb: ' + cap(first), 'One word that says what you did.');
    else add('info', '“' + cap(first) + '” is not on our verb list', 'Keep it if it is a past-tense verb that names exactly what you did. The verbs this page counts as strong are listed below.');
    if (!what) add('fix', 'Nothing after the verb', 'Say what you built, led, changed or sold, and for whom.');
    if (kind === 'none') add('fix', 'No result', 'Add what changed because of your work: time saved, money earned, errors avoided, people served.');
    else if (kind !== 'verb') add('info', 'Start the result with a past-tense verb', 'Written as “cut…”, “saved…”, “raised…” or “won…”, the result fits more sentence patterns and you get more variants.');
    if (NUMBER.test(what + ' ' + result)) add('ok', 'Has a number', 'A figure tells the reader how big the work was.');
    else add('warn', 'No number', 'Add how much, how many or how fast: a percent, an amount, a count of users, a team size, a deadline.');
    if (main.length < 40) add('warn', 'Short: ' + main.length + ' characters', 'The line says little so far. Add what the work was for and what it changed.');
    else if (main.length <= 2 * T.LINE) add('ok', 'Length is fine: ' + main.length + ' characters, about ' + main.lines + ' line' + (main.lines === 1 ? '' : 's'), 'One to two lines is easy to scan.');
    else add('warn', 'Long: ' + main.length + ' characters, about ' + main.lines + ' lines', 'Keep a bullet point to two lines. Cut adjectives, and tools that are already in your skills list.');
    var dull = findPhrases(all, DULL);
    if (dull.length) add('fix', 'Duty wording: ' + dull.map(function (x) { return '“' + x.term + '”'; }).join(', '), cap(dull.map(function (x) { return '“' + x.term + '”: ' + x.tip; }).join('. ')) + '.');
    else add('ok', 'No “responsible for” wording', 'The line describes something you did, not a duty you held.');
    if (/\b(?:i|my|we)\b(?!\.e)/i.test(all)) add('info', 'Leave out “I”, “my” and “we”', 'Resume bullet points start with the verb; the reader knows the line is about you.');
    var rank = { fix: 0, warn: 1, info: 2, ok: 3 }, scored = items.filter(function (i) { return i.level !== 'info'; });
    items.sort(function (a, b) { return rank[a.level] - rank[b.level]; });
    return { variants: variants, checks: items, kind: kind, passed: scored.filter(function (i) { return i.level === 'ok'; }).length, of: scored.length };
  };

  /* ---------- date ranges in running text: "Jan 2021 – Mar 2023", "2019–2021", "03/2020 - present" ---------- */
  var MON3 = ['jan', 'feb', 'mar', 'apr', 'may', 'jun', 'jul', 'aug', 'sep', 'oct', 'nov', 'dec'];
  var MON = 'jan(?:uary)?|feb(?:ruary)?|mar(?:ch)?|apr(?:il)?|may|june?|july?|aug(?:ust)?|sep(?:t(?:ember)?)?|oct(?:ober)?|nov(?:ember)?|dec(?:ember)?';
  var POINT = '(?:(?:' + MON + ')\\.?,?\\s+\\d{4}|\\d{1,2}[/.]\\d{4}|\\d{4}[/.-]\\d{1,2}(?![/.\\d-])|\\d{4}|present|current|now|today|ongoing|date)';
  var RANGE_SRC = '(^|[^a-z0-9/.-])(' + POINT + ')\\s*(?:[-–—−]|to|until|till|through)\\s*(' + POINT + ')(?![a-z0-9])';
  function monthNow(today) {                               // "2026-11-13" (or nothing: the real date) -> months since year 0
    var m = /^(\d{4})-(\d{2})/.exec(today || ''), d = new Date();
    return m ? +m[1] * 12 + +m[2] - 1 : d.getFullYear() * 12 + d.getMonth();
  }
  function monthOf(s, end, now) {                          // one end of a range -> months since year 0; a bare year means January at the start and December at the end
    s = s.toLowerCase().trim();
    if (/^(?:present|current|now|today|ongoing|date)$/.test(s)) return end ? now : NaN;
    var m, y, mo;
    if ((m = /^([a-z]+)\.?,?\s+(\d{4})$/.exec(s))) { mo = MON3.indexOf(m[1].slice(0, 3)); y = +m[2]; }
    else if ((m = /^(\d{1,2})[/.](\d{4})$/.exec(s))) { mo = +m[1] - 1; y = +m[2]; }
    else if ((m = /^(\d{4})[/.-](\d{1,2})$/.exec(s))) { y = +m[1]; mo = +m[2] - 1; }
    else if ((m = /^(\d{4})$/.exec(s))) { y = +m[1]; mo = end ? 11 : 0; }
    else return NaN;
    if (!(mo >= 0 && mo <= 11) || y < 1950 || y > Math.floor(now / 12) + 1) return NaN;
    return Math.min(y * 12 + mo, end ? now : Infinity);
  }
  T.monthLabel = function (i) { return MONTH_NAMES[mod(i, 12)].slice(0, 3) + ' ' + Math.floor(i / 12); };
  // Every date range the text holds, with the line it stands on. Ranges that end before they start, and dates that are not dates, are left out.
  T.dateRanges = function (text, today) {
    var now = monthNow(today), out = [];
    String(text || '').split(/\r?\n/).forEach(function (ln, i) {
      var rx = new RegExp(RANGE_SRC, 'gi'), m;
      while ((m = rx.exec(ln))) {
        var a = monthOf(m[2], false, now), b = monthOf(m[3], true, now);
        if (!isNaN(a) && !isNaN(b) && a <= b) out.push({ start: a, end: b, open: /^[a-z]+$/i.test(m[3].trim()), years: /^\d{4}$/.test(m[2].trim()) || /^\d{4}$/.test(m[3].trim()), raw: clean(m[2] + ' – ' + m[3]), line: clean(ln), at: i });
      }
    });
    return out;
  };
  // Breaks of more than `min` months (six unless told otherwise) between the ranges, and the time since the last one ended.
  T.gaps = function (ranges, today, min) {
    var now = monthNow(today), list = (ranges || []).slice().sort(function (x, y) { return x.start - y.start || x.end - y.end; }), out = [], last = null;
    min = min == null ? 6 : min;
    list.forEach(function (r) {
      if (last && r.start - last.end - 1 > min) out.push({ months: r.start - last.end - 1, from: last.end + 1, to: r.start - 1, after: last, before: r });
      if (!last || r.end > last.end) last = r;
    });
    if (last && now - last.end > min) out.push({ months: now - last.end, from: last.end + 1, to: now, after: last, before: null });
    return out;
  };

  /* ---------- resume review: six plain checks, ten points ---------- */
  var SECTIONS = [
    ['experience', /^(?:work|professional|relevant|career)?\s*(?:experience|employment(?: history)?|work history|career history)$/i],
    ['education', /^(?:education(?: (?:and|&) training)?|academic background|studies|qualifications)$/i],
    ['skills', /^(?:technical|key|core|hard|top)?\s*(?:skills(?: (?:and|&) (?:tools|technologies))?|competencies|technologies|tech stack|stack|tools)$/i],
    ['summary', /^(?:(?:professional|career|personal)?\s*(?:summary|profile|objective|statement)|about(?: me)?)$/i],
    ['other', /^(?:(?:side |personal )?projects|certifications?|certificates|languages|awards|publications|interests|hobbies|references|volunteering|volunteer work|courses|training|contact|links)$/i]
  ];
  function heading(s) {                                    // "Experience", "SKILLS:", "Skills: Python, Go" -> { section, rest }
    var m = /^([A-Za-z &]{3,40}?)\s*:\s*(.*)$/.exec(s), name = (m ? m[1] : s).trim(), rest = m ? m[2].trim() : '';
    if (name.split(/\s+/).length > 4 || /[.!?]$/.test(name)) return null;
    for (var k = 0; k < SECTIONS.length; k++) if (SECTIONS[k][1].test(name)) return { section: SECTIONS[k][0], rest: rest };
    return null;
  }
  function cut(s, n) { s = clean(s); n = n || 140; return s.length > n ? s.slice(0, n - 1).replace(/\s+\S*$/, '') + '…' : s; }
  function hasFigure(s) { return /\d/.test(String(s).replace(/\b(?:19|20)\d{2}\b/g, '')) || /\b(?:percent|doubled|halved|tripled)\b/i.test(s); }
  T.REVIEW = { screen: 12, summary: 60, before: 10, list: 20, gap: 6, onePage: 650, twoPages: 1300, thin: 250, least: 150 };     // the thresholds, named on the page under “How it works”
  T.resumeReview = function (text, today) {
    text = String(text || '').replace(/\r/g, '');
    var words = wordCount(text), R = T.REVIEW;
    if (words < 80) return { error: 'short', words: words };
    // every line gets a section: the part before the first heading is "top"; a line with a date range starts the experience when no heading did
    var rows = [], sec = 'top', named = false;
    text.split('\n').forEach(function (raw, i) {
      var s = raw.trim(); if (!s) return;
      var h = BULLET.test(raw) ? null : heading(s), ranges = T.dateRanges(s, today), row = { at: i, s: s, head: false, bullet: BULLET.test(raw), words: wordCount(s), lines: Math.max(1, Math.ceil(s.length / T.LINE)), ranges: ranges };
      if (h && !(sec === 'skills' && h.section === 'other' && h.rest)) {           // "Languages: Python, Go" inside the skills block is a list, not a new section
        sec = h.section; if (sec === 'experience') named = true;
        row.head = true; row.rest = h.rest;
      } else if (ranges.length && !named && (sec === 'top' || sec === 'summary' || sec === 'skills')) sec = 'experience';
      row.sec = sec; rows.push(row);
    });
    var of = function (name) { return rows.filter(function (r) { return r.sec === name && !r.head; }); };
    var exp = of('experience'), bullets = exp.filter(function (r) { return r.bullet; });
    if (!bullets.length) bullets = exp.filter(function (r) { return r.words >= 8 && !r.ranges.length; });
    var checks = [], fixes = [], strengths = [];
    var done = function (id, name, points, max, t, good) { checks.push({ id: id, name: name, points: points, max: max, t: t }); if (points === max && good) strengths.push({ name: name, t: t, d: good }); };
    var fix = function (id, t, d, q) { fixes.push({ id: id, t: t, d: d, q: (q || []).filter(Boolean).map(function (x) { return cut(x); }) }); };

    // 1. the first screen: what the first 12 lines of the page hold (a long line counts as several)
    var line = 0, firstJob = null, hold = {}, lost = 0;
    rows.forEach(function (r) {
      var from = line + 1; line += r.lines;
      if (r.sec === 'experience' && !r.head && firstJob == null) firstJob = from;
      if (!(r.head && r.sec === 'experience')) for (var k = from; k <= Math.min(line, R.screen); k++) hold[r.sec] = (hold[r.sec] || 0) + 1;      // the heading “Experience” alone is not a job
    });
    var NAMES = { top: 'your name and contact details', summary: 'the summary', skills: 'the skills list', education: 'education', other: 'other sections', experience: 'experience' };
    var held = ['top', 'summary', 'skills', 'education', 'other', 'experience'].filter(function (k) { return hold[k]; }).map(function (k) { return NAMES[k] + ' (' + hold[k] + ')'; });
    var summary = rows.filter(function (r) { return r.sec === 'summary' && (!r.head || r.rest); }).concat(named || firstJob != null ? rows.filter(function (r) { return r.sec === 'top' && r.words >= 15; }) : []);
    var sumWords = summary.reduce(function (s, r) { return s + (r.head ? wordCount(r.rest) : r.words); }, 0);
    var skillRows = rows.filter(function (r) { return r.sec === 'skills' && (r.head ? r.rest : true); }), seen = {}, skills = [];
    skillRows.forEach(function (r) {
      (r.head ? r.rest : r.s.replace(/^\s*(?:[-*•·▪◦‣–—>]|\d{1,2}[.)])\s+/, '').replace(/^[A-Za-z &/]{2,30}:\s*/, '')).replace(/[()]/g, ',').split(/[,;•·|]+/).forEach(function (x) {
        x = clean(x).replace(/^(?:and|&)\s+/i, '').replace(/\.$/, ''); var k = x.toLowerCase();
        if (x && x.length <= 40 && x.split(' ').length <= 4 && !seen[k]) { seen[k] = 1; skills.push(x); }
      });
    });
    var skillsFirst = skillRows.length && (firstJob == null || skillRows[0].at < (exp[0] ? exp[0].at : Infinity));
    if (firstJob == null) { lost = 2; fix('screen', 'No job with dates was found', 'We could not find an “Experience” heading or a line with a date range, so the review cannot tell where your work history starts. Put each job on its own line with its dates.', []); }
    else {
      if (firstJob > R.screen) { lost++; fix('screen', 'The first job starts on line ' + firstJob, 'The first ' + R.screen + ' lines hold ' + andList(held) + '. A reader who stops there has not seen where you worked. Move the latest job up, or shorten what stands above it.', [(summary[0] || skillRows[0] || rows[0]).s]); }
      if (sumWords > R.summary) { lost++; fix('screen', 'The summary runs to ' + sumWords + ' words', 'Keep it to two or three lines (up to ' + R.summary + ' words): your role, your years of experience and your strongest result. The rest belongs under the jobs.', [summary[0].s]); }
      if (skillsFirst && skills.length > R.before) { lost++; fix('screen', skills.length + ' skills are listed before any job', 'A long list of tools ahead of the work history says what you have touched, not what you did with it. Keep up to ' + R.before + ' there, or move the list below the experience.', [skillRows[0].head ? skillRows[0].rest : skillRows[0].s]); }
    }
    done('screen', 'First screen', Math.max(0, 2 - lost), 2, firstJob == null ? 'No job found on the page' : lost ? 'The first ' + R.screen + ' lines hold ' + andList(held) : 'Your latest job starts on line ' + firstJob + ' of the page',
      'The first ' + R.screen + ' lines hold ' + andList(held) + '.');

    // 2. wording: duties instead of results
    var duty = (bullets.length ? bullets : exp).filter(function (r) { return findPhrases(r.s, DULL).length; });
    if (duty.length) fix('wording', duty.length + ' line' + (duty.length === 1 ? ' describes a duty' : 's describe duties') + ', not a result', 'Lines that open with “' + findPhrases(duty[0].s, DULL)[0].term + '” and similar say what the job was. Start each with what you did (Built, Led, Cut) and end with what it changed.', duty.slice(0, 5).map(function (r) { return r.s; }));
    done('wording', 'Wording', duty.length === 0 ? 2 : duty.length <= 2 ? 1 : 0, 2, duty.length ? duty.length + ' line' + (duty.length === 1 ? '' : 's') + ' with duty wording' : 'No “responsible for” wording',
      'None of the lines under your jobs uses “responsible for”, “worked on”, “participated in” or the other duty phrases on our list.');

    // 3. numbers
    var withNum = bullets.filter(function (r) { return hasFigure(r.s); }), share = bullets.length ? withNum.length / bullets.length : 0, plain3 = bullets.filter(function (r) { return !hasFigure(r.s); });
    if (!bullets.length) fix('numbers', 'No bullet points found under your jobs', 'Describe each job in three to five short lines that start with a dash, one piece of work per line.', []);
    else if (share < 0.5) fix('numbers', withNum.length + ' of ' + bullets.length + ' bullet points contain a number', 'Add a figure where you honestly can: how many users, how much faster, what budget, how large the team. Half or more of the lines with a number earns full points.', plain3.slice(0, 3).map(function (r) { return r.s; }));
    done('numbers', 'Numbers', share >= 0.5 ? 2 : share >= 0.25 ? 1 : 0, 2, bullets.length ? withNum.length + ' of ' + bullets.length + ' bullet points have a number' : 'No bullet points found',
      withNum.length ? 'For example: “' + cut(withNum[0].s, 110) + '”' : '');

    // 4. skills: the list against the experience text
    var expText = (exp.length ? exp : rows.filter(function (r) { return r.sec !== 'skills'; })).map(function (r) { return r.s; }).join('\n');
    var unused = skills.filter(function (x) { return !new RegExp('(^|[^a-z0-9+#])' + x.toLowerCase().replace(/[.*+?^${}()|[\]\\\/]/g, '\\$&') + '(?![a-z0-9+#])', 'i').test(expText); });
    var uShare = skills.length ? unused.length / skills.length : 0, sPts = !skills.length ? 0.5 : (uShare <= 1 / 3 ? 1 : uShare <= 2 / 3 ? 0.5 : 0) + (skills.length <= R.list ? 0.5 : 0);
    if (!skills.length) fix('skills', 'No skills line found', 'Add one line headed “Skills” with the tools and methods you can be asked about, each of them also named in the job where you used it.', []);
    else {
      if (uShare > 1 / 3) fix('skills', unused.length + ' of ' + skills.length + ' listed skills never appear under a job', 'Not found in your experience text: ' + unused.slice(0, 12).join(', ') + (unused.length > 12 ? ' and ' + (unused.length - 12) + ' more' : '') + '. Name each skill in the job where you used it, in the same spelling, or take it off the list.', [skillRows[0].head ? skillRows[0].rest : skillRows[0].s]);
      if (skills.length > R.list) fix('skills', 'The skills list has ' + skills.length + ' entries', 'Past ' + R.list + ' a list stops saying what you are good at. Keep the skills the jobs you want ask for and that your experience backs up.', []);
    }
    done('skills', 'Skills', sPts, 1.5, !skills.length ? 'No skills line found' : unused.length ? unused.length + ' of ' + skills.length + ' listed skills are not in the experience text' : 'All ' + skills.length + ' listed skills appear under a job',
      skills.length + ' skills are listed, and ' + (unused.length ? 'all but ' + unused.length + ' of them also appear' : 'every one of them also appears') + ' in the text of your jobs.');

    // 5. gaps between the date ranges that could be read
    var ranges = []; rows.forEach(function (r) { r.ranges.forEach(function (x) { ranges.push(x); }); });
    var gaps = T.gaps(ranges, today, R.gap);
    if (!ranges.length) fix('gaps', 'The dates could not be read', 'We found no date range in a form we can read, such as “Jan 2021 – Mar 2023”, “2019–2021” or “03/2020 – present”, so gaps were not checked. Give every job a start and an end in one of these forms.', []);
    gaps.forEach(function (g) {
      if (g.before) fix('gaps', 'A break of ' + g.months + ' months: ' + T.monthLabel(g.from) + ' to ' + T.monthLabel(g.to), 'Nothing is listed between these two entries' + (g.after.years || g.before.years ? ' (a range given in years only is counted from January of the first year to December of the last)' : '') + '. A gap is not a fault, but a reader will ask. Add one line saying what you did: study, care, travel, freelance work.', [g.after.line, g.before.line]);
      else fix('gaps', 'Nothing listed for the last ' + g.months + ' months', 'Your latest entry ends in ' + T.monthLabel(g.after.end) + '. If you are still in that job, write “present”. If not, add a line for what you have done since.', [g.after.line]);
    });
    done('gaps', 'Gaps', !ranges.length ? 0.5 : gaps.length === 0 ? 1 : gaps.length === 1 ? 0.5 : 0, 1, !ranges.length ? 'Dates could not be read' : gaps.length ? gaps.length + ' break' + (gaps.length === 1 ? '' : 's') + ' of more than ' + R.gap + ' months' : 'No break of more than ' + R.gap + ' months',
      ranges.length + ' date range' + (ranges.length === 1 ? ' was' : 's were') + ' read, and none of them leaves more than ' + R.gap + ' months uncovered.');

    // 6. length
    var long = exp.filter(function (r) { return r.s.length > 2 * T.LINE; }), pages = words <= R.onePage ? 'about one page' : words <= R.twoPages ? 'about two pages' : 'more than two pages';
    var lenPts = words >= R.thin && words <= R.twoPages ? 1 : words >= R.least && words < R.thin ? 0.5 : 0;
    if (words < R.thin) fix('length', 'Short: ' + words + ' words', 'A full page holds roughly 450 to 650 words. Check that the whole resume was pasted, then give each job three to five lines about what you did and what changed.', []);
    else if (words > R.twoPages) fix('length', 'Long: ' + fmt(words) + ' words, more than two pages', 'Cut jobs older than ten years to one line each and keep the detail for the work that matches the jobs you want.', []);
    if (long.length) fix('length', long.length + ' line' + (long.length === 1 ? '' : 's') + ' longer than two lines of the page', 'A bullet point of more than about ' + 2 * T.LINE + ' characters is a paragraph. Split it, or keep the one result that matters.', long.slice(0, 3).map(function (r) { return r.s; }));
    done('length', 'Length', lenPts + (long.length ? 0 : 0.5), 1.5, fmt(words) + ' words, ' + pages + (long.length ? '; ' + long.length + ' over-long line' + (long.length === 1 ? '' : 's') : ''),
      fmt(words) + ' words is ' + pages + ', and no line under your jobs runs past two lines.');

    var score = checks.reduce(function (s, c) { return s + c.points; }, 0), order = {};
    checks.forEach(function (c) { order[c.id] = c.max - c.points; });
    fixes.sort(function (a, b) { return order[b.id] - order[a.id]; });        // the checks that cost the most points come first
    return { score: score, verdict: score >= 8.5 ? 'Reads well on a first skim' : score >= 6.5 ? 'Solid, with a few things to tighten' : score >= 4.5 ? 'Readable, but the best points are hard to find' : 'Hard to skim: start with the first fixes on the list',
      words: words, pages: pages, checks: checks, strengths: strengths, weaknesses: checks.filter(function (c) { return c.points < c.max; }), fixes: fixes,
      bullets: bullets.length, withNumbers: withNum.length, skills: skills, unused: unused, ranges: ranges, gaps: gaps, firstJob: firstJob, summaryWords: sumWords, duty: duty.length };
  };

  /* ---------- LinkedIn profile review: headline and About ---------- */
  var BUZZ = ['passionate', 'results-driven', 'results-oriented', 'guru', 'ninja', 'rockstar', 'rock star', 'wizard', 'synergy', 'synergies', 'thought leader', 'visionary', 'detail-oriented', 'team player',
    'self-starter', 'go-getter', 'hard-working', 'hardworking', 'motivated', 'innovative', 'strategic thinker', 'proven track record', 'outside the box', 'out of the box', 'game-changer', 'seasoned', 'driven'];
  var ROLE = /\b(?:engineer|developer|programmer|designer|architect|analyst|scientist|researcher|manager|director|lead|head of|officer|founder|co-founder|owner|president|vp|ceo|cto|cfo|coo|cmo|consultant|advisor|adviser|specialist|strategist|coordinator|administrator|assistant|associate|recruiter|sourcer|marketer|copywriter|writer|editor|journalist|translator|accountant|bookkeeper|auditor|controller|lawyer|attorney|paralegal|nurse|doctor|physician|pharmacist|therapist|teacher|tutor|professor|lecturer|trainer|coach|technician|mechanic|electrician|operator|driver|representative|agent|broker|buyer|planner|producer|photographer|illustrator|animator|artist|tester|qa|sre|devops|sysadmin|student|graduate|intern|apprentice|freelancer|contractor|executive|supervisor|partner|generalist|clerk|chef|pilot|scrum master|product owner|salesperson)\b/i;
  var LOOKING = /#?open\s?to\s?work|open to (?:new )?(?:opportunities|roles|offers|work)|(?:looking|seeking|searching) for (?:a |an |my )?(?:new |next )?(?:job|role|position|opportunit(?:y|ies)|challenges?)|actively (?:looking|seeking)|job ?seeker|unemployed|available (?:immediately|now)|between jobs/gi;
  var ASK = /\b(?:contact|reach|e-?mail|message|dm|get in touch|connect|write to|call me|let[’']s talk|book a|open to|looking for|hire me|available for)\b|[\w.+-]+@[\w-]+\.[\w.]+|https?:\/\/|www\./i;
  var DOES = /\bI(?:[’']m| am| help| build| design| lead| write| work| manage| run| create| develop| teach| sell| make| turn| speciali[sz]e| focus| support| analy[sz]e| plan| fix| grow| train| coach| recruit| hire| translate| edit| test| automate| ship| deliver| advise| care| treat)\b/i;
  var WHOM = /\b(?:help(?:s|ing)?|serv(?:e|es|ing)|clients?|customers?|users?|teams?|companies|businesses|startups?|founders?|patients?|students?|brands?|agencies|employers?|organi[sz]ations|nonprofits|readers|shoppers)\b/i;
  var EMOJI; try { EMOJI = new RegExp('\\p{Extended_Pictographic}', 'gu'); } catch (e) { EMOJI = /[☀-➿]|[\uD83C-\uD83E][\uDC00-\uDFFF]/g; }
  T.OPENING = 300;                                         // the part of the About text this page treats as visible before “see more”
  T.linkedinReview = function (f) {
    f = f || {};
    var head = clean(f.headline), about = String(f.about || '').replace(/\r/g, '').trim(), items = [];
    if (!head && !about) return { empty: true, items: [], fixes: 0, headline: 0, about: 0, opening: '' };
    var add = function (level, t, d, q) { items.push({ level: level, t: t, d: d, q: (q || []).filter(Boolean).map(function (x) { return cut(x, 160); }) }); };
    var sents = (about.match(/[^.!?\n]+[.!?]*/g) || []).map(clean).filter(Boolean), holding = function (rx) { return sents.filter(function (s) { return s.search(rx) >= 0; })[0] || ''; };
    var emoji = function (s) { return (s.match(EMOJI) || []).length; }, upper = function (s) { var l = s.replace(/[^A-Za-z]/g, ''); return l.length ? l.replace(/[^A-Z]/g, '').length / l.length : 0; };

    if (!head) add('fix', 'No headline', 'Paste the line that stands under your name on LinkedIn. It is the only text people see next to your name in search results and comments.');
    else {
      if (head.length > T.HEADLINE_MAX) add('fix', 'The headline is ' + head.length + ' characters: ' + (head.length - T.HEADLINE_MAX) + ' over the limit', 'LinkedIn cuts a headline at ' + T.HEADLINE_MAX + ' characters. Everything from this point is lost:', [head.slice(T.HEADLINE_MAX)]);
      else if (head.length < 30) add('info', 'The headline uses ' + head.length + ' of ' + T.HEADLINE_MAX + ' characters', 'There is room for your field, your main skills or the kind of customer you work for.', [head]);
      else add('ok', 'Headline length: ' + head.length + ' of ' + T.HEADLINE_MAX + ' characters', 'Inside the limit.');
      var looking = head.match(LOOKING), role = ROLE.test(head);
      var rest = head.replace(LOOKING, ' ').replace(new RegExp(ROLE.source, 'gi'), ' ').replace(/(?:\bat\b|@)\s+[A-Z][\w&.-]*(?:\s+[A-Z][\w&.-]*)*/g, ' ').toLowerCase().match(/[a-z][a-z+#.-]{2,}/g) || [];
      var field = rest.filter(function (w) { return !STOP[w] && !/^(?:senior|junior|principal|staff|chief|mid|level|experienced|new|next)$/.test(w); }).length > 0;
      if (looking && !role) add('fix', 'The headline only says you are looking', '“' + looking[0] + '” tells a recruiter you are available, not what you do. Lead with your job title and your field; LinkedIn has a separate “Open to work” setting for the rest.', [head]);
      else if (!role) add('warn', 'No job title found in the headline', 'We looked for a title such as engineer, designer, manager or nurse and found none. A slogan or a company name does not tell a searcher what you do. If your title is an unusual one, ignore this.', [head]);
      else if (!field) add('info', 'A job title, but no field or specialty', 'Add what kind of work it is or who it is for: the industry, your main tools, the type of customer.', [head]);
      else add('ok', 'The headline names a role and a field', 'A searcher can tell what you do from this line alone.');
      var hb = findPhrases(head, BUZZ);
      if (hb.length) add('warn', 'Buzzword' + (hb.length === 1 ? '' : 's') + ' in the headline: ' + hb.map(function (x) { return x.term; }).join(', '), 'These words fit any profile. Use the space for a skill, a field or a result.', [head]);
      if (head.replace(/[^A-Za-z]/g, '').length >= 12 && upper(head) > 0.6) add('warn', 'The headline is written in capital letters', 'Capitals read as shouting and are harder to scan. Keep them for abbreviations.', [head]);
      if (emoji(head) > 2) add('warn', emoji(head) + ' emoji in the headline', 'One or two as separators are fine; more push the words out of the visible part.', [head]);
    }

    var opening = about.length > T.OPENING ? about.slice(0, T.OPENING + 1).replace(/\s+\S*$/, '') : about;
    if (!about) add('fix', 'No About text', 'Paste your About section to have it checked. A profile without one leaves the reader with job titles only.');
    else {
      if (about.length > T.ABOUT_MAX) add('fix', 'The About text is ' + fmt(about.length) + ' characters: over the limit', 'LinkedIn accepts ' + fmt(T.ABOUT_MAX) + ' characters. This is where it would be cut:', [about.slice(T.ABOUT_MAX)]);
      else if (about.length < T.OPENING) add('warn', 'The About text is short: ' + about.length + ' characters', 'All of it fits in the opening lines. Add one result with a number and say what you want next.', [about]);
      else add('ok', 'About length: ' + fmt(about.length) + ' of ' + fmt(T.ABOUT_MAX) + ' characters', 'Inside the limit, and long enough to say something.');
      var does = ROLE.test(opening) || DOES.test(opening), whom = WHOM.test(opening);
      if (!does) add('warn', 'The opening does not say what you do', 'Only the first lines show before “see more”. Start with your role and the work you do; move the story of how you got there further down.', [opening]);
      else if (!whom) add('info', 'The opening does not say who you do it for', 'Name the kind of company, team or customer your work serves, in the first two sentences.', [opening]);
      else add('ok', 'The opening says what you do and for whom', 'The lines that show before “see more” carry the main point.');
      if (!/\b(?:i|my|me)\b(?!\.e)/i.test(about)) add('warn', 'Not written in the first person', 'It is your own profile: write “I” and “my”. A text about “he” or “she” reads like someone else’s press release.', [holding(/\b(?:he|she|his|her|is|has|was)\b/i) || sents[0]]);
      else add('ok', 'Written in the first person', 'The text speaks as “I”.');
      if (hasFigure(about)) add('ok', 'Has a number or a concrete result', 'For example: “' + cut(sents.filter(hasFigure)[0] || about, 110) + '”');
      else add('warn', 'No number and no concrete result', 'Add one thing you can count: years in the field, people served, money saved, the size of the team or the project.', []);
      if (ASK.test(about)) add('ok', 'Says how to reach you or what you want', 'Found: “' + cut(holding(ASK) || about, 110) + '”');
      else add('warn', 'No ask and no contact line', 'End with what you are open to and how to reach you: a message on LinkedIn, an email address.', [sents[sents.length - 1]]);
      var ab = findPhrases(about, BUZZ);
      if (ab.length) add(ab.length > 2 ? 'warn' : 'info', ab.length + ' buzzword' + (ab.length === 1 ? '' : 's') + ' in the About text: ' + ab.map(function (x) { return x.term; }).join(', '), 'Replace each with the fact behind it: what you did, for whom, with what result.',
        ab.slice(0, 2).map(function (x) { return holding(phraseRx(x.term)); }).filter(function (s, i, a) { return a.indexOf(s) === i; }));
      var shout = about.match(/\b[A-Z]{2,}(?:[ \t]+[A-Z]{2,}){2,}\b/);
      if (shout || (about.replace(/[^A-Za-z]/g, '').length >= 80 && upper(about) > 0.3)) add('warn', 'Capital letters in the About text', 'Whole phrases in capitals read as shouting. Keep capitals for names and abbreviations.', [shout ? shout[0] : sents[0]]);
      if (emoji(about) > 5) add('warn', emoji(about) + ' emoji in the About text', 'A few as bullet marks are fine. More than five compete with the words.', [sents.filter(function (s) { return emoji(s); })[0]]);
    }
    var rank = { fix: 0, warn: 1, info: 2, ok: 3 };
    items.sort(function (a, b) { return rank[a.level] - rank[b.level]; });
    return { items: items, fixes: items.filter(function (i) { return i.level === 'fix' || i.level === 'warn'; }).length, notes: items.filter(function (i) { return i.level === 'info'; }).length,
      headline: head.length, about: about.length, opening: opening, more: about.length > opening.length };
  };

  /* ---------- offer check: an offered salary against the advertised ranges ---------- */
  // Uses the same embedded aggregates as the salary checker. When the chosen category and level have too few postings, the next wider group is used:
  // every category at the same level (pay follows the level first), then the same category at any level, then everything.
  // `also` is the other of those two groups when it exists, so the page can show both yardsticks.
  T.offerCheck = function (data, pay, cat, lvl) {
    var x = num(pay); cat = cat || ''; lvl = lvl || '';
    if (!(x > 0)) return null;
    var tries = [[cat, lvl], ['', lvl], [cat, ''], ['', '']], g = null, used = null;
    for (var i = 0; i < tries.length && !g; i++) { g = T.salaryGroup(data, tries[i][0], tries[i][1], ''); used = tries[i]; }
    if (!g) return { pay: x, group: null };
    var wider = used[0] !== cat || used[1] !== lvl, other = wider && cat && lvl && used[1] === lvl ? T.salaryGroup(data, cat, '', '') : null, diff = (x - g.median) / g.median * 100, d = Math.round(Math.abs(diff)), zone = x < g.p25 ? 'low' : x > g.p75 ? 'high' : 'mid';
    var med = wider ? 'the median of the wider group' : 'the median';          // advice is given only for the group that was asked for
    var verdict = zone === 'low' ? d + '% below ' + med + ': ' + (wider ? 'low for that group, which is only a rough guide' : 'worth asking for more')
      : zone === 'high' ? d + '% above ' + med + ': higher than three quarters of ' + (wider ? 'its' : 'the') + ' advertised ranges'
      : d <= 5 ? 'Close to ' + med + (wider ? '' : ': in line with what postings advertise')
      : diff < 0 ? d + '% below ' + med + ', inside the middle half' + (wider ? '' : ': there is room to ask') : d + '% above ' + med + ', inside the middle half';
    return { pay: x, group: g, cat: used[0], lvl: used[1], wider: wider, mixesLevels: wider && used[1] !== lvl, mixesCategories: wider && used[0] !== cat, also: other ? { cat: cat, lvl: '', group: other } : null, diff: diff, zone: zone, pct: T.percentile(data.q, g.vals, x), verdict: verdict };
  };

  if (typeof module !== 'undefined' && module.exports) module.exports = T;
  if (typeof document === 'undefined') return;

  /* ================================================================ part 2: pages ================================================================ */
  var root = document.querySelector('.tl[data-tool]'); if (!root) return;
  var H = window.HRN || {
    get: function (k, d) { try { var v = JSON.parse(localStorage.getItem(k)); return v == null ? d : v; } catch (e) { return d; } },
    set: function (k, v) { try { localStorage.setItem(k, JSON.stringify(v)); } catch (e) {} },
    esc: function (s) { return String(s == null ? '' : s).replace(/[&<>"]/g, function (c) { return { '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;' }[c]; }); },
    base: document.documentElement.getAttribute('data-base') || ''
  };
  var esc = H.esc, $ = function (id) { return document.getElementById(id); };
  var KEY = 'hrn_tool_' + root.getAttribute('data-tool').replace(/-/g, '_');
  var each = function (sel, fn) { Array.prototype.forEach.call(root.querySelectorAll(sel), fn); };

  /* Form state: every field with data-k is restored from localStorage, saved on each change, and reset by the [data-clear] button.
     Defaults are whatever the page's HTML says, so the markup stays the single source of truth. */
  function form(render) {
    var els = Array.prototype.slice.call(root.querySelectorAll('[data-k]')), def = {};
    var box = function (el) { return el.type === 'checkbox'; };
    els.forEach(function (el) {
      var k = el.getAttribute('data-k');
      if (box(el)) def[k] = el.defaultChecked;
      else if (el.tagName === 'SELECT') { var o = el.querySelector('option[selected]') || el.options[0]; def[k] = o ? o.value : ''; }
      else def[k] = el.defaultValue || '';
    });
    var put = function (v) {
      els.forEach(function (el) {
        var k = el.getAttribute('data-k'), x = v[k] === undefined ? def[k] : v[k];
        if (box(el)) el.checked = !!x;
        else { el.value = x; if (el.tagName === 'SELECT' && el.selectedIndex < 0) el.value = def[k]; }
      });
    };
    var read = function () { var v = {}; els.forEach(function (el) { v[el.getAttribute('data-k')] = box(el) ? el.checked : el.value; }); return v; };
    var api = {
      read: read,
      save: function () { H.set(KEY, read()); },
      set: function (k, val) { els.forEach(function (el) { if (el.getAttribute('data-k') === k) { if (box(el)) el.checked = !!val; else el.value = val; } }); },
      draw: function () { render(read(), '', api); }
    };
    var saved = H.get(KEY, null);
    put(saved && typeof saved === 'object' ? saved : {});
    var on = function (ev) {
      var k = ev.target && ev.target.getAttribute ? ev.target.getAttribute('data-k') : null;
      if (k == null) return;
      render(read(), k, api); api.save();
    };
    root.addEventListener('input', on);
    root.addEventListener('change', on);
    root.addEventListener('click', function (ev) {
      var x = ev.target.closest ? ev.target.closest('[data-example]') : null;
      if (x) {                                            // fill every empty field with its example so the result shows at once
        var v = read(), any = false;
        els.forEach(function (el) {
          if (box(el) || el.tagName === 'SELECT' || el.value) return;
          var ex = el.getAttribute('data-ex');
          if (ex == null) { var ph = el.getAttribute('placeholder') || ''; ex = /^(paste|type|e\.g)\b/i.test(ph) ? '' : ph.split(' or ')[0]; }
          if (ex) { v[el.getAttribute('data-k')] = ex; any = true; }
        });
        if (any) { put(v); render(read(), '', api); api.save(); }
        var go = root.querySelector('#tl-run'); if (go) go.click();
        return;
      }
      var b = ev.target.closest ? ev.target.closest('[data-clear]') : null;
      if (!b) return;
      if (b.getAttribute('data-clear') === 'ask' && !window.confirm('Erase everything you typed here from this browser?')) return;
      try { localStorage.removeItem(KEY); } catch (e) {}
      put({}); render(read(), '', api);
    });
    render(read(), '', api);
    return api;
  }

  /* copy / download / print buttons */
  function copy(btn, text, src) {
    var label = btn.getAttribute('data-label') || btn.textContent;
    btn.setAttribute('data-label', label);
    var say = function (msg, ms) { btn.textContent = msg; setTimeout(function () { btn.textContent = label; }, ms); };
    var done = function () { say('Copied ✓', 1500); };
    var pick = function () {                      // copying was refused: select the text so it can be copied by hand
      try {
        if (src && src.select) src.select();
        else if (src) { var r = document.createRange(); r.selectNodeContents(src); var sel = window.getSelection(); sel.removeAllRanges(); sel.addRange(r); }
      } catch (e) {}
      say('Selected: copy with Ctrl/⌘+C', 3000);
    };
    var old = function () {
      var ta = document.createElement('textarea'), ok = false; ta.value = text; ta.setAttribute('readonly', ''); ta.style.position = 'fixed'; ta.style.opacity = '0';
      document.body.appendChild(ta); ta.select();
      try { ok = document.execCommand('copy'); } catch (e) {}
      document.body.removeChild(ta);
      if (ok) done(); else pick();
    };
    if (navigator.clipboard && navigator.clipboard.writeText) navigator.clipboard.writeText(text).then(done, old); else old();
  }
  function download(name, text) {
    var a = document.createElement('a'), url = URL.createObjectURL(new Blob([text], { type: 'text/plain;charset=utf-8' }));
    a.href = url; a.download = name; document.body.appendChild(a); a.click(); document.body.removeChild(a);
    setTimeout(function () { URL.revokeObjectURL(url); }, 2000);
  }
  root.addEventListener('click', function (ev) {
    var t = ev.target.closest ? ev.target.closest('[data-copy],[data-dl],[data-print]') : null;
    if (!t) return;
    if (t.hasAttribute('data-print')) { window.print(); return; }
    var src = $(t.getAttribute('data-copy') || t.getAttribute('data-dl')), text = src ? ('value' in src ? src.value : src.textContent) : '';
    if (!text || (src && src.getAttribute('data-empty') === '1')) return;
    if (t.hasAttribute('data-copy')) copy(t, text, src); else download(t.getAttribute('data-name') || 'text.txt', text);
  });

  /* result board pieces */
  function board(el, left, right, inner) { el.innerHTML = '<div class="tl-board-h"><span>' + esc(left) + '</span><b>' + esc(right || '') + '</b></div>' + inner; }
  function big(text, small) { return '<p class="tl-big">' + esc(text) + (small ? ' <small>' + esc(small) + '</small>' : '') + '</p>'; }
  function sub(html) { return '<p class="tl-sub">' + html + '</p>'; }
  function kv(rows) { return '<dl class="tl-kv">' + rows.filter(Boolean).map(function (r) { return '<div><dt>' + esc(r[0]) + '</dt><dd>' + esc(r[1]) + '</dd></div>'; }).join('') + '</dl>'; }
  function idle(el, left, msg) { board(el, left, '', '<p class="tl-big tl-dim">—</p>' + sub(esc(msg))); }
  function meter(pct) { return '<div class="tl-meter" aria-hidden="true"><i style="width:' + Math.max(0, Math.min(100, pct)) + '%"></i></div>'; }
  function cash(x, s) { return money(x, s, Math.abs(x) < 100 || Math.abs(x) < 1000 && Math.round(x * 100) % 100 ? 2 : 0); }   // cents only where they say something: $440, not $440.00
  function tags(level) { return { fix: ['fix', 'Fix'], warn: ['warn', 'Check'], info: ['info', 'Note'], ok: ['ok', 'OK'] }[level]; }
  function list(items) {
    return '<ul class="tl-list">' + items.map(function (i) { var t = tags(i.level); return '<li><span class="tl-tag ' + t[0] + '">' + t[1] + '</span><div><b>' + esc(i.t) + '</b>' + (i.d ? '<p>' + esc(i.d) + '</p>' : '') +
      (i.q || []).map(function (q) { return '<blockquote class="tl-quote">' + esc(q) + '</blockquote>'; }).join('') + '</div></li>'; }).join('') + '</ul>';
  }
  var tools = {};

  /* ---------- pay converter ---------- */
  tools['salary-converter'] = function () {
    var out = $('tl-out'), title = 'Your pay in every unit';
    form(function (v) {
      if (!clean(v.amount)) return idle(out, title, 'Enter an amount to see it per hour, day, week, month and year.');
      var r = T.convertPay(v.amount, v.period, v.hours, v.weeks, v.days), s = v.cur;
      if (!r) return idle(out, title, 'Check the figures: the amount must be a number, hours per week between 1 and 168, days per week between 1 and 7, paid weeks per year between 1 and 52.');
      var toYear = v.period !== 'year';
      board(out, title, fmt(r.hoursYear, 1) + ' paid hours a year',
        big(toYear ? money(r.year, s, 0) : money(r.hour, s, 2), toYear ? 'per year' : 'per hour') +
        sub('Before tax, for ' + esc(fmt(num(v.hours), 2)) + ' hours a week over ' + esc(fmt(num(v.days), 1)) + ' days, ' + esc(fmt(num(v.weeks), 1)) + ' paid weeks a year.') +
        kv([['Per hour', money(r.hour, s, 2)], ['Per day', cash(r.day, s)], ['Per week', cash(r.week, s)], ['Per month', cash(r.month, s)], ['Per year', money(r.year, s, 0)]]));
    });
  };

  /* ---------- pay raise ---------- */
  tools['raise-calculator'] = function () {
    var out = $('tl-out'), FREQ = { '52': 'weekly paychecks', '26': 'a paycheck every two weeks', '24': 'two paychecks a month', '12': 'monthly paychecks' };
    form(function (v, k, F) {
      if (k === 'pct' || k === 'amount' || k === 'next') { v.by = k; F.set('by', k); }
      var by = v.by || 'pct', s = v.cur;
      var r = T.raise({ current: v.current, pct: v.pct, amount: v.amount, next: v.next, by: by, periods: v.freq, inflation: v.infl });
      ['pct', 'amount', 'next'].forEach(function (f) { if (f !== by) F.set(f, r ? plain(r[f], 2) : ''); });       // the two figures the visitor did not type follow from the one they did
      if (!r) return idle(out, 'Your raise', num(v.current) > 0 ? 'Now enter the raise as a percent, as an amount or as the new salary. The other two are filled in for you.' : 'Enter your current yearly salary, then the raise as a percent, an amount or the new salary.');
      var up = r.amount >= 0, word = up ? 'more' : 'less', real = '';
      if (r.realPct !== undefined) {
        real = ' With prices ' + (r.inflation >= 0 ? 'up ' : 'down ') + esc(plain(Math.abs(r.inflation), 2)) + '%, that is ' + (r.realPct >= 0 ? 'a real raise of ' : 'a real pay cut of ') + esc(plain(Math.abs(r.realPct), 2)) + '%: the new salary buys what ' +
          esc(money(r.next / (1 + r.inflation / 100), s, 0)) + ' bought before.';
      }
      board(out, up ? 'Your raise' : 'Your pay cut', (up ? '+' : '−') + plain(Math.abs(r.pct), 2) + '%',
        big(money(r.next, s, 0), 'new yearly salary') +
        sub(esc(money(Math.abs(r.amount), s, 0)) + ' ' + word + ' a year, or ' + esc(money(Math.abs(r.payDiff), s, 2)) + ' ' + word + ' per paycheck before tax (' + esc(FREQ[v.freq] || 'monthly paychecks') + ').' + real) +
        kv([['Paycheck now', money(r.payBefore, s, 2)], ['Paycheck after', money(r.payAfter, s, 2)], ['Change per paycheck', (up ? '+' : '') + money(r.payDiff, s, 2)], ['Change per month', (up ? '+' : '') + money(r.monthDiff, s, 2)],
          r.realPct !== undefined ? ['After inflation', (r.realPct >= 0 ? '+' : '−') + plain(Math.abs(r.realPct), 2) + '%'] : null]));
    });
  };

  /* ---------- offer comparison ---------- */
  tools['compare-offers'] = function () {
    var out = $('tl-out'), table = $('tl-table'), colC = $('tl-col-c'), addBtn = $('tl-add'), FIELDS = ['name', 'base', 'bonus', 'equity', 'signon', 'match', 'other', 'pto', 'cdays', 'ccost'];
    var F = form(function (v) {
      var three = v.n === '3', ids = three ? ['a', 'b', 'c'] : ['a', 'b'], s = v.cur;
      colC.hidden = !three; addBtn.textContent = three ? 'Remove the third offer' : '+ Add a third offer';
      var res = T.compareOffers(ids.map(function (p, i) {
        var o = {}; FIELDS.forEach(function (f) { o[f] = v[p + '_' + f]; });
        o.name = clean(o.name) || 'Offer ' + 'ABC'.charAt(i);
        return o;
      }));
      if (!res.count) { table.innerHTML = ''; return idle(out, 'Yearly value', 'Enter the base salary of each offer. Add bonus, equity and benefits where you know them; leave the rest empty.'); }
      var best = res.offers[res.best], notes = [];
      if (res.count < 2) notes.push('Fill in a second offer to see the difference.');
      else if (res.lead === 0) notes.push('The best two offers are worth the same per year.');
      else notes.push('<b>' + esc(best.name) + '</b> is worth ' + esc(money(res.lead, s, 0)) + ' more a year than ' + esc(res.second.name) + (res.leadPct != null ? ' (+' + esc(plain(res.leadPct, 1)) + '%)' : '') + '.');
      if (res.count > 1 && res.bestFirst !== res.best) notes.push('Counting the sign-on bonus, ' + esc(res.offers[res.bestFirst].name) + ' pays more in the first year.');
      if (res.count > 1 && res.bestDay !== res.best) notes.push(esc(res.offers[res.bestDay].name) + ' pays more per day you actually work.');
      if (res.count > 1 && best.equity > 0 && best.equity >= res.lead) notes.push('The lead depends on equity (' + esc(money(best.equity, s, 0)) + ' a year), which is not cash until the shares can be sold.');
      board(out, 'Highest yearly value', best.name, big(money(best.yearly, s, 0), 'per year') + sub(notes.join(' ')));
      var row = function (label, f, bestIdx, cls) {
        return '<tr' + (cls ? ' class="' + cls + '"' : '') + '><td>' + label + '</td>' + res.offers.map(function (o, i) {
          return '<td class="num' + (bestIdx === i && res.count > 1 ? ' tl-best' : '') + '">' + (o.filled ? esc(f(o)) : '—') + '</td>';
        }).join('') + '</tr>';
      };
      var m = function (k) { return function (o) { return money(o[k], s, 0); }; };
      table.innerHTML = '<div class="tablewrap"><table><tr><th>Per year</th>' + res.offers.map(function (o) { return '<th>' + esc(o.name) + '</th>'; }).join('') + '</tr>' +
        row('Base salary', m('base')) + row('Bonus', m('bonus')) + row('Equity', m('equity')) + row('Retirement match', m('match')) + row('Other benefits', m('other')) +
        row('Commute cost', function (o) { return o.commute ? '−' + money(o.commute, s, 0) : money(0, s, 0); }) +
        row('Yearly value', m('yearly'), res.best, 'tl-total') +
        row('Sign-on bonus (once)', m('signon')) + row('First-year value', m('first'), res.bestFirst, 'tl-total') +
        row('Paid days off', function (o) { return fmt(o.pto, 1); }) + row('Days worked a year', function (o) { return fmt(o.workDays, 1); }) +
        row('Value per day worked', function (o) { return money(o.perDay, s, 0); }, res.bestDay, 'tl-total') + '</table></div>';
    });
    addBtn.addEventListener('click', function () { F.set('n', F.read().n === '3' ? '2' : '3'); F.save(); F.draw(); });
  };

  /* ---------- stock options ---------- */
  tools['equity-calculator'] = function () {
    var out = $('tl-out'), table = $('tl-table');
    var px = function (x, s) { return money(x, s, x < 1 ? 4 : 2); }, share = function (x) { return plain(x * 100, x < 0.001 ? 5 : 3) + '%'; };
    form(function (v) {
      each('[data-show]', function (el) { el.hidden = el.getAttribute('data-show') !== v.mode; });
      var s = v.cur, r = T.equity({ mode: v.mode, options: v.options, strike: v.strike, price: v.price, valuation: v.valuation, fdShares: v.fd, rounds: v.rounds, dilution: v.dilution,
        multiples: [v.m1, v.m2, v.m3], vestYears: v.vestYears, cliffMonths: v.cliff, monthsIn: v.monthsIn });
      if (!r) {
        table.innerHTML = '';
        return idle(out, 'Paper value today', v.mode === 'valuation' ? 'Enter the number of options, the strike price, the company valuation and the fully diluted share count.' : 'Enter the number of options, the strike price and the latest price per share.');
      }
      board(out, 'Paper value today', r.ownership != null ? share(r.ownership) + ' of the company' : 'before tax',
        big(money(r.paper, s, 0), 'before tax') +
        sub(esc(fmt(r.options)) + ' options × (' + esc(px(r.price, s)) + ' a share − ' + esc(px(r.strike, s)) + ' strike). ' +
          (r.paper > 0 ? 'Buying all of them would cost you ' + esc(money(r.cost, s, 0)) + '.' : 'The strike is at or above today’s share price, so on paper the options are worth nothing yet.') +
          ' An estimate, not a promise: private shares cannot be sold freely.') +
        kv([['Price per share', px(r.price, s)], ['Cost to exercise all', money(r.cost, s, 0)], r.valuation ? ['Company value', money(r.valuation, s, 0)] : null,
          r.vest ? ['Vested so far', fmt(r.vest.options) + ' (' + plain(r.vest.pct, 1) + '%)'] : null, r.vest ? ['Vested, paper value', money(r.vest.value, s, 0)] : null,
          r.perYear != null ? ['Per year of vesting', money(r.perYear, s, 0)] : null,
          r.strike > 0 && r.breakEven != null ? ['Worth something above', plain(r.breakEven, 2) + '× today’s value'] : null]));
      if (!r.scenarios.length) { table.innerHTML = ''; return; }
      table.innerHTML = '<div class="tablewrap"><table><tr><th>Exit at</th>' + (r.valuation ? '<th>Company sells for</th>' : '') + '<th>Price per share</th>' + (r.ownership != null ? '<th>Your stake</th>' : '') + '<th>Your options, after the strike</th></tr>' +
        r.scenarios.map(function (x) {
          return '<tr><td class="num">' + esc(plain(x.multiple, 2)) + '× today</td>' + (r.valuation ? '<td class="num">' + esc(money(x.exitValuation, s, 0)) + '</td>' : '') + '<td class="num">' + esc(px(x.price, s)) + '</td>' +
            (r.ownership != null ? '<td class="num">' + esc(share(x.ownership)) + '</td>' : '') + '<td class="num"><strong>' + esc(money(x.net, s, 0)) + '</strong></td></tr>';
        }).join('') + '</table></div><p class="note">' + (r.rounds && r.retained < 1 ? 'After ' + r.rounds + ' more funding round' + (r.rounds === 1 ? '' : 's') + ' at ' + esc(plain((1 - Math.pow(r.retained, 1 / r.rounds)) * 100, 2)) +
          '% dilution each you keep ' + esc(plain(r.retained * 100, 1)) + '% of your stake, so each share is worth less than the headline price suggests. ' : 'No future dilution is assumed. Add expected funding rounds to see their effect. ') +
        'Before tax. Liquidation preferences, which pay investors first, are not modelled and can reduce these figures, most of all in a low exit.</p>';
    });
  };

  /* ---------- time zone overlap ---------- */
  var ZONES = ['Pacific/Honolulu', 'America/Anchorage', 'America/Los_Angeles', 'America/Vancouver', 'America/Denver', 'America/Phoenix', 'America/Chicago', 'America/Mexico_City', 'America/New_York', 'America/Toronto',
    'America/Bogota', 'America/Lima', 'America/Halifax', 'America/St_Johns', 'America/Sao_Paulo', 'America/Argentina/Buenos_Aires', 'America/Santiago', 'Atlantic/Reykjavik', 'Europe/London', 'Europe/Dublin',
    'Europe/Lisbon', 'Europe/Madrid', 'Europe/Paris', 'Europe/Amsterdam', 'Europe/Brussels', 'Europe/Berlin', 'Europe/Zurich', 'Europe/Rome', 'Europe/Vienna', 'Europe/Prague', 'Europe/Warsaw', 'Europe/Stockholm',
    'Europe/Helsinki', 'Europe/Athens', 'Europe/Bucharest', 'Europe/Kiev', 'Europe/Istanbul', 'Europe/Moscow', 'Africa/Lagos', 'Africa/Cairo', 'Africa/Johannesburg', 'Africa/Nairobi', 'Asia/Dubai', 'Asia/Tehran',
    'Asia/Karachi', 'Asia/Kolkata', 'Asia/Kathmandu', 'Asia/Dhaka', 'Asia/Bangkok', 'Asia/Jakarta', 'Asia/Ho_Chi_Minh', 'Asia/Singapore', 'Asia/Kuala_Lumpur', 'Asia/Manila', 'Asia/Hong_Kong', 'Asia/Shanghai',
    'Asia/Taipei', 'Asia/Seoul', 'Asia/Tokyo', 'Australia/Perth', 'Australia/Adelaide', 'Australia/Brisbane', 'Australia/Sydney', 'Australia/Melbourne', 'Pacific/Auckland'];
  tools['time-zone-overlap'] = function () {
    var out = $('tl-out'), dayEl = $('tl-day'), table = $('tl-table'), addBtn = $('tl-add'), rows = Array.prototype.slice.call(root.querySelectorAll('[data-row]'));
    var mine = 'UTC', zones = ZONES, now = new Date();
    try { mine = Intl.DateTimeFormat().resolvedOptions().timeZone || 'UTC'; } catch (e) {}
    try { if (Intl.supportedValuesOf) zones = Intl.supportedValuesOf('timeZone'); } catch (e) {}
    zones = zones.filter(function (z) { try { T.tzOffset(z, now); return true; } catch (e) { return false; } });
    if (zones.indexOf(mine) < 0 && mine !== 'UTC') { try { T.tzOffset(mine, now); zones.push(mine); zones.sort(); } catch (e) { mine = 'UTC'; } }
    // some browsers list zones under older names (Asia/Calcutta, Europe/Kiev); show today's city names, keep the browser's own id as the value
    var MODERN = { 'Asia/Calcutta': 'Asia/Kolkata', 'Asia/Saigon': 'Asia/Ho_Chi_Minh', 'Asia/Katmandu': 'Asia/Kathmandu', 'Asia/Rangoon': 'Asia/Yangon', 'Europe/Kiev': 'Europe/Kyiv', 'Atlantic/Faeroe': 'Atlantic/Faroe',
      'America/Godthab': 'America/Nuuk', 'America/Buenos_Aires': 'America/Argentina/Buenos_Aires', 'America/Indianapolis': 'America/Indiana/Indianapolis', 'America/Louisville': 'America/Kentucky/Louisville',
      'Africa/Asmera': 'Africa/Asmara', 'Pacific/Truk': 'Pacific/Chuuk', 'Pacific/Ponape': 'Pacific/Pohnpei', 'Pacific/Enderbury': 'Pacific/Kanton' };
    var zoneName = function (z) { return (MODERN[z] || z).replace(/_/g, ' '); };
    var place = function (z) { z = MODERN[z] || z; return z.split('/').slice(1).join(' / ').replace(/_/g, ' ') || z; }, groups = {}, order = [];
    var known = function (id) { if (zones.indexOf(id) >= 0) return id; for (var k in MODERN) if (MODERN[k] === id && zones.indexOf(k) >= 0) return k; return 'UTC'; };
    zones.forEach(function (z) { var g = z.indexOf('/') > 0 ? z.split('/')[0] : 'Other'; if (!groups[g]) { groups[g] = []; order.push(g); } groups[g].push(z); });
    order.forEach(function (g) { groups[g].sort(function (a, b) { return place(a) < place(b) ? -1 : place(a) > place(b) ? 1 : 0; }); });
    var isMine = function (id) { return known(id) === mine; };
    var defaults = [mine, isMine('America/New_York') ? 'Europe/London' : 'America/New_York', isMine('Asia/Kolkata') ? 'Europe/Berlin' : 'Asia/Kolkata', isMine('Asia/Singapore') ? 'Australia/Sydney' : 'Asia/Singapore'];
    var poss = function (p) { return p.name.toLowerCase() === 'you' ? 'your' : p.name + '’s'; };
    each('select[data-tz]', function (sel, i) {
      var want = known(defaults[i]);
      sel.innerHTML = '<option value="UTC"' + (want === 'UTC' ? ' selected' : '') + '>UTC</option>' + order.map(function (g) {
        return '<optgroup label="' + esc(g) + '">' + groups[g].map(function (z) { return '<option value="' + esc(z) + '"' + (z === want ? ' selected' : '') + '>' + esc(place(z)) + '</option>'; }).join('') + '</optgroup>';
      }).join('');
    });
    var clock = root.querySelector('[data-k="clock"]'), h12 = false;
    try { h12 = !!new Intl.DateTimeFormat(undefined, { hour: 'numeric' }).resolvedOptions().hour12; } catch (e) {}
    if (clock && h12) Array.prototype.forEach.call(clock.options, function (o) { if (o.value === '12') o.setAttribute('selected', ''); else o.removeAttribute('selected'); });
    var lastClock = '';
    var F = form(function (v) {
      var n = Math.max(2, Math.min(rows.length, +v.n || 2)), am = v.clock === '12';
      rows.forEach(function (el, i) { el.hidden = i >= n; });
      addBtn.hidden = n >= rows.length;
      if (v.clock !== lastClock) { lastClock = v.clock; each('select[data-time] option', function (o) { o.textContent = T.hm(+o.value, am); }); }
      var picked = /^\d{4}-\d{2}-\d{2}$/.test(v.date) && !isNaN(new Date(v.date + 'T12:00:00Z').getTime()), date = picked ? new Date(v.date + 'T12:00:00Z') : new Date();
      var people = [], bad = '';
      for (var i = 1; i <= n; i++) {
        var p = { name: clean(v['z' + i + '_name']) || (i === 1 ? 'You' : 'Person ' + i), tz: v['z' + i + '_tz'], start: +v['z' + i + '_start'], end: +v['z' + i + '_end'] };
        try { p.off = T.tzOffset(p.tz, date); } catch (e) { p.off = NaN; }
        if (isNaN(p.off)) bad = 'This browser does not know the time zone “' + zoneName(p.tz || '?') + '”. Pick another one nearby.';
        else if (p.start === p.end) bad = p.name + ': the working day starts and ends at the same time. Change one of the two.';
        people.push(p);
      }
      if (bad) { dayEl.innerHTML = table.innerHTML = ''; return idle(out, 'Shared working time', bad); }
      var ov = T.overlap(people), me = people[0];
      var span = function (startLocal, len) { var a = mod(startLocal, 1440); return T.hm(a, am) + '–' + T.hm(a + len, am) + (a + len > 1440 ? ' next day' : ''); };
      var shared = function (p) { return ov.blocks.map(function (b) { return span(b.start + p.off, b.len); }).join(' and '); };
      var when = date.toLocaleDateString('en-GB', picked ? { day: 'numeric', month: 'short', year: 'numeric', timeZone: 'UTC' } : { day: 'numeric', month: 'short', year: 'numeric' });
      board(out, 'Shared working time', 'Offsets on ' + when,
        big(ov.minutes ? T.dur(ov.minutes) : 'No overlap', ov.minutes ? 'a day' : '') +
        sub(ov.minutes ? people.map(function (p) { return '<b>' + esc(p.name) + '</b> ' + esc(shared(p)); }).join(' · ')
          : 'No hour of the day falls inside everyone’s working day. In ' + esc(poss(me)) + ' local time the others work: ' +
            people.slice(1).map(function (p) { return '<b>' + esc(p.name) + '</b> ' + esc(span(p.start - p.off + me.off, mod(p.end - p.start, 1440))); }).join(' · ') + '. Move a start or an end to find a slot.'));
      // the 24-hour bar, drawn in the first person's local time
      var seg = function (ints, cls) { return ints.map(function (x) { return '<i class="tl-seg ' + cls + '" style="left:' + plain(x[0] / 14.4, 3) + '%;width:' + plain((x[1] - x[0]) / 14.4, 3) + '%"></i>'; }).join(''); };
      dayEl.innerHTML = '<p class="tl-t">24 hours in ' + esc(poss(me)) + ' local time (' + esc(place(me.tz)) + ')</p><div class="tl-day">' +
        people.map(function (p, i) {
          var local = T.shift(T.dayIntervals(p.start, p.end, p.off), me.off);
          return '<div class="tl-day-row"><span class="tl-day-n">' + esc(p.name) + '</span><div class="tl-track" role="img" aria-label="' + esc(p.name + ': working day ' + span(p.start - p.off + me.off, mod(p.end - p.start, 1440)) + ' in ' + poss(me) + ' local time') + '">' + seg(local, i ? 'b' : 'a') + '</div></div>';
        }).join('') +
        '<div class="tl-day-row"><span class="tl-day-n">Overlap</span><div class="tl-track" role="img" aria-label="' + esc(ov.minutes ? 'Shared time ' + shared(me) : 'No shared time') + '">' + seg(T.shift(ov.utc, me.off), 'ov') + '</div></div>' +
        '<div class="tl-day-row" aria-hidden="true"><span></span><div class="tl-axis"><span>' + (am ? ['12am', '6am', '12pm', '6pm', '12am'] : ['00', '06', '12', '18', '24']).join('</span><span>') + '</span></div></div></div>';
      table.innerHTML = '<div class="tablewrap"><table><tr><th>Who</th><th>Time zone</th><th>Offset</th><th>Working day</th><th>Shared time, local</th></tr>' + people.map(function (p) {
        return '<tr><td><strong>' + esc(p.name) + '</strong></td><td>' + esc(zoneName(p.tz)) + '</td><td class="num">' + esc(T.utcLabel(p.off)) + '</td><td class="num">' + esc(span(p.start, mod(p.end - p.start, 1440))) + '</td><td class="num">' + (ov.minutes ? esc(shared(p)) : '—') + '</td></tr>';
      }).join('') + '</table></div>';
    });
    root.addEventListener('click', function (ev) {
      var t = ev.target.closest ? ev.target.closest('#tl-add,[data-rm]') : null; if (!t) return;
      var v = F.read(), n = Math.max(2, Math.min(rows.length, +v.n || 2));
      if (t.id === 'tl-add') n = Math.min(rows.length, n + 1);
      else {                                   // remove a row: shift the rows below it up
        for (var i = +t.getAttribute('data-rm'); i < n; i++) ['name', 'tz', 'start', 'end'].forEach(function (f) { F.set('z' + i + '_' + f, v['z' + (i + 1) + '_' + f]); });
        n = Math.max(2, n - 1);
      }
      F.set('n', String(n)); F.save(); F.draw();
    });
  };

  /* ---------- resume vs job description ---------- */
  tools['resume-match'] = function () {
    var out = $('tl-out'), detail = $('tl-detail'), imp = $('tl-import'), pats = null, offline = false;
    var F = form(function (v) {
      if (pats === null) { detail.innerHTML = ''; return idle(out, 'Match score', 'Loading the skills list…'); }
      var r = T.matchResume(v.resume, v.jd, pats, v.title);
      if (r.error) {
        detail.innerHTML = '';
        return idle(out, 'Match score', !clean(v.resume) && !clean(v.jd) ? 'Paste your resume and the job description to see how well they match.' : r.error === 'resume' ? 'Paste the full text of your resume (at least 30 words).' :
          r.error === 'jd' ? 'Now paste the job description (at least 30 words).' : 'The posting has too little text to compare. Paste the whole description.');
      }
      board(out, 'Match score', r.label, big(String(r.score), '/ 100') + meter(r.score) +
        sub((r.jdSkills ? esc(r.matched.length + ' of ' + r.jdSkills) + ' skills and ' : 'The posting names no skills from our list, so the score rests on its repeated terms: ') + esc(r.termsFound + ' of ' + r.terms.length) +
          ' repeated terms from the posting appear in your resume.' + (offline ? ' The skills list could not be loaded, so only repeated terms were compared.' : '') + ' A keyword overlap, not a forecast of your chances.'));
      var pill = function (text, okay) { return '<span class="pill ' + (okay ? 'ok' : 'tl-miss') + '">' + (okay ? '✓ ' : '') + esc(text) + '</span>'; };
      detail.innerHTML =
        (r.jdSkills ? '<div class="card"><p class="tl-t">Skills the posting asks for</p><div class="tl-pills">' + r.matched.map(function (s) { return pill(s, true); }).join('') + r.missing.map(function (s) { return pill(s, false); }).join('') +
          '</div><p class="note">' + (r.missing.length ? 'Dashed = named in the posting, not found in your resume.' : 'Every skill the posting names is in your resume.') + '</p></div>' : '') +
        (r.terms.length ? '<div class="card"><p class="tl-t">Other terms the posting repeats</p><div class="tl-pills">' + r.terms.map(function (t) { return pill(t.term + ' ×' + t.n, t.found); }).join('') +
          '</div><p class="note">×2 means the posting uses the term twice. Words that every posting uses (“team”, “experience”) are left out.</p></div>' : '') +
        '<p class="tl-t">What to fix</p>' + list(r.fixes.map(function (f) { return { level: f.ok ? 'ok' : 'fix', t: f.t, d: f.d }; }));
    });
    fetch(H.base + '/data/skills.json').then(function (res) { if (!res.ok) throw new Error('skills'); return res.json(); })
      .then(function (data) { pats = T.compilePats(data); F.draw(); })
      .catch(function () { pats = []; offline = true; F.draw(); });
    var cv = H.get('hrn_resume', null);
    if (imp && cv && (cv.summary || cv.skills || (cv.exp || []).some(function (x) { return x.role || x.text; }))) {
      imp.hidden = false;
      imp.addEventListener('click', function () {
        var text = [cv.title, cv.summary].concat((cv.exp || []).map(function (x) { return [x.role, x.org, x.dates].filter(Boolean).join(', ') + '\n' + (x.text || ''); }),
          (cv.edu || []).map(function (x) { return [x.what, x.org, x.dates].filter(Boolean).join(', '); }), [cv.skills ? 'Skills: ' + cv.skills : '']).filter(Boolean).join('\n\n');
        F.set('resume', text); F.save(); F.draw();
      });
    }
    var go = $('tl-run');
    if (go) go.addEventListener('click', function () { F.draw(); if (out.scrollIntoView) out.scrollIntoView({ behavior: 'smooth', block: 'start' }); });
    // ?job=<slug>: a job page sent the visitor here; its posting is read from this site's own page and put into the form
    var slug = (location.search.match(/[?&]job=([a-z0-9-]{3,160})/) || [])[1];
    if (slug && window.fetch && window.DOMParser) {
      fetch(H.base + '/job/' + slug + '/').then(function (r) { return r.ok ? r.text() : ''; }).then(function (page) {
        if (!page) return;
        var doc = new DOMParser().parseFromString(page, 'text/html'), d = doc.querySelector('.prose.desc') || doc.querySelector('.prose');
        if (!d) return;
        var blocks = [].map.call(d.querySelectorAll('h2,h3,h4,p,li'), function (x) { return x.textContent.trim(); }).filter(Boolean);
        var title = ((doc.querySelector('h1') || {}).textContent || '').trim(), apply = doc.getElementById('apply');
        F.set('jd', blocks.length ? blocks.join('\n') : d.textContent.trim());
        if (title) F.set('title', title);
        F.save(); F.draw();
        var note = document.createElement('p');
        note.className = 'note tl-loaded';
        note.innerHTML = 'The posting <b>' + esc(title) + '</b> is filled in from its page on this site.' +
          (d.classList.contains('desc') ? '' : ' Only its opening lines are here: for a full check, paste the whole description' + (apply ? ' from <a href="' + esc(apply.getAttribute('href')) + '" target="_blank" rel="nofollow noopener">the employer’s page</a>' : '') + '.') +
          (imp && !imp.hidden ? ' Now press “Use my resume from the builder” or paste your resume.' : ' Now paste your resume.');
        var form_ = document.querySelector('.tl-form');
        if (form_) form_.parentNode.insertBefore(note, form_);
      }).catch(function () {});
    }
  };

  /* ---------- keywords of a job description: the skills it names and the terms it repeats, and a skills line to copy ---------- */
  tools['job-description-keywords'] = function () {
    var out = $('tl-out'), detail = $('tl-detail'), pats = null;
    var F = form(function (v) {
      if (pats === null) { detail.innerHTML = ''; return idle(out, 'Keywords', 'Loading the skills list…'); }
      var jd = clean(v.jd), words = jd ? jd.split(/\s+/).length : 0;
      if (words < 30) { detail.innerHTML = ''; return idle(out, 'Keywords', words ? 'Paste the whole description: at least 30 words.' : 'Paste a job description to see the keywords it stresses.'); }
      var skills = T.findSkills(jd, pats), terms = T.keyTerms(jd, pats, 20);
      board(out, 'Keywords', skills.length + ' skills · ' + terms.length + ' terms', big(String(skills.length + terms.length), 'keywords') +
        sub(skills.length ? 'Named skills: ' + skills.slice(0, 6).join(', ') + (skills.length > 6 ? ' and ' + (skills.length - 6) + ' more.' : '.') : 'The posting names none of the tracked skills; its repeated terms are below.'));
      var pill = function (t) { return '<span class="pill ok">' + esc(t) + '</span>'; };
      detail.innerHTML =
        (skills.length ? '<div class="card"><p class="tl-t">Skills the posting names</p><div class="tl-pills">' + skills.map(pill).join('') + '</div></div>' : '') +
        (terms.length ? '<div class="card"><p class="tl-t">Terms the posting repeats</p><div class="tl-pills">' + terms.map(function (t) { return pill(t.term + ' ×' + t.n); }).join('') +
          '</div><p class="note">×3 means the posting uses the term three times. Use these words where they describe work you really did.</p></div>' : '') +
        (skills.length ? '<div class="card"><p class="tl-t">A skills line to copy</p><textarea id="tl-line" rows="2" readonly aria-label="Skills line">Skills: ' + esc(skills.join(', ')) + '</textarea>' +
          '<p><button class="btn sm" type="button" data-copy="tl-line">Copy the line</button> <span class="note">Delete the skills you do not have before you paste it.</span></p></div>' : '') +
        '<p><a class="btn ghost sm" href="' + H.base + '/tools/resume-match/">Check your resume against this posting</a></p>';
    });
    fetch(H.base + '/data/skills.json').then(function (res) { if (!res.ok) throw new Error('skills'); return res.json(); })
      .then(function (data) { pats = T.compilePats(data); F.draw(); })
      .catch(function () { pats = []; F.draw(); });
    var go = $('tl-run');
    if (go) go.addEventListener('click', function () { F.draw(); if (out.scrollIntoView) out.scrollIntoView({ behavior: 'smooth', block: 'start' }); });
    var slug = (location.search.match(/[?&]job=([a-z0-9-]{3,160})/) || [])[1];         // ?job=<slug>: read the posting from its page on this site
    if (slug && window.fetch && window.DOMParser) {
      fetch(H.base + '/job/' + slug + '/').then(function (r) { return r.ok ? r.text() : ''; }).then(function (page) {
        if (!page) return;
        var doc = new DOMParser().parseFromString(page, 'text/html'), d = doc.querySelector('.prose.desc') || doc.querySelector('.prose');
        if (!d) return;
        var blocks = [].map.call(d.querySelectorAll('h2,h3,h4,p,li'), function (x) { return x.textContent.trim(); }).filter(Boolean);
        F.set('jd', blocks.length ? blocks.join('\n') : d.textContent.trim()); F.save(); F.draw();
      }).catch(function () {});
    }
  };

  /* ---------- cover letter ---------- */
  tools['cover-letter'] = function () {
    var paper = $('tl-paper'), count = $('tl-count');
    form(function (v) {
      var text = T.coverLetter(v), n = T.wordCount(text), todo = (text.match(/\[[^\]]+\]/g) || []).length;
      paper.textContent = text;
      count.textContent = n + ' words' + (todo ? ' · ' + todo + ' blank' + (todo === 1 ? '' : 's') + ' in [brackets] still to fill' : n > 320 ? ' · long for a cover letter: shorten your answers' : ' · fits on one page');
    });
  };

  /* ---------- negotiation email ---------- */
  tools['negotiation-email'] = function () {
    var paper = $('tl-paper'), info = $('tl-count'), offerL = $('tl-offer-l'), dateL = $('tl-date-l');
    var EXTRA = [['x_signon', 'a sign-on bonus', 'counter'], ['x_once', 'a one-time bonus', 'raise'], ['x_equity', 'additional equity', 'counter raise'], ['x_pto', 'extra paid days off', 'counter raise'],
      ['x_remote', 'more remote days', 'counter raise'], ['x_review', 'an earlier salary review', 'counter raise'], ['x_start', 'a later start date', 'counter']];
    form(function (v) {
      var sc = v.scenario;
      each('[data-for]', function (el) { el.hidden = el.getAttribute('data-for').split(' ').indexOf(sc) < 0; });
      if (offerL) offerL.textContent = sc === 'raise' ? 'Your current salary' : 'Salary they offered';
      if (dateL) dateL.textContent = sc === 'time' ? 'Date you will answer by' : sc === 'raise' ? 'Talk before (optional)' : 'Date you will answer by (optional)';
      var f = { scenario: sc, tone: v.tone, name: v.name, to: v.to, company: v.company, title: v.title, cur: v.cur, offer: v.offer, target: v.target, reasons: sc === 'time' ? '' : v.reasons, deadline: v.deadline,
        extras: EXTRA.filter(function (x) { return v[x[0]] && x[2].split(' ').indexOf(sc) >= 0; }).map(function (x) { return x[1]; }) };
      var m = T.negotiationEmail(f), todo = (m.text.match(/\[[^\]]+\]/g) || []).length;
      paper.textContent = m.text;
      info.textContent = (sc !== 'time' && m.pct != null ? (m.gap >= 0 ? 'You are asking for ' + money(m.gap, v.cur, 0) + ' more (' + plain(m.pct, 1) + '%). ' : 'Your figure is below the current one. Check the two numbers. ') : '') +
        T.wordCount(m.body) + ' words' + (todo ? ' · ' + todo + ' blank' + (todo === 1 ? '' : 's') + ' in [brackets] still to fill' : '');
    });
  };

  /* ---------- job description checker ---------- */
  tools['job-description-checker'] = function () {
    var out = $('tl-out'), detail = $('tl-detail');
    var F = form(function (v) {
      var r = T.checkJD(v.text);
      if (r.error) { detail.innerHTML = ''; return idle(out, 'Job description score', clean(v.text) ? 'Paste the whole posting: ' + r.words + ' words is too little to check. At least 40 are needed.' : 'Paste a job description to see its score and what to fix.'); }
      board(out, 'Job description score', r.label, big(String(r.score), '/ 100') + meter(r.score) +
        sub(esc(fmt(r.words)) + ' words. ' + (r.fixes ? r.fixes + ' point' + (r.fixes === 1 ? '' : 's') + ' to fix or check, most important first.' : 'Nothing to fix. The list shows what was tested.')));
      detail.innerHTML = list(r.items);
    });
    var go = $('tl-run');
    if (go) go.addEventListener('click', function () { F.draw(); if (out.scrollIntoView) out.scrollIntoView({ behavior: 'smooth', block: 'start' }); });
  };

  /* ---------- JobPosting structured data ---------- */
  tools['jobposting-schema'] = function () {
    var out = $('tl-out'), checks = $('tl-detail'), code = $('tl-code'), TYPES = ['FULL_TIME', 'PART_TIME', 'CONTRACTOR', 'TEMPORARY', 'INTERN', 'VOLUNTEER', 'PER_DIEM', 'OTHER'];
    var d = new Date(), today = d.getFullYear() + '-' + ('0' + (d.getMonth() + 1)).slice(-2) + '-' + ('0' + d.getDate()).slice(-2);
    var posted = root.querySelector('[data-k="posted"]'); if (posted) posted.setAttribute('value', today);        // default: published today
    form(function (v) {
      var remote = v.loc === 'remote';
      each('[data-show]', function (el) { el.hidden = el.getAttribute('data-show') !== v.loc; });
      var r = T.jobPosting({ title: v.title, description: v.desc, datePosted: v.posted, validThrough: v.through, employmentType: TYPES.filter(function (t) { return v['et_' + t]; }),
        orgName: v.org, orgUrl: v.orgurl, orgLogo: v.logo, locType: v.loc, street: remote ? '' : v.street, city: remote ? '' : v.city, region: remote ? '' : v.region, postal: remote ? '' : v.postal,
        country: remote ? '' : v.country, remoteCountries: remote ? v.remote : '', salaryCurrency: v.scur, salaryMin: v.smin, salaryMax: v.smax, salaryUnit: v.sunit, identifier: v.ident, directApply: v.direct }, today);
      var e = r.errors.length, w = r.warnings.length;
      board(out, 'Markup check', r.valid ? (w ? 'Valid' : 'Complete') : 'Not valid yet',
        big(r.valid ? (w ? 'Valid' : 'Complete') : e + ' to fix', r.valid ? (w ? 'can be richer' : 'nothing missing') : 'required field' + (e === 1 ? '' : 's')) +
        sub(r.valid ? (w ? 'Every required field is present. ' + w + ' recommended field' + (w === 1 ? ' is' : 's are') + ' still empty: filling them gives Google more to show.' : 'All required and recommended fields are filled. Copy the code and paste it into the HTML of the job page.')
          : 'Google leaves a job out of the job search experience when a required field is missing. Fill in the fields listed below.') +
        kv([['Required missing', String(e)], ['Recommended missing', String(w)]]));
      var item = function (level) { return function (m) { var i = m.indexOf(': '), d = m.slice(i + 2); return { level: level, t: m.slice(0, i), d: d.charAt(0).toUpperCase() + d.slice(1) }; }; };   // "property: text"
      checks.innerHTML = e || w ? list(r.errors.map(item('fix')).concat(r.warnings.map(item('warn')))) : '';
      code.value = r.script;
    });
  };

  /* ---------- Boolean search ---------- */
  tools['boolean-search'] = function () {
    var q1 = $('tl-q1'), q2 = $('tl-q2'), q3 = $('tl-q3'), n1 = $('tl-n1'), n2 = $('tl-n2'), n3 = $('tl-n3');
    var show = function (el, text, hint) { el.textContent = text || hint; el.setAttribute('data-empty', text ? '0' : '1'); };
    var long = function (n) { return n + ' search word' + (n === 1 ? '' : 's') + (n > 32 ? '. Google ignores words after the 32nd, so shorten the lists.' : '.'); };
    form(function (v) {
      var r = T.booleanSearch(v), hint = 'Add a job title or a skill above to build the string.';
      show(q1, r.boolean, hint); show(q2, r.linkedin, hint); show(q3, r.github, r.empty ? hint : 'Add at least one skill: GitHub profiles rarely state a job title, so this string is built from skills.');
      n1.textContent = r.empty ? '' : r.length + ' characters. Operators are in capitals, phrases in quotes.';
      n2.textContent = r.empty ? '' : long(r.words);
      n3.textContent = r.github ? long(r.wordsGithub) : '';
    });
  };

  /* ---------- contractor rate ---------- */
  tools['contractor-rate'] = function () {
    var out = $('tl-out'), title = 'Rate you need to charge';
    form(function (v) {
      if (!clean(v.income)) return idle(out, title, 'Enter the yearly income you want to end up with, before tax.');
      var r = T.contractorRate(v), s = v.cur;
      if (!r) return idle(out, title, 'Check the figures: the income must be above zero, days off below 260, the billable share above 0% and hours per day 24 or fewer.');
      board(out, title, fmt(r.days, 1) + ' billable days a year',
        big(money(r.day, s, 0), 'per day') +
        sub('You need to invoice ' + esc(money(r.revenue, s, 0)) + ' a year over ' + esc(fmt(r.days, 1)) + ' billable days. ' +
          (r.upliftPct > 0.5 ? 'Per hour that is ' + esc(plain(r.upliftPct, 0)) + '% more than the ' + esc(money(r.salariedHour, s, 2)) + ' an hour that the same yearly income pays in a salaried job (2,080 paid hours a year). The difference covers your days off, unbilled time and costs, which an employer would otherwise carry.' : 'With no days off, no unbilled time and no extra costs entered, this equals the salaried hourly rate. Fill in those fields for a realistic figure.')) +
        kv([['Per hour', money(r.hour, s, 2)], ['Per day', money(r.day, s, 0)], ['Per month, average', money(r.month, s, 0)], ['Yearly invoices', money(r.revenue, s, 0)], ['Days worked', fmt(r.workDays, 1)], ['Days billed', fmt(r.days, 1)]]));
    });
  };

  /* ---------- salary checker ---------- */
  tools['salary-checker'] = function () {
    var out = $('tl-out'), D;
    try { D = JSON.parse($('tl-data').textContent); } catch (e) { D = null; }
    var text = function (k) { var el = root.querySelector('[data-k="' + k + '"]'), o = el && el.options[el.selectedIndex]; return o ? o.text : ''; };
    var K = function (x) { return '$' + fmt(x / 1000, 0) + 'K'; };
    form(function (v) {
      var what = (v.lvl && v.lvl !== 'none' ? text('lvl') + ' ' : '') + (v.cat ? text('cat') : 'tech') + ' roles' + (v.lvl === 'none' ? ' with no level in the title' : '') + (v.skill ? ' that mention ' + v.skill : '');
      var g = T.salaryGroup(D, v.cat, v.lvl, v.skill), pay = num(v.pay);
      if (!g) return idle(out, 'Advertised salaries', 'Fewer than ' + (D ? D.min : 20) + ' open postings with a published salary match ' + what + ', so no figure is shown. Remove the skill or pick “Any level” for a larger sample.');
      var lo = g.p10 - (g.p90 - g.p10) * 0.12, hi = g.p90 + (g.p90 - g.p10) * 0.12, at = function (x) { return hi > lo ? Math.max(0, Math.min(100, (x - lo) / (hi - lo) * 100)) : 50; };
      var bar = '<div class="tl-range" aria-hidden="true"><i style="left:' + plain(at(g.p25), 2) + '%;width:' + plain(at(g.p75) - at(g.p25), 2) + '%"></i><u style="left:' + plain(at(g.median), 2) + '%"></u>' +
        (pay >= 1000 ? '<b style="left:' + plain(at(pay), 2) + '%"><span>you</span></b>' : '') + '</div><div class="tl-scale" aria-hidden="true"><span>' + K(g.p10) + ' · lowest tenth</span><span>top tenth · ' + K(g.p90) + '</span></div>';
      var you = '', typo = pay > 0 && pay < 1000;                 // "150" was probably meant as 150,000
      if (typo) you = 'Enter the full yearly figure, for example 150,000 or 150k. ';
      else if (pay > 0) {
        var p = Math.round(T.percentile(D.q, g.vals, pay)), diff = pay - g.median;
        you = '<b>Your ' + esc(money(pay, '$', 0)) + '</b> is ' + (p <= 0 ? 'below every advertised midpoint in this group' : p >= 100 ? 'above every advertised midpoint in this group' : 'higher than about ' + p + '% of the advertised midpoints in this group') +
          (diff ? ', ' + esc(money(Math.abs(diff), '$', 0)) + ' (' + esc(plain(Math.abs(diff) / g.median * 100, 0)) + '%) ' + (diff > 0 ? 'above' : 'below') + ' the median. ' : ', exactly at the median. ');
      }
      board(out, 'Advertised salaries', fmt(g.n) + ' postings',
        big(K(g.median), 'median') + bar +
        sub(you + 'Sample: ' + esc(fmt(g.n)) + ' open ' + esc(what) + ', each with a published yearly US-dollar range, as of ' + esc(D.date) + '. The typical posting advertises ' + esc(K(g.low)) + ' to ' + esc(K(g.high)) + '.' + (pay > 0 ? '' : ' Enter your salary to see where it sits.')) +
        kv([['Lowest tenth, below', K(g.p10)], ['Middle half', K(g.p25) + ' – ' + K(g.p75)], ['Median', K(g.median)], ['Top tenth, above', K(g.p90)], ['Postings counted', fmt(g.n)]]));
    });
  };

  /* ================================================================ pages added 2026-11-13 ================================================================ */
  function localIso() { var d = new Date(); return d.getFullYear() + '-' + ('0' + (d.getMonth() + 1)).slice(-2) + '-' + ('0' + d.getDate()).slice(-2); }
  function fill(el, text, hint) { el.textContent = text || hint; el.setAttribute('data-empty', text ? '0' : '1'); }
  function blanks(text) { var n = (text.match(/\[[^\]]+\]/g) || []).length; return n ? ' · ' + n + ' blank' + (n === 1 ? '' : 's') + ' in [brackets] still to fill' : ''; }
  // a letter or an email on the sheet beside the form; `note` adds a line in front of the word count
  function letter(make, note, each_) {
    var paper = $('tl-paper'), info = $('tl-count');
    return form(function (v) {
      if (each_) each_(v);
      var m = make(v);
      paper.textContent = m.text;
      info.textContent = (note ? note(m, v) : '') + T.wordCount(m.body) + ' words' + blanks(m.text);
    });
  }

  /* ---------- thank-you email ---------- */
  tools['thank-you-email'] = function () { letter(T.thankYou); };

  /* ---------- resignation letter ---------- */
  tools['resignation-letter'] = function () {
    var today = localIso(), date = root.querySelector('[data-k="date"]'), last = root.querySelector('[data-k="lastDay"]'), two = T.lastDay({ date: today, amount: 2, unit: 'weeks' });
    if (date) date.setAttribute('value', today);                        // the letter is dated today unless changed
    if (last && two) last.setAttribute('data-ex', two.last);            // the example leaves two weeks from today
    letter(T.resignation, function (m) {
      return m.days == null ? 'Check your contract for the notice period you owe. '
        : m.days < 0 ? 'The last working day is before the date of the letter. Check the two dates. '
        : 'From the date of the letter to your last day: ' + m.days + ' day' + (m.days === 1 ? '' : 's') + '. Check that this covers the notice period in your contract. ';
    }, function (v) { each('[data-if]', function (el) { el.hidden = !v[el.getAttribute('data-if')]; }); });
  };

  /* ---------- raise request email ---------- */
  tools['raise-request-email'] = function () {
    var out = $('tl-out'), title = 'The raise you are asking for';
    letter(T.raiseRequest, null, function (v) {
      var m = T.raiseRequest(v), s = v.cur, per = v.period === 'month' ? 'month' : 'year';
      if (m.diff == null) return idle(out, title, 'Enter your current pay and the pay you are asking for to see the difference in percent and per month.');
      if (m.diff <= 0) return idle(out, title, 'The pay you ask for is not above your current pay. Check the two numbers.');
      board(out, title, '+' + money(m.perYear, s, 0) + ' a year', big('+' + plain(m.pct, 1) + '%', 'more than now') +
        sub('From ' + esc(money(num(v.current), s, 0)) + ' to ' + esc(money(num(v.target), s, 0)) + ' a ' + per + ', before tax. The email states the same percent, so the reader does not have to work it out.') +
        kv([['More per month', '+' + cash(m.perMonth, s)], ['More per year', '+' + money(m.perYear, s, 0)], ['Pay now, per ' + per, money(num(v.current), s, 0)], ['Pay asked for, per ' + per, money(num(v.target), s, 0)]]));
    });
  };

  /* ---------- reference request email ---------- */
  tools['reference-request-email'] = function () { letter(T.referenceRequest); };

  /* ---------- LinkedIn headline and About ---------- */
  tools['linkedin-headline'] = function () {
    var hint = 'Enter your job title to build the headlines.';
    form(function (v) {
      var r = T.linkedin(v);
      [0, 1, 2].forEach(function (i) {
        var h = r.empty ? null : r.headlines[i], n = i + 1;
        $('tl-c' + n).hidden = !h && i > 0;
        $('tl-k' + n).textContent = 'Headline ' + n + (h ? ' · ' + h.kind.toLowerCase() : '');
        fill($('tl-q' + n), h ? h.text : '', hint);
        $('tl-n' + n).textContent = h ? h.length + ' of ' + T.HEADLINE_MAX + ' characters · ' + h.left + ' left' : '';
      });
      fill($('tl-q4'), r.empty ? '' : r.about, 'Your About paragraph appears here.');
      $('tl-n4').textContent = r.empty ? '' : fmt(r.aboutLength) + ' of ' + fmt(T.ABOUT_MAX) + ' characters · ' + T.wordCount(r.about) + ' words' + blanks(r.about);
    });
  };

  /* ---------- interview answer ---------- */
  tools['interview-answer-builder'] = function () {
    var paper = $('tl-paper'), info = $('tl-count'), out = $('tl-out'), detail = $('tl-detail'), title = 'Speaking time';
    form(function (v) {
      var r = T.star(v), q = clean(v.question);
      if (r.empty) {
        fill(paper, '', 'Fill in the four parts. Your answer appears here as you type.'); info.textContent = ''; detail.innerHTML = '';
        return idle(out, title, 'Describe the situation, the task, what you did and the result to see how long the answer takes to say.');
      }
      fill(paper, (q ? 'Question: ' + q + '\n\n' : '') + r.text);
      info.textContent = r.words + ' words · about ' + r.time + ' spoken at ' + T.WPM + ' words a minute';
      var at = Math.max(4, Math.min(96, r.seconds / 150 * 100));
      board(out, title, r.complete ? (r.fixes ? r.fixes + ' to fix or check' : 'All checks pass') : 'Not complete yet',
        big(r.time, 'said aloud') +
        '<div class="tl-range" aria-hidden="true"><i style="left:40%;width:20%"></i><b style="left:' + plain(at, 1) + '%"><span>this answer</span></b></div>' +
        '<div class="tl-scale" aria-hidden="true"><span>0 s</span><span>green: 60 to 90 s</span><span>2 min 30 s</span></div>' +
        sub(esc(r.words + ' words at ' + T.WPM + ' words a minute. ') + (r.fixes ? 'The list below shows what to fix or check, most important first.' : 'Every check passes.') + ' People speak at different speeds: say it aloud once with a timer.') +
        kv([['Situation', r.parts.situation + ' words'], ['Task', r.parts.task + ' words'], ['Action', r.parts.action + ' words'], ['Result', r.parts.result + ' words']]));
      detail.innerHTML = list(r.checks);
    });
  };

  /* ---------- resume bullet point ---------- */
  tools['resume-bullet-builder'] = function () {
    var out = $('tl-out'), detail = $('tl-detail'), verbs = $('tl-verbs'), title = 'Bullet point check', hint = 'Type a verb, what you did and the result to build the line.';
    if (verbs) verbs.textContent = T.STRONG.map(cap).join(', ') + '.';
    form(function (v) {
      var r = T.bullet(v);
      [0, 1, 2].forEach(function (i) {
        var x = r.variants[i], n = i + 1;
        $('tl-c' + n).hidden = !x && i > 0;
        $('tl-k' + n).textContent = 'Variant ' + n + (x ? ' · ' + x.kind.toLowerCase() : '');
        fill($('tl-q' + n), x ? x.text : '', hint);
        $('tl-n' + n).textContent = x ? x.length + ' characters · about ' + x.lines + ' line' + (x.lines === 1 ? '' : 's') + ' on the page' : '';
      });
      if (r.empty) { detail.innerHTML = ''; return idle(out, title, hint); }
      board(out, title, r.passed === r.of ? 'All checks pass' : (r.of - r.passed) + ' to fix', big(r.passed + ' of ' + r.of, 'checks passed') + meter(r.of ? r.passed / r.of * 100 : 0) +
        sub('The checks are run on the first variant: <b>' + esc(r.variants[0].text) + '</b>'));
      detail.innerHTML = list(r.checks);
    });
  };

  /* ---------- job search funnel ---------- */
  tools['job-search-calculator'] = function () {
    var out = $('tl-out'), title = 'Applications for one offer';
    form(function (v) {
      if (!clean(v.perWeek) && !clean(v.reply) && !clean(v.offer)) return idle(out, title, 'Enter how many applications you send a week and your own two rates.');
      var r = T.funnel(v);
      if (!r) return idle(out, title, 'Check the figures: applications a week and weeks must be above zero, and each rate a percent from 0 to 100 or a count such as “3 of 40”.');
      var n1 = function (x) { return fmt(x, x < 10 ? 1 : 0); }, pc = function (x) { return plain(x, 1) + '%'; }, right = fmt(r.applications, 1) + ' applications in ' + fmt(r.weeks, 1) + ' week' + (r.weeks === 1 ? '' : 's');
      var rough = [r.replyFrom, r.offerFrom].some(function (n) { return n != null && n < 20; }) ? ' A rate worked out from fewer than 20 applications or interviews is rough: update it as your search goes on.' : '';
      var rows = [['Applications sent', fmt(r.applications, 1)], ['Interviews expected', n1(r.interviews)], ['Offers expected', fmt(r.offers, r.offers < 10 ? 2 : 0)], ['Chance of at least one offer', plain(r.chance, 0) + '%'],
        ['Applications that lead to an interview', pc(r.replyPct)], ['Interviews that lead to an offer', pc(r.offerPct)]];
      if (r.perOffer == null) return board(out, title, right, '<p class="tl-big tl-dim">—</p>' +
        sub('One of your rates is 0%, so this arithmetic gives no offer however many applications you send. If your search has only just started, enter the rates again once you have had a few replies.') + kv(rows));
      board(out, title, right, big(fmt(r.perOffer, 0), 'applications') +
        sub('At your rates, one offer takes about ' + esc(fmt(r.perOffer, 0)) + ' applications: ' + esc(n1(r.perInterview)) + ' applications for each interview, and ' + esc(n1(100 / r.offerPct)) + ' interview' + (r.offerPct === 100 ? '' : 's') + ' for each offer. At ' +
          esc(fmt(r.perWeek, 1)) + ' a week that is about ' + esc(n1(r.weeksToOffer)) + ' week' + (r.weeksToOffer === 1 ? '' : 's') + ' of applying. These are averages from the numbers you typed. They are not statistics about the job market and not a promise.' + rough) +
        kv(rows));
    });
  };

  /* ---------- remote work savings ---------- */
  tools['remote-work-savings'] = function () {
    var out = $('tl-out'), title = 'Saved by working from home';
    form(function (v) {
      if (['minutes', 'cost', 'lunch', 'lunchHome', 'home'].every(function (k) { return !clean(v[k]); })) return idle(out, title, 'Enter your commute and what a day at the office costs you.');
      var r = T.remoteSavings(v), s = v.cur;
      if (!r) return idle(out, title, 'Check the figures: office days a week from 0 to 7, working weeks a year from 1 to 52, and a commute of at most 12 hours one way.');
      if (!r.days) return board(out, title, 'No change', '<p class="tl-big tl-dim">0</p>' + sub('The number of office days is the same before and after, so nothing changes. Lower “office days a week after the change”.'));
      var more = r.days < 0, flip = more ? -1 : 1, hours = r.hours * flip, cashNet = r.money * flip, gain = cashNet >= 0 !== more;       // gain: money stays in your pocket
      var signed = function (x) { return (x < 0 ? '−' : '') + money(Math.abs(x), s, 0); };
      board(out, more ? 'Cost of more office days' : title, fmt(Math.abs(r.days), 1) + (more ? ' more' : ' fewer') + ' office days a year',
        (cashNet ? big(money(Math.abs(cashNet), s, 0), gain ? 'saved a year' : 'more spent a year') : big(fmt(hours, 0), more ? 'more hours of travel a year' : 'hours of travel saved a year')) +
        sub('Going from ' + esc(fmt(r.daysNow, 1)) + ' to ' + esc(fmt(r.daysNew, 1)) + ' office days a week over ' + esc(fmt(r.weeks, 1)) + ' working weeks ' + (more ? 'adds ' : 'removes ') + '<b>' + esc(fmt(hours, 0)) + ' hours</b> of travel a year, which is ' +
          esc(fmt(hours / 40, 1)) + ' working weeks of 40 hours.' + (cashNet ? ' In money that is ' + esc(money(Math.abs(cashNet) / 12, s, 0)) + ' a month ' + (gain ? 'kept' : 'spent') + '.' : '') +
          (r.timeValue != null ? ' At the hourly figure you entered, the travel time alone is worth ' + esc(money(Math.abs(r.timeValue), s, 0)) + ' a year.' : '') + ' Every figure here is your own; nothing is assumed about prices or taxes.') +
        kv([[more ? 'Extra travel time a year' : 'Travel time saved a year', fmt(hours, 0) + ' h'], [more ? 'Extra travel cost' : 'Travel cost saved', signed(r.travel * flip)],
          [more ? 'Extra lunch and coffee' : 'Lunch and coffee saved', signed(r.food * flip)], r.homeCost ? [more ? 'Saved at home' : 'Extra cost at home', signed(r.homeCost * flip)] : null,
          [gain ? 'Money kept a year' : 'Extra cost a year', money(Math.abs(cashNet), s, 0)], [gain ? 'Money kept a month' : 'Extra cost a month', money(Math.abs(cashNet) / 12, s, 0)],
          r.timeValue != null ? ['Travel time in money', money(Math.abs(r.timeValue), s, 0)] : null]));
    });
  };

  /* ---------- last working day ---------- */
  tools['last-working-day'] = function () {
    var out = $('tl-out'), title = 'Your last working day', date = root.querySelector('[data-k="date"]');
    if (date) date.setAttribute('value', localIso());                   // notice is given today unless changed
    var short = function (s) { var p = T.longDate(s).split(' '); return p[0].slice(0, 3) + ' ' + p.slice(1).join(' '); };
    form(function (v) {
      if (!clean(v.amount)) return idle(out, title, 'Enter the length of your notice period.');
      var r = T.lastDay(v);
      if (!r) return idle(out, title, 'Check the two fields: a real date, and a notice period from 0 up to 10 years.');
      var one = r.count === 1, period = plain(r.count, 2) + ' ' + ({ weeks: one ? 'week' : 'weeks', workdays: one ? 'working day' : 'working days', months: one ? 'month' : 'months', days: one ? 'calendar day' : 'calendar days' })[r.unit];
      board(out, title, r.count ? period + ' of notice' : 'No notice period', big(short(r.last), T.dayName(r.last)) +
        sub('Notice given on ' + esc(T.longDate(r.date, true)) + '. ' + (r.count ? 'The notice period of ' + esc(period) + ' starts ' + (r.from === 'same' ? 'that day' : 'the next day') + ' and ends on ' + esc(T.longDate(r.end, true)) + '.' : 'With no notice period, the job ends that day.') +
          (r.endsOnWeekend ? ' That is a ' + esc(T.dayName(r.end)) + ', so the last Monday-to-Friday on or before it is ' + esc(T.longDate(r.last, true)) + '.' : '') +
          (r.count && !r.workDays ? ' No working day falls inside this notice period.' : '') +
          (r.givenOnWeekend ? ' The day you picked for giving notice is a ' + esc(T.dayName(r.date)) + '; an employer may count it from the next working day.' : '') +
          ' <b>Public holidays are not known to this page.</b> If one falls on that day or inside the period, or if your contract counts notice differently, the date changes: your contract decides.') +
        kv([['Notice ends', short(r.end)], ['Last working day', short(r.last)], ['Working days left', fmt(r.workDays) + ' (Mon to Fri)'], ['Calendar days', fmt(r.calendarDays)]]));
    });
  };

  /* ---------- cost per hire ---------- */
  tools['cost-per-hire'] = function () {
    var out = $('tl-out'), table = $('tl-table'), title = 'Cost per hire';
    form(function (v) {
      var r = T.costPerHire(v), s = v.cur;
      if (!r) { table.innerHTML = ''; return idle(out, title, 'Enter what the hiring cost and how many people were hired.'); }
      var gap = r.unpriced ? ' Hours entered without an hourly cost are not counted: add what an hour of that person’s time costs.' : '';
      if (r.perHire == null) board(out, title, 'Total ' + money(r.total, s, 0), '<p class="tl-big tl-dim">—</p>' + sub('Enter the number of people hired (1 or more) to divide the total of ' + esc(money(r.total, s, 0)) + '.' + gap));
      else board(out, title, fmt(r.hires, 1) + (r.hires === 1 ? ' hire' : ' hires'), big(money(r.perHire, s, 0), 'per hire') +
        sub('Total cost ' + esc(money(r.total, s, 0)) + ' ÷ ' + esc(fmt(r.hires, 1)) + (r.hires === 1 ? ' hire' : ' hires') + '. The largest part is <b>' + esc(r.top.name.toLowerCase()) + '</b>: ' + esc(plain(r.top.share, 0)) + '% of the total.' + gap) +
        kv([['Total cost', money(r.total, s, 0)], ['Paid to others', money(r.outside, s, 0) + ' · ' + plain(r.outside / r.total * 100, 0) + '%'], ['Your staff’s time', money(r.time, s, 0) + ' · ' + plain(r.time / r.total * 100, 0) + '%'],
          r.hours ? ['Staff hours per hire', fmt(r.hoursPerHire, 1)] : null]));
      table.innerHTML = '<div class="tablewrap"><table><tr><th>Part of the cost</th><th>Amount</th><th>Share</th><th>Per hire</th></tr>' + r.parts.map(function (p) {
        return '<tr><td>' + esc(p.name) + '</td><td class="num">' + esc(money(p.amount, s, 0)) + '</td><td class="num">' + esc(plain(p.share, 1)) + '%</td><td class="num">' + (p.perHire == null ? '—' : esc(money(p.perHire, s, 0))) + '</td></tr>';
      }).join('') + '<tr class="tl-total"><td>Total</td><td class="num">' + esc(money(r.total, s, 0)) + '</td><td class="num">100%</td><td class="num">' + (r.perHire == null ? '—' : esc(money(r.perHire, s, 0))) + '</td></tr></table></div>';
    });
  };

  /* ---------- interview scorecard ---------- */
  tools['interview-scorecard'] = function () {
    var out = $('tl-out'), table = $('tl-table'), sheet = $('tl-sheet'), text = $('tl-text'), IDS = ['a', 'b', 'c'], N = 6, title = 'Weighted score';
    var two = function (x) { return roundTo(x, 2).toFixed(2); };          // scores always with two decimals, so 4.05 and 4.00 line up
    form(function (v) {
      var crit = [], i;
      for (i = 1; i <= N; i++) crit.push({ name: v['c' + i], weight: v['w' + i] });
      var r = T.scorecard({ role: v.role, max: v.max, criteria: crit, candidates: IDS.map(function (p) { var x = []; for (var k = 1; k <= N; k++) x.push(v[p + '_r' + k]); return { name: v[p + '_name'], ratings: x }; }) });
      for (i = 1; i <= N; i++) IDS.forEach(function (p) {                // each rating box carries the name of its criterion; a box without one is hidden
        var lab = root.querySelector('label[for="tl-' + p + '_r' + i + '"]'), c = r.criteria.filter(function (x) { return x.i === i - 1; })[0];
        if (!lab) return;
        lab.parentNode.hidden = !c || !(c.weight > 0);
        if (c) lab.textContent = c.name + ', 1 to ' + r.max;
      });
      var notes = [];
      if (r.equal) notes.push('No weights are typed, so every criterion counts the same.');
      else if (r.criteria.length && !r.sum100) notes.push('The weights add up to ' + plain(r.total, 2) + ', not 100, so each one counts as its share of that total.');
      if (r.unweighted.length) notes.push(andList(r.unweighted) + (r.unweighted.length === 1 ? ' has' : ' have') + ' no weight and ' + (r.unweighted.length === 1 ? 'is' : 'are') + ' not counted.');
      if (r.criteria.length && r.criteria.length < 4) notes.push('This page suggests four to six criteria; you have ' + r.criteria.length + '.');
      if (!r.criteria.length) {
        sheet.innerHTML = '<p class="note">Name the criteria above to build the scorecard.</p>'; text.textContent = ''; table.innerHTML = '';
        return idle(out, title, 'Name four to six criteria, give each a weight, then rate each candidate.');
      }
      var scale = []; for (i = 1; i <= r.max; i++) scale.push(i);
      sheet.innerHTML = '<p class="tl-t">Interview scorecard' + (r.role ? ': ' + esc(r.role) : '') + '</p><p class="tl-fill">Candidate ______________________ &nbsp; Interviewer ______________________ &nbsp; Date ______________</p>' +
        '<div class="tablewrap"><table><tr><th>Criterion</th><th>Weight</th><th>Rating: circle one</th><th>What you saw or heard</th></tr>' +
        r.criteria.map(function (c) { return '<tr><td>' + esc(c.name) + '</td><td class="num">' + esc(plain(c.share, 1)) + '%</td><td class="num">' + scale.join(' &nbsp; ') + '</td><td class="tl-wide"></td></tr>'; }).join('') +
        '</table></div><p class="note">' + esc(cap(r.legend)) + '. Weighted score = sum of (rating × weight) ÷ sum of weights = ______ out of ' + r.max + '.</p>';
      text.textContent = r.text;
      var rated = r.candidates.filter(function (c) { return c.score != null; }), bad = r.candidates.reduce(function (n, c) { return n + c.bad; }, 0);
      if (bad) notes.push(bad + ' rating' + (bad === 1 ? '' : 's') + ' outside 1 to ' + r.max + (bad === 1 ? ' was' : ' were') + ' left out.');
      if (!rated.length) { table.innerHTML = ''; return board(out, title, '', '<p class="tl-big tl-dim">—</p>' + sub('Rate a candidate on each criterion, from 1 to ' + r.max + ', to see the weighted score. ' + esc(notes.join(' ')))); }
      var best = r.best >= 0 ? r.candidates[r.best] : null, top = best || rated[0], open = rated.filter(function (c) { return !c.complete; });
      board(out, title, best ? (r.tie ? 'A tie at the top' : best.name) : 'Ratings not complete', big(two(top.score), 'out of ' + r.max) +
        sub((best ? (r.tie ? 'The top candidates have the same weighted score of ' + esc(two(best.score)) + '.' : '<b>' + esc(best.name) + '</b> has the highest weighted score: ' + esc(two(best.score)) + ' out of ' + r.max + ', which is ' + esc(plain(best.pct, 0)) + '% of the maximum.')
          : esc(top.name) + ' so far: ' + esc(two(top.score)) + ' from ' + top.rated + ' of ' + top.of + ' criteria.') +
          (open.length ? ' Not fully rated yet: ' + esc(open.map(function (c) { return c.name + ' (' + c.rated + ' of ' + c.of + ')'; }).join(', ')) + '.' : '') + ' ' + esc(notes.join(' ')) +
          ' The score puts your ratings in order; the decision stays with the people who did the interviews.') +
        kv(rated.map(function (c) { return [c.name, two(c.score) + (c.complete ? '' : ' so far')]; })));
      table.innerHTML = '<div class="tablewrap"><table><tr><th>Criterion</th><th>Weight</th>' + r.candidates.map(function (c) { return '<th>' + esc(c.name) + '</th>'; }).join('') + '</tr>' +
        r.criteria.map(function (c, k) {
          return '<tr><td>' + esc(c.name) + '</td><td class="num">' + esc(plain(c.share, 1)) + '%</td>' + r.candidates.map(function (cd) { var x = cd.rows[k]; return '<td class="num">' + (x ? esc(plain(x.rating, 1)) : '—') + '</td>'; }).join('') + '</tr>';
        }).join('') +
        '<tr class="tl-total"><td>Weighted score</td><td class="num">100%</td>' + r.candidates.map(function (cd, k) { return '<td class="num' + (k === r.best && !r.tie ? ' tl-best' : '') + '">' + (cd.score == null ? '—' : esc(two(cd.score))) + '</td>'; }).join('') + '</tr></table></div>';
    });
  };

  /* ---------- resume review ---------- */
  tools['resume-review'] = function () {
    var out = $('tl-out'), detail = $('tl-detail'), title = 'Resume review';
    var F = form(function (v) {
      var r = T.resumeReview(v.text);
      if (r.error) { detail.innerHTML = ''; return idle(out, title, clean(v.text) ? 'Paste the whole resume: ' + r.words + ' words is too little to review. At least 80 are needed.' : 'Paste the text of your resume to see its score and what to fix.'); }
      var pts = function (c) { return plain(c.points, 1) + ' of ' + plain(c.max, 1); };
      board(out, title, fmt(r.words) + ' words · ' + r.pages, big(plain(r.score, 1), '/ 10') + meter(r.score * 10) +
        sub('<b>' + esc(r.verdict) + '.</b> The score is the sum of the six checks below. It rates how the page reads on a first skim; it cannot tell whether the content is true, how the layout looks or how well you fit a particular job.') +
        kv(r.checks.map(function (c) { return [c.name, pts(c)]; })));
      detail.innerHTML = '<p class="tl-t">Strengths</p>' + (r.strengths.length ? list(r.strengths.map(function (x) { return { level: 'ok', t: x.name + ': ' + x.t, d: x.d }; })) : '<p class="note">No check has full points yet.</p>') +
        '<p class="tl-t">Weaknesses</p>' + (r.weaknesses.length ? list(r.weaknesses.map(function (c) { return { level: 'warn', t: c.name + ': ' + c.t, d: 'Points: ' + pts(c) + '.' }; })) : '<p class="note">Every check has full points.</p>') +
        '<p class="tl-t">What to fix, starting with what costs the most points</p>' + (r.fixes.length ? list(r.fixes.map(function (x) { return { level: 'fix', t: x.t, d: x.d, q: x.q }; })) : '<p class="note">Nothing on our list. Read the first lines of the page once more: that is the part that gets read.</p>');
    });
    var go = $('tl-run');
    if (go) go.addEventListener('click', function () { F.draw(); if (out.scrollIntoView) out.scrollIntoView({ behavior: 'smooth', block: 'start' }); });
  };

  /* ---------- LinkedIn profile review ---------- */
  tools['linkedin-review'] = function () {
    var out = $('tl-out'), detail = $('tl-detail'), title = 'Profile review';
    var F = form(function (v) {
      var r = T.linkedinReview(v);
      if (r.empty) { detail.innerHTML = ''; return idle(out, title, 'Paste your headline and your About text to see what to fix.'); }
      board(out, title, r.fixes ? 'Fixes first' : 'Nothing to fix', big(String(r.fixes), r.fixes === 1 ? 'thing to fix' : 'things to fix') +
        sub((r.fixes ? 'The list below starts with what to fix and quotes the part of your text each point is about.' : 'None of the checks found a problem. The list shows what was tested.') + (r.notes ? ' ' + r.notes + ' smaller note' + (r.notes === 1 ? '' : 's') + ' follow.' : '')) +
        kv([['Headline', r.headline + ' / ' + T.HEADLINE_MAX], ['About', fmt(r.about) + ' / ' + fmt(T.ABOUT_MAX)], ['To fix', String(r.fixes)], ['Notes', String(r.notes)]]));
      detail.innerHTML = (r.opening ? '<div class="card"><p class="tl-t">The first ' + T.OPENING + ' characters of your About text: the part read before “see more”</p><blockquote class="tl-quote">' + esc(r.opening) + (r.more ? '…' : '') + '</blockquote></div>' : '') + list(r.items);
    });
    var go = $('tl-run');
    if (go) go.addEventListener('click', function () { F.draw(); if (out.scrollIntoView) out.scrollIntoView({ behavior: 'smooth', block: 'start' }); });
  };

  /* ---------- offer check ---------- */
  tools['offer-check'] = function () {
    var out = $('tl-out'), title = 'Your offer against advertised pay', D;
    try { D = JSON.parse($('tl-data').textContent); } catch (e) { D = null; }
    var label = function (k, val) { var el = root.querySelector('[data-k="' + k + '"]'), o = el ? Array.prototype.filter.call(el.options, function (x) { return x.value === val; })[0] : null; return o ? o.text : ''; };
    var what = function (cat, lvl) { return (lvl && lvl !== 'none' ? label('lvl', lvl) + ' ' : '') + (cat ? label('cat', cat) : 'tech') + ' roles' + (lvl === 'none' ? ' with no level in the title' : ''); };
    var K = function (x) { return '$' + fmt(x / 1000, 0) + 'K'; };
    form(function (v) {
      if (!clean(v.pay)) return idle(out, title, 'Enter the yearly pay you were offered, in US dollars.');
      var r = T.offerCheck(D, v.pay, v.cat, v.lvl);
      if (!r) return idle(out, title, 'Enter the offer as a number, for example 150,000 or 150k.');
      if (r.pay < 1000) return idle(out, title, 'Enter the full yearly figure, for example 150,000 or 150k.');
      if (!r.group) return idle(out, title, 'There are not enough open postings with a published salary to compare with today.');
      var g = r.group, lo = g.p10 - (g.p90 - g.p10) * 0.12, hi = g.p90 + (g.p90 - g.p10) * 0.12, at = function (x) { return hi > lo ? Math.max(0, Math.min(100, (x - lo) / (hi - lo) * 100)) : 50; };
      var bar = '<div class="tl-range" aria-hidden="true"><i style="left:' + plain(at(g.p25), 2) + '%;width:' + plain(at(g.p75) - at(g.p25), 2) + '%"></i><u style="left:' + plain(at(g.median), 2) + '%"></u>' +
        '<b style="left:' + plain(Math.max(4, Math.min(96, at(r.pay))), 2) + '%"><span>offer</span></b></div><div class="tl-scale" aria-hidden="true"><span>' + K(g.p10) + ' · lowest tenth</span><span>top tenth · ' + K(g.p90) + '</span></div>';
      var zone = r.zone === 'low' ? 'below the lower quarter: three out of four advertised ranges have a higher midpoint' : r.zone === 'high' ? 'above the upper quarter: three out of four advertised ranges have a lower midpoint' : 'in the middle half of the advertised ranges';
      var wide = r.wider ? ' Fewer than ' + (D.min || 20) + ' open postings with a published salary match ' + esc(what(v.cat, v.lvl)) + ', so the offer is compared with the wider group: ' + esc(what(r.cat, r.lvl)) + '.' +
        ' That group mixes ' + (r.mixesLevels && r.mixesCategories ? 'every category and level' : r.mixesLevels ? 'all levels' : 'every category') + ', so read the result as a rough guide.' +
        (r.also ? ' For comparison, ' + esc(what(r.also.cat, r.also.lvl)) + ' at every level have a median of ' + K(r.also.group.median) + ' from ' + esc(fmt(r.also.group.n)) + ' postings, senior roles included.' : '') : '';
      board(out, title, fmt(g.n) + ' postings', big((r.diff >= 0 ? '+' : '−') + plain(Math.abs(r.diff), 0) + '%', 'against the median of ' + K(g.median)) + bar +
        sub('<b>' + esc(r.verdict) + '.</b> ' + esc(money(r.pay, '$', 0)) + ' is ' + zone + '.' + wide + ' Compared with ' + esc(fmt(g.n)) + ' open ' + esc(what(r.cat, r.lvl)) + ' that publish a yearly US-dollar range, as of ' + esc(D.date) +
          '. These are advertised ranges, not what people were paid, and bonus and equity are not in them.') +
        kv([['Lower quarter, below', K(g.p25)], ['Median', K(g.median)], ['Upper quarter, above', K(g.p75)], ['Your offer', money(r.pay, '$', 0)], ['Postings counted', fmt(g.n)]]));
    });
  };

  var run = tools[root.getAttribute('data-tool')];
  if (run) run();
})();
