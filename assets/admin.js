/* The moderator's page (/admin/), for the owner: what waits for a person. Jobs held for review (approve, or reject with a reason the
   employer reads), claims of company pages, reports about listings, and the numbers of the accounts. It works under the owner's own
   sign-in: the API lets a signed-in account from ADMIN_EMAILS use the moderation routes (server/README.md). The owner reads Russian,
   so this one page is in Russian; nothing here is linked from the public site or listed in the sitemap.
   26 Nov 2026 (the owner, 18 Nov: block an account and edit a job right here): a job is edited in place, from the queue and from the
   list of posted jobs, with the log of who changed what; an account is blocked from the list of accounts and from the queue, with a
   reason and a step to confirm, and unblocked. What needs the newer API appears only when the server names it (GET review: features),
   so this page keeps working against a server that was not updated yet. A block always needs the owner's key (ADMIN_TOKEN): the
   server keeps bans away from a signed-in session on purpose, so the key is asked for once and kept in this tab only. */
(function () {
  var root = document.getElementById('adm');
  if (!root || !window.HRN) return;
  var H = window.HRN, esc = H.esc, API = (root.getAttribute('data-api') || '').replace(/\/+$/, ''), SITE = root.getAttribute('data-site') || '';
  var token = H.get('hrn_token', ''), S = {}, F = {}, note = '', ME = '';

  function call(key, method, path, data) {
    var headers = { Authorization: 'Bearer ' + key };
    if (data) headers['Content-Type'] = 'application/json';
    return fetch(API + path, { method: method, headers: headers, body: data ? JSON.stringify(data) : undefined }).then(function (r) {
      return r.json().catch(function () { return {}; }).then(function (b) {
        if (r.ok) return b;
        var e = new Error(b.message || 'Не получилось. Попробуйте ещё раз.'); e.status = r.status; e.code = b.error; e.body = b; throw e;
      });
    }, function () { throw new Error('Нет связи с сервером.'); });
  }
  var api = function (method, path, data) { return call(token, method, path, data); };
  // the owner's key (ADMIN_TOKEN) for what only it may do (blocks): typed once, kept in this tab until it is closed, sent only with those requests
  var KEY = 'hrn_owner_key';
  var ownerKey = function () { try { return sessionStorage.getItem(KEY) || ''; } catch (e) { return ''; } };
  var keepKey = function (k) { try { if (k) sessionStorage.setItem(KEY, k); else sessionStorage.removeItem(KEY); } catch (e) {} };
  var quiet = function (p, dflt) { return p.catch(function () { return dflt; }); };
  var num = function (n) { return Number(n || 0).toLocaleString('ru-RU'); };
  var day = function (s) { return String(s || '').slice(0, 10); };
  var when = function (iso) { var d = new Date(iso); return isNaN(d) ? esc(iso || '') : d.toLocaleString('ru-RU', { day: '2-digit', month: '2-digit', year: 'numeric', hour: '2-digit', minute: '2-digit' }); };
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
  // what the server says when an edit or a block is refused, in Russian; anything else as it came
  var FIELD = { title: 'название', location: 'место', salary: 'оплата', description: 'описание', apply_url: 'ссылка отклика', remote: 'удалённо', hybrid: 'гибрид' };
  function why(e) {
    var m = e.message || '', c = e.code || '';
    if (e.status === 403) return 'Нет прав на это действие: войдите под адресом модератора.';
    if (c === 'title') return 'Название: от 4 до 120 знаков.';
    if (c === 'description') return /links/i.test(m) ? 'В описании не больше двух ссылок: откликаются по ссылке отклика.' : 'Описание: от 80 до 1 500 знаков.';
    if (c === 'salary') return 'Оплата: не больше 60 знаков.';
    if (c === 'location') return 'Место: не больше 120 знаков.';
    if (c === 'apply_url') return /starting with https/i.test(m) ? 'Ссылка отклика должна начинаться с https://' : /must be on/i.test(m) ? 'Ссылка отклика должна вести на сайт компании или в систему найма (Greenhouse, Lever, Ashby…). ' + esc(m)
      : 'Ссылка отклика не прошла проверку: ' + esc(m);
    if (c === 'rejected') return 'Проверка текста не пропускает такую вакансию: ' + esc(((e.body && e.body.reasons) || []).join(' ') || m);
    if (c === 'duplicate') return 'У этого аккаунта уже есть вакансия с таким названием.';
    if (c === 'remote') return 'Вакансия либо удалённая, либо гибрид, не оба сразу.';
    if (c === 'limit') return 'Слишком много проверок ссылок за час. Попробуйте позже.';
    if (c === 'reason') return 'Причина: от 3 до 300 знаков.';
    if (c === 'moderator') return 'Это ваш собственный аккаунт модератора (адрес из ADMIN_EMAILS): его отсюда не блокируют.';
    if (c === 'not_banned') return 'Этот аккаунт не заблокирован.';
    return esc(m);
  }

  function gate(text, link) {
    root.innerHTML = '<div class="banner">' + text + '</div>' + (link ? '<p><a class="btn primary" href="' + esc(SITE) + '/account/">Войти в аккаунт</a></p>' : '');
  }

  function load() {
    return Promise.all([api('GET', '/api/admin/review'), quiet(api('GET', '/api/admin/claims'), { claims: [] }), quiet(api('GET', '/api/admin/reports'), { reports: [] }),
      quiet(api('GET', '/api/admin/overview'), null), quiet(api('GET', '/api/admin/audience'), null), quiet(api('GET', '/api/admin/accounts'), null), quiet(api('GET', '/api/me'), null)]).then(function (r) {
      F = {}; (r[0].features || []).forEach(function (f) { F[f] = true; });
      ME = r[6] && r[6].user ? String(r[6].user.email || '').toLowerCase() : '';        // the account signed in here: never offered for a block
      S = { jobs: r[0].jobs || [], claims: r[1].claims || [], reports: (r[2].reports || []).filter(function (x) { return !x.decided; }), ov: r[3], aud: r[4], acc: r[5], log: null };
      return F.log ? quiet(api('GET', '/api/admin/log'), null) : null;
    }).then(function (log) { S.log = log; draw(); });
  }

  // a section: one light framed panel, a small label over a headline in two weights (the account pages' look of 25 Nov 2026)
  function panel(id, label, title, inner, sub) {
    return '<section class="sec adm-pan" id="' + id + '"><div class="sec-head' + (sub ? ' has-sub' : '') + '"><div class="sec-ttl"><p class="sec-label">' + label + '</p><h2 class="tw">' + title + '</h2></div>' +
      (sub ? '<p class="sec-sub">' + sub + '</p>' : '') + '</div>' + inner + '</section>';
  }
  var ICON = { edit: 'M4 20h4L19 9l-4-4L4 16zM13.5 6.5l4 4', block: 'M12 3a9 9 0 1 0 0 18 9 9 0 0 0 0-18zM5.6 5.6l12.8 12.8', open: 'M7 11V8a5 5 0 0 1 9.6-2M5 11h14v10H5z' };
  var ic = function (k) { return '<svg class="adm-ic" viewBox="0 0 24 24" aria-hidden="true" focusable="false"><path d="' + ICON[k] + '"/></svg>'; };
  var place = function (j) { return [j.location, j.remote ? 'удалённо' : j.hybrid ? 'гибрид' : ''].filter(Boolean).map(esc).join(' · '); };
  function edits(list) {                // the last edit of a job made here, and how many there were
    if (!list || !list.length) return '';
    var l = list[0], f = (l.fields || []).map(function (x) { return FIELD[x.field] || x.field; }).join(', ');
    return '<p class="adm-edited">' + ic('edit') + '<span>Изменена здесь' + (list.length > 1 ? ' ' + list.length + ' раза' : '') + ': ' + when(l.at) + ', ' + esc(l.by) + ' — ' + esc(f) + '</span></p>';
  }

  function jobCard(j) {
    var a = j.account || {};
    var facts = [BY[j.posted_by] || j.posted_by, a.email ? esc(a.email) : (a.email_domain ? 'домен ' + esc(a.email_domain) : ''), 'аккаунту ' + (a.age_days || 0) + ' дн.',
      'одобрено раньше: ' + (a.approved_jobs || 0), a.upheld_reports ? 'подтверждённых жалоб: ' + a.upheld_reports : '', j.held_placements ? 'оплаченное продвижение ждёт: ' + j.held_placements : '',
      j.open_reports ? 'жалоб на вакансию: ' + j.open_reports : ''].filter(Boolean);
    var where = place(j);
    var more = (F.job_edit ? '<button class="btn ghost sm" type="button" data-edit="' + esc(j.id) + '">' + ic('edit') + 'Править вакансию</button>' : '') +
      (a.id && String(a.email || '').toLowerCase() !== ME ? '<button class="btn ghost sm adm-ban" type="button" data-ban="' + esc(a.id) + '" data-email="' + esc(a.email || '') + '">' + ic('block') + 'Заблокировать аккаунт</button>' : '');
    return '<article class="adm-card" data-id="' + esc(j.id) + '"><div class="adm-h"><h3>' + esc(j.title) + '</h3><span class="adm-co">' + esc(j.company) + (where ? ' · ' + where : '') + (j.salary ? ' · ' + esc(j.salary) : '') + '</span></div>' +
      '<p class="adm-why"><b>Почему на проверке:</b> ' + (ru(j.reason) || 'первая вакансия нового аккаунта') + '</p>' + edits(j.edits) +
      '<p class="adm-links"><a href="' + esc(j.apply_url) + '" target="_blank" rel="noopener noreferrer">Открыть страницу отклика ↗</a> <a href="' + esc(j.company_url) + '" target="_blank" rel="noopener noreferrer">Сайт компании ↗</a></p>' +
      '<p class="adm-desc">' + esc(j.description) + '</p><p class="adm-facts">' + facts.join(' · ') + ' · отправлена ' + esc(day(j.posted)) + '</p>' +
      '<div class="adm-act"><button class="btn primary" type="button" data-job-ok="' + esc(j.id) + '" data-page="' + esc(j.page || '') + '" data-company="' + esc(j.company || '') + '">Одобрить: вакансия выйдет на сайт</button>' +
      '<form class="adm-no" data-job-no="' + esc(j.id) + '"><input name="reason" maxlength="300" required placeholder="Причина отказа, по-английски: её увидит работодатель" aria-label="Причина отказа">' +
      '<button class="btn ghost" type="submit" style="margin:0">Отклонить</button></form></div>' + (more ? '<div class="adm-more">' + more + '</div>' : '') + '<p class="acc-err" role="alert" hidden></p></article>';
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
  // on a phone each row of these tables is a card (.rkt): the first cell is its title, every other one carries the name of its column
  var td = function (label, html) { return '<td data-l="' + label + '">' + html + '</td>'; };
  function accRow(a) {
    var jobs = a.jobs ? num(a.jobs_live) + ' на сайте' + (a.jobs_review ? ', ' + num(a.jobs_review) + ' на проверке' : '') + ', всего ' + num(a.jobs) : '0';
    var status = a.banned ? '<span class="adm-tag bad">заблокирован' + (a.banned_on ? ' ' + esc(a.banned_on) : '') + '</span>' + (a.ban_reason ? '<span class="adm-tag-why">' + esc(a.ban_reason) + '</span>' : '')
      : a.moderator || String(a.email).toLowerCase() === ME ? '<span class="adm-tag">ваш аккаунт модератора</span>' : '';
    var act = a.banned ? (F.unban ? '<button class="btn ghost sm" type="button" data-unban="' + esc(a.id) + '" data-email="' + esc(a.email) + '">' + ic('open') + 'Разблокировать</button>' : '')
      : a.moderator || String(a.email).toLowerCase() === ME ? '' : '<button class="btn ghost sm adm-ban" type="button" data-ban="' + esc(a.id) + '" data-email="' + esc(a.email) + '" data-jobs="' + esc((a.jobs_live || 0) + (a.jobs_review || 0)) + '">' + ic('block') + 'Заблокировать</button>';
    return '<tr data-find="' + esc((a.email + ' ' + (a.company || '')).toLowerCase()) + '"' + (a.banned ? ' class="adm-off"' : '') + '><td class="adm-who"><b>' + esc(a.email) + '</b>' + (status ? '<span class="adm-st">' + status + '</span>' : '') + (act ? '<span class="adm-ra">' + act + '</span>' : '') + '</td>' +
      td('Регистрация', esc(a.created)) + td('Компания', a.company ? (a.jobs_live ? out('/companies/' + slug(a.company) + '/', a.company) : esc(a.company)) : '—') + td('Кто', SIDE[a.side] || esc(a.side)) +
      td('Почта подтверждена', a.confirmed ? 'да' : '<span class="adm-bad">нет</span>') + td('Вакансии', jobs) + td('Страниц компании', num(a.company_pages)) + td('Резюме', num(a.resumes)) +
      td('Оплатил (заказов)', a.paid_usd ? '<b>$' + num(a.paid_usd) + '</b> (' + num(a.paid_orders) + ')' : '$0') + td('Последняя оплата', esc(a.last_paid || '—')) + td('Последний вход', esc(a.last_signin || '—')) + td('Plus до', esc(a.plus_until || '—')) + '</tr>';
  }
  function accounts() {
    var a = S.acc;
    if (!a) return '';
    var k = ownerKey(), banned = a.accounts.filter(function (x) { return x.banned; }).length;
    var keyLine = '<p class="adm-key">' + ic('block') + '<span>' + (k ? 'Ключ владельца введён в этой вкладке: блокировка работает. <button class="linkbtn" type="button" data-forget>Забыть ключ</button>'
      : 'Блокировка аккаунта требует ключа владельца (ADMIN_TOKEN): его спросят при первой блокировке и запомнят только в этой вкладке.') + '</span></p>';
    return panel('accounts', 'Аккаунты', 'Все <b>аккаунты</b>',
      '<p class="note">Всего аккаунтов: <b>' + num(a.total) + '</b>. Оплачено заказов: <b>' + num(a.paid_orders) + '</b> на <b>$' + num(a.paid_usd) + '</b>.' + (banned ? ' Заблокировано среди показанных: <b>' + num(banned) + '</b>.' : '') +
      (a.total > a.accounts.length ? ' Показаны ' + num(a.accounts.length) + ' самых новых; поиск ищет по всем.' : '') + '</p>' + keyLine +
      '<p class="dirfind"><input type="search" id="acc-find" placeholder="Почта или компания" aria-label="Найти аккаунт"></p>' +
      '<div class="tablewrap rkwrap"><table class="adm-acc rkt"><tr><th>Почта</th><th>Регистрация</th><th>Компания</th><th>Кто</th><th>Почта подтверждена</th><th>Вакансии</th><th>Страниц компании</th><th>Резюме</th><th>Оплатил (заказов)</th><th>Последняя оплата</th><th>Последний вход</th><th>Plus до</th></tr>' +
      a.accounts.map(accRow).join('') + '</table></div><p class="note" id="acc-none" hidden>Нет аккаунтов с такими буквами.</p>');
  }
  function logPart() {
    if (!S.log) return '';
    var rows = (S.log.log || []).map(function (l) {
      var what, detail;
      if (l.action === 'job_edit') {
        what = 'Правка вакансии ' + (l.title ? '«' + esc(l.title) + '»' + (l.company ? ', ' + esc(l.company) : '') : esc(l.target));
        detail = (l.fields || []).map(function (f) {
          var name = FIELD[f.field] || esc(f.field);
          if (f.field === 'description') return name + ': текст изменён (' + num(String(f.from || '').length) + ' → ' + num(String(f.to || '').length) + ' знаков)';
          if (typeof f.to === 'boolean') return name + ': ' + (f.to ? 'да' : 'нет');
          return name + ': «' + esc(f.from || '—') + '» → «' + esc(f.to || '—') + '»';
        }).join('<br>');
      } else {
        what = (l.action === 'ban' ? 'Блокировка ' : 'Разблокировка ') + esc(l.email || l.target);
        detail = l.reason ? 'Причина: ' + esc(l.reason) : 'без причины';
      }
      return '<tr><td>' + what + '</td>' + td('Когда', when(l.at)) + td('Кто', esc(l.by)) + td('Что изменено', detail) + '</tr>';
    }).join('');
    return panel('log', 'Журнал', 'Что сделано <b>вручную</b>', rows ? '<p class="note">Правки вакансий, блокировки и разблокировки: кто, когда и что именно, новые сверху (200 последних).</p>' +
      '<div class="tablewrap rkwrap"><table class="adm-log rkt"><tr><th>Действие</th><th>Когда</th><th>Кто</th><th>Что изменено</th></tr>' + rows + '</table></div>' : '<p class="note">Пока ничего: здесь появятся правки вакансий и блокировки.</p>');
  }

  function draw() {
    var ov = S.ov, aud = S.aud, html = '';
    html += (note ? '<div class="banner ok" role="status">' + note + '</div>' : '');
    html += '<div class="pillrow" role="navigation" aria-label="Разделы"><a href="#queue">Очередь<i>' + num(S.jobs.length) + '</i></a><a href="#claims">Заявки на страницу<i>' + num(S.claims.length) + '</i></a><a href="#reports">Жалобы<i>' + num(S.reports.length) + '</i></a>' +
      '<a href="#posted">Вакансии</a><a href="#orders">Заказы</a>' + (S.acc ? '<a href="#accounts">Аккаунты<i>' + num(S.acc.total) + '</i></a>' : '') + (S.log ? '<a href="#log">Журнал</a>' : '') + '</div>';
    html += '<div class="ov-grid">' + tile(num(S.jobs.length), 'вакансий ждут проверки') + tile(num(S.claims.length), 'заявок на страницу компании') + tile(num(S.reports.length), 'жалоб без решения') +
      (ov ? tile(num(ov.users), 'аккаунтов') + tile(num(ov.live_jobs), 'размещённых вакансий на сайте') + tile('$' + num(ov.revenue_usd), 'выручка, оплачено заказов: ' + num(ov.paid_orders)) : '') +
      (aud && aud.accounts ? tile(num(aud.accounts.job_seekers), 'соискателей') + tile(num(aud.accounts.employers), 'работодателей') : '') +
      (aud && aud.alerts ? tile(num(aud.alerts.active), 'подписок на вакансии') : '') + '</div>';
    html += panel('queue', 'Очередь', 'Вакансии <b>на проверке</b>', S.jobs.length ? S.jobs.map(jobCard).join('') :
      '<p class="note">Очередь пуста. Новая вакансия от неподтверждённого работодателя появится здесь.</p>', F.job_edit && S.jobs.length ? 'Вакансию можно поправить прямо здесь, потом одобрить или отклонить.' : '');
    html += panel('claims', 'Заявки', 'Заявки на <b>страницу компании</b>', S.claims.length ? S.claims.map(claimCard).join('') : '<p class="note">Заявок нет.</p>');
    html += panel('reports', 'Жалобы', 'Жалобы <b>на вакансии</b>', S.reports.length ? S.reports.map(reportCard).join('') : '<p class="note">Жалоб нет.</p>');
    if (ov && ov.recent_jobs && ov.recent_jobs.length) html += panel('posted', 'Вакансии', 'Размещённые <b>вакансии</b>',
      '<p class="note">Название открывает страницу вакансии на сайте, компания — страницу компании. Обе появляются после ближайшего обновления сайта (обычно в течение часа после одобрения).' +
      (F.job_edit ? ' «Править» меняет текст вакансии на месте: на сайте он обновится при ближайшем обновлении.' : '') + '</p>' +
      '<div class="tablewrap rkwrap"><table class="adm-jobs rkt"><tr><th>Вакансия</th><th>Компания</th><th>Аккаунт</th><th>Дата</th><th>Статус</th><th>Просмотры</th><th>Клики</th><th></th></tr>' +
      ov.recent_jobs.map(function (j) {
        var on = j.status === 'live', editable = F.job_edit && ['live', 'review', 'closed', 'expired'].indexOf(j.status) >= 0;
        return '<tr class="adm-row"><td>' + (j.page ? out(j.page, j.title) : esc(j.title)) + (j.edits ? ' <span class="adm-tag">изменена ' + num(j.edits) + '×</span>' : '') + '</td>' +
          td('Компания', j.company_page ? out(j.company_page, j.company) : esc(j.company)) + td('Аккаунт', esc(j.email || '')) + td('Дата', dts(j.created_at)) +
          td('Статус', esc(st(j.status)) + (on && j.until ? ' до ' + esc(j.until) : '')) + td('Просмотры', num(j.views)) + td('Клики', num(j.applies)) +
          '<td class="adm-ra">' + (j.apply_url ? '<a href="' + esc(j.apply_url) + '" target="_blank" rel="noopener nofollow">ссылка отклика</a> ' : '') +
          (editable ? '<button class="btn ghost sm" type="button" data-edit="' + esc(j.id) + '">' + ic('edit') + 'Править</button> ' : '') +
          (on ? '<button class="btn ghost sm" type="button" style="margin:0" data-job-rm="' + esc(j.id) + '">Снять с сайта</button>' : '') + '</td></tr>';
      }).join('') + '</table></div>');
    if (ov && ov.recent_orders && ov.recent_orders.length) html += panel('orders', 'Заказы', 'Заказы <b>и оплаты</b>', '<div class="tablewrap rkwrap"><table class="rkt"><tr><th>Продукт</th><th>Дата</th><th>Аккаунт</th><th>Для</th><th>Сумма</th><th>Статус</th><th>Оплачен</th></tr>' +
      ov.recent_orders.map(function (o) { return '<tr><td>' + esc(o.product) + '</td>' + td('Дата', dts(o.created_at)) + td('Аккаунт', esc(o.email || '')) + td('Для', esc(o.label || '—')) + td('Сумма', o.amount_usd ? '$' + num(o.amount_usd) : (o.credits ? num(o.credits) + ' кредитов' : '$0')) + td('Статус', esc(st(o.status))) + td('Оплачен', dts(o.paid_at) || '—') + '</tr>'; }).join('') + '</table></div>');
    else html += panel('orders', 'Заказы', 'Заказы <b>и оплаты</b>', '<p class="note">Заказов пока нет.</p>');
    html += accounts();
    html += logPart();
    root.innerHTML = html;
    if (note) {                                  // what was just done is said at the top: brought into view if the page was scrolled past it
      var said = root.querySelector('.banner.ok'), top = said ? said.getBoundingClientRect().top : 0;
      if (said && (top < 70 || top > window.innerHeight - 80)) window.scrollTo(0, Math.max(0, window.scrollY + top - 90));
    }
    note = '';
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

  /* ---- a window over the page (<dialog>): the edit of a job, a block and its lifting. Escape or "Отмена" closes it, and the focus
     goes back to the button that opened it. ---- */
  var dlg = null, opener = null;
  function windowWith(html, from) {
    if (!dlg) {
      dlg = document.createElement('dialog'); dlg.className = 'adm-dlg'; dlg.setAttribute('aria-labelledby', 'adm-dlg-h');
      document.body.appendChild(dlg);
      dlg.addEventListener('click', function (ev) { if (ev.target.closest && ev.target.closest('[data-close]')) shut(); });      // not a click beside it: a half-made edit is not lost by a stray click
      dlg.addEventListener('close', function () { if (opener && document.body.contains(opener)) { try { opener.focus(); } catch (e) {} } });
    }
    opener = from || null;
    dlg.innerHTML = '<div class="adm-dlg-in">' + html + '</div>';
    if (!dlg.open) { if (dlg.showModal) dlg.showModal(); else dlg.setAttribute('open', ''); }
    var first = dlg.querySelector('input:not([type=hidden]):not([type=radio]), textarea'); if (first) { try { first.focus(); } catch (e) {} }
    return dlg;
  }
  function shut() { if (dlg && dlg.open) { if (dlg.close) dlg.close(); else { dlg.removeAttribute('open'); } } }
  var closeBtn = '<button class="btn ghost" type="button" data-close>Отмена</button>';
  function fail(form, e, field) {
    var box = form.querySelector('.acc-err');
    box.innerHTML = why(e); box.hidden = false;
    Array.prototype.forEach.call(form.querySelectorAll('[aria-invalid]'), function (x) { x.removeAttribute('aria-invalid'); });
    var bad = field && form.elements[field];
    if (bad && bad.focus) { if (bad.setAttribute) bad.setAttribute('aria-invalid', 'true'); try { bad.focus(); } catch (x) {} } else box.scrollIntoView({ block: 'nearest' });
  }
  function busy(form, on) { Array.prototype.forEach.call(form.querySelectorAll('button, input, textarea'), function (b) { b.disabled = on; }); }

  // the edit of a job: what the employer's form has, checked by the server with the same rules; then approved or rejected as before
  var MODE = [['', 'В офисе'], ['hybrid', 'Гибрид'], ['remote', 'Удалённо']];
  function openEdit(id, from) {
    windowWith('<p class="note">Загрузка вакансии…</p><div class="adm-dlg-act">' + closeBtn + '</div>', from);
    api('GET', '/api/admin/jobs/' + encodeURIComponent(id)).then(function (r) { drawEdit(r.job, from); },
      function (e) { windowWith('<div class="banner">' + why(e) + '</div><div class="adm-dlg-act">' + closeBtn + '</div>', from); });
  }
  function drawEdit(j, from) {
    var mode = j.remote ? 'remote' : j.hybrid ? 'hybrid' : '';
    var field = function (name, label, input, hint) { return '<label class="adm-f"><span>' + label + '</span>' + input + (hint ? '<small>' + hint + '</small>' : '') + '</label>'; };
    var hist = (j.edits || []).map(function (l) {
      return '<li><b>' + when(l.at) + '</b>, ' + esc(l.by) + ': ' + (l.fields || []).map(function (f) { return FIELD[f.field] || esc(f.field); }).join(', ') + '</li>';
    }).join('');
    var d = windowWith('<form class="adm-edit" novalidate><p class="sec-label">Правка вакансии · ' + esc(st(j.status)) + '</p><h2 class="tw" id="adm-dlg-h">' + esc(j.company) + ': <b>' + esc(j.title) + '</b></h2>' +
      '<p class="adm-dlg-sub">Аккаунт ' + esc(j.email || '') + '. Правила те же, что в форме работодателя; новая ссылка отклика открывается и проверяется. ' +
      (j.status === 'review' ? 'После правки вакансия по-прежнему ждёт решения: одобрите или отклоните её как обычно.' : 'Вакансия останется на своём месте, текст на сайте обновится при ближайшем обновлении.') + '</p>' +
      field('title', 'Название', '<input name="title" required minlength="4" maxlength="120" value="' + esc(j.title) + '">') +
      '<div class="adm-2">' + field('location', 'Место', '<input name="location" maxlength="120" value="' + esc(j.location || '') + '" placeholder="Berlin, Germany">') +
      field('salary', 'Оплата', '<input name="salary" maxlength="60" value="' + esc(j.salary || '') + '" placeholder="$90K – $110K">', 'Как в объявлении, до 60 знаков') + '</div>' +
      '<fieldset class="adm-f adm-mode"><legend>Формат работы</legend>' + MODE.map(function (m) {
        return '<label><input type="radio" name="mode" value="' + m[0] + '"' + (mode === m[0] ? ' checked' : '') + '><span>' + m[1] + '</span></label>';
      }).join('') + '</fieldset>' +
      field('apply_url', 'Ссылка отклика', '<input name="apply_url" type="url" required maxlength="500" value="' + esc(j.apply_url) + '" placeholder="https://">', 'На сайте компании или в системе найма (Greenhouse, Lever, Ashby…)') +
      field('description', 'Описание', '<textarea name="description" required minlength="80" maxlength="1500" rows="9">' + esc(j.description || '') + '</textarea>', '<span data-count>' + num((j.description || '').length) + '</span> из 1 500 знаков, не меньше 80') +
      '<p class="acc-err" role="alert" hidden></p><div class="adm-dlg-act"><button class="btn primary" type="submit">Сохранить правку</button>' + closeBtn + '</div>' +
      (hist ? '<details class="adm-hist"><summary>История правок: ' + (j.edits || []).length + '</summary><ol>' + hist + '</ol></details>' : '') + '</form>', from);
    var form = d.querySelector('form'), area = form.elements.description, count = form.querySelector('[data-count]');
    area.addEventListener('input', function () { count.textContent = num(area.value.length); });
    form.addEventListener('submit', function (ev) {
      ev.preventDefault();
      var v = function (n) { return form.elements[n].value.trim(); }, m = (form.querySelector('input[name=mode]:checked') || {}).value || '';
      var now = { title: v('title'), location: v('location'), salary: v('salary'), apply_url: v('apply_url'), description: area.value.trim(), remote: m === 'remote', hybrid: m === 'hybrid' };
      var was = { title: j.title, location: j.location || '', salary: j.salary || '', apply_url: j.apply_url, description: j.description || '', remote: !!j.remote, hybrid: !!j.hybrid };
      // the browser's own checks first, said in Russian (the server checks the same again)
      var local = now.title.length < 4 || now.title.length > 120 ? ['title', 'Название: от 4 до 120 знаков.'] : now.description.length < 80 || now.description.length > 1500 ? ['description', 'Описание: от 80 до 1 500 знаков.']
        : !/^https:\/\/\S+\.\S+/.test(now.apply_url) ? ['apply_url', 'Ссылка отклика должна начинаться с https://'] : null;
      if (local) return fail(form, { message: local[1] }, local[0]);
      var send = {};
      Object.keys(now).forEach(function (k) { if (now[k] !== was[k]) send[k] = now[k]; });
      if (send.remote === false && send.hybrid === true) delete send.remote;       // one switched on switches the other off on the server
      if (send.hybrid === false && send.remote === true) delete send.hybrid;
      if (!Object.keys(send).length) return fail(form, { message: 'Ничего не изменилось.' });
      busy(form, true);
      api('POST', '/api/admin/jobs/' + encodeURIComponent(j.id) + '/edit', send).then(function (r) {
        shut();
        var names = (r.changed || []).map(function (k) { return FIELD[k] || k; }).join(', ');
        note = (r.changed && r.changed.length ? 'Правка сохранена: ' + esc(names) + '. ' : 'Ничего не изменилось. ') +
          (j.status === 'review' ? 'Вакансия ждёт решения: одобрите или отклоните её.' : 'На сайте текст обновится при ближайшем обновлении.') +
          (r.reasons && r.reasons.length ? ' Проверки сайта говорят: ' + ru(r.reasons.join('; ')) + '.' : '');
        return load();
      }, function (e) { busy(form, false); fail(form, e, ['title', 'location', 'salary', 'description', 'apply_url'].indexOf(e.code) >= 0 ? e.code : e.code === 'rejected' ? 'description' : null); });
    });
  }

  // a block: what it does, a reason, the owner's key when this tab has none, and one more press to confirm
  function keyField(k) {
    return k ? '' : '<label class="adm-f"><span>Ключ владельца (ADMIN_TOKEN)</span><input name="key" type="password" autocomplete="off" spellcheck="false" required>' +
      '<small>Блокировать и снимать блокировку может только ключ владельца. Он лежит на сервере в /etc/hrn-api/api.env и в вашем менеджере паролей. Здесь он хранится только в этой вкладке, до её закрытия.</small></label>';
  }
  function openBan(b) {
    var id = b.getAttribute('data-ban'), email = b.getAttribute('data-email') || id, jobs = b.getAttribute('data-jobs'), k = ownerKey();
    var d = windowWith('<form class="adm-ban-f" novalidate><p class="sec-label bad">Блокировка аккаунта</p><h2 class="tw" id="adm-dlg-h">Заблокировать <b>' + esc(email) + '</b>?</h2>' +
      '<ul class="adm-conseq"><li>вход закрывается, все его сессии завершаются;</li><li>его вакансии снимаются с сайта' + (jobs && jobs !== '0' ? ' (сейчас на сайте и на проверке: ' + esc(jobs) + ')' : '') + ', оплаченное продвижение выключается;</li>' +
      '<li>его страницы компаний и названия освобождаются, резюме уходит из базы;</li><li>жалобы на его вакансии считаются верными.</li></ul>' +
      '<p class="adm-dlg-sub">' + (F.unban ? 'Блокировку можно снять в списке аккаунтов, но снятые вакансии не вернутся: их размещают заново.' : 'Снять блокировку с этой страницы пока нельзя: это появится после обновления сервера.') + '</p>' +
      '<label class="adm-f"><span>Причина</span><input name="reason" required minlength="3" maxlength="300" placeholder="Например: просил деньги за обучение"><small>' +
      (F.ban_reason ? 'Видна только вам: в списке аккаунтов и в журнале.' : 'Сервер начнёт хранить причину после своего обновления; сейчас она нужна только для подтверждения.') + '</small></label>' + keyField(k) +
      '<p class="acc-err" role="alert" hidden></p><div class="adm-dlg-act"><button class="btn adm-danger" type="submit">' + ic('block') + 'Да, заблокировать</button>' + closeBtn + '</div></form>', b);
    var form = d.querySelector('form');
    form.addEventListener('submit', function (ev) {
      ev.preventDefault();
      var reason = form.elements.reason.value.trim(), key = k || (form.elements.key ? form.elements.key.value.trim() : '');
      if (reason.length < 3 || reason.length > 300) return fail(form, { message: 'Причина: от 3 до 300 знаков.' }, 'reason');
      if (!key) return fail(form, { message: 'Нужен ключ владельца.' }, 'key');
      busy(form, true);
      call(key, 'POST', '/api/admin/accounts/' + encodeURIComponent(id) + '/ban', { reason: reason }).then(function (r) {
        keepKey(key); shut();
        note = 'Аккаунт ' + esc(email) + ' заблокирован' + (r && typeof r.jobs_taken_down === 'number' ? ', снято вакансий: ' + num(r.jobs_taken_down) : '') + '.';
        return load();
      }, function (e) {
        busy(form, false);
        if (e.status === 403 && !k) return fail(form, { message: 'Ключ владельца не подошёл. Проверьте его и попробуйте ещё раз.' }, 'key');
        if (e.status === 403) { keepKey(''); return fail(form, { message: 'Ключ владельца из этой вкладки больше не подходит: закройте окно и введите его заново.' }); }
        fail(form, e, e.code === 'reason' ? 'reason' : null);
      });
    });
  }
  function openUnban(b) {
    var id = b.getAttribute('data-unban'), email = b.getAttribute('data-email') || id, k = ownerKey();
    var d = windowWith('<form class="adm-ban-f" novalidate><p class="sec-label">Снять блокировку</p><h2 class="tw" id="adm-dlg-h">Разблокировать <b>' + esc(email) + '</b>?</h2>' +
      '<p class="adm-dlg-sub">Аккаунт снова сможет входить и размещать вакансии. Вакансии, снятые блокировкой, на сайт не вернутся: работодатель размещает их заново (то же название — через 30 дней после блокировки). ' +
      'Страницы компаний он заявляет снова, резюме возвращает в базу сам.</p>' +
      '<label class="adm-f"><span>Почему снимаете (для журнала, можно оставить пустым)</span><input name="reason" maxlength="300"></label>' + keyField(k) +
      '<p class="acc-err" role="alert" hidden></p><div class="adm-dlg-act"><button class="btn primary" type="submit">' + ic('open') + 'Да, разблокировать</button>' + closeBtn + '</div></form>', b);
    var form = d.querySelector('form');
    form.addEventListener('submit', function (ev) {
      ev.preventDefault();
      var reason = form.elements.reason.value.trim(), key = k || (form.elements.key ? form.elements.key.value.trim() : '');
      if (reason && reason.length < 3) return fail(form, { message: 'Причина: от 3 до 300 знаков или пусто.' }, 'reason');
      if (!key) return fail(form, { message: 'Нужен ключ владельца.' }, 'key');
      busy(form, true);
      call(key, 'POST', '/api/admin/accounts/' + encodeURIComponent(id) + '/unban', reason ? { reason: reason } : {}).then(function () {
        keepKey(key); shut(); note = 'Блокировка с ' + esc(email) + ' снята: аккаунт снова может входить.'; return load();
      }, function (e) {
        busy(form, false);
        if (e.status === 403 && !k) return fail(form, { message: 'Ключ владельца не подошёл. Проверьте его и попробуйте ещё раз.' }, 'key');
        if (e.status === 403) { keepKey(''); return fail(form, { message: 'Ключ владельца из этой вкладки больше не подходит: закройте окно и введите его заново.' }); }
        fail(form, e);
      });
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
      var go = function () { act(b, function () { return api('POST', '/api/admin/jobs/' + b.getAttribute('data-job-rm') + '/remove'); }, 'Вакансия снята с сайта: пропадёт при ближайшем обновлении, в течение часа.'); };
      if (!b.closest('.adm-row')) return go();
      H.sure(b, 'Снять эту вакансию с сайта? Она пропадёт при ближайшем обновлении, работодатель увидит её в кабинете как снятую.', 'Да, снять').then(function (ok) { if (ok) go(); }); }); });
    each('[data-edit]', function (b) { b.addEventListener('click', function () { openEdit(b.getAttribute('data-edit'), b); }); });
    each('[data-ban]', function (b) { b.addEventListener('click', function () { openBan(b); }); });
    each('[data-unban]', function (b) { b.addEventListener('click', function () { openUnban(b); }); });
    each('[data-forget]', function (b) { b.addEventListener('click', function () { keepKey(''); note = 'Ключ владельца забыт в этой вкладке.'; draw(); }); });
  }

  if (!token) return gate('Сначала войдите в свой аккаунт на сайте, потом откройте эту страницу снова.', true);
  root.innerHTML = '<p class="note">Загрузка…</p>';
  load().catch(function (e) {
    if (e.status === 401) gate('Сессия закончилась. Войдите в аккаунт заново.', true);
    else if (e.status === 403) gate('Этот аккаунт не модератор. Страница работает только для аккаунта владельца сайта: выйдите из этого аккаунта, зарегистрируйтесь или войдите под адресом администратора (он задан на сервере в ADMIN_EMAILS), подтвердите почту по ссылке из письма и откройте эту страницу снова.', true);
    else gate(esc(e.message), false);
  });
})();
