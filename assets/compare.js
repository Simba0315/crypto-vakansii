/* /vs/compare/: pick up to five job sites (and this one) and see the same sourced facts side by side.
   The data is in the page (#cmp-data, built from compare_sites.py); the choice lives in the address (?sites=a,b,jobseveryhour) so a
   table can be shared. The page already holds the default table, so without this script it still reads. No dialogs (the built-in
   browser pane of the desktop app suppresses them): the copy button answers in the line beside it. */
(function () {
  "use strict";
  var el = document.getElementById("cmp-data"), pick = document.getElementById("cmp-pick"), out = document.getElementById("cmp-out");
  if (!el || !pick || !out) return;
  var D;
  try { D = JSON.parse(el.textContent); } catch (err) { return; }
  var by = {}, i;
  for (i = 0; i < D.sites.length; i++) by[D.sites[i].s] = D.sites[i];
  var boxes = pick.querySelectorAll('input[name="site"]'), msg = document.getElementById("cmp-msg");
  var esc = function (t) { return String(t).replace(/[&<>"]/g, function (c) { return { "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;" }[c]; }); };

  function fromUrl() {
    var m = /[?&]sites=([^&#]*)/.exec(location.search), list = [], seen = {}, others = 0;
    if (!m) return null;
    var raw = decodeURIComponent(m[1].replace(/\+/g, " ")).split(/[,\s]+/);
    for (var k = 0; k < raw.length; k++) {
      var s = raw[k].toLowerCase();
      if (!by[s] || seen[s]) continue;
      if (s !== D.us) { if (others >= D.max) continue; others++; }
      seen[s] = 1; list.push(s);
    }
    return list;
  }
  function chosen() {
    var list = [], us = false;
    for (var k = 0; k < boxes.length; k++) if (boxes[k].checked) { if (boxes[k].value === D.us) us = true; else list.push(boxes[k].value); }
    if (us) list.push(D.us);
    return list;
  }
  function cell(c, row) {
    if (row === "What it is") return esc(c.w);
    if (row === "Sources") {
      if (c.us) return "This site, " + esc(D.today) + '. <a href="' + esc(c.u) + '">About it</a>';
      var a = [];
      for (var k = 0; k < c.src.length; k++) a.push('<a href="' + esc(c.src[k][0]) + '" rel="nofollow noopener">' + esc(c.src[k][2]) + "</a>");
      return a.join(" · ") + '<br><span class="src">Read ' + (c.src.length ? esc(c.src[0][1]) : "") + '</span> · <a href="' + esc(c.u) + '">Full comparison</a>';
    }
    var t = c.r[row];
    return t ? esc(t) : '<span class="miss">' + esc(D.miss) + "</span>";
  }
  function draw(list) {
    if (!list.length) {
      out.innerHTML = '<p class="cmp-empty">Pick at least one job site above to see its facts here.</p>';
      return;
    }
    var cols = list.map(function (s) { return by[s]; });
    var h = '<table class="vs-t cmp-t"><tr><th scope="col"><span class="sr-only">Question</span></th>';
    cols.forEach(function (c) { h += '<th scope="col"' + (c.us ? ' class="us"' : "") + ">" + esc(c.n) + "</th>"; });
    h += "</tr>";
    D.rows.forEach(function (row) {
      h += '<tr><th scope="row">' + esc(row) + "</th>";
      cols.forEach(function (c) { h += '<td data-l="' + esc(c.n) + '"' + (c.us ? ' class="us"' : "") + ">" + cell(c, row) + "</td>"; });
      h += "</tr>";
    });
    out.innerHTML = h + "</table>";
  }
  function sync(list, push) {
    var others = 0, k;
    for (k = 0; k < boxes.length; k++) boxes[k].checked = list.indexOf(boxes[k].value) >= 0;
    for (k = 0; k < list.length; k++) if (list[k] !== D.us) others++;
    for (k = 0; k < boxes.length; k++) if (boxes[k].value !== D.us) boxes[k].disabled = !boxes[k].checked && others >= D.max;
    msg.textContent = others >= D.max ? "That is " + D.max + " sites, the most at a time: take one out to add another."
      : others === 0 ? "Pick the job sites to compare." : "Sites in the table: " + list.map(function (s) { return by[s].n; }).join(", ") + ".";
    draw(list);
    if (push !== false && window.history && history.replaceState) {
      var q = list.length ? "?sites=" + list.join(",") : location.pathname;
      history.replaceState(null, "", list.length ? location.pathname + q + location.hash : q + location.hash);
    }
  }
  pick.addEventListener("change", function () { sync(chosen()); });
  document.getElementById("cmp-clear").addEventListener("click", function () {
    for (var k = 0; k < boxes.length; k++) boxes[k].checked = false;
    sync([]);
  });
  document.getElementById("cmp-copy").addEventListener("click", function () {
    var url = location.href, done = function (ok) { msg.textContent = ok ? "Link copied: " + url : "Copy this link: " + url; };
    if (navigator.clipboard && navigator.clipboard.writeText) navigator.clipboard.writeText(url).then(function () { done(true); }, function () { done(false); });
    else done(false);
  });
  var start = fromUrl();
  sync(start === null ? D.def : start, start !== null);
})();
