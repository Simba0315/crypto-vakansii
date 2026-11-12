/* Employer account: sign in, post a job, buy a placement, pay at the crypto checkout. Talks to the API named in data-api.
   Nothing here needs a person on our side: a paid order switches itself on. */
(function () {
  var root = document.getElementById('acc');
  if (!root || !window.HRN) return;
  var H = window.HRN, esc = H.esc, API = root.getAttribute('data-api').replace(/\/+$/, '');
  var D = JSON.parse(document.getElementById('acc-data').textContent);
  var token = H.get('hrn_token', ''), me = null, products = {}, payments = 'off', jobs = [], placements = [], orders = [];

  function api(method, path, data) {
    var headers = {};
    if (data) headers['Content-Type'] = 'application/json';
    if (token) headers.Authorization = 'Bearer ' + token;
    return fetch(API + path, { method: method, headers: headers, body: data ? JSON.stringify(data) : undefined }).then(function (r) {
      return r.json().catch(function () { return {}; }).then(function (b) {
        if (r.ok) return b;
        var err = new Error(b.message || 'Something went wrong. Please try again.'); err.code = b.error; err.status = r.status; throw err;
      });
    }, function () { throw new Error('Could not reach the server. Check your connection and try again.'); });
  }
  function field(label, name, attrs, hint) {
    return '<label class="fld">' + label + '<input name="' + name + '" ' + (attrs || 'type="text"') + '>' + (hint ? '<span class="hint">' + hint + '</span>' : '') + '</label>';
  }
  function values(form) {
    var out = {};
    Array.prototype.forEach.call(form.elements, function (el) { if (el.name) out[el.name] = el.type === 'checkbox' ? el.checked : el.value.trim(); });
    return out;
  }
  // run an action from a form: lock the button, show the server's message under the form if it fails
  function submit(form, work) {
    form.addEventListener('submit', function (ev) {
      ev.preventDefault();
      var btn = ev.submitter || form.querySelector('button[type=submit]'), box = form.querySelector('.acc-err'), label = btn.textContent;
      box.hidden = true; btn.disabled = true; btn.textContent = 'One moment…';
      Promise.resolve().then(function () { return work(values(form), btn); }).catch(function (err) {
        box.textContent = err.message; box.hidden = false;
        if (err.status === 401 && token) { signOut(); }
      }).then(function () { btn.disabled = false; btn.textContent = label; });
    });
  }
  var money = function (n) { return '$' + Number(n).toLocaleString('en-US'); };
  var state = function (s) { return '<span class="state ' + esc(s) + '">' + esc(s) + '</span>'; };

  /* ---------- signed out ---------- */
  function drawAuth(mode) {
    var up = mode !== 'in';
    root.innerHTML = '<div class="card acc-auth"><div class="tabs" role="tablist" style="margin-top:0">' +
      '<button class="tab" type="button" role="tab" data-mode="up" aria-selected="' + up + '">Create account</button>' +
      '<button class="tab" type="button" role="tab" data-mode="in" aria-selected="' + !up + '">Sign in</button></div>' +
      '<form novalidate>' + field('Work email', 'email', 'type="email" autocomplete="email" required') +
      field('Password', 'password', 'type="password" autocomplete="' + (up ? 'new-password' : 'current-password') + '" required minlength="8"', up ? 'At least 8 characters.' : '') +
      (up ? field('Company (optional)', 'company', 'type="text" autocomplete="organization" maxlength="80"') : '') +
      '<p class="acc-err" role="alert" hidden></p><button class="btn primary lg" type="submit" style="width:100%">' + (up ? 'Create account' : 'Sign in') + '</button></form>' +
      '<p class="note" style="margin:14px 0 0">' + (up ? 'No card needed. You pay only if you choose a paid placement, in crypto, at checkout.' : 'Forgot the password? Create a new account with another email for now: password reset by email arrives with email alerts.') + '</p></div>';
    Array.prototype.forEach.call(root.querySelectorAll('.tab'), function (t) { t.addEventListener('click', function () { drawAuth(t.getAttribute('data-mode')); }); });
    submit(root.querySelector('form'), function (v) {
      return api('POST', up ? '/api/auth/signup' : '/api/auth/login', v).then(function (r) { token = r.token; H.set('hrn_token', token); me = r.user; return load(); });
    });
  }
  function signOut() {
    api('POST', '/api/auth/logout').catch(function () {});
    token = ''; me = null; H.set('hrn_token', ''); drawAuth('in');
  }

  /* ---------- signed in ---------- */
  function load() {
    return Promise.all([api('GET', '/api/me'), api('GET', '/api/public/products'), api('GET', '/api/jobs'), api('GET', '/api/placements'), api('GET', '/api/orders')]).then(function (r) {
      me = r[0].user; payments = r[1].payments; products = {}; r[1].products.forEach(function (p) { products[p.id] = p; });
      jobs = r[2].jobs; placements = r[3].placements; orders = r[4].orders; draw();
    });
  }
  function productCard(id, fields, extra) {
    var p = products[id]; if (!p) return '';
    return '<form class="acc-card" data-product="' + id + '" novalidate><p class="pname">' + esc(p.name) + '</p><p class="price">' + money(p.usd) + '</p>' +
      '<p class="what">' + esc(D.what[p.name] || '') + '</p>' + fields + '<p class="acc-err" role="alert" hidden></p>' +
      '<button class="btn primary" type="submit"' + (payments === 'off' ? ' disabled' : '') + '>Continue to payment</button>' + (extra || '') + '</form>';
  }
  function draw() {
    var liveJobs = jobs.filter(function (j) { return j.status === 'live'; });
    var own = liveJobs.length ? '<label class="fld">Or a job you posted here<select name="job_id"><option value="">—</option>' +
      liveJobs.map(function (j) { return '<option value="' + esc(j.id) + '">' + esc(j.title) + '</option>'; }).join('') + '</select></label>' : '';
    var jobField = field('Link to the job on this site', 'job', 'type="url" placeholder="' + esc(D.site) + '/job/…/"') + own;
    var companyField = field('Company, as it is named on the site', 'company', 'type="text" list="acc-companies" value="' + esc(me.company || '') + '" maxlength="80"');
    var pages = '<label class="fld">Page to sponsor<select name="page"><optgroup label="Categories">' +
      D.categories.map(function (c) { return '<option value="category:' + esc(c[0]) + '">' + esc(c[1]) + ' jobs</option>'; }).join('') + '</optgroup><optgroup label="Skills">' +
      D.skills.map(function (s) { return '<option value="skill:' + esc(s[0]) + '">' + esc(s[1]) + ' jobs</option>'; }).join('') + '</optgroup></select></label>';
    var credit = me.credits ? '<button class="btn ghost" type="submit" data-credit="1">Use a pack credit (' + me.credits + ' left)</button>' : '';

    var html = '<div class="acc-top"><p class="note" style="margin:0">Signed in as <strong>' + esc(me.email) + '</strong>' + (me.credits ? ' · ' + me.credits + ' featured listing' + (me.credits > 1 ? 's' : '') + ' left in your pack' : '') +
      '</p><button class="btn ghost sm" type="button" id="acc-out" style="margin:0">Sign out</button></div><div id="acc-pay"></div>' +
      (payments === 'off' ? '<div class="banner">Checkout is being connected. You can post free jobs now; paid placements open as soon as it is on.</div>' : '') +
      (payments === 'test' ? '<div class="banner">Test mode: payments are simulated on this machine. No money moves.</div>' : '') +
      '<section class="sec" style="margin-top:8px"><div class="sec-head"><h2>Put a job or your company in front</h2></div><div class="acc-grid">' +
      productCard('featured', jobField, credit) + productCard('pinned', jobField) + productCard('spotlight', companyField) + productCard('sponsor', companyField + pages) + productCard('pack5', '') +
      '</div><p class="note" style="margin-top:12px">You pay on a crypto checkout page (USDT, BTC, ETH and other coins). The placement switches on by itself when the network confirms the payment, and shows on the site within about ten minutes.</p>' +
      '<datalist id="acc-companies">' + D.companies.map(function (c) { return '<option value="' + esc(c) + '">'; }).join('') + '</datalist></section>' +

      '<section class="sec"><div class="sec-head"><h2>Post a job for free</h2></div><form class="card" id="acc-job" novalidate><div class="acc-two">' +
      field('Company', 'company', 'type="text" maxlength="80" required value="' + esc(me.company || '') + '"') + field('Company site', 'company_url', 'type="url" placeholder="https://" required') +
      field('Job title', 'title', 'type="text" maxlength="120" required') + field('Link where people apply', 'apply_url', 'type="url" placeholder="https://" required', 'The page of this exact job on your site or hiring system.') +
      field('Location', 'location', 'type="text" maxlength="120" placeholder="Berlin, or Remote, Europe"') + field('Salary range (optional)', 'salary', 'type="text" maxlength="60" placeholder="$120K - $150K"', 'Jobs with a range are found by people who filter by pay.') +
      '</div><label class="fld">Employment type<select name="etype"><option value="">Not specified</option><option>Full-time</option><option>Contract</option><option>Part-time</option><option>Internship</option></select></label>' +
      '<label class="check"><input type="checkbox" name="remote"> Remote</label>' +
      '<label class="fld" style="margin-top:8px">About the role<textarea name="description" rows="6" maxlength="1500" required placeholder="What the person will do, with whom, and what you need from them. 80 to 1,500 characters."></textarea></label>' +
      '<p class="acc-err" role="alert" hidden></p><button class="btn primary" type="submit">Publish the job</button>' +
      '<p class="note" style="margin:12px 0 0">Free for 30 days. We open your link to make sure the job is really there, then it goes live without a manual review.</p></form></section>';

    if (jobs.length) html += '<section class="sec"><div class="sec-head"><h2>Jobs you posted</h2></div><div class="card" style="padding:0">' + jobs.map(function (j) {
      return '<div class="trow"><span>' + state(j.status) + '</span><div class="main"><a class="tt" href="' + esc(D.site + j.page) + '">' + esc(j.title) + '</a><span class="js">' + esc(j.company) +
        (j.location ? ' · ' + esc(j.location) : '') + ' · until ' + esc(j.until) + '</span></div><div class="ctl">' +
        (j.status === 'live' ? '<button class="btn ghost sm" type="button" style="margin:0" data-act="close" data-id="' + esc(j.id) + '">Close</button>' :
          '<button class="btn ghost sm" type="button" style="margin:0" data-act="renew" data-id="' + esc(j.id) + '">Publish again</button>') + '</div></div>';
    }).join('') + '</div><p class="note" style="margin-top:10px">A new job appears on the site after the next update, usually within ten minutes.</p></section>';

    if (placements.length) html += '<section class="sec"><div class="sec-head"><h2>What is running</h2></div><div class="tablewrap"><table><tr><th>Placement</th><th>For</th><th>From</th><th>Until</th><th>State</th></tr>' +
      placements.map(function (p) { return '<tr><td><strong>' + esc(p.kind) + '</strong></td><td>' + esc(p.label) + '</td><td>' + esc(p.from) + '</td><td>' + esc(p.until) + '</td><td>' + state(p.state) + '</td></tr>'; }).join('') + '</table></div></section>';

    if (orders.length) html += '<section class="sec"><div class="sec-head"><h2>Payments</h2></div><div class="tablewrap"><table><tr><th>Date</th><th>What</th><th>Amount</th><th>Status</th><th></th></tr>' +
      orders.map(function (o) {
        return '<tr><td>' + esc(o.created) + '</td><td><strong>' + esc(o.name) + '</strong>' + (o.label && o.label !== o.name ? '<br><span class="note">' + esc(o.label) + '</span>' : '') + '</td><td>' +
          (o.amount_usd ? money(o.amount_usd) : 'Pack credit') + '</td><td>' + state(o.status) + '</td><td>' + (o.pay_url ? '<a href="' + esc(o.pay_url) + '">Pay now</a>' : '') + '</td></tr>';
      }).join('') + '</table></div></section>';

    root.innerHTML = html;
    document.getElementById('acc-out').addEventListener('click', signOut);
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
    submit(document.getElementById('acc-job'), function (v) { return api('POST', '/api/jobs', v).then(load); });
    Array.prototype.forEach.call(root.querySelectorAll('[data-act]'), function (b) {
      b.addEventListener('click', function () { b.disabled = true; api('POST', '/api/jobs/' + b.getAttribute('data-id') + '/' + b.getAttribute('data-act')).then(load, function (err) { b.disabled = false; alert(err.message); }); });
    });
    watchOrder();
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
          history.replaceState(null, '', location.pathname);
          if (!orders.some(function (x) { return x.id === o.id && x.status === 'paid'; })) load();
        } else if (o.status === 'pending' && tries++ < 45) {
          box.innerHTML = '<div class="banner">Waiting for the network to confirm your payment. This page updates by itself; you can also close it and come back later.</div>';
          setTimeout(check, 4000);
        } else if (o.status === 'pending') box.innerHTML = '<div class="banner">The payment has not been confirmed yet. Crypto networks can take a while; it will switch on by itself as soon as it is.</div>';
        else box.innerHTML = '<div class="banner">This payment is marked “' + esc(o.status) + '”. Nothing was switched on.' + (o.status === 'underpaid' ? ' The amount received was lower than the price.' : '') + '</div>';
      }).catch(function () {});
    })();
  }

  root.innerHTML = '<p class="note">Loading…</p>';
  if (token) load().catch(function (err) { if (err.status === 401) { token = ''; H.set('hrn_token', ''); drawAuth('in'); } else root.innerHTML = '<div class="banner">' + esc(err.message) + '</div>'; });
  else drawAuth('up');
})();
