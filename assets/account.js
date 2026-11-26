/* Your account, for job seekers and employers alike: sign in (email and password, or Google), job alerts, saved jobs on every device,
   your resumes, your resume for employers (only if you tick it), and for employers: free posting, what a job brought, company pages,
   the team, promotions and receipts. Everything you keep here can be downloaded or deleted in Settings. Talks to the API in data-api;
   the rules behind each part are in server/README.md. Nothing here needs a person on our side: a paid order switches itself on.

   How the page is put together (pass of 17 Nov 2026):
   - one side at a time. hrn_role (seeker or employer) decides which menu and which first screen are drawn; the other side is one press
     away ("Hiring?" / "Looking for a job?") and a link to one of its parts (#post, #resumes) switches by itself;
   - every part opens with a small label and a two-weight headline, has one main button, and says in one sentence what to do when it is empty;
   - a mistake is said next to the field it belongs to (check for what the browser can tell, ERR_FIELD for what the server answers);
   - the header (site.js) is told whenever the sign-in or the side changes: the event "hrn:auth" on document.
   Pass of 25 Nov 2026 (PLAN_RU.md part 2, items 1, 2, 4, 9, 10, and the look of dlocal.com and ashbyhq.com): one framed panel per section
   (part), icons in the menu, a pill with an arrow for the main action (go); a job seeker's status for employers, "Who sees you" (who can
   find the resume, its own link, the companies it is hidden from, who opened it), a payment link for whoever pays (#invoice=), a shared
   resume (#cv=), two-step sign-in and the password changed with the old one. Each new part is drawn only when the server's answer
   carries its new field (pub.pay_links, me.seeking, me.two_step, me.has_password, profile.visibility, profile.viewers, order.can_share),
   so the page keeps working unchanged with a server that does not have them yet. */
