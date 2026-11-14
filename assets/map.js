/* The jobs map (/map/): a dot per city, sized by its open jobs; a search word recounts the dots in the browser.
   Map drawing: MapLibre GL with the free OpenFreeMap base map. Jobs: the same index the search page uses (window.HRN from site.js).
   data/map.json: c = [[key, name, country code, lat, lng, address of its list]], n = open jobs per city, ix = city number of each index row (-1: not placed).
   The dots are drawn from n at once; the full job index (a few MB) is loaded after, for search and for the list of a city. */
(function () {
  var box = document.getElementById('jobmap'), H = window.HRN;
  if (!box || !H) return;
  var P = H.base, esc = H.esc, $ = function (id) { return document.getElementById(id); };
  var panel = $('mappanel'), form = $('mapform'), input = $('mapq'), note = $('mapnote');
  var num = function (x) { return Number(x).toLocaleString('en-US'); };
  function flag(cc) { return cc && cc.length === 2 ? '<i class="fl">' + String.fromCodePoint(0x1F1E6 + cc.charCodeAt(0) - 65, 0x1F1E6 + cc.charCodeAt(1) - 65) + '</i>' : ''; }
  function fail() { box.classList.add('off'); if (note) note.textContent = 'The map could not load here. Every city is listed below.'; }
  if (!window.maplibregl) { fail(); return; }
  if (note) note.textContent = 'Loading the map…';

  var M, rows, counts = [], picked = -1, f = H.parse('');
  var map = new maplibregl.Map({ container: box, style: 'https://tiles.openfreemap.org/styles/positron', center: [-40, 30], zoom: 1.3,
    minZoom: 1, maxZoom: 11, attributionControl: { compact: true }, cooperativeGestures: matchMedia('(pointer: coarse)').matches });
  map.addControl(new maplibregl.NavigationControl({ showCompass: false }), 'top-right');
  map.on('error', function (ev) { if (ev && ev.error && /style|Failed to fetch/i.test(String(ev.error.message || ''))) fail(); });

  function recount() {
    if (!rows) { counts = M.n.slice(); return counts.reduce(function (a, b) { return a + b; }, 0); }
    counts = M.c.map(function () { return 0; });
    var on = 0;
    for (var i = 0; i < rows.length; i++) { var c = M.ix[i]; if (c >= 0 && H.match(rows[i], f)) { counts[c]++; on++; } }
    return on;
  }
  function geo() {
    return { type: 'FeatureCollection', features: M.c.map(function (c, i) {
      return counts[i] ? { type: 'Feature', id: i, properties: { i: i, n: counts[i] }, geometry: { type: 'Point', coordinates: [c[4], c[3]] } } : null;
    }).filter(Boolean) };
  }
  function show(i) {
    picked = i;
    if (!rows) { panel.innerHTML = '<p class="note">Loading the jobs…</p>'; panel.hidden = false; ready.then(function () { show(i); }); return; }
    var c = M.c[i], list = [];
    for (var k = 0; k < rows.length && list.length < 20; k++) if (M.ix[k] === i && H.match(rows[k], f)) list.push(rows[k]);
    var q = input.value.trim(), all = q ? P + '/jobs/?q=' + encodeURIComponent(q + ' ' + c[1]) : P + '/' + c[5];
    panel.innerHTML = '<div class="mp-head"><h2>' + flag(c[2]) + esc(c[1]) + '</h2><span class="pill">' + num(counts[i]) + (q ? ' match' : ' open') + '</span></div>' +
      '<ul class="jobs">' + list.map(function (j) { return H.card(j); }).join('') + '</ul>' +
      (counts[i] > list.length ? '<p><a class="btn ghost sm" href="' + all + '">All ' + num(counts[i]) + ' in ' + esc(c[1]) + '</a></p>' : '') +
      '<div class="mp-help"><p><b>Applying to these?</b> Check your resume against one of the postings first: it shows which of its words your resume is missing.</p>' +
      '<p><a class="btn primary sm" href="' + P + '/tools/resume-match/">Check my resume</a> <a class="btn ghost sm" href="' + P + '/resume/">Build a resume</a></p></div>';
    if (H.decorate) try { H.decorate(panel); } catch (e) {}
    panel.hidden = false;
  }
  function draw(fit) {
    var on = recount(), src = map.getSource('jobs');
    if (src) src.setData(geo());
    var cities = counts.filter(Boolean).length;
    note.textContent = num(on) + ' jobs in ' + cities + ' cities' + (input.value.trim() ? ' match “' + input.value.trim() + '”' : '') + '. Remote jobs that name no city are in the search.';
    if (fit && cities) {
      var b = new maplibregl.LngLatBounds();
      counts.forEach(function (n, i) { if (n) b.extend([M.c[i][4], M.c[i][3]]); });
      map.fitBounds(b, { padding: 50, maxZoom: 8, duration: 600 });
    }
    if (picked >= 0) { if (counts[picked]) show(picked); else panel.hidden = true; }
  }
  var ready = H.load().then(function (r) { rows = r; });
  // the dots go on as soon as the map style is in (style.load), not after every base-map tile (load)
  Promise.all([fetch(P + '/data/map.json').then(function (r) { return r.json(); }), new Promise(function (ok) { if (map.isStyleLoaded()) ok(); else map.once('style.load', ok); })]).then(function (got) {
    M = got[0];
    var q0 = new URLSearchParams(location.search).get('q') || '';
    if (q0) { input.value = q0; f = H.parse('q=' + encodeURIComponent(q0)); }
    recount();
    map.addSource('jobs', { type: 'geojson', data: geo() });
    map.addLayer({ id: 'jobs', type: 'circle', source: 'jobs', paint: {
      'circle-radius': ['interpolate', ['linear'], ['sqrt', ['get', 'n']], 1, 4, 10, 10, 70, 30],
      'circle-color': '#12a150', 'circle-opacity': 0.72, 'circle-stroke-color': '#ffffff', 'circle-stroke-width': 1.5 } });
    var tip = new maplibregl.Popup({ closeButton: false, closeOnClick: false, offset: 10 });
    map.on('mouseenter', 'jobs', function (ev) {
      map.getCanvas().style.cursor = 'pointer';
      var p = ev.features[0].properties, c = M.c[p.i];
      tip.setLngLat([c[4], c[3]]).setHTML('<b>' + esc(c[1]) + '</b><br>' + num(p.n) + ' jobs').addTo(map);
    });
    map.on('mouseleave', 'jobs', function () { map.getCanvas().style.cursor = ''; tip.remove(); });
    map.on('click', 'jobs', function (ev) { show(ev.features[0].properties.i); panel.scrollIntoView({ behavior: 'smooth', block: 'nearest' }); });
    draw(false);
    if (q0) ready.then(function () { draw(true); });
  }).catch(fail);
  form.addEventListener('submit', function (ev) {
    ev.preventDefault();
    if (!M) return;
    var q = input.value.trim();
    f = H.parse(q ? 'q=' + encodeURIComponent(q) : '');
    try { history.replaceState(null, '', q ? '?q=' + encodeURIComponent(q) : location.pathname); } catch (e) {}
    if (rows) draw(true); else { note.textContent = 'Counting…'; ready.then(function () { draw(true); }); }
  });
  document.addEventListener('click', function (ev) {
    var a = ev.target.closest ? ev.target.closest('[data-city]') : null;
    if (!a || !M) return;
    var i = Number(a.getAttribute('data-city'));
    if (!counts[i]) return;
    ev.preventDefault();
    map.flyTo({ center: [M.c[i][4], M.c[i][3]], zoom: 8, duration: 700 });
    show(i); box.scrollIntoView({ behavior: 'smooth', block: 'start' });
  });
})();
