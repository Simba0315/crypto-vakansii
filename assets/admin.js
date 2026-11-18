/* The moderator's page (/admin/), for the owner: what waits for a person. Jobs held for review (approve, or reject with a reason the
   employer reads), claims of company pages, reports about listings, and the numbers of the accounts. It works under the owner's own
   sign-in: the API lets a signed-in account from ADMIN_EMAILS use the moderation routes (server/README.md). The owner reads Russian,
   so this one page is in Russian; nothing here is linked from the public site or listed in the sitemap. */
(function () {
  var root = document.getElementById('adm');
  if (!root || !window.HRN) return;
  var H = window.HRN, esc = H.esc, API = (root.getAttribute('data-api') || '').replace(/\/+$/, ''), SITE = root.getAttribute('data-site') || '';
  var token = H.get('hrn_token', ''), S = {}, note = '';

  function api(method, path, data) {
    var headers = { Authorization: 'Bearer ' + token };
    if (data) headers['Content-Type'] = 'application/json';
    return fetch(API + path, { method: method, headers: headers, body: data ? JSON.stringify(data) : undefined }).then(function (r) {
      return r.json().catch(function () { return {}; }).then(function (b) {
        if (r.ok) return b;
        var e = new Error(b.message || 'Не получилось. Попробуйте ещё раз.'); e.status = r.status; e.code = b.error; throw e;
      });
    }, function () { throw new Error('Нет связи с сервером.'); });
  }
  var quiet = function (p, dflt) { return p.catch(function () { return dflt; }); };
  var num = function (n) { return Number(n || 0).toLocaleString('ru-RU'); };
  var day = function (s) { return String(s || '').slice(0, 10); };
  var BY = { '': 'работодатель со своего домена', unverified: 'не подтверждён (личная почта)', recruiter: 'рекрутер (LinkedIn)', employer: 'работодатель со своего домена' };

  // the server gives its reasons in English; the usual ones are said here in Russian, an unusual one is shown as it came
  var RU = [[/the employer is not verified yet/i, 'работодатель не подтверждён: аккаунт на личной почте, а не на почте компании'],
    [/does not show this job title/i, 'на странице отклика нет названия этой вакансии: откройте ссылку и проверьте, что она ведёт именно на неё'],
    [/not trusted yet: its first jobs/i, 'новый аккаунт: его первые вакансии смотрит человек'],
    [/a report about a job of this account was upheld/i, 'по вакансии этого аккаунта уже была подтверждённая жалоба'],
    [/posted by a recruiter/i, 'разместил рекрутер (вход через LinkedIn) для чужой компании: такие вакансии проверяются всегда'],
    [/is on a shared host/i, 'сайт компании на общем хостинге, где страницу может сделать кто угодно'],
    [/is on a hiring system/i, 'ссылка отклика ведёт в систему найма, которую нельзя связать с сайтом компании'],
    [/did not answer: look whether it is listed already/i, 'проверка на дубль не ответила: посмотрите, нет ли этой вакансии на сайте'],
    [/was registered \d+ days ago/i, 'домен компании зарегистрирован совсем недавно'],
    [/well-known employer whose name is often borrowed/i, 'известный работодатель, чьим именем часто прикрываются мошенники: проверьте особенно внимательно'],
    [/is not on a domain of/i, 'название известной компании, а сайт или аккаунт не на её домене: возможна подделка'],
    [/sent again after it was not accepted/i, 'отправлена повторно после отказа'],
    [/does not know .* own domain/i, 'сайт не знает официальный домен этой компании: проверьте, что домен аккаунта её']];
  function ru(reason) {
    return String(reason || '').split(/;\s+/).filter(Boolean).map(function (part) {
      for (var i = 0; i < RU.length; i++) if (RU[i][0].test(part)) return RU[i][1];
      return esc(part);
    }).join('; ');
  }

  function gate(text, link) {
    root.innerHTML = '<div class="banner">' + text + '</div>' + (link ? '<p><a class="btn primary" href="' + esc(SITE) + '/account/">Войти в аккаунт</a></p>' : '');
  }

  function load() {
    return Promise.all([api('GET', '/api/admin/review'), quiet(api('GET', '/api/admin/claims'), { claims: [] }), quiet(api('GET', '/api/admin/reports'), { reports: [] }),
      quiet(api('GET', '/api/admin/overview'), null), quiet(api('GET', '/api/admin/audience'), null), quiet(api('GET', '/api/admin/accounts'), null)]).then(function (r) {
      S = { jobs: r[0].jobs || [], claims: r[1].claims || [], reports: (r[2].reports || []).filter(function (x) { return !x.decided; }), ov: r[3], aud: r[4], acc: r[5] };
      draw();
    });
  }

  function jobCard(j) {
    var a = j.account || {};
    var facts = [BY[j.posted_by] || j.posted_by, a.email ? esc(a.email) : (a.email_domain ? 'домен ' + esc(a.email_domain) : ''), 'аккаунту ' + (a.age_days || 0) + ' дн.',
      'одобрено раньше: ' + (a.approved_jobs || 0), a.upheld_reports ? 'подтверждённых жалоб: ' + a.upheld_reports : '', j.held_placements ? 'оплаченное продвижение ждёт: ' + j.held_placements : '',
      j.open_reports ? 'жалоб на вакансию: ' + j.open_reports : ''].filter(Boolean);
    return '<article class="adm-card" data-id="' + esc(j.id) + '"><div class="adm-h"><h3>' + esc(j.title) + '</h3><span class="adm-co">' + esc(j.company) + (j.location ? ' · ' + esc(j.location) : '') + (j.salary ? ' · ' + esc(j.salary) : '') + '</span></div>' +
      '<p class="adm-why"><b>Почему на проверке:</b> ' + (ru(j.reason) || 'первая вакансия нового аккаунта') + '</p>' +
      '<p class="adm-links"><a href="' + esc(j.apply_url) + '" target="_blank" rel="noopener noreferrer">Открыть страницу отклика ↗</a> <a href="' + esc(j.company_url) + '" target="_blank" rel="noopener noreferrer">Сайт компании ↗</a></p>' +
      '<p class="adm-desc">' + esc(j.description) + '</p><p class="adm-facts">' + facts.join(' · ') + ' · отправлена ' + esc(day(j.posted)) + '</p>' +
      '<div class="adm-act"><button class="btn primary" type="button" data-job-ok="' + esc(j.id) + '" data-page="' + esc(j.page || '') + '" data-company="' + esc(j.company || '') + '">Одобрить: вакансия выйдет на сайт</button>' +
      '<form class="adm-no" data-job-no="' + esc(j.id) + '"><input name="reason" maxlength="300" required placeholder="Причина отказа, по-английски: её увидит работодатель" aria-label="Причина отказа">' +
      '<button class="btn ghost" type="submit" style="margin:0">Отклонить</button></form></div><p class="acc-err" role="alert" hidden></p></article>';
  }
  function claimCard(c) {
    var a = c.account || {};
    return '<article class="adm-card" data-id="' + esc(c.id) + '"><div class="adm-h"><h3>' + esc(c.company) + '</h3><span class="adm-co">заявка от ' + esc(c.asked) + '</span></div>' +
      '<p class="adm-facts">Домен аккаунта: <b>' + esc(c.domain) + '</b> · сайт компании по нашим данным: <b>' + esc(c.site_we_know || 'неизвестен') + '</b> · аккаунту ' + (a.age_days || 0) + ' дн.' +
      (a.proved_by && a.proved_by.length ? ' · домен подтверждён: ' + esc(a.proved_by.join(', ')) : '') + '</p>' + (c.reason ? '<p class="adm-why"><b>Почему ждёт:</b> ' + ru(c.reason) + '</p>' : '') +
      '<div class="adm-act"><button class="btn primary" type="button" data-claim-ok="' + esc(c.id) + '">Отдать страницу компании</button>' +
      '<form class="adm-no" data-claim-no="' + esc(c.id) + '"><input name="reason" maxlength="300" required placeholder="Причина отказа, по-английски" aria-label="Причина отказа">' +
      '<button class="btn ghost" type="submit" style="margin:0">Отклонить</button></form></div><p class="acc-err" role="alert" hidden></p></article>';
  }
  function reportCard(r) {
    return '<article class="adm-card" data-id="' + esc(r.id) + '"><div class="adm-h"><h3>' + esc(r.title || r.page || 'Вакансия') + '</h3><span class="adm-co">' + esc(r.company || '') + ' · ' + esc(day(r.received)) + '</span></div>' +
      '<p class="adm-why"><b>Жалоба:</b> ' + esc(r.reason) + (r.note ? ' — ' + esc(r.note) : '') + '</p>' + (r.page ? '<p class="adm-links"><a href="' + esc(SITE + r.page) + '" target="_blank" rel="noopener">Открыть вакансию ↗</a></p>' : '') +
      '<div class="adm-act"><button class="btn primary" type="button" data-rep="upheld" data-id="' + esc(r.id) + '">Жалоба верная</button> <button class="btn ghost" type="button" style="margin:0" data-rep="dismissed" data-id="' + esc(r.id) + '">Жалоба не по делу</button>' +
      (r.job_id ? ' <button class="btn ghost" type="button" style="margin:0" data-job-rm="' + esc(r.job_id) + '">Снять вакансию с сайта</button>' : '') + '</div><p class="acc-err" role="alert" hidden></p></article>';
  }
  function tile(n, label) { return '<div class="ov-c"><b>' + n + '</b><span>' + label + '</span></div>'; }
  // the owner approved a job on 18 Nov 2026 and found no way from this page to the job or to its company: every job and company
  // here is a link to its page on the site, opened in a new tab
  var slug = function (x) { return String(x || '').toLowerCase().replace(/[^a-z0-9]+/g, '-').replace(/^-+|-+$/g, '').slice(0, 60).replace(/-+$/, '') || 'job'; };
  var out = function (path, text) { return '<a href="' + esc(SITE + path) + '" target="_blank" rel="noopener">' + esc(text) + '</a>'; };
  var ST = { review: 'на проверке', live: 'на сайте', expired: 'срок вышел', closed: 'закрыта', rejected: 'отклонена', removed: 'снята с сайта', paid: 'оплачен', pending: 'ждёт оплаты', cancelled: 'отменён', failed: 'не прошёл' };
  var st = function (x) { return ST[x] || x; };
  var dts = function (ts) { return ts ? esc(day(new Date(ts * 1000).toISOString())) : ''; };
  var SIDE = { employer: 'работодатель', 'job seeker': 'соискатель', both: 'работодатель и соискатель', 'nothing yet': 'пока ничего не делал' };
  function accRow(a) {
    var jobs = a.jobs ? num(a.jobs_live) + ' на сайте' + (a.jobs_review ? ', ' + num(a.jobs_review) + ' на проверке' : '') + ', всего ' + num(a.jobs) : '0';
    return '<tr data-find="' + esc((a.email + ' ' + (a.company || '')).toLowerCase()) + '"><td>' + esc(a.created) + '</td><td><b>' + esc(a.email) + '</b>' + (a.banned ? ' <span class="adm-bad">заблокирован</span>' : '') + '</td>' +
      '<td>' + (a.company ? (a.jobs_live ? out('/companies/' + slug(a.company) + '/', a.company) : esc(a.company)) : '') + '</td><td>' + (SIDE[a.side] || esc(a.side)) + '</td><td>' + (a.confirmed ? 'да' : '<span class="adm-bad">нет</span>') + '</td>' +
      '<td>' + jobs + '</td><td>' + num(a.company_pages) + '</td><td>' + num(a.resumes) + '</td><td>' + (a.paid_usd ? '<b>$' + num(a.paid_usd) + '</b> (' + num(a.paid_orders) + ')' : '$0') + '</td>' +
      '<td>' + esc(a.last_paid || '') + '</td><td>' + esc(a.last_signin || '') + '</td><td>' + esc(a.plus_until || '') + '</td></tr>';
  }
  function accounts() {
    var a = S.acc;
    if (!a) return '';
    return '<section class="sec" id="accounts"><div class="sec-head"><h2>Аккаунты</h2></div>' +
      '<p class="note">Всего аккаунтов: <b>' + num(a.total) + '</b>. Оплачено заказов: <b>' + num(a.paid_orders) + '</b> на <b>$' + num(a.paid_usd) + '</b>.' + (a.total > a.accounts.length ? ' Показаны ' + num(a.accounts.length) + ' самых новых; поиск ищет по всем.' : '') + '</p>' +
      '<p class="dirfind"><input type="search" id="acc-find" placeholder="Почта или компания" aria-label="Найти аккаунт"></p>' +
      '<div class="tablewrap"><table class="adm-acc"><tr><th>Регистрация</th><th>Почта</th><th>Компания</th><th>Кто</th><th>Почта подтверждена</th><th>Вакансии</th><th>Страниц компании</th><th>Резюме</th><th>Оплатил (заказов)</th><th>Последняя оплата</th><th>Последний вход</th><th>Plus до</th></tr>' +
      a.accounts.map(accRow).join('') + '</table></div><p class="note" id="acc-none" hidden>Нет аккаунтов с такими буквами.</p></section>';
  }

  function draw() {
    var ov = S.ov, aud = S.aud, html = '';
    html += (note ? '<div class="banner ok">' + note + '</div>' : '');
    html += '<div class="pillrow" role="navigation" aria-label="Разделы"><a href="#queue">Очередь<i>' + num(S.jobs.length) + '</i></a><a href="#claims">Заявки на страницу<i>' + num(S.claims.length) + '</i></a><a href="#reports">Жалобы<i>' + num(S.reports.length) + '</i></a>' +
      '<a href="#posted">Вакансии</a><a href="#orders">Заказы</a>' + (S.acc ? '<a href="#accounts">Аккаунты<i>' + num(S.acc.total) + '</i></a>' : '') + '</div>';
    html += '<div class="ov-grid">' + tile(num(S.jobs.length), 'вакансий ждут проверки') + tile(num(S.claims.length), 'заявок на страницу компании') + tile(num(S.reports.length), 'жалоб без решения') +
      (ov ? tile(num(ov.users), 'аккаунтов') + tile(num(ov.live_jobs), 'размещённых вакансий на сайте') + tile('$' + num(ov.revenue_usd), 'выручка, оплачено заказов: ' + num(ov.paid_orders)) : '') +
      (aud && aud.accounts ? tile(num(aud.accounts.job_seekers), 'соискателей') + tile(num(aud.accounts.employers), 'работодателей') : '') +
      (aud && aud.alerts ? tile(num(aud.alerts.active), 'подписок на вакансии') : '') + '</div>';
    html += '<section class="sec" id="queue"><div class="sec-head"><h2>Вакансии на проверке</h2></div>' + (S.jobs.length ? S.jobs.map(jobCard).join('') :
      '<p class="note">Очередь пуста. Новая вакансия от неподтверждённого работодателя появится здесь.</p>') + '</section>';
    html += '<section class="sec" id="claims"><div class="sec-head"><h2>Заявки на страницу компании</h2></div>' + (S.claims.length ? S.claims.map(claimCard).join('') : '<p class="note">Заявок нет.</p>') + '</section>';
    html += '<section class="sec" id="reports"><div class="sec-head"><h2>Жалобы на вакансии</h2></div>' + (S.reports.length ? S.reports.map(reportCard).join('') : '<p class="note">Жалоб нет.</p>') + '</section>';
    if (ov && ov.recent_jobs && ov.recent_jobs.length) html += '<section class="sec" id="posted"><div class="sec-head"><h2>Размещённые вакансии</h2></div>' +
      '<p class="note">Название открывает страницу вакансии на сайте, компания — страницу компании. Обе появляются после ближайшего обновления сайта (обычно в течение часа после одобрения).</p>' +
      '<div class="tablewrap"><table><tr><th>Дата</th><th>Вакансия</th><th>Компания</th><th>Аккаунт</th><th>Статус</th><th>Просмотры</th><th>Клики</th><th></th></tr>' +
      ov.recent_jobs.map(function (j) {
        var on = j.status === 'live';
        return '<tr class="adm-row"><td>' + dts(j.created_at) + '</td><td>' + (j.page ? out(j.page, j.title) : esc(j.title)) + '</td><td>' + (j.company_page ? out(j.company_page, j.company) : esc(j.company)) + '</td><td>' + esc(j.email || '') + '</td>' +
          '<td>' + esc(st(j.status)) + (on && j.until ? ' до ' + esc(j.until) : '') + '</td><td>' + num(j.views) + '</td><td>' + num(j.applies) + '</td>' +
          '<td>' + (j.apply_url ? '<a href="' + esc(j.apply_url) + '" target="_blank" rel="noopener nofollow">ссылка отклика</a> ' : '') + (on ? '<button class="btn ghost sm" type="button" style="margin:0" data-job-rm="' + esc(j.id) + '">Снять с сайта</button>' : '') + '</td></tr>';
      }).join('') + '</table></div></section>';
    if (ov && ov.recent_orders && ov.recent_orders.length) html += '<section class="sec" id="orders"><div class="sec-head"><h2>Заказы</h2></div><div class="tablewrap"><table><tr><th>Дата</th><th>Аккаунт</th><th>Продукт</th><th>Для</th><th>Сумма</th><th>Статус</th><th>Оплачен</th></tr>' +
      ov.recent_orders.map(function (o) { return '<tr><td>' + dts(o.created_at) + '</td><td>' + esc(o.email || '') + '</td><td>' + esc(o.product) + '</td><td>' + esc(o.label || '') + '</td><td>' + (o.amount_usd ? '$' + num(o.amount_usd) : (o.credits ? num(o.credits) + ' кредитов' : '$0')) + '</td><td>' + esc(st(o.status)) + '</td><td>' + dts(o.paid_at) + '</td></tr>'; }).join('') + '</table></div></section>';
    else html += '<section class="sec" id="orders"><div class="sec-head"><h2>Заказы</h2></div><p class="note">Заказов пока нет.</p></section>';
    html += accounts();
    root.innerHTML = html; note = '';
    wire();
  }

  function act(el, work, done) {
    var card = el.closest('.adm-card, .adm-row'), box = card && card.querySelector('.acc-err');
    Array.prototype.forEach.call(card ? card.querySelectorAll('button') : [el], function (b) { b.disabled = true; });
    if (box) box.hidden = true;
    work().then(function () { note = done; return load(); }, function (e) {
      Array.prototype.forEach.call(card ? card.querySelectorAll('button') : [el], function (b) { b.disabled = false; });
      if (box) { box.textContent = e.message; box.hidden = false; }
      else root.insertAdjacentHTML('afterbegin', '<div class="banner">' + esc(e.message) + '</div>');      // a row of a table has no place of its own for the message
    });
  }
  function wire() {
    var each = function (sel, fn) { Array.prototype.forEach.call(root.querySelectorAll(sel), fn); };
    each('[data-job-ok]', function (b) { b.addEventListener('click', function () {
      var pg = b.getAttribute('data-page'), co = b.getAttribute('data-company');
      act(b, function () { return api('POST', '/api/admin/jobs/' + b.getAttribute('data-job-ok') + '/approve'); }, 'Вакансия одобрена: выйдет на сайт при ближайшем обновлении, работодателю ушло письмо.' +
        (pg ? ' Где она будет: ' + out(pg, 'страница вакансии') + (co ? ', ' + out('/companies/' + slug(co) + '/', 'страница компании ' + co) : '') + '.' : ''));
    }); });
    var find = document.getElementById('acc-find');
    if (find) {
      var filter = function () {
        var q = find.value.trim().toLowerCase(), shown = 0;
        each('.adm-acc tr[data-find]', function (tr) { var ok = !q || tr.getAttribute('data-find').indexOf(q) >= 0; tr.hidden = !ok; if (ok) shown++; });
        var none = document.getElementById('acc-none'); if (none) none.hidden = shown > 0;
      };
      find.addEventListener('input', filter);
      // more accounts than the page holds: Enter asks the server, which looks through all of them
      find.addEventListener('keydown', function (ev) {
        if (ev.key !== 'Enter' || !S.acc || S.acc.total <= S.acc.accounts.length && !S.acc.searched) return;
        var q = find.value.trim();
        api('GET', '/api/admin/accounts' + (q ? '?q=' + encodeURIComponent(q) : '')).then(function (r) { r.searched = !!q; S.acc = r; draw(); var f = document.getElementById('acc-find'); if (f) { f.value = q; f.focus(); } }, function () {});
      });
    }
    each('form[data-job-no]', function (f) { f.addEventListener('submit', function (ev) { ev.preventDefault(); act(f, function () { return api('POST', '/api/admin/jobs/' + f.getAttribute('data-job-no') + '/reject', { reason: f.elements.reason.value.trim() }); }, 'Вакансия отклонена, работодатель увидит причину.'); }); });
    each('[data-claim-ok]', function (b) { b.addEventListener('click', function () { act(b, function () { return api('POST', '/api/admin/claims/' + b.getAttribute('data-claim-ok') + '/approve'); }, 'Страница компании отдана аккаунту.'); }); });
    each('form[data-claim-no]', function (f) { f.addEventListener('submit', function (ev) { ev.preventDefault(); act(f, function () { return api('POST', '/api/admin/claims/' + f.getAttribute('data-claim-no') + '/reject', { reason: f.elements.reason.value.trim() }); }, 'Заявка отклонена.'); }); });
    each('[data-rep]', function (b) { b.addEventListener('click', function () { act(b, function () { return api('POST', '/api/admin/reports/' + b.getAttribute('data-id') + '/decide', { decision: b.getAttribute('data-rep') }); }, 'Решение по жалобе записано.'); }); });
    each('[data-job-rm]', function (b) { b.addEventListener('click', function () {
      // in the table one click is close to the links, so it asks first; on a report's card the button stands alone
      if (b.closest('.adm-row') && !window.confirm('Снять эту вакансию с сайта? Она пропадёт при ближайшем обновлении, работодатель увидит её в кабинете как снятую.')) return;
      act(b, function () { return api('POST', '/api/admin/jobs/' + b.getAttribute('data-job-rm') + '/remove'); }, 'Вакансия снята с сайта.'); }); });
  }

  if (!token) return gate('Сначала войдите в свой аккаунт на сайте, потом откройте эту страницу снова.', true);
  root.innerHTML = '<p class="note">Загрузка…</p>';
  load().catch(function (e) {
    if (e.status === 401) gate('Сессия закончилась. Войдите в аккаунт заново.', true);
    else if (e.status === 403) gate('Этот аккаунт не модератор. Страница работает только для аккаунта владельца сайта: выйдите из этого аккаунта, зарегистрируйтесь или войдите под адресом администратора (он задан на сервере в ADMIN_EMAILS), подтвердите почту по ссылке из письма и откройте эту страницу снова.', true);
    else gate(esc(e.message), false);
  });
})();