(function () {
  var root = document.getElementById('acc');
  if (!root || !window.HRN) return;
  var H = window.HRN, esc = H.esc, API = root.getAttribute('data-api').replace(/\/+$/, '');
  var D = JSON.parse(document.getElementById('acc-data').textContent);
  var hd = document.getElementById('acc-hd');                       // the page's own title and lead: read without JavaScript and while it loads
  var token = H.get('hrn_token', ''), me = null, pub = { products: [], payments: 'off' }, products = {}, S = {}, notice = '', noticeBad = false, saidAt = 0, fresh = false, usedLink = false;
  var promo = null, paintPost = null, shareOpen = '';                // shareOpen: the order whose payment link is open in Billing (kept across reloads of S)                               // a promo code that was applied: { code, percent, quotes: { product id: { amount_usd, full_usd } } }
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
    confirm: 'confirm', consent: 'consent', message: 'message', name: 'name', current: 'current', code: 'code', code_gone: 'code', blocked: 'blocked', job_url: 'job_url' };
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
  // one framed panel per section (pass of 25 Nov 2026): a small label above a headline in two weights, then what the section holds
  var part = function (title, inner, id, label, cls) {
    return '<section class="acc-sec acc-pan' + (cls ? ' ' + cls : '') + '"' + (id ? ' id="acc-' + id + '"' : '') + '>' + (label ? '<p class="acc-lbl sm">' + label + '</p>' : '') + '<h2 class="acc-h2">' + title + '</h2>' + inner + '</section>';
  };
  /* small line icons for the menu and the empty states (24 px grid, drawn with the text colour) */
  var IC = { overview: 'M4 4h7v7H4zM13 4h7v7h-7zM4 13h7v7H4zM13 13h7v7h-7z', saved: 'M6 3h12v18l-6-4-6 4z', resumes: 'M7 3h7l5 5v13H7zM14 3v5h5M10 13h6M10 17h6',
    alerts: 'M6 16v-5a6 6 0 0 1 12 0v5l2 2H4zM10 21h4', visibility: 'M2 12s3.6-7 10-7 10 7 10 7-3.6 7-10 7S2 12 2 12zM12 9a3 3 0 1 0 0 6 3 3 0 0 0 0-6z',
    settings: 'M4 7h9M17 7h3M4 12h3M11 12h9M4 17h11M19 17h1M15 5v4M9 10v4M17 15v4', jobs: 'M3 8h18v12H3zM8 8V5h8v3M3 13h18', post: 'M12 3a9 9 0 1 0 0 18 9 9 0 0 0 0-18zM12 8v8M8 12h8',
    promote: 'M3 17l6-6 4 4 8-8M15 7h6v6', credits: 'M12 3a9 9 0 1 0 0 18 9 9 0 0 0 0-18zM9.5 15c.5 1 1.5 1.5 2.5 1.5 1.7 0 2.8-.9 2.8-2.2 0-3-5.6-1.6-5.6-4.6C9.2 8.4 10.3 7.5 12 7.5c1 0 2 .5 2.5 1.5M12 6v1.5M12 16.5V18',
    company: 'M4 21V5l8-2v18M12 9h8v12M3 21h18M8 8v.01M8 12v.01M8 16v.01M16 13v.01M16 17v.01', team: 'M9 11a4 4 0 1 0 0-8 4 4 0 0 0 0 8zM2 21v-1a7 7 0 0 1 14 0v1M16 3.6a4 4 0 0 1 0 7.8M22 21v-1a7 7 0 0 0-4-6.3',
    find: 'M11 4a7 7 0 1 0 0 14 7 7 0 0 0 0-14zM20 20l-4-4', billing: 'M6 3h12v18l-3-2-3 2-3-2-3 2zM9 8h6M9 12h6M9 16h4', arrow: 'M5 12h14M13 6l6 6-6 6',
    lock: 'M6 11h12v10H6zM8 11V8a4 4 0 0 1 8 0v3', link: 'M10 14a4 4 0 0 0 5.7 0l3-3a4 4 0 0 0-5.7-5.7l-1 1M14 10a4 4 0 0 0-5.7 0l-3 3a4 4 0 0 0 5.7 5.7l1-1', mail: 'M3 6h18v12H3zM3 7l9 6 9-6',
    check: 'M5 12l4 4 10-10', shield: 'M12 3l8 3v6c0 4.5-3.4 8.3-8 9-4.6-.7-8-4.5-8-9V6z' };
  var icon = function (k, cls) { return '<svg class="ic' + (cls ? ' ' + cls : '') + '" viewBox="0 0 24 24" aria-hidden="true" focusable="false"><path d="' + (IC[k] || IC.overview) + '"/></svg>'; };
  // the one main action of a block: a pill with an arrow in a circle (DESIGN_STUDY.md, "dLocal and Ashby", 6)
  var go = function (href, label, ghost) { return '<a class="btn ' + (ghost ? 'ghost' : 'primary') + ' acc-go" href="' + href + '">' + label + '<span class="acc-arr">' + icon('arrow') + '</span></a>'; };
  var empty = function (title, text, action, ic) { return '<div class="acc-none">' + (ic ? '<span class="acc-none-i">' + icon(ic) + '</span>' : '') + '<p><b>' + title + '</b>' + text + '</p>' + (action || '') + '</div>'; };
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
      // what the server of 25 Nov 2026 adds, said only where it answers with it
      if (emp && pub.pay_links === 'on') why.splice(3, 0, ['A payment link for your accountant', 'They pay without an account, and the receipt is on the same page.']);
      if (!emp && pub.talent === 'on' && pub.two_step === 'on') why.splice(3, 0, ['You decide who sees your resume', 'Open to offers, only by its link or hidden from your employer; you see which companies looked.']);
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
        return api('POST', up ? '/api/auth/signup' : '/api/auth/login', v).then(function (r) {
          if (r.step === 'code') return drawCode(v, r);            // two-step sign-in: the password was right, the code from the mail comes next
          token = r.token; H.set('hrn_token', token); fresh = !up; flash(''); return load();
        });
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
  /* two-step sign-in, the second step: the six digits from the letter. The email and password stay in this function only, for
     "Send a new code" (which signs in again), and are dropped as soon as the code is accepted. */
  function drawCode(cred, r) {
    if (hd) hd.hidden = true;
    var ticket = r.ticket;
    root.innerHTML = '<div class="acc-gate one"><div class="card acc-auth"><p class="acc-lbl"><i></i>Two-step sign-in</p><h1 class="acc-t sm">Type the <b>code from your email</b></h1>' +
      '<p class="acc-sub" id="code-said">' + esc(r.message || 'We sent a code of six digits to your address.') + ' It works for ' + (r.minutes || 10) + ' minutes.</p><form novalidate>' +
      field('Code', 'code', 'type="text" inputmode="numeric" autocomplete="one-time-code" maxlength="7" required data-need="Type the six digits from the letter." placeholder="000000" class="acc-code"',
        r.code ? 'Test mode, no mailbox on this machine: the code is ' + esc(r.code) + '.' : 'The newest letter has the code that works. Check the spam folder too.') +
      err + '<button class="btn primary lg wide" type="submit">Sign in</button></form>' +
      '<p class="acc-alt"><a href="#" id="code-again">Send a new code</a> · <a href="#" data-mode="in">Back to sign in</a></p></div></div>';
    var form = root.querySelector('form');
    try { form.elements.code.focus(); } catch (e) {}
    submit(form, function (v) {
      return api('POST', '/api/auth/login/code', { ticket: ticket, code: v.code }).then(function (x) { cred = null; token = x.token; H.set('hrn_token', token); fresh = true; flash(''); return load(); }, function (e) {
        if (e.code === 'code_gone') { cred = null; flash(esc(e.message), true); drawAuth('in'); e.gone = true; }
        throw e;
      });
    });
    document.getElementById('code-again').addEventListener('click', function (ev) {
      ev.preventDefault(); if (!cred) return drawAuth('in');
      api('POST', '/api/auth/login', cred).then(function (x) {
        if (x.step !== 'code') { token = x.token; H.set('hrn_token', token); fresh = true; return load(); }
        ticket = x.ticket; document.getElementById('code-said').textContent = 'A new code is on its way to ' + x.sent_to + '. Only the newest one works.';
        var h = form.querySelector('.hint'); if (h && x.code) h.textContent = 'Test mode, no mailbox on this machine: the code is ' + x.code + '.';
      }, function (e) { authSay(e.message); });
    });
    Array.prototype.forEach.call(root.querySelectorAll('[data-mode]'), function (t) { t.addEventListener('click', function (ev) { ev.preventDefault(); cred = null; drawAuth('in'); }); });
    window.scrollTo(0, 0);
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
  document.addEventListener('hrn:signout', function () { if (token) signOut(); });
  // a "More" menu of a job closes when the person clicks anywhere else or presses Escape
  document.addEventListener('click', function (ev) { Array.prototype.forEach.call(root.querySelectorAll('.acc-menu[open]'), function (m) { if (!m.contains(ev.target)) m.open = false; }); });
  document.addEventListener('keydown', function (ev) { if (ev.key === 'Escape') Array.prototype.forEach.call(root.querySelectorAll('.acc-menu[open]'), function (m) { m.open = false; var s = m.querySelector('summary'); if (s) s.focus(); }); });      // "Sign out" in the header menu, pressed on this page

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
      if (afterAuth) { var back = afterAuth; afterAuth = ''; location.hash = back; }
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
      (S.incoming || []).forEach(function (q) { if (q.status === 'sent') up('warn', '<b>' + esc(q.company) + '</b> asked to contact you about a job.', '#visibility', 'Answer'); });
      var tp = S.talent && S.talent.profile;
      if (tp && tp.views && tp.views.companies) up('ok', '<b>' + tp.views.companies + plural(tp.views.companies, ' company', ' companies') + '</b> opened your resume' + (tp.viewers && tp.viewers[0] ? ', the latest ' + esc(tp.viewers[0].company) + ' on ' + nice(tp.viewers[0].last) : '') + '.', '#visibility', 'See who');
      row = nums([[t.saved, plural(t.saved, 'saved job', 'saved jobs'), '#saved'], [t.applied, plural(t.applied, 'application', 'applications'), '#saved'], [nres, plural(nres, 'resume', 'resumes'), '#resumes'], [S.alerts.length, plural(S.alerts.length, 'job alert', 'job alerts'), '#alerts']]);
      if (!nres) steps.push(['Keep your resume here', 'Make it in the free builder, then press “Save to my account”.', '#resumes']);
      if (!S.alerts.length) steps.push(['Get new jobs by email', 'Choose the words and how often. One click stops it.', '#alerts']);
      if (!t.saved && !t.applied) steps.push(['Save the jobs you like', 'Press Save on a job: it is here and on your phone too.', esc(D.site) + '/jobs/']);
      if (pub.talent === 'on' && S.talent && !S.talent.profile) steps.push(['Let employers find you', 'Only if you tick the box. Your name and contacts stay hidden until you accept a request.', '#visibility']);
      setTimeout(fillFit, 0);
    }
    // one framed panel on top: who, the headline, the main button, the person's own figures in a row (and a job seeker's status)
    return '<div class="acc-hero">' + head(emp ? 'Employer account' : 'Job seeker account', emp ? 'Your hiring <b>at a glance</b>' : 'Your job search <b>at a glance</b>', '',
        emp ? go('#post', 'Post a job') : go(esc(D.site) + '/jobs/', 'Search jobs')) + (emp ? '' : seekPick()) + row + '</div>' +
      (ups.length ? part('What needs <b>you</b>', '<ul class="acc-ups">' + ups.slice(0, 12).join('') + '</ul>', 'ups', 'Now') : '') +
      (steps.length ? part('Next <b>steps</b>', '<ul class="acc-steps">' + steps.map(function (x) { return '<li><a href="' + x[2] + '"><b>' + x[0] + '</b><span>' + x[1] + '</span><i class="acc-arr">' + icon('arrow') + '</i></a></li>'; }).join('') + '</ul>', '', 'To do') : '') +
      (emp ? '' : '<div id="acc-fit" hidden></div>');
  }
  /* the job seeker's status for employers (LinkedIn's "Open to work", hh.ru's "ищу работу"): only with a server that keeps it (me.seeking)
     and the resume database on, because only employers who search the database see it */
  var SEEK = [['active', 'Looking actively'], ['open', 'Open to offers'], ['not', 'Not looking']];
  function seekPick(plain) {
    if (me.seeking === undefined || pub.talent !== 'on') return '';
    var on_ = S.talent && S.talent.profile;
    return '<div class="acc-seek' + (plain ? ' inset' : '') + '">' + (plain ? '' : '<p class="acc-seek-l">' + icon('visibility') + '<span>Your status for employers</span></p>') + '<div class="acc-pills" role="group" aria-label="Your status for employers">' + SEEK.map(function (x) {
      return '<button type="button" class="acc-pill" data-seek="' + x[0] + '" aria-pressed="' + (me.seeking === x[0]) + '">' + (me.seeking === x[0] ? icon('check') : '') + x[1] + '</button>'; }).join('') + '</div>' +
      '<p class="acc-seek-n">' + (on_ ? (me.seeking ? 'Shown on your resume to employers who search the resume database' + (me.seeking_since ? ', since ' + nice(me.seeking_since) : '') + '. Press it again to hide it.' : 'Not said. Employers who search the resume database see it on your resume once you choose.')
        : 'Employers see it once you <a href="#visibility">let them find your resume</a>.') + '</p></div>';
  }
  /* Jobs that fit you, in the job seeker's overview (plan, part 2 item 3, 20 Nov 2026: other sites show matches in the account; ours did
     not). From the answers given on For you, kept in this browser, matched against today's open jobs here: nothing is sent anywhere. */
  function fillFit() {
    var box = document.getElementById('acc-fit'); if (!box) return;
    var p = H.get('hrn_profile', null) || {}, cats = p.cats || [], skills = p.skills || [], pay = Number(p.pay) || 0;
    if (!cats.length && !skills.length && !p.where && !pay) {
      box.innerHTML = part('Jobs that <b>fit you</b>', '<p class="acc-sub">Answer five questions on <a href="' + esc(D.site) + '/for-you/">For you</a>: the newest jobs that fit your answers then show here.</p>', '', 'For you');
      box.hidden = false; return;
    }
    H.listOf(H.fitQuery(p)).then(function (got) {      // asked of the server (the list of every job, 22 MB, was downloaded for this until 25 Nov 2026)
      var fit = got.rows.slice().sort(function (a, b) { return (b[16] || 0) - (a[16] || 0); });
      box.innerHTML = part('Jobs that <b>fit you</b>', fit.length
        ? '<p class="acc-sub">' + got.total.toLocaleString('en-US') + ' open jobs fit your answers on For you. The newest:</p><ul class="jobs">' + fit.slice(0, 5).map(function (j) { return H.card(j); }).join('') + '</ul>' +
          '<p><a href="' + esc(D.site) + '/for-you/">See all of them, or change your answers</a></p>'
        : '<p class="acc-sub">No open job fits all your answers today. <a href="' + esc(D.site) + '/for-you/">Loosen one of them on For you</a>.</p>', '', 'For you');
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
        : empty('Nothing saved yet.', ' Press Save on any job, or mark it as applied: it shows here and in every browser where you sign in.', go(esc(D.site) + '/jobs/', 'Search jobs'), 'saved')) +
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
    var list = n ? part('Saved <b>versions</b>', '<div class="acc-list">' + R.resumes.map(function (r) {
      return '<div class="acc-row"><span class="rs-i" aria-hidden="true">CV</span><div class="main"><strong>' + esc(r.name) + '</strong><span class="js">' + (r.title ? esc(r.title) + ' · ' : '') + 'updated ' + nice(r.updated) + '</span></div>' +
        '<div class="ctl"><button class="btn ghost sm" type="button" data-res-open="' + esc(r.id) + '">Open in the builder</button><button class="btn ghost sm" type="button" data-res-del="' + esc(r.id) + '">Delete</button></div></div>';
    }).join('') + '</div>', 'versions', n + ' of ' + R.max) : '';
    var none = n ? '' : !me.confirmed ? confirmLine('Your resumes are kept here') : local ? '' :
      empty('No resume yet.', ' Make one in the free builder, then press “Save to my account” there: it is kept here and opens on any device.', builder, 'resumes');
    var t = pub.talent === 'on' && S.talent ? S.talent.profile : undefined;
    var forEmp = t === undefined ? '' : callout(t ? '<b>Employers ' + (t.paused ? 'cannot find your resume now' : t.visibility === 'link' ? 'see your resume only by its link' : 'can find your resume') + '.</b> Who sees it, who looked, and the companies it is hidden from: on Who sees you.'
      : '<b>Employers cannot find you yet.</b> Let them find your resume without your name and contacts: you decide who sees it.', '<a class="btn ghost sm" href="#visibility">Who sees you</a>', 'soft');
    return head('Resumes', 'Your <b>resumes</b>', 'Up to ' + R.max + ' versions, one for each kind of job you apply for. Open any of them in the builder on any device.', n || local || !me.confirmed ? builder : '') +
      save + list + none + forEmp;
  }
  /* ---------- job seeker: who sees the resume (PLAN_RU.md part 2, items 1, 2, 4; pass of 25 Nov 2026). The status for employers, who can
     find it (everyone who searches, only by its link, nobody), the companies it is hidden from, who opened it, the requests, and the
     resume as employers see it. Each part that needs the server of 25 Nov 2026 shows only when its answer carries the new field. ---------- */
  var SEEKN = { active: 'Looking actively', open: 'Open to offers', not: 'Not looking' };
  var ASKED = { sent: 'Waiting for their answer', accepted: 'Accepted', declined: 'Declined', expired: 'No answer in 14 days' };
  var cap = function (x) { return String(x || '').charAt(0).toUpperCase() + String(x || '').slice(1); };
  var placeName = function (p) { return p === 'remote' ? 'Remote' : String(p).split('-').map(function (w) { return w.length <= 2 ? w.toUpperCase() : cap(w); }).join(' '); };
  function cvCard(c, full) {
    var meta = [c.level ? cap(c.level) : '', c.years ? c.years + plural(c.years, ' year', ' years') : '', (c.places || []).map(placeName).join(', ')].filter(Boolean).join(' · ');
    var ini = c.name ? c.name.split(/\s+/).map(function (w) { return w.charAt(0); }).join('').slice(0, 2).toUpperCase() : '';
    return '<article class="acc-cv"><header class="acc-cv-h"><span class="acc-cv-av">' + (ini ? esc(ini) : icon('lock')) + '</span><div class="acc-cv-t"><h3>' + esc(c.name || c.headline || 'Candidate') + '</h3>' +
      '<p>' + (c.name && c.headline ? esc(c.headline) + (meta ? ' · ' : '') : '') + esc(meta) + '</p></div>' + (c.seeking ? '<span class="acc-badge s-' + esc(c.seeking) + '">' + SEEKN[c.seeking] + '</span>' : '') + '</header>' +
      ((c.skills || []).length ? '<ul class="acc-tags">' + c.skills.slice(0, 18).map(function (x) { return '<li>' + esc(x) + '</li>'; }).join('') + '</ul>' : '') +
      (full ? (c.summary ? '<p class="acc-cv-sum">' + esc(c.summary) + '</p>' : '') +
        ((c.experience || []).length ? '<h4>Experience</h4><ul class="acc-cv-x">' + c.experience.map(function (x) {
          return '<li><b>' + esc(x.role || 'Role') + '</b>' + (x.org ? ' · ' + esc(x.org) : '') + (x.dates ? '<span>' + esc(x.dates) + '</span>' : '') + (x.text ? '<p>' + esc(x.text) + '</p>' : '') + '</li>'; }).join('') + '</ul>' : '') +
        ((c.education || []).length ? '<h4>Education</h4><ul class="acc-cv-x">' + c.education.map(function (x) {
          return '<li><b>' + esc(x.what || '') + '</b>' + (x.org ? ' · ' + esc(x.org) : '') + (x.dates ? '<span>' + esc(x.dates) + '</span>' : '') + '</li>'; }).join('') + '</ul>' : '') : '') + '</article>';
  }
  function visibilityPanel() {
    if (!(pub.talent === 'on' && S.talent)) return '';
    var t = S.talent.profile, local = H.get('hrn_resume', null);
    var top = head('Who sees you', 'Who <b>sees your resume</b>', 'Employers with a proved company account search the resume database. You decide if you are in it and who may see you, and you see who looked.');
    var how = '<ol class="acc-how"><li><b>You switch it on.</b> Your resume is kept on our server only after you tick the box.</li><li><b>Employers find it without your name.</b> No email, phone or links; you can hide it from your own employer.</li>' +
      '<li><b>You accept, or not.</b> An employer gets your name and contacts only when you accept its request.</li></ol>';
    if (!t) return top + (!local ? part('Make your resume <b>first</b>', how + '<p class="acc-sub">Employers can find you only by a resume. Make it in the free builder, then come back here to switch this on.</p><p class="acc-btns">' + go(esc(D.site) + '/resume/', 'Open the resume builder') + '</p>', 'talent', 'Off now')
      : part('Let employers <b>find you</b>', how + (!me.confirmed ? confirmLine('You can switch this on') :
        '<form id="talent-on" novalidate><label class="check acc-consent"><input type="checkbox" name="consent" required data-need="Tick the box first: nothing is stored without it."> <span>' + esc(S.talent.consent_text) + '</span></label>' +
        '<details class="acc-more"><summary>Choose the kinds of work, the places and who never sees it (optional)</summary>' + talentFields(null, true) + '</details>' + err +
        '<p class="acc-btns"><button class="btn primary" type="submit">Let employers find my resume</button></p></form>'), 'talent', 'Off now'));
    var fresh2 = t.visibility !== undefined, mode = t.paused ? 'none' : t.visibility === 'link' ? 'link' : 'all';
    var opt = function (c, ic, name, text) {
      return '<label class="acc-opt"><input type="radio" name="vis" value="' + c + '"' + (mode === c ? ' checked' : '') + '><span class="acc-opt-i">' + icon(ic) + '</span><span class="acc-opt-t"><b>' + name + '</b>' + text + '</span></label>'; };
    var share = t.share_url ? '<div class="acc-share"><p class="fld-l">' + icon('link') + 'Your resume’s own link</p><div class="acc-share-r"><input type="text" readonly value="' + esc(t.share_url) + '" aria-label="Your resume’s own link">' +
      '<button class="btn sm" type="button" data-copy="' + esc(t.share_url) + '">Copy</button><a class="btn ghost sm" href="' + esc(t.share_url) + '" target="_blank" rel="noopener">Open</a></div>' +
      '<p class="hint">It shows your resume without your name or contacts, ' + (mode === 'none' ? 'once you show it again.' : 'to anyone you send it to.') + ' <button class="linkbtn" type="button" id="cv-new">Make a new link</button> and the old one stops at once.</p></div>' : '';
    var who = fresh2 ? '<div class="acc-opts" role="radiogroup" aria-label="Who can find your resume">' + opt('all', 'find', 'Employers who search', 'Companies with a proved account find it, without your name or contacts.') +
        opt('link', 'link', 'Only people with the link', 'Not in search. You send its link to the employers you choose.') + opt('none', 'lock', 'Nobody for now', 'Paused: hidden everywhere and kept. Switch it back any time.') + '</div>' + share
      : '<p class="acc-fold-h"><b>' + (t.paused ? 'Paused: employers cannot find it.' : 'On: employers can find your resume.') + '</b> Since ' + nice(t.consented) + ', updated ' + nice(t.updated) + '.</p>' +
        '<p class="acc-btns"><button class="btn ghost sm" type="button" id="talent-pause">' + (t.paused ? 'Show it again' : 'Pause') + '</button></p>';
    var bl = t.blocked || [];
    var hidden = '<p class="acc-sub">Your current employer, say. They see your resume neither in search nor by its link: every account on that web address is left out.</p>' +
      (bl.length ? '<ul class="acc-chips">' + bl.map(function (d) { return '<li>' + icon('lock') + '<span>' + esc(d) + '</span><button type="button" data-unblock="' + esc(d) + '" aria-label="Show it to ' + esc(d) + ' again" title="Show it to them again">×</button></li>'; }).join('') + '</ul>' : '') +
      '<form id="block-add" class="acc-inline flat" novalidate>' + field('Company’s web address', 'blocked', 'type="text" autocomplete="off" placeholder="yourcompany.com" required data-need="Enter the company’s web address, like initech.com."') +
      '<button class="btn ghost" type="submit">Hide it from them</button>' + err + '</form>';
    var V = t.views, list = t.viewers || [];
    var viewed = !V ? '' : part('Who <b>viewed it</b>', '<div class="acc-nums three"><div><b>' + V.companies + '</b><span>' + plural(V.companies, 'company opened it', 'companies opened it') + '</span></div>' +
        '<div><b>' + V.shown_7 + '</b><span>times in search results, last 7 days</span></div><div><b>' + V.shown_30 + '</b><span>times in search results, last 30 days</span></div></div>' +
      (list.length ? '<div class="acc-list">' + list.map(function (v) {
        return '<div class="acc-row"><span class="acc-co" aria-hidden="true">' + esc(String(v.company || v.domain).charAt(0).toUpperCase()) + '</span><div class="main"><strong>' + esc(v.company || v.domain) + '</strong><span class="js">' + esc(v.domain) + ' · ' +
          (v.via === 'link' ? 'by your link' : 'from search') + ' · ' + (v.times > 1 ? 'opened ' + v.times + ' times, last on ' : 'opened on ') + nice(v.last) + '</span></div>' +
          (v.asked ? '<div class="ctl">' + state(v.asked, v.asked === 'sent' ? 'Asked to contact you' : '') + '</div>' : '') + '</div>'; }).join('') + '</div>'
        : '<p class="acc-quiet">No company has opened your resume yet.' + (V.shown_7 ? ' It was among search results ' + V.shown_7 + plural(V.shown_7, ' time', ' times') + ' this week.' : '') + '</p>') +
      '<p class="note">Each company that opens your resume is listed here, as on hh.ru and LinkedIn. It still has no name or contacts of yours until you accept its request.</p>', 'views', 'Views');
    var req = S.incoming.length ? part('Employers who <b>asked to contact you</b>', '<div class="acc-list">' + S.incoming.map(function (q) {
      return '<div class="acc-row"><div class="main">' + state(q.status) + ' <strong>' + esc(q.company) + '</strong> <span class="js">' + esc(q.domain) + ' · ' + nice(q.received) + '</span><p class="acc-msg">' + esc(q.message) + '</p>' +
        (q.job_url ? '<a class="tt" href="' + esc(q.job_url) + '" rel="noopener">The job</a>' : '') + '</div><div class="ctl">' + (q.status === 'sent' ? '<button class="btn sm" type="button" data-q="accept" data-id="' + esc(q.id) + '">Accept</button><button class="btn ghost sm" type="button" data-q="decline" data-id="' + esc(q.id) + '">Decline</button>' : '') + '</div></div>';
    }).join('') + '</div><p class="note">Accepting gives that employer your name and contact details. Declining, or not answering in 14 days, tells it nothing about you.</p>', 'requests', 'Requests') : '';
    var preview = part('What employers <b>see</b>', cvCard(t.as_employers_see, true) +
      '<p class="acc-btns">' + (local ? '<button class="btn ghost sm" type="button" id="talent-update">Update it with my current resume</button>' : '') + '<button class="btn ghost sm acc-del" type="button" id="talent-del">Delete it for good</button></p>' +
      '<details class="acc-more"><summary>Change the kinds of work, places and what they see</summary><form id="talent-set" novalidate>' + talentFields(t, false) + err +
      '<p class="acc-btns"><button class="btn ghost" type="submit">Save these settings</button></p></form></details>', 'preview', 'Your resume, as they see it');
    var status = me.seeking !== undefined ? part('Your <b>status</b>', seekPick(true), 'status', 'Status') : '';
    return top + status + part('Who can <b>find it</b>', who, 'who', 'Visibility') + viewed + req + part('Hidden from <b>these companies</b>', hidden, 'blocked', 'Never shown to') + preview;
  }
  function talentFields(t, withBlocked) {
    var has = function (list, v) { return (list || []).indexOf(v) >= 0; };
    return '<div class="acc-two"><label class="fld"><span class="fld-l">Level</span><select name="level"><option value="">Not said</option>' + ['entry', 'mid', 'senior', 'lead'].map(function (l) {
      return '<option' + (t && t.level === l ? ' selected' : '') + '>' + l + '</option>'; }).join('') + '</select></label>' +
      field('Years of experience', 'years', 'type="number" min="0" max="60" value="' + (t ? t.years : 0) + '"') + '</div>' +
      '<fieldset class="fld acc-roles"><legend>Kinds of work to be found for (up to 5)</legend>' + D.categories.map(function (c) {
        return '<label><input type="checkbox" data-many name="roles" value="' + esc(c[0]) + '"' + (t && has(t.roles, c[0]) ? ' checked' : '') + '> ' + esc(c[1]) + '</label>'; }).join('') + '</fieldset>' +
      field('Places, as on the site (comma separated)', 'places', 'type="text" value="' + esc(t ? t.places.join(', ') : 'remote') + '" placeholder="remote, germany, london"', 'Place names from the locations pages, and “remote”.') +
      (withBlocked ? field('Companies that must never see it', 'blocked', 'type="text" value="' + esc(t ? t.blocked.join(', ') : '') + '" placeholder="yourcurrentemployer.com"', 'Their web addresses, comma separated: your current employer, say.') : '') +
      '<label class="check"><input type="checkbox" name="show_name"' + (t && t.show_name ? ' checked' : '') + '> <span>Show my name before I accept a request</span></label>' +
      '<label class="check"><input type="checkbox" name="show_employers"' + (t && t.show_employers ? ' checked' : '') + '> <span>Show the names of my employers</span></label>';
  }
  var talentValues = function (v) { return { level: v.level, years: Number(v.years) || 0, roles: v.roles || [], places: v.places.split(/[\s,]+/).filter(Boolean).map(function (x) { return x.toLowerCase(); }),
    blocked: v.blocked === undefined ? undefined : v.blocked.split(/[\s,]+/).filter(Boolean), show_name: !!v.show_name, show_employers: !!v.show_employers }; };
  var FREQ = [['daily', 'Once a day'], ['weekly', 'Once a week'], ['instant', 'Within the hour']];
  function alertsPanel() {
    var freq = function (cur, attr) { return '<select ' + attr + '>' + FREQ.map(function (f) { return '<option value="' + f[0] + '"' + (cur === f[0] ? ' selected' : '') + '>' + f[1] + '</option>'; }).join('') + '</select>'; };
    var form = !me.confirmed ? confirmLine('You can make alerts here') :
      '<form id="alert-new" class="acc-pan acc-form" novalidate><p class="acc-lbl sm">Make one</p><h2 class="acc-h2">' + (S.alerts.length ? 'A new <b>alert</b>' : 'Your first <b>alert</b>') + '</h2><div class="acc-two">' + field('Words in the job', 'q', 'type="text" maxlength="80" placeholder="python, nurse, product manager"') +
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
      (S.alerts.length ? part('Your <b>alerts</b>', list, 'list', S.alerts.length + plural(S.alerts.length, ' alert', ' alerts')) + form : (me.confirmed ? empty('No alerts yet.', ' Make the first one below, or search on the site and press “Free job alerts” under the results.', '', 'alerts') : '') + form);
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
      // the rarer actions in a small menu, so a card shows two or three buttons instead of six (on a phone they took three rows)
      acts += '<details class="acc-menu"><summary class="btn ghost sm" aria-label="More actions for ' + esc(j.title) + '">More</summary><div class="acc-menu-l">' +
        (live || rev ? '<button type="button" data-act="close" data-id="' + esc(j.id) + '">Close the job</button>' : '') +
        '<button type="button" data-job-copy="' + esc(j.id) + '">Post a similar job</button>' + (live ? '<a href="' + esc(D.site + j.page) + '">Open its page</a>' : '') +
        '<button type="button" class="acc-del" data-job-del="' + esc(j.id) + '">Delete</button></div></details>';
      return '<article class="acc-job' + (rej ? ' bad' : '') + '"><div class="acc-job-h"><div>' + state(ending ? 'pending' : j.status, ending ? 'Ends soon' : '') + '<h2 class="acc-job-t">' +
        (live ? '<a href="' + esc(D.site + j.page) + '">' + esc(j.title) + '</a>' : esc(j.title)) + '</h2><p class="js">' + esc(j.company) + (j.location ? ' · ' + esc(j.location) : '') + (j.remote ? ' · Remote' : '') + ' · posted ' + nice(j.posted) + '</p></div>' +
        (live || j.views || j.applies ? '<div class="acc-job-n"><span><b>' + (j.views || 0) + '</b>' + plural(j.views || 0, 'view', 'views') + '</span><span><b>' + (j.applies || 0) + '</b>' + plural(j.applies || 0, 'click on Apply', 'clicks on Apply') + '</span>' + spark + '</div>' : '') + '</div>' +
        '<p class="acc-job-s">' + line + '</p><div class="ctl">' + acts + '</div>' +
        '<form class="job-edit" data-id="' + esc(j.id) + '" novalidate hidden><h3 class="acc-h3">Edit “' + esc(j.title) + '”</h3>' + jobFields(j, me.domain) + err +
        '<p class="acc-btns"><button class="btn primary" type="submit">' + (rej ? 'Save and send again' : 'Save the changes') + '</button><button class="btn ghost" type="button" data-job-cancel="' + esc(j.id) + '">Cancel</button></p>' +
        '<p class="note">' + (rej ? 'It goes to a person again, with your changes.' : 'A changed title, link or text may send the job to a person again before it shows.') + '</p></form></article>';
    }).join('');
    return head('Your jobs', 'Jobs <b>you posted</b>', S.jobs.length ? 'The status of each job, and what it brought: views of its page and clicks on Apply, each visitor counted once a day.' : '',
        S.jobs.length ? go('#post', 'Post a job') : '') +
      (S.jobs.length ? cards + '<p class="note">A new or changed job shows on the site after its next update, within the hour. <button class="linkbtn" type="button" id="jobs-csv">Download these figures (CSV)</button></p>'
        : empty('You have not posted a job yet.', ' Posting is free for 30 days. Its status, views and clicks on Apply show here.', go('#post', 'Post a job free'), 'jobs'));
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
      '<div class="card acc-paste"><p class="acc-lbl sm">Quick start</p><h2 class="acc-h2">Paste the <b>posting</b></h2><label class="fld"><span class="fld-l">Have the posting as text? Paste it and the form fills itself</span>' +
      '<textarea id="job-paste" rows="4" placeholder="The whole posting, as it is on your site or in your message: the title on the first line, then the text."></textarea>' +
      '<span class="hint">The title, place, pay, employment type and the link are read from it right here in your browser; nothing is sent anywhere. Check each field after.</span></label>' +
      '<p class="acc-btns"><button class="btn ghost" type="button" id="job-paste-go">Fill the form from this text</button><span class="note" id="job-paste-out" role="status"></span></p></div>' +
      '<form class="card acc-form" id="acc-job" novalidate><p class="acc-lbl sm">The job</p><h2 class="acc-h2">Check the <b>details</b></h2>' + jobFields(draft, me.domain) + boosts + err +
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
      (me.credits && kind !== 'none' && pub.payments !== 'off' ? '<button class="btn ghost" type="submit" data-credit="1">Pay from my credits (' + money(me.credits) + ' left)</button>' : '') +
      // someone else pays (the accountant): the order is made with its own payment page to send on (needs the server of 25 Nov 2026)
      (pub.pay_links === 'on' && pub.payments !== 'off' ? '<button class="linkbtn pc-for" type="submit" data-for="1">Someone else pays? Get a payment link</button>' : '') + '</div></form>';
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
      part('For <b>one job</b>', jobCards + coverForm, 'one', 'A job') +
      part('For your <b>company</b>', '<div class="card acc-pick">' + field('Company, as it is named on the site', 'company', 'type="text" id="pr-company" list="acc-companies" value="' + esc(me.company || '') + '" maxlength="80"') + '</div>' +
        '<div class="acc-grid">' + productCard('spotlight', 'company') + productCard('pass', 'company') + productCard('sponsor', 'company', pages) + '</div>', 'co', 'Your company') +
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
    return top + list + '<form class="acc-pan acc-form" id="claim" novalidate><p class="acc-lbl sm">Claim</p><h2 class="acc-h2">' + (S.claims.length ? 'Claim <b>another page</b>' : 'Claim <b>your page</b>') + '</h2>' +
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
      (team.members.length ? part('People on <b>the team</b>', '<div class="acc-list">' + team.members.map(function (m) { return '<div class="acc-row"><span class="acc-co" aria-hidden="true">' + esc(m.email.charAt(0).toUpperCase()) + '</span><div class="main"><strong>' + esc(m.email) + '</strong><span class="js">' +
        (m.has_account ? (m.confirmed ? m.live_jobs + plural(m.live_jobs, ' live job', ' live jobs') : 'has an account, email not confirmed yet') : 'no account yet: they sign up with this address') + '</span></div>' +
        '<div class="ctl"><button class="btn ghost sm" type="button" data-team-del="' + esc(m.email) + '">Remove</button></div></div>'; }).join('') + '</div>', 'members', team.members.length + plural(team.members.length, ' colleague', ' colleagues'))
        : empty('Nobody added yet.', ' You are the only one who posts for ' + esc(me.company || me.domain) + '. Add a colleague below: they post under the company’s name from their own account.', '', 'team')) +
      part('Add a <b>colleague</b>', '<form class="acc-inline flat" id="team-add" novalidate>' + field('Colleague’s work email', 'email', 'type="email" required placeholder="name@' + esc(me.domain) + '"') + err + '<button class="btn primary" type="submit">Add to the team</button></form>' +
        '<p class="note">They get a letter, sign up with that address and post from their own account. Their first jobs are read by a person, like anyone’s.</p>', 'add', 'Invite');
  }
  function findPanel() {
    if (!(pub.talent === 'on' && S.sent && me.posts_as.indexOf('employer') >= 0)) return '';
    return head('Find candidates', 'Find people in the <b>resume database</b>', 'People who chose to be found. You see no name or contacts until the person accepts your request, and you pay only for people who accept.') +
      '<form class="card acc-form" id="talent-search" novalidate><div class="acc-two">' + field('Words', 'q', 'type="text" placeholder="rust engineer"') + field('Skill', 'skill', 'type="text" placeholder="python"') +
      '<label class="fld"><span class="fld-l">Kind of work</span><select name="role"><option value="">Any</option>' + D.categories.map(function (c) { return '<option value="' + esc(c[0]) + '">' + esc(c[1]) + '</option>'; }).join('') + '</select></label>' +
      field('Place', 'place', 'type="text" placeholder="remote, germany"') + '</div>' +
      (pub.pay_links === 'on' ? '<label class="check"><input type="checkbox" name="seeking" value="open"> <span>Only people looking for work or open to offers</span></label>' : '') + err +
      '<p class="acc-btns"><button class="btn primary" type="submit">Search</button><span class="note">' + S.sent.credits + plural(S.sent.credits, ' contact request', ' contact requests') + ' left.</span></p></form><div id="talent-out"></div>' +
      (S.sent.requests.length ? part('Your <b>requests</b>', '<div class="acc-list">' + S.sent.requests.map(function (q) {
        var c = q.candidate; return '<div class="acc-row"><div class="main">' + state(q.status, ASKED[q.status]) + ' <strong>' + esc(c.headline || 'Candidate') + '</strong>' + (q.status === 'accepted' && c.contact ? '<span class="js"><strong>' + esc(c.contact.name) + '</strong>, <a href="mailto:' + esc(c.contact.email) + '">' + esc(c.contact.email) + '</a>' + (c.contact.phone ? ', ' + esc(c.contact.phone) : '') + '</span>' : '') + '<span class="js">sent ' + nice(q.sent) + '</span></div></div>';
      }).join('') + '</div>', 'sent', 'Sent') : '');
  }
  /* the payment link of one order, for whoever pays (the accountant): made on the first press (POST /api/orders/<id>/share), then copied
     or sent by email from here. The page behind it needs no account and shows the receipt once paid. */
  function shareBoxOf(o) {
    var url = o.share_key ? esc(D.site) + '/account/#invoice=' + esc(o.share_key) : '';
    return '<p class="acc-payl-t">' + icon('mail') + '<span><b>For your accountant, or whoever pays.</b> The link opens a page with what this payment is for, the price and the button to pay. No account needed; the receipt shows there once it is paid. It works for 30 days.</span></p>' +
      (url ? '<div class="acc-share-r"><input type="text" readonly value="' + url + '" aria-label="The payment link"><button class="btn sm" type="button" data-copy="' + url + '">Copy</button></div>' : '<p class="acc-btns"><button class="btn sm" type="button" data-share-make="' + esc(o.id) + '">Make the link</button></p>') +
      '<form class="acc-inline flat" data-share-mail="' + esc(o.id) + '" novalidate>' + field('Or send it by email', 'email', 'type="email" autocomplete="off" placeholder="accounts@yourcompany.com" required data-need="Enter the address of the person who pays."') +
      '<button class="btn ghost" type="submit">Send the link</button>' + err + '</form>';
  }
  function billingPanel() {
    var B = S.billing || {}, boosts = {}, credits = me.credits || (B.wallet && B.wallet.balance) || 0, passes = (B.passes || []).filter(function (p) { return p.live; });
    (B.boosts || []).forEach(function (b) { boosts[b.id] = b; });
    var top = head('Billing', 'Payments and <b>receipts</b>', 'Every payment is a single payment for a fixed time. Nothing renews.', S.orders.length || S.placements.length ? '<a class="btn ghost" href="#promote">See promotions</a>' : '');
    var have = (credits ? '<p class="acc-synced"><b>' + money(credits) + ' in credits.</b> ' + (B.wallet && B.wallet.next_expiry ? 'The first of them run out on ' + nice(B.wallet.next_expiry) + '. ' : '') + 'Use them on any promotion: “Pay from my credits”.</p>' : '') +
      passes.map(function (p) { return '<p class="acc-synced"><b>Hiring Pass for ' + esc(p.company) + '</b> until ' + nice(p.until) + ': ' + p.premium_left + plural(p.premium_left, ' Premium boost', ' Premium boosts') + ' left.</p>'; }).join('');
    if (!S.orders.length && !S.placements.length) return top + have + empty('No payments yet.', ' Posting jobs is free. When you promote a job, the payment and its receipt show here.', go('#promote', 'See promotions'), 'billing') + testNote();
    return top + have + testNote() +
      // rows, not tables: on a phone a table of seven columns is a strip to drag sideways
      (S.placements.length ? part('What is <b>running</b>', '<div class="acc-list">' + S.placements.map(function (p) {
        var b = boosts[p.id];
        return '<div class="acc-row"><div class="main">' + state(p.state) + ' <strong>' + esc(KIND[p.kind] || p.kind) + '</strong><span class="js">' + esc(p.label) + '</span><span class="js">' +
          (p.from && p.until ? nice(p.from) + ' to ' + nice(p.until) : p.days ? p.days + ' days, from the day the job is approved' : '') +
          (b ? ' · ' + b.views + plural(b.views, ' view', ' views') + ' · ' + b.applies + plural(b.applies, ' click on Apply', ' clicks on Apply') : '') + '</span></div></div>';
      }).join('') + '</div>', 'running', 'Promotions') : '') +
      (S.orders.length ? part('Every <b>payment</b>', '<div class="acc-list">' + S.orders.map(function (o) {
        return '<div class="acc-row"><div class="main">' + state(o.status) + ' <strong>' + esc(o.name) + '</strong><span class="js">' + (o.label && o.label !== o.name ? esc(o.label) + ' · ' : '') +
          (o.amount_usd ? money(o.amount_usd) + (o.coupon ? ' with ' + esc(o.coupon.code) + ' (full price ' + money(o.coupon.full_usd) + ')' : '') : o.credits ? o.credits + ' credits' : 'Included') + ' · ' + nice(o.created) + '</span></div><div class="ctl">' +
          (o.pay_url ? '<a class="btn sm" href="' + esc(o.pay_url) + '">Pay now</a>' + (o.can_share ? '<button class="btn ghost sm" type="button" data-share="' + esc(o.id) + '" aria-expanded="' + (shareOpen === o.id) + '">Send to whoever pays</button>'
            : '<button class="btn ghost sm" type="button" data-pay-copy="' + esc(o.pay_url) + '">Copy the link for whoever pays</button>') : '') +
          (o.status === 'paid' ? '<button class="btn ghost sm" type="button" data-receipt="' + esc(o.id) + '">Receipt</button>' : '') + '</div>' +
          (o.can_share ? '<div class="acc-payl" data-share-box="' + esc(o.id) + '"' + (shareOpen === o.id ? '' : ' hidden') + '>' + shareBoxOf(o) + '</div>' : '') + '</div>';
      }).join('') + '</div><div id="receipt-out"></div>', 'payments', 'History') : '');
  }

  /* ---------- settings: the address, the password, which side you use, your data, deleting the account ---------- */
  function settingsPanel() {
    var emp = ROLE === 'employer';
    // the password: changed here with the current one (server of 25 Nov 2026: me.has_password); before it, and without a password, by a link
    var pw = me.has_password ? '<div><dt>Password</dt><dd><span>Change it with your current one. Every other browser is then signed out, and we tell your address.</span>' +
        '<button class="btn ghost sm" type="button" id="pw-open" aria-expanded="false">Change the password</button><form id="pw-form" class="acc-dd-f" novalidate hidden>' +
        '<div class="acc-two">' + field('Current password', 'current', 'type="password" autocomplete="current-password" required data-need="Enter your current password."') +
        field('New password', 'password', 'type="password" autocomplete="new-password" required minlength="8"', 'At least 8 characters.') + '</div>' + err +
        '<p class="acc-btns"><button class="btn primary" type="submit">Save the new password</button><button class="linkbtn" type="button" id="acc-pass">Forgot it? Email me a link</button></p></form></dd></div>'
      : '<div><dt>Password</dt><dd><span>' + (me.has_password === false ? 'None yet: you sign in with Google or LinkedIn. To set one, we send a link to your email.' :
        'To change it, we send a link to your email. Opening it lets you choose a new password and signs out every browser.') + '</span><button class="btn ghost sm" type="button" id="acc-pass">Send me the link</button></dd></div>';
    var two = me.two_step === undefined ? '' : '<div><dt>Two-step sign-in</dt><dd><span>' + (me.two_step ? state('live', 'On') + ' A sign-in with your password also asks for a code we email to you.' :
        'Off. Switch it on, and a sign-in with your password also asks for a code we email to you: a stolen password alone is then not enough.') + '</span>' +
      (me.two_step ? '<button class="btn ghost sm" type="button" id="two-off-open" aria-expanded="false">Switch it off</button><form id="two-off" class="acc-dd-f" novalidate hidden>' +
        field('Your password, to switch it off', 'password', 'type="password" autocomplete="current-password" required data-need="Enter your current password."') + err +
        '<p class="acc-btns"><button class="btn ghost" type="submit">Switch two-step sign-in off</button></p></form>'
        : me.has_password && me.confirmed ? '<button class="btn sm" type="button" id="two-on">Switch it on</button>' : '') + '</dd></div>';
    return head('Settings', 'Your <b>account</b>', '') +
      part('Sign-in and <b>security</b>', '<dl class="acc-dl"><div><dt>Email</dt><dd><span>' + esc(me.email) + ' ' + (me.confirmed ? state('live', 'Confirmed') : state('review', 'Not confirmed')) + '</span>' +
        (me.confirmed ? '' : '<button class="btn ghost sm acc-confirm" type="button">Send the link again</button>') + '</dd></div>' + pw + two +
      (me.linkedin || pub.linkedin === 'on' ? '<div><dt>LinkedIn</dt><dd>' + (me.linkedin ? '<span>Connected' + (me.linkedin.name ? ' as ' + esc(me.linkedin.name) : '') + '</span>' : '<span>Not connected</span><button class="btn ghost sm li-start" type="button">Connect LinkedIn</button>') + '</dd></div>' : '') + '</dl>', 'security', 'Security') +
      part('How you <b>use it</b>', '<dl class="acc-dl"><div><dt>You use it as</dt><dd><span>' + (emp ? 'An employer: jobs, promotion, company page.' : 'A job seeker: resumes, saved jobs, alerts.') + '</span><button class="btn ghost sm" type="button" data-role-to="' + (emp ? 'seeker' : 'employer') + '">' + (emp ? 'Open the job seeker side' : 'Open the employer side') + '</button></dd></div>' +
      (me.domain ? '<div><dt>Company domain</dt><dd><span>' + esc(me.domain) + (me.company ? ' · ' + esc(me.company) : '') + '</span></dd></div>' : '') + '</dl>', 'use', 'Account') +
      part('Your <b>data</b>', '<p class="acc-sub">Download everything we keep about your account as one file. <a href="' + esc(D.site) + '/privacy/">What we keep and why</a></p>' +
        '<p class="acc-btns"><button class="btn ghost" type="button" id="me-export">Download my data</button></p>', 'data', 'Privacy') +
      part('Delete the <b>account</b>', '<form class="acc-danger" id="me-delete" novalidate><p>This removes your alerts, your resumes, your synced lists and everything you posted, at once and for good. It cannot be undone.</p>' +
        field('To go on, type: delete my account', 'confirm', 'type="text" autocomplete="off" required data-need="Type the words “delete my account” to go on."') + err +
        '<p class="acc-btns"><button class="btn ghost" type="submit">Delete my account for good</button></p></form>', 'delete', 'For good');
  }

  var TABS = { seeker: [['overview', 'Overview'], ['saved', 'Saved jobs'], ['resumes', 'Resumes'], ['visibility', 'Who sees you'], ['alerts', 'Job alerts'], ['settings', 'Settings']],
    employer: [['overview', 'Overview'], ['jobs', 'Your jobs'], ['post', 'Post a job'], ['promote', 'Promote'], ['credits', 'Credits'], ['company', 'Company page'], ['team', 'Team'], ['find', 'Find candidates'], ['billing', 'Billing'], ['settings', 'Settings']] };
  var TAB_ROLE = { saved: 'seeker', resumes: 'seeker', visibility: 'seeker', alerts: 'seeker', jobs: 'employer', post: 'employer', promote: 'employer', credits: 'employer', company: 'employer', team: 'employer', find: 'employer', billing: 'employer' };
  // older links and the links in our letters (#talent) name a block inside a part: open the part, then go to the block
  var ALIAS = { talent: 'visibility', views: 'visibility', sync: 'saved', myresumes: 'resumes', hiring: 'post', payments: 'billing', running: 'billing', data: 'settings', account: 'settings' };
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
    else { P.saved = savedPanel(); P.resumes = resumesPanel(); P.visibility = visibilityPanel(); P.alerts = alertsPanel(); }
    var nav = '', panels = '';
    TABS[ROLE].forEach(function (t) {
      if (!P[t[0]]) return;
      var n = t[0] === 'jobs' ? S.jobs.length : t[0] === 'alerts' ? S.alerts.length : t[0] === 'resumes' && S.resumes ? S.resumes.resumes.length :
        t[0] === 'visibility' ? (S.incoming || []).filter(function (q) { return q.status === 'sent'; }).length : 0;
      if (t[0] === 'credits' && creditsNow()) n = money(creditsNow());                    // the balance stands next to the word, so it is never a question where bought credits went
      nav += '<a href="#' + t[0] + '">' + icon(t[0]) + '<span>' + t[1] + '</span>' + (n ? '<i>' + n + '</i>' : '') + '</a>';
      panels += '<section class="acc-panel" data-tab="' + t[0] + '" hidden>' + P[t[0]] + '</section>';
    });
    var lit = !emp && pub.talent === 'on' && (me.seeking === 'active' || me.seeking === 'open');      // a green ring, as LinkedIn's "Open to work"
    root.innerHTML = '<div class="acc-shell"><aside class="acc-side"><div class="acc-me"><span class="acc-av' + (lit ? ' lit' : '') + '" aria-hidden="true">' + esc(me.email.charAt(0).toUpperCase()) + '</span><div><b>' + esc(me.email) + '</b><span>' +
      (emp ? esc(me.company || me.domain || 'Employer') : lit ? SEEKN[me.seeking] : 'Job seeker') + '</span></div></div><div class="acc-nav" role="navigation" aria-label="Your account">' + nav + '</div>' +
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
        if (btn && btn.getAttribute('data-for')) data.for_someone = true;
        return api('POST', '/api/orders', withPromo(data)).then(function (r) {
          if (data.for_someone && r.order.status === 'pending') {                        // a bill for the accountant: to Billing, with its link open
            shareOpen = r.order.id; flash('<b>The payment link for ' + esc(r.order.name) + ' is ready.</b> Copy it or send it by email below: whoever has it can pay, without an account.');
            location.hash = '#billing'; return load();
          }
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
      var qs = Object.keys(v).filter(function (k) { return v[k]; }).map(function (k) { return k + '=' + encodeURIComponent(v[k] === true ? 'open' : v[k]); }).join('&');
      return api('GET', '/api/talent/search?' + qs).then(function (r) {
        var out = document.getElementById('talent-out'), opens = r.views === 'on';
        out.innerHTML = (r.total ? '<p class="acc-quiet"><b>' + r.total + ' found.</b>' + (opens ? ' Opening a resume tells the person that your company looked, as on hh.ru and LinkedIn; your name and contacts stay yours.' : '') + '</p>'
          : empty('Nobody found for this search.', ' Try fewer words, or leave the place empty.', '', 'find')) + r.results.map(function (c) {
          return '<div class="acc-pan acc-cand">' + cvCard(c, !opens) + (opens ? '<p class="acc-btns"><button class="btn ghost sm" type="button" data-open-cv="' + esc(c.id) + '">Open the resume</button></p>' : askForm(c.id)) + '</div>';
        }).join('');
        wireAsk(out);
        Array.prototype.forEach.call(out.querySelectorAll('[data-open-cv]'), function (b) {
          b.addEventListener('click', function () {
            b.disabled = true;
            api('GET', '/api/talent/' + b.getAttribute('data-open-cv')).then(function (x) {
              var box = b.closest('.acc-cand');
              box.innerHTML = cvCard(x.candidate, true) + (x.asked ? '<p class="acc-quiet">You asked this person already: ' + state(x.asked, ASKED[x.asked]) + '</p>' : askForm(x.candidate.id));
              wireAsk(box);
            }, function (e) { b.disabled = false; fail(e); });
          });
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

    /* pass of 25 Nov 2026: the status, who sees the resume, the companies it is hidden from, payment links, the password, two-step sign-in */
    on('[data-seek]', function (b) {
      var v = b.getAttribute('aria-pressed') === 'true' ? '' : b.getAttribute('data-seek');
      Array.prototype.forEach.call(root.querySelectorAll('[data-seek]'), function (x) { x.disabled = true; });
      api('PATCH', '/api/me', { seeking: v }).then(function (r) {
        me = r.user; flash(v ? '<b>Your status: ' + SEEKN[v] + '.</b> ' + (S.talent && S.talent.profile ? 'Employers who search the resume database see it on your resume.' : 'Employers see it once you let them find your resume.') : 'Your status is hidden.'); draw();
      }, function (e) { Array.prototype.forEach.call(root.querySelectorAll('[data-seek]'), function (x) { x.disabled = false; }); fail(e); });
    });
    Array.prototype.forEach.call(root.querySelectorAll('.acc-opts input[name=vis]'), function (r) {
      r.addEventListener('change', function () {
        var v = r.value, data = v === 'none' ? { paused: true } : { paused: false, visibility: v };
        Array.prototype.forEach.call(root.querySelectorAll('.acc-opts input'), function (x) { x.disabled = true; });
        api('PUT', '/api/talent/profile', data).then(function () {
          flash(v === 'none' ? '<b>Paused.</b> Nobody finds your resume now; it is kept, and its link shows nothing.' : v === 'link' ? '<b>Only by its link now.</b> It left search; copy the link below and send it to the employers you choose.' : '<b>In search again.</b> Employers who search find your resume, without your name or contacts.');
          return load();
        }, fail);
      });
    });
    on('[data-copy]', function (b) {
      var text = b.getAttribute('data-copy'), was = b.textContent, done = function () { b.textContent = 'Copied'; setTimeout(function () { b.textContent = was; }, 1800); };
      var inp = b.parentNode.querySelector('input'); if (inp) { try { inp.select(); } catch (e) {} }
      if (navigator.clipboard) navigator.clipboard.writeText(text).then(done, function () {}); else done();
    });
    on('#cv-new', function (b) {
      H.sure(b, 'Make a new link? The old one stops working at once: whoever has it sees nothing.', 'Make a new link').then(function (ok) {
        if (ok) api('PUT', '/api/talent/profile', { new_link: true }).then(function () { flash('<b>A new link is ready.</b> The old one shows nothing any more.'); return load(); }, fail);
      });
    });
    var blockList = function () { return (S.talent && S.talent.profile && S.talent.profile.blocked) || []; };
    submit(document.getElementById('block-add'), function (v) {
      var d = String(v.blocked || '').trim().toLowerCase().replace(/^[a-z]+:\/\//, '').replace(/^[^@]*@/, '').replace(/[\/?#].*$/, '').replace(/^www\./, '');
      if (!/^[a-z0-9-]+(\.[a-z0-9-]+)+$/.test(d)) throw oops('blocked', 'Enter the company’s web address, like initech.com.');
      if (blockList().indexOf(d) >= 0) throw oops('blocked', d + ' is on the list already.');
      return api('PUT', '/api/talent/profile', { blocked: blockList().concat([d]) }).then(function (r) {
        var got = r.profile && r.profile.blocked || [];
        flash(got.indexOf(d) >= 0 || got.some(function (x) { return d.slice(-x.length - 1) === '.' + x; }) ? '<b>Hidden from ' + esc(d) + '.</b> No account on that address sees your resume, in search or by its link.' : 'Saved.');
        return load();
      });
    });
    on('[data-unblock]', function (b) {
      var d = b.getAttribute('data-unblock'); b.disabled = true;
      api('PUT', '/api/talent/profile', { blocked: blockList().filter(function (x) { return x !== d; }) }).then(function () { flash(esc(d) + ' can find your resume again.'); return load(); }, function (e) { b.disabled = false; fail(e); });
    });
    on('[data-share]', function (b) {
      var box = root.querySelector('[data-share-box="' + b.getAttribute('data-share') + '"]'); if (!box) return;
      box.hidden = !box.hidden; b.setAttribute('aria-expanded', String(!box.hidden)); shareOpen = box.hidden ? '' : b.getAttribute('data-share');
      if (!box.hidden && !box.querySelector('input[readonly]')) { var mk = box.querySelector('[data-share-make]'); if (mk) mk.click(); }
    });
    on('[data-share-make]', function (b) {
      b.disabled = true;
      api('POST', '/api/orders/' + b.getAttribute('data-share-make') + '/share', {}).then(function () { shareOpen = b.getAttribute('data-share-make'); return load(); }, function (e) { b.disabled = false; fail(e); });
    });
    Array.prototype.forEach.call(root.querySelectorAll('form[data-share-mail]'), function (f) {
      submit(f, function (v) {
        return api('POST', '/api/orders/' + f.getAttribute('data-share-mail') + '/share', { email: v.email }).then(function (r) {
          shareOpen = f.getAttribute('data-share-mail'); flash('<b>The payment link is on its way to ' + esc(r.sent_to) + '.</b> Whoever opens it can pay without an account; the payment shows here when it is confirmed.'); return load();
        });
      });
    });
    if (shareOpen && location.hash === '#billing') { var sb = root.querySelector('[data-share-box="' + shareOpen + '"]'); if (sb) setTimeout(function () { sb.scrollIntoView({ block: 'center' }); }, 60); }
    on('#pw-open', function (b) { var f = document.getElementById('pw-form'); f.hidden = !f.hidden; b.setAttribute('aria-expanded', String(!f.hidden)); if (!f.hidden) { try { f.elements.current.focus(); } catch (e) {} } });
    submit(document.getElementById('pw-form'), function (v) {
      return api('POST', '/api/auth/password', { current: v.current, password: v.password }).then(function (r) {
        var f = document.getElementById('pw-form'); f.reset(); f.hidden = true; say('<b>' + esc(r.message || 'Your new password is saved.') + '</b>');
      });
    });
    on('#two-on', function (b) {
      b.disabled = true;
      api('PUT', '/api/me/security', { two_step: true }).then(function (r) { me = r.user; flash('<b>Two-step sign-in is on.</b> Next time you sign in with your password, we also email you a code.'); draw(); }, function (e) { b.disabled = false; fail(e); });
    });
    on('#two-off-open', function (b) { var f = document.getElementById('two-off'); f.hidden = !f.hidden; b.setAttribute('aria-expanded', String(!f.hidden)); if (!f.hidden) { try { f.elements.password.focus(); } catch (e) {} } });
    submit(document.getElementById('two-off'), function (v) {
      return api('PUT', '/api/me/security', { two_step: false, password: v.password }).then(function (r) { me = r.user; flash('Two-step sign-in is off: the password alone signs in. We told your address.'); draw(); });
    });
  }
  // the form that asks a person in the resume database to get in touch (search results, an opened resume, a resume shared by its link)
  function askForm(id) {
    return '<form class="talent-ask" data-id="' + esc(id) + '" novalidate><label class="fld"><span class="fld-l">Your message</span><textarea name="message" rows="3" maxlength="1000" required data-need="Write a few words: who you are, the job, and why them." placeholder="Who you are, the job, and why them."></textarea></label>' +
      field('Link to the job (optional)', 'job_url', 'type="url" placeholder="https://"') + err + '<p class="acc-btns"><button class="btn primary sm" type="submit">Ask to contact</button><span class="note">They get your company’s name and message; you get their contacts if they accept.</span></p></form>';
  }
  function wireAsk(box) {
    Array.prototype.forEach.call(box.querySelectorAll('form.talent-ask'), function (f) {
      submit(f, function (x) { return api('POST', '/api/talent/' + f.getAttribute('data-id') + '/contact', x).then(function () { f.innerHTML = '<p class="acc-quiet"><b>Sent.</b> You get their name and contacts if they accept.</p>'; }); });
    });
  }
  // a page of its own, without the menu: a payment link or a shared resume that did not open, and the like
  function gateMsg(label, title, text, action) {
    return '<div class="acc-gate one"><div class="card acc-auth"><p class="acc-lbl"><i></i>' + label + '</p><h1 class="acc-t sm">' + title + '</h1><p class="acc-sub">' + esc(text) + '</p>' + (action ? '<p class="acc-btns">' + action + '</p>' : '') + '</div></div>';
  }
  /* A payment link for someone else (#invoice=<key>; PLAN_RU.md part 2, item 9): what it is for, the price, the button to the checkout,
     a new checkout when the last one ran out, and the receipt once paid. No account and no sign-in: the key is the permission. */
  var invTries = 0;
  function drawInvoice(key, again) {
    if (hd) hd.hidden = true;
    if (!again) { root.innerHTML = waiting; invTries = 0; }
    return api('GET', '/api/invoice/' + key).then(function (r) { paintInvoice(key, r.invoice); }, function (e) {
      root.innerHTML = gateMsg('Payment', 'This link <b>does not work</b>', e.message, '<a class="btn ghost" href="' + esc(D.site) + '/">Go to the home page</a>');
    });
  }
  function paintInvoice(key, x) {
    var st = { pending: ['pending', 'Waiting for payment'], checking: ['review', 'Being checked'], expired: ['review', 'Payment page ran out'], underpaid: ['rejected', 'Underpaid'], paid: ['paid', 'Paid'] }[x.status] || ['review', x.status];
    var plan = (D.plans || {})[x.item], paid = x.status === 'paid';
    var rows = [['Item', esc(x.item) + (x.label ? '<span>' + esc(x.label) + '</span>' : '')], ['For', esc(x.company) + (x.domain && x.domain !== x.company ? ' · ' + esc(x.domain) : '')], ['Asked by', esc(x.asked_by)],
      ['Period', x.days ? x.days + ' days. One payment; nothing renews' : x.credits ? x.credits + ' credits, valid for 12 months' : 'One payment'], [paid ? 'Receipt number' : 'Number', esc(x.number)],
      [paid ? 'Paid' : 'Date', paid ? nice(x.paid) + ', with ' + esc(x.paid_with) : nice(x.created)]];
    var act = x.status === 'pending' ? '<a class="btn primary lg acc-go" href="' + esc(x.pay_url) + '">Pay ' + money(x.amount_usd) + ' in crypto<span class="acc-arr">' + icon('arrow') + '</span></a><p class="note">The checkout is Cryptomus. It stays open for an hour; after that this page makes a new one at the same price.</p>'
      : x.status === 'expired' && x.renewable ? '<button class="btn primary lg" type="button" id="inv-renew">Open a new payment page</button><p class="note">The last payment page was open for an hour and ran out unpaid. The price stays the same.</p>'
      : x.status === 'expired' ? '<p class="acc-quiet">This payment link has run out. Ask ' + esc(x.asked_by || 'whoever sent it') + ' for a new one.</p>'
      : x.status === 'checking' ? '<p class="acc-quiet"><b>We are asking the payment service about the last payment page.</b> If it was paid, this page says so within minutes; if not, a new one can be opened.</p><p class="acc-btns"><button class="btn ghost" type="button" id="inv-check">Check again</button></p>'
      : x.status === 'underpaid' ? '<p class="acc-quiet">Less than the price arrived, so nothing was switched on. Write to us from the contact page with the number above.</p>'
      : '<div class="acc-paid">' + icon('check') + '<p><b>Paid. Thank you.</b> ' + esc(x.note) + '</p></div><p class="acc-btns"><button class="btn ghost sm" type="button" id="inv-print">Print the receipt</button></p>';
    root.innerHTML = '<div class="acc-inv"><div class="acc-inv-c"><p class="acc-lbl"><i></i>' + (paid ? 'Receipt' : 'Payment request') + '</p>' +
      '<h1 class="acc-t sm">' + (paid ? 'Paid: <b>' + esc(x.item) + '</b>' : esc(x.company || 'An employer') + ' asks you to pay for <b>' + esc(x.item) + '</b>') + '</h1>' +
      '<div class="acc-inv-amt"><b>' + money(x.amount_usd) + (x.coupon ? ' <s>' + money(x.coupon.full_usd) + '</s>' : '') + '</b>' + state(st[0], st[1]) + '</div>' +
      '<dl class="acc-inv-dl">' + rows.filter(function (r) { return r[1]; }).map(function (r) { return '<div><dt>' + r[0] + '</dt><dd>' + r[1] + '</dd></div>'; }).join('') + '</dl>' +
      (plan && !paid ? '<p class="fld-l">What it includes</p><ul class="pc-inc">' + plan[0].map(function (y) { return '<li>' + esc(y) + '</li>'; }).join('') + '</ul>' : '') +
      '<div class="acc-inv-act">' + act + '</div><p class="acc-inv-f">' + icon('shield') + '<span>Sold by ' + esc(x.seller) + '. You need no account here, and no card or wallet is kept.</span></p></div></div>';
    var rn = document.getElementById('inv-renew');
    if (rn) rn.addEventListener('click', function () { rn.disabled = true; rn.textContent = 'One moment…'; api('POST', '/api/invoice/' + key + '/renew').then(function (r) { paintInvoice(key, r.invoice); }, function (e) { rn.disabled = false; rn.textContent = 'Open a new payment page'; say(esc(e.message), true); paintInvoice(key, x); }); });
    var ck = document.getElementById('inv-check'); if (ck) ck.addEventListener('click', function () { ck.disabled = true; drawInvoice(key, true); });
    var pr = document.getElementById('inv-print'); if (pr) pr.addEventListener('click', function () { window.print(); });
    // back from the checkout, the confirmation can take a minute: the page looks again by itself for a while
    if ((x.status === 'pending' || x.status === 'checking') && invTries++ < 40) setTimeout(function () { if (location.hash === '#invoice=' + key && !document.hidden) drawInvoice(key, true); }, 15000);
  }
  /* A resume shared "only by link" (#cv=<key>): as employers see it, without the name or contacts. A company account may ask the person
     to get in touch from here; a visitor who is not signed in is offered the employer sign-in, and comes back here after it. */
  var afterAuth = '';
  function drawCv(key) {
    if (hd) hd.hidden = true;
    root.innerHTML = waiting;
    return api('GET', '/api/cv/' + key).then(function (r) {
      var c = r.candidate, act;
      if (r.own) act = callout('<b>This is your resume as people with its link see it:</b> without your name, email, phone or links.', '<a class="btn ghost sm" href="#visibility">Who sees you</a>', 'soft');
      else if (r.can_contact) act = r.asked ? '<p class="acc-quiet">You asked this person already: ' + state(r.asked, ASKED[r.asked]) + '</p>' : part('Ask them to <b>get in touch</b>', askForm(c.id), 'ask', r.credits + plural(r.credits, ' contact request left', ' contact requests left'));
      else if (r.signed_in) act = callout('Only an employer whose account is tied to its company’s address can ask this person to get in touch.', '<a class="btn ghost sm" href="#hiring">Tie my account to my company</a>', 'soft');
      else act = callout('<b>Hiring?</b> Sign in with your company account to ask this person to get in touch. They see your company and your message, and you get their contacts if they accept.', '<button class="btn sm" type="button" id="cv-signin">Sign in as an employer</button>', 'soft');
      root.innerHTML = '<div class="acc-cvp">' + head('Shared resume', 'A resume: <b>' + esc(c.headline || 'candidate') + '</b>', 'Shared through Jobs Every Hour by the person it belongs to. Their name and contact details stay hidden until they accept a request.') +
        '<div class="acc-pan">' + cvCard(c, true) + '</div>' + act + '</div>';
      wireAsk(root);
      var si = document.getElementById('cv-signin');
      if (si) si.addEventListener('click', function () { afterAuth = '#cv=' + key; setRole('employer'); cleanUrl(); drawAuth('in'); window.scrollTo(0, 0); });
    }, function (e) {
      root.innerHTML = gateMsg('Shared resume', 'This resume is <b>not shared any more</b>', e.message, '<a class="btn ghost" href="' + esc(D.site) + '/jobs/">Search jobs</a>');
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
    if ((m = /^#invoice=([a-f0-9]{32})$/.exec(hash))) return drawInvoice(m[1]);
    if ((m = /^#cv=([a-f0-9]{32})$/.exec(hash))) return drawCv(m[1]);
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
    if (/^#(confirm|reset|work|signin|invoice|cv)=/.test(location.hash)) return start();      // a link from a letter opened in a tab where the account is open already
    if (root.querySelector('.acc-inv, .acc-cvp')) return start();                              // from a payment page or a shared resume to a part of the account
    if (!me || !root.querySelector('.acc-shell')) return;
    if (Date.now() - saidAt > 1500) { var box = document.getElementById('acc-say'); if (box) box.innerHTML = ''; }
    showTab(); if (!ALIAS[location.hash.slice(1)]) toTop();
  });
  /* One H1 on every screen (26 Nov 2026). The page's own heading (#acc-hd, read without JavaScript) goes once a screen draws its own; in
     the signed-in account every part carries its headline, so only the open part's is the H1 and the hidden parts keep theirs as H2.
     Watched here, so every way a screen is drawn or a part is opened keeps to it; while the account loads the hidden page heading stays. */
  function oneH1() {
    var hs = root.querySelectorAll('h1.acc-t, h2.acc-t');
    if (!hs.length) return;
    if (hd && hd.parentNode) hd.parentNode.removeChild(hd);
    hd = null;
    var lead = null;
    Array.prototype.forEach.call(hs, function (h) { if (!lead && !h.closest('[hidden]')) lead = h; });
    if (!lead) lead = hs[0];
    Array.prototype.forEach.call(hs, function (h) {
      var want = h === lead ? 'H1' : 'H2';
      if (h.tagName === want) return;
      var n = document.createElement(want);
      Array.prototype.forEach.call(h.attributes, function (a) { n.setAttribute(a.name, a.value); });
      while (h.firstChild) n.appendChild(h.firstChild);
      h.parentNode.replaceChild(n, h);
    });
  }
  if (window.MutationObserver) new MutationObserver(oneH1).observe(root, { childList: true, subtree: true, attributes: true, attributeFilter: ['hidden'] });
  var waiting = '<div class="acc-wait"><p class="note">Loading your account…</p></div>';
  if (hd) hd.hidden = true;
  root.innerHTML = waiting;
  api('GET', '/api/public/products').then(setPub, function () {}).then(start);
})();
