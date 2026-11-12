(async function () {
  const root = document.getElementById('search');
  if (!root) return;
  const P = root.dataset.base, list = document.getElementById('results'), count = document.getElementById('count'), more = document.getElementById('more');
  const q = document.getElementById('q'), cat = document.getElementById('cat'), fRemote = document.getElementById('f-remote'), fEntry = document.getElementById('f-entry'), fSal = document.getElementById('f-sal');
  const esc = (s) => String(s).replace(/[&<>"]/g, (c) => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;' }[c]));
  const plural = (n) => (n === 1 ? 'job' : 'jobs');
  const params = new URLSearchParams(location.search);
  q.value = params.get('q') || ''; cat.value = params.get('cat') || '';
  fRemote.checked = params.has('remote'); fEntry.checked = params.has('entry'); fSal.checked = params.has('salary');
  let jobs = [];
  try { jobs = await (await fetch(P + '/data/index.json')).json(); }
  catch (e) { count.textContent = 'Could not load the list. Please reload the page.'; return; }
  // row: [slug, title, company, location, remote, cat, level, tags, salary, posted, entry, featured, avatarHue]
  let shown = 100, found = [];
  const card = (j) => {
    const pills = (j[11] ? '<span class="pill acc">Featured</span>' : '') + (j[4] ? '<span class="pill ok">Remote</span>' : '') +
      (j[8] ? '<span class="pill sal">' + esc(j[8].slice(0, 28)) + '</span>' : '') + (j[6] ? '<span class="pill">' + esc(j[6]) + '</span>' : '') +
      j[7].slice(0, 3).map((t) => '<span class="pill">' + esc(t) + '</span>').join('');
    const loc = j[3].length > 60 ? j[3].slice(0, 57) + '…' : j[3];
    const letter = (j[2].match(/[A-Za-z0-9]/) || ['?'])[0].toUpperCase();
    return '<li class="job' + (j[11] ? ' feat' : '') + '"><a href="' + P + '/job/' + j[0] + '/"><span class="ava" style="--h:' + j[12] + '" aria-hidden="true">' + esc(letter) + '</span>' +
      '<span><span class="jt">' + esc(j[1]) + '</span><span class="js">' + esc(j[2]) + (loc ? ' · ' + esc(loc) : '') + '</span></span>' +
      '<span class="jr"><span class="pills">' + pills + '</span><time>' + esc(j[9]) + '</time></span></a></li>';
  };
  const render = () => {
    list.innerHTML = found.slice(0, shown).map(card).join('');
    count.textContent = found.length ? found.length.toLocaleString('en-US') + ' ' + plural(found.length) + ' found' : 'No jobs match. Try removing some filters.';
    more.hidden = found.length <= shown;
  };
  const run = () => {
    const words = q.value.toLowerCase().split(/\s+/).filter(Boolean);
    found = jobs.filter((j) => {
      if (cat.value && j[5] !== cat.value) return false;
      if (fRemote.checked && !j[4]) return false;
      if (fEntry.checked && !j[10]) return false;
      if (fSal.checked && !j[8]) return false;
      if (!words.length) return true;
      const hay = (j[1] + ' ' + j[2] + ' ' + j[3] + ' ' + j[7].join(' ')).toLowerCase();
      return words.every((w) => hay.includes(w));
    });
    shown = 100; render();
  };
  [q, cat, fRemote, fEntry, fSal].forEach((el) => el.addEventListener('input', run));
  more.addEventListener('click', () => { shown += 100; render(); });
  run();
})();
