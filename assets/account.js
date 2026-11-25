/* Your account, for job seekers and employers alike: sign in (email and password, or Google), job alerts, saved jobs on every device,
   your resumes, your resume for employers (only if you tick it), and for employers: free posting, what a job brought, company pages,
   the team, promotions and receipts. Everything you keep here can be downloaded or deleted in Settings. Talks to the API in data-api;
   the rules behind each part are in server/README.md. Nothing here needs a person on our side: a paid order switches itself on.

   How the page is put together (pass of 17 Nov 2026):
   - one side at a time. hrn_role (seeker or employer) decides which menu and which first screen are drawn; the other side is one press
     away ("Hiring?" / "Looking for a job?") and a link to one of its parts (#post, #resumes) switches by itself;
   - every part opens with a small label and a two-weight headline, has one main button, and says in one sentence what to do when it is empty;
   - a mistake is said next to the field it belongs to (check for what the browser can tell, ERR_FIELD for what the server answers);
   - the header (site.js) is told whenever the sign-in or the side changes: the event "hrn:auth" on document. */
(function () {
  var root = document.getElementById('acc');
  if (!root || !window.HRN) return;
  var H = window.HRN, esc = H.esc, API = root.getAttribute('data-api').replace(/\/+$/, '');
  var D = JSON.parse(document.getElementById('acc-data').textContent);
  var hd = document.getElementById('acc-hd');                       // the page's own title and lead: read without JavaScript and while it loads
  var token = H.get('hrn_token', ''), me = null, pub = { products: [], payments: 'off' }, products = {}, S = {}, notice = '', noticeBad = false, saidAt = 0, fresh = false, usedLink = false;
  var promo = null, paintPost = null;                               // a promo code that was applied: { code, percent, quotes: { product id: { amount_usd, full_usd } } }
  var ROLE = (function () { var q = ''; try { q = new URLSearchParams(location.search).get('as') || ''; } catch (e) {} return q === 'employer' || q === 'seeker' ? q : H.get('hrn_role', 'seeker'); })();
  if (ROLE !== 'employer') ROLE = 'seeker';
  H.set('hrn_role', ROLE);
  var SYNC_KEYS = ['hrn_jobs', 'hrn_saved', 'hrn_searches', 'hrn_follow', 'hrn_hidden', 'hrn_mute'];   // what "My jobs" keeps in this browser
  var MON = ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun', 'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec'];
  var KIND = { featured: 'Standard boost', premium: 'Premium boost', spotlight: 'Company spotlight', sponsor: 'Category or skill sponsor', bump: 'Bump to top', urgent: 'Urgently hiring badge' };

  function told() { try { document.dispatchEvent(new CustomEvent('hrn:auth')); } catch (e) {} }
  function setRole(r) { ROLE = r === 'employer' ? 'employer' : 'seeker'; H.set('hrn_role', ROLE); told(); }
  function flash(html, bad) { notice = html; noticeBad = !!bad; }
  function setPub(p) { pub = p; products = {}; (p.products || []).forEach(function (x) { products[x.id] = x; }); }
  told();                                                           // ?as=employer may have just changed the side

  function api(method, path, data) {
    var headers = {}, sent = token;
    if (data) headers['Content-Type'] = 'application/json';
    if (token) headers.Authorization = 'Bearer ' + token;
    return fetch(API + path, { method: method, headers: headers, body: data ? JSON.stringify(data) : undefined }).then(function (r) {
      return r.json().catch(function () { return {}; }).then(function (b) {
        if (r.ok) return b;
        var err = new Error(b.message || 'Something went wrong. Please try again.'); err.code = b.error; err.status = r.status; err.body = b;
        if (r.status === 401 && sent && sent === token && path.indexOf('/api/auth/log') !== 0) { err.gone = true; ended(); }      // the sign-in ran out: back to the form, and the header says "Sign in" again
        throw err;
      });
    }, function () { throw new Error('Could not reach the server. Check your connection and try again.'); });
  }
  var quiet = function (p, dflt) { return p.catch(function () { return dflt; }); };
  function field(label, name, attrs, hint) {
    return '<label class="fld"><span class="fld-l">' + label + '</span><input name="' + name + '" ' + (attrs || 'type="text"') + '>' + (hint ? '<span class="hint">' + hint + '</span>' : '') + '</label>';
  }
  function values(form) {
    var out = {};
    Array.prototype.forEach.call(form.elements, function (el) {
      if (!el.name || el.type === 'file') return;
      if (el.type === 'radio') { if (el.checked) out[el.name] = el.value; return; }
      if (el.type === 'checkbox' && el.hasAttribute('data-many')) { (out[el.name] = out[el.name] || []); if (el.checked) out[el.name].push(el.value); }
      else out[el.name] = el.type === 'checkbox' ? el.checked : el.value.trim();
    });
    return out;
  }
  /* a mistake is written under the field it is about, in plain words; the field is marked for screen readers and gets the focus */
  function mark(el, msg) {
    var holder = el.closest('.fld') || el.closest('label') || el.parentNode, old = holder.querySelector('.ferr');
    if (old) old.remove();
    el.setAttribute('aria-invalid', 'true');
    var s = document.createElement('span'); s.className = 'ferr'; s.setAttribute('role', 'alert'); s.textContent = msg; holder.appendChild(s);
  }
  function unmark(form) {
    Array.prototype.forEach.call(form.querySelectorAll('.ferr'), function (x) { x.remove(); });
    Array.prototype.forEach.call(form.querySelectorAll('[aria-invalid]'), function (x) { x.removeAttribute('aria-invalid'); });
  }
  root.addEventListener('input', function (ev) {                     // the note goes as soon as the person starts to correct the field
    var el = ev.target; if (!el || !el.getAttribute || !el.getAttribute('aria-invalid')) return;
    el.removeAttribute('aria-invalid');
    var h = el.closest('.fld') || el.closest('label'), x = h && h.querySelector('.ferr'); if (x) x.remove();
  });
  var NEED = { email: 'Enter your email address.', password: 'Enter a password.', url: 'Enter the address, starting with https://' };
  function check(form) {
    var first = null;
    Array.prototype.forEach.call(form.elements, function (el) {
      if (!el.name || el.disabled || el.type === 'hidden' || el.type === 'file' || el.type === 'radio') return;
      var v = el.type === 'checkbox' ? (el.checked ? '1' : '') : String(el.value || '').trim(), msg = '', min = Number(el.getAttribute('minlength')) || 0;
      if (el.required && !v) msg = el.getAttribute('data-need') || (el.type === 'checkbox' ? 'Tick the box to go on.' : NEED[el.type] || 'Please fill this in.');
      else if (v && el.type === 'email' && !/^[^\s@]+@[^\s@]+\.[^\s@]{2,}$/.test(v)) msg = 'This does not look like an email address. It should read like name@example.com.';
      else if (v && el.type === 'url' && !/^https:\/\/[^\s.]+\.\S+$/i.test(v)) msg = 'Enter the full address, starting with https://';
      else if (v && min && v.length < min) msg = 'At least ' + min + ' characters: ' + (min - v.length) + ' more to go.';
      if (msg) { mark(el, msg); if (!first) first = el; }
    });
    if (first) { try { first.focus(); } catch (e) {} }
    return !first;
  }
  // what the server names in its answer, and the field that answer is about
  var ERR_FIELD = { email: 'email', exists: 'email', throwaway_email: 'email', free_mail: 'email', credentials: 'password', password: 'password', company: 'company', company_taken: 'company', listed: 'company', not_listed: 'company',
    claimed: 'company', company_url: 'company_url', title: 'title', duplicate: 'title', already_listed: 'title', apply_url: 'apply_url', description: 'description', domain: 'domain', cat: 'cat', freq: 'freq', loc: 'loc',
    confirm: 'confirm', consent: 'consent', message: 'message', name: 'name' };
  function oops(fieldName, msg) { var e = new Error(msg); e.field = fieldName; return e; }
  // run an action from a form: check it, lock the button, and put the server's answer under the field it is about (or under the form)
  function submit(form, work) {
    if (!form) return;
    form.addEventListener('submit', function (ev) {
      ev.preventDefault();
      var btn = ev.submitter || form.querySelector('button[type=submit]'), box = form.querySelector('.acc-err'), label = btn.textContent;
      unmark(form); if (box) box.hidden = true;
      if (!check(form)) return;
      btn.disabled = true; btn.textContent = 'One moment…';
      Promise.resolve().then(function () { return work(values(form), btn); }).catch(function (e) {
        if (e.gone) return;                                           // the sign-in ran out: the sign-in form is on screen already and says so
        var name = e.field || ERR_FIELD[e.code], el = name ? form.elements[name] : null;
        if (el && !el.tagName && el.length) el = el[0];
        if (el && el.type !== 'hidden') { mark(el, e.message); try { el.focus(); } catch (x) {} }
        else if (box) { box.textContent = e.message; box.hidden = false; } else say(esc(e.message), true);
      }).then(function () { btn.disabled = false; btn.textContent = label; });
    });
  }
  function on(sel, fn) { Array.prototype.forEach.call(root.querySelectorAll(sel), function (el) { el.addEventListener('click', function () { fn(el); }); }); }
  // a message at the top of the open part (instead of a browser dialog): what was done, or what went wrong
  function say(html, bad) {
    var box = document.getElementById('acc-say');
    if (!box) { flash(html, bad); return; }
    saidAt = Date.now();
    box.innerHTML = html ? '<div class="banner' + (bad ? '' : ' ok') + '" role="' + (bad ? 'alert' : 'status') + '">' + html + '</div>' : '';
    if (html) { var r = box.getBoundingClientRect(); if (r.top < 70 || r.top > window.innerHeight - 80) window.scrollTo(0, Math.max(0, window.scrollY + r.top - 90)); }
  }
  var fail = function (e) { say(esc(e.message), true); };
  var money = function (n) { n = Number(n); return '$' + n.toLocaleString('en-US', n % 1 ? { minimumFractionDigits: 2, maximumFractionDigits: 2 } : {}); };     // $99, $69.30
  var plural = function (n, one, many) { return n === 1 ? one : many; };
  function nice(d) {                                                 // 2026-12-17 -> Dec 17 (the year only when it is not this one)
    var m = /^(\d{4})-(\d\d)-(\d\d)/.exec(d || '');
    return m ? MON[+m[2] - 1] + ' ' + (+m[3]) + (+m[1] !== new Date().getFullYear() ? ', ' + m[1] : '') : esc(d || '');
  }
  var STATE = { live: 'Live', review: 'Waiting for review', closed: 'Closed', rejected: 'Not accepted', expired: 'Expired', pending: 'Waiting for payment', paid: 'Paid',
    held: 'Starts after review', scheduled: 'Scheduled', ended: 'Ended', paused: 'Paused', verified: 'Verified', sent: 'New', accepted: 'Accepted', declined: 'Declined', active: 'On',
    refunded: 'Refunded', underpaid: 'Underpaid', cancelled: 'Cancelled' };
  var state = function (s, label) { return '<span class="state ' + esc(s) + '">' + esc(label || STATE[s] || s) + '</span>'; };
  var err = '<p class="acc-err" role="alert" hidden></p>';
  var cleanUrl = function () { try { history.replaceState(null, '', location.pathname); } catch (e) {} };
  // the top of a part: a small label, a headline in two weights, one sentence, and the part's main button on the right
  function head(label, title, text, action) {
    return '<header class="acc-ph"><div><p class="acc-lbl">' + label + '</p><h1 class="acc-t">' + title + '</h1>' + (text ? '<p class="acc-sub">' + text + '</p>' : '') + '</div>' +
      (action ? '<div class="acc-pa">' + action + '</div>' : '') + '</header>';
  }
  var part = function (title, inner, id) { return '<section class="acc-sec"' + (id ? ' id="acc-' + id + '"' : '') + '><h2 class="acc-h2">' + title + '</h2>' + inner + '</section>'; };
  var empty = function (title, text, action) { return '<div class="acc-none"><p><b>' + title + '</b>' + text + '</p>' + (action || '') + '</div>'; };
  var callout = function (text, action, cls) { return '<div class="acc-call' + (cls ? ' ' + cls : '') + '"><p>' + text + '</p>' + (action || '') + '</div>'; };
  var fileBtn = function (name, accept, label) {
    return '<span class="acc-file"><label class="btn ghost sm">' + label + '<input type="file" name="' + name + '" accept="' + accept + '"></label><span class="acc-file-n">No file chosen</span></span>';
  };
  var testNote = function () { return pub.payments === 'test' ? '<p class="note acc-test">Test mode: payments are simulated on this machine. No money moves.</p>' : ''; };
  var confirmLine = function (what) { return '<p class="acc-quiet">' + what + ' once your email is confirmed.</p>'; };

  /* ---------- signed out: who you are, then create an account or sign in (Google and LinkedIn when they are switched on), a new password ---------- */
  function drawAuth(mode) {
    if (hd) hd.hidden = true;
    var up = mode === 'up', google = pub.google === 'on', linked = pub.linkedin === 'on', emp = ROLE === 'employer';
    var typed = (root.querySelector('.acc-auth input[name=email]') || {}).value || '';
    var ban = notice ? '<div class="banner' + (noticeBad ? '' : ' ok') + '" role="status">' + notice + '</div>' : '';
    notice = ''; noticeBad = false;
    if (mode === 'link') {
      root.innerHTML = '<div class="acc-gate one"><div class="card acc-auth">' + ban + '<p class="acc-lbl">Sign in</p><h1 class="acc-t sm">Sign in <b>without a password</b></h1>' +
        '<p class="acc-sub">Enter the email of your account. We send a link to it; open it on this device and you are in. It works once, for 15 minutes.</p><form novalidate>' +
        field('Email', 'email', 'type="email" autocomplete="email" required value="' + esc(typed) + '"') + err + '<button class="btn primary lg wide" type="submit">Send me the link</button></form>' +
        '<p class="acc-alt"><a href="#" data-mode="in">Back to sign in</a></p></div></div>';
      submit(root.querySelector('form'), function (v) { return api('POST', '/api/auth/link/request', v).then(function (r) { flash(esc(r.message)); drawAuth('in'); }); });
    } else if (mode === 'forgot') {
      root.innerHTML = '<div class="acc-gate one"><div class="card acc-auth">' + ban + '<p class="acc-lbl">Password</p><h1 class="acc-t sm">Get a link to <b>a new password</b></h1>' +
        '<p class="acc-sub">Enter the email of your account. We send a link to it; open the link and choose a new password.</p><form novalidate>' +
        field('Email', 'email', 'type="email" autocomplete="email" required value="' + esc(typed) + '"') + err + '<button class="btn primary lg wide" type="submit">Send me the link</button></form>' +
        '<p class="acc-alt"><a href="#" data-mode="in">Back to sign in</a></p></div></div>';
      submit(root.querySelector('form'), function (v) { return api('POST', '/api/auth/reset/request', v).then(function (r) { flash(esc(r.message)); drawAuth('in'); }); });
    } else {
      var from = products.bump ? ', from ' + money(products.bump.usd) : '';
      var why = emp ? [['Free posting', '30 days in the lists and in search.'], ['Status and numbers for every job', 'Waiting, live or closed, with views and clicks on Apply day by day.'],
          ['Promotion in one click' + from, 'Pick one of your jobs from a list. One payment, nothing renews.'], ['Your company page', 'Your logo, your text and your open jobs.']]
        : [['Resumes', 'Up to ten versions, open in the builder on any device.'], ['Saved jobs and applications', 'What you save on your phone is on your computer too.'],
          ['Job alerts', 'New jobs for your search by email: within the hour, daily or weekly.'], ['Free', 'We do not ask for a phone number and do not sell your data.']];
      var who = function (r, name, what) { return '<button type="button" data-role="' + r + '" aria-pressed="' + (ROLE === r) + '"><b>' + name + '</b><span>' + what + '</span></button>'; };
      var seg = function (m, name) { return '<button type="button" role="tab" data-mode="' + m + '" aria-selected="' + (mode === m) + '">' + name + '</button>'; };
      root.innerHTML = '<div class="acc-gate"><div class="acc-pitch"><p class="acc-lbl"><i></i>Free account</p>' +
        '<h1 class="acc-t">' + (emp ? 'Post a job free and <b>see what it brings</b>' : 'Your resumes, saved jobs and alerts <b>on every device</b>') + '</h1>' +
        '<div class="acc-who" role="group" aria-label="What you are here for">' + who('seeker', 'I’m looking for a job', 'Resumes, saved jobs, alerts') + who('employer', 'I’m hiring', 'Post jobs, see views, promote') + '</div></div>' +
        '<div class="card acc-auth">' + ban + '<div class="acc-seg" role="tablist" aria-label="Create an account or sign in">' + seg('up', 'Create account') + seg('in', 'Sign in') + '</div>' +
        (google || linked ? '<div class="acc-sso">' + (google ? '<button class="btn sso" type="button" id="acc-google"><span class="sso-i g">G</span>Continue with Google</button>' : '') +
          (linked ? '<button class="btn sso" type="button" id="acc-li"><span class="sso-i in">in</span>Continue with LinkedIn</button>' : '') + '</div><p class="acc-or"><span>or with your email</span></p>' : '') +
        '<form novalidate aria-label="' + (up ? 'Create an account' : 'Sign in') + '">' +
        field(emp ? 'Work email' : 'Email', 'email', 'type="email" autocomplete="email" required value="' + esc(typed) + '"', up && emp ? 'Your address at your company (you@yourcompany.com): your jobs go live without waiting. A personal address works too; its jobs are read by a person first.' : '') +
        field('Password', 'password', 'type="password" autocomplete="' + (up ? 'new-password' : 'current-password') + '" required' + (up ? ' minlength="8"' : ''), up ? 'At least 8 characters.' : '') +
        (up && emp ? field('Company', 'company', 'type="text" autocomplete="organization" maxlength="80"', 'As it should read on the site. You can leave it empty for now.') : '') +
        err + '<button class="btn primary lg wide" type="submit">' + (up ? (emp ? 'Create employer account' : 'Create free account') : 'Sign in') + '</button></form>' +
        '<p class="acc-alt">' + (up ? 'Free. No card, no phone number. We send one link to confirm the address. <a href="' + esc(D.site) + '/privacy/">What we keep and why</a>' : (pub.email_link === 'on' ? '<a href="#" data-mode="link">Email me a sign-in link</a> · ' : '') + '<a href="#" data-mode="forgot">Forgot the password?</a>') + '</p></div>' +
        '<ul class="acc-why">' + why.map(function (x) { return '<li><b>' + x[0] + '</b><span>' + x[1] + '</span></li>'; }).join('') + '</ul></div>';
      submit(root.querySelector('form'), function (v) {
        return api('POST', up ? '/api/auth/signup' : '/api/auth/login', v).then(function (r) { token = r.token; H.set('hrn_token', token); fresh = !up; flash(''); return load(); });
      });
      var li = document.getElementById('acc-li');
      if (li) li.addEventListener('click', function () {
        li.disabled = true;
        api('POST', '/api/auth/linkedin/start', { signin: true }).then(function (r) { try { if (r.secret) sessionStorage.setItem('hrn_li', r.secret); } catch (e) {} location.href = r.url; }, function (e) { li.disabled = false; authSay(e.message); });
      });
      var g = document.getElementById('acc-google');
      if (g) g.addEventListener('click', function () {
        g.disabled = true;
        api('POST', '/api/auth/google/start').then(function (r) { try { sessionStorage.setItem('hrn_google', r.secret); } catch (e) {} location.href = r.url; }, function (e) { g.disabled = false; authSay(e.message); });
      });
    }
    Array.prototype.forEach.call(root.querySelectorAll('[data-mode]'), function (t) { t.addEventListener('click', function (ev) { ev.preventDefault(); drawAuth(t.getAttribute('data-mode')); }); });
    Array.prototype.forEach.call(root.querySelectorAll('[data-role]'), function (t) { t.addEventListener('click', function () { setRole(t.getAttribute('data-role')); drawAuth(mode === 'forgot' || mode === 'link' ? 'in' : mode); }); });
  }
  function authSay(msg) { var box = root.querySelector('.acc-auth .acc-err'); if (box) { box.textContent = msg; box.hidden = false; } }
  function drawReset(resetToken) {
    if (hd) hd.hidden = true;
    root.innerHTML = '<div class="acc-gate one"><div class="card acc-auth"><p class="acc-lbl">Password</p><h1 class="acc-t sm">Choose a <b>new password</b></h1><form novalidate>' +
      field('New password', 'password', 'type="password" autocomplete="new-password" required minlength="8"', 'At least 8 characters. Every browser signed in to the account is signed out.') +
      err + '<button class="btn primary lg wide" type="submit">Save the password</button></form><p class="acc-alt"><a href="#" data-mode="in">Back to sign in</a></p></div></div>';
    submit(root.querySelector('form'), function (v) {
      return api('POST', '/api/auth/reset/confirm', { token: resetToken, password: v.password }).then(function () { flash('Your new password is saved. Sign in with it.'); token = ''; me = null; H.set('hrn_token', ''); H.set('hrn_me_email', ''); told(); drawAuth('in'); });
    });
    Array.prototype.forEach.call(root.querySelectorAll('[data-mode]'), function (t) { t.addEventListener('click', function (ev) { ev.preventDefault(); drawAuth('in'); }); });
    window.scrollTo(0, 0);
  }
  function forget() { token = ''; me = null; H.set('hrn_token', ''); H.set('hrn_me_email', ''); H.set('hrn_job_draft', null); told(); }
  function signOut() {
    if (token) api('POST', '/api/auth/logout').catch(function () {});
    forget(); cleanUrl(); flash('You are signed out.'); drawAuth('in'); window.scrollTo(0, 0);
  }
  // the server no longer knows this sign-in (it ran out, or the password was changed elsewhere)
  function ended() {
    if (!token) return;
    forget(); flash('Your sign-in ran out. Sign in again to go on.', true); drawAuth('in'); window.scrollTo(0, 0);
  }
  document.addEventListener('hrn:signout', function () { if (token) signOut(); });      // "Sign out" in the header menu, pressed on this page

  /* ---------- signed in ---------- */
  function load() {
    return Promise.all([api('GET', '/api/me'), api('GET', '/api/public/products')]).then(function (r) {
      me = r[0].user; setPub(r[1]);
      var emp = me.posts_as.length > 0, talent = pub.talent === 'on';
      return Promise.all([quiet(api('GET', '/api/alerts'), { alerts: [] }), me.confirmed ? quiet(api('GET', '/api/sync'), { data: null }) : { data: null },
        talent ? quiet(api('GET', '/api/talent/profile'), { profile: null }) : null, talent ? quiet(api('GET', '/api/talent/requests'), { requests: [] }) : null,
        quiet(api('GET', '/api/jobs'), { jobs: [] }), quiet(api('GET', '/api/placements'), { placements: [] }), quiet(api('GET', '/api/orders'), { orders: [] }),
        emp ? quiet(api('GET', '/api/claims'), { claims: [] }) : null, emp ? quiet(api('GET', '/api/team'), { members: [] }) : null, quiet(api('GET', '/api/domain'), {}),
        talent && emp ? quiet(api('GET', '/api/talent/sent'), { requests: [], credits: 0 }) : null,
        me.confirmed ? quiet(api('GET', '/api/resumes'), { resumes: [], max: 10 }) : { resumes: [], max: 10 }, quiet(api('GET', '/api/billing'), null)]);
    }).then(function (r) {
      if (!me) return;                                                // signed out while the answers were on their way
      S = { alerts: r[0].alerts, sync: r[1], talent: r[2], incoming: r[3] ? r[3].requests : [], jobs: r[4].jobs, placements: r[5].placements, orders: r[6].orders,
        claims: r[7] ? r[7].claims : [], team: r[8], domain: r[9] || {}, sent: r[10], resumes: r[11], billing: r[12] };
      H.set('hrn_me_email', me.email); H.set('hrn_known', 1);
      if (usedLink && me.confirmed) flash('Your email is confirmed already. There is nothing more to do.');      // the link from the letter, pressed a second time
      usedLink = false;
      if (fresh && ROLE === 'seeker' && S.jobs.length) { ROLE = 'employer'; H.set('hrn_role', ROLE); }     // signing in to an account that posts jobs opens the employer side
      fresh = false;
      told();
      autoSync();
      draw();
    });
  }

  /* saved jobs, statuses, searches and follows: kept the same on every device by themselves, merged, never one copy over the other */
  function mergeLists(a, b) {
    if (Array.isArray(a) && Array.isArray(b)) { var seen = {}, out = []; a.concat(b).forEach(function (x) { var k = JSON.stringify(x); if (!seen[k]) { seen[k] = 1; out.push(x); } }); return out; }
    if (a && b && typeof a === 'object' && typeof b === 'object') return Object.assign({}, a, b);
    return b != null ? b : a;
  }
  function autoSync() {
    if (!me.confirmed) return;
    var srv = (S.sync && S.sync.data) || {}, merged = {}, changed = false;
    SYNC_KEYS.forEach(function (k) {
      var v = mergeLists(srv[k], H.get(k, null));
      if (v == null) return;
      merged[k] = v;
      if (JSON.stringify(v) !== JSON.stringify(srv[k])) changed = true;
      H.set(k, v);
    });
    if (changed) api('PUT', '/api/sync', { data: merged }).then(function (r) { S.sync = { data: merged, updated: r.updated }; }, function () {});
  }
  // the person's own numbers, counted from what My jobs keeps (the same lists that are synced)
  function tally() {
    var jobs = H.get('hrn_jobs', {}) || {}, saved = 0, applied = 0;
    Object.keys(jobs).forEach(function (k) { var st = jobs[k] && jobs[k].st; if (st === 'saved') saved++; else if (st) applied++; });
    return { saved: saved, applied: applied, searches: (H.get('hrn_searches', []) || []).length, follows: Object.keys(H.get('hrn_follow', {}) || {}).length };
  }
  var nums = function (list) { return '<div class="acc-nums">' + list.map(function (x) { return '<a href="' + x[2] + '"><b>' + Number(x[0]).toLocaleString('en-US') + '</b><span>' + x[1] + '</span></a>'; }).join('') + '</div>'; };

  /* ---------- the first screen: what needs you, your own numbers, what to do next ---------- */
  function overview() {
    var emp = ROLE === 'employer', ups = [], steps = [], soon = new Date(Date.now() + 5 * 86400000).toISOString().slice(0, 10), row;
    var up = function (kind, text, href, label) { ups.push('<li class="up-' + kind + '"><span>' + text + '</span>' + (href ? '<a href="' + href + '">' + label + '</a>' : '') + '</li>'); };
    S.orders.forEach(function (o) { if (o.status === 'pending' && o.pay_url) up('warn', 'Waiting for payment: <b>' + esc(o.name) + '</b>' + (o.label && o.label !== o.name ? ' for ' + esc(o.label) : '') + '.', esc(o.pay_url), 'Pay now'); });
    if (emp) {
      var live = 0, wait = 0, views = 0, applies = 0;
      S.jobs.forEach(function (j) {
        if (j.status === 'live') live++; if (j.status === 'review') wait++; views += j.views || 0; applies += j.applies || 0;
        if (j.status === 'rejected') up('bad', '<b>' + esc(j.title) + '</b> was not accepted' + (j.reject_reason ? ': ' + esc(j.reject_reason) : '') + '.', '#jobs', 'Edit or delete it');
        else if (j.status === 'review') up('wait', '<b>' + esc(j.title) + '</b> is waiting for a quick check by a person, usually within a day. You get an email either way.', '#jobs', 'See it');
        else if (j.status === 'live' && j.until && j.until <= soon) up('warn', '<b>' + esc(j.title) + '</b> leaves the site on ' + nice(j.until) + '.', '#jobs', 'Keep it up');
        else if (j.status === 'expired' || j.status === 'closed') up('wait', '<b>' + esc(j.title) + '</b> is ' + (j.status === 'expired' ? 'off the site: its 30 days ran out' : 'closed') + '.', '#jobs', 'Publish again');
      });
      S.placements.forEach(function (p) {
        if (p.state === 'held') up('wait', 'Your <b>' + esc(KIND[p.kind] || p.kind) + '</b> for ' + esc(p.label) + ' is paid and starts the moment the job is approved.', '#billing', 'Details');
        else if (p.state === 'live') up('ok', 'Your <b>' + esc(KIND[p.kind] || p.kind) + '</b> for ' + esc(p.label) + ' is running until ' + nice(p.until) + '.', '#billing', 'Details');
      });
      S.claims.forEach(function (c) {
        if (c.status === 'pending') up('wait', 'Your claim of the <b>' + esc(c.company) + '</b> page is being checked by a person.', '#company', 'See it');
        else if (c.status === 'rejected') up('bad', 'Your claim of the <b>' + esc(c.company) + '</b> page was not accepted' + (c.reason ? ': ' + esc(c.reason) : '') + '.', '#company', 'See it');
      });
      row = nums([[live, plural(live, 'job live', 'jobs live'), '#jobs'], [wait, 'waiting for review', '#jobs'], [views, plural(views, 'view of your jobs', 'views of your jobs'), '#jobs'], [applies, plural(applies, 'click on Apply', 'clicks on Apply'), '#jobs']]);
      if (!S.jobs.length) steps.push(['Post your first job', 'Free for 30 days. Its status, views and clicks on Apply show here.', '#post']);
      if (!me.verified) steps.push(['Add your work email', 'Jobs from a company address go live without the wait.', '#hiring']);
      if (S.jobs.some(function (j) { return j.status === 'live' || j.status === 'review'; }) && !S.placements.length && products.featured) steps.push(['Promote a job', 'More views and clicks on Apply' + (products.bump ? ', from ' + money(products.bump.usd) : '') + '. One payment, nothing renews.', '#promote']);
      if (me.verified && !S.claims.length) steps.push(S.jobs.length ? ['Claim your company page', 'Your logo and text on it, and views and clicks for every job.', '#company'] :
        ['Your company page', 'It is made with your first job. A company the site already lists can claim its page now.', '#company']);
      else if (S.claims.some(function (c) { return c.status === 'verified' && c.page && !c.page.logo && !c.page.about; })) steps.push(['Add your logo and a few lines about the company', 'They show on your company page and next to your jobs.', '#company']);
    } else {
      var t = tally(), nres = S.resumes ? S.resumes.resumes.length : 0;
      (S.incoming || []).forEach(function (q) { if (q.status === 'sent') up('warn', '<b>' + esc(q.company) + '</b> asked to contact you about a job.', '#talent', 'Answer'); });
      row = nums([[t.saved, plural(t.saved, 'saved job', 'saved jobs'), '#saved'], [t.applied, plural(t.applied, 'application', 'applications'), '#saved'], [nres, plural(nres, 'resume', 'resumes'), '#resumes'], [S.alerts.length, plural(S.alerts.length, 'job alert', 'job alerts'), '#alerts']]);
      if (!nres) steps.push(['Keep your resume here', 'Make it in the free builder, then press “Save to my account”.', '#resumes']);
      if (!S.alerts.length) steps.push(['Get new jobs by email', 'Choose the words and how often. One click stops it.', '#alerts']);
      if (!t.saved && !t.applied) steps.push(['Save the jobs you like', 'Press Save on a job: it is here and on your phone too.', esc(D.site) + '/jobs/']);
      if (pub.talent === 'on' && S.talent && !S.talent.profile) steps.push(['Let employers find you', 'Only if you tick the box. Your name and contacts stay hidden until you accept a request.', '#talent']);
      setTimeout(fillFit, 0);
    }
    return head(emp ? 'Employer account' : 'Job seeker account', emp ? 'Your hiring <b>at a glance</b>' : 'Your job search <b>at a glance</b>', '',
        emp ? '<a class="btn primary" href="#post">Post a job</a>' : '<a class="btn primary" href="' + esc(D.site) + '/jobs/">Search jobs</a>') +
      (ups.length ? '<ul class="acc-ups">' + ups.slice(0, 12).join('') + '</ul>' : '') + row +
      (steps.length ? part('Next steps', '<ul class="acc-steps">' + steps.map(function (x) { return '<li><a href="' + x[2] + '"><b>' + x[0] + '</b><span>' + x[1] + '</span></a></li>'; }).join('') + '</ul>') : '') +
      (emp ? '' : '<div id="acc-fit" hidden></div>');
  }
  /* Jobs that fit you, in the job seeker's overview (plan, part 2 item 3, 20 Nov 2026: other sites show matches in the account; ours did
     not). From the answers given on For you, kept in this browser, matched against today's open jobs here: nothing is sent anywhere. */
  function fillFit() {
    var box = document.getElementById('acc-fit'); if (!box) return;
    var p = H.get('hrn_profile', null) || {}, cats = p.cats || [], skills = p.skills || [], pay = Number(p.pay) || 0;
    if (!cats.length && !skills.length && !p.where && !pay) {
      box.innerHTML = part('Jobs that fit you', '<p class="acc-sub">Answer five questions on <a href="' + esc(D.site) + '/for-you/">For you</a>: the newest jobs that fit your answers then show here.</p>');
      box.hidden = false; return;
    }
    H.load().then(function (rows) {
      var fit = rows.filter(H.fitTest(p)).sort(function (a, b) { return (b[16] || 0) - (a[16] || 0); });
      box.innerHTML = part('Jobs that fit you', fit.length
        ? '<p class="acc-sub">' + fit.length.toLocaleString('en-US') + ' open jobs fit your answers on For you. The newest:</p><ul class="jobs">' + fit.slice(0, 5).map(function (j) { return H.card(j); }).join('') + '</ul>' +
          '<p><a href="' + esc(D.site) + '/for-you/">See all of them, or change your answers</a></p>'
        : '<p class="acc-sub">No open job fits all your answers today. <a href="' + esc(D.site) + '/for-you/">Loosen one of them on For you</a>.</p>');
      box.hidden = false;
      if (H.decorate) H.decorate(box);
    }).catch(function () {});
  }

  /* ---------- job seeker: saved jobs on every device, resumes, the resume for employers, job alerts ---------- */
  function savedPanel() {
    var t = tally(), any = t.saved + t.applied + t.searches + t.follows, synced = S.sync && S.sync.updated ? new Date(S.sync.updated * 1000).toISOString().slice(0, 10) : '';
    return head('Saved jobs', 'Saved jobs and <b>applications</b>', 'What you save, the status of each application, your saved searches and the companies you follow. The full list is on My jobs.',
        any ? '<a class="btn primary" href="' + esc(D.site) + '/my-jobs/">Open My jobs</a>' : '') +
      (any ? nums([[t.saved, plural(t.saved, 'saved job', 'saved jobs'), esc(D.site) + '/my-jobs/'], [t.applied, plural(t.applied, 'application', 'applications'), esc(D.site) + '/my-jobs/'],
          [t.searches, plural(t.searches, 'saved search', 'saved searches'), esc(D.site) + '/my-jobs/'], [t.follows, plural(t.follows, 'company followed', 'companies followed'), esc(D.site) + '/my-jobs/']])
        : empty('Nothing saved yet.', ' Press Save on any job, or mark it as applied: it shows here and in every browser where you sign in.', '<a class="btn primary" href="' + esc(D.site) + '/jobs/">Search jobs</a>')) +
      (me.confirmed ? '<p class="acc-synced"><b>Synced on all your devices.</b> ' + (synced ? 'Last change kept ' + nice(synced) + '.' : 'Nothing to keep yet.') + '</p>' +
        '<details class="acc-more"><summary>Sync by hand</summary><p class="note">The lists merge by themselves each time you open this page. These two buttons are for the rare case when one browser has the wrong copy.</p>' +
        '<p class="acc-btns"><button class="btn ghost sm" type="button" id="sync-up">Copy this browser’s lists to my account</button> <button class="btn ghost sm" type="button" id="sync-down">Replace this browser’s lists with my account’s</button></p></details>'
        : confirmLine('Your lists stay in this browser for now. They follow you to other devices'));
  }
  function resumesPanel() {
    var R = S.resumes || { resumes: [], max: 10 }, local = H.get('hrn_resume', null), n = R.resumes.length;
    var builder = '<a class="btn' + (n || local ? ' ghost' : ' primary') + '" href="' + esc(D.site) + '/resume/">' + (n || local ? 'Open the resume builder' : 'Make a resume, free') + '</a>';
    var save = !me.confirmed ? '' : local ? '<form id="res-save" class="card acc-inline" novalidate><p class="acc-inline-t"><b>The resume in the builder on this device</b>' + (local.title || local.name ? ': ' + esc(local.title || local.name) : '') + '. ' + (n ? 'Save it as a new version whenever you change it.' : 'It is not in your account yet.') + '</p>' +
      field('Name for this version', 'name', 'type="text" maxlength="60" value="' + esc(String(local.title || 'Resume').slice(0, 40)) + ' · ' + new Date().toISOString().slice(0, 10) + '"') + err +
      '<button class="btn' + (n ? ' ghost' : ' primary') + '" type="submit">' + (n ? 'Save as a new version' : 'Save it to my account') + '</button></form>' : '';
    var list = n ? '<div class="acc-list">' + R.resumes.map(function (r) {
      return '<div class="acc-row"><span class="rs-i" aria-hidden="true">CV</span><div class="main"><strong>' + esc(r.name) + '</strong><span class="js">' + (r.title ? esc(r.title) + ' · ' : '') + 'updated ' + nice(r.updated) + '</span></div>' +
        '<div class="ctl"><button class="btn ghost sm" type="button" data-res-open="' + esc(r.id) + '">Open in the builder</button><button class="btn ghost sm" type="button" data-res-del="' + esc(r.id) + '">Delete</button></div></div>';
    }).join('') + '</div>' : '';
    var none = n ? '' : !me.confirmed ? confirmLine('Your resumes are kept here') : local ? '' :
      empty('No resume yet.', ' Make one in the free builder, then press “Save to my account” there: it is kept here and opens on any device.', builder);
    return head('Resumes', 'Your <b>resumes</b>', 'Up to ' + R.max + ' versions, one for each kind of job you apply for. Open any of them in the builder on any device.', n || local || !me.confirmed ? builder : '') +
      save + list + none + talentPart();
  }
  // the resume employers can find: off until the person ticks the box, and then without a name or contacts until they accept a request
  function talentPart() {
    if (!(pub.talent === 'on' && S.talent)) return '';
    var t = S.talent.profile, local = H.get('hrn_resume', null), inner;
    if (!t) {
      inner = !local ? '<p class="acc-quiet">Off. Make your resume in the builder first; then you can switch this on here.</p>' :
        '<details class="acc-fold"><summary><b>Off.</b> Employers cannot see your resume. <span class="acc-fold-a">Set it up</span></summary>' +
        '<form id="talent-on" novalidate><p>Your resume stays in this browser unless you tick the box below. Employers then see it without your name, email, phone or links, and get your name and contact details only if you accept their request.</p>' +
        '<label class="check"><input type="checkbox" name="consent" required data-need="Tick the box first: nothing is stored without it."> <span>' + esc(S.talent.consent_text) + '</span></label>' + talentFields(null) + err +
        '<p class="acc-btns"><button class="btn primary" type="submit">Let employers find my resume</button></p></form></details>';
    } else {
      inner = '<div class="acc-fold open"><p class="acc-fold-h"><b>' + (t.paused ? 'Paused: employers cannot find it.' : 'On: employers can find your resume.') + '</b> Since ' + nice(t.consented) + ', updated ' + nice(t.updated) + '.</p>' +
        '<p class="note">Employers see: ' + esc(t.as_employers_see.headline || 'your headline') + ' · ' + esc(t.as_employers_see.skills.slice(0, 8).join(', ')) + (t.as_employers_see.name ? ' · ' + esc(t.as_employers_see.name) : ' · no name') + '.</p>' +
        '<p class="acc-btns">' + (local ? '<button class="btn ghost sm" type="button" id="talent-update">Update it with my current resume</button>' : '') +
        '<button class="btn ghost sm" type="button" id="talent-pause">' + (t.paused ? 'Show it again' : 'Pause') + '</button><button class="btn ghost sm" type="button" id="talent-del">Delete it for good</button></p>' +
        '<details class="acc-more"><summary>Change who finds it and what they see</summary><form id="talent-set" novalidate>' + talentFields(t) + err +
        '<p class="acc-btns"><button class="btn ghost" type="submit">Save these settings</button></p></form></details></div>';
    }
    if (S.incoming.length) inner += '<h3 class="acc-h3">Employers who asked to contact you</h3><div class="acc-list">' + S.incoming.map(function (q) {
      return '<div class="acc-row"><div class="main">' + state(q.status) + ' <strong>' + esc(q.company) + '</strong> <span class="js">' + esc(q.domain) + ' · ' + nice(q.received) + '</span><p class="acc-msg">' + esc(q.message) + '</p>' +
        (q.job_url ? '<a class="tt" href="' + esc(q.job_url) + '" rel="noopener">The job</a>' : '') + '</div><div class="ctl">' + (q.status === 'sent' ? '<button class="btn sm" type="button" data-q="accept" data-id="' + esc(q.id) + '">Accept</button><button class="btn ghost sm" type="button" data-q="decline" data-id="' + esc(q.id) + '">Decline</button>' : '') + '</div></div>';
    }).join('') + '</div><p class="note">Accepting gives that employer your name and contact details. Declining, or not answering in 14 days, tells it nothing about you.</p>';
    return part('Let employers find you', inner, 'talent');
  }
  function talentFields(t) {
    var has = function (list, v) { return (list || []).indexOf(v) >= 0; };
    return '<div class="acc-two"><label class="fld"><span class="fld-l">Level</span><select name="level"><option value="">Not said</option>' + ['entry', 'mid', 'senior', 'lead'].map(function (l) {
      return '<option' + (t && t.level === l ? ' selected' : '') + '>' + l + '</option>'; }).join('') + '</select></label>' +
      field('Years of experience', 'years', 'type="number" min="0" max="60" value="' + (t ? t.years : 0) + '"') + '</div>' +
      '<fieldset class="fld acc-roles"><legend>Kinds of work to be found for (up to 5)</legend>' + D.categories.map(function (c) {
        return '<label><input type="checkbox" data-many name="roles" value="' + esc(c[0]) + '"' + (t && has(t.roles, c[0]) ? ' checked' : '') + '> ' + esc(c[1]) + '</label>'; }).join('') + '</fieldset>' +
      field('Places, as on the site (comma separated)', 'places', 'type="text" value="' + esc(t ? t.places.join(', ') : 'remote') + '" placeholder="remote, germany, london"', 'Place names from the locations pages, and “remote”.') +
      field('Companies that must never see it', 'blocked', 'type="text" value="' + esc(t ? t.blocked.join(', ') : '') + '" placeholder="yourcurrentemployer.com"', 'Their web addresses, comma separated: your current employer, say.') +
      '<label class="check"><input type="checkbox" name="show_name"' + (t && t.show_name ? ' checked' : '') + '> <span>Show my name before I accept a request</span></label>' +
      '<label class="check"><input type="checkbox" name="show_employers"' + (t && t.show_employers ? ' checked' : '') + '> <span>Show the names of my employers</span></label>';
  }
  var talentValues = function (v) { return { level: v.level, years: Number(v.years) || 0, roles: v.roles || [], places: v.places.split(/[\s,]+/).filter(Boolean).map(function (x) { return x.toLowerCase(); }),
    blocked: v.blocked.split(/[\s,]+/).filter(Boolean), show_name: !!v.show_name, show_employers: !!v.show_employers }; };
  var FREQ = [['daily', 'Once a day'], ['weekly', 'Once a week'], ['instant', 'Within the hour']];
  function alertsPanel() {
    var freq = function (cur, attr) { return '<select ' + attr + '>' + FREQ.map(function (f) { return '<option value="' + f[0] + '"' + (cur === f[0] ? ' selected' : '') + '>' + f[1] + '</option>'; }).join('') + '</select>'; };
    var form = !me.confirmed ? confirmLine('You can make alerts here') :
      '<form id="alert-new" class="card acc-form" novalidate><h2 class="acc-h2">' + (S.alerts.length ? 'New alert' : 'Your first alert') + '</h2><div class="acc-two">' + field('Words in the job', 'q', 'type="text" maxlength="80" placeholder="python, nurse, product manager"') +
      '<label class="fld"><span class="fld-l">Kind of work</span><select name="cat"><option value="">Any</option>' + D.categories.map(function (c) { return '<option value="' + esc(c[0]) + '">' + esc(c[1]) + '</option>'; }).join('') + '</select></label>' +
      '<label class="fld"><span class="fld-l">Place</span><select name="loc"><option value="">Anywhere</option></select></label>' +
      '<label class="fld"><span class="fld-l">How often</span>' + freq('daily', 'name="freq"') + '</label></div>' +
      '<label class="check"><input type="checkbox" name="remote"> <span>Remote jobs only</span></label>' + err +
      '<p class="acc-btns"><button class="btn primary" type="submit">Create the alert</button></p></form>';
    var list = S.alerts.length ? '<div class="acc-list">' + S.alerts.map(function (a) {
      var pending = a.status === 'pending', paused = a.status === 'paused';
      return '<div class="acc-row"><div class="main"><a class="tt" href="' + esc(a.search) + '">' + esc(a.alert) + '</a><span class="js">' + (pending ? state('pending', 'Confirm it in your inbox') : paused ? state('paused') : state('active')) + ' ' +
        (a.letters ? a.letters + plural(a.letters, ' letter', ' letters') + ' so far' : 'no letter yet') + ' · since ' + nice(a.created) + '</span></div><div class="ctl">' +
        (pending ? '' : '<label class="acc-mini"><span>How often</span>' + freq(a.freq, 'data-alert-freq="' + esc(a.id) + '"') + '</label><button class="btn ghost sm" type="button" data-alert-pause="' + esc(a.id) + '" data-on="' + (paused ? '0' : '1') + '">' + (paused ? 'Switch on' : 'Pause') + '</button>') +
        '<button class="btn ghost sm" type="button" data-alert-del="' + esc(a.id) + '">Delete</button></div></div>';
    }).join('') + '</div>' : '';
    return head('Job alerts', 'New jobs <b>by email</b>', 'Each alert is a search we run for you. It comes as often as you choose, and every letter has a one-click unsubscribe.') +
      (S.alerts.length ? part('Your alerts', list) + form : (me.confirmed ? '<p class="acc-quiet"><b>No alerts yet.</b> Make the first one here, or search on the site and press “Free job alerts” under the results.</p>' : '') + form);
  }

  /* ---------- employer: your jobs with their status and numbers, posting, promotion, the company page, the team, resume search, billing ---------- */
  var WHY = [[/not trusted yet/, 'the first jobs of a new account are always read by a person'], [/not verified yet/, 'your account is not tied to a company address yet'],
    [/does not show this job title/, 'the page at your link does not show this job title, so a person checks that it is the right job']];
  function plainWhy(s) { for (var i = 0; i < WHY.length; i++) if (WHY[i][0].test(s)) return WHY[i][1]; return s; }
  function jobFields(j, own) {
    var val = function (k) { return ' value="' + esc(j[k] || '') + '"'; };
    return '<div class="acc-two">' + field('Company', 'company', 'type="text" maxlength="80" required data-need="Enter the company name."' + val('company')) +
      field('Company site', 'company_url', 'type="url" placeholder="https://yourcompany.com" required' + val('company_url'), own ? 'On ' + esc(own) + ', the domain of your account.' : '') +
      field('Job title', 'title', 'type="text" maxlength="120" required data-need="Enter the job title."' + val('title')) +
      field('Link where people apply', 'apply_url', 'type="url" placeholder="https://" required' + val('apply_url'), 'The page of this exact job on your site or hiring system.') +
      field('Location', 'location', 'type="text" maxlength="120" placeholder="Berlin, or Remote, Europe"' + val('location')) +
      field('Salary range (optional)', 'salary', 'type="text" maxlength="60" placeholder="$120K - $150K"' + val('salary'), 'Jobs with a range are found by people who filter by pay.') +
      '<label class="fld"><span class="fld-l">Employment type</span><select name="etype"><option value="">Not specified</option>' + ['Full-time', 'Contract', 'Part-time', 'Internship'].map(function (x) {
        return '<option' + (j.etype === x ? ' selected' : '') + '>' + x + '</option>'; }).join('') + '</select></label>' +
      '<label class="check acc-remote"><input type="checkbox" name="remote"' + (j.remote ? ' checked' : '') + '> <span>This job is remote</span></label></div>' +
      '<label class="fld"><span class="fld-l">About the role</span><textarea name="description" rows="7" minlength="80" maxlength="1500" required data-need="Describe the role in 80 to 1,500 characters." ' +
      'placeholder="What the person will do, with whom, and what you need from them.">' + esc(j.description || '') + '</textarea><span class="hint acc-count" data-count>80 to 1,500 characters.</span></label>';
  }
  function jobsPanel() {
    var soon = new Date(Date.now() + 5 * 86400000).toISOString().slice(0, 10);
    var cards = S.jobs.map(function (j) {
      var live = j.status === 'live', rev = j.status === 'review', rej = j.status === 'rejected', off = j.status === 'closed' || j.status === 'expired', ending = live && j.until && j.until <= soon;
      var line = rev ? 'A person reads it before it appears, usually within a day. You get an email either way.' + (j.review_reason ? ' Why it waits: ' + esc(plainWhy(j.review_reason)) + '.' : '') :
        rej ? '<b>Not accepted' + (j.reject_reason ? ':</b> ' + esc(j.reject_reason) + '.' : '.</b>') + ' Edit it to send it again, or delete it.' :
        j.status === 'expired' ? 'Its 30 days ran out on ' + nice(j.until) + '. Publish it again for 30 more days, free.' :
        j.status === 'closed' ? 'You closed it. Publish it again any time before ' + nice(j.until) + '.' :
        ending ? '<b>Leaves the site on ' + nice(j.until) + '.</b> Keep it for 30 more days, free.' : 'On the site until ' + nice(j.until) + '.';
      var days = (j.by_day || []).map(function (d) { return typeof d === 'number' ? d : (d && d.views) || 0; }), mx = Math.max.apply(null, days.concat([1]));      // the server sends { day, views, applies } for each of the last days
      var spark = days.some(function (v) { return v > 0; }) ? '<span class="spark" role="img" aria-label="Views a day, last ' + days.length + ' days" title="Views a day, last ' + days.length + ' days">' + days.map(function (v) { return '<i style="height:' + Math.max(6, Math.round(100 * v / mx)) + '%"></i>'; }).join('') + '</span>' : '';
      // one filled button per job, and only when the job needs something from its owner; the rest are quiet
      var acts = ending ? '<button class="btn sm" type="button" data-act="renew" data-id="' + esc(j.id) + '">Keep it 30 more days</button>' :
        off ? '<button class="btn sm" type="button" data-act="renew" data-id="' + esc(j.id) + '">Publish again</button>' : '';
      if ((live || rev) && products.featured) acts += '<button class="btn ghost sm" type="button" data-promote="' + esc(j.id) + '">Promote</button>';
      acts += '<button class="btn ' + (rej ? '' : 'ghost ') + 'sm" type="button" data-job-edit="' + esc(j.id) + '" aria-expanded="false">' + (rej ? 'Edit and send again' : 'Edit') + '</button>';
      if (live || rev) acts += '<button class="btn ghost sm" type="button" data-act="close" data-id="' + esc(j.id) + '">Close</button>';
      acts += '<button class="btn ghost sm" type="button" data-job-copy="' + esc(j.id) + '">Post a similar job</button>';
      acts += '<button class="btn ghost sm" type="button" data-job-del="' + esc(j.id) + '">Delete</button>';
      return '<article class="acc-job' + (rej ? ' bad' : '') + '"><div class="acc-job-h"><div>' + state(ending ? 'pending' : j.status, ending ? 'Ends soon' : '') + '<h2 class="acc-job-t">' +
        (live ? '<a href="' + esc(D.site + j.page) + '">' + esc(j.title) + '</a>' : esc(j.title)) + '</h2><p class="js">' + esc(j.company) + (j.location ? ' · ' + esc(j.location) : '') + (j.remote ? ' · Remote' : '') + ' · posted ' + nice(j.posted) + '</p></div>' +
        (live || j.views || j.applies ? '<div class="acc-job-n"><span><b>' + (j.views || 0) + '</b>' + plural(j.views || 0, 'view', 'views') + '</span><span><b>' + (j.applies || 0) + '</b>' + plural(j.applies || 0, 'click on Apply', 'clicks on Apply') + '</span>' + spark + '</div>' : '') + '</div>' +
        '<p class="acc-job-s">' + line + '</p><div class="ctl">' + acts + '</div>' +
        '<form class="job-edit" data-id="' + esc(j.id) + '" novalidate hidden><h3 class="acc-h3">Edit “' + esc(j.title) + '”</h3>' + jobFields(j, me.domain) + err +
        '<p class="acc-btns"><button class="btn primary" type="submit">' + (rej ? 'Save and send again' : 'Save the changes') + '</button><button class="btn ghost" type="button" data-job-cancel="' + esc(j.id) + '">Cancel</button></p>' +
        '<p class="note">' + (rej ? 'It goes to a person again, with your changes.' : 'A changed title, link or text may send the job to a person again before it shows.') + '</p></form></article>';
    }).join('');
    return head('Your jobs', 'Jobs <b>you posted</b>', S.jobs.length ? 'The status of each job, and what it brought: views of its page and clicks on Apply, each visitor counted once a day.' : '',
        S.jobs.length ? '<a class="btn primary" href="#post">Post a job</a>' : '') +
      (S.jobs.length ? cards + '<p class="note">A new or changed job shows on the site after its next update, within the hour. <button class="linkbtn" type="button" id="jobs-csv">Download these figures (CSV)</button></p>'
        : empty('You have not posted a job yet.', ' Posting is free for 30 days. Its status, views and clicks on Apply show here.', '<a class="btn primary" href="#post">Post a job free</a>'));
  }
  function postPanel() {
    if (me.confirmed && !me.can_post) return head('Post a job', 'Post a job, <b>free for 30 days</b>', '') + callout('This account cannot post jobs. If you think that is a mistake, write to the address on the contact page.', '');
    var draft = { company: me.company || '', company_url: me.domain ? 'https://' + me.domain : '' };
    var boosts = products.featured ? '<fieldset class="fld acc-boost"><legend>How many people should see it</legend>' +
      '<label><input type="radio" name="boost" value="" checked><span><b>Free</b>30 days in the lists and in search</span></label>' +
      '<label><input type="radio" name="boost" value="featured"><span><b data-cost="featured" data-name="Standard boost">' + boostName('featured', 'Standard boost') + '</b>Highlighted and above the free jobs for ' + (products.featured.days || 30) + ' days</span></label>' +
      (products.premium ? '<label><input type="radio" name="boost" value="premium"><span><b data-cost="premium" data-name="Premium">' + boostName('premium', 'Premium') + '</b>Top of its lists, “Urgently hiring”, your logo and an invitation to matching job seekers</span></label>' : '') +
      '</fieldset>' + promoBox(false) : '';
    return head('Post a job', 'Post a job, <b>free for 30 days</b>', 'We check that the job is not on the site already and open your link to see that it is really there.') +
      (!me.confirmed ? '<p class="acc-quiet">You can fill the job in now: it is kept in this browser. Publishing opens once your email is confirmed.</p>' :
        !me.verified && !me.posts_as.length ? callout('<b>You can post now.</b> Jobs from a personal address (Gmail and the like) are read by a person before they go live, usually within a day. With your work email they go live without the wait.', '<a class="btn ghost sm" href="#hiring">Add my work email</a>', 'soft') : '') +
      '<div class="card acc-paste"><label class="fld"><span class="fld-l">Have the posting as text? Paste it and the form fills itself</span>' +
      '<textarea id="job-paste" rows="4" placeholder="The whole posting, as it is on your site or in your message: the title on the first line, then the text."></textarea>' +
      '<span class="hint">The title, place, pay, employment type and the link are read from it right here in your browser; nothing is sent anywhere. Check each field after.</span></label>' +
      '<p class="acc-btns"><button class="btn ghost" type="button" id="job-paste-go">Fill the form from this text</button><span class="note" id="job-paste-out" role="status"></span></p></div>' +
      '<form class="card acc-form" id="acc-job" novalidate>' + jobFields(draft, me.domain) + boosts + err +
      '<p class="acc-btns"><button class="btn primary lg" type="submit" id="acc-publish">' + (me.confirmed ? 'Publish the job' : 'Check the job') + '</button></p>' +
      '<p class="note">Posting is free for 30 days' + (boosts ? '; a boost is one payment, and nothing renews' : '') + '. The first jobs of a new account are read by a person before they appear, usually within a day.' + (pub.payments === 'test' && boosts ? ' Test mode: payments are simulated on this machine, no money moves.' : '') + '</p></form>' +
      (!me.verified ? hiringPart() : '');
  }
  // an account with no company domain yet: how to get one (the site's own rules for who may post)
  function hiringPart() {
    var sentTo = S.domain && S.domain.pending_email ? S.domain.pending_email.email : '';
    return part('Tie the account to your company', '<p class="acc-sub">Add your work email and press the link we send to it: your jobs then go live without waiting. One minute, nothing to install.</p>' +
      (sentTo ? callout('A link is on its way to <b>' + esc(sentTo) + '</b>. Open it to finish.', '', 'soft') : '') +
      '<form class="card acc-inline" id="work-email" novalidate>' + field('Your work email', 'email', 'type="email" autocomplete="email" placeholder="you@yourcompany.com" required') + err + '<button class="btn ghost" type="submit">Send me the link</button></form>' +
      '<details class="acc-more"><summary>Other ways to show the company is yours</summary><form class="card acc-form" id="domain" novalidate>' + field('Your company’s domain', 'domain', 'type="text" placeholder="yourcompany.com" required') + err +
      '<p class="acc-btns"><button class="btn ghost" type="submit">Get the code to publish</button></p><div id="domain-out"></div></form></details>' +
      (pub.linkedin === 'on' && !me.linkedin ? '<p><button class="btn ghost li-start" type="button">Recruiter? Attach your LinkedIn profile</button></p>' : ''), 'hiring');
  }
  /* ---------- promo codes: the server prices them (POST /api/orders/quote); the page only shows its answer and sends the code with the order ---------- */
  var cut = function (id) { return promo && promo.quotes[id] || null; };
  function priceHtml(id) {                                           // "$69.30 $99" with the old price struck through, while a code covers the product
    var p = products[id], q = cut(id);
    return (q ? money(q.amount_usd) + ' <s>' + money(p.usd) + '</s>' : money(p.usd)) + (!p.credits && p.days ? ' <small>for ' + p.days + ' days</small>' : '');
  }
  function boostName(id, name) { var q = cut(id); return esc(name) + ' · ' + (q ? money(q.amount_usd) + ' <s>' + money(q.full_usd) + '</s>' : money(products[id].usd)); }
  function promoSaid() {
    if (!promo) return '';
    var f = promo.quotes.featured;
    return '<b>' + esc(promo.code) + '</b>: ' + promo.percent + '% off' + (f ? '. Standard boost: <b>' + money(f.amount_usd) + '</b> instead of ' + money(f.full_usd) : '') + '. Once per account, when you pay in crypto.';
  }
  function promoBox(card) {
    return '<div class="acc-inline acc-promo' + (card ? ' card' : ' flat') + '" data-promo><label class="fld"><span class="fld-l">Promo code</span><input type="text" data-promo-in autocomplete="off" autocapitalize="characters" spellcheck="false" maxlength="40" placeholder="Optional" value="' + esc(promo ? promo.code : '') + '"></label>' +
      '<button class="btn ghost" type="button" data-promo-go>Apply</button><p class="acc-promo-out" role="status">' + promoSaid() + '</p></div>';
  }
  function promoPaint(box, msg) {                                    // every price on the page, and the answer under the box that was used
    Array.prototype.forEach.call(root.querySelectorAll('[data-price]'), function (el) { el.innerHTML = priceHtml(el.getAttribute('data-price')); });
    Array.prototype.forEach.call(root.querySelectorAll('[data-cost]'), function (el) { el.innerHTML = boostName(el.getAttribute('data-cost'), el.getAttribute('data-name')); });
    Array.prototype.forEach.call(root.querySelectorAll('[data-promo]'), function (b) {
      var out = b.querySelector('.acc-promo-out'); if (promo) b.querySelector('[data-promo-in]').value = promo.code;
      out.classList.toggle('bad', !!(msg && b === box)); if (msg && b === box) out.textContent = msg; else out.innerHTML = promoSaid();
    });
    if (paintPost) paintPost();
  }
  function promoApply(box) {
    var input = box.querySelector('[data-promo-in]'), btn = box.querySelector('[data-promo-go]'), code = input.value.trim();
    if (!code) { promo = null; promoPaint(box); return; }
    btn.disabled = true;
    api('POST', '/api/orders/quote', { coupon: code }).then(function (r) { promo = { code: r.coupon.code, percent: r.coupon.percent, quotes: r.quotes }; promoPaint(box); },
      function (e) { promo = null; promoPaint(box, e.message); }).then(function () { btn.disabled = false; });
  }
  function withPromo(data) { if (data.pay !== 'wallet' && cut(data.product)) data.coupon = promo.code; return data; }
  function productCard(id, kind, fields) {
    var p = products[id]; if (!p) return '';
    var pl = (D.plans || {})[p.name], best = id === 'premium' || id === 'pass';
    return '<form class="acc-card' + (best ? ' best' : '') + '" data-product="' + id + '" data-kind="' + kind + '" novalidate>' + (id === 'premium' ? '<span class="pc-flag">Most chosen</span>' : id === 'pass' ? '<span class="pc-flag">Best value</span>' : '') +
      '<p class="pname">' + esc(p.name) + '</p><p class="price" data-price="' + id + '">' + priceHtml(id) + '</p>' +
      (pl ? '<ul class="pc-inc">' + pl[0].map(function (x) { return '<li>' + esc(x) + '</li>'; }).join('') + '</ul>' + (pl[1] ? '<p class="pc-vs"><b>Elsewhere:</b> ' + esc(pl[1]) + '</p>' : '')
        : '<p class="what">' + esc(D.what[p.name] || '') + '</p>') + demo(id) + (fields || '') + err +
      '<div class="pc-act"><button class="btn ' + (best ? 'primary' : 'ghost') + '" type="submit"' + (pub.payments === 'off' ? ' disabled' : '') + '>' + (p.credits ? 'Buy credits' : 'Continue to payment') + '</button>' +
      (me.credits && kind !== 'none' && pub.payments !== 'off' ? '<button class="btn ghost" type="submit" data-credit="1">Pay from my credits (' + money(me.credits) + ' left)</button>' : '') + '</div></form>';
  }
  function creditsNow() { var B = S.billing || {}; return me.credits || (B.wallet && B.wallet.balance) || 0; }
  /* ---------- credits: the balance, how they work, buying more, what was bought and what they were spent on ---------- */
  function creditsPanel() {
    var W = (S.billing || {}).wallet || {}, bal = creditsNow(), lots = W.lots || [];
    var spent = S.orders.filter(function (o) { return o.status === 'paid' && o.credits && !/^credits/.test(o.product || ''); });
    var top = head('Credits', 'Your <b>credits</b>', 'One credit is one US dollar on this site. You buy them once and spend them on any promotion within 12 months.');
    var balance = '<div class="acc-bal"><div class="acc-bal-n"><b>' + money(bal) + '</b><span>in credits now</span></div><div class="acc-bal-t">' +
      (bal ? '<p>' + (W.next_expiry ? 'The first of them run out on ' + nice(W.next_expiry) + '.' : 'They are valid for 12 months from the day you bought them.') + '</p><a class="btn primary" href="#promote">Spend on a promotion</a>'
        : '<p>You have no credits yet. Buy some below and they show here as soon as the payment is confirmed.</p>') + '</div></div>';
    var how = '<ol class="acc-how"><li><b>Buy credits below.</b> When the payment is confirmed they are added to this account and the balance above grows. Nothing else changes.</li>' +
      '<li><b>Open Promote</b> and pick a job or your company. Every card there gets a second button: “Pay from my credits”.</li>' +
      '<li><b>The price comes off the balance</b> and the promotion starts at once, with no checkout page. What is left stays here for the next one.</li></ol>';
    var buy = '<div class="acc-grid four">' + ['credits100', 'credits250', 'credits550', 'credits1200'].map(function (id) { return productCard(id, 'none'); }).join('') + '</div>' +
      (pub.payments === 'off' ? '<p class="note">Credits are not on sale yet.</p>' : '<p class="note">You pay on a crypto checkout page. Credits buy every promotion here; they cannot be turned back into money.</p>');
    return top + balance + testNote() + part('How credits work', how, 'how') + part('Top up', buy, 'buy') +
      (lots.length ? part('Credits you bought', '<div class="acc-list">' + lots.map(function (l) {
        return '<div class="acc-row"><div class="main"><strong>' + l.credits + ' credits</strong><span class="js">Bought ' + nice(l.bought) + ' · ' + (l.expired ? 'ran out ' : 'valid until ') + nice(l.expires) + '</span></div>' +
          '<div class="ctl"><b>' + money(l.remaining) + '</b> left</div></div>'; }).join('') + '</div>', 'lots') : '') +
      (spent.length ? part('What you paid for with credits', '<div class="acc-list">' + spent.map(function (o) {
        return '<div class="acc-row"><div class="main"><strong>' + esc(o.name) + '</strong><span class="js">' + (o.label && o.label !== o.name ? esc(o.label) + ' · ' : '') + nice(o.created) + '</span></div>' +
          '<div class="ctl">' + o.credits + ' credits</div></div>'; }).join('') + '</div>', 'spent') : '');
  }
  /* What a paid product looks like on the site: a piece cut from a real page of the site (the owner, 18 Nov 2026: "not a drawing,
     a cut-out screenshot of the home page and the other pages, how it will be promoted"). The pictures show an example company;
     they were taken from a build in which every product was bought for it in test mode, and live in assets/paid/. A click opens
     the picture in full size. */
  var SHOTS = {
    featured: [['boost-standard', 'A job with a Standard boost in a list: the green “Featured” mark, above the free jobs.']],
    premium: [['boost-premium', 'A Premium job leads its list, with “Featured” and “Urgently hiring” and the company’s logo.'], ['boost-premium-page', 'The page of a Premium job: the logo, the badge and the cover picture.']],
    urgent: [['badge-urgent', 'A job with only the badge: it keeps its place by date and says “Urgently hiring”.']],
    bump: [['bump', 'A job posted two weeks ago and bumped today stands above jobs posted today; its own date stays on it.']],
    spotlight: [['spotlight-home', '“Featured employers” on the home page.'], ['spotlight-company', 'The company page with the “Featured employer” badge.']],
    pass: [['boost-premium', 'Every job of the company is boosted while the pass runs, and three of them can be Premium.'], ['spotlight-home', 'The company is in “Featured employers” for the same 30 days.']],
    sponsor: [['sponsor', 'The top of a category page with the sponsor’s name, logo and open roles.']]
  };
  function demo(id) {
    if (id === 'extend') return '<figure class="pcd"><figcaption>How it works</figcaption><div class="pcd-bar"><span>30 days running</span><span class="more">+30 days</span></div><p>The boost that is running now simply ends 30 days later.</p></figure>';
    var list = SHOTS[id]; if (!list) return '';
    var base = (document.documentElement.getAttribute('data-base') || '') + '/paid/';
    return '<figure class="pcd shot"><figcaption>How it looks on the site (an example company)</figcaption>' + list.map(function (x) {
      return '<a href="' + base + x[0] + '.jpg" target="_blank" rel="noopener" title="Open the picture in full size"><img src="' + base + x[0] + '.jpg" alt="' + esc(x[1]) + '" loading="lazy"></a><p>' + esc(x[1]) + '</p>'; }).join('') + '</figure>';
  }
  function promotePanel() {
    var mine = S.jobs.filter(function (j) { return j.status === 'live' || j.status === 'review'; }), claimed = S.claims.filter(function (c) { return c.status === 'verified'; });
    var data = '<datalist id="acc-companies">' + D.companies.map(function (c) { return '<option value="' + esc(c) + '">'; }).join('') + '</datalist>';
    if (!products.featured) return head('Promote', 'Get <b>more applicants</b>', '') + empty('Nothing is on sale right now.', ' Posting a job stays free.', '<a class="btn primary" href="#post">Post a job free</a>') + data;
    var pick = mine.length || claimed.length ? '<div class="card acc-pick"><label class="fld"><span class="fld-l">Job to promote</span><select id="pr-job">' + mine.map(function (j) {
        return '<option value="id:' + esc(j.id) + '">' + esc(j.title) + (j.status === 'review' ? ' (waiting for review)' : '') + '</option>'; }).join('') + (mine.length ? '' : '<option value="">Loading the jobs of your company…</option>') + '</select>' +
        '<span class="hint">Pick it here once; every choice below is for this job.' + (mine.some(function (j) { return j.status === 'review'; }) ? ' For a job that waits for review, the paid days start when it is approved.' : '') + '</span></label>' +
        (claimed.length ? '<details class="acc-more" id="pr-url"><summary>A job we list from your careers page is not in the list</summary>' + field('Its page on this site', 'job', 'type="url" id="pr-joburl" placeholder="' + esc(D.site) + '/job/…/"') + '</details>' : '') + '</div>' : '';
    var jobCards = mine.length || claimed.length ? pick + '<div class="acc-grid">' + ['featured', 'premium', 'urgent', 'bump', 'extend'].map(function (id) { return productCard(id, 'job'); }).join('') + '</div>' :
      empty('Post a job first.', ' Then pick it here, or press “Promote” next to it in Your jobs: there is no link to copy.', '<a class="btn primary" href="#post">Post a job free</a>');
    var coverForm = mine.length && products.premium ? '<form class="card acc-inline" id="cover-up" novalidate><p class="acc-inline-t"><b>Cover picture for a Premium job.</b> Shown at the top of the job page while its Premium boost runs. PNG, JPG or WebP, wide, up to 450 KB.</p>' +
      '<label class="fld"><span class="fld-l">Job</span><select name="job_id">' + mine.map(function (j) { return '<option value="' + esc(j.id) + '">' + esc(j.title) + '</option>'; }).join('') + '</select></label>' +
      fileBtn('cover_file', 'image/png,image/jpeg,image/webp', 'Choose a picture') + err + '<button class="btn ghost" type="submit">Upload the cover</button></form>' : '';
    var pages = '<label class="fld"><span class="fld-l">Page to sponsor</span><select name="page"><optgroup label="Categories">' +
      D.categories.map(function (c) { return '<option value="category:' + esc(c[0]) + '">' + esc(c[1]) + ' jobs</option>'; }).join('') + '</optgroup><optgroup label="Skills">' +
      D.skills.map(function (s) { return '<option value="skill:' + esc(s[0]) + '">' + esc(s[1]) + ' jobs</option>'; }).join('') + '</optgroup></select></label>';
    return head('Promote', 'Get <b>more applicants</b>', 'Every price is one payment for a fixed time. Nothing renews, and no card is kept on file.') +
      (pub.payments === 'off' ? callout('Paid placements are not on sale yet. Everything else in your account is free.', '', 'soft') : '') + testNote() + promoBox(true) +
      part('For one job', jobCards + coverForm) +
      part('For your company', '<div class="card acc-pick">' + field('Company, as it is named on the site', 'company', 'type="text" id="pr-company" list="acc-companies" value="' + esc(me.company || '') + '" maxlength="80"') + '</div>' +
        '<div class="acc-grid">' + productCard('spotlight', 'company') + productCard('pass', 'company') + productCard('sponsor', 'company', pages) + '</div>') +
      '<p class="acc-synced">' + (creditsNow() ? '<b>' + money(creditsNow()) + ' in credits.</b> Press “Pay from my credits” on any card above to spend them. ' : '<b>Credits:</b> pay once, spend on anything here within 12 months. ') +
        '<a href="#credits">' + (creditsNow() ? 'Top up or see what you spent' : 'See how credits work and buy some') + '</a></p>' +
      (pub.payments === 'off' ? '' : '<p class="note">You pay on a crypto checkout page. What you bought switches on by itself when the network confirms the payment.</p>') + data;
  }
  // a company that posts its own jobs from this account and has none live yet: its page is not on the site so far
  function ownNotLive(c) {
    var k = String(c.company || '').toLowerCase(), mine = S.jobs.filter(function (j) { return String(j.company || '').toLowerCase() === k; });
    return mine.length > 0 && !mine.some(function (j) { return j.status === 'live'; });
  }
  function companyPanel() {
    var top = head('Company page', 'Your <b>company page</b>', 'Your logo, your text and the places where you hire, on the page that lists your open jobs. You also see views and clicks on Apply for every job on it.');
    if (me.posts_as.indexOf('employer') < 0) return top + empty('A company page needs an account at the company’s address.', ' Add your work email first; then you can claim the page here.', '<a class="btn primary" href="#hiring">Add my work email</a>');
    var list = S.claims.map(function (c) {
      var ok = c.status === 'verified', wait = c.status === 'pending';
      return '<article class="acc-job' + (c.status === 'rejected' ? ' bad' : '') + '"><div class="acc-job-h"><div>' + state(c.status, wait ? 'Being checked' : '') + '<h2 class="acc-job-t">' + esc(c.company) + '</h2><p class="js">' + esc(c.domain) + ' · since ' + nice(c.since) + '</p></div></div>' +
        (wait ? '<p class="acc-job-s">A person checks that ' + esc(c.domain) + ' belongs to ' + esc(c.company) + ', usually within a day. You get an email either way.</p>' :
          c.status === 'rejected' ? '<p class="acc-job-s"><b>Not accepted' + (c.reason ? ':</b> ' + esc(c.reason) + '.' : '.</b>') + '</p>' :
          ownNotLive(c) ? '<p class="acc-job-s">This is your company’s page. It goes on the site with your first live job; what you save here is shown on it from that moment.</p>' : '') +
        (ok ? '<form class="claim-page" data-id="' + esc(c.id) + '" novalidate>' +
          '<div class="logo-up"><span class="logo-prev" aria-hidden="true">' + (c.page && c.page.logo ? '<img src="' + esc(c.page.logo) + '" alt="Company logo" title="Company logo">' : esc(c.company.charAt(0))) + '</span><div><p class="fld-l">Company logo</p>' +
          fileBtn('logo_file', 'image/png,image/jpeg,image/webp', c.page && c.page.logo ? 'Change the logo' : 'Upload a logo') + '<p class="hint">PNG, JPG or WebP, square, up to 150 KB.</p></div></div>' +
          '<label class="fld"><span class="fld-l">About the company (shown on its page)</span><textarea name="about" rows="4" maxlength="1000">' + esc((c.page && c.page.about) || '') + '</textarea></label>' +
          '<div class="acc-two"><label class="fld"><span class="fld-l">Places where you hire, one per line (up to 10)</span><textarea name="locations" rows="3" placeholder="Berlin&#10;London&#10;Remote, Europe">' + esc(((c.page && c.page.locations) || []).join('\n')) + '</textarea></label>' +
          field('Company site', 'website', 'type="url" value="' + esc((c.page && c.page.website) || '') + '" placeholder="https://' + esc(c.domain) + '"') + '</div>' + err +
          '<p class="acc-btns"><button class="btn primary" type="submit">Save the page</button><button class="btn ghost" type="button" data-stats="' + esc(c.id) + '">Views and clicks</button></p><div class="stats-out"></div></form>' : '') + '</article>';
    }).join('');
    return top + list + '<form class="card acc-form" id="claim" novalidate><h2 class="acc-h2">' + (S.claims.length ? 'Claim another page' : 'Claim your page') + '</h2>' +
      '<p class="acc-sub">' + (S.claims.length ? 'Is your company also on the site under another name, read from its own hiring system? Claim that page too.' :
        'New here? <a href="#post">Post your first job</a>: your company page is made with it and appears on this tab at once, ready for your logo and text. ' +
        'Is your company already on the site (we read the jobs of thousands of companies from their own hiring systems)? Claim its page:') + '</p>' +
      '<div class="acc-inline flat">' + field('Company, as the site names it', 'company', 'type="text" list="acc-companies2" maxlength="80" required data-need="Enter the company name as the site shows it."') + '<button class="btn' + (S.claims.length ? ' ghost' : ' primary') + '" type="submit">Claim the page</button></div>' + err +
      '<p class="note">If the site already knows that ' + esc(me.domain) + ' is the company’s own address, the page is yours at once. If not, a person checks it, usually within a day.</p>' +
      '<datalist id="acc-companies2">' + D.companies.map(function (c) { return '<option value="' + esc(c) + '">'; }).join('') + '</datalist></form>';
  }
  function teamPanel() {
    if (me.posts_as.indexOf('employer') < 0) return '';
    var team = S.team || { members: [] };
    return head('Team', 'Your <b>team</b>', 'Colleagues on ' + esc(me.domain) + ' you add here post under your company’s name from their own accounts.') +
      (team.members.length ? '<div class="acc-list">' + team.members.map(function (m) { return '<div class="acc-row"><div class="main"><strong>' + esc(m.email) + '</strong><span class="js">' +
        (m.has_account ? (m.confirmed ? m.live_jobs + plural(m.live_jobs, ' live job', ' live jobs') : 'has an account, email not confirmed yet') : 'no account yet: they sign up with this address') + '</span></div>' +
        '<div class="ctl"><button class="btn ghost sm" type="button" data-team-del="' + esc(m.email) + '">Remove</button></div></div>'; }).join('') + '</div>'
        : '<p class="acc-quiet">Nobody added yet. You are the only one who posts for ' + esc(me.company || me.domain) + '.</p>') +
      '<form class="card acc-inline" id="team-add" novalidate>' + field('Colleague’s work email', 'email', 'type="email" required placeholder="name@' + esc(me.domain) + '"') + err + '<button class="btn primary" type="submit">Add to the team</button></form>';
  }
  function findPanel() {
    if (!(pub.talent === 'on' && S.sent && me.posts_as.indexOf('employer') >= 0)) return '';
    return head('Find candidates', 'Find people in the <b>resume database</b>', 'People who chose to be found. You see no name or contacts until the person accepts your request, and you pay only for people who accept.') +
      '<form class="card acc-form" id="talent-search" novalidate><div class="acc-two">' + field('Words', 'q', 'type="text" placeholder="rust engineer"') + field('Skill', 'skill', 'type="text" placeholder="python"') +
      '<label class="fld"><span class="fld-l">Kind of work</span><select name="role"><option value="">Any</option>' + D.categories.map(function (c) { return '<option value="' + esc(c[0]) + '">' + esc(c[1]) + '</option>'; }).join('') + '</select></label>' +
      field('Place', 'place', 'type="text" placeholder="remote, germany"') + '</div>' + err + '<p class="acc-btns"><button class="btn primary" type="submit">Search</button><span class="note">' + S.sent.credits + plural(S.sent.credits, ' contact request', ' contact requests') + ' left.</span></p></form><div id="talent-out"></div>' +
      (S.sent.requests.length ? part('Your requests', '<div class="acc-list">' + S.sent.requests.map(function (q) {
        var c = q.candidate; return '<div class="acc-row"><div class="main">' + state(q.status) + ' <strong>' + esc(c.headline || 'Candidate') + '</strong>' + (q.status === 'accepted' && c.contact ? '<span class="js"><strong>' + esc(c.contact.name) + '</strong>, <a href="mailto:' + esc(c.contact.email) + '">' + esc(c.contact.email) + '</a>' + (c.contact.phone ? ', ' + esc(c.contact.phone) : '') + '</span>' : '') + '<span class="js">sent ' + nice(q.sent) + '</span></div></div>';
      }).join('') + '</div>') : '');
  }
  function billingPanel() {
    var B = S.billing || {}, boosts = {}, credits = me.credits || (B.wallet && B.wallet.balance) || 0, passes = (B.passes || []).filter(function (p) { return p.live; });
    (B.boosts || []).forEach(function (b) { boosts[b.id] = b; });
    var top = head('Billing', 'Payments and <b>receipts</b>', 'Every payment is a single payment for a fixed time. Nothing renews.', S.orders.length || S.placements.length ? '<a class="btn ghost" href="#promote">See promotions</a>' : '');
    var have = (credits ? '<p class="acc-synced"><b>' + money(credits) + ' in credits.</b> ' + (B.wallet && B.wallet.next_expiry ? 'The first of them run out on ' + nice(B.wallet.next_expiry) + '. ' : '') + 'Use them on any promotion: “Pay from my credits”.</p>' : '') +
      passes.map(function (p) { return '<p class="acc-synced"><b>Hiring Pass for ' + esc(p.company) + '</b> until ' + nice(p.until) + ': ' + p.premium_left + plural(p.premium_left, ' Premium boost', ' Premium boosts') + ' left.</p>'; }).join('');
    if (!S.orders.length && !S.placements.length) return top + have + empty('No payments yet.', ' Posting jobs is free. When you promote a job, the payment and its receipt show here.', '<a class="btn primary" href="#promote">See promotions</a>') + testNote();
    return top + have + testNote() +
      // rows, not tables: on a phone a table of seven columns is a strip to drag sideways
      (S.placements.length ? part('What is running', '<div class="acc-list">' + S.placements.map(function (p) {
        var b = boosts[p.id];
        return '<div class="acc-row"><div class="main">' + state(p.state) + ' <strong>' + esc(KIND[p.kind] || p.kind) + '</strong><span class="js">' + esc(p.label) + '</span><span class="js">' +
          (p.from && p.until ? nice(p.from) + ' to ' + nice(p.until) : p.days ? p.days + ' days, from the day the job is approved' : '') +
          (b ? ' · ' + b.views + plural(b.views, ' view', ' views') + ' · ' + b.applies + plural(b.applies, ' click on Apply', ' clicks on Apply') : '') + '</span></div></div>';
      }).join('') + '</div>', 'running') : '') +
      (S.orders.length ? part('Payments', '<div class="acc-list">' + S.orders.map(function (o) {
        return '<div class="acc-row"><div class="main">' + state(o.status) + ' <strong>' + esc(o.name) + '</strong><span class="js">' + (o.label && o.label !== o.name ? esc(o.label) + ' · ' : '') +
          (o.amount_usd ? money(o.amount_usd) + (o.coupon ? ' with ' + esc(o.coupon.code) + ' (full price ' + money(o.coupon.full_usd) + ')' : '') : o.credits ? o.credits + ' credits' : 'Included') + ' · ' + nice(o.created) + '</span></div><div class="ctl">' +
          (o.pay_url ? '<a class="btn sm" href="' + esc(o.pay_url) + '">Pay now</a><button class="btn ghost sm" type="button" data-pay-copy="' + esc(o.pay_url) + '">Copy the link for whoever pays</button>' : '') +
          (o.status === 'paid' ? '<button class="btn ghost sm" type="button" data-receipt="' + esc(o.id) + '">Receipt</button>' : '') + '</div></div>';
      }).join('') + '</div><div id="receipt-out"></div>', 'payments') : '');
  }

  /* ---------- settings: the address, the password, which side you use, your data, deleting the account ---------- */
  function settingsPanel() {
    var emp = ROLE === 'employer';
    return head('Settings', 'Your <b>account</b>', '') +
      '<dl class="acc-dl"><div><dt>Email</dt><dd><span>' + esc(me.email) + ' ' + (me.confirmed ? state('live', 'Confirmed') : state('review', 'Not confirmed')) + '</span>' +
        (me.confirmed ? '' : '<button class="btn ghost sm acc-confirm" type="button">Send the link again</button>') + '</dd></div>' +
      '<div><dt>Password</dt><dd><span>To change it, we send a link to your email. Opening it lets you choose a new password and signs out every browser.</span><button class="btn ghost sm" type="button" id="acc-pass">Send me the link</button></dd></div>' +
      '<div><dt>You use it as</dt><dd><span>' + (emp ? 'An employer: jobs, promotion, company page.' : 'A job seeker: resumes, saved jobs, alerts.') + '</span><button class="btn ghost sm" type="button" data-role-to="' + (emp ? 'seeker' : 'employer') + '">' + (emp ? 'Open the job seeker side' : 'Open the employer side') + '</button></dd></div>' +
      (me.domain ? '<div><dt>Company domain</dt><dd><span>' + esc(me.domain) + (me.company ? ' · ' + esc(me.company) : '') + '</span></dd></div>' : '') +
      (me.linkedin || pub.linkedin === 'on' ? '<div><dt>LinkedIn</dt><dd>' + (me.linkedin ? '<span>Connected' + (me.linkedin.name ? ' as ' + esc(me.linkedin.name) : '') + '</span>' : '<span>Not connected</span><button class="btn ghost sm li-start" type="button">Connect LinkedIn</button>') + '</dd></div>' : '') + '</dl>' +
      part('Your data', '<p class="acc-sub">Download everything we keep about your account as one file. <a href="' + esc(D.site) + '/privacy/">What we keep and why</a></p>' +
        '<p class="acc-btns"><button class="btn ghost" type="button" id="me-export">Download my data</button></p>', 'data') +
      part('Delete the account', '<form class="acc-danger" id="me-delete" novalidate><p>This removes your alerts, your resumes, your synced lists and everything you posted, at once and for good. It cannot be undone.</p>' +
        field('To go on, type: delete my account', 'confirm', 'type="text" autocomplete="off" required data-need="Type the words “delete my account” to go on."') + err +
        '<p class="acc-btns"><button class="btn ghost" type="submit">Delete my account for good</button></p></form>', 'delete');
  }

  var TABS = { seeker: [['overview', 'Overview'], ['saved', 'Saved jobs'], ['resumes', 'Resumes'], ['alerts', 'Job alerts'], ['settings', 'Settings']],
    employer: [['overview', 'Overview'], ['jobs', 'Your jobs'], ['post', 'Post a job'], ['promote', 'Promote'], ['credits', 'Credits'], ['company', 'Company page'], ['team', 'Team'], ['find', 'Find candidates'], ['billing', 'Billing'], ['settings', 'Settings']] };
  var TAB_ROLE = { saved: 'seeker', resumes: 'seeker', alerts: 'seeker', jobs: 'employer', post: 'employer', promote: 'employer', credits: 'employer', company: 'employer', team: 'employer', find: 'employer', billing: 'employer' };
  // older links and the links in our letters (#talent) name a block inside a part: open the part, then go to the block
  var ALIAS = { talent: 'resumes', sync: 'saved', myresumes: 'resumes', hiring: 'post', payments: 'billing', running: 'billing', data: 'settings', account: 'settings' };
  function toTop() { var r = root.getBoundingClientRect(); if (r.top < 0) window.scrollTo(0, Math.max(0, window.scrollY + r.top - 76)); }
  // a link to a part of the other side (#post while the job seeker side is open) opens that side
  function otherSide() { var raw = location.hash.slice(1), r = TAB_ROLE[ALIAS[raw] || raw]; return r && r !== ROLE ? r : ''; }
  function showTab() {
    var raw = location.hash.slice(1), want = ALIAS[raw] || raw;
    if (otherSide()) { setRole(otherSide()); return draw(); }
    var panels = root.querySelectorAll('.acc-panel'), ok = false;
    Array.prototype.forEach.call(panels, function (p) { if (p.getAttribute('data-tab') === want) ok = true; });
    if (!ok) want = ROLE === 'employer' && !S.jobs.length && !raw ? 'post' : 'overview';
    Array.prototype.forEach.call(panels, function (p) { p.hidden = p.getAttribute('data-tab') !== want; });
    Array.prototype.forEach.call(root.querySelectorAll('.acc-nav a'), function (a) {
      var on_ = a.getAttribute('href') === '#' + want;
      a.classList.toggle('on', on_); if (on_) { a.setAttribute('aria-current', 'page'); if (a.parentNode.scrollWidth > a.parentNode.clientWidth) a.parentNode.scrollLeft = Math.max(0, a.offsetLeft - a.parentNode.offsetLeft - 16); } else a.removeAttribute('aria-current');
    });
    var block = ALIAS[raw] ? document.getElementById('acc-' + raw) : null;
    if (block) window.scrollTo(0, Math.max(0, window.scrollY + block.getBoundingClientRect().top - 84));
  }
  function draw() {
    if (hd) hd.hidden = true;
    if (otherSide()) setRole(otherSide());
    var emp = ROLE === 'employer', P = { overview: overview(), settings: settingsPanel() };
    if (emp) { P.jobs = jobsPanel(); P.post = postPanel(); P.promote = promotePanel(); P.credits = creditsPanel(); P.company = companyPanel(); P.team = teamPanel(); P.find = findPanel(); P.billing = billingPanel(); }
    else { P.saved = savedPanel(); P.resumes = resumesPanel(); P.alerts = alertsPanel(); }
    var nav = '', panels = '';
    TABS[ROLE].forEach(function (t) {
      if (!P[t[0]]) return;
      var n = t[0] === 'jobs' ? S.jobs.length : t[0] === 'alerts' ? S.alerts.length : t[0] === 'resumes' && S.resumes ? S.resumes.resumes.length : 0;
      if (t[0] === 'credits' && creditsNow()) n = money(creditsNow());                    // the balance stands next to the word, so it is never a question where bought credits went
      nav += '<a href="#' + t[0] + '">' + t[1] + (n ? '<i>' + n + '</i>' : '') + '</a>';
      panels += '<section class="acc-panel" data-tab="' + t[0] + '" hidden>' + P[t[0]] + '</section>';
    });
    root.innerHTML = '<div class="acc-shell"><aside class="acc-side"><div class="acc-me"><span class="acc-av" aria-hidden="true">' + esc(me.email.charAt(0).toUpperCase()) + '</span><div><b>' + esc(me.email) + '</b><span>' +
      (emp ? esc(me.company || me.domain || 'Employer') : 'Job seeker') + '</span></div></div><div class="acc-nav" role="navigation" aria-label="Your account">' + nav + '</div>' +
      '<div class="acc-foot"><button type="button" class="acc-sw" data-role-to="' + (emp ? 'seeker' : 'employer') + '">' + (emp ? '<b>I’m looking for a job</b> Open the job seeker side' : '<b>I’m hiring</b> Open the employer side') + '</button>' +
      (me.admin ? '<a class="acc-adm" href="' + esc(D.site) + '/admin/">Moderation</a>' : '') +
      '<button class="btn ghost sm acc-out" type="button" id="acc-out">Sign out</button></div></aside><div class="acc-main"><div id="acc-say" aria-live="polite">' +
      (notice ? '<div class="banner' + (noticeBad ? '' : ' ok') + '" role="status">' + notice + '</div>' : '') + '</div><div id="acc-pay"></div>' +
      (!me.confirmed ? callout('<b>Confirm your email.</b> We sent a link to ' + esc(me.email) + '. Open it to ' + (emp ? 'publish jobs' : 'keep your resumes, saved jobs and alerts here') + '.', '<button class="btn sm acc-confirm" type="button">Send the link again</button>') : '') +
      panels + '</div></div>';
    if (notice) saidAt = Date.now();
    notice = ''; noticeBad = false;
    showTab();
    wire();
    watchOrder();
  }

  function wire() {
    document.getElementById('acc-out').addEventListener('click', signOut);
    on('[data-role-to]', function (b) { setRole(b.getAttribute('data-role-to')); cleanUrl(); draw(); toTop(); });
    Array.prototype.forEach.call(root.querySelectorAll('.acc-file input'), function (inp) {
      inp.addEventListener('change', function () { var n = inp.closest('.acc-file').querySelector('.acc-file-n'); if (n) n.textContent = inp.files && inp.files[0] ? inp.files[0].name : 'No file chosen'; });
    });
    on('.acc-confirm', function (b) { b.disabled = true; api('POST', '/api/auth/confirm/request').then(function (r) { b.textContent = 'Sent'; say(esc(r.confirmed ? 'Your email is confirmed already.' : (r.message || 'A new link is on its way.'))); if (r.confirmed) load(); }, function (e) { b.disabled = false; fail(e); }); });

    /* job seeker */
    submit(document.getElementById('res-save'), function (v) {
      return api('POST', '/api/resumes', { name: v.name || 'My resume', resume: H.get('hrn_resume', null) }).then(function () { flash('Your resume is saved in your account.'); return load(); });
    });
    on('[data-res-open]', function (b) {
      var cur = H.get('hrn_resume', null);
      (cur ? H.sure(b, 'Open this version in the builder? It replaces the resume that is in the builder now.', 'Open it') : Promise.resolve(true)).then(function (ok) {
        if (!ok) return;
        b.disabled = true;
        api('GET', '/api/resumes/' + b.getAttribute('data-res-open')).then(function (r) { H.set('hrn_resume', r.resume.resume); location.href = D.site + '/resume/'; }, function (e) { b.disabled = false; fail(e); });
      });
    });
    on('[data-res-del]', function (b) {
      H.sure(b, 'Delete this version from your account?', 'Delete').then(function (ok) {
        if (ok) api('DELETE', '/api/resumes/' + b.getAttribute('data-res-del')).then(function () { flash('The version is deleted.'); return load(); }, fail);
      });
    });
    on('[data-alert-del]', function (b) { b.disabled = true; api('DELETE', '/api/alerts/' + b.getAttribute('data-alert-del')).then(function () { flash('The alert is deleted. No more letters for it.'); return load(); }, function (e) { b.disabled = false; fail(e); }); });
    on('[data-alert-pause]', function (b) {
      var pause = b.getAttribute('data-on') === '1'; b.disabled = true;
      api('PATCH', '/api/alerts/' + b.getAttribute('data-alert-pause'), { paused: pause }).then(function (r) { S.alerts = r.alerts; flash(pause ? 'The alert is paused: no letters until you switch it on.' : 'The alert is on again.'); draw(); }, function (e) { b.disabled = false; fail(e); });
    });
    Array.prototype.forEach.call(root.querySelectorAll('[data-alert-freq]'), function (sl) {
      sl.addEventListener('change', function () { api('PATCH', '/api/alerts/' + sl.getAttribute('data-alert-freq'), { freq: sl.value }).then(function (r) { S.alerts = r.alerts; say('Saved: this alert now comes ' + esc(sl.options[sl.selectedIndex].text.toLowerCase()) + '.'); }, fail); });
    });
    var an = document.getElementById('alert-new');
    if (an) {
      // the places of the site, for the list (a small file every list page reads anyway)
      fetch(H.base + '/data/head.json').then(function (r) { return r.json(); }).then(function (d) {
        var sl = an.elements.loc, small = { and: 1, of: 1, the: 1 }; if (!sl || !d || !d.p) return;
        sl.insertAdjacentHTML('beforeend', d.p.map(function (p) { return '<option value="' + esc(p) + '">' + esc(p.split('-').map(function (w, i) { return small[w] && i ? w : w.length <= 2 ? w.toUpperCase() : w.charAt(0).toUpperCase() + w.slice(1); }).join(' ')) + '</option>'; }).join(''));
      }).catch(function () {});
      submit(an, function (v) {
        if (!v.q && !v.cat && !v.loc) throw oops('q', 'Add a word, or pick a kind of work or a place: an alert has to be about something.');
        return api('POST', '/api/me/alerts', v).then(function (r) { S.alerts = r.alerts; flash('The alert is on. Its first letter comes with the next matching jobs.'); draw(); });
      });
    }
    on('#sync-up', function (b) {
      var data = {}; SYNC_KEYS.forEach(function (k) { var v = H.get(k, null); if (v != null) data[k] = v; });
      b.disabled = true; api('PUT', '/api/sync', { data: data }).then(function () { flash('Your lists are copied to your account.'); return load(); }, function (e) { b.disabled = false; fail(e); });
    });
    on('#sync-down', function (b) {
      H.sure(b, 'Replace the lists in this browser with the copy in your account?', 'Replace').then(function (ok) {
        if (!ok) return;
        var data = (S.sync && S.sync.data) || {}; SYNC_KEYS.forEach(function (k) { if (k in data) H.set(k, data[k]); });
        flash('Your lists are in this browser now.'); draw();
      });
    });
    submit(document.getElementById('talent-on'), function (v) {
      return api('PUT', '/api/talent/profile', Object.assign(talentValues(v), { consent: true, consent_text: S.talent.consent_text, resume: H.get('hrn_resume', null) })).then(function () { flash('Employers can now find your resume, without your name and contacts.'); return load(); });
    });
    submit(document.getElementById('talent-set'), function (v) { return api('PUT', '/api/talent/profile', talentValues(v)).then(function () { flash('Saved.'); return load(); }); });
    on('#talent-update', function () { api('PUT', '/api/talent/profile', { resume: H.get('hrn_resume', null) }).then(function () { flash('The copy employers see is updated.'); return load(); }, fail); });
    on('#talent-pause', function () { api('PUT', '/api/talent/profile', { paused: !S.talent.profile.paused }).then(load, fail); });
    on('#talent-del', function (b) {
      H.sure(b, 'Delete your resume from our server for good? Employers will no longer find it.', 'Delete').then(function (ok) {
        if (ok) api('DELETE', '/api/talent/profile').then(function (r) { flash(esc(r.message)); return load(); }, fail);
      });
    });
    on('[data-q]', function (b) { b.disabled = true; api('POST', '/api/talent/requests/' + b.getAttribute('data-id') + '/' + b.getAttribute('data-q')).then(load, function (e) { b.disabled = false; fail(e); }); });

    /* employer: posting. What is typed is kept in this browser, so confirming the email (a new tab) or a reload loses nothing. */
    var jf = document.getElementById('acc-job');
    paintPost = null;
    if (jf) {
      var draft = H.get('hrn_job_draft', null), pubBtn = document.getElementById('acc-publish');
      if (draft) Object.keys(draft).forEach(function (k) {
        var el = jf.elements[k]; if (!el || draft[k] === '' || draft[k] == null) return;
        if (el.type === 'checkbox') el.checked = !!draft[k]; else if (el.tagName) el.value = draft[k]; else Array.prototype.forEach.call(el, function (r) { r.checked = r.value === draft[k]; });
      });
      var paint = function () {
        var b = (values(jf).boost || ''), p = products[b], q = cut(b);
        if (me.confirmed) pubBtn.textContent = p ? 'Publish and pay ' + money(q ? q.amount_usd : p.usd) : 'Publish the job';
      };
      paintPost = paint;
      var keep = function () { H.set('hrn_job_draft', values(jf)); paint(); };
      jf.addEventListener('input', keep); jf.addEventListener('change', keep); paint();
      var pasteGo = document.getElementById('job-paste-go'), pasteOut = document.getElementById('job-paste-out');
      if (pasteGo) pasteGo.addEventListener('click', function () {
        var got = H.readPosting(document.getElementById('job-paste').value), names = { title: 'title', company: 'company', location: 'place', salary: 'pay', etype: 'employment type', apply_url: 'link', description: 'text', remote: 'remote' }, done = [];
        Object.keys(got).forEach(function (k) {
          var el = jf.elements[k]; if (!el || got[k] === '' || got[k] == null) return;
          if (k === 'company' && el.value.trim()) return;                    // the account's own company name stays
          if (el.type === 'checkbox') el.checked = !!got[k]; else el.value = got[k];
          done.push(names[k] || k);
        });
        Array.prototype.forEach.call(jf.querySelectorAll('textarea, input'), function (el) { el.dispatchEvent(new Event('input', { bubbles: true })); });
        pasteOut.textContent = done.length ? 'Filled in: ' + done.join(', ') + '. Check each field, then add what is missing.' : 'Nothing could be read from this text. Paste the whole posting, with the title on the first line.';
        if (done.length) jf.scrollIntoView({ block: 'start', behavior: 'smooth' });
      });
      submit(jf, function (v) {
        var boost = v.boost; delete v.boost;
        if (!me.confirmed) return api('POST', '/api/jobs/preview', v).then(function (r) {
          say('<b>The job passes our checks.</b> ' + (r.review ? 'A person will read it before it appears, usually within a day. ' : '') + 'It is kept in this browser: confirm your email, then press “Publish the job”.');
        });
        return api('POST', '/api/jobs', v).then(function (r) {
          var j = r.job, first = !S.jobs.length && me.domain; H.set('hrn_job_draft', null);
          // the first job makes the company's page: say so, with the way to it (the owner looked for "create a company" and found nothing)
          flash((j.status === 'live' ? '<b>Your job is live:</b> ' + esc(j.title) + '. It is on the site after the next update, within the hour.' :
            '<b>Your job “' + esc(j.title) + '” is saved.</b> A person reads it before it appears, usually within a day; you get an email either way.') +
            (first ? ' Your company page is ready too: <a href="#company">add your logo and a few lines about ' + esc(j.company || 'the company') + '</a>.' : ''));
          var done = function () { location.hash = '#jobs'; return load(); };
          if (!boost) return done();
          return api('POST', '/api/orders', withPromo({ product: boost, target: { job_id: j.id } })).then(function (o) {
            if (o.order.status === 'pending' && o.order.pay_url) { location.href = o.order.pay_url; return new Promise(function () {}); }
            return done();
          }, function (e2) { notice += ' The promotion was not ordered: ' + esc(e2.message); return done(); });
        }, function (e) {
          if ((e.code === 'already_listed' || e.code === 'listed') && e.body && e.body.claim) e.message += ' You can claim the page of ' + e.body.claim.company + ' under “Company page”.';
          throw e;
        });
      });
    }
    Array.prototype.forEach.call(root.querySelectorAll('textarea[minlength]'), function (ta) {            // how much is written, against the least and the most
      var out = ta.parentNode.querySelector('[data-count]'), min = Number(ta.getAttribute('minlength')), max = Number(ta.getAttribute('maxlength'));
      var count = function () { var n = ta.value.trim().length; if (out) out.textContent = n ? (n < min ? n + ' characters: ' + (min - n) + ' more to reach ' + min + '.' : n.toLocaleString('en-US') + ' of ' + max.toLocaleString('en-US') + ' characters.') : min + ' to ' + max.toLocaleString('en-US') + ' characters.'; };
      ta.addEventListener('input', count); count();
    });
    on('[data-job-edit]', function (b) {
      var f = root.querySelector('form.job-edit[data-id="' + b.getAttribute('data-job-edit') + '"]'); if (!f) return;
      f.hidden = !f.hidden; b.setAttribute('aria-expanded', String(!f.hidden));
      if (!f.hidden) { try { f.elements.title.focus(); } catch (e) {} }
    });
    on('[data-job-cancel]', function (b) { var f = b.closest('form'); f.hidden = true; unmark(f); var e = root.querySelector('[data-job-edit="' + b.getAttribute('data-job-cancel') + '"]'); if (e) { e.setAttribute('aria-expanded', 'false'); e.focus(); } });
    Array.prototype.forEach.call(root.querySelectorAll('form.job-edit'), function (f) {
      submit(f, function (v) {
        return api('PATCH', '/api/jobs/' + f.getAttribute('data-id'), v).then(function (r) {
          var j = r.job;
          flash(j.status === 'review' ? '<b>Saved.</b> “' + esc(j.title) + '” is waiting for a quick check by a person before it shows.' : '<b>Saved:</b> “' + esc(j.title) + '”. The site shows the change after its next update.');
          return load();
        });
      });
    });
    // a new job that starts as a copy of this one; the title and the link are the person's to change, so the link is left empty
    on('[data-job-copy]', function (b) {
      var j = S.jobs.filter(function (x) { return x.id === b.getAttribute('data-job-copy'); })[0]; if (!j) return;
      H.set('hrn_job_draft', { company: j.company, company_url: j.company_url, title: j.title, apply_url: '', location: j.location || '', salary: j.salary || '', etype: j.etype || '', remote: !!j.remote, description: j.description || '' });
      flash('The form is filled from “' + esc(j.title) + '”. Change the title, add the link of the new job, and publish.');
      location.hash = '#post'; draw();
    });
    on('#jobs-csv', function () {
      var cell = function (v) { v = String(v == null ? '' : v); if (/^[=+\-@\t\r]/.test(v)) v = "'" + v; return /[",\n]/.test(v) ? '"' + v.replace(/"/g, '""') + '"' : v; };      // a leading = would be a formula in a spreadsheet
      var rows = [['Job', 'Company', 'Location', 'Status', 'Posted', 'On the site until', 'Views', 'Clicks on Apply']].concat(S.jobs.map(function (j) { return [j.title, j.company, j.location, j.status, j.posted, j.until, j.views || 0, j.applies || 0]; }));
      var a = document.createElement('a'); a.href = URL.createObjectURL(new Blob(['﻿' + rows.map(function (r) { return r.map(cell).join(','); }).join('\r\n')], { type: 'text/csv;charset=utf-8' }));
      a.download = 'jobs-every-hour-jobs.csv'; document.body.appendChild(a); a.click(); a.remove(); setTimeout(function () { URL.revokeObjectURL(a.href); }, 5000);
    });
    on('[data-pay-copy]', function (b) {
      var done = function () { b.textContent = 'Link copied'; setTimeout(function () { b.textContent = 'Copy the link for whoever pays'; }, 1800); };
      if (navigator.clipboard) navigator.clipboard.writeText(b.getAttribute('data-pay-copy')).then(done, function () {}); else done();
    });
    on('[data-job-del]', function (b) {
      // asked on the page, not in a browser window: where such windows are switched off the button used to do nothing
      H.sure(b, 'Delete this job for good? It leaves the site at its next update, and what was bought for it stops.', 'Delete the job').then(function (ok) {
        if (!ok) return;
        b.disabled = true; api('DELETE', '/api/jobs/' + b.getAttribute('data-job-del')).then(function () { flash('The job is deleted. It leaves the site at the next update, within the hour.'); return load(); }, function (e) { b.disabled = false; fail(e); });
      });
    });
    on('[data-act]', function (b) {
      var act = b.getAttribute('data-act'); b.disabled = true;
      api('POST', '/api/jobs/' + b.getAttribute('data-id') + '/' + act).then(function (r) {
        var j = r.job || {};
        flash(act === 'close' ? '“' + esc(j.title) + '” is closed. It leaves the site at its next update; you can publish it again.' :
          j.status === 'review' ? '“' + esc(j.title) + '” is waiting for a quick check by a person before it shows again.' : '“' + esc(j.title) + '” is on the site until ' + nice(j.until) + '.');
        return load();
      }, function (e) { b.disabled = false; fail(e); });
    });
    on('[data-promo-go]', function (b) { promoApply(b.closest('[data-promo]')); });
    Array.prototype.forEach.call(root.querySelectorAll('[data-promo-in]'), function (inp) {
      inp.addEventListener('keydown', function (ev) { if (ev.key === 'Enter') { ev.preventDefault(); promoApply(inp.closest('[data-promo]')); } });
    });
    on('[data-promote]', function (b) { S.pick = 'id:' + b.getAttribute('data-promote'); var sl = document.getElementById('pr-job'); if (sl) sl.value = S.pick; location.hash = '#promote'; });
    var prJob = document.getElementById('pr-job');
    if (prJob) {
      if (S.pick) prJob.value = S.pick;
      prJob.addEventListener('change', function () { S.pick = prJob.value; });
      // the jobs we read from the careers page of a company whose page is claimed: picked from the same list, nothing to paste
      S.claims.filter(function (c) { return c.status === 'verified'; }).forEach(function (c) {
        var slug = c.company.toLowerCase().replace(/[^a-z0-9]+/g, '-').replace(/^-+|-+$/g, '');
        fetch(H.base + '/data/companies/' + slug + '.json').then(function (r) { return r.ok ? r.json() : { jobs: [] }; }).then(function (d) {
          var first = prJob.options[0]; if (first && !first.value) first.remove();
          if (d.jobs && d.jobs.length) prJob.insertAdjacentHTML('beforeend', '<optgroup label="From the careers page of ' + esc(c.company) + '">' + d.jobs.slice(0, 300).map(function (j) {
            return '<option value="url:' + esc(j.url) + '">' + esc(j.title) + (j.location ? ' · ' + esc(j.location) : '') + '</option>'; }).join('') + '</optgroup>');
          else if (!prJob.options.length) { prJob.insertAdjacentHTML('beforeend', '<option value="">No job of ' + esc(c.company) + ' is on the site right now</option>'); var dt = document.getElementById('pr-url'); if (dt) dt.open = true; }
          if (S.pick) prJob.value = S.pick;
        }).catch(function () { var first = prJob.options[0]; if (first && !first.value) first.textContent = 'Paste the address of the job page below'; var dt = document.getElementById('pr-url'); if (dt) dt.open = true; });
      });
    }
    submit(document.getElementById('cover-up'), function (v) {
      var form = document.getElementById('cover-up'), file = form.querySelector('input[type=file]').files[0];
      if (!file) throw new Error('Choose a picture first.');
      if (file.size > 450000) throw new Error('The picture is larger than 450 KB. Save it smaller (for example 1200 × 400 pixels) and try again.');
      return new Promise(function (ok, bad) { var rd = new FileReader(); rd.onload = function () { ok(rd.result); }; rd.onerror = function () { bad(new Error('The file could not be read.')); }; rd.readAsDataURL(file); })
        .then(function (img) { return api('PUT', '/api/listings/cover', { target: { job_id: v.job_id }, image: img }); })
        .then(function () { flash('The cover is saved. It shows on the job page while its Premium boost runs.'); return load(); });
    });
    Array.prototype.forEach.call(root.querySelectorAll('form[data-product]'), function (form) {
      submit(form, function (v, btn) {
        var kind = form.getAttribute('data-kind'), t = {};
        if (kind === 'job') {
          var url = document.getElementById('pr-joburl'), sel = document.getElementById('pr-job'), val = sel ? sel.value : '';
          if (url && url.value.trim()) t.job = url.value.trim(); else if (val.indexOf('id:') === 0) t.job_id = val.slice(3); else if (val.indexOf('url:') === 0) t.job = val.slice(4);
          if (!t.job && !t.job_id) throw new Error('Pick the job to promote in the list above the prices.');
        } else if (kind === 'company') {
          var co = document.getElementById('pr-company');
          t.company = co ? co.value.trim() : '';
          if (!t.company) { if (co) { mark(co, 'Enter the company name as the site shows it.'); co.focus(); } throw new Error('Enter the company name above the prices first.'); }
          if (v.page) t.page = v.page;
        }
        var data = { product: form.getAttribute('data-product'), target: t };
        if (btn && btn.getAttribute('data-credit')) data.pay = 'wallet';
        return api('POST', '/api/orders', withPromo(data)).then(function (r) {
          if (r.order.status === 'pending' && r.order.pay_url) { location.href = r.order.pay_url; return new Promise(function () {}); }   // on to the checkout
          flash('<b>' + esc(r.order.name) + '</b> is on' + (r.order.label && r.order.label !== r.order.name ? ' for ' + esc(r.order.label) : '') + '.'); location.hash = '#billing';
          return load();
        });
      });
    });

    /* employer: the company page, the team, the resume database */
    submit(document.getElementById('claim'), function (v) {
      return api('POST', '/api/claims', v).then(function (r) {
        flash(r.claim && r.claim.status === 'verified' ? '<b>The page of ' + esc(r.claim.company) + ' is yours.</b> Add your logo and text below.' : '<b>Your claim is in.</b> A person checks it, usually within a day; you get an email either way.');
        return load();
      });
    });
    Array.prototype.forEach.call(root.querySelectorAll('form.claim-page'), function (f) {
      var fileIn = f.querySelector('input[name=logo_file]');
      if (fileIn) fileIn.addEventListener('change', function () {
        var file = fileIn.files && fileIn.files[0], box = f.querySelector('.acc-err'); f._logo = ''; if (box) box.hidden = true;
        if (!file) return;
        if (file.size > 150000) {
          fileIn.value = ''; f.querySelector('.acc-file-n').textContent = 'No file chosen';
          if (box) { box.textContent = 'The logo is larger than 150 KB. Save it smaller (for example 400 × 400 pixels) and try again.'; box.hidden = false; }
          return;
        }
        var rd = new FileReader();
        rd.onload = function () { f._logo = rd.result; var pv = f.querySelector('.logo-prev'); if (pv) pv.innerHTML = '<img src="' + rd.result + '" alt="Company logo" title="Company logo">'; };
        rd.readAsDataURL(file);
      });
      submit(f, function (v) {
        if (f._logo) v.logo = f._logo;
        v.locations = String(v.locations || '').split(/\n+/).map(function (x) { return x.trim(); }).filter(Boolean);
        return api('PUT', '/api/claims/' + f.getAttribute('data-id') + '/page', v).then(function () { flash('The company page is saved' + (f._logo ? ', with your logo' : '') + '. It shows on the site after the next update.'); return load(); });
      });
    });
    on('[data-stats]', function (b) {
      var out = b.closest('form').querySelector('.stats-out');
      api('GET', '/api/claims/' + b.getAttribute('data-stats') + '/stats').then(function (r) {
        out.innerHTML = r.jobs.length ? '<div class="tablewrap"><table><tr><th>Job page</th><th>Views</th><th>Clicks on Apply</th></tr>' + r.jobs.map(function (j) {
          return '<tr><td><a href="' + esc(j.page) + '">' + esc(j.page.replace(/^.*\/job\//, '').replace(/\/$/, '')) + '</a></td><td>' + j.views + '</td><td>' + j.applies + '</td></tr>'; }).join('') + '</table></div>' : '<p class="acc-quiet">No views counted yet. They show here from the first visit to one of your job pages.</p>';
      }, function (e) { out.innerHTML = '<p class="acc-err">' + esc(e.message) + '</p>'; });
    });
    submit(document.getElementById('team-add'), function (v) { return api('POST', '/api/team', v).then(function () { flash(esc(v.email) + ' is on the team. We sent them a letter.'); return load(); }); });
    on('[data-team-del]', function (b) { api('DELETE', '/api/team/' + encodeURIComponent(b.getAttribute('data-team-del'))).then(function () { flash('Removed from the team.'); return load(); }, fail); });
    submit(document.getElementById('work-email'), function (v) {
      return api('POST', '/api/domain/email', { email: v.email }).then(function (r) { flash(esc(r.message || ('We sent a link to ' + v.email + '. Open it to tie your account to your company.'))); return load(); });
    });
    submit(document.getElementById('domain'), function (v) {
      return api('POST', '/api/domain/token', v).then(function (r) {
        document.getElementById('domain-out').innerHTML = '<p>Publish one of these, then press its button:</p><p><strong>A DNS record:</strong> a TXT record named <code>' + esc(r.dns.name) + '</code> with the value <code>' + esc(r.dns.value) + '</code></p>' +
          '<p><strong>Or a file:</strong> <code>' + esc(r.file.url) + '</code> containing <code>' + esc(r.file.content) + '</code></p><p class="acc-btns"><button class="btn sm" type="button" data-check="dns">Check the DNS record</button><button class="btn ghost sm" type="button" data-check="file">Check the file</button></p><p class="acc-err" id="domain-err" role="alert" hidden></p>';
        on('[data-check]', function (b) {
          b.disabled = true;
          api('POST', '/api/domain/check', { method: b.getAttribute('data-check') }).then(function () { flash('Your company’s domain is proved. You can post jobs now.'); return load(); },
            function (e) { b.disabled = false; var box = document.getElementById('domain-err'); if (box) { box.textContent = e.message; box.hidden = false; } });
        });
      });
    });
    on('.li-start', function () { api('POST', '/api/auth/linkedin/start').then(function (r) { location.href = r.url; }, fail); });
    submit(document.getElementById('talent-search'), function (v) {
      var qs = Object.keys(v).filter(function (k) { return v[k]; }).map(function (k) { return k + '=' + encodeURIComponent(v[k]); }).join('&');
      return api('GET', '/api/talent/search?' + qs).then(function (r) {
        document.getElementById('talent-out').innerHTML = (r.total ? '<p class="acc-quiet">' + r.total + ' found.</p>' : empty('Nobody found for this search.', ' Try fewer words, or leave the place empty.', '')) + r.results.map(function (c) {
          return '<div class="card acc-form"><p><strong>' + esc(c.name || c.headline || 'Candidate') + '</strong>' + [c.name ? c.headline : '', c.level, c.years ? c.years + ' years' : '', c.places.join(', ')].filter(Boolean).map(function (x) { return ' · ' + esc(x); }).join('') + '</p><p class="note">' + esc(c.skills.join(', ')) + '</p>' +
            (c.summary ? '<p>' + esc(c.summary) + '</p>' : '') + '<form class="talent-ask" data-id="' + esc(c.id) + '" novalidate><label class="fld"><span class="fld-l">Your message</span><textarea name="message" rows="3" maxlength="1000" required data-need="Write a few words: who you are, the job, and why them." placeholder="Who you are, the job, and why them."></textarea></label>' +
            field('Link to the job (optional)', 'job_url', 'type="url" placeholder="https://"') + err + '<button class="btn sm" type="submit">Ask to contact</button></form></div>';
        }).join('');
        Array.prototype.forEach.call(document.querySelectorAll('form.talent-ask'), function (f) {
          submit(f, function (x) { return api('POST', '/api/talent/' + f.getAttribute('data-id') + '/contact', x).then(function () { f.innerHTML = '<p class="acc-quiet">Sent. You get their name and contacts if they accept.</p>'; }); });
        });
      });
    });

    /* billing and settings */
    on('[data-receipt]', function (b) {
      api('GET', '/api/orders/' + b.getAttribute('data-receipt') + '/receipt').then(function (r) {
        var x = r.receipt, out = document.getElementById('receipt-out');
        out.innerHTML = '<div class="card acc-receipt"><h3 class="acc-h3">Receipt ' + esc(x.number) + '</h3><p>' + nice(x.date) + ' · ' + esc(x.seller) + '</p><p>To: ' + esc(x.buyer.email) + (x.buyer.company ? ', ' + esc(x.buyer.company) : '') + '</p>' +
          '<p><strong>' + esc(x.item) + '</strong>' + (x.period_days ? ', ' + x.period_days + ' days' : '') + ': ' + money(x.amount_usd) + (x.coupon ? ' (promo code ' + esc(x.coupon.code) + ', full price ' + money(x.coupon.full_usd) + ')' : '') + ', paid with ' + esc(x.paid_with) + '.</p><p class="note">' + esc(x.note) + '</p>' +
          '<p class="acc-btns"><button class="btn ghost sm" type="button" onclick="document.getElementById(\'acc\').classList.add(\'pr\');window.print()">Print</button></p></div>';
        out.scrollIntoView({ block: 'nearest' });
      }, fail);
    });
    on('#acc-pass', function (b) {
      b.disabled = true;
      api('POST', '/api/auth/reset/request', { email: me.email }).then(function () { b.textContent = 'Sent'; say('<b>A link is on its way to ' + esc(me.email) + '.</b> Open it to choose a new password. It works for a short time, so use it soon.'); }, function (e) { b.disabled = false; fail(e); });
    });
    on('#me-export', function () {
      api('GET', '/api/me/export').then(function (r) {
        var a = document.createElement('a'); a.href = URL.createObjectURL(new Blob([JSON.stringify(r, null, 2)], { type: 'application/json' })); a.download = 'my-data-' + new Date().toISOString().slice(0, 10) + '.json';
        document.body.appendChild(a); a.click(); a.remove();
      }, fail);
    });
    submit(document.getElementById('me-delete'), function (v) {
      if (v.confirm.toLowerCase() !== 'delete my account') throw oops('confirm', 'Type the words “delete my account” exactly, to show you mean it.');
      return api('DELETE', '/api/me', { confirm: v.confirm }).then(function (r) { forget(); H.set('hrn_known', 0); cleanUrl(); flash(esc(r.message)); drawAuth('up'); window.scrollTo(0, 0); });
    });
  }
  // back from the checkout: wait for the confirmation and say plainly what happened
  function watchOrder() {
    var id = new URLSearchParams(location.search).get('order'), box = document.getElementById('acc-pay');
    if (!id || !box) return;
    var tries = 0;
    (function check_() {
      api('GET', '/api/orders/' + encodeURIComponent(id) + '?refresh=1').then(function (r) {
        var o = r.order; box = document.getElementById('acc-pay'); if (!box) return;
        if (o.status === 'paid') {
          cleanUrl();
          var tell = function () {      // a boost bought for a job that waits for review does not run yet: say so instead of "it is on"
            var held = S.placements.some(function (p) { return p.state === 'held' && p.label === o.label; });
            say('<b>Payment received:</b> ' + esc(o.name) + (o.label && o.label !== o.name ? ' for ' + esc(o.label) : '') +
              (/^credits/.test(o.product) ? '. The credits are in your account: use them on any promotion with “Pay from my credits”.' :
                held ? '. It starts the moment the job is approved; the paid days do not run while it waits.' : ' is on. It shows on the site within about ten minutes.'));
          };
          if (!S.orders.some(function (x) { return x.id === o.id && x.status === 'paid'; })) load().then(tell, function () {}); else tell();
        } else if (o.status === 'pending' && tries++ < 45) {
          box.innerHTML = '<div class="banner" role="status">Waiting for the network to confirm your payment. This page updates by itself; you can also close it and come back later.</div>';
          setTimeout(check_, 4000);
        } else if (o.status === 'pending') box.innerHTML = '<div class="banner" role="status">The payment has not been confirmed yet. Crypto networks can take a while; it will switch on by itself as soon as it is.</div>';
        else box.innerHTML = '<div class="banner" role="status">This payment is marked “' + esc(STATE[o.status] || o.status) + '”. Nothing was switched on.' + (o.status === 'underpaid' ? ' The amount received was lower than the price.' : '') + '</div>';
      }).catch(function () {});
    })();
  }

  /* ---------- start: links from letters (#confirm=, #reset=, #work=) and the way back from Google or LinkedIn (?code=&state=) ---------- */
  function start() {
    var hash = location.hash, q = new URLSearchParams(location.search), m;
    if ((m = /^#confirm=([a-f0-9]{64})$/.exec(hash))) {
      cleanUrl();
      return api('POST', '/api/auth/confirm', { token: m[1] }).then(function () { flash('<b>Your email is confirmed.</b>'); }, function (e) { flash(esc(e.message), true); usedLink = true; }).then(begin);
    }
    if ((m = /^#reset=([a-f0-9]{64})$/.exec(hash))) { cleanUrl(); return drawReset(m[1]); }
    if ((m = /^#signin=([a-f0-9]{64})$/.exec(hash))) {
      cleanUrl();
      return api('POST', '/api/auth/link/confirm', { token: m[1] }).then(function (r) { token = r.token; H.set('hrn_token', token); fresh = true; flash('<b>You are signed in.</b>'); }, function (e) { flash(esc(e.message), true); usedLink = true; }).then(begin);
    }
    if ((m = /^#work=([a-f0-9]{64})$/.exec(hash))) {
      cleanUrl();
      return api('POST', '/api/domain/email/confirm', { token: m[1] }).then(function (r) { flash(esc(r.message || 'Your work email is confirmed: your account is tied to your company.')); }, function (e) { flash(esc(e.message), true); }).then(begin);
    }
    if (q.get('error') && q.get('state')) { cleanUrl(); flash('The sign-in was cancelled.', true); return begin(); }
    if (q.get('code') && q.get('state')) {
      var secret = ''; try { secret = sessionStorage.getItem('hrn_google') || ''; sessionStorage.removeItem('hrn_google'); } catch (e) {}
      var code = q.get('code'), st = q.get('state'); cleanUrl();
      var liSecret = ''; try { liSecret = sessionStorage.getItem('hrn_li') || ''; sessionStorage.removeItem('hrn_li'); } catch (e) {}
      var signedIn = function (r) { token = r.token; H.set('hrn_token', token); fresh = true; flash(r.created ? '<b>Welcome:</b> your account is ready.' : ''); };
      if (liSecret && !token) return api('POST', '/api/auth/linkedin/callback', { code: code, state: st, secret: liSecret }).then(signedIn, function (e) { flash(esc(e.message), true); }).then(begin);
      if (secret) return api('POST', '/api/auth/google/callback', { code: code, state: st, secret: secret }).then(signedIn, function (e) { flash(esc(e.message), true); }).then(begin);
      if (token) return api('POST', '/api/auth/linkedin/callback', { code: code, state: st }).then(function () { flash('Your LinkedIn profile is attached.'); }, function (e) { flash(esc(e.message), true); }).then(begin);
    }
    return begin();
  }
  function begin() {
    if (token) return load().catch(function (e) {
      if (e.status === 401) { if (token) ended(); else if (!root.querySelector('.acc-gate')) drawAuth('in'); return; }
      if (hd) hd.hidden = true;
      root.innerHTML = '<div class="acc-gate one"><div class="card acc-auth"><p class="acc-lbl">Your account</p><h1 class="acc-t sm">The account <b>did not load</b></h1><p class="acc-sub">' + esc(e.message) + '</p>' +
        '<p class="acc-btns"><button class="btn primary" type="button" id="acc-retry">Try again</button><button class="btn ghost" type="button" id="acc-out2">Sign out</button></p></div></div>';
      document.getElementById('acc-retry').addEventListener('click', function () { root.innerHTML = waiting; begin(); });
      document.getElementById('acc-out2').addEventListener('click', signOut);
    });
    return drawAuth(notice || H.get('hrn_known', 0) ? 'in' : 'up');      // a browser that has been signed in before opens on "Sign in", a new one on "Create account"
  }
  window.addEventListener('hashchange', function () {
    if (/^#(confirm|reset|work|signin)=/.test(location.hash)) return start();      // a link from a letter opened in a tab where the account is open already
    if (!me || !root.querySelector('.acc-shell')) return;
    if (Date.now() - saidAt > 1500) { var box = document.getElementById('acc-say'); if (box) box.innerHTML = ''; }
    showTab(); if (!ALIAS[location.hash.slice(1)]) toTop();
  });
  var waiting = '<div class="acc-wait"><p class="note">Loading your account…</p></div>';
  if (hd) hd.hidden = true;
  root.innerHTML = waiting;
  api('GET', '/api/public/products').then(setPub, function () {}).then(start);
})();
