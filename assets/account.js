/* Your account, for job seekers and employers alike: sign in (email and password, or Google), job alerts, saved jobs on every device,
   your resume for employers (only if you tick it), and for employers: free posting, what a job brought, company pages, the team,
   promotions and receipts. Everything you keep here can be downloaded or deleted from the last section. Talks to the API in data-api;
   the rules behind each part are in server/README.md. Nothing here needs a person on our side: a paid order switches itself on. */
(function () {
  var root = document.getElementById('acc');
  if (!root || !window.HRN) return;
  var H = window.HRN, esc = H.esc, API = root.getAttribute('data-api').replace(/\/+$/, '');
  var D = JSON.parse(document.getElementById('acc-data').textContent);
  var token = H.get('hrn_token', ''), me = null, pub = { products: [], payments: 'off' }, products = {}, S = {}, notice = '';
  var SYNC_KEYS = ['hrn_jobs', 'hrn_saved', 'hrn_searches', 'hrn_follow', 'hrn_hidden', 'hrn_mute'];   // what "My jobs" keeps in this browser

  function api(method, path, data) {
    var headers = {};
    if (data) headers['Content-Type'] = 'application/json';
    if (token) headers.Authorization = 'Bearer ' + token;
    return fetch(API + path, { method: method, headers: headers, body: data ? JSON.stringify(data) : undefined }).then(function (r) {
      return r.json().catch(function () { return {}; }).then(function (b) {
        if (r.ok) return b;
        var err = new Error(b.message || 'Something went wrong. Please try again.'); err.code = b.error; err.status = r.status; err.body = b; throw err;
      });
    }, function () { throw new Error('Could not reach the server. Check your connection and try again.'); });
  }
  var quiet = function (p, dflt) { return p.catch(function () { return dflt; }); };
  function field(label, name, attrs, hint) {
    return '<label class="fld">' + label + '<input name="' + name + '" ' + (attrs || 'type="text"') + '>' + (hint ? '<span class="hint">' + hint + '</span>' : '') + '</label>';
  }
  function values(form) {
    var out = {};
    Array.prototype.forEach.call(form.elements, function (el) {
      if (!el.name) return;
      if (el.type === 'checkbox' && el.hasAttribute('data-many')) { (out[el.name] = out[el.name] || []); if (el.checked) out[el.name].push(el.value); }
      else out[el.name] = el.type === 'checkbox' ? el.checked : el.value.trim();
    });
    return out;
  }
  // run an action from a form: lock the button, show the server's message under the form if it fails
  function submit(form, work) {
    if (!form) return;
    form.addEventListener('submit', function (ev) {
      ev.preventDefault();
      var btn = ev.submitter || form.querySelector('button[type=submit]'), box = form.querySelector('.acc-err'), label = btn.textContent;
      if (box) box.hidden = true; btn.disabled = true; btn.textContent = 'One moment…';
      Promise.resolve().then(function () { return work(values(form), btn); }).catch(function (err) {
        if (box) { box.textContent = err.message; box.hidden = false; } else alert(err.message);
        if (err.status === 401 && token) signOut();
      }).then(function () { btn.disabled = false; btn.textContent = label; });
    });
  }
  function on(sel, fn) { Array.prototype.forEach.call(root.querySelectorAll(sel), function (el) { el.addEventListener('click', function () { fn(el); }); }); }
  var money = function (n) { return '$' + Number(n).toLocaleString('en-US'); };
  var state = function (s) { return '<span class="state ' + esc(s) + '">' + esc(s) + '</span>'; };
  var sec = function (title, inner, id) { return '<section class="sec"' + (id ? ' id="' + id + '"' : '') + '><div class="sec-head"><h2>' + title + '</h2></div>' + inner + '</section>'; };
  var err = '<p class="acc-err" role="alert" hidden></p>';
  var cleanUrl = function () { try { history.replaceState(null, '', location.pathname); } catch (e) {} };

  /* ---------- signed out: create an account, sign in, Google, a new password ---------- */
  function drawAuth(mode) {
    var up = mode === 'up', google = pub.google === 'on';
    if (mode === 'forgot') {
      root.innerHTML = '<div class="card acc-auth">' + (notice ? '<div class="banner">' + notice + '</div>' : '') + '<h2 style="margin-top:0">Set a new password</h2><form novalidate>' +
        field('Your email', 'email', 'type="email" autocomplete="email" required') + err + '<button class="btn primary lg" type="submit" style="width:100%">Send me a link</button></form>' +
        '<p class="note"><a href="#" data-mode="in">Back to sign in</a></p></div>';
      submit(root.querySelector('form'), function (v) { return api('POST', '/api/auth/reset/request', v).then(function (r) { notice = esc(r.message); drawAuth('in'); }); });
    } else {
      root.innerHTML = '<div class="card acc-auth">' + (notice ? '<div class="banner">' + notice + '</div>' : '') + '<div class="tabs" role="tablist" style="margin-top:0">' +
        '<button class="tab" type="button" role="tab" data-mode="up" aria-selected="' + up + '">Create account</button>' +
        '<button class="tab" type="button" role="tab" data-mode="in" aria-selected="' + !up + '">Sign in</button></div>' +
        (google ? '<button class="btn lg" type="button" id="acc-google" style="width:100%;margin:4px 0 14px">Continue with Google</button><p class="note" style="text-align:center;margin:0 0 10px">or with your email</p>' : '') +
        '<form novalidate>' + field('Email', 'email', 'type="email" autocomplete="email" required', up ? 'To post jobs for your company, use your work address (you@yourcompany.com).' : '') +
        field('Password', 'password', 'type="password" autocomplete="' + (up ? 'new-password' : 'current-password') + '" required minlength="8"', up ? 'At least 8 characters.' : '') +
        (up ? field('Company (optional)', 'company', 'type="text" autocomplete="organization" maxlength="80"') : '') +
        err + '<button class="btn primary lg" type="submit" style="width:100%">' + (up ? 'Create account' : 'Sign in') + '</button></form>' +
        '<p class="note" style="margin:14px 0 0">' + (up ? 'Free. No card, no phone number. We send one link to confirm the address.' : '<a href="#" data-mode="forgot">Forgot the password?</a>') + '</p></div>';
      submit(root.querySelector('form'), function (v) {
        return api('POST', up ? '/api/auth/signup' : '/api/auth/login', v).then(function (r) { token = r.token; H.set('hrn_token', token); notice = ''; return load(); });
      });
      var g = document.getElementById('acc-google');
      if (g) g.addEventListener('click', function () {
        g.disabled = true;
        api('POST', '/api/auth/google/start').then(function (r) { try { sessionStorage.setItem('hrn_google', r.secret); } catch (e) {} location.href = r.url; }, function (e) { g.disabled = false; alert(e.message); });
      });
    }
    Array.prototype.forEach.call(root.querySelectorAll('[data-mode]'), function (t) { t.addEventListener('click', function (ev) { ev.preventDefault(); drawAuth(t.getAttribute('data-mode')); }); });
  }
  function drawReset(resetToken) {
    root.innerHTML = '<div class="card acc-auth"><h2 style="margin-top:0">Choose a new password</h2><form novalidate>' +
      field('New password', 'password', 'type="password" autocomplete="new-password" required minlength="8"', 'At least 8 characters. Every browser signed in to the account is signed out.') +
      err + '<button class="btn primary lg" type="submit" style="width:100%">Save the password</button></form></div>';
    submit(root.querySelector('form'), function (v) {
      return api('POST', '/api/auth/reset/confirm', { token: resetToken, password: v.password }).then(function () { notice = 'Your new password is saved. Sign in with it.'; token = ''; H.set('hrn_token', ''); drawAuth('in'); });
    });
  }
  function signOut() {
    api('POST', '/api/auth/logout').catch(function () {});
    token = ''; me = null; H.set('hrn_token', ''); notice = ''; drawAuth('in');
  }

  /* ---------- signed in ---------- */
  function load() {
    return Promise.all([api('GET', '/api/me'), api('GET', '/api/public/products')]).then(function (r) {
      me = r[0].user; pub = r[1]; products = {}; pub.products.forEach(function (p) { products[p.id] = p; });
      var emp = me.posts_as.length > 0, talent = pub.talent === 'on';
      return Promise.all([quiet(api('GET', '/api/alerts'), { alerts: [] }), me.confirmed ? quiet(api('GET', '/api/sync'), { data: null }) : { data: null },
        talent ? quiet(api('GET', '/api/talent/profile'), { profile: null }) : null, talent ? quiet(api('GET', '/api/talent/requests'), { requests: [] }) : null,
        quiet(api('GET', '/api/jobs'), { jobs: [] }), quiet(api('GET', '/api/placements'), { placements: [] }), quiet(api('GET', '/api/orders'), { orders: [] }),
        emp ? quiet(api('GET', '/api/claims'), { claims: [] }) : null, emp ? quiet(api('GET', '/api/team'), { members: [] }) : null, quiet(api('GET', '/api/domain'), {}),
        talent && emp ? quiet(api('GET', '/api/talent/sent'), { requests: [], credits: 0 }) : null]);
    }).then(function (r) {
      S = { alerts: r[0].alerts, sync: r[1], talent: r[2], incoming: r[3] ? r[3].requests : [], jobs: r[4].jobs, placements: r[5].placements, orders: r[6].orders,
        claims: r[7] ? r[7].claims : [], team: r[8], domain: r[9], sent: r[10] };
      draw();
    });
  }

  function productCard(id, fields, extra) {
    var p = products[id]; if (!p) return '';
    return '<form class="acc-card" data-product="' + id + '" novalidate><p class="pname">' + esc(p.name) + '</p><p class="price">' + money(p.usd) + '</p>' +
      '<p class="what">' + esc(D.what[p.name] || '') + '</p>' + fields + err +
      '<button class="btn primary" type="submit"' + (pub.payments === 'off' ? ' disabled' : '') + '>Continue to payment</button>' +
      // what employers hate most on other job sites is a charge they did not expect: say plainly that this is one payment and nothing renews
      '<p class="note">One payment' + (p.days ? ' for ' + p.days + ' days' : '') + '. Nothing renews: no trial, no subscription, no card kept on file.</p>' + (extra || '') + '</form>';
  }

  // job alerts, saved jobs on every device, the resume for employers
  function seekerPart() {
    var html = sec('Your job alerts', (S.alerts.length ? '<div class="card" style="padding:0">' + S.alerts.map(function (a) {
      return '<div class="trow"><span>' + state(a.status === 'pending' ? 'confirm in your inbox' : a.freq) + '</span><div class="main"><a class="tt" href="' + esc(a.search) + '">' + esc(a.alert) + '</a><span class="js">' +
        (a.letters ? a.letters + ' letter' + (a.letters > 1 ? 's' : '') + ' so far' : 'no letter yet') + ' · since ' + esc(a.created) + '</span></div><div class="ctl"><button class="btn ghost sm" type="button" style="margin:0" data-alert-del="' + esc(a.id) + '">Delete</button></div></div>';
    }).join('') + '</div>' : '<p>No alerts yet. On any <a href="' + esc(D.site) + '/jobs/">search</a>, category or place page, “Free job alerts” sends you its new jobs once a day or once a week.</p>') +
      '<p class="note">One letter a day at most, whatever alerts you have; every letter has a one-click unsubscribe.</p>', 'alerts');

    var synced = S.sync && S.sync.updated ? new Date(S.sync.updated * 1000).toISOString().slice(0, 10) : '';
    html += sec('Saved jobs on every device', '<p>Your saved jobs, application statuses, saved searches and followed companies live in this browser. Keep a copy in your account to have them on your phone and computer alike.' +
      (synced ? ' Last copy: ' + esc(synced) + '.' : '') + '</p><p><button class="btn" type="button" id="sync-up">Copy this browser’s lists to my account</button> ' +
      (synced ? '<button class="btn ghost" type="button" id="sync-down">Bring my account’s lists to this browser</button>' : '') + '</p>', 'sync');

    if (pub.talent === 'on' && S.talent) {
      var t = S.talent.profile, local = H.get('hrn_resume', null), inner;
      if (!t) {
        inner = !local ? '<p>Make your resume in the <a href="' + esc(D.site) + '/resume/">free resume builder</a> first; then come back here if you want employers to find it.</p>' :
          '<form class="card" id="talent-on" novalidate><p>Your resume stays in this browser unless you tick the box below. Employers then see it without your name, email, phone or links, and get your name and contact details only if you accept their request.</p>' +
          '<label class="check"><input type="checkbox" name="consent" required> <span>' + esc(S.talent.consent_text) + '</span></label>' + talentFields(null) + err +
          '<button class="btn primary" type="submit">Let employers find my resume</button></form>';
      } else {
        inner = '<div class="card"><p><strong>' + (t.paused ? 'Paused: employers cannot find it.' : 'Employers can find your resume.') + '</strong> Since ' + esc(t.consented) + ', updated ' + esc(t.updated) + '.</p>' +
          '<p class="note">Employers see: ' + esc(t.as_employers_see.headline || 'your headline') + ' · ' + esc(t.as_employers_see.skills.slice(0, 8).join(', ')) + (t.as_employers_see.name ? ' · ' + esc(t.as_employers_see.name) : ' · no name') + '.</p>' +
          '<form id="talent-set" novalidate>' + talentFields(t) + err + '<button class="btn" type="submit">Save these settings</button> ' +
          (local ? '<button class="btn ghost" type="button" id="talent-update">Update it with my current resume</button> ' : '') +
          '<button class="btn ghost" type="button" id="talent-pause">' + (t.paused ? 'Show it again' : 'Pause') + '</button> <button class="btn ghost" type="button" id="talent-del">Delete it for good</button></form></div>';
      }
      if (S.incoming.length) inner += '<h3>Employers who asked to contact you</h3><div class="card" style="padding:0">' + S.incoming.map(function (q) {
        return '<div class="trow"><span>' + state(q.status) + '</span><div class="main"><strong>' + esc(q.company) + '</strong> <span class="js">' + esc(q.domain) + ' · ' + esc(q.received) + '</span><p style="margin:6px 0">' + esc(q.message) + '</p>' +
          (q.job_url ? '<a href="' + esc(q.job_url) + '" rel="noopener">The job</a>' : '') + '</div><div class="ctl">' + (q.status === 'sent' ? '<button class="btn sm" type="button" data-q="accept" data-id="' + esc(q.id) + '">Accept</button> <button class="btn ghost sm" type="button" data-q="decline" data-id="' + esc(q.id) + '">Decline</button>' : '') + '</div></div>';
      }).join('') + '</div><p class="note">Accepting gives that employer your name and contact details. Declining, or not answering in 14 days, tells it nothing about you.</p>';
      html += sec('Your resume for employers', inner, 'talent');
    }
    return html;
  }
  function talentFields(t) {
    var has = function (list, v) { return (list || []).indexOf(v) >= 0; };
    return '<div class="acc-two"><label class="fld">Level<select name="level"><option value="">Not said</option>' + ['entry', 'mid', 'senior', 'lead'].map(function (l) {
      return '<option' + (t && t.level === l ? ' selected' : '') + '>' + l + '</option>'; }).join('') + '</select></label>' +
      field('Years of experience', 'years', 'type="number" min="0" max="60" value="' + (t ? t.years : 0) + '"') + '</div>' +
      '<fieldset class="fld acc-roles"><legend>Kinds of work to be found for (up to 5)</legend>' + D.categories.map(function (c) {
        return '<label><input type="checkbox" data-many name="roles" value="' + esc(c[0]) + '"' + (t && has(t.roles, c[0]) ? ' checked' : '') + '> ' + esc(c[1]) + '</label>'; }).join('') + '</fieldset>' +
      field('Places, as on the site (comma separated)', 'places', 'type="text" value="' + esc(t ? t.places.join(', ') : 'remote') + '" placeholder="remote, germany, london"', 'Place names from the locations pages, and “remote”.') +
      field('Companies that must never see it', 'blocked', 'type="text" value="' + esc(t ? t.blocked.join(', ') : '') + '" placeholder="yourcurrentemployer.com"', 'Their web addresses, comma separated: your current employer, say.') +
      '<label class="check"><input type="checkbox" name="show_name"' + (t && t.show_name ? ' checked' : '') + '> Show my name before I accept a request</label> ' +
      '<label class="check"><input type="checkbox" name="show_employers"' + (t && t.show_employers ? ' checked' : '') + '> Show the names of my employers</label>';
  }
  var talentValues = function (v) { return { level: v.level, years: Number(v.years) || 0, roles: v.roles || [], places: v.places.split(/[\s,]+/).filter(Boolean).map(function (x) { return x.toLowerCase(); }),
    blocked: v.blocked.split(/[\s,]+/).filter(Boolean), show_name: !!v.show_name, show_employers: !!v.show_employers }; };

  // posting, what a job brought, company pages, team, resume search, promotions, receipts
  function employerPart() {
    if (!me.posts_as.length) return hiringPart();
    var liveJobs = S.jobs.filter(function (j) { return j.status === 'live'; }), html = '';
    var own = liveJobs.length ? '<label class="fld">Or a job you posted here<select name="job_id"><option value="">—</option>' +
      liveJobs.map(function (j) { return '<option value="' + esc(j.id) + '">' + esc(j.title) + '</option>'; }).join('') + '</select></label>' : '';
    var jobField = field('Link to the job on this site', 'job', 'type="url" placeholder="' + esc(D.site) + '/job/…/"') + own;
    var companyField = field('Company, as it is named on the site', 'company', 'type="text" list="acc-companies" value="' + esc(me.company || '') + '" maxlength="80"');
    var pages = '<label class="fld">Page to sponsor<select name="page"><optgroup label="Categories">' +
      D.categories.map(function (c) { return '<option value="category:' + esc(c[0]) + '">' + esc(c[1]) + ' jobs</option>'; }).join('') + '</optgroup><optgroup label="Skills">' +
      D.skills.map(function (s) { return '<option value="skill:' + esc(s[0]) + '">' + esc(s[1]) + ' jobs</option>'; }).join('') + '</optgroup></select></label>';
    var credit = me.credits ? '<button class="btn ghost" type="submit" data-credit="1">Use a pack credit (' + me.credits + ' left)</button>' : '';

    html += sec('Post a job for free', '<form class="card" id="acc-job" novalidate><div class="acc-two">' +
      field('Company', 'company', 'type="text" maxlength="80" required value="' + esc(me.company || '') + '"') + field('Company site', 'company_url', 'type="url" placeholder="https://" required') +
      field('Job title', 'title', 'type="text" maxlength="120" required') + field('Link where people apply', 'apply_url', 'type="url" placeholder="https://" required', 'The page of this exact job on your site or hiring system.') +
      field('Location', 'location', 'type="text" maxlength="120" placeholder="Berlin, or Remote, Europe"') + field('Salary range (optional)', 'salary', 'type="text" maxlength="60" placeholder="$120K - $150K"', 'Jobs with a range are found by people who filter by pay.') +
      '</div><label class="fld">Employment type<select name="etype"><option value="">Not specified</option><option>Full-time</option><option>Contract</option><option>Part-time</option><option>Internship</option></select></label>' +
      '<label class="check"><input type="checkbox" name="remote"> Remote</label>' +
      '<label class="fld" style="margin-top:8px">About the role<textarea name="description" rows="6" maxlength="1500" required placeholder="What the person will do, with whom, and what you need from them. 80 to 1,500 characters."></textarea></label>' +
      err + '<button class="btn primary" type="submit">Publish the job</button>' +
      '<p class="note" style="margin:12px 0 0">Free for 30 days. We check that the job is not on the site already and open your link to make sure it is really there. The first jobs of a new account are read by a person before they appear, usually within a day.</p></form>', 'post');

    if (S.jobs.length) html += sec('Jobs you posted', '<div class="card" style="padding:0">' + S.jobs.map(function (j) {
      return '<div class="trow"><span>' + state(j.status) + '</span><div class="main"><a class="tt" href="' + esc(D.site + j.page) + '">' + esc(j.title) + '</a><span class="js">' + esc(j.company) +
        (j.location ? ' · ' + esc(j.location) : '') + ' · until ' + esc(j.until) + ' · ' + (j.views || 0) + ' views · ' + (j.applies || 0) + ' clicks on Apply</span>' +
        (j.review_reason ? '<span class="js">Waiting for a person: ' + esc(j.review_reason) + '</span>' : '') + (j.reject_reason ? '<span class="js">Not accepted: ' + esc(j.reject_reason) + '</span>' : '') + '</div><div class="ctl">' +
        (j.status === 'live' ? '<button class="btn ghost sm" type="button" style="margin:0" data-act="close" data-id="' + esc(j.id) + '">Close</button>' :
          j.status !== 'rejected' ? '<button class="btn ghost sm" type="button" style="margin:0" data-act="renew" data-id="' + esc(j.id) + '">Publish again</button>' : '') + '</div></div>';
    }).join('') + '</div><p class="note" style="margin-top:10px">Views and clicks count each visitor once a day. A new job appears on the site after the next update.</p>', 'jobs');

    if (me.posts_as.indexOf('employer') >= 0) {
      html += sec('Your company pages', (S.claims.length ? '<div class="card" style="padding:0">' + S.claims.map(function (c) {
        return '<div class="trow"><span>' + state(c.status) + '</span><div class="main"><strong>' + esc(c.company) + '</strong><span class="js">' + esc(c.domain) + ' · since ' + esc(c.since) + (c.reason ? ' · ' + esc(c.reason) : '') + '</span>' +
          (c.status === 'verified' ? '<form class="claim-page" data-id="' + esc(c.id) + '" novalidate>' + '<label class="fld">About the company (shown on its page)<textarea name="about" rows="3" maxlength="1000"></textarea></label>' +
            field('Company site', 'website', 'type="url" placeholder="https://' + esc(c.domain) + '"') + err + '<button class="btn sm" type="submit">Save the page</button> <button class="btn ghost sm" type="button" data-stats="' + esc(c.id) + '">Views and clicks</button><div class="stats-out"></div></form>' : '') + '</div></div>';
      }).join('') + '</div>' : '') +
        '<form class="card" id="claim" novalidate><p>We read the jobs of thousands of companies from their own hiring systems. If one of them is yours, claim its page: you see how many people view each job and click Apply, write the text of the page, and can add jobs your hiring system does not list.</p>' +
        field('Company, as the site names it', 'company', 'type="text" list="acc-companies" maxlength="80" required') + err + '<button class="btn" type="submit">Claim the page</button></form>', 'company');
      var team = S.team || { members: [] };
      html += sec('Your team', '<p>Colleagues on ' + esc(me.domain) + ' you add here can post under your company’s name from their own accounts.</p>' +
        (team.members.length ? '<ul class="feats">' + team.members.map(function (m) { return '<li>' + esc(m.email) + ' · ' + (m.has_account ? (m.confirmed ? m.live_jobs + ' live jobs' : 'not confirmed yet') : 'no account yet') +
          ' <button class="btn ghost sm" type="button" data-team-del="' + esc(m.email) + '">Remove</button></li>'; }).join('') + '</ul>' : '') +
        '<form id="team-add" novalidate>' + field('Colleague’s work email', 'email', 'type="email" required placeholder="name@' + esc(me.domain) + '"') + err + '<button class="btn" type="submit">Add to the team</button></form>', 'team');
      if (pub.talent === 'on' && S.sent) {
        html += sec('Find people in the resume database', '<form class="card" id="talent-search" novalidate><div class="acc-two">' + field('Words', 'q', 'type="text" placeholder="rust engineer"') + field('Skill', 'skill', 'type="text" placeholder="python"') +
          '<label class="fld">Kind of work<select name="role"><option value="">Any</option>' + D.categories.map(function (c) { return '<option value="' + esc(c[0]) + '">' + esc(c[1]) + '</option>'; }).join('') + '</select></label>' +
          field('Place', 'place', 'type="text" placeholder="remote, germany"') + '</div>' + err + '<button class="btn" type="submit">Search</button><span class="note"> ' + S.sent.credits + ' contact requests left; you pay only for people who accept.</span></form><div id="talent-out"></div>' +
          (S.sent.requests.length ? '<h3>Your requests</h3><ul class="feats">' + S.sent.requests.map(function (q) {
            var c = q.candidate; return '<li>' + state(q.status) + ' ' + esc(c.headline || 'Candidate') + (q.status === 'accepted' && c.contact ? ': <strong>' + esc(c.contact.name) + '</strong>, <a href="mailto:' + esc(c.contact.email) + '">' + esc(c.contact.email) + '</a>' + (c.contact.phone ? ', ' + esc(c.contact.phone) : '') : '') + ' · ' + esc(q.sent) + '</li>';
          }).join('') + '</ul>' : ''), 'resumes');
      }
    } else html += hiringPart();

    if (products.featured || products.pinned) html += sec('Put a job or your company in front', '<div class="acc-grid">' +
      productCard('featured', jobField, credit) + productCard('pinned', jobField) + productCard('spotlight', companyField) + productCard('sponsor', companyField + pages) + productCard('pack5', '') +
      '</div>' + (pub.payments === 'off' ? '<div class="banner">Paid placements are not on sale yet. Everything else on this page is free.</div>' : '<p class="note" style="margin-top:12px">You pay on a crypto checkout page. The placement switches on by itself when the network confirms the payment.</p>') +
      '<datalist id="acc-companies">' + D.companies.map(function (c) { return '<option value="' + esc(c) + '">'; }).join('') + '</datalist>', 'promote');
    else html += '<datalist id="acc-companies">' + D.companies.map(function (c) { return '<option value="' + esc(c) + '">'; }).join('') + '</datalist>';

    if (S.placements.length) html += sec('What is running', '<div class="tablewrap"><table><tr><th>Placement</th><th>For</th><th>From</th><th>Until</th><th>State</th></tr>' +
      S.placements.map(function (p) { return '<tr><td><strong>' + esc(p.kind) + '</strong></td><td>' + esc(p.label) + '</td><td>' + esc(p.from) + '</td><td>' + esc(p.until) + '</td><td>' + state(p.state) + '</td></tr>'; }).join('') + '</table></div>');
    if (S.orders.length) html += sec('Payments and receipts', '<div class="tablewrap"><table><tr><th>Date</th><th>What</th><th>Amount</th><th>Status</th><th></th></tr>' +
      S.orders.map(function (o) {
        return '<tr><td>' + esc(o.created) + '</td><td><strong>' + esc(o.name) + '</strong>' + (o.label && o.label !== o.name ? '<br><span class="note">' + esc(o.label) + '</span>' : '') + '</td><td>' +
          (o.amount_usd ? money(o.amount_usd) : 'Pack credit') + '</td><td>' + state(o.status) + '</td><td>' + (o.pay_url ? '<a href="' + esc(o.pay_url) + '">Pay now</a>' : '') +
          (o.status === 'paid' ? '<button class="btn ghost sm" type="button" data-receipt="' + esc(o.id) + '">Receipt</button>' : '') + '</td></tr>';
      }).join('') + '</table></div><div id="receipt-out"></div><p class="note">Every payment is a single payment for a fixed period. Nothing renews.</p>', 'payments');
    return html;
  }

  // an account with no company domain yet: how to get one (the site's own rules for who may post)
  function hiringPart() {
    return sec('Hiring? Post jobs for free', '<p>Jobs are posted from an account tied to the company’s own domain: sign up with your work address, or prove the domain here with a DNS record or a file on the company site.</p>' +
      '<form class="card" id="domain" novalidate>' + field('Your company’s domain', 'domain', 'type="text" placeholder="yourcompany.com" required') + err + '<button class="btn" type="submit">Get the code to publish</button><div id="domain-out"></div></form>' +
      (pub.linkedin === 'on' && !me.linkedin ? '<p><button class="btn ghost" type="button" id="li-start">Recruiter? Attach your LinkedIn profile</button></p>' : ''), 'hiring');
  }
  function draw() {
    var emp = me.posts_as.length > 0;
    var html = '<div class="acc-top"><p class="note" style="margin:0">Signed in as <strong>' + esc(me.email) + '</strong>' + (emp ? ' · ' + esc(me.domain || 'recruiter') : '') +
      '</p><button class="btn ghost sm" type="button" id="acc-out" style="margin:0">Sign out</button></div><div id="acc-pay"></div>' + (notice ? '<div class="banner ok">' + notice + '</div>' : '') +
      (!me.confirmed ? '<div class="banner">Confirm your email: open the link we sent to ' + esc(me.email) + '. <button class="btn ghost sm" type="button" id="acc-confirm">Send a new link</button></div>' : '') +
      (pub.payments === 'test' ? '<div class="banner">Test mode: payments are simulated on this machine. No money moves.</div>' : '');
    html += emp ? employerPart() + seekerPart() : seekerPart() + employerPart();
    html += sec('Your data', '<p>Download everything we keep about your account, or delete the account. Deleting removes your alerts, your resume, your synced lists and everything you posted, at once.</p>' +
      '<p><button class="btn ghost" type="button" id="me-export">Download my data</button> <button class="btn ghost" type="button" id="me-delete">Delete my account</button></p>' +
      '<p class="note"><a href="' + esc(D.site) + '/privacy/">What we keep and why</a></p>', 'data');
    notice = '';
    root.innerHTML = html;
    wire();
    watchOrder();
  }

  function wire() {
    document.getElementById('acc-out').addEventListener('click', signOut);
    on('#acc-confirm', function (b) { b.disabled = true; api('POST', '/api/auth/confirm/request').then(function (r) { b.textContent = 'Sent'; }, function (e) { b.disabled = false; alert(e.message); }); });
    on('[data-alert-del]', function (b) { b.disabled = true; api('DELETE', '/api/alerts/' + b.getAttribute('data-alert-del')).then(load, function (e) { b.disabled = false; alert(e.message); }); });
    on('#sync-up', function (b) {
      var data = {}; SYNC_KEYS.forEach(function (k) { var v = H.get(k, null); if (v != null) data[k] = v; });
      b.disabled = true; api('PUT', '/api/sync', { data: data }).then(function () { notice = 'Your lists are copied to your account.'; return load(); }, function (e) { b.disabled = false; alert(e.message); });
    });
    on('#sync-down', function (b) {
      if (!confirm('Replace the lists in this browser with the copy in your account?')) return;
      var data = (S.sync && S.sync.data) || {}; SYNC_KEYS.forEach(function (k) { if (k in data) H.set(k, data[k]); });
      notice = 'Your lists are in this browser now.'; draw();
    });
    submit(document.getElementById('talent-on'), function (v) {
      if (!v.consent) throw new Error('Tick the box first: nothing is stored without it.');
      return api('PUT', '/api/talent/profile', Object.assign(talentValues(v), { consent: true, consent_text: S.talent.consent_text, resume: H.get('hrn_resume', null) })).then(function () { notice = 'Employers can now find your resume, without your name and contacts.'; return load(); });
    });
    submit(document.getElementById('talent-set'), function (v) { return api('PUT', '/api/talent/profile', talentValues(v)).then(function () { notice = 'Saved.'; return load(); }); });
    on('#talent-update', function () { api('PUT', '/api/talent/profile', { resume: H.get('hrn_resume', null) }).then(function () { notice = 'The copy employers see is updated.'; return load(); }, function (e) { alert(e.message); }); });
    on('#talent-pause', function () { api('PUT', '/api/talent/profile', { paused: !S.talent.profile.paused }).then(load, function (e) { alert(e.message); }); });
    on('#talent-del', function () {
      if (!confirm('Delete your resume from our server for good? Employers will no longer find it.')) return;
      api('DELETE', '/api/talent/profile').then(function (r) { notice = esc(r.message); return load(); }, function (e) { alert(e.message); });
    });
    on('[data-q]', function (b) { b.disabled = true; api('POST', '/api/talent/requests/' + b.getAttribute('data-id') + '/' + b.getAttribute('data-q')).then(load, function (e) { b.disabled = false; alert(e.message); }); });
    submit(document.getElementById('acc-job'), function (v) {
      return api('POST', '/api/jobs', v).then(load, function (e) {
        if (e.code === 'already_listed' || e.code === 'listed') e.message += e.body && e.body.claim ? ' You can claim the page of ' + e.body.claim.company + ' below.' : '';
        throw e;
      });
    });
    on('[data-act]', function (b) { b.disabled = true; api('POST', '/api/jobs/' + b.getAttribute('data-id') + '/' + b.getAttribute('data-act')).then(load, function (e) { b.disabled = false; alert(e.message); }); });
    submit(document.getElementById('claim'), function (v) { return api('POST', '/api/claims', v).then(load); });
    Array.prototype.forEach.call(root.querySelectorAll('form.claim-page'), function (f) {
      submit(f, function (v) { return api('PUT', '/api/claims/' + f.getAttribute('data-id') + '/page', v).then(function () { notice = 'The company page is saved; it shows after the next update.'; return load(); }); });
    });
    on('[data-stats]', function (b) {
      var out = b.parentNode.querySelector('.stats-out');
      api('GET', '/api/claims/' + b.getAttribute('data-stats') + '/stats').then(function (r) {
        out.innerHTML = r.jobs.length ? '<div class="tablewrap"><table><tr><th>Job page</th><th>Views</th><th>Clicks on Apply</th></tr>' + r.jobs.map(function (j) {
          return '<tr><td><a href="' + esc(j.page) + '">' + esc(j.page.replace(/^.*\/job\//, '').replace(/\/$/, '')) + '</a></td><td>' + j.views + '</td><td>' + j.applies + '</td></tr>'; }).join('') + '</table></div>' : '<p class="note">No views counted yet.</p>';
      }, function (e) { out.textContent = e.message; });
    });
    submit(document.getElementById('team-add'), function (v) { return api('POST', '/api/team', v).then(load); });
    on('[data-team-del]', function (b) { api('DELETE', '/api/team/' + encodeURIComponent(b.getAttribute('data-team-del'))).then(load, function (e) { alert(e.message); }); });
    submit(document.getElementById('domain'), function (v) {
      return api('POST', '/api/domain/token', v).then(function (r) {
        document.getElementById('domain-out').innerHTML = '<p>Publish one of these, then press a button:</p><p><strong>DNS:</strong> a TXT record named <code>' + esc(r.dns.name) + '</code> with the value <code>' + esc(r.dns.value) + '</code></p>' +
          '<p><strong>Or a file:</strong> <code>' + esc(r.file.url) + '</code> containing <code>' + esc(r.file.content) + '</code></p><p><button class="btn sm" type="button" data-check="dns">Check the DNS record</button> <button class="btn ghost sm" type="button" data-check="file">Check the file</button></p>';
        on('[data-check]', function (b) { api('POST', '/api/domain/check', { method: b.getAttribute('data-check') }).then(function () { notice = 'Your company’s domain is proved. You can post jobs now.'; return load(); }, function (e) { alert(e.message); }); });
      });
    });
    on('#li-start', function () { api('POST', '/api/auth/linkedin/start').then(function (r) { location.href = r.url; }, function (e) { alert(e.message); }); });
    submit(document.getElementById('talent-search'), function (v) {
      var qs = Object.keys(v).filter(function (k) { return v[k]; }).map(function (k) { return k + '=' + encodeURIComponent(v[k]); }).join('&');
      return api('GET', '/api/talent/search?' + qs).then(function (r) {
        document.getElementById('talent-out').innerHTML = '<p class="note">' + r.total + ' found.</p>' + r.results.map(function (c) {
          return '<div class="card"><p><strong>' + esc(c.name || c.headline || 'Candidate') + '</strong>' + [c.name ? c.headline : '', c.level, c.years ? c.years + ' years' : '', c.places.join(', ')].filter(Boolean).map(function (x) { return ' · ' + esc(x); }).join('') + '</p><p class="note">' + esc(c.skills.join(', ')) + '</p>' +
            (c.summary ? '<p>' + esc(c.summary) + '</p>' : '') + '<form class="talent-ask" data-id="' + esc(c.id) + '" novalidate><label class="fld">Your message<textarea name="message" rows="3" maxlength="1000" required placeholder="Who you are, the job, and why them."></textarea></label>' +
            field('Link to the job (optional)', 'job_url', 'type="url" placeholder="https://"') + err + '<button class="btn sm" type="submit">Ask to contact</button></form></div>';
        }).join('');
        Array.prototype.forEach.call(document.querySelectorAll('form.talent-ask'), function (f) {
          submit(f, function (x) { return api('POST', '/api/talent/' + f.getAttribute('data-id') + '/contact', x).then(function () { f.innerHTML = '<p class="note">Sent. You get their name and contacts if they accept.</p>'; }); });
        });
      });
    });
    on('[data-receipt]', function (b) {
      api('GET', '/api/orders/' + b.getAttribute('data-receipt') + '/receipt').then(function (r) {
        var x = r.receipt;
        document.getElementById('receipt-out').innerHTML = '<div class="card"><h3 style="margin-top:0">Receipt ' + esc(x.number) + '</h3><p>' + esc(x.date) + ' · ' + esc(x.seller) + '</p><p>To: ' + esc(x.buyer.email) + (x.buyer.company ? ', ' + esc(x.buyer.company) : '') + '</p>' +
          '<p><strong>' + esc(x.item) + '</strong>' + (x.period_days ? ', ' + x.period_days + ' days' : '') + ': ' + money(x.amount_usd) + ', paid with ' + esc(x.paid_with) + '.</p><p class="note">' + esc(x.note) + '</p>' +
          '<p><button class="btn ghost sm" type="button" onclick="window.print()">Print</button></p></div>';
      }, function (e) { alert(e.message); });
    });
    on('#me-export', function () {
      api('GET', '/api/me/export').then(function (r) {
        var a = document.createElement('a'); a.href = URL.createObjectURL(new Blob([JSON.stringify(r, null, 2)], { type: 'application/json' })); a.download = 'my-data-' + new Date().toISOString().slice(0, 10) + '.json';
        document.body.appendChild(a); a.click(); a.remove();
      }, function (e) { alert(e.message); });
    });
    on('#me-delete', function () {
      var typed = prompt('This deletes your account, alerts, resume and jobs for good. Type “delete my account” to go on.');
      if (!typed) return;
      api('DELETE', '/api/me', { confirm: typed }).then(function (r) { token = ''; H.set('hrn_token', ''); notice = esc(r.message); drawAuth('up'); }, function (e) { alert(e.message); });
    });
    Array.prototype.forEach.call(root.querySelectorAll('form[data-product]'), function (form) {
      submit(form, function (v, btn) {
        var data = { product: form.getAttribute('data-product'), target: v };
        if (btn && btn.getAttribute('data-credit')) data.use_credit = true;
        return api('POST', '/api/orders', data).then(function (r) {
          if (r.order.status === 'pending' && r.order.pay_url) { location.href = r.order.pay_url; return new Promise(function () {}); }   // on to the checkout
          return load();
        });
      });
    });
  }
  // back from the checkout: wait for the confirmation and say plainly what happened
  function watchOrder() {
    var id = new URLSearchParams(location.search).get('order'), box = document.getElementById('acc-pay');
    if (!id || !box) return;
    var tries = 0;
    (function check() {
      api('GET', '/api/orders/' + encodeURIComponent(id) + '?refresh=1').then(function (r) {
        var o = r.order;
        if (o.status === 'paid') {
          box.innerHTML = '<div class="banner ok">Payment received: ' + esc(o.name) + (o.label && o.label !== o.name ? ' for ' + esc(o.label) : '') + ' is on. It shows on the site within about ten minutes.</div>';
          cleanUrl();
          if (!S.orders.some(function (x) { return x.id === o.id && x.status === 'paid'; })) load();
        } else if (o.status === 'pending' && tries++ < 45) {
          box.innerHTML = '<div class="banner">Waiting for the network to confirm your payment. This page updates by itself; you can also close it and come back later.</div>';
          setTimeout(check, 4000);
        } else if (o.status === 'pending') box.innerHTML = '<div class="banner">The payment has not been confirmed yet. Crypto networks can take a while; it will switch on by itself as soon as it is.</div>';
        else box.innerHTML = '<div class="banner">This payment is marked “' + esc(o.status) + '”. Nothing was switched on.' + (o.status === 'underpaid' ? ' The amount received was lower than the price.' : '') + '</div>';
      }).catch(function () {});
    })();
  }

  /* ---------- start: links from letters (#confirm=, #reset=) and the way back from Google or LinkedIn (?code=&state=) ---------- */
  function start() {
    var hash = location.hash, q = new URLSearchParams(location.search), m;
    if ((m = /^#confirm=([a-f0-9]{64})$/.exec(hash))) {
      cleanUrl();
      return api('POST', '/api/auth/confirm', { token: m[1] }).then(function () { notice = 'Your email is confirmed.'; }, function (e) { notice = esc(e.message); }).then(begin);
    }
    if ((m = /^#reset=([a-f0-9]{64})$/.exec(hash))) { cleanUrl(); return drawReset(m[1]); }
    if (q.get('error') && q.get('state')) { cleanUrl(); notice = 'The sign-in was cancelled.'; return begin(); }
    if (q.get('code') && q.get('state')) {
      var secret = ''; try { secret = sessionStorage.getItem('hrn_google') || ''; sessionStorage.removeItem('hrn_google'); } catch (e) {}
      var code = q.get('code'), st = q.get('state'); cleanUrl();
      if (secret) return api('POST', '/api/auth/google/callback', { code: code, state: st, secret: secret }).then(function (r) { token = r.token; H.set('hrn_token', token); notice = r.created ? 'Welcome: your account is ready.' : ''; }, function (e) { notice = esc(e.message); }).then(begin);
      if (token) return api('POST', '/api/auth/linkedin/callback', { code: code, state: st }).then(function () { notice = 'Your LinkedIn profile is attached.'; }, function (e) { notice = esc(e.message); }).then(begin);
    }
    return begin();
  }
  function begin() {
    if (token) return load().catch(function (e) { if (e.status === 401) { token = ''; H.set('hrn_token', ''); drawAuth('in'); } else root.innerHTML = '<div class="banner">' + esc(e.message) + '</div>'; });
    return drawAuth(notice ? 'in' : 'up');
  }
  root.innerHTML = '<p class="note">Loading…</p>';
  api('GET', '/api/public/products').then(function (p) { pub = p; }, function () {}).then(start);
})();
