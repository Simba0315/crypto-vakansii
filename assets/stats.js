/* The owner's statistics page (/stats/), in Russian like the moderator's page. It reads GET /api/admin/stats (server/src/worker.js,
   statsReport) with ?key=<STATS_KEY> from the page address, or with the session of the owner's own account. Opening it leaves this
   browser out of the statistics (localStorage hrn_nostats, read by the visit counter at the end of site.js). Not linked from the
   public pages, not in the sitemap, noindex. */
(function () {
  var root = document.getElementById('st');
  if (!root) return;
  try { localStorage.setItem('hrn_nostats', '1'); } catch (e) {}
  var API = (root.getAttribute('data-api') || '').replace(/\/+$/, ''), SITE = root.getAttribute('data-site') || '';
  var key = new URLSearchParams(location.search).get('key') || '', token = '';
  try { token = JSON.parse(localStorage.getItem('hrn_token')) || ''; } catch (e) {}
  var esc = function (s) { return String(s == null ? '' : s).replace(/[&<>"']/g, function (c) { return { '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' }[c]; }); };
  var num = function (n) { return Number(n || 0).toLocaleString('ru-RU'); };
  var pct = function (a, b) { return b ? (Math.round(a / b * 1000) / 10).toLocaleString('ru-RU') + '%' : '—'; };
  var region = null; try { region = new Intl.DisplayNames(['ru'], { type: 'region' }); } catch (e) {}
  var iso = function (d) { return d.toISOString().slice(0, 10); };
  var DAY = 864e5, today = new Date(), sel = 7;
  var PERIODS = [['Сегодня', 0, 0], ['Вчера', 1, 1], ['7 дней', 6, 0], ['30 дней', 29, 0], ['90 дней', 89, 0], ['Год', 364, 0]];

  function load(i) {
    sel = i;
    var p = PERIODS[i], from = iso(new Date(today - p[1] * DAY)), to = iso(new Date(today - p[2] * DAY));
    var url = API + '/api/admin/stats?from=' + from + '&to=' + to + (key ? '&key=' + encodeURIComponent(key) : '');
    root.querySelector('.st-body').innerHTML = '<p class="st-muted">Загружаю…</p>';
    fetch(url, { headers: token && !key ? { Authorization: 'Bearer ' + token } : {} }).then(function (r) {
      if (r.status === 403 || r.status === 401) throw new Error('auth');
      if (!r.ok) throw new Error('server');
      return r.json();
    }).then(draw, function (e) {
      root.querySelector('.st-body').innerHTML = e.message === 'auth'
        ? '<div class="banner">Эта страница открывается по ссылке с ключом (её печатает установка сервера: <code>statistics: …/stats/?key=…</code>) или под вашим аккаунтом владельца.</div><p><a class="btn primary" href="' + esc(SITE) + '/account/">Войти в аккаунт</a></p>'
        : '<div class="banner">Сервер не ответил. Обновите страницу через минуту.</div>';
    });
  }

  function table(title, note, rows, total, opt) {
    opt = opt || {};
    var head = '<div class="st-card"><h3>' + esc(title) + (total != null ? ' <span class="st-muted">' + num(total) + '</span>' : '') + '</h3>' + (note ? '<p class="st-muted">' + note + '</p>' : '');
    if (!rows || !rows.length) return head + '<p class="st-muted">Пока нет данных.</p></div>';
    var sum = total || rows.reduce(function (s, r) { return s + r.n; }, 0), cut = opt.all ? rows.length : 30;
    var body = rows.map(function (r, i) {
      var label = opt.country ? (r.k === '—' ? 'неизвестно' : esc(r.k) + (region ? ' <span class="st-muted">' + esc(region.of(r.k) || '') + '</span>' : '')) : esc(r.k);
      var cells = '<td>' + num(r.n) + '</td><td>' + pct(r.n, sum) + '</td>' + (opt.clicks ? '<td>' + (r.c ? num(r.c) : '—') + '</td><td>' + (r.c ? pct(r.c, r.n) : '—') + '</td>' : '');
      return '<tr' + (i >= cut ? ' class="st-more" hidden' : '') + '><td class="st-k"><span class="st-bar" style="width:' + Math.max(1, Math.round(r.n / rows[0].n * 100)) + '%"></span><span>' + label + '</span></td>' + cells + '</tr>';
    }).join('');
    var th = '<tr><th>' + esc(opt.col || '') + '</th><th>' + esc(opt.ncol || 'Визиты') + '</th><th>Доля</th>' + (opt.clicks ? '<th>' + esc(opt.ccol || 'Клики Apply') + '</th><th>Конверсия</th>' : '') + '</tr>';
    return head + '<div class="st-tw"><table class="st-t">' + th + body + '</table></div>' + (rows.length > cut ? '<button type="button" class="btn ghost sm st-all">и ещё ' + (rows.length - cut) + '</button>' : '') + '</div>';
  }

  function days(d) {
    var by = {}; (d.by_day || []).forEach(function (r) { by[r.k] = r.n; });
    var list = [], t = new Date(d.from + 'T00:00:00Z'), end = new Date(d.to + 'T00:00:00Z');
    for (; t <= end; t = new Date(+t + DAY)) list.push([iso(t), by[iso(t)] || 0]);
    var max = Math.max.apply(null, list.map(function (x) { return x[1]; }).concat([1]));
    return '<div class="st-card"><h3>Визиты по дням</h3><div class="st-days">' + list.map(function (x) {
      return '<span title="' + x[0] + ': ' + num(x[1]) + '" style="height:' + Math.max(2, Math.round(x[1] / max * 100)) + '%"></span>';
    }).join('') + '</div><p class="st-muted">' + esc(d.from) + ' — ' + esc(d.to) + '</p></div>';
  }

  function draw(d) {
    var T = d.totals || {}, v = T.visits || 0;
    var tiles = [['Визиты', num(v)], ['Просмотры страниц', num(T.pageviews)], ['Страниц за визит', v ? (Math.round(T.pageviews / v * 10) / 10).toLocaleString('ru-RU') : '—'],
      ['Клики «Apply»', num(T.applies)], ['Конверсия в клик', pct(T.apply_visits, v)], ['Поисков по сайту', num(T.searches)], ['Подписки на вакансии', num(T.alerts)], ['Скачано резюме', num(T.resumes)]];
    var searchNoPick = (d.searches || []).filter(function (r) { return !r.c; });
    root.querySelector('.st-body').innerHTML =
      '<div class="st-tiles">' + tiles.map(function (x) { return '<div><span>' + x[0] + '</span><b>' + x[1] + '</b></div>'; }).join('') + '</div>' +
      '<h2>Трафик</h2><p class="st-muted">Сколько людей пришло, откуда и на какую страницу.</p>' + days(d) +
      table('Откуда пришли и сколько это дало', 'Google, Bing, Yandex — поиск; ChatGPT, Perplexity, Claude — ИИ-ассистенты; Telegram, Reddit, X — соцсети; адрес сайта — переход по ссылке с него (в том числе с наших размещений); «Прямой заход» — ввели адрес или открыли закладку.', d.sources, v, { col: 'Источник', clicks: true }) +
      table('Сайты, с которых перешли', 'Домен страницы, где стояла ссылка.', d.referrers, null, { col: 'Сайт' }) +
      table('Страница входа', 'Первая страница визита.', d.entries, v, { col: 'Страница' }) +
      table('Откуда → на какую страницу', 'Например «Google → Вакансия: …»: по какому источнику на какую страницу попадают.', d.source_entry, v, { col: 'Источник → страница' }) +
      table('Страны', 'По данным Cloudflare.', d.countries, v, { col: 'Страна', country: true }) +
      table('UTM-метки', 'Ссылки с метками ?utm_source=… (например, из ваших постов).', d.utm, null, { col: 'source / medium / campaign' }) +
      '<h2>Отклики: клики «Apply»</h2><p class="st-muted">Переходы на сайт работодателя. Сами отклики видит работодатель.</p>' +
      table('Компания', 'По каким компаниям нажимают «Apply».', d.apply_company, T.applies, { col: 'Компания', ncol: 'Клики' }) +
      table('Откуда пришёл человек, который нажал', '', d.apply_source, T.applies, { col: 'Источник', ncol: 'Клики' }) +
      table('С какой страницы', '', d.apply_page, T.applies, { col: 'Страница', ncol: 'Клики' }) +
      table('Куда ведёт отклик', 'Сайт работодателя или его система найма.', d.apply_host, T.applies, { col: 'Сайт', ncol: 'Клики' }) +
      '<h2>Что делают на сайте</h2><p class="st-muted">Страницы, поиск, кнопки.</p>' +
      table('Разделы сайта', '', d.sections, T.pageviews, { col: 'Раздел', ncol: 'Просмотры' }) +
      table('Просмотры страниц', '', d.pageviews, T.pageviews, { col: 'Страница', ncol: 'Просмотры' }) +
      table('Поиск по сайту: что искали', 'Сколько раз искали и сколько раз после этого открыли вакансию из результатов.', d.searches, T.searches, { col: 'Запрос', ncol: 'Поиски', clicks: true, ccol: 'Открыли' }) +
      table('Что искали → что открыли', '', d.picks, null, { col: 'Запрос → вакансия', ncol: 'Раз' }) +
      table('Поиск без выбора', 'Ввели, но ничего не открыли: возможно, вакансий нет или поиск их не нашёл.', searchNoPick, null, { col: 'Запрос', ncol: 'Поиски' }) +
      table('Нажатия кнопок и настроек', '', d.buttons, null, { col: 'Кнопка', ncol: 'Нажатия' }) +
      table('Переходы на другие сайты', 'Уходы по ссылкам, кроме «Apply».', d.outbound, null, { col: 'Сайт', ncol: 'Переходы' }) +
      table('Подписки на вакансии: с какой страницы', '', d.alerts_from, T.alerts, { col: 'Страница', ncol: 'Подписки' }) +
      '<h2>Аудитория</h2><p class="st-muted">Чем и как открывают сайт.</p>' +
      table('Устройство', '', d.devices, v, { col: '' }) + table('Система', '', d.systems, v, { col: '' }) +
      table('Как открыли сайт', '', d.opened, v, { col: '' }) + table('Язык браузера', '', d.languages, v, { col: '' }) +
      '<p class="st-muted">Поисковые запросы из Google видны только в Google Search Console, из Bing — в Bing Webmaster Tools: браузеры не передают их сайтам.</p>';
    root.querySelector('.st-period').textContent = d.from === d.to ? d.from + ' (UTC)' : d.from + ' — ' + d.to + ' (UTC)';
  }

  root.innerHTML = '<p class="st-muted"><span class="st-period"></span>. Анонимно и без cookies. Этот браузер больше не считается в статистике. Визит засчитывается после первого движения мыши, прокрутки, касания или 15 секунд на открытой вкладке: роботы, которые открывают страницы без человека, в цифры не попадают.</p>' +
    '<div class="st-tabs" role="group" aria-label="Период">' + PERIODS.map(function (p, i) { return '<button type="button" class="btn sm' + (i === 2 ? ' primary' : ' ghost') + '" data-i="' + i + '">' + p[0] + '</button>'; }).join('') + '</div><div class="st-body"></div>';
  root.addEventListener('click', function (e) {
    var b = e.target.closest('[data-i]');
    if (b) { [].forEach.call(root.querySelectorAll('.st-tabs button'), function (x) { x.className = 'btn sm ' + (x === b ? 'primary' : 'ghost'); }); return load(+b.getAttribute('data-i')); }
    var all = e.target.closest('.st-all');
    if (all) { [].forEach.call(all.parentNode.querySelectorAll('.st-more'), function (tr) { tr.hidden = false; }); all.remove(); }
  });
  load(2);
})();
