/* Saved jobs and recently viewed, stored in the visitor's browser (no account). */
(function () {
  var P = document.documentElement.getAttribute('data-base') || '';
  function get(k) { try { return JSON.parse(localStorage.getItem(k) || '[]'); } catch (e) { return []; } }
  function set(k, v) { try { localStorage.setItem(k, JSON.stringify(v)); } catch (e) {} }
  function esc(s) { return String(s).replace(/[&<>"]/g, function (c) { return { '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;' }[c]; }); }
  var saved = get('hrn_saved');
  var badge = document.getElementById('saved-n');
  function paint() { if (badge) badge.textContent = saved.length ? saved.length : ''; }
  paint();

  var b = document.getElementById('save');
  if (b) {
    var job = { s: b.getAttribute('data-slug'), t: b.getAttribute('data-title'), c: b.getAttribute('data-company') };
    var has = function () { return saved.some(function (x) { return x.s === job.s; }); };
    var label = function () { b.textContent = has() ? 'Saved ✓' : 'Save job'; b.setAttribute('aria-pressed', has() ? 'true' : 'false'); };
    label();
    b.addEventListener('click', function () {
      saved = has() ? saved.filter(function (x) { return x.s !== job.s; }) : [job].concat(saved).slice(0, 200);
      set('hrn_saved', saved); label(); paint();
    });
    var seen = get('hrn_seen').filter(function (x) { return x.s !== job.s; });
    seen.unshift(job); set('hrn_seen', seen.slice(0, 30));
  }

  var root = document.getElementById('saved-root');
  if (root) {
    var row = function (j, removable) {
      var letter = (String(j.c).match(/[A-Za-z0-9]/) || ['?'])[0].toUpperCase();
      return '<li class="job"><a href="' + P + '/job/' + encodeURIComponent(j.s) + '/"><span class="ava" aria-hidden="true">' + esc(letter) + '</span>' +
        '<span><span class="jt">' + esc(j.t) + '</span><span class="js">' + esc(j.c) + '</span></span>' +
        (removable ? '<span class="jr"><button class="unsave" type="button" data-s="' + esc(j.s) + '">Remove</button></span>' : '') + '</a></li>';
    };
    var draw = function () {
      var seen = get('hrn_seen');
      document.getElementById('saved-list').innerHTML = saved.map(function (j) { return row(j, true); }).join('');
      document.getElementById('saved-empty').hidden = saved.length > 0;
      document.getElementById('seen-list').innerHTML = seen.map(function (j) { return row(j, false); }).join('');
      document.getElementById('seen-empty').hidden = seen.length > 0;
    };
    root.addEventListener('click', function (ev) {
      var t = ev.target;
      if (t && t.classList && t.classList.contains('unsave')) {
        ev.preventDefault();
        saved = saved.filter(function (x) { return x.s !== t.getAttribute('data-s'); });
        set('hrn_saved', saved); paint(); draw();
      }
    });
    draw();
  }
})();
