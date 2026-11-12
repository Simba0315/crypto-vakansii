/* Jobs widget: <script src=".../embed.js" data-company="company-slug" async></script> */
(function () {
  var s = document.currentScript;
  if (!s) return;
  var slug = s.getAttribute('data-company');
  if (!slug) return;
  var base = s.src.replace(/\/embed\.js.*$/, '');
  var max = parseInt(s.getAttribute('data-limit') || '8', 10) || 8;
  var host = document.createElement('div');
  s.parentNode.insertBefore(host, s);
  var root = host.attachShadow ? host.attachShadow({ mode: 'open' }) : host;
  var esc = function (v) { return String(v == null ? '' : v).replace(/[&<>"]/g, function (c) { return { '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;' }[c]; }); };
  fetch(base + '/data/companies/' + encodeURIComponent(slug) + '.json').then(function (r) { return r.json(); }).then(function (d) {
    var rows = d.jobs.slice(0, max).map(function (j) {
      return '<a class="r" href="' + esc(j.url) + '" target="_blank" rel="noopener"><span class="t">' + esc(j.title) + '</span><span class="l">' + esc(j.location || (j.remote ? 'Remote' : '')) + '</span></a>';
    }).join('');
    root.innerHTML = '<style>' +
      '.w{font:15px/1.5 system-ui,-apple-system,"Segoe UI",Roboto,sans-serif;color:#0b0d12;background:#fff;border:1px solid #e7e9ee;border-radius:14px;overflow:hidden;max-width:640px}' +
      '.h{font-weight:700;padding:14px 16px;border-bottom:1px solid #e7e9ee}' +
      '.r{display:flex;justify-content:space-between;gap:16px;padding:12px 16px;border-bottom:1px solid #f0f1f4;color:inherit;text-decoration:none}' +
      '.r:hover{background:#f5f6f8}.t{font-weight:600}.l{color:#566072;font-size:13px;text-align:right;max-width:45%;overflow:hidden;text-overflow:ellipsis;white-space:nowrap}' +
      '.e{padding:16px;color:#566072}.f{display:block;padding:12px 16px;font-size:13px;font-weight:600;color:#4f46e5;text-decoration:none}.f:hover{text-decoration:underline}' +
      '@media(prefers-color-scheme:dark){.w{color:#eceef3;background:#12141b;border-color:#20242e}.h,.r{border-color:#20242e}.r:hover{background:#181b24}.l,.e{color:#9aa3b3}.f{color:#8b83ff}}' +
      '</style><div class="w"><div class="h">Open roles at ' + esc(d.company) + '</div>' + (rows || '<div class="e">No open roles right now.</div>') +
      '<a class="f" href="' + esc(d.page) + '" target="_blank" rel="noopener">See all ' + esc(d.total) + ' jobs on ' + esc(d.site) + ' →</a></div>';
  }).catch(function () {});
})();
