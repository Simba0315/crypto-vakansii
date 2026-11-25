/* Salary explorer (/salaries/explorer/): filters over every open posting that states a yearly US-dollar range, counted here in the
   browser from data/salary-explorer.json. Rows: [low $K, high $K, field, level, years asked (0 = not stated), remote, [places],
   [skills], [roles]]. Every figure shows how many postings it rests on, and none is drawn from fewer than d.min postings. */
(function () {
  var out = document.getElementById('ex-out'); if (!out || !window.fetch) return;
  var H = window.HRN || {}, base = H.base || '', esc = H.esc || function (s) { return String(s); };
  var $ = function (id) { return document.getElementById(id); };
  var F = { role: $('ex-role'), place: $('ex-place'), skill: $('ex-skill'), cat: $('ex-cat'), lvl: $('ex-lvl'), remote: $('ex-remote') };
  var d = null, MIN = 20;
  var k = function (v) { return '$' + Math.round(v) + 'K'; };
  var nf = function (x) { return Number(x).toLocaleString('en-US'); };
  var q = function (a, p) { return a[Math.min(a.length - 1, Math.floor(a.length * p))]; };            // a is sorted
  var med = function (a) { a = a.slice().sort(function (x, y) { return x - y; }); return q(a, 0.5); };
  var mid = function (r) { return (r[0] + r[1]) / 2; };

  // the filters live in the address, so a view can be shared
  var keys = ['role', 'place', 'skill', 'cat', 'lvl'];
  var fromUrl = function () {
    var p = new URLSearchParams(location.search);
    keys.forEach(function (k_) { var v = p.get(k_); if (v != null && F[k_].querySelector('option[value="' + v + '"]')) F[k_].value = v; });
    F.remote.checked = p.get('remote') === '1';
  };
  var toUrl = function () {
    var p = new URLSearchParams();
    keys.forEach(function (k_) { if (F[k_].value !== '') p.set(k_, F[k_].value); });
    if (F.remote.checked) p.set('remote', '1');
    var s = p.toString(); history.replaceState(null, '', location.pathname + (s ? '?' + s : ''));
  };

  var bars = function (rows, unit) {        // rows: [label html, value, note]; the bar is the value against the largest
    var top = Math.max.apply(null, rows.map(function (r) { return r[1]; })) || 1;
    return '<div class="hbars">' + rows.map(function (r) {
      return '<div><span class="hn">' + r[0] + '</span><span class="hb"><i style="width:' + Math.max(3, Math.round(100 * r[1] / top)) + '%"></i></span><span class="hc">' + (unit ? unit(r[1]) : r[1]) + (r[2] ? ' · ' + r[2] : '') + '</span></div>';
    }).join('') + '</div>';
  };
  var pic = function (title, cap, body) { return '<figure class="pic"><figcaption><b>' + title + '</b>' + cap + '</figcaption>' + body + '</figure>'; };

  var draw = function () {
    var f = {}; keys.forEach(function (k_) { f[k_] = F[k_].value === '' ? null : +F[k_].value; });
    var rem = F.remote.checked;
    var rows = d.rows.filter(function (r) {
      return (f.cat == null || r[2] === f.cat) && (f.lvl == null || r[3] === f.lvl) && (!rem || r[5]) &&
        (f.place == null || r[6].indexOf(f.place) >= 0) && (f.skill == null || r[7].indexOf(f.skill) >= 0) && (f.role == null || r[8].indexOf(f.role) >= 0);
    });
    toUrl();
    var what = [f.role != null ? d.roles[f.role][0] : '', f.skill != null ? d.skills[f.skill][0] : '', f.cat != null ? d.cats[f.cat][0] : '',
      f.lvl != null ? ['No level in the title', 'Intern', 'Junior', 'Senior', 'Lead and above'][f.lvl] : '', rem ? 'remote' : '',
      f.place != null ? 'in ' + d.places[f.place][0] : ''].filter(Boolean).join(' · ') || 'All postings';
    if (rows.length < MIN) {
      out.innerHTML = '<p class="ex-none"><b>' + esc(what) + ':</b> ' + nf(rows.length) + ' posting' + (rows.length === 1 ? '' : 's') + ' with pay. A figure needs at least ' + MIN + ', so none is shown. Remove a filter to widen the count.</p>';
      return;
    }
    var mids = rows.map(mid).sort(function (a, b) { return a - b; });
    var link = function (u, t) { return u ? '<a href="' + base + '/' + u + '">' + t + '</a>' : t; };
    var tile = function (l, v, s) { return '<div class="st"><span class="st-l">' + l + '</span><b class="st-v">' + v + '</b><span class="st-s">' + s + '</span></div>'; };
    var yrs = rows.filter(function (r) { return r[4] > 0; });
    var html = '<p class="ex-what"><b>' + esc(what) + '</b> · ' + nf(rows.length) + ' postings with pay</p><div class="stats3 st4">'
      + tile('Median', k(q(mids, 0.5)), nf(mids.length) + ' postings') + tile('Middle half', k(q(mids, 0.25)) + '–' + k(q(mids, 0.75)), '25% to 75%')
      + tile('Top of the market', k(q(mids, 0.75)) + '–' + k(q(mids, 0.9)), '75% to 90%') + tile('Below the middle', k(q(mids, 0.1)) + '–' + k(q(mids, 0.25)), '10% to 25%') + '</div>';
    // how the pay is spread: postings by the middle of their range, in $25K steps
    var lo = Math.floor(q(mids, 0.02) / 25) * 25, hi = Math.ceil(q(mids, 0.98) / 25) * 25, steps = [];
    for (var s = lo; s < hi; s += 25) steps.push(s);
    var cnt = steps.map(function (s_) { return mids.filter(function (m) { return m >= s_ && m < s_ + 25; }).length; }), mx = Math.max.apply(null, cnt) || 1, mi = steps.indexOf(Math.floor(q(mids, 0.5) / 25) * 25);
    var hist = '<div class="exh" role="img" aria-label="Postings by pay band">' + steps.map(function (s_, i) {
      return '<i class="' + (i === mi ? 'hi' : '') + '" style="height:' + Math.max(2, Math.round(100 * cnt[i] / mx)) + '%" data-tip="' + k(s_) + ' to ' + k(s_ + 25) + (i === mi ? ' · ' + nf(cnt[i]) + ' postings · the median is here' : ' · ' + nf(cnt[i]) + ' postings') + '"></i>';
    }).join('') + '</div><div class="exhx"><span>' + k(lo) + '</span><span>' + k(hi) + '</span></div>'
      + '<table class="sr-only"><tr><th>Pay band</th><th>Postings</th></tr>' + steps.map(function (s_, i) { return '<tr><td>' + k(s_) + ' to ' + k(s_ + 25) + '</td><td>' + nf(cnt[i]) + '</td></tr>'; }).join('') + '</table>';      // the same counts as a table, for a screen reader
    var panels = pic('How the pay is spread', 'Postings by the middle of their range, in $25K steps. The marked column holds the median.', hist);
    // pay by the years of experience the posting asks for
    var bands = [['Entry, 1–2 years', 1, 2], ['Mid, 3–5 years', 3, 5], ['Senior, 6–9 years', 6, 9], ['Expert, 10+ years', 10, 99]].map(function (b) {
      var g = yrs.filter(function (r) { return r[4] >= b[1] && r[4] <= b[2]; }); return [b[0], g.length >= MIN ? med(g.map(mid)) : 0, nf(g.length) + ' postings'];
    }).filter(function (b) { return b[1]; });
    panels += pic('Pay by experience asked', (yrs.length ? nf(yrs.length) + ' of these postings say how many years they want; the median of each group.' : 'None of these postings says how many years it wants.'),
      bands.length ? bars(bands, k) : '<p class="note">Too few postings in each group to show a figure.</p>');
    // the best-paid skills here
    var bySkill = {}; rows.forEach(function (r) { r[7].forEach(function (i) { (bySkill[i] = bySkill[i] || []).push(mid(r)); }); });
    var sk = Object.keys(bySkill).filter(function (i) { return bySkill[i].length >= MIN && +i !== f.skill; }).map(function (i) { return [+i, med(bySkill[i]), bySkill[i].length]; })
      .sort(function (a, b) { return b[1] - a[1]; }).slice(0, 8);
    if (sk.length) panels += pic('Best-paid skills here', 'Skills named in at least ' + MIN + ' of these postings, by their median pay.', bars(sk.map(function (x) { return [link(d.skills[x[0]][1], esc(d.skills[x[0]][0])), x[1], nf(x[2])]; }), k));
    // where, and in which fields
    var byPlace = {}; rows.forEach(function (r) { r[6].forEach(function (i) { (byPlace[i] = byPlace[i] || []).push(mid(r)); }); });
    var pl = Object.keys(byPlace).filter(function (i) { return byPlace[i].length >= MIN && +i !== f.place; }).map(function (i) { return [+i, byPlace[i].length, med(byPlace[i])]; })
      .sort(function (a, b) { return b[1] - a[1]; }).slice(0, 8);
    if (pl.length) panels += pic('Top locations', 'The places with the most of these postings, with their median pay.', bars(pl.map(function (x) {
      var P_ = d.places[x[0]]; return ['<i class="fl">' + esc(P_[1]) + '</i>' + link(P_[2], esc(P_[0])), x[1], k(x[2]) + ' median'];
    }), nf));
    if (f.cat == null) {
      var byCat = {}; rows.forEach(function (r) { if (r[2] >= 0) (byCat[r[2]] = byCat[r[2]] || []).push(mid(r)); });
      var ct = Object.keys(byCat).filter(function (i) { return byCat[i].length >= MIN; }).map(function (i) { return [+i, byCat[i].length, med(byCat[i])]; }).sort(function (a, b) { return b[1] - a[1]; }).slice(0, 8);
      if (ct.length) panels += pic('Top fields', 'The fields with the most of these postings, with their median pay.', bars(ct.map(function (x) { return [link(d.cats[x[0]][1], esc(d.cats[x[0]][0])), x[1], k(x[2]) + ' median']; }), nf));
    }
    out.innerHTML = html + '<div class="pics ex-pics">' + panels + '</div>';
    if (H.decorate) try { H.decorate(out); } catch (e) {}
  };

  fetch(base + '/data/salary-explorer.json').then(function (r) { return r.json(); }).then(function (data) {
    d = data; MIN = d.min || MIN;
    fromUrl(); draw();
    Object.keys(F).forEach(function (k_) { F[k_].addEventListener('change', draw); });
    $('ex-reset').addEventListener('click', function () { keys.forEach(function (k_) { F[k_].value = ''; }); F.remote.checked = false; draw(); });
  }).catch(function () { out.insertAdjacentHTML('beforeend', '<p class="note">The postings could not be loaded. The figures above are for all postings.</p>'); });
})();
