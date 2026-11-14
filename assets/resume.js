/* Resume builder: everything stays in this browser (localStorage). "Download PDF" uses the browser's print dialog. */
(function () {
  var root = document.getElementById('rb'); if (!root) return;
  var H = window.HRN, esc = H.esc, $ = function (id) { return document.getElementById(id); };
  var blank = { name: '', title: '', email: '', phone: '', place: '', links: '', summary: '', skills: '', exp: [{ role: '', org: '', dates: '', text: '' }], edu: [{ what: '', org: '', dates: '' }] };
  var data = H.get('hrn_resume', null);
  if (!data || typeof data !== 'object' || Array.isArray(data)) data = {};          // a damaged or foreign value must not break the builder
  Object.keys(blank).forEach(function (k) { if (Array.isArray(blank[k]) ? !Array.isArray(data[k]) || !data[k].length : typeof data[k] !== 'string') data[k] = JSON.parse(JSON.stringify(blank[k])); });
  var TPLS = ['classic', 'modern', 'compact', 'developer', 'executive'];
  if (TPLS.indexOf(data.tpl) < 0) data.tpl = 'classic';
  var applyTpl = function () { var pv = $('rb-preview'), sel = $('rb-tpl'); pv.className = 'tpl-' + data.tpl; if (sel) sel.value = data.tpl; };
  var save = function () { H.set('hrn_resume', data); };
  var field = function (label, key, type, ph) {
    return '<label class="rl">' + label + (type === 'area' ? '<textarea data-k="' + key + '" rows="4" placeholder="' + ph + '">' + esc(data[key]) + '</textarea>'
      : '<input type="text" data-k="' + key + '" placeholder="' + ph + '" value="' + esc(data[key]) + '">') + '</label>';
  };
  var drawForm = function () {
    var exp = data.exp.map(function (x, i) {
      return '<div class="rblock" data-list="exp" data-i="' + i + '"><div class="rrow"><input type="text" data-f="role" placeholder="Job title" value="' + esc(x.role) + '">' +
        '<input type="text" data-f="org" placeholder="Company" value="' + esc(x.org) + '"><input type="text" data-f="dates" placeholder="2022 – now" value="' + esc(x.dates) + '"></div>' +
        '<textarea data-f="text" rows="4" placeholder="One achievement per line. Start with a verb, add a number where you can.">' + esc(x.text) + '</textarea>' +
        '<button class="linkbtn" type="button" data-del="exp">Remove this job</button></div>';
    }).join('');
    var edu = data.edu.map(function (x, i) {
      return '<div class="rblock" data-list="edu" data-i="' + i + '"><div class="rrow"><input type="text" data-f="what" placeholder="Degree or course" value="' + esc(x.what) + '">' +
        '<input type="text" data-f="org" placeholder="School" value="' + esc(x.org) + '"><input type="text" data-f="dates" placeholder="2018 – 2022" value="' + esc(x.dates) + '"></div>' +
        '<button class="linkbtn" type="button" data-del="edu">Remove</button></div>';
    }).join('');
    $('rb-form').innerHTML =
      '<span class="flabel">About you</span>' + field('Full name', 'name', 'text', 'Alex Morgan') + field('Headline', 'title', 'text', 'Senior Backend Engineer') +
      '<div class="rrow">' + field('Email', 'email', 'text', 'you@example.com') + field('Phone', 'phone', 'text', '+1 555 010 0199') + '</div>' +
      '<div class="rrow">' + field('Location', 'place', 'text', 'Berlin, Germany · open to remote') + field('Links', 'links', 'text', 'github.com/you, linkedin.com/in/you') + '</div>' +
      field('Summary', 'summary', 'area', 'Two or three sentences: what you do, for how long, and what you are best at.') +
      '<span class="flabel">Experience</span>' + exp + '<p><button class="btn ghost sm" type="button" data-add="exp">+ Add a job</button></p>' +
      '<span class="flabel">Education</span>' + edu + '<p><button class="btn ghost sm" type="button" data-add="edu">+ Add education</button></p>' +
      '<span class="flabel">Skills</span>' + field('Comma-separated', 'skills', 'text', 'Python, PostgreSQL, AWS, Kubernetes');
  };
  var drawPreview = function () {
    var contact = [data.email, data.phone, data.place].concat(String(data.links || '').split(',').map(function (s) { return s.trim(); })).filter(Boolean).map(esc).join(' · ');
    var exp = data.exp.filter(function (x) { return x.role || x.org || x.text; }).map(function (x) {
      var lines = String(x.text || '').split('\n').map(function (l) { return l.replace(/^[-•*\s]+/, '').trim(); }).filter(Boolean);
      return '<div class="pv-item"><div class="pv-top"><strong>' + esc(x.role) + (x.org ? ', ' + esc(x.org) : '') + '</strong><span>' + esc(x.dates) + '</span></div>' +
        (lines.length ? '<ul>' + lines.map(function (l) { return '<li>' + esc(l) + '</li>'; }).join('') + '</ul>' : '') + '</div>';
    }).join('');
    var edu = data.edu.filter(function (x) { return x.what || x.org; }).map(function (x) {
      return '<div class="pv-item"><div class="pv-top"><strong>' + esc(x.what) + (x.org ? ', ' + esc(x.org) : '') + '</strong><span>' + esc(x.dates) + '</span></div></div>';
    }).join('');
    var skills = String(data.skills || '').split(',').map(function (s) { return s.trim(); }).filter(Boolean);
    $('rb-preview').innerHTML = (data.name || data.title || contact || exp || edu || skills.length)
      ? '<h2 class="pv-name">' + esc(data.name || 'Your name') + '</h2>' + (data.title ? '<p class="pv-title">' + esc(data.title) + '</p>' : '') +
        (contact ? '<p class="pv-contact">' + contact + '</p>' : '') + (data.summary ? '<h3>Summary</h3><p>' + esc(data.summary) + '</p>' : '') +
        (exp ? '<h3>Experience</h3>' + exp : '') + (edu ? '<h3>Education</h3>' + edu : '') + (skills.length ? '<h3>Skills</h3><p>' + skills.map(esc).join(' · ') + '</p>' : '')
      : '<p class="pane-empty">Start typing on the left. Your resume appears here.</p>';
    applyTpl();
  };
  // a Word file: the same page as simple HTML, which Word opens and saves as .docx
  // The same resume in the open JSON Resume format (jsonresume.org): a file other tools and AI assistants can read
  var jsonFile = function () {
    var links = String(data.links || '').split(',').map(function (x) { return x.trim(); }).filter(Boolean);
    var url = function (x) { return /^https?:\/\//i.test(x) ? x : 'https://' + x; };
    var out = {
      $schema: 'https://raw.githubusercontent.com/jsonresume/resume-schema/v1.0.0/schema.json',
      basics: { name: data.name || '', label: data.title || '', email: data.email || '', phone: data.phone || '', summary: data.summary || '',
        location: { address: data.place || '' }, profiles: links.map(function (x) { return { network: x.replace(/^https?:\/\//i, '').split('/')[0], url: url(x) }; }) },
      work: data.exp.filter(function (x) { return x.role || x.org || x.text; }).map(function (x) {
        return { name: x.org || '', position: x.role || '', summary: x.dates || '', highlights: String(x.text || '').split('\n').map(function (l) { return l.replace(/^\s*[-*•]\s*/, '').trim(); }).filter(Boolean) };
      }),
      education: data.edu.filter(function (x) { return x.what || x.org; }).map(function (x) { return { institution: x.org || '', area: x.what || '', studyType: '', endDate: x.dates || '' }; }),
      skills: String(data.skills || '').split(',').map(function (x) { return x.trim(); }).filter(Boolean).map(function (x) { return { name: x }; })
    };
    var a = document.createElement('a');
    a.href = URL.createObjectURL(new Blob([JSON.stringify(out, null, 2)], { type: 'application/json' }));
    a.download = (data.name ? data.name.replace(/[^A-Za-z0-9]+/g, '-').replace(/^-|-$/g, '') : 'resume') + '.json';
    document.body.appendChild(a); a.click(); a.remove(); setTimeout(function () { URL.revokeObjectURL(a.href); }, 2000);
  };
  var wordFile = function () {
    var css = 'body{font-family:' + (data.tpl === 'classic' ? 'Georgia,serif' : data.tpl === 'developer' ? 'Consolas,monospace' : 'Arial,sans-serif') + ';font-size:11pt;line-height:1.4;color:#111}' +
      'h2{font-size:20pt;margin:0}h3{font-size:10pt;text-transform:uppercase;letter-spacing:1pt;border-bottom:1px solid #111;margin:14pt 0 6pt}p{margin:0 0 5pt}ul{margin:3pt 0 0}.pv-top span{color:#555}';
    var html = '<html xmlns:o="urn:schemas-microsoft-com:office:office" xmlns:w="urn:schemas-microsoft-com:office:word"><head><meta charset="utf-8"><title>Resume</title><style>' + css + '</style></head><body>' +
      $('rb-preview').innerHTML.replace(/<div class="pv-top"><strong>(.*?)<\/strong><span>(.*?)<\/span><\/div>/g, '<p><strong>$1</strong> &nbsp; <span>$2</span></p>') + '</body></html>';
    var a = document.createElement('a');
    a.href = URL.createObjectURL(new Blob(['\ufeff' + html], { type: 'application/msword' }));
    a.download = (data.name ? data.name.replace(/[^\w\- ]+/g, '').trim().replace(/\s+/g, '-') + '-' : '') + 'resume.doc';
    document.body.appendChild(a); a.click(); a.remove();
  };
  root.addEventListener('change', function (ev) { if (ev.target.id === 'rb-tpl') { data.tpl = ev.target.value; save(); applyTpl(); } });
  root.addEventListener('input', function (ev) {
    var t = ev.target, blk = t.closest('.rblock');
    if (blk && t.getAttribute('data-f')) data[blk.getAttribute('data-list')][Number(blk.getAttribute('data-i'))][t.getAttribute('data-f')] = t.value;
    else if (t.getAttribute('data-k')) data[t.getAttribute('data-k')] = t.value;
    else return;
    save(); drawPreview();
  });
  root.addEventListener('click', function (ev) {
    var t = ev.target, add = t.getAttribute('data-add'), del = t.getAttribute('data-del');
    if (add) { data[add].push(add === 'exp' ? { role: '', org: '', dates: '', text: '' } : { what: '', org: '', dates: '' }); save(); drawForm(); drawPreview(); }
    else if (del) { data[del].splice(Number(t.closest('.rblock').getAttribute('data-i')), 1); if (!data[del].length) data[del] = JSON.parse(JSON.stringify(blank[del])); save(); drawForm(); drawPreview(); }
    else if (t.id === 'rb-print') window.print();
    else if (t.id === 'rb-doc') wordFile();
    else if (t.id === 'rb-json') jsonFile();
    else if (t.id === 'rb-clear') { if (confirm('Erase this resume from this browser?')) { data = JSON.parse(JSON.stringify(blank)); save(); drawForm(); drawPreview(); } }
    else if (t.id === 'rb-match') {
      var text = [data.title, data.summary, data.skills].concat(data.exp.map(function (x) { return x.role + ' ' + x.text; })).join('\n');
      t.textContent = 'Matching…';
      fetch(H.base + '/data/skills.json').then(function (r) { return r.json(); }).then(function (pats) {
        var prof = H.get('hrn_profile', { skills: [], lvl: '', cat: '', sal: 0, remote: false });
        pats.forEach(function (p) { try { if (new RegExp(p[1], 'i').test(text) && prof.skills.indexOf(p[0]) < 0) prof.skills.push(p[0]); } catch (e) {} });
        H.set('hrn_profile', prof); location.href = H.base + '/for-you/';
      }).catch(function () { location.href = H.base + '/for-you/'; });
    }
  });
  drawForm(); drawPreview();

  /* Score and target job, as resume builders like Rezi do it, but in the browser: the review of /tools/resume-review/ gives a score
     out of 10 with the first fixes, and a pasted posting (or ?job=<slug> from a job page here) gives the match and the missing
     skills, each one button away from the skills line. The same checks as the tools, so the numbers agree. */
  var chk = $('rb-check'), jd = H.get('hrn_rb_target', ''), jdTitle = '', skillPats = null, ctimer;
  var asText = function () {
    var L = [data.name, data.title, [data.email, data.phone, data.place, data.links].filter(Boolean).join(' · '), ''];
    if (data.summary) L.push('Summary', data.summary, '');
    if (data.skills) L.push('Skills', data.skills, '');
    var ex = data.exp.filter(function (x) { return x.role || x.org || x.text; });
    if (ex.length) {
      L.push('Experience');
      ex.forEach(function (x) {
        L.push([x.role, x.org].filter(Boolean).join(', ') + (x.dates ? ' ' + x.dates : ''));
        String(x.text || '').split('\n').forEach(function (l) { l = l.replace(/^[-•*\s]+/, '').trim(); if (l) L.push('- ' + l); });
      });
      L.push('');
    }
    var ed = data.edu.filter(function (x) { return x.what || x.org; });
    if (ed.length) { L.push('Education'); ed.forEach(function (x) { L.push([x.what, x.org, x.dates].filter(Boolean).join(', ')); }); }
    return L.join('\n');
  };
  var drawCheck = function () {
    var T = window.HRNT;
    if (!chk || !T) return;
    var text = asText(), r = T.resumeReview(text), html = '<div class="rbc-score">';
    if (r.error) html += '<p class="rbc-h"><b>Score</b> after 80 words</p><p class="note">You have ' + r.words + ' so far. Add your jobs with one result each, and the score appears here.</p>';
    else {
      html += '<p class="rbc-h"><b>' + (Math.round(r.score * 10) / 10) + '</b><small>/10</small> ' + esc(r.verdict) + '</p>'
        + (r.fixes.length ? '<ol class="rbc-fix">' + r.fixes.slice(0, 3).map(function (f) { return '<li><b>' + esc(f.t) + '</b> ' + esc(f.d || '') + '</li>'; }).join('') + '</ol>' : '<p class="note">Nothing important to fix.</p>');
    }
    html += '<p class="note"><a href="' + H.base + '/tools/resume-review/">The full review</a> lists every check.</p></div><div class="rbc-target">';
    // a skill written in the skills line counts as the resume's, even where the posting's pattern needs context ("advanced Excel")
    var listed = {}; String(data.skills || '').split(',').forEach(function (x) { x = x.trim().toLowerCase(); if (x) listed[x] = 1; });
    var pats2 = skillPats && skillPats.map(function (p) { return listed[p[0].toLowerCase()] ? [p[0], new RegExp(p[0].replace(/[.*+?^${}()|[\]\\]/g, '\\$&').replace(/^(\w)/, '\\b$1').replace(/(\w)$/, '$1\\b') + '|' + p[1].source, 'i')] : p; });
    var m = jd && pats2 ? T.matchResume(text, jd, pats2, jdTitle) : null;
    if (!jd) html += '<p class="rbc-h"><b>Target job</b></p><p class="note">Paste the posting you are applying for: you will see how well this resume matches it and which of its skills are missing.</p>';
    else if (!m) html += '<p class="rbc-h"><b>Target job</b></p><p class="note">Reading the skills list…</p>';
    else if (m.error) html += '<p class="rbc-h"><b>Target job</b></p><p class="note">' + (m.error === 'resume' ? 'Write at least 30 words of resume to compare.' : m.error === 'jd' ? 'Paste the whole posting: at least 30 words.' : 'The posting names too few skills or repeated terms to compare.') + '</p>';
    else {
      html += '<p class="rbc-h"><b>' + m.score + '%</b> ' + esc(m.label) + (jdTitle ? ' · ' + esc(jdTitle) : '') + '</p>'
        + (m.missing.length ? '<p class="note">Skills the posting names and this resume does not. Add only the ones you have:</p><p class="rbc-add">' + m.missing.slice(0, 12).map(function (s) { return '<button class="chipbtn" type="button" data-addskill="' + esc(s) + '">+ ' + esc(s) + '</button>'; }).join('') + '</p>'
          : '<p class="note">Every skill the posting names is in this resume.</p>')
        + (m.terms.filter(function (t) { return !t.found; }).length ? '<p class="note">Its repeated words you do not use yet: ' + m.terms.filter(function (t) { return !t.found; }).slice(0, 6).map(function (t) { return '“' + esc(t.term) + '”'; }).join(', ') + '.</p>' : '');
    }
    html += '<details class="rbc-jd"' + (jd ? '' : ' open') + '><summary>' + (jd ? 'Change the posting' : 'Paste a posting') + '</summary><textarea id="rb-jd" rows="5" placeholder="Paste the full text of the job posting">' + esc(jd) + '</textarea>'
      + (jd ? '<button class="linkbtn" type="button" id="rb-jd-clear">Remove the posting</button>' : '') + '</details></div>' + payLine(text) + aiLine(text);
    chk.innerHTML = html;
    chk.hidden = false;
  };
  /* What jobs like this resume advertise (Adzuna's ValueMyCV, from postings rather than a model): the resume's skill with the most
     postings that state pay, at the level its title suggests, from the same groups the salary checker uses. */
  var payData = null, payAsked = false;
  var payLine = function (text) {
    var T = window.HRNT;
    if (!payData || !skillPats || !T) {
      if (!payAsked && window.fetch) {
        payAsked = true;
        fetch(H.base + '/tools/salary-checker/').then(function (r) { return r.ok ? r.text() : ''; }).then(function (page) {
          var m = page.match(/<script type="application\/json" id="tl-data">([\s\S]*?)<\/script>/);
          if (m) { try { payData = JSON.parse(m[1]); } catch (e) {} }
          if (payData) drawCheck();
        }).catch(function () {});
      }
      return '';
    }
    var t = String(data.title || ''), lvl = /\b(lead|principal|staff|head|director|vp|chief)\b/i.test(t) ? 'Lead' : /\b(senior|sr)\b/i.test(t) ? 'Senior' : /\b(junior|jr|intern|graduate|entry)\b/i.test(t) ? 'Junior' : '';
    var groups = [];
    T.findSkills(text, skillPats).forEach(function (sk) {
      var g = T.salaryGroup(payData, '', lvl, sk), lv = lvl;
      if (!(g && g.n >= 20)) { g = T.salaryGroup(payData, '', '', sk); lv = ''; }
      if (g && g.n >= 20) groups.push({ sk: sk, lv: lv, g: g });
    });
    if (!groups.length) return '';
    groups.sort(function (a, b) { return a.g.median - b.g.median; });
    var mid = groups[Math.floor((groups.length - 1) / 2)], lo = groups[0], hi = groups[groups.length - 1];
    var k = function (v) { return '$' + Math.round(v / 1000) + 'K'; };
    return '<div class="rbc-pay"><p class="rbc-h"><b>' + k(mid.g.median) + '</b> a year: what jobs asking for your skills advertise</p><p class="note">'
      + (groups.length > 1 ? 'The middle of ' + groups.length + ' skills in this resume: postings that ask for ' + esc(lo.sk) + ' advertise a median of ' + k(lo.g.median) + ', for ' + esc(hi.sk) + ' ' + k(hi.g.median) + '. '
        : 'The median of ' + mid.g.n.toLocaleString('en-US') + ' open postings that ask for ' + esc(mid.sk) + ' and state yearly pay. ')
      + (lvl && mid.lv ? 'Counted at ' + esc(lvl.toLowerCase()) + ' level, from your title. ' : '') + 'Pay depends on the country and the employer too. '
      + '<a href="' + H.base + '/tools/salary-checker/">Check a skill or level</a> · <a href="' + H.base + '/tools/offer-check/">Check an offer</a></p></div>';
  };
  /* AI help without a server of our own: each button opens ChatGPT, Claude or Perplexity with this resume and a ready request.
     Nothing is sent until the visitor clicks, and the request says plainly not to invent anything. */
  var aiAsks = [];
  var aiLine = function (text) {
    if (String(text).replace(/\s+/g, ' ').trim().length < 60) return '';
    var cut = function (t, n) { t = String(t || ''); return t.length > n ? t.slice(0, n) + '…' : t; };
    var cv = cut(text, 2400), post = cut(jd, 1600);
    var asks = [
      ['Rewrite my bullet points', 'Rewrite the bullet points of my resume below. Start each with a strong past-tense verb, keep one result per line, and add a number where my text gives one. Do not invent facts, numbers or employers: where a number is missing, write [number] for me to fill in.\n\nMY RESUME:\n' + cv],
      ['Write my summary', 'Write a resume summary of 2 or 3 sentences from my resume below: my current role, my strongest skills and one result. Plain words, no buzzwords, nothing that is not in my resume.\n\nMY RESUME:\n' + cv]];
    if (jd) asks.push(['Tailor it to the target job', 'Compare my resume with the job posting below. List the skills and words of the posting my resume is missing, then rewrite my summary and my bullet points to match the posting, using only experience that is in my resume.\n\nJOB POSTING:\n' + post + '\n\nMY RESUME:\n' + cv],
                      ['Write the cover letter', 'Write a short cover letter (under 250 words) for the job posting below, from my resume. Lead with two results from my experience that match the posting. Do not invent anything.\n\nJOB POSTING:\n' + post + '\n\nMY RESUME:\n' + cv],
                      ['Practise the interview', 'Interview me for the job posting below, one question at a time, using my resume. After each answer, tell me what was strong and what to add.\n\nJOB POSTING:\n' + post + '\n\nMY RESUME:\n' + cv]);
    var go = [['ChatGPT', 'https://chatgpt.com/'], ['Claude', 'https://claude.ai/new'], ['Perplexity', 'https://www.perplexity.ai/']];
    aiAsks = asks;                                                     // the request is copied, not put in the address: a resume does not belong in browser history
    return '<div class="rbc-ai"><p class="rbc-h"><b>AI help</b> with your own ChatGPT, Claude or Perplexity</p>'
      + '<p class="note">Each link copies a ready request with your resume' + (jd ? ' and the target job' : '') + ' and opens that assistant: paste it there (Ctrl+V or ⌘V). Nothing leaves this page until you paste it. Check every line it writes.</p><ul class="rbc-asks">'
      + asks.map(function (a, i) { return '<li><b>' + esc(a[0]) + '</b>' + go.map(function (g) { return '<a href="' + g[1] + '" target="_blank" rel="nofollow noopener" data-ask="' + i + '">' + g[0] + '</a>'; }).join('') + '</li>'; }).join('')
      + '</ul><p class="note" id="rb-ai-done" hidden>Copied. Paste it in the assistant’s message box.</p></div>';
  };
  var needPats = function () {
    if (skillPats || !window.HRNT) return;
    fetch(H.base + '/data/skills.json').then(function (r) { return r.json(); }).then(function (p) { skillPats = window.HRNT.compilePats(p); drawCheck(); }).catch(function () {});
  };
  if (chk) {
    var drawPreview0 = drawPreview, ptimer;
    drawPreview = function () { drawPreview0(); clearTimeout(ptimer); ptimer = setTimeout(drawCheck, 500); };      // any change to the resume (typing, an example, a skill added) updates the score
    var start = function () { if (!window.HRNT) return setTimeout(start, 150); needPats(); drawCheck(); };
    start();
    root.addEventListener('input', function (ev) {
      if (ev.target.id === 'rb-jd') { jd = ev.target.value; H.set('hrn_rb_target', jd); jdTitle = ''; }
      clearTimeout(ctimer);
      ctimer = setTimeout(function () {
        var keep = document.activeElement && document.activeElement.id === 'rb-jd';
        if (keep) return;                                  // do not redraw under the cursor; the result updates when the box loses focus
        drawCheck();
      }, 700);
    });
    root.addEventListener('focusout', function (ev) { if (ev.target.id === 'rb-jd') drawCheck(); });
    root.addEventListener('click', function (ev) {
      var ai = ev.target.getAttribute && ev.target.getAttribute('data-ask');
      if (ai != null && aiAsks[+ai]) {                      // copy first; the link itself then opens the assistant in a new tab
        var txt = aiAsks[+ai][1], done = $('rb-ai-done');
        var ok = function () { if (done) done.hidden = false; };
        if (navigator.clipboard && navigator.clipboard.writeText) navigator.clipboard.writeText(txt).then(ok, function () {});
        else { var ta = document.createElement('textarea'); ta.value = txt; document.body.appendChild(ta); ta.select(); try { document.execCommand('copy'); ok(); } catch (e) {} ta.remove(); }
        return;
      }
      var add = ev.target.getAttribute && ev.target.getAttribute('data-addskill');
      if (add) {
        var list = String(data.skills || '').split(',').map(function (s) { return s.trim(); }).filter(Boolean);
        if (list.indexOf(add) < 0) list.push(add);
        data.skills = list.join(', '); save(); drawForm(); drawPreview(); drawCheck();
      } else if (ev.target.id === 'rb-jd-clear') { jd = ''; jdTitle = ''; H.set('hrn_rb_target', ''); drawCheck(); }
    });
    var slug = (location.search.match(/[?&]job=([a-z0-9-]{3,160})/) || [])[1];      // ?job=<slug>: the posting from its page on this site
    if (slug && window.fetch && window.DOMParser) {
      fetch(H.base + '/job/' + slug + '/').then(function (r) { return r.ok ? r.text() : ''; }).then(function (page) {
        if (!page) return;
        var doc = new DOMParser().parseFromString(page, 'text/html'), d = doc.querySelector('.prose.desc') || doc.querySelector('.prose'), h1 = doc.querySelector('h1');
        if (!d) return;
        var blocks = [].map.call(d.querySelectorAll('h2,h3,h4,p,li'), function (x) { return x.textContent.trim(); }).filter(Boolean);
        jd = blocks.length ? blocks.join('\n') : d.textContent.trim(); jdTitle = h1 ? h1.textContent.trim() : '';
        H.set('hrn_rb_target', jd); drawCheck();
      }).catch(function () {});
    }
  }

  /* What the open jobs ask for: the skills this resume names, each with the number of open jobs that ask for it, and how many
     jobs ask for at least three of them. Counted in the browser from the same index the search uses. */
  var demand = document.getElementById('rb-demand'), pats = null, timer;
  /* Skill GPS: the one skill to add that would bring the most open jobs within reach (jobs that ask for all but one of the
     resume's skills, plus this one), with the pay those jobs advertise at the top of their range. Counted in the browser. */
  function nextSkills(gain, gainPay, nf, need) {
    var best = Object.keys(gain).sort(function (a, b) { return gain[b] - gain[a]; }).slice(0, 4);
    if (!best.length || gain[best[0]] < 5) return '';
    var med = function (a) { if (!a || a.length < 10) return ''; a = a.slice().sort(function (x, y) { return x - y; }); return ' · up to $' + Math.round(a[Math.floor(a.length / 2)] / 1000) + 'K at the median'; };
    return '<div class="rbd-next"><p class="rbd-h"><b>Skill GPS</b> the one skill to add next</p><ol>' + best.map(function (t) {
      return '<li><a href="' + H.base + '/jobs/?skills=' + encodeURIComponent(t) + '">' + H.esc(t) + '</a>: <b>+' + nf(gain[t]) + '</b> open jobs would ask for ' + (need === 1 ? 'a skill' : need + ' of the skills') + ' in this resume' + med(gainPay[t]) + '</li>';
    }).join('') + '</ol><p class="note">Counted now from every open job: the jobs that ask for all but one of your skills, plus this one. Learn it only if it fits the work you want.</p></div>';
  }
  function drawDemand() {
    if (!demand || !H.load) return;
    var text = [data.title, data.summary, data.skills].concat(data.exp.map(function (x) { return x.role + ' ' + x.text; })).join('\n');
    if (text.replace(/\s/g, '').length < 20) { demand.innerHTML = ''; return; }
    (pats ? Promise.resolve(pats) : fetch(H.base + '/data/skills.json').then(function (r) { return r.json(); }).then(function (p) { pats = p; return p; })).then(function (p) {
      var mine = []; p.forEach(function (x) { try { if (new RegExp(x[1], 'i').test(text)) mine.push(x[0]); } catch (e) {} });
      if (!mine.length) { demand.innerHTML = '<p class="note">No skill that employers name in postings was found in this resume yet. Write the tools and methods you use by their names.</p>'; return; }
      return H.load().then(function (all) {
        var per = {}, need = Math.min(3, mine.length), fit = 0, gain = {}, gainPay = {};
        mine.forEach(function (t) { per[t] = 0; });
        all.forEach(function (j) {
          var k = 0; for (var i = 0; i < j[7].length; i++) if (per[j[7][i]] != null) { per[j[7][i]]++; k++; }
          if (k >= need) { fit++; return; }
          if (k === need - 1) j[7].forEach(function (t) { if (per[t] == null) { gain[t] = (gain[t] || 0) + 1; if (j[13]) (gainPay[t] = gainPay[t] || []).push(j[13]); } });   // one more skill would make it fit
        });
        var top = mine.slice().sort(function (a, b) { return per[b] - per[a]; }).slice(0, 8), mx = per[top[0]] || 1, nf = function (x) { return Number(x).toLocaleString('en-US'); };
        demand.innerHTML = '<p class="rbd-h"><b>' + nf(fit) + '</b> open jobs ask for ' + (need === 1 ? 'the skill' : 'at least ' + need + ' of the ' + mine.length + ' skills') + ' in this resume</p><div class="hbars">' +
          top.map(function (t) { return '<a href="' + H.base + '/jobs/?skills=' + encodeURIComponent(t) + '"><span class="hn">' + H.esc(t) + '</span><span class="hb"><i style="width:' + Math.max(2, Math.round(100 * per[t] / mx)) + '%"></i></span><span class="hc">' + nf(per[t]) + ' jobs</span></a>'; }).join('') + '</div>'
          + nextSkills(gain, gainPay, nf, need);
      });
    }).catch(function () {});
  }
  document.getElementById('rb').addEventListener('input', function () { clearTimeout(timer); timer = setTimeout(drawDemand, 900); });
  setTimeout(drawDemand, 600);

  /* An example from /resume/examples/<role>/ opens here: ?example=<role>. A resume that is already in this browser is replaced
     only if the visitor agrees. */
  var exq = ''; try { exq = new URLSearchParams(location.search).get('example') || ''; } catch (e) {}
  if (exq) fetch(H.base + '/data/resume-examples.json').then(function (r) { return r.json(); }).then(function (all) {
    var ex = all[exq]; if (!ex) return;
    var mine = (data.name + data.summary + data.exp.map(function (x) { return x.role + x.text; }).join('')).trim();
    if (mine && !confirm('Replace the resume in this browser with the example?')) return;
    Object.keys(ex).forEach(function (k) { data[k] = JSON.parse(JSON.stringify(ex[k])); });
    save(); applyTpl(); drawForm(); drawPreview(); drawDemand();
    try { history.replaceState(null, '', location.pathname); } catch (e) {}
  }).catch(function () {});
})();
