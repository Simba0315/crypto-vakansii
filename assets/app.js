(async function () {
  const root = document.getElementById('search');
  if (!root) return;
  const P = root.dataset.base, list = document.getElementById('results'), count = document.getElementById('count'), more = document.getElementById('more');
  const q = document.getElementById('q'), cat = document.getElementById('cat'), fRemote = document.getElementById('f-remote'), fSng = document.getElementById('f-sng'), fSal = document.getElementById('f-sal');
  const esc = (s) => String(s).replace(/[&<>"]/g, (c) => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;' }[c]));
  const plural = (n) => { const a = n % 10, b = n % 100; return a === 1 && b !== 11 ? 'вакансия' : a >= 2 && a <= 4 && (b < 12 || b > 14) ? 'вакансии' : 'вакансий'; };
  const params = new URLSearchParams(location.search);
  q.value = params.get('q') || ''; cat.value = params.get('cat') || '';
  fRemote.checked = params.has('remote'); fSng.checked = params.has('sng'); fSal.checked = params.has('salary');
  let jobs = [];
  try { jobs = await (await fetch(P + '/data/index.json')).json(); }
  catch (e) { count.textContent = 'Не удалось загрузить список. Обновите страницу.'; return; }
  // row: [slug, title, company, location, remote, cat, level, tags, salary, posted, sng, featured]
  let shown = 100, found = [];
  const card = (j) => '<li class="job' + (j[11] ? ' feat' : '') + '"><a class="t" href="' + P + '/vakansiya/' + j[0] + '/">' + esc(j[1]) + '</a>' +
    '<div class="m">' + esc(j[2]) + (j[3] ? ' · ' + esc(j[3]) : '') + '</div><div class="b">' +
    (j[11] ? '<span class="tag acc">Выделено</span>' : '') + (j[4] ? '<span class="tag ok">Удалённо</span>' : '') +
    (j[8] ? '<span class="tag warn">' + esc(j[8]) + '</span>' : '') + (j[6] ? '<span class="tag">' + esc(j[6]) + '</span>' : '') +
    j[7].map((t) => '<span class="tag">' + esc(t) + '</span>').join('') + '<time>' + esc(j[9]) + '</time></div></li>';
  const render = () => {
    list.innerHTML = found.slice(0, shown).map(card).join('');
    count.textContent = found.length ? 'Найдено: ' + found.length + ' ' + plural(found.length) : 'Ничего не найдено. Попробуйте убрать часть фильтров.';
    more.hidden = found.length <= shown;
  };
  const run = () => {
    const words = q.value.toLowerCase().split(/\s+/).filter(Boolean);
    found = jobs.filter((j) => {
      if (cat.value && j[5] !== cat.value) return false;
      if (fRemote.checked && !j[4]) return false;
      if (fSng.checked && !j[10]) return false;
      if (fSal.checked && !j[8]) return false;
      if (!words.length) return true;
      const hay = (j[1] + ' ' + j[2] + ' ' + j[3] + ' ' + j[7].join(' ')).toLowerCase();
      return words.every((w) => hay.includes(w));
    });
    shown = 100; render();
  };
  [q, cat, fRemote, fSng, fSal].forEach((el) => el.addEventListener('input', run));
  more.addEventListener('click', () => { shown += 100; render(); });
  run();
})();
