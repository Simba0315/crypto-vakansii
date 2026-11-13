/* Hiring Right Now — embeddable jobs widget.
   <div data-hrn-jobs="skill:python" data-limit="6" data-layout="list" data-theme="auto" data-accent="#1f9d55">
     <a href="…">Python jobs on Hiring Right Now</a>
   </div>
   <script src="…/widget.js" async></script>
   Layouts: list (default), cards, compact, ticker, careers. data-search="1" adds a search box and "show more".
   A company can also show its own jobs straight from its hiring system, with no account anywhere:
     data-hrn-jobs="greenhouse:acme" | "lever:acme" | "ashby:acme"   (the name of the board in that system), data-company="Acme"
   The link inside the div stays visible as the footer and works even if scripts are blocked. */
(function () {
  var S = document.currentScript;
  var base = (S && S.src ? S.src : '').replace(/\/widget\.js.*$/, '');
  function esc(v) { return String(v == null ? '' : v).replace(/[&<>"]/g, function (c) { return { '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;' }[c]; }); }
  function age(iso) {
    var p = String(iso || '').split('-'); if (p.length < 3) return '';
    var now = new Date(), d = new Date(+p[0], +p[1] - 1, +p[2]);
    var days = Math.max(0, Math.round((new Date(now.getFullYear(), now.getMonth(), now.getDate()) - d) / 864e5));
    return days === 0 ? 'Today' : days < 14 ? days + 'd' : days < 60 ? Math.floor(days / 7) + 'w' : Math.floor(days / 30) + 'mo';
  }
  var MONO = 'ui-monospace,"SF Mono",Menlo,Consolas,monospace';
  var CSS =
    ':host{all:initial;display:block}' +
    '.w{--bg:#fff;--ink:#0e0e0c;--mut:#5d5b54;--line:#e2dfd5;--hov:#f4f8f4;--acc:#1f9d55;font:15px/1.45 system-ui,-apple-system,"Segoe UI",Roboto,sans-serif;color:var(--ink);background:var(--bg);border:1px solid var(--line);border-radius:8px;overflow:hidden}' +
    '.w.dark{--bg:#141412;--ink:#f3f2ec;--mut:#a5a399;--line:#2b2b27;--hov:#1b211c;--acc:#5fd486}' +
    '@media(prefers-color-scheme:dark){.w.auto{--bg:#141412;--ink:#f3f2ec;--mut:#a5a399;--line:#2b2b27;--hov:#1b211c;--acc:#5fd486}}' +
    '.h{display:flex;justify-content:space-between;align-items:center;gap:12px;padding:13px 16px;border-bottom:1px solid var(--line)}' +
    '.ht{display:flex;align-items:center;gap:9px;font-weight:800;font-size:16px;letter-spacing:-.01em}' +
    '.dot{width:8px;height:8px;border-radius:50%;background:#3ecf5f;flex:none}' +
    '.n,.by{font-size:12.5px;color:var(--mut);white-space:nowrap}' +
    'a{color:inherit;text-decoration:none}' +
    '.r{display:grid;grid-template-columns:auto minmax(0,1fr) auto;gap:2px 12px;align-items:center;padding:11px 16px;border-bottom:1px solid var(--line);position:relative}' +
    '.r:hover{background:var(--hov)}.r:hover::before{content:"";position:absolute;left:0;top:0;bottom:0;width:3px;background:var(--acc)}.r:hover .t{text-decoration:underline;text-decoration-color:var(--acc);text-decoration-thickness:2px;text-underline-offset:3px}' +
    '.lg{grid-row:1/3;width:34px;height:34px;border-radius:6px;border:1px solid var(--line);background:#fff;object-fit:contain;padding:2px}' +
    '.lt{grid-row:1/3;width:34px;height:34px;border-radius:6px;background:var(--hov);display:flex;align-items:center;justify-content:center;font-weight:800;color:var(--mut)}' +
    '.t{grid-column:2;font-weight:650;white-space:nowrap;overflow:hidden;text-overflow:ellipsis}' +
    '.c{grid-column:2;color:var(--mut);font-size:13px;white-space:nowrap;overflow:hidden;text-overflow:ellipsis}' +
    '.m{grid-row:1/3;grid-column:3;text-align:right;font:500 12px ' + MONO + ';color:var(--mut);white-space:nowrap}' +
    '.m b{display:block;color:var(--ink);font-weight:600;font-size:12.5px}' +
    '.e{padding:18px 16px;color:var(--mut)}' +
    '.own .r{grid-template-columns:minmax(0,1fr) auto}.own .lg,.own .lt{display:none}.own .t,.own .c{grid-column:1}.own .m{grid-column:2}' +
    '.f{display:flex;justify-content:space-between;align-items:center;gap:10px;padding:11px 16px;font-size:13px;font-weight:600}' +
    '::slotted(a),.f a{color:var(--ink);text-decoration:underline;text-decoration-color:var(--acc);text-decoration-thickness:2px;text-underline-offset:3px}' +
    /* cards */
    '.cards{display:grid;grid-template-columns:repeat(auto-fill,minmax(210px,1fr));gap:1px;background:var(--line);border-bottom:1px solid var(--line)}' +
    '.cards .r{display:flex;flex-direction:column;align-items:flex-start;gap:6px;background:var(--bg);border:0;padding:14px 16px}' +
    '.cards .r:hover{background:var(--hov)}.cards .t{white-space:normal}.cards .m{text-align:left}' +
    /* compact */
    '.compact .r{grid-template-columns:minmax(0,1fr) auto;padding:8px 14px}.compact .lg,.compact .lt,.compact .c{display:none}.compact .t{grid-column:1;font-size:14px}.compact .m{grid-column:2;grid-row:1}.compact .m b{display:none}' +
    /* ticker */
    '.tick{overflow:hidden;border-bottom:1px solid var(--line);padding:10px 0}' +
    '.tick .run{display:flex;gap:28px;width:max-content;animation:hrn 60s linear infinite}.tick:hover .run{animation-play-state:paused}' +
    '.tick a{display:flex;gap:8px;align-items:baseline;white-space:nowrap;font-size:14px}.tick a b{font-weight:650}.tick a span{color:var(--mut);font-size:13px}' +
    '@keyframes hrn{from{transform:translateX(0)}to{transform:translateX(-50%)}}' +
    '.cs{display:flex;gap:8px;padding:12px 16px;border-bottom:1px solid var(--line);flex-wrap:wrap}' +
    '.cs input,.cs select{font:inherit;font-size:14px;padding:8px 10px;border:1px solid var(--line);border-radius:6px;background:var(--bg);color:var(--ink)}.cs input{flex:1;min-width:150px}' +
    '.more{display:block;width:100%;padding:11px;border:0;border-bottom:1px solid var(--line);background:var(--hov);color:var(--ink);font:inherit;font-weight:600;cursor:pointer}' +
    '@media(prefers-reduced-motion:reduce){.tick .run{animation:none;flex-wrap:wrap;width:auto;padding:0 14px}}';
  function row(j, logos) {
    var mark = j.logo && logos ? '<img class="lg" src="' + esc(j.logo) + '" alt="" loading="lazy">' : '<span class="lt">' + esc((String(j.company).match(/[A-Za-z0-9]/) || ['?'])[0].toUpperCase()) + '</span>';
    return '<a class="r" href="' + esc(j.url) + '" target="_blank" rel="noopener">' + mark + '<span class="t">' + esc(j.title) + '</span>' +
      '<span class="c">' + esc([j.company, j.location || (j.remote ? 'Remote' : '')].filter(Boolean).join(' · ')) + '</span>' +
      '<span class="m">' + (j.salary ? '<b>' + esc(j.salary) + '</b>' : '') + esc(age(j.posted)) + '</span></a>';
  }
  // A company's own board, read in the visitor's browser from the hiring system's public feed. Nothing passes through our site.
  function own(type, raw, el, src) {
    var jobs = [], day = function (v) { return String(v || '').slice(0, 10); };
    if (type === 'greenhouse') (raw.jobs || []).forEach(function (j) {
      jobs.push({ title: j.title, url: j.absolute_url, location: j.location && j.location.name || '', posted: day(j.first_published || j.updated_at), category: '' });
    });
    else if (type === 'lever') (Array.isArray(raw) ? raw : []).forEach(function (j) {
      var c = j.categories || {};
      jobs.push({ title: j.text, url: j.hostedUrl, location: c.location || '', posted: j.createdAt ? day(new Date(j.createdAt).toISOString()) : '', category: c.team || c.department || '' });
    });
    else (raw.jobs || []).forEach(function (j) {
      if (j.isListed === false) return;
      jobs.push({ title: j.title, url: j.jobUrl, location: j.location || '', posted: day(j.publishedAt), category: j.department || j.team || '' });
    });
    jobs = jobs.filter(function (j) { return j.title && /^https:\/\//.test(j.url || ''); });
    jobs.sort(function (a, b) { return a.posted < b.posted ? 1 : a.posted > b.posted ? -1 : 0; });
    var co = el.getAttribute('data-company') || '';
    jobs.forEach(function (j) { j.company = co; });
    var site = (S && S.src ? S.src : '').replace(/\/widget\.js.*$/, '') || src;
    return { name: co ? 'Jobs at ' + co : 'Open roles', total: jobs.length, url: site + '/widgets/', site: 'Hiring Right Now', jobs: jobs, own: true };
  }
  function render(el) {
    if (!el || el.getAttribute('data-hrn-ready')) return;
    el.setAttribute('data-hrn-ready', '1');
    var spec = (el.getAttribute('data-hrn-jobs') || 'latest').split(':'), type = spec[0], slug = spec.slice(1).join(':');
    var path = { latest: 'latest', remote: 'remote', skill: 'skills/' + slug, category: 'categories/' + slug, location: 'locations/' + slug, company: 'companies/' + slug }[type] || 'latest';
    var ats = { greenhouse: 'https://boards-api.greenhouse.io/v1/boards/' + encodeURIComponent(slug) + '/jobs',
                lever: 'https://api.lever.co/v0/postings/' + encodeURIComponent(slug) + '?mode=json',
                ashby: 'https://api.ashbyhq.com/posting-api/job-board/' + encodeURIComponent(slug) }[type];
    var limit = Math.max(1, Math.min(20, parseInt(el.getAttribute('data-limit') || '6', 10) || 6));
    var theme = { light: 'light', dark: 'dark' }[el.getAttribute('data-theme')] || 'auto';
    var layout = { cards: 'cards', compact: 'compact', ticker: 'ticker', careers: 'careers' }[el.getAttribute('data-layout')] || 'list';
    var accent = /^#[0-9a-fA-F]{3,8}$/.test(el.getAttribute('data-accent') || '') ? el.getAttribute('data-accent') : '';
    var src = el.getAttribute('data-hrn-base') || base;
    var interactive = layout === 'careers' || el.getAttribute('data-search') === '1', step = layout === 'careers' ? 20 : limit;
    fetch(ats || src + '/api/v1/' + path + '.json').then(function (r) { return r.json(); }).then(function (d) {
      if (ats) d = own(type, d, el, src);
      var jobs = interactive ? d.jobs : d.jobs.slice(0, limit), body;
      if (!jobs.length) body = '<div class="e">No open roles right now.</div>';
      else if (layout === 'ticker') {
        var items = jobs.map(function (j) { return '<a href="' + esc(j.url) + '" target="_blank" rel="noopener"><b>' + esc(j.title) + '</b><span>' + esc(j.company) + '</span></a>'; }).join('');
        body = '<div class="tick"><div class="run">' + items + items + '</div></div>';
      } else if (interactive) {
        body = '<div class="cs"><input type="search" placeholder="Search ' + jobs.length + ' open roles" aria-label="Search roles"><select aria-label="Team"><option value="">All teams</option></select></div>' +
          '<div class="rows' + (layout === 'compact' ? ' compact' : '') + (d.own ? ' own' : '') + '"></div><button class="more" type="button" hidden>Show more</button>';
      } else body = '<div class="' + (layout === 'list' ? 'rows' : layout) + (d.own ? ' own' : '') + '">' + jobs.map(function (j) { return row(j, layout !== 'compact'); }).join('') + '</div>';
      var root = el.shadowRoot || (el.attachShadow ? el.attachShadow({ mode: 'open' }) : null);
      var html = '<style>' + CSS + '</style><div class="w ' + theme + '"' + (accent ? ' style="--acc:' + accent + '"' : '') + '><div class="h"><span class="ht"><span class="dot"></span>' + esc(el.getAttribute('data-title') || d.name) + '</span>' +
        '<span class="n">' + Number(d.total).toLocaleString('en-US') + ' open</span></div>' + body +
        '<div class="f">' + (root ? '<slot><a href="' + esc(d.url) + '" target="_blank" rel="noopener">' + (d.own ? 'Jobs widget by ' : 'See all on ') + esc(d.site) + '</a></slot>' :
          '<a href="' + esc(d.url) + '" target="_blank" rel="noopener">' + (d.own ? 'Jobs widget by ' : 'See all on ') + esc(d.site) + '</a>') + '<span class="by">' + (d.own ? 'Live from the hiring system' : 'Updated daily') + '</span></div></div>';
      if (root) root.innerHTML = html; else el.innerHTML = html;
      if (interactive && jobs.length && layout !== 'ticker') {     // search by text and team, a page of rows at a time
        var scope = root || el, box = scope.querySelector('.cs input'), team = scope.querySelector('.cs select'), rowsEl = scope.querySelector('.rows'), moreBtn = scope.querySelector('.more'), shown = step;
        var logos = layout === 'list' && !d.own;
        var teams = {}; jobs.forEach(function (j) { if (j.category) teams[j.category] = (teams[j.category] || 0) + 1; });
        team.innerHTML += Object.keys(teams).sort(function (a, b) { return teams[b] - teams[a]; }).map(function (t) { return '<option value="' + esc(t) + '">' + esc(t) + ' (' + teams[t] + ')</option>'; }).join('');
        team.hidden = Object.keys(teams).length < 2;
        var paint = function () {
          var q = box.value.trim().toLowerCase(), list = jobs.filter(function (j) {
            return (!team.value || j.category === team.value) && (!q || (j.title + ' ' + j.location).toLowerCase().indexOf(q) >= 0);
          });
          rowsEl.innerHTML = list.slice(0, shown).map(function (j) { return row(j, logos); }).join('') || '<div class="e">No roles match.</div>';
          moreBtn.hidden = list.length <= shown; moreBtn.textContent = 'Show more (' + (list.length - shown) + ')';
        };
        box.addEventListener('input', function () { shown = step; paint(); });
        team.addEventListener('change', function () { shown = step; paint(); });
        moreBtn.addEventListener('click', function () { shown += step; paint(); });
        paint();
      }
    }).catch(function () {});          // on failure the plain link inside the element stays as it is
  }
  function all() { Array.prototype.forEach.call(document.querySelectorAll('[data-hrn-jobs]'), render); }
  window.HRNWidget = { render: render, all: all };
  if (document.readyState === 'loading') document.addEventListener('DOMContentLoaded', all); else all();
})();
