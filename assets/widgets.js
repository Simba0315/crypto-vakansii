/* Builder on the /widgets/ page: pick what to show, see it live, copy the code. */
(function () {
  var root = document.getElementById('wb'); if (!root) return;
  var D = JSON.parse(document.getElementById('wb-data').textContent), FULL = root.getAttribute('data-full');
  var $ = function (id) { return document.getElementById(id); };
  var type = $('wb-type'), val = $('wb-val'), limit = $('wb-limit'), theme = $('wb-theme'), layout = $('wb-layout'), accent = $('wb-accent'), mode = $('wb-mode');
  var fill = function () {
    var list = { skill: D.skills, category: D.categories, location: D.locations, company: D.companies }[type.value];
    val.innerHTML = list ? list.map(function (x) { return '<option value="' + x[0] + '">' + x[1].replace(/&/g, '&amp;').replace(/</g, '&lt;') + '</option>'; }).join('') : '';
    val.parentNode.hidden = !list;
  };
  var nameOf = function () { var o = val.options[val.selectedIndex]; return o ? o.text : ''; };
  var copy = function (btn, text) {
    var done = function () { var t = btn.textContent; btn.textContent = 'Copied ✓'; setTimeout(function () { btn.textContent = t; }, 1500); };
    if (navigator.clipboard) navigator.clipboard.writeText(text).then(done, function () {}); else done();
  };
  var run = function () {
    var t = type.value, slug = val.value, spec = t === 'latest' || t === 'remote' ? t : t + ':' + slug;
    var page = { latest: 'jobs/', remote: 'remote/', skill: 'skills/' + slug + '/', category: 'jobs/' + slug + '/', location: 'locations/' + slug + '/', company: 'companies/' + slug + '/' }[t];
    var label = { latest: 'Tech jobs', remote: 'Remote tech jobs', skill: nameOf() + ' jobs', category: nameOf() + ' jobs', location: 'Tech jobs in ' + nameOf(), company: 'Jobs at ' + nameOf() }[t];
    var link = '<a href="' + FULL + '/' + page + '">' + label.replace(/&/g, '&amp;') + ' on ' + D.site + '</a>';
    var acc = accent.value && accent.value.toLowerCase() !== '#c8f560' ? accent.value : '';
    var attrs = ' data-limit="' + limit.value + '"' + (layout.value !== 'list' ? ' data-layout="' + layout.value + '"' : '') + (theme.value !== 'auto' ? ' data-theme="' + theme.value + '"' : '') + (acc ? ' data-accent="' + acc + '"' : '');
    var q = 'jobs=' + encodeURIComponent(spec) + '&limit=' + limit.value + (layout.value !== 'list' ? '&layout=' + layout.value : '') + (theme.value !== 'auto' ? '&theme=' + theme.value : '') + (acc ? '&accent=' + encodeURIComponent(acc) : '');
    var rowsH = layout.value === 'careers' ? 1300 : layout.value === 'ticker' ? 150 : layout.value === 'cards' ? 150 + Math.ceil(limit.value / 3) * 120 : 120 + limit.value * (layout.value === 'compact' ? 38 : 58);
    var code = mode.value === 'iframe'
      ? '<iframe src="' + FULL + '/embed/?' + q + '" title="' + label.replace(/"/g, '') + '" loading="lazy" style="width:100%;max-width:720px;height:' + rowsH + 'px;border:0"></iframe>\n<p><a href="' + FULL + '/' + page + '">' + label.replace(/&/g, '&amp;') + ' on ' + D.site + '</a></p>'
      : '<div data-hrn-jobs="' + spec + '"' + attrs + '>' + link + '</div>\n<script src="' + FULL + '/widget.js" async><\/script>';
    $('wb-code').value = code;
    var prev = $('wb-preview'); prev.innerHTML = '';
    var el = document.createElement('div');
    el.setAttribute('data-hrn-jobs', spec); el.setAttribute('data-limit', limit.value); el.setAttribute('data-theme', theme.value);
    el.setAttribute('data-layout', layout.value); if (acc) el.setAttribute('data-accent', acc);
    el.setAttribute('data-hrn-base', root.getAttribute('data-base')); el.innerHTML = link;
    prev.appendChild(el); if (window.HRNWidget) window.HRNWidget.render(el);
    var badge = { latest: 'badge/jobs.svg', remote: 'badge/remote.svg', skill: 'badge/skills/' + slug + '.svg', category: 'badge/categories/' + slug + '.svg', location: 'badge/locations/' + slug + '.svg', company: 'badge/companies/' + slug + '.svg' }[t];
    $('wb-badge').src = root.getAttribute('data-base') + '/' + badge;
    $('wb-badge-html').value = '<a href="' + FULL + '/' + page + '"><img src="' + FULL + '/' + badge + '" alt="' + label.replace(/"/g, '') + ' on ' + D.site + '" height="28"></a>';
    $('wb-badge-md').value = '[![' + label + ' on ' + D.site + '](' + FULL + '/' + badge + ')](' + FULL + '/' + page + ')';
  };
  type.addEventListener('change', function () { fill(); run(); });
  [val, limit, theme, layout, accent, mode].forEach(function (el) { el.addEventListener('change', run); });
  accent.addEventListener('input', run);
  root.addEventListener('click', function (ev) {
    var b = ev.target.closest('[data-copy]'); if (b) copy(b, $(b.getAttribute('data-copy')).value);
  });
  fill(); run();
})();
