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
      quiet(api('GET', '/api/admin/overview'), null), quiet(api('GET', '/api/admin/audience'), null)]).then(function (r) {
      S = { jobs: r[0].jobs || [], claims: r[1].claims || [], reports: (r[2].reports || []).filter(function (x) { return !x.decided; }), ov: r[3], aud: r[4] };
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
      '<div class="adm-act"><button class="btn primary" type="button" data-job-ok="' + esc(j.id) + '">Одобрить: вакансия выйдет на сайт</button>' +
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

  function draw() {
    var ov = S.ov, aud = S.aud, html = '';
    html += (note ? '<div class="banner ok">' + note + '</div>' : '');
    html += '<div class="ov-grid">' + tile(num(S.jobs.length), 'вакансий ждут проверки') + tile(num(S.claims.length), 'заявок на страницу компании') + tile(num(S.reports.length), 'жалоб без решения') +
      (ov ? tile(num(ov.users), 'аккаунтов') + tile(num(ov.live_jobs), 'размещённых вакансий на сайте') + tile('$' + num(ov.revenue_usd), 'выручка, оплачено заказов: ' + num(ov.paid_orders)) : '') +
      (aud && aud.accounts ? tile(num(aud.accounts.job_seekers), 'соискателей') + tile(num(aud.accounts.employers), 'работодателей') : '') +
      (aud && aud.alerts ? tile(num(aud.alerts.active), 'подписок на вакансии') : '') + '</div>';
    html += '<section class="sec"><div class="sec-head"><h2>Вакансии на проверке</h2></div>' + (S.jobs.length ? S.jobs.map(jobCard).join('') :
      '<p class="note">Очередь пуста. Новая вакансия от неподтверждённого работодателя появится здесь.</p>') + '</section>';
    html += '<section class="sec"><div class="sec-head"><h2>Заявки на страницу компании</h2></div>' + (S.claims.length ? S.claims.map(claimCard).join('') : '<p class="note">Заявок нет.</p>') + '</section>';
    html += '<section class="sec"><div class="sec-head"><h2>Жалобы на вакансии</h2></div>' + (S.reports.length ? S.reports.map(reportCard).join('') : '<p class="note">Жалоб нет.</p>') + '</section>';
    if (ov && ov.recent_jobs && ov.recent_jobs.length) html += '<section class="sec"><div class="sec-head"><h2>Последние размещённые вакансии</h2></div><div class="tablewrap"><table><tr><th>Дата</th><th>Вакансия</th><th>Компания</th><th>Статус</th><th>Просмотры</th><th>Клики</th></tr>' +
      ov.recent_jobs.map(function (j) { return '<tr><td>' + esc(day(new Date(j.created_at * 1000).toISOString())) + '</td><td>' + esc(j.title) + '</td><td>' + esc(j.company) + '</td><td>' + esc(j.status) + '</td><td>' + num(j.views) + '</td><td>' + num(j.applies) + '</td></tr>'; }).join('') + '</table></div></section>';
    if (ov && ov.recent_orders && ov.recent_orders.length) html += '<section class="sec"><div class="sec-head"><h2>Последние заказы</h2></div><div class="tablewrap"><table><tr><th>Дата</th><th>Продукт</th><th>Для</th><th>Сумма</th><th>Статус</th></tr>' +
      ov.recent_orders.map(function (o) { return '<tr><td>' + esc(day(new Date(o.created_at * 1000).toISOString())) + '</td><td>' + esc(o.product) + '</td><td>' + esc(o.label || '') + '</td><td>$' + num(o.amount_usd) + '</td><td>' + esc(o.status) + '</td></tr>'; }).join('') + '</table></div></section>';
    root.innerHTML = html; note = '';
    wire();
  }

  function act(el, work, done) {
    var card = el.closest('.adm-card'), box = card && card.querySelector('.acc-err');
    Array.prototype.forEach.call(card ? card.querySelectorAll('button') : [el], function (b) { b.disabled = true; });
    if (box) box.hidden = true;
    work().then(function () { note = done; return load(); }, function (e) {
      Array.prototype.forEach.call(card ? card.querySelectorAll('button') : [el], function (b) { b.disabled = false; });
      if (box) { box.textContent = e.message; box.hidden = false; }
    });
  }
  function wire() {
    var each = function (sel, fn) { Array.prototype.forEach.call(root.querySelectorAll(sel), fn); };
    each('[data-job-ok]', function (b) { b.addEventListener('click', function () { act(b, function () { return api('POST', '/api/admin/jobs/' + b.getAttribute('data-job-ok') + '/approve'); }, 'Вакансия одобрена: выйдет на сайт при ближайшем обновлении, работодателю ушло письмо.'); }); });
    each('form[data-job-no]', function (f) { f.addEventListener('submit', function (ev) { ev.preventDefault(); act(f, function () { return api('POST', '/api/admin/jobs/' + f.getAttribute('data-job-no') + '/reject', { reason: f.elements.reason.value.trim() }); }, 'Вакансия отклонена, работодатель увидит причину.'); }); });
    each('[data-claim-ok]', function (b) { b.addEventListener('click', function () { act(b, function () { return api('POST', '/api/admin/claims/' + b.getAttribute('data-claim-ok') + '/approve'); }, 'Страница компании отдана аккаунту.'); }); });
    each('form[data-claim-no]', function (f) { f.addEventListener('submit', function (ev) { ev.preventDefault(); act(f, function () { return api('POST', '/api/admin/claims/' + f.getAttribute('data-claim-no') + '/reject', { reason: f.elements.reason.value.trim() }); }, 'Заявка отклонена.'); }); });
    each('[data-rep]', function (b) { b.addEventListener('click', function () { act(b, function () { return api('POST', '/api/admin/reports/' + b.getAttribute('data-id') + '/decide', { decision: b.getAttribute('data-rep') }); }, 'Решение по жалобе записано.'); }); });
    each('[data-job-rm]', function (b) { b.addEventListener('click', function () { act(b, function () { return api('POST', '/api/admin/jobs/' + b.getAttribute('data-job-rm') + '/remove'); }, 'Вакансия снята с сайта.'); }); });
  }

  if (!token) return gate('Сначала войдите в свой аккаунт на сайте, потом откройте эту страницу снова.', true);
  root.innerHTML = '<p class="note">Загрузка…</p>';
  load().catch(function (e) {
    if (e.status === 401) gate('Сессия закончилась. Войдите в аккаунт заново.', true);
    else if (e.status === 403) gate('Этот аккаунт не модератор. Страница работает только для аккаунта владельца сайта.', false);
    else gate(esc(e.message), false);
  });
})();
