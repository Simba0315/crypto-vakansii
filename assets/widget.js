/* Hiring Right Now — embeddable jobs widget.
   <div data-hrn-jobs="skill:python" data-limit="6" data-theme="auto"><a href="…">Python jobs on Hiring Right Now</a></div>
   <script src="…/widget.js" async></script>
   The link inside the div stays visible as the widget's footer and works even if scripts are blocked. */
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
  var CSS =
    ':host{all:initial;display:block}' +
    '.w{--bg:#fff;--ink:#0e0e0c;--mut:#5d5b54;--line:#e2dfd5;--hov:#eef9cf;font:15px/1.45 system-ui,-apple-system,"Segoe UI",Roboto,sans-serif;color:var(--ink);background:var(--bg);border:1px solid var(--line);border-radius:12px;overflow:hidden;max-width:680px;box-shadow:5px 5px 0 #c8f560}' +
    '.w.dark{--bg:#141412;--ink:#f3f2ec;--mut:#a5a399;--line:#2b2b27;--hov:#222c0c}' +
    '@media(prefers-color-scheme:dark){.w.auto{--bg:#141412;--ink:#f3f2ec;--mut:#a5a399;--line:#2b2b27;--hov:#222c0c}}' +
    '.h{display:flex;justify-content:space-between;align-items:center;gap:12px;padding:13px 16px;border-bottom:1px solid var(--line)}' +
    '.ht{display:flex;align-items:center;gap:9px;font-weight:800;font-size:16px;letter-spacing:-.01em}' +
    '.dot{width:8px;height:8px;border-radius:50%;background:#3ecf5f;flex:none}' +
    '.n{font:500 11.5px ui-monospace,"SF Mono",Menlo,Consolas,monospace;letter-spacing:.05em;text-transform:uppercase;color:var(--mut);white-space:nowrap}' +
    '.r{display:grid;grid-template-columns:minmax(0,1fr) auto;gap:4px 14px;align-items:center;padding:11px 16px;border-bottom:1px solid var(--line);color:inherit;text-decoration:none;position:relative}' +
    '.r:hover{background:var(--hov)}.r:hover::before{content:"";position:absolute;left:0;top:0;bottom:0;width:4px;background:#c8f560}' +
    '.t{font-weight:650;white-space:nowrap;overflow:hidden;text-overflow:ellipsis}' +
    '.c{grid-column:1;color:var(--mut);font-size:13px;white-space:nowrap;overflow:hidden;text-overflow:ellipsis}' +
    '.m{grid-row:1/3;grid-column:2;text-align:right;font:500 11.5px ui-monospace,"SF Mono",Menlo,Consolas,monospace;letter-spacing:.04em;text-transform:uppercase;color:var(--mut);white-space:nowrap}' +
    '.m b{display:block;color:var(--ink);font-weight:500;text-transform:none;letter-spacing:0;font-size:12.5px}' +
    '.e{padding:18px 16px;color:var(--mut)}' +
    '.f{display:flex;justify-content:space-between;align-items:center;gap:10px;padding:11px 16px;font-size:13px;font-weight:600}' +
    '::slotted(a),.f a{color:var(--ink);text-decoration:underline;text-decoration-color:#c8f560;text-decoration-thickness:2px;text-underline-offset:3px}' +
    '.by{font:500 11px ui-monospace,"SF Mono",Menlo,Consolas,monospace;letter-spacing:.05em;text-transform:uppercase;color:var(--mut);white-space:nowrap}';
  function render(el) {
    if (!el || el.getAttribute('data-hrn-ready')) return;
    el.setAttribute('data-hrn-ready', '1');
    var spec = (el.getAttribute('data-hrn-jobs') || 'latest').split(':'), type = spec[0], slug = spec.slice(1).join(':');
    var path = { latest: 'latest', remote: 'remote', skill: 'skills/' + slug, category: 'categories/' + slug, location: 'locations/' + slug, company: 'companies/' + slug }[type] || 'latest';
    var limit = Math.max(1, Math.min(20, parseInt(el.getAttribute('data-limit') || '6', 10) || 6));
    var theme = { light: 'light', dark: 'dark' }[el.getAttribute('data-theme')] || 'auto';
    var src = el.getAttribute('data-hrn-base') || base;
    fetch(src + '/api/v1/' + path + '.json').then(function (r) { return r.json(); }).then(function (d) {
      var rows = d.jobs.slice(0, limit).map(function (j) {
        return '<a class="r" href="' + esc(j.url) + '" target="_blank" rel="noopener"><span class="t">' + esc(j.title) + '</span>' +
          '<span class="c">' + esc(j.company) + (j.location ? ' · ' + esc(j.location) : j.remote ? ' · Remote' : '') + '</span>' +
          '<span class="m">' + (j.salary ? '<b>' + esc(j.salary) + '</b>' : '') + esc(age(j.posted)) + '</span></a>';
      }).join('');
      var root = el.shadowRoot || (el.attachShadow ? el.attachShadow({ mode: 'open' }) : null);
      var html = '<style>' + CSS + '</style><div class="w ' + theme + '"><div class="h"><span class="ht"><span class="dot"></span>' + esc(el.getAttribute('data-title') || d.name) + '</span>' +
        '<span class="n">' + Number(d.total).toLocaleString('en-US') + ' open</span></div>' + (rows || '<div class="e">No open roles right now.</div>') +
        '<div class="f">' + (root ? '<slot><a href="' + esc(d.url) + '" target="_blank" rel="noopener">See all on ' + esc(d.site) + '</a></slot>' :
          '<a href="' + esc(d.url) + '" target="_blank" rel="noopener">See all on ' + esc(d.site) + '</a>') + '<span class="by">Updated daily</span></div></div>';
      if (root) root.innerHTML = html; else el.innerHTML = html;
    }).catch(function () {});          // on failure the plain link inside the element stays as it is
  }
  function all() { Array.prototype.forEach.call(document.querySelectorAll('[data-hrn-jobs]'), render); }
  window.HRNWidget = { render: render, all: all };
  if (document.readyState === 'loading') document.addEventListener('DOMContentLoaded', all); else all();
})();
