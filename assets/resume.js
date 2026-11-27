/* Resume builder: everything stays in this browser (localStorage). "Download PDF" uses the browser's print dialog. */
(function () {
  var root = document.getElementById('rb'); if (!root) return;
  var H = window.HRN, esc = H.esc, $ = function (id) { return document.getElementById(id); };
  var blank = { name: '', title: '', email: '', phone: '', place: '', links: '', summary: '', skills: '', interests: '', exp: [{ role: '', org: '', dates: '', text: '' }], edu: [{ what: '', org: '', dates: '' }],
    proj: [], cert: [], lang: [] };
  var copy = function (x) { return JSON.parse(JSON.stringify(x)); };
  // the templates, in the order of the gallery; build.py writes /resume-templates/ and each template's page from the same ids (TPL_NAMES below)
  var TPLS = ['classic', 'modern', 'simple', 'professional', 'compact', 'executive', 'student', 'creative', 'elegant', 'bold', 'fresh', 'heritage', 'developer', 'timeline', 'minimal', 'accent'];
  // Design: a colour for the headings (all dark enough to print and read), a font, the paper. '' is the template's own choice.
  var COLS = [['', 'The template’s own'], ['#111111', 'Black'], ['#1f3a68', 'Navy'], ['#2b5d8a', 'Blue'], ['#0f6b6b', 'Teal'], ['#1d5c3a', 'Green'], ['#7a1f2b', 'Burgundy'], ['#4b2a5e', 'Plum'], ['#3b4a5a', 'Slate']];
  var FONTS = [['', 'Template'], ['inter', 'Inter'], ['arial', 'Arial'], ['georgia', 'Georgia'], ['times', 'Times New Roman']];
  var PAPER = { letter: [816, 1056, 'Letter'], a4: [794, 1123, 'A4'] }, MARGIN = 48;          // CSS pixels at 96 per inch; a half-inch margin on every side
  var fill = function (d) {                                                         // a damaged, old or foreign value must not break the builder
    if (!d || typeof d !== 'object' || Array.isArray(d)) d = {};
    Object.keys(blank).forEach(function (k) {
      if (Array.isArray(blank[k]) ? !Array.isArray(d[k]) || (!d[k].length && blank[k].length) : typeof d[k] !== 'string') d[k] = copy(blank[k]);
      else if (Array.isArray(d[k])) d[k] = d[k].filter(function (x) { return x && typeof x === 'object'; });
    });
    if (TPLS.indexOf(d.tpl) < 0) d.tpl = 'classic';
    if (!COLS.some(function (c) { return c[0] === d.col; })) delete d.col;
    if (!FONTS.some(function (f) { return f[0] === d.font; })) delete d.font;
    if (!PAPER[d.paper]) delete d.paper;
    if (typeof d.fs !== 'number' || !(d.fs >= 10.5 && d.fs <= 16)) delete d.fs;
    if (typeof d.lh !== 'number' || !(d.lh >= 1.2 && d.lh <= 1.8)) delete d.lh;
    return d;
  };
  // Letter where the visitor's browser says US, Canada, Mexico or the Philippines (or just "en"), A4 everywhere else, until they pick one
  var paperOf = function (d) { return d.paper || (/^en$|-(US|CA|MX|PH)$/i.test(navigator.language || 'en') ? 'letter' : 'a4'); };
  var data = fill(H.get('hrn_resume', null));
  /* Several resumes, one per kind of job: the open one stays in hrn_resume, which the other pages read; the others, with the posting
     each was aimed at, wait in hrn_resume_set. */
  var SET = H.get('hrn_resume_set', null);
  if (!SET || typeof SET !== 'object' || !Array.isArray(SET.items) || !SET.items.length) SET = { cur: 'r1', items: [{ id: 'r1', label: '' }] };
  SET.items = SET.items.filter(function (x) { return x && typeof x.id === 'string'; }).slice(0, 30);
  if (!SET.items.length) SET.items = [{ id: 'r1', label: '' }];
  if (!SET.items.some(function (x) { return x.id === SET.cur; })) SET.cur = SET.items[0].id;
  // the template, the colour, the font and the size on one sheet element (the preview, or a small picture in the Design gallery)
  var styleSheet = function (el, d, tpl) {
    el.className = 'rbs tpl-' + (tpl || d.tpl) + (d.font ? ' ff-' + d.font : '');
    if (d.col) el.style.setProperty('--uac', d.col); else el.style.removeProperty('--uac');
    if (d.fs) el.style.setProperty('--fs', d.fs + 'px'); else el.style.removeProperty('--fs');
    el.style.lineHeight = d.lh ? String(d.lh) : '';
  };
  var applyTpl = function () {
    var pv = $('rb-preview'), sel = $('rb-tpl'); styleSheet(pv, data); if (sel) sel.value = data.tpl;
    Array.prototype.forEach.call(document.querySelectorAll('.tplcard'), function (c) { c.classList.toggle('on', c.getAttribute('data-pick') === data.tpl); });
  };
  var save = function () { H.set('hrn_resume', data); };
  var cutText = function (t, n) { t = String(t || ''); return t.length > n ? t.slice(0, n) + '…' : t; };
  var copyText = function (txt, ok) {
    if (navigator.clipboard && navigator.clipboard.writeText) navigator.clipboard.writeText(txt).then(ok, function () {});
    else { var ta = document.createElement('textarea'); ta.value = txt; document.body.appendChild(ta); ta.select(); try { document.execCommand('copy'); ok(); } catch (e) {} ta.remove(); }
  };
  var field = function (label, key, type, ph) {
    return '<label class="rl">' + label + (type === 'area' ? '<textarea data-k="' + key + '" rows="4" placeholder="' + ph + '">' + esc(data[key]) + '</textarea>'
      : '<input type="text" data-k="' + key + '" placeholder="' + ph + '" value="' + esc(data[key]) + '">') + '</label>';
  };
  /* The lists of the resume: jobs, schools, projects, certificates, languages. Each field is [key, placeholder, label for screen readers]. */
  var LISTS = {
    exp: { f: [['role', 'Job title'], ['org', 'Company'], ['dates', '2022 – now', 'Dates']], text: 'One achievement per line. Start with a verb, add a number where you can.', add: '+ Add a job', del: 'Remove this job', hints: true },
    edu: { f: [['what', 'Degree or course'], ['org', 'School'], ['dates', '2018 – 2022', 'Dates']], add: '+ Add education', del: 'Remove' },
    proj: { f: [['name', 'Project name'], ['link', 'github.com/you/project', 'Link']], text: 'What it does and what came of it: users, downloads, time saved. One point per line.', add: '+ Add a project', del: 'Remove this project', hints: true },
    cert: { f: [['name', 'Certificate or licence'], ['org', 'Issued by'], ['date', '2024', 'Year']], add: '+ Add a certificate', del: 'Remove' },
    lang: { f: [['name', 'Language'], ['level', 'Native, fluent, B2…', 'Level']], add: '+ Add a language', del: 'Remove', levels: true }
  };
  var emptyOf = function (k) { var o = {}; LISTS[k].f.forEach(function (x) { o[x[0]] = ''; }); if (LISTS[k].text) o.text = ''; return o; };
  /* Hints under each line of a job or project, as it is typed: a verb first, a number, two lines at most (the bullet point tool's rules). */
  var hintsHtml = function (text) {
    var T = window.HRNT; if (!T || !T.lineHints) return '';
    var rows = String(text || '').split('\n').map(T.lineHints).filter(Boolean);
    if (!rows.length) return '';
    var bad = rows.filter(function (r) { return !r.ok || r.hints.length; }), good = rows.length - rows.filter(function (r) { return !r.ok; }).length;
    return '<p class="rbh-sum"><b class="' + (good === rows.length ? 'ok' : '') + '">' + good + ' of ' + rows.length + '</b> line' + (rows.length === 1 ? '' : 's') + ' read well</p>'
      + (bad.length ? '<ul class="rbh">' + bad.map(function (r) {
        var lvl = r.hints.some(function (h) { return h.level === 'fix'; }) ? 'fix' : r.ok ? 'info' : 'warn';
        return '<li class="' + lvl + '"><span class="rbh-l">' + esc(r.text.length > 54 ? r.text.slice(0, 52).replace(/\s+\S*$/, '') + '…' : r.text) + '</span><span class="rbh-t">' + r.hints.map(function (h) { return esc(h.t); }).join(' · ') + '</span></li>';
      }).join('') + '</ul>' : '');
  };
  var listBlock = function (k, x, i) {
    var L = LISTS[k];
    return '<div class="rblock" data-list="' + k + '" data-i="' + i + '"><div class="rrow">' + L.f.map(function (f) {
        return '<input type="text" data-f="' + f[0] + '" placeholder="' + esc(f[1]) + '" aria-label="' + esc(f[2] || f[1]) + '" value="' + esc(x[f[0]]) + '"' + (L.levels && f[0] === 'level' ? ' list="rb-levels"' : '') + '>';
      }).join('') + '</div>'
      + (L.text ? '<textarea data-f="text" rows="' + Math.min(9, Math.max(4, String(x.text || '').split('\n').length + 1)) + '" placeholder="' + esc(L.text) + '">' + esc(x.text) + '</textarea>' : '')
      + (L.hints ? '<div class="rbh-box" aria-live="polite">' + hintsHtml(x.text) + '</div>' : '')
      + '<button class="linkbtn" type="button" data-del="' + k + '">' + L.del + '</button></div>';
  };
  var listOf = function (k) { return data[k].map(function (x, i) { return listBlock(k, x, i); }).join('') + '<p><button class="btn ghost sm" type="button" data-add="' + k + '">' + LISTS[k].add + '</button></p>'; };
  /* The summary step: a word count, and the request for an AI assistant in the tone the visitor picks. */
  var tone = H.get('hrn_rb_tone', 'plain');
  var sumCount = function () {
    var n = String(data.summary || '').split(/\s+/).filter(Boolean).length;
    return n ? n + (n === 1 ? ' word' : ' words') + (n > 60 ? ': over 60, cut it to two or three lines' : n < 20 ? ': a summary is usually 30 to 60 words' : ': a good length') : 'Aim for 30 to 60 words.';
  };
  var sumAI = function () {
    var T = window.HRNT; if (!T || !T.TONES) return '';
    return '<div class="rb-sumai"><p><b>Let an AI assistant draft it</b><span>From the jobs you entered, in the tone you pick. It copies the request; you paste it and check every line.</span></p>'
      + '<p class="rb-tones" role="radiogroup" aria-label="Tone">' + T.TONES.map(function (t) { return '<button type="button" class="chipbtn" role="radio" aria-checked="' + (tone === t[0]) + '" aria-pressed="' + (tone === t[0]) + '" data-tone="' + t[0] + '">' + t[1] + '</button>'; }).join('') + '</p>'
      + '<p class="rb-sumgo">' + [['ChatGPT', 'https://chatgpt.com/'], ['Claude', 'https://claude.ai/new'], ['Perplexity', 'https://www.perplexity.ai/']].map(function (g) {
        return '<a href="' + g[1] + '" target="_blank" rel="nofollow noopener" data-asksum="1">Write it with ' + g[0] + '</a>'; }).join('') + '</p>'
      + '<p class="note" id="rb-sum-done" hidden>Copied. Paste it in the assistant’s message box (Ctrl+V or ⌘V).</p></div>';
  };
  var drawForm = function () {
    var exp = listOf('exp'), edu = listOf('edu'), empty = !hasContent(data);
    var sec = function (id, inner) { return '<div class="rsec' + (tab === id ? ' on' : '') + '" data-sec="' + id + '">' + inner + nextBtn(id) + '</div>'; };
    var fileIn = '<input type="file" id="rb-file" accept=".docx,.pdf,.txt,.md,.json" hidden>';
    $('rb-form').innerHTML =
      // two ways in while the builder is empty, as CVMaker opens: your old resume (read here, never uploaded) or a blank form
      sec('contact', '<div class="rb-imp no-print">' + (empty
        ? '<p><b>Two ways to start</b><span>Bring in the resume you have, or start from nothing. Either way it stays in this browser.</span></p>' +
          '<div class="rb-ways"><label><b>Upload my resume</b><span>PDF or Word (.docx). Read in this browser, nothing is uploaded.</span>' + fileIn + '</label>' +
          '<button type="button" id="rb-scratch"><b>Start from scratch</b><span>Begin with the job you want</span></button></div><p class="rb-imp-a">'
        : '<p><b>Already have a resume?</b><span>Word, PDF, text or JSON Resume: it is read in this browser, nothing is uploaded.</span></p>' +
          '<p class="rb-imp-a"><label class="btn ghost sm">Import a file' + fileIn + '</label>') +
        '<button class="linkbtn" type="button" id="rb-paste">' + (empty ? 'Or paste the text of your resume' : 'or paste the text') + '</button></p>' +
        '<div id="rb-pastebox" hidden><textarea id="rb-pastetext" rows="7" placeholder="Paste the whole resume as text: name, contacts, experience, education, skills"></textarea>' +
        '<p><button class="btn sm" type="button" id="rb-pasteread">Read it</button></p></div>' +
        (impMsg ? '<p class="note rb-impmsg" role="status">' + impMsg + '</p>' : '') +
        // a third way to start, while the builder is empty (plan item 4.7, 20 Nov 2026): one of the 390 examples for your work
        (hasContent(data) ? '' : '<p class="rb-imp-a rb-start"><label for="rb-expick">Or start from an example for your work:</label> <input id="rb-expick" list="rb-exlist" placeholder="Type a job, for example nurse" autocomplete="off"><datalist id="rb-exlist"></datalist> <button class="btn ghost sm" type="button" id="rb-exgo">Open it</button></p>') +
        '</div>' +
        // the job you want comes first (CVMaker asks for the desired job title before anything else): it is the headline under the name,
        // and it brings the skills employers ask for in that work and lines to start from, one click each
        '<span class="flabel">The job you want</span>' + field('Target job title (the headline under your name)', 'title', 'text', 'SEO Specialist') +
        '<div id="rb-tsug" class="rb-tsug no-print" aria-live="polite">' + sugHtml(false) + '</div>' +
        '<span class="flabel">About you</span>' + field('Full name', 'name', 'text', 'Alex Morgan') +
        '<div class="rrow">' + field('Email', 'email', 'text', 'you@example.com') + field('Phone', 'phone', 'text', '+1 555 010 0199') + '</div>' +
        '<div class="rrow">' + field('Location', 'place', 'text', 'Berlin, Germany · open to remote') + field('Links', 'links', 'text', 'github.com/you, linkedin.com/in/you') + '</div>') +
      sec('summary', field('Summary', 'summary', 'area', 'Two or three sentences: what you do, for how long, and what you are best at.') + '<p class="note rb-sumc" id="rb-sumc">' + sumCount() + '</p>' + sumAI()) +
      sec('experience', '<span class="flabel">Experience</span>' + exp) +
      sec('education', '<span class="flabel">Education</span>' + edu) +
      sec('skills', '<span class="flabel">Skills</span>' + field('Comma-separated', 'skills', 'text', 'Python, PostgreSQL, AWS, Kubernetes') +
        '<div id="rb-ssug" class="rb-tsug no-print" aria-live="polite">' + sugHtml(true) + '</div>') +
      sec('more', '<p class="note rb-more-n">Each of these is optional: a section with nothing in it is left off the page.</p>'
        + '<span class="flabel">Projects</span>' + listOf('proj') + '<span class="flabel">Certificates and licences</span>' + listOf('cert')
        + '<span class="flabel">Languages</span>' + listOf('lang')
        + '<span class="flabel">Interests</span>' + field('Two to four, each specific (optional)', 'interests', 'text', 'Volunteer soccer coach, two seasons · Half-marathons, three finished')
        + '<datalist id="rb-levels"><option value="Native"><option value="Fluent"><option value="Professional"><option value="Conversational"><option value="Basic"><option value="C2"><option value="C1"><option value="B2"><option value="B1"><option value="A2"></datalist>') +
      sec('finish', finishUp());
    drawTabs(); drawSet(); drawMode(); needSug();
  };
  /* ---- Import an old resume, as resumai and Rezi offer it: a Word file is unzipped here (the browser's own DecompressionStream), a PDF
     is read with pdf.js, loaded only when a PDF is chosen; the text goes through HRNT.parseResume. Nothing leaves the browser. ---- */
  var impMsg = '';
  var PDFJS = 'https://cdnjs.cloudflare.com/ajax/libs/pdf.js/3.11.174/';
  var docxXml = function (buf) {
    var v = new DataView(buf), u8 = new Uint8Array(buf), eocd = -1, i, dec = new TextDecoder();
    for (i = u8.length - 22; i >= Math.max(0, u8.length - 65557); i--) if (v.getUint32(i, true) === 0x06054b50) { eocd = i; break; }
    if (eocd < 0) return Promise.reject(new Error('This is not a Word (.docx) file.'));
    var n = v.getUint16(eocd + 10, true), p = v.getUint32(eocd + 16, true);
    for (i = 0; i < n && v.getUint32(p, true) === 0x02014b50; i++) {
      var method = v.getUint16(p + 10, true), size = v.getUint32(p + 20, true), nl = v.getUint16(p + 28, true), xl = v.getUint16(p + 30, true), cl = v.getUint16(p + 32, true), off = v.getUint32(p + 42, true);
      if (dec.decode(u8.subarray(p + 46, p + 46 + nl)) === 'word/document.xml') {
        var start = off + 30 + v.getUint16(off + 26, true) + v.getUint16(off + 28, true), raw = u8.slice(start, start + size);
        if (method === 0) return Promise.resolve(dec.decode(raw));
        if (method !== 8 || typeof DecompressionStream === 'undefined') return Promise.reject(new Error('This browser cannot open Word files. Paste the text instead.'));
        return new Response(new Blob([raw]).stream().pipeThrough(new DecompressionStream('deflate-raw'))).text();
      }
      p += 46 + nl + xl + cl;
    }
    return Promise.reject(new Error('This is not a Word (.docx) file.'));
  };
  var docxText = function (xml) {
    var W = 'http://schemas.openxmlformats.org/wordprocessingml/2006/main', doc = new DOMParser().parseFromString(xml, 'application/xml');
    return Array.prototype.map.call(doc.getElementsByTagNameNS(W, 'p'), function (para) {
      var s = para.getElementsByTagNameNS(W, 'numPr').length ? '• ' : '';          // a list item in Word has no bullet character, only list settings
      Array.prototype.forEach.call(para.getElementsByTagNameNS(W, '*'), function (el) {
        if (el.localName === 't') s += el.textContent; else if (el.localName === 'tab') s += ' '; else if (el.localName === 'br' || el.localName === 'cr') s += '\n';
      });
      return s;
    }).join('\n');
  };
  var pdfLib = function () {
    if (window.pdfjsLib) return Promise.resolve(window.pdfjsLib);
    return new Promise(function (ok, no) {
      var sc = document.createElement('script'); sc.src = PDFJS + 'pdf.min.js'; sc.crossOrigin = 'anonymous';
      sc.onload = function () { window.pdfjsLib.GlobalWorkerOptions.workerSrc = PDFJS + 'pdf.worker.min.js'; ok(window.pdfjsLib); };
      sc.onerror = function () { no(new Error('The PDF reader did not load. Check the connection, or paste the text instead.')); };
      document.head.appendChild(sc);
    });
  };
  var pdfText = function (buf) {
    return pdfLib().then(function (lib) { return lib.getDocument({ data: new Uint8Array(buf) }).promise; }).then(function (doc) {
      var pages = []; for (var i = 1; i <= Math.min(doc.numPages, 6); i++) pages.push(doc.getPage(i).then(function (pg) { return pg.getTextContent(); }));
      return Promise.all(pages);
    }).then(function (contents) {
      return contents.map(function (c) {
        var rows = [], last = null;                                                 // the pieces of text on one height make one line
        c.items.forEach(function (it) {
          if (typeof it.str !== 'string') return;
          var x = it.transform[4], y = Math.round(it.transform[5]);
          if (last && Math.abs(last.y - y) <= 2) last.s += (it.str && last.s && !/\s$/.test(last.s) && !/^\s/.test(it.str) && x - last.end > 1.5 ? ' ' : '') + it.str;
          else { last = { y: y, s: it.str }; rows.push(last); }
          last.end = x + (it.width || 0);
        });
        return rows.map(function (r) { return r.s; }).join('\n');
      }).join('\n');
    });
  };
  var useImport = function (r, how, sureDone) {
    if (!r || !(r.name || r.summary || r.skills || r.exp.length)) { impMsg = 'Nothing could be read from ' + esc(how) + '. Paste the text instead, or fill in the form.'; drawForm(); return; }
    if (hasContent(data) && !sureDone) {              // asked on the page; the answer calls this again
      H.sure(document.getElementById('rb-pasteread') || document.getElementById('rb-paste'), 'Open the resume from ' + how + ' as a new resume? The one you have now stays in the list above the form.', 'Open as new')
        .then(function (ok) { if (ok) useImport(r, how, true); });
      return;
    }
    if (hasContent(data) && !addResume({ tpl: data.tpl })) return;
    ['name', 'title', 'email', 'phone', 'place', 'links', 'summary', 'skills'].forEach(function (k) { data[k] = r[k] || ''; });
    data.exp = r.exp.length ? r.exp.map(function (x) { return { role: x.role || '', org: x.org || '', dates: x.dates || '', text: x.text || '' }; }) : copy(blank.exp);
    data.edu = r.edu.length ? r.edu.map(function (x) { return { what: x.what || '', org: x.org || '', dates: x.dates || '' }; }) : copy(blank.edu);
    ['proj', 'cert', 'lang'].forEach(function (k) { data[k] = (r[k] || []).map(function (x) { var o = emptyOf(k); Object.keys(o).forEach(function (f) { o[f] = String(x[f] || ''); }); return o; }); });
    var nsk = r.skills ? r.skills.split(',').length : 0, more = function (k, one, many) { var n = (r[k] || []).length; return n ? [n + ' ' + (n === 1 ? one : many)] : []; };
    impMsg = '<b>Read from ' + esc(how) + ':</b> ' + [r.exp.length + (r.exp.length === 1 ? ' job' : ' jobs'), r.edu.length + (r.edu.length === 1 ? ' school' : ' schools'), nsk + (nsk === 1 ? ' skill' : ' skills')]
      .concat(more('proj', 'project', 'projects'), more('cert', 'certificate', 'certificates'), more('lang', 'language', 'languages')).join(', ') +
      '. An import is a first draft: check each section, above all the jobs.';
    save(); drawForm(); drawPreview(); drawDemand();
  };
  var hasContent = function (d) { return !!(d.name + d.summary + d.exp.map(function (x) { return x.role + x.text; }).join('')).trim(); };

  /* Several resumes: a list above the form, with New (your contact details, the rest blank), Duplicate, Rename and Delete. */
  var curItem = function () { return SET.items.filter(function (x) { return x.id === SET.cur; })[0]; };
  var keepSet = function () { H.set('hrn_resume_set', SET); };
  var labelOf = function (it) { var d = it.id === SET.cur ? data : it.data || {}; return it.label || d.title || d.name || 'Untitled resume'; };
  var stash = function () { var c = curItem(); c.data = copy(data); c.jd = typeof jd === 'string' ? jd : ''; };
  var redraw = function () { applyTpl(); drawForm(); drawPreview(); drawDemand(); if (chk) drawCheck(); };
  var setJd = function (v) { jd = v || ''; jdTitle = ''; H.set('hrn_rb_target', jd); };
  var addResume = function (start, label, post) {             // the current resume goes into the list; a new one opens
    // said on the page, not in the browser's own alert window (some browsers and the app's pane suppress those)
    if (SET.items.length >= 20) { H.sure(document.getElementById('rb-new'), 'Twenty resumes is the limit here. Delete one you no longer use first.', 'OK'); return false; }
    stash();
    var id = 'r' + Date.now().toString(36) + Math.floor(Math.random() * 1296).toString(36);
    SET.items.push({ id: id, label: label || '' }); SET.cur = id;
    data = fill(copy(start || {})); setJd(post); keepSet(); save();
    return true;
  };
  var openItem = function (id) {
    var it = SET.items.filter(function (x) { return x.id === id; })[0];
    if (!it || id === SET.cur) return;
    stash();
    data = fill(it.data); setJd(it.jd); delete it.data; delete it.jd; SET.cur = id;
    keepSet(); save(); redraw();
  };
  var drawSet = function () {
    var el = $('rb-set'); if (!el) return;
    var n = SET.items.length;
    el.innerHTML = '<label class="rb-which"><span>' + (n > 1 ? 'Your resumes (' + n + ')' : 'Your resume') + '</span><select id="rb-which">'
      + SET.items.map(function (it) { return '<option value="' + esc(it.id) + '"' + (it.id === SET.cur ? ' selected' : '') + '>' + esc(labelOf(it)) + '</option>'; }).join('') + '</select></label>'
      + '<span class="rb-setb"><button class="linkbtn" type="button" id="rb-new" title="A new resume with your contact details filled in">New</button>'
      + '<button class="linkbtn" type="button" id="rb-dup" title="A copy of this resume to aim at another kind of job">Duplicate</button>'
      + '<button class="linkbtn" type="button" id="rb-ren">Rename</button>' + (n > 1 ? '<button class="linkbtn" type="button" id="rb-delr">Delete</button>' : '') + '</span>'
      + (n === 1 && hasContent(data) ? '<p class="note">Applying for two kinds of jobs? Duplicate this resume and aim the copy at the other posting: each keeps its own target job.</p>' : '');
  };
  var readFile = function (f) {
    var T = window.HRNT, name = f.name || 'the file', ext = (name.split('.').pop() || '').toLowerCase();
    impMsg = 'Reading ' + esc(name) + '…'; drawForm();
    var done = function (text) { useImport(T.parseResume(text), name); };
    var fail = function (err) { impMsg = esc(err && err.message || 'This file could not be read.') ; drawForm(); };
    if (f.size > 8e6) return fail(new Error('This file is over 8 MB. A resume is usually under 1 MB: save it again, or paste the text.'));
    if (ext === 'json') return f.text().then(function (t) { var o; try { o = JSON.parse(t); } catch (e) { return fail(new Error('This JSON file could not be read.')); } var r = T.fromJsonResume(o); return r ? useImport(r, name) : fail(new Error('This JSON file is not in the JSON Resume format.')); });
    if (ext === 'docx') return f.arrayBuffer().then(docxXml).then(docxText).then(done).catch(fail);
    if (ext === 'pdf') return f.arrayBuffer().then(pdfText).then(done).catch(fail);
    if (ext === 'doc') return fail(new Error('An old .doc file cannot be read here. Open it in Word and save it as .docx or PDF, or paste the text.'));
    return f.text().then(done).catch(fail);
  };
  root.addEventListener('change', function (ev) { if (ev.target.id === 'rb-file' && ev.target.files && ev.target.files[0]) readFile(ev.target.files[0]); });

  /* Tabs, as Rezi lays its builder out: one section at a time, a "next" button, and "Finish up" with the templates and the format. */
  var TABS = [['contact', 'Contact'], ['summary', 'Summary'], ['experience', 'Experience'], ['education', 'Education'], ['skills', 'Skills'], ['more', 'Projects & more'], ['finish', 'Finish up']];
  var tab = H.get('hrn_rb_tab', 'contact');
  if (!TABS.some(function (t) { return t[0] === tab; })) tab = 'contact';
  var filled = function (id) {
    return id === 'contact' ? !!(data.name && (data.email || data.phone)) : id === 'summary' ? String(data.summary || '').length > 40
      : id === 'experience' ? data.exp.some(function (x) { return x.role && x.text; }) : id === 'education' ? data.edu.some(function (x) { return x.what || x.org; })
      : id === 'skills' ? String(data.skills || '').split(',').filter(function (x) { return x.trim(); }).length >= 3
      : id === 'more' ? data.proj.some(function (x) { return x.name || x.text; }) || data.cert.some(function (x) { return x.name; }) || data.lang.some(function (x) { return x.name; }) || !!data.interests : false;
  };
  var drawTabs = function () {
    var nav = $('rb-tabs'); if (!nav) return;
    nav.innerHTML = TABS.map(function (t, i) { return '<button type="button" data-tab="' + t[0] + '" class="' + (t[0] === tab ? 'on' : '') + (filled(t[0]) ? ' done' : '') + '"><i>' + (filled(t[0]) ? '✓' : i + 1) + '</i>' + t[1] + '</button>'; }).join('');
  };
  var nextBtn = function (id) {
    var i = TABS.map(function (t) { return t[0]; }).indexOf(id);
    return i < TABS.length - 1 ? '<p class="rsec-next"><button class="btn sm" type="button" data-tab="' + TABS[i + 1][0] + '">Next: ' + TABS[i + 1][1] + ' →</button></p>' : '';
  };
  var setTab = function (id) {
    tab = id; H.set('hrn_rb_tab', id);
    Array.prototype.forEach.call(document.querySelectorAll('#rb-form .rsec'), function (el) { el.classList.toggle('on', el.getAttribute('data-sec') === id); });
    drawTabs();
    var left = document.querySelector('.rb-left'); if (left && left.getBoundingClientRect().top < 0) left.scrollIntoView({ behavior: 'smooth', block: 'start' });
  };
  /* The templates: a name and one line each. build.py reads this list (the count in the page copy, and a check that every template has
     its page at /resume-templates/<id>/). */
  var TPL_NAMES = { classic: ['Classic', 'Serif text, calm headings, for any field'], modern: ['Modern', 'Clean sans-serif, a bar on each heading'],
    simple: ['Simple', 'The plainest page: Arial, bold headings, no lines'], professional: ['Professional', 'Serif, small capitals, a rule under the header'],
    compact: ['Compact', 'Smaller type that fits more on one page'], executive: ['Executive', 'Centred name and headings, for senior roles'],
    student: ['Student', 'Education and projects first, for a first job'], creative: ['Creative', 'A coloured header band, the rest plain'],
    elegant: ['Elegant', 'Serif throughout, centred, thin rules'], bold: ['Bold', 'A large name and heavy headings'],
    fresh: ['Fresh', 'Teal headings on a light band'], heritage: ['Heritage', 'Burgundy and serif, a double rule'],
    developer: ['Developer', 'Monospace type, for engineers'], timeline: ['Timeline', 'Dates and time in each job on the left'],
    minimal: ['Minimal', 'Light lines and space, for design and product'], accent: ['Accent', 'Navy name and headings, for sales and business'] };
  var fmtRow = function () {
    return '<div class="fmtrow"><span>Text size</span><button class="btn ghost sm" type="button" data-fs="-1" aria-label="Smaller text">A−</button><b id="rb-fs">' + sizeNow() + '</b><button class="btn ghost sm" type="button" data-fs="1" aria-label="Larger text">A+</button>'
      + '<span>Spacing</span><button class="btn ghost sm" type="button" data-lh="-0.05" aria-label="Less space between lines">−</button><b id="rb-lh">' + (data.lh || 1.5).toFixed(2) + '</b><button class="btn ghost sm" type="button" data-lh="0.05" aria-label="More space between lines">+</button></div>';
  };
  var sizeNow = function () { var pv = $('rb-preview'); return data.fs || (pv ? parseFloat(getComputedStyle(pv).getPropertyValue('--fs')) || 14 : 14); };
  var nameOf = function (list, v) { return (list.filter(function (x) { return x[0] === v; })[0] || ['', ''])[1]; };
  /* Finish up: what the page will look like, and the downloads. The template, colour, font and paper are chosen under Design. */
  var finishUp = function () {
    return '<span class="flabel">Your design</span><p class="rb-dnote"><b>' + esc(TPL_NAMES[data.tpl][0]) + '</b> template'
      + (data.col ? ', ' + esc(nameOf(COLS, data.col)).toLowerCase() + ' headings' : '') + (data.font ? ', ' + esc(nameOf(FONTS, data.font)) : '') + ', ' + PAPER[paperOf(data)][2] + ' paper. '
      + '<button class="linkbtn" type="button" data-mode="design">Change the design</button></p>'
      + '<p class="note">One page is what most recruiters read: if the sheet runs over, make the text a little smaller under Design or cut older jobs to a line each.</p>'
      + '<p class="rsec-dl"><button class="btn primary" type="button" id="rb-print2">Download PDF</button><button class="btn ghost" type="button" id="rb-doc2">Word</button></p>'
      + '<p class="note">Both are free, with no account and no watermark. “Download PDF” opens your browser’s print window: choose “Save as PDF”.</p>' + myJobsBox();
  };
  /* Design: the templates as small pictures of this resume (or of an example while the form is empty), the colour, the font, the size
     and the paper. Every choice is saved with the resume and changes the page at once. */
  var SAMPLE = { name: 'Morgan Lee', title: 'Customer Success Manager', email: 'morgan.lee@example.com', phone: '(555) 010-0144', place: 'Denver, CO', links: 'linkedin.com/in/morgan-lee-example',
    summary: 'Customer success manager with six years in B2B software. Keeps 120 accounts growing: renewals at 94% and expansion revenue up 31% last year.',
    skills: 'Account management, Onboarding, Renewals, Salesforce, Gainsight, SQL, Training',
    exp: [{ role: 'Customer Success Manager', org: 'Brightpath Software', dates: 'Mar 2022 – now', text: 'Kept renewals at 94% across 120 mid-market accounts worth $6.8M a year\nCut onboarding time from 45 days to 28 with a shared launch plan\nGrew expansion revenue 31% in 2025 by running quarterly business reviews' },
      { role: 'Account Coordinator', org: 'Northside Media', dates: 'Jun 2019 – Feb 2022', text: 'Handled 40 client accounts and their monthly reports\nTrained 6 new coordinators on the reporting tools' }],
    edu: [{ what: 'B.A. in Communication', org: 'University of Colorado', dates: '2019' }], proj: [], cert: [], lang: [] };
  var drawDesign = function () {
    var el = $('rb-design'); if (!el || el.hidden) return;
    var src = hasContent(data) ? data : SAMPLE;
    el.innerHTML = '<span class="flabel">Template</span><div class="tplgal">' + TPLS.map(function (t) {
        return '<div class="tplcard' + (data.tpl === t ? ' on' : '') + '" data-pick="' + t + '"><div class="tplsheet" aria-hidden="true"><div data-mini="' + t + '">' + sheetHtml(src, t) + '</div></div>'
          + '<button type="button" class="tpln" data-pick="' + t + '" aria-pressed="' + (data.tpl === t) + '" title="' + esc(TPL_NAMES[t][1]) + '"><b>' + TPL_NAMES[t][0] + '</b></button></div>';
      }).join('') + '</div><p class="rb-dnote" id="rb-tplnote"></p>'
      + '<span class="flabel">Colour of the headings</span><div class="rb-swatch" role="group" aria-label="Colour of the headings">' + COLS.map(function (c) {
        return '<button type="button" data-col="' + c[0] + '"' + (c[0] ? ' style="background:' + c[0] + '"' : ' class="none"') + ' aria-pressed="' + ((data.col || '') === c[0]) + '" aria-label="' + esc(c[1]) + '" title="' + esc(c[1]) + '"></button>';
      }).join('') + '</div>'
      + '<span class="flabel">Font</span><div class="rb-dsel" role="group" aria-label="Font">' + FONTS.map(function (f) {
        return '<button type="button" data-font="' + f[0] + '" aria-pressed="' + ((data.font || '') === f[0]) + '">' + esc(f[0] ? f[1] : 'The template’s own') + '</button>'; }).join('') + '</div>'
      + '<span class="flabel">Size and spacing</span>' + fmtRow()
      + '<span class="flabel">Paper</span><div class="rb-dsel" role="group" aria-label="Paper size">' + ['letter', 'a4'].map(function (p) {
        return '<button type="button" data-paper="' + p + '" aria-pressed="' + (paperOf(data) === p) + '">' + (p === 'letter' ? 'US Letter' : 'A4') + '</button>'; }).join('') + '</div>'
      + '<p class="rb-dnote">Letter is the size used in the US and Canada, A4 in most other countries. Every template is one column of real text with standard headings, the layout screening software reads best.</p>'
      + '<p class="rsec-dl"><button class="btn primary" type="button" id="rb-print3">Download PDF</button><button class="btn ghost" type="button" id="rb-doc3">Word</button></p>';
    restyleDesign();
  };
  var restyleDesign = function () {             // after a choice: the pictures, the pressed buttons and the line about the template, without drawing them again
    var el = $('rb-design'); if (!el || el.hidden || !el.firstChild) return;
    Array.prototype.forEach.call(el.querySelectorAll('[data-mini]'), function (m) { styleSheet(m, data, m.getAttribute('data-mini')); });
    var press = function (sel, attr, v) { Array.prototype.forEach.call(el.querySelectorAll(sel), function (b) { b.setAttribute('aria-pressed', String(b.getAttribute(attr) === v)); }); };
    press('button[data-pick]', 'data-pick', data.tpl); press('[data-col]', 'data-col', data.col || ''); press('[data-font]', 'data-font', data.font || ''); press('[data-paper]', 'data-paper', paperOf(data));
    var n = $('rb-tplnote');
    if (n) n.innerHTML = '<b>' + esc(TPL_NAMES[data.tpl][0]) + ':</b> ' + esc(TPL_NAMES[data.tpl][1]) + '. <a href="' + H.base + '/resume-templates/' + data.tpl + '/">What it suits</a>';
    if ($('rb-fs')) $('rb-fs').textContent = sizeNow();
    if ($('rb-lh')) $('rb-lh').textContent = (data.lh || 1.5).toFixed(2);
  };
  var mode = H.get('hrn_rb_mode', 'content'); if (mode !== 'design') mode = 'content';
  var drawMode = function () {
    var m = $('rb-mode'); if (!m) return;
    m.innerHTML = '<button type="button" role="tab" data-mode="content" aria-selected="' + (mode === 'content') + '" aria-controls="rb-form">Content</button>'
      + '<button type="button" role="tab" data-mode="design" aria-selected="' + (mode === 'design') + '" aria-controls="rb-design">Design</button>';
    $('rb-tabs').hidden = $('rb-form').hidden = mode !== 'content';
    if ($('rb-design')) $('rb-design').hidden = mode !== 'design';
  };
  var setMode = function (m) {
    mode = m === 'design' ? 'design' : 'content'; H.set('hrn_rb_mode', mode); drawMode(); drawDesign();
    var left = document.querySelector('.rb-left'); if (left && left.getBoundingClientRect().top < 0) left.scrollIntoView({ behavior: 'smooth', block: 'start' });
  };
  var linesOf = function (t) { return String(t || '').split('\n').map(function (l) { return l.replace(/^[-•*\s]+/, '').trim(); }).filter(Boolean); };
  var ulOf = function (t) { var lines = linesOf(t); return lines.length ? '<ul>' + lines.map(function (l) { return '<li>' + esc(l) + '</li>'; }).join('') + '</ul>' : ''; };
  // "Jan 2021 – Mar 2023", "2019–2021", "03/2020 – present", "2022 – now" -> months spent (the last month counts), or 0
  var MON = { jan: 1, feb: 2, mar: 3, apr: 4, may: 5, jun: 6, jul: 7, aug: 8, sep: 9, oct: 10, nov: 11, dec: 12 };
  var ym = function (t, end) {
    t = String(t || '').trim().toLowerCase();
    if (/now|present|current|today/.test(t)) { var d = new Date(); return [d.getFullYear(), d.getMonth() + 1]; }
    var m = t.match(/(\d{1,2})\s*[\/.]\s*(\d{4})/); if (m) return [+m[2], +m[1]];
    m = t.match(/([a-z]{3})[a-z]*\.?\s+(\d{4})/); if (m && MON[m[1]]) return [+m[2], MON[m[1]]];
    m = t.match(/(\d{4})/); if (m) return [+m[1], end ? 12 : 1];
    return null;
  };
  var range = function (dates) {          // [first month, last month] as month numbers since year 0, or null
    var parts = String(dates || '').split(/\s*(?:–|—|-|\bto\b)\s*(?=[a-z0-9])/i);
    if (parts.length < 2) return null;
    var a = ym(parts[0], false), b = ym(parts[parts.length - 1], true);
    if (!a || !b) return null;
    var r = [a[0] * 12 + a[1], b[0] * 12 + b[1]];
    return r[1] >= r[0] && r[1] - r[0] < 600 ? r : null;
  };
  var months = function (dates) { var r = range(dates); return r ? r[1] - r[0] + 1 : 0; };
  var union = function (rs) {             // total months worked, overlapping jobs counted once (as hh.ru counts experience)
    rs = rs.filter(Boolean).sort(function (x, y) { return x[0] - y[0]; });
    var n = 0, cur = null;
    rs.forEach(function (r) { if (cur && r[0] <= cur[1] + 1) cur[1] = Math.max(cur[1], r[1]); else { if (cur) n += cur[1] - cur[0] + 1; cur = r.slice(); } });
    return cur ? n + cur[1] - cur[0] + 1 : n;
  };
  var span = function (n) {
    var y = Math.floor(n / 12), m = n % 12;
    return (y ? y + (y === 1 ? ' yr' : ' yrs') : '') + (y && m ? ' ' : '') + (m ? m + (m === 1 ? ' mo' : ' mos') : '');
  };
  /* The sheet's HTML for a resume d in template tpl: the preview, the pictures under Design and the Word file use it (and build.py's
     sheet_html() writes the same markup for the template gallery). '' when there is nothing to show. */
  var sheetHtml = function (d, tpl) {
    var contact = [d.email, d.phone, d.place].concat(String(d.links || '').split(',').map(function (s) { return s.trim(); })).filter(Boolean).map(esc).join(' · ');
    var tl = tpl === 'timeline', spans = [];
    var exp = d.exp.filter(function (x) { return x.role || x.org || x.text; }).map(function (x) {
      if (tl) {
        var n = months(x.dates); spans.push(range(x.dates));
        return '<div class="pv-item pv-tl"><div class="pv-when">' + esc(x.dates) + (n ? '<span>' + span(n) + '</span>' : '') + '</div><div class="pv-what">'
          + (x.org ? '<strong>' + esc(x.org) + '</strong>' : '') + (x.role ? '<b>' + esc(x.role) + '</b>' : '') + ulOf(x.text) + '</div></div>';
      }
      return '<div class="pv-item"><div class="pv-top"><strong>' + esc(x.role) + (x.org ? ', ' + esc(x.org) : '') + '</strong><span>' + esc(x.dates) + '</span></div>' + ulOf(x.text) + '</div>';
    }).join('');
    var proj = d.proj.filter(function (x) { return x.name || x.text; }).map(function (x) {
      return '<div class="pv-item"><div class="pv-top"><strong>' + esc(x.name) + '</strong><span>' + esc(x.link) + '</span></div>' + ulOf(x.text) + '</div>';
    }).join('');
    var cert = d.cert.filter(function (x) { return x.name; }).map(function (x) {
      return '<div class="pv-item"><div class="pv-top"><strong>' + esc(x.name) + (x.org ? ', ' + esc(x.org) : '') + '</strong><span>' + esc(x.date) + '</span></div></div>';
    }).join('');
    var lang = d.lang.filter(function (x) { return x.name; }).map(function (x) { return esc(x.name) + (x.level ? ' (' + esc(x.level) + ')' : ''); });
    var edu = d.edu.filter(function (x) { return x.what || x.org; }).map(function (x) {
      return '<div class="pv-item"><div class="pv-top"><strong>' + esc(x.what) + (x.org ? ', ' + esc(x.org) : '') + '</strong><span>' + esc(x.dates) + '</span></div></div>';
    }).join('');
    var skills = String(d.skills || '').split(',').map(function (s) { return s.trim(); }).filter(Boolean);
    if (!(d.name || d.title || contact || exp || edu || skills.length || proj || cert || lang.length || d.interests)) return '';
    var S = { summary: d.summary ? '<h3>Summary</h3><p>' + esc(d.summary) + '</p>' : '',
      exp: exp ? '<h3>Experience' + (tl && union(spans) ? ' <small>' + span(union(spans)) + '</small>' : '') + '</h3>' + exp : '',
      proj: proj ? '<h3>Projects</h3>' + proj : '', edu: edu ? '<h3>Education</h3>' + edu : '', cert: cert ? '<h3>Certifications</h3>' + cert : '',
      skills: skills.length ? '<h3>Skills</h3>' + (tl ? '<p class="pv-tags">' + skills.map(function (k) { return '<span>' + esc(k) + '</span>'; }).join('') + '</p>' : '<p>' + skills.map(esc).join(' · ') + '</p>') : '',
      lang: lang.length ? '<h3>Languages</h3><p>' + lang.join(' · ') + '</p>' : '', interests: d.interests ? '<h3>Interests</h3><p>' + esc(d.interests) + '</p>' : '' };
    // the Student template puts what a first job is judged by first: school, then projects, then any work
    var order = tpl === 'student' ? ['summary', 'edu', 'proj', 'exp', 'skills', 'cert', 'lang', 'interests'] : ['summary', 'exp', 'proj', 'edu', 'cert', 'skills', 'lang', 'interests'];
    return '<div class="pv-head"><h2 class="pv-name">' + esc(d.name || 'Your name') + '</h2>' + (d.title ? '<p class="pv-title">' + esc(d.title) + '</p>' : '') +
      (contact ? '<p class="pv-contact">' + contact + '</p>' : '') + '</div>' + order.map(function (k) { return S[k]; }).join('');
  };
  var drawPreview = function () {
    $('rb-preview').innerHTML = sheetHtml(data, data.tpl)
      // the empty sheet: one sentence and one way out (an example to start from), not a blank box with a grey line
      || '<div class="pane-empty"><p>Start typing on the left. Your resume appears here.</p><p class="no-print"><a class="btn ghost sm" href="' + H.base + '/resume/examples/">Open an example to start from</a></p></div>';
    applyTpl(); paginate();
  };
  /* The sheet is a real page: Letter or A4 with half-inch margins (the PDF gets the same through @page), zoomed to fit the column or as
     the visitor sets it. The page count is measured on the sheet itself, and a dashed line shows where each next page starts. */
  var zoomPref = H.get('hrn_rb_zoom', 'fit'), ZOOMS = [0.35, 0.5, 0.65, 0.8, 1, 1.25], pageAt = 1, nPages = 1;
  if (zoomPref !== 'fit' && ZOOMS.indexOf(zoomPref) < 0) zoomPref = 'fit';
  var pageCss = function () {
    var st = $('rb-page-css');
    if (!st) { st = document.createElement('style'); st.id = 'rb-page-css'; document.head.appendChild(st); }
    st.textContent = '@page{size:' + (paperOf(data) === 'a4' ? 'A4' : 'letter') + ';margin:0.5in}';
  };
  var zoomNow = function () {
    var box = $('rb-pbox'), W = PAPER[paperOf(data)][0];
    if (zoomPref !== 'fit' || !box) return zoomPref === 'fit' ? 1 : zoomPref;
    var cs = getComputedStyle(box), inner = box.clientWidth - parseFloat(cs.paddingLeft) - parseFloat(cs.paddingRight);
    return Math.max(0.25, Math.min(1, Math.floor(inner / W * 100) / 100));
  };
  var paginate = function () {
    var pv = $('rb-preview'); if (!pv) return;
    var pp = PAPER[paperOf(data)], CH = pp[1] - 2 * MARGIN;
    pageCss();
    Array.prototype.forEach.call(pv.querySelectorAll('.pv-break'), function (x) { x.remove(); });
    pv.style.zoom = 1; pv.style.width = pp[0] + 'px'; pv.style.minHeight = '';
    nPages = Math.max(1, Math.ceil((pv.scrollHeight - 2 * MARGIN - 2) / CH));
    pv.style.minHeight = (nPages * CH + 2 * MARGIN) + 'px';
    for (var k = 1; k < nPages; k++) {
      var b = document.createElement('div'); b.className = 'pv-break no-print'; b.setAttribute('aria-hidden', 'true');
      b.style.top = (MARGIN + k * CH) + 'px'; b.innerHTML = '<span>Page ' + (k + 1) + ' starts here</span>'; pv.appendChild(b);
    }
    pv.style.zoom = zoomNow(); drawBar();
  };
  var drawBar = function () {
    var bar = $('rb-pvbar'); if (!bar) return;
    pageAt = Math.max(1, Math.min(pageAt, nPages));
    bar.innerHTML = '<span class="grp"><button type="button" data-pg="-1" aria-label="Previous page"' + (pageAt <= 1 ? ' disabled' : '') + '>‹</button>'
      + '<span>Page <b>' + pageAt + '</b> of ' + nPages + '</span><button type="button" data-pg="1" aria-label="Next page"' + (pageAt >= nPages ? ' disabled' : '') + '>›</button></span>'
      + (nPages > 1 ? '<span class="over">' + nPages + ' pages: shorten older jobs, or make the text smaller under Design</span>' : '<span>Fits on one page · ' + PAPER[paperOf(data)][2] + '</span>')
      + '<span class="grp"><button type="button" data-zoom="-1" aria-label="Zoom out">−</button><b>' + Math.round(zoomNow() * 100) + '%</b>'
      + '<button type="button" data-zoom="1" aria-label="Zoom in">+</button><button type="button" data-zoom="fit"' + (zoomPref === 'fit' ? ' aria-pressed="true"' : '') + '>Fit</button></span>';
  };
  var zoomBy = function (v) {
    if (v === 'fit') zoomPref = 'fit';
    else { var z = zoomNow(), i = ZOOMS.filter(function (x) { return v > 0 ? x > z + 0.001 : x < z - 0.001; }); zoomPref = i.length ? (v > 0 ? i[0] : i[i.length - 1]) : (v > 0 ? ZOOMS[ZOOMS.length - 1] : ZOOMS[0]); }
    H.set('hrn_rb_zoom', zoomPref); $('rb-preview').style.zoom = zoomNow(); drawBar();
  };
  var goPage = function (step) {
    pageAt = Math.max(1, Math.min(nPages, pageAt + step)); drawBar();
    var pv = $('rb-preview'), to = pageAt === 1 ? pv : pv.querySelectorAll('.pv-break')[pageAt - 2];
    if (to) to.scrollIntoView({ behavior: 'smooth', block: 'start' });
  };
  var rtimer;
  window.addEventListener('resize', function () { clearTimeout(rtimer); rtimer = setTimeout(function () { if (zoomPref === 'fit') { $('rb-preview').style.zoom = zoomNow(); drawBar(); } }, 150); });
  if (document.fonts && document.fonts.ready) document.fonts.ready.then(function () { paginate(); });       // the page count with the real fonts
  // a Word file: the same page as simple HTML, which Word opens and saves as .docx
  // The same resume in the open JSON Resume format (jsonresume.org): a file other tools and AI assistants can read
  var jsonFile = function () {
    var out = window.HRNT.toJsonResume(data);
    var a = document.createElement('a');
    a.href = URL.createObjectURL(new Blob([JSON.stringify(out, null, 2)], { type: 'application/json' }));
    a.download = (data.name ? data.name.replace(/[^A-Za-z0-9]+/g, '-').replace(/^-|-$/g, '') : 'resume') + '.json';
    document.body.appendChild(a); a.click(); a.remove(); setTimeout(function () { URL.revokeObjectURL(a.href); }, 2000);
  };
  // the template's look in Word's terms: its font, its accent colour, a centred header where the template centres it
  var SERIF = { classic: 1, executive: 1, professional: 1, elegant: 1, heritage: 1 };
  var TAC = { accent: '#1f3a68', professional: '#2d3a4a', student: '#2b5d8a', creative: '#1f4e5f', fresh: '#0f6b6b', heritage: '#7a1f2b', elegant: '#333333' };
  var wordFile = function () {
    var t = data.tpl, ac = data.col || TAC[t] || '#111111';
    var ff = { inter: 'Inter,Arial,sans-serif', arial: 'Arial,sans-serif', georgia: 'Georgia,serif', times: '"Times New Roman",serif' }[data.font]
      || (SERIF[t] ? 'Georgia,serif' : t === 'developer' ? 'Consolas,monospace' : t === 'simple' ? 'Arial,sans-serif' : 'Calibri,Arial,sans-serif');
    var pt = ((data.fs || 14) * 11 / 14).toFixed(1);          // 14 CSS px on the sheet is 11 pt in Word
    var css = 'body{font-family:' + ff + ';font-size:' + pt + 'pt;line-height:' + (data.lh || 1.4) + ';color:#111}' +
      'h2{font-size:20pt;margin:0;color:' + (/^(accent|professional|fresh|heritage|creative)$/.test(t) ? ac : '#111') + '}' +
      'h3{font-size:10pt;text-transform:uppercase;letter-spacing:1pt;color:' + ac + ';border-bottom:1px solid ' + ac + ';margin:14pt 0 6pt}p{margin:0 0 5pt}ul{margin:3pt 0 0}.pv-top span{color:#555}' +
      (/^(executive|elegant)$/.test(t) ? '.pv-head p,.pv-head h2{text-align:center}' : '') + (t === 'minimal' ? 'h3{border-bottom-color:#ccc;color:#444;font-weight:normal}' : '') +
      (t === 'simple' ? 'h3{text-transform:none;letter-spacing:0;border:0;font-size:11pt}' : '') + (t === 'professional' ? 'h3{font-variant:small-caps;text-transform:none;font-size:12pt}' : '');
    var html = '<html xmlns:o="urn:schemas-microsoft-com:office:office" xmlns:w="urn:schemas-microsoft-com:office:word"><head><meta charset="utf-8"><title>Resume</title><style>' + css + '</style></head><body>' +
      sheetHtml(data, t).replace(/<div class="pv-top"><strong>(.*?)<\/strong><span>(.*?)<\/span><\/div>/g, '<p><strong>$1</strong> &nbsp; <span>$2</span></p>')
        .replace(/<div class="pv-item pv-tl"><div class="pv-when">(.*?)<\/div><div class="pv-what">(.*?)<\/div><\/div>/g,
                 '<table width="100%" style="margin:0 0 8pt"><tr><td width="27%" valign="top" style="color:#555;font-size:10pt">$1</td><td valign="top">$2</td></tr></table>') + '</body></html>';
    var a = document.createElement('a');
    a.href = URL.createObjectURL(new Blob(['﻿' + html], { type: 'application/msword' }));
    a.download = (data.name ? data.name.replace(/[^\w\- ]+/g, '').trim().replace(/\s+/g, '-') + '-' : '') + 'resume.doc';
    document.body.appendChild(a); a.click(); a.remove();
  };
  root.addEventListener('change', function (ev) { if (ev.target.id === 'rb-tpl') { data.tpl = ev.target.value; save(); drawPreview(); } });      // a template can change the markup (Timeline), not only the style
  var htimer, stimer;
  root.addEventListener('input', function (ev) {
    var t = ev.target, blk = t.closest('.rblock');
    if (blk && t.getAttribute('data-f')) {
      var lk = blk.getAttribute('data-list'), item = data[lk][Number(blk.getAttribute('data-i'))];
      if (!item) return;
      item[t.getAttribute('data-f')] = t.value;
      var hb = blk.querySelector('.rbh-box');
      if (t.tagName === 'TEXTAREA' && t.scrollHeight > t.clientHeight + 2) t.style.height = Math.min(t.scrollHeight + 4, 420) + 'px';      // the box grows with the lines
      if (hb && t.getAttribute('data-f') === 'text') { clearTimeout(htimer); htimer = setTimeout(function () { hb.innerHTML = hintsHtml(t.value); }, 350); }
    } else if (t.getAttribute('data-k')) {
      var k = t.getAttribute('data-k'); data[k] = t.value;
      if (k === 'summary' && $('rb-sumc')) $('rb-sumc').textContent = sumCount();
      if (k === 'title' && / \(copy\)$/.test(curItem().label || '')) { curItem().label = ''; keepSet(); }        // a copy renamed by its new headline
      if (k === 'title' || k === 'name') { var o = document.querySelector('#rb-which option[value="' + SET.cur + '"]'); if (o) o.textContent = labelOf(curItem()); }
      if (k === 'title' || k === 'skills') { clearTimeout(stimer); stimer = setTimeout(drawSug, 400); }
    } else return;
    save(); drawPreview();
  });
  root.addEventListener('change', function (ev) { if (ev.target.id === 'rb-which') openItem(ev.target.value); });
  root.addEventListener('click', function (ev) {
    var t = ev.target, add = t.getAttribute('data-add'), del = t.getAttribute('data-del');
    if (add && LISTS[add]) {
      data[add].push(emptyOf(add)); save(); drawForm(); drawPreview();
      var nb = document.querySelector('#rb-form [data-list="' + add + '"][data-i="' + (data[add].length - 1) + '"] input'); if (nb) nb.focus();
    }
    else if (del && LISTS[del]) { data[del].splice(Number(t.closest('.rblock').getAttribute('data-i')), 1); if (!data[del].length && blank[del].length) data[del] = copy(blank[del]); save(); drawForm(); drawPreview(); }
    else if (t.closest && t.closest('[data-tone]')) {
      tone = t.closest('[data-tone]').getAttribute('data-tone'); H.set('hrn_rb_tone', tone);
      Array.prototype.forEach.call(document.querySelectorAll('[data-tone]'), function (b) { var on = b.getAttribute('data-tone') === tone; b.setAttribute('aria-checked', on); b.setAttribute('aria-pressed', on); });
      if (chk) drawCheck();
    }
    else if (t.getAttribute('data-asksum')) {                 // copy the request; the link then opens the assistant in a new tab
      var done = $('rb-sum-done');
      if (!data.exp.some(function (x) { return x.role || x.text; })) { ev.preventDefault(); done.textContent = 'Add at least one job first: the assistant writes the summary from your experience.'; done.hidden = false; return; }
      var ask = window.HRNT.summaryAsk(cutText(asText(), 2400), tone, jd ? cutText(jd, 1600) : '');
      copyText(ask, function () { done.textContent = 'Copied. Paste it in the assistant’s message box (Ctrl+V or ⌘V).'; done.hidden = false; });
    }
    else if (t.id === 'rb-new') { if (addResume({ name: data.name, email: data.email, phone: data.phone, place: data.place, links: data.links, tpl: data.tpl })) { setTab('contact'); redraw(); } }
    else if (t.id === 'rb-dup') { var src = copy(data), lb = labelOf(curItem()); if (addResume(src, lb + ' (copy)', jd)) redraw(); }
    else if (t.id === 'rb-ren') { H.askText(t, 'Name this resume (only you see the name):', labelOf(curItem()), 'Save the name').then(function (nm) { if (nm != null) { curItem().label = nm.trim().slice(0, 60); keepSet(); drawSet(); } }); }
    else if (t.id === 'rb-delr') {
      if (SET.items.length < 2) return;
      H.sure(t, 'Delete “' + labelOf(curItem()) + '” from this browser? The other resumes stay.', 'Delete').then(function (ok) {
        if (!ok) return;
        SET.items = SET.items.filter(function (x) { return x.id !== SET.cur; });
        var nx = SET.items[0]; data = fill(nx.data); setJd(nx.jd); delete nx.data; delete nx.jd; SET.cur = nx.id; keepSet(); save(); redraw();
      });
    }
    else if (t.closest && t.closest('[data-tab]')) setTab(t.closest('[data-tab]').getAttribute('data-tab'));
    else if (t.closest && t.closest('[data-pick]')) { data.tpl = t.closest('[data-pick]').getAttribute('data-pick'); save(); drawPreview(); restyleDesign(); }
    else if (t.closest && t.closest('[data-mode]')) setMode(t.closest('[data-mode]').getAttribute('data-mode'));
    else if (t.hasAttribute('data-col')) { var c_ = t.getAttribute('data-col'); if (c_) data.col = c_; else delete data.col; save(); applyTpl(); paginate(); restyleDesign(); }
    else if (t.hasAttribute('data-font')) { var f_ = t.getAttribute('data-font'); if (f_) data.font = f_; else delete data.font; save(); applyTpl(); paginate(); restyleDesign(); }
    else if (t.hasAttribute('data-paper')) { data.paper = t.getAttribute('data-paper'); save(); paginate(); restyleDesign(); }
    else if (t.getAttribute('data-fs')) { data.fs = Math.max(10.5, Math.min(16, sizeNow() + Number(t.getAttribute('data-fs')) * 0.5)); save(); applyTpl(); paginate(); restyleDesign(); }
    else if (t.getAttribute('data-lh')) { data.lh = Math.max(1.2, Math.min(1.8, Math.round(((data.lh || 1.5) + Number(t.getAttribute('data-lh'))) * 100) / 100)); save(); applyTpl(); paginate(); restyleDesign(); }
    else if (t.getAttribute('data-zoom')) { var z_ = t.getAttribute('data-zoom'); zoomBy(z_ === 'fit' ? 'fit' : Number(z_)); }
    else if (t.getAttribute('data-pg')) goPage(Number(t.getAttribute('data-pg')));
    else if (t.getAttribute('data-addline') != null && sugLines[+t.getAttribute('data-addline')]) addLine(sugLines[+t.getAttribute('data-addline')]);
    else if (t.closest && t.closest('#rb-scratch')) { var ti = document.querySelector('#rb-form [data-k="title"]'); if (ti) ti.focus(); }
    else if (t.id === 'rb-print' || t.id === 'rb-print2' || t.id === 'rb-print3') window.print();
    else if (t.id === 'rb-doc2' || t.id === 'rb-doc3') wordFile();
    else if (t.id === 'rb-doc') wordFile();
    else if (t.id === 'rb-myjobs') {
      var mj = $('rb-myjobs-n'), txt = asText();
      if (!hasContent(data)) { mj.textContent = 'Fill in the resume first.'; return; }
      H.cvSkillsOf(txt).catch(function () { return []; }).then(function (sk) {
        var kept = H.cvSave({ id: 'rb-' + SET.cur, name: labelOf(curItem()), title: data.title || '', text: txt, skills: sk });
        mj.innerHTML = kept ? 'Kept in <a href="' + H.base + '/my-jobs/#resumes">My jobs</a>' + (sk.length ? ', with ' + sk.length + ' skills it names' : '') + '. Save again after a change to update it.'
          : 'My jobs keeps five resumes, and five are there: <a href="' + H.base + '/my-jobs/#resumes">remove one</a> first.';
      });
    }
    else if (t.id === 'rb-json') jsonFile();
    else if (t.id === 'rb-exgo') {
      var pick = ($('rb-expick').value || '').trim().toLowerCase();
      exList().then(function (all) {
        var slug_ = Object.keys(all).filter(function (k) { return (all[k].title || '').toLowerCase() === pick || k === pick; })[0] ||
                    Object.keys(all).filter(function (k) { return (all[k].title || '').toLowerCase().indexOf(pick) >= 0; })[0];
        if (slug_) location.href = location.pathname + '?example=' + slug_;
        else { $('rb-expick').setCustomValidity('No example with these words: try another job.'); $('rb-expick').reportValidity(); setTimeout(function () { $('rb-expick').setCustomValidity(''); }, 2500); }
      });
    }
    else if (t.id === 'rb-paste') { var pb = $('rb-pastebox'); pb.hidden = !pb.hidden; if (!pb.hidden) $('rb-pastetext').focus(); }
    else if (t.id === 'rb-pasteread') { var txt = $('rb-pastetext').value; if (txt.trim()) useImport(window.HRNT.parseResume(txt), 'the pasted text'); }
    else if (t.id === 'rb-clear') { H.sure(t, 'Erase this resume from this browser?', 'Erase').then(function (ok) { if (ok) { data = fill({ tpl: data.tpl }); save(); drawForm(); drawPreview(); } }); }
    else if (t.id === 'rb-match') {
      var text = [data.title, data.summary, data.skills].concat(data.exp.map(function (x) { return x.role + ' ' + x.text; }), data.proj.map(function (x) { return x.name + ' ' + x.text; })).join('\n');
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
    var pj = data.proj.filter(function (x) { return x.name || x.text; });
    if (pj.length) { L.push('', 'Projects'); pj.forEach(function (x) { L.push([x.name, x.link].filter(Boolean).join(', ')); linesOf(x.text).forEach(function (l) { L.push('- ' + l); }); }); }
    var ce = data.cert.filter(function (x) { return x.name; });
    if (ce.length) { L.push('', 'Certifications'); ce.forEach(function (x) { L.push([x.name, x.org, x.date].filter(Boolean).join(', ')); }); }
    var la = data.lang.filter(function (x) { return x.name; });
    if (la.length) L.push('', 'Languages: ' + la.map(function (x) { return x.name + (x.level ? ' (' + x.level + ')' : ''); }).join(', '));
    if (data.interests) L.push('', 'Interests: ' + data.interests);
    return L.join('\n');
  };
  var drawCheck = function () {
    var T = window.HRNT;
    if (!chk || !T) return;
    var text = asText(), r = T.resumeReview(text), html = '<div class="rbc-score">';
    if (r.error) html += '<p class="rbc-h"><b>Resume score</b> after 80 words</p><p class="note">You have ' + r.words + ' so far. Add your jobs with one result each, and the score appears here.</p>';
    else {
      var v = Math.round(r.score * 10), col = v >= 85 ? 'var(--ac)' : v >= 65 ? '#d4a017' : '#d9534f', len = Math.PI * 80;
      html += '<div class="gauge"><svg viewBox="0 0 200 112" aria-hidden="true"><path d="M20 100 A80 80 0 0 1 180 100" fill="none" stroke="var(--line)" stroke-width="16" stroke-linecap="round"/>'
        + '<path d="M20 100 A80 80 0 0 1 180 100" fill="none" stroke="' + col + '" stroke-width="16" stroke-linecap="round" stroke-dasharray="' + (len * v / 100).toFixed(1) + ' ' + len.toFixed(1) + '"/></svg>'
        + '<p><b>' + v + '</b><span>' + (v >= 90 ? 'Excellent' : v >= 75 ? 'Good' : v >= 50 ? 'Fair' : 'Needs work') + '</span></p></div>'
        + '<ul class="gcat">' + r.checks.map(function (c) { var p = c.max ? Math.round(100 * c.points / c.max) : 0; return '<li><span>' + esc(c.name) + '</span><i><em style="width:' + p + '%"></em></i><b>' + p + '</b></li>'; }).join('') + '</ul>'
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
        + (m.missing.length ? '<p class="note">Skills the posting names and this resume does not. Add only the ones you have:</p><p class="rbc-add">' + chips(m.missing.slice(0, 12)) + '</p>'
          : '<p class="note">Every skill the posting names is in this resume.</p>')
        + (m.terms.filter(function (t) { return !t.found; }).length ? '<p class="note">Its repeated words you do not use yet: ' + m.terms.filter(function (t) { return !t.found; }).slice(0, 6).map(function (t) { return '“' + esc(t.term) + '”'; }).join(', ') + '.</p>' : '');
    }
    html += '<details class="rbc-jd"' + (jd ? '' : ' open') + '><summary>' + (jd ? 'Change the posting' : 'Paste a posting') + '</summary><textarea id="rb-jd" rows="5" aria-label="The job posting to match your resume to" placeholder="Paste the full text of the job posting">' + esc(jd) + '</textarea>'
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
  /* Skills for the job title, as hh.ru suggests them after the profession is chosen: here from the example of the closest kind of
     work, whose skills come from today's postings. Each is one button away from the skills line. */
  var exAll = null;
  function exList() { return exAll ? Promise.resolve(exAll) : fetch(H.base + '/data/resume-examples.json').then(function (r) { return r.json(); }).then(function (d) { exAll = d; return d; }); }
  root.addEventListener('focusin', function (ev) {
    if (ev.target.id !== 'rb-expick' || $('rb-exlist').options.length) return;
    exList().then(function (all) { $('rb-exlist').innerHTML = Object.keys(all).map(function (k) { return '<option value="' + esc(all[k].title || k) + '">'; }).join(''); }).catch(function () {});
  });
  // skills the visitor said no to are not offered again (plan item 4.7: the suggestions had "+" and no way to set one aside)
  function skipped() { return H.get('hrn_rb_skip', []) || []; }
  function chips(list) {
    var no = skipped().map(function (x) { return String(x).toLowerCase(); });
    return list.filter(function (x) { return no.indexOf(String(x).toLowerCase()) < 0; }).map(function (x) {
      return '<span class="rb-chip"><button class="chipbtn" type="button" data-addskill="' + esc(x) + '">+ ' + esc(x) + '</button><button class="rb-skip" type="button" data-skipskill="' + esc(x) + '" aria-label="Skip ' + esc(x) + '" title="Not mine: do not suggest it again">×</button></span>';
    }).join('');
  }
  /* The target job (27 Nov 2026, from CVMaker's "desired job title"): under the title, the skills today's postings for that work ask for
     most (data/role-skills.json, counted by build.py, with the number of postings) and lines to start from, taken from our example for that
     work with every number left as [number] for the visitor to fill in. One click adds a skill to the skills line or a line to the first job. */
  var roleSk, sugEx, sugAsked, sugLines = [], sugMsg = '';
  function needSug() {
    if (sugAsked || !window.fetch) return;
    sugAsked = true;
    Promise.all([fetch(H.base + '/data/role-skills.json').then(function (r) { return r.json(); }).catch(function () { return null; }), exList().catch(function () { return null; })])
      .then(function (r) { roleSk = (r[0] && r[0].roles) || []; sugEx = r[1] || {}; drawSug(); });
  }
  function words(s) {
    return String(s || '').toLowerCase().split(/[^a-z0-9+#]+/).filter(function (w) { return w.length > 1; })
      .map(function (w) { return w.length > 3 ? w.replace(/ies$/, 'y').replace(/s$/, '') : w; });
  }
  // words that name a level or a kind of job title rather than the work: "SEO Specialist" is SEO work, not "specialist" work
  var GENERIC = { and: 1, of: 1, the: 1, for: 1, in: 1, manager: 1, specialist: 1, engineer: 1, analyst: 1, associate: 1, assistant: 1, senior: 1, junior: 1, lead: 1, staff: 1,
    principal: 1, head: 1, director: 1, officer: 1, coordinator: 1, representative: 1, consultant: 1, technician: 1, developer: 1, designer: 1, administrator: 1, intern: 1,
    executive: 1, worker: 1, operator: 1, supervisor: 1, professional: 1, expert: 1 };
  function bestOf(title, items) {        // items [key, name, postings, …]: the share of the name's words found in the title, at least one of them about the work itself
    var t = words(title), best = null;
    if (!t.length) return null;
    items.forEach(function (it) {
      var w = words(it[1]).filter(function (x) { return x !== 'and' && x !== 'of' && x !== 'the' && x !== 'for' && x !== 'in'; });
      var m = w.filter(function (x) { return t.indexOf(x) >= 0; });
      if (!m.length || !m.some(function (x) { return !GENERIC[x]; })) return;
      var sc = m.length / w.length + m.length / 100;
      if (!best || sc > best.sc || (sc === best.sc && (it[2] || 0) > best.w)) best = { key: it[0], name: it[1], w: it[2] || 0, sc: sc, it: it };
    });
    return best;
  }
  function placeholders(l) {             // "from 480 ms to 190 ms", "41%", "$6.8M" -> "from [number] ms to [number] ms", "[number]%", "$[number]M"
    return l.replace(/([$€£])?\d+(?:[.,]\d+)*(\s?(?:%|[KkMmBb]\b))?/g, function (m, cur, unit) { return (cur || '') + '[number]' + (unit || ''); });
  }
  function sugHtml(skillsOnly) {
    if (!roleSk || !sugEx) return '';
    var title = String(data.title || '');
    if (title.replace(/\s/g, '').length < 3) return skillsOnly ? '' : '<p class="note">Type the job you want: the skills employers ask for in it and lines to start from appear here.</p>';
    var rs = bestOf(title, roleSk), ex = bestOf(title, Object.keys(sugEx).map(function (k) { return [k, sugEx[k].title || '', 0]; }));
    if (!ex && rs && sugEx[rs.key]) ex = { key: rs.key, name: sugEx[rs.key].title || rs.name };
    if (!rs && !ex) return skillsOnly ? '' : '<p class="note">No suggestions for “' + esc(title) + '” yet. Try the usual name of the job, for example “Data Analyst” or “Registered Nurse”.</p>';
    var seen = {}, list = [], mineSk = String(data.skills || '').toLowerCase();
    // a skill already in the skills line, or inside one of its items ("SEO" in "technical SEO"), is not offered again
    var haveSk = function (k) { try { return new RegExp('(^|[^a-z0-9+#])' + k.replace(/[.*+?^${}()|[\]\\]/g, '\\$&') + '($|[^a-z0-9+#])').test(mineSk); } catch (e) { return false; } };
    (rs ? rs.it[3].map(function (x) { return x[0]; }) : []).concat(ex && sugEx[ex.key].skills ? String(sugEx[ex.key].skills).split(',') : []).forEach(function (x) {
      x = String(x).trim(); var k = x.toLowerCase();
      if (x && !seen[k] && !haveSk(k)) { seen[k] = 1; list.push(x); }
    });
    var low = function (n) { return String(n).replace(/\b([A-Z])([a-z]+)\b/g, function (m) { return m.toLowerCase(); }); };      // "SEO Manager" -> "SEO manager"
    var ch = chips(list.slice(0, 12)), out = '';
    if (ch) out += '<p><b>Skills employers ask for in ' + esc(low(rs ? rs.name : ex.name)) + ' jobs</b>'
      + (rs ? ' <span class="note">(counted in ' + Number(rs.w).toLocaleString('en-US') + ' open postings)</span>' : '') + '. Add the ones you have:</p><p class="rbc-add">' + ch + '</p>';
    if (!skillsOnly && ex) {
      var mine = {};
      data.exp.forEach(function (x) { String(x.text || '').split('\n').forEach(function (l) { mine[l.trim()] = 1; }); });
      sugLines = [];
      (sugEx[ex.key].exp || []).forEach(function (j) {
        String(j.text || '').split('\n').forEach(function (l) { l = placeholders(l.trim()); if (l && !mine[l] && sugLines.indexOf(l) < 0) sugLines.push(l); });
      });
      sugLines = sugLines.slice(0, 5);
      if (sugLines.length) out += '<p><b>Lines to start from</b>, written for our ' + esc(low(ex.name)) + ' example. One goes into your first job; change each [number] to your own:</p><ul class="rb-lines">'
        + sugLines.map(function (l, i) { return '<li><button type="button" data-addline="' + i + '">' + esc(l) + '</button></li>'; }).join('') + '</ul>';
      out += '<p class="note">' + (sugMsg ? '<b>' + sugMsg + '</b> ' : '') + '<a href="' + H.base + '/resume/examples/' + ex.key + '/">The whole ' + esc(low(ex.name)) + ' resume example</a></p>';
    }
    return out;
  }
  /* "Save this resume to My jobs" (27 Nov 2026): My jobs keeps up to five resumes (hrn_resumes, written by site.js cvSave), and the
     "Fits you" marks on every job list count the skills of the primary one. The resume keeps one place there however often it is saved. */
  function myJobsBox() {
    if (!H.cvSave || !H.cvSkillsOf) return '';
    return '<p class="note rb-myj"><button class="btn ghost sm" type="button" id="rb-myjobs">Save this resume to My jobs</button> '
      + '<span id="rb-myjobs-n">Its skills then count in the “Fits you” marks on job lists. Kept in this browser.</span></p>';
  }
  function drawSug() { var a = $('rb-tsug'), b = $('rb-ssug'); if (a) a.innerHTML = sugHtml(false); if (b) b.innerHTML = sugHtml(true); }
  function addLine(l) {
    if (!data.exp.length) data.exp.push(emptyOf('exp'));
    var j = data.exp[0]; j.text = (String(j.text || '').replace(/\s+$/, '') + '\n' + l).replace(/^\n/, '');
    sugMsg = 'Added to your first job under Experience.';
    save(); drawForm(); drawPreview(); sugMsg = '';
  }
  var aiAsks = [];
  var aiLine = function (text) {
    if (String(text).replace(/\s+/g, ' ').trim().length < 60) return '';
    var cv = cutText(text, 2400), post = cutText(jd, 1600), T = window.HRNT, toneName = (T.TONES.filter(function (x) { return x[0] === tone; })[0] || [0, 'Plain'])[1];
    var asks = [
      ['Rewrite my bullet points', 'Rewrite the bullet points of my resume below. Start each with a strong past-tense verb, keep one result per line, and add a number where my text gives one. Do not invent facts, numbers or employers: where a number is missing, write [number] for me to fill in.\n\nMY RESUME:\n' + cv],
      ['Write my summary' + (tone !== 'plain' ? ' (' + toneName.toLowerCase() + ')' : ''), T.summaryAsk(cv, tone, '')]];
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
    drawPreview = function () { drawPreview0(); drawTabs(); clearTimeout(ptimer); ptimer = setTimeout(drawCheck, 500); };      // any change to the resume (typing, an example, a skill added) updates the score
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
        var done = $('rb-ai-done');
        copyText(aiAsks[+ai][1], function () { if (done) done.hidden = false; });
        return;
      }
      var skip = ev.target.getAttribute && ev.target.getAttribute('data-skipskill');
      if (skip) { var sk = skipped(); if (sk.indexOf(skip) < 0) sk.push(skip); H.set('hrn_rb_skip', sk.slice(-200)); drawCheck(); return; }
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
  var demandOk = false;                 // on a phone the count waits for a tap: it reads the list of every open job (22 MB; site.js heavyOk)
  if (demand) demand.addEventListener('click', function (ev) { if (ev.target && ev.target.id === 'rbd-go') { demandOk = true; drawDemand(); } });
  function drawDemand() {
    if (!demand || !H.load) return;
    var text = [data.title, data.summary, data.skills].concat(data.exp.map(function (x) { return x.role + ' ' + x.text; }), data.proj.map(function (x) { return x.name + ' ' + x.text; })).join('\n');
    if (text.replace(/\s/g, '').length < 20) { demand.innerHTML = ''; return; }
    (pats ? Promise.resolve(pats) : fetch(H.base + '/data/skills.json').then(function (r) { return r.json(); }).then(function (p) { pats = p; return p; })).then(function (p) {
      var mine = []; p.forEach(function (x) { try { if (new RegExp(x[1], 'i').test(text)) mine.push(x[0]); } catch (e) {} });
      if (!mine.length) { demand.innerHTML = '<p class="note">No skill that employers name in postings was found in this resume yet. Write the tools and methods you use by their names.</p>'; return; }
      if (!demandOk && H.heavyOk && !H.heavyOk()) {
        demand.innerHTML = '<p class="note">How many open jobs ask for the ' + mine.length + (mine.length === 1 ? ' skill' : ' skills') + ' in this resume, and which one skill would add the most: counted from every open job, ' +
          'which means downloading the whole list (about 22 MB). <button class="btn sm" type="button" id="rbd-go">Count them</button></p>';
        return;
      }
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
  /* ?tpl=<id>: "Use this template" on /resume-templates/ opens the builder with that template, keeping whatever is already written. */
  var tq = ''; try { tq = new URLSearchParams(location.search).get('tpl') || ''; } catch (e) {}
  if (TPLS.indexOf(tq) >= 0) {
    data.tpl = tq; save(); applyTpl(); drawPreview(); restyleDesign();
    if (!exq) try { history.replaceState(null, '', location.pathname); } catch (e) {}
    var tn = document.createElement('div'), rbf = document.getElementById('rb');
    tn.className = 'banner ok rb-opened'; tn.setAttribute('role', 'status');
    tn.innerHTML = 'Template: <b>' + esc(TPL_NAMES[tq][0]) + '</b>. ' + (hasContent(data) ? 'Your resume is shown in it.' : 'Fill in the form; the page takes its look as you type.')
      + ' Change the template, colour or font any time under Design.';
    if (rbf && rbf.parentNode) rbf.parentNode.insertBefore(tn, rbf);
  }
  /* A file dropped anywhere on the builder is read like "Upload my resume". */
  var dragN = 0;
  root.addEventListener('dragenter', function (ev) { if (ev.dataTransfer && [].indexOf.call(ev.dataTransfer.types || [], 'Files') >= 0) { dragN++; root.classList.add('drag'); } });
  root.addEventListener('dragleave', function () { if (--dragN <= 0) { dragN = 0; root.classList.remove('drag'); } });
  root.addEventListener('dragover', function (ev) { if (root.classList.contains('drag')) ev.preventDefault(); });
  root.addEventListener('drop', function (ev) {
    dragN = 0; root.classList.remove('drag');
    var f = ev.dataTransfer && ev.dataTransfer.files && ev.dataTransfer.files[0];
    if (f) { ev.preventDefault(); if (mode !== 'content') setMode('content'); setTab('contact'); readFile(f); }
  });
  if (exq) fetch(H.base + '/data/resume-examples.json').then(function (r) { return r.json(); }).then(function (all) {
    var ex = all[exq]; if (!ex) return;
    var kept = hasContent(data);
    if (kept) {                                             // a resume in progress is never replaced: the example opens as another resume, no question asked
      if (!addResume(Object.assign({ tpl: data.tpl }, ex), (ex.title || 'Example') + ' (example)')) return;
    } else { data = fill(Object.assign({ tpl: data.tpl }, copy(ex))); save(); }
    redraw();
    try { history.replaceState(null, '', location.pathname); } catch (e) {}
    // say what happened and bring the form into view (owner, 15 Nov 2026: "nothing happened" when the example opened below the fold)
    var form = document.getElementById('rb'), note = document.createElement('div');
    note.className = 'banner ok rb-opened'; note.setAttribute('role', 'status');
    note.innerHTML = 'Opened the example: <b>' + H.esc(ex.title || 'resume') + '</b>. Replace the details with yours, then download it.' +
      (kept ? ' Your own resume is kept: pick it in “Your resume”.' : '');
    if (form && form.parentNode) { form.parentNode.insertBefore(note, form); note.scrollIntoView({ behavior: 'smooth', block: 'start' }); }
  }).catch(function () {});
})();

/* "Save to my account": once signed in (the header keeps the session in this browser), the resume being edited is kept as a version in
   the account, up to ten, and opens on any device from the account's Resumes. */
(function () {
  var bar = document.querySelector('#rb .rb-actions'); if (!bar) return;
  // the sign-in is read when it is needed, not once: signing out in the header (site.js says so with "hrn:auth") changes the button at once
  var signedIn = function () { try { return JSON.parse(localStorage.getItem('hrn_token')) || ''; } catch (e) { return ''; } };
  var b = document.createElement('button'); b.type = 'button'; b.className = 'btn ghost'; b.id = 'rb-acc';
  var label = function () { b.textContent = signedIn() ? 'Save to my account' : 'Sign in to keep it in your account'; };
  label(); document.addEventListener('hrn:auth', label);
  bar.appendChild(b);
  b.addEventListener('click', function () {
    var base = (window.HRN && window.HRN.base) || '', token = signedIn();
    if (!token) { location.href = base + '/account/'; return; }
    var data = null; try { data = JSON.parse(localStorage.getItem('hrn_resume')); } catch (e) {}
    if (!data) { b.textContent = 'Fill in the resume first'; return; }
    b.disabled = true; b.textContent = 'Saving…';
    var title = ((data.basics && (data.basics.title || data.basics.name)) || data.title || 'My resume');
    // the API's own address (the header link carries it; site.js keeps it in HRN.api): the same site in production, another port on a developer's machine
    fetch(((window.HRN && window.HRN.api) || location.origin) + '/api/resumes', { method: 'POST', headers: { 'Content-Type': 'application/json', Authorization: 'Bearer ' + token },
      body: JSON.stringify({ name: String(title).slice(0, 50) + ' · ' + new Date().toISOString().slice(0, 10), resume: data }) })
      .then(function (r) { return r.json().catch(function () { return {}; }).then(function (x) { return { ok: r.ok, x: x }; }); })
      .then(function (res) {
        b.disabled = false;
        b.textContent = res.ok ? 'Saved to your account ✓' : (res.x && res.x.message) || 'Could not save: try again';
        if (res.ok) setTimeout(function () { b.textContent = 'Save to my account'; }, 4000);
      }, function () { b.disabled = false; b.textContent = 'No connection: try again'; });
  });
})();

/* The template gallery (/resume-templates/) and a template's own page: each picture is the sheet at its real width (816 px), zoomed to
   the width of its frame, and the filters show the templates for one experience level and one style. */
(function () {
  var pics = document.querySelectorAll('.tg-pic'); if (!pics.length) return;
  var fit = function () { Array.prototype.forEach.call(pics, function (a) { var w = a.clientWidth; if (w) a.style.setProperty('--z', (w / 816).toFixed(4)); }); };
  fit(); window.addEventListener('resize', fit);
  var f = document.getElementById('tg-filter'), none = document.getElementById('tg-none'); if (!f) return;
  f.hidden = false;
  var lvl = '', sty = '';
  var has = function (c, attr, v) { return !v || (' ' + c.getAttribute(attr) + ' ').indexOf(' ' + v + ' ') >= 0; };
  var apply = function () {
    var n = 0;
    Array.prototype.forEach.call(document.querySelectorAll('#tg-grid .tg-card'), function (c) { var ok = has(c, 'data-lvl', lvl) && has(c, 'data-sty', sty); c.hidden = !ok; if (ok) n++; });
    if (none) none.hidden = n > 0;
    Array.prototype.forEach.call(f.querySelectorAll('[data-tgl]'), function (b) { b.setAttribute('aria-pressed', String(b.getAttribute('data-tgl') === lvl)); });
    Array.prototype.forEach.call(f.querySelectorAll('[data-tgs]'), function (b) { b.setAttribute('aria-pressed', String(b.getAttribute('data-tgs') === sty)); });
    fit();
  };
  document.addEventListener('click', function (ev) {
    var b = ev.target && ev.target.closest && ev.target.closest('[data-tgl],[data-tgs],[data-tgall]'); if (!b) return;
    if (b.hasAttribute('data-tgall')) lvl = sty = ''; else if (b.hasAttribute('data-tgl')) lvl = b.getAttribute('data-tgl'); else sty = b.getAttribute('data-tgs');
    apply();
  });
})();
