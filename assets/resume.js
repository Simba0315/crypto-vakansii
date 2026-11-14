/* Resume builder: everything stays in this browser (localStorage). "Download PDF" uses the browser's print dialog. */
(function () {
  var root = document.getElementById('rb'); if (!root) return;
  var H = window.HRN, esc = H.esc, $ = function (id) { return document.getElementById(id); };
  var blank = { name: '', title: '', email: '', phone: '', place: '', links: '', summary: '', skills: '', exp: [{ role: '', org: '', dates: '', text: '' }], edu: [{ what: '', org: '', dates: '' }],
    proj: [], cert: [], lang: [] };
  var copy = function (x) { return JSON.parse(JSON.stringify(x)); };
  var TPLS = ['classic', 'modern', 'compact', 'developer', 'executive'];
  var fill = function (d) {                                                         // a damaged, old or foreign value must not break the builder
    if (!d || typeof d !== 'object' || Array.isArray(d)) d = {};
    Object.keys(blank).forEach(function (k) {
      if (Array.isArray(blank[k]) ? !Array.isArray(d[k]) || (!d[k].length && blank[k].length) : typeof d[k] !== 'string') d[k] = copy(blank[k]);
      else if (Array.isArray(d[k])) d[k] = d[k].filter(function (x) { return x && typeof x === 'object'; });
    });
    if (TPLS.indexOf(d.tpl) < 0) d.tpl = 'classic';
    return d;
  };
  var data = fill(H.get('hrn_resume', null));
  /* Several resumes, one per kind of job: the open one stays in hrn_resume, which the other pages read; the others, with the posting
     each was aimed at, wait in hrn_resume_set. */
  var SET = H.get('hrn_resume_set', null);
  if (!SET || typeof SET !== 'object' || !Array.isArray(SET.items) || !SET.items.length) SET = { cur: 'r1', items: [{ id: 'r1', label: '' }] };
  SET.items = SET.items.filter(function (x) { return x && typeof x.id === 'string'; }).slice(0, 30);
  if (!SET.items.length) SET.items = [{ id: 'r1', label: '' }];
  if (!SET.items.some(function (x) { return x.id === SET.cur; })) SET.cur = SET.items[0].id;
  var applyTpl = function () {
    var pv = $('rb-preview'), sel = $('rb-tpl'); pv.className = 'tpl-' + data.tpl; if (sel) sel.value = data.tpl;
    pv.style.fontSize = data.fs ? data.fs + 'px' : ''; pv.style.lineHeight = data.lh ? String(data.lh) : '';
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
    var exp = listOf('exp'), edu = listOf('edu');
    var sec = function (id, inner) { return '<div class="rsec' + (tab === id ? ' on' : '') + '" data-sec="' + id + '">' + inner + nextBtn(id) + '</div>'; };
    $('rb-form').innerHTML =
      sec('contact', '<div class="rb-imp no-print"><p><b>Already have a resume?</b><span>Word, PDF, text or JSON Resume: it is read in this browser, nothing is uploaded.</span></p>' +
        '<p class="rb-imp-a"><label class="btn ghost sm">Import a file<input type="file" id="rb-file" accept=".docx,.pdf,.txt,.md,.json" hidden></label>' +
        '<button class="linkbtn" type="button" id="rb-paste">or paste the text</button></p>' +
        '<div id="rb-pastebox" hidden><textarea id="rb-pastetext" rows="7" placeholder="Paste the whole resume as text: name, contacts, experience, education, skills"></textarea>' +
        '<p><button class="btn sm" type="button" id="rb-pasteread">Read it</button></p></div>' +
        (impMsg ? '<p class="note rb-impmsg" role="status">' + impMsg + '</p>' : '') + '</div>' +
        '<span class="flabel">About you</span>' + field('Full name', 'name', 'text', 'Alex Morgan') + field('Headline: the job you want', 'title', 'text', 'Senior Backend Engineer') +
        '<div class="rrow">' + field('Email', 'email', 'text', 'you@example.com') + field('Phone', 'phone', 'text', '+1 555 010 0199') + '</div>' +
        '<div class="rrow">' + field('Location', 'place', 'text', 'Berlin, Germany · open to remote') + field('Links', 'links', 'text', 'github.com/you, linkedin.com/in/you') + '</div>') +
      sec('summary', field('Summary', 'summary', 'area', 'Two or three sentences: what you do, for how long, and what you are best at.') + '<p class="note rb-sumc" id="rb-sumc">' + sumCount() + '</p>' + sumAI()) +
      sec('experience', '<span class="flabel">Experience</span>' + exp) +
      sec('education', '<span class="flabel">Education</span>' + edu) +
      sec('skills', '<span class="flabel">Skills</span>' + field('Comma-separated', 'skills', 'text', 'Python, PostgreSQL, AWS, Kubernetes')) +
      sec('more', '<p class="note rb-more-n">Each of these is optional: a section with nothing in it is left off the page.</p>'
        + '<span class="flabel">Projects</span>' + listOf('proj') + '<span class="flabel">Certificates and licences</span>' + listOf('cert')
        + '<span class="flabel">Languages</span>' + listOf('lang')
        + '<datalist id="rb-levels"><option value="Native"><option value="Fluent"><option value="Professional"><option value="Conversational"><option value="Basic"><option value="C2"><option value="C1"><option value="B2"><option value="B1"><option value="A2"></datalist>') +
      sec('finish', finishUp());
    drawTabs(); drawSet();
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
  var useImport = function (r, how) {
    if (!r || !(r.name || r.summary || r.skills || r.exp.length)) { impMsg = 'Nothing could be read from ' + esc(how) + '. Paste the text instead, or fill in the form.'; drawForm(); return; }
    if (hasContent(data)) {
      if (!confirm('Open the resume from ' + how + ' as a new resume? The one you have now stays in the list above the form.')) return;
      if (!addResume({ tpl: data.tpl })) return;
    }
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
    if (SET.items.length >= 20) { alert('Twenty resumes is the limit here. Delete one you no longer use first.'); return false; }
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
      : id === 'more' ? data.proj.some(function (x) { return x.name || x.text; }) || data.cert.some(function (x) { return x.name; }) || data.lang.some(function (x) { return x.name; }) : false;
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
  /* Finish up: the template gallery with small pictures, and the format (size and spacing), saved with the resume. */
  var TPL_NAMES = { classic: ['Classic', 'Serif, calm, for any field'], modern: ['Modern', 'Clean sans-serif, a bar on each heading'], compact: ['Compact', 'Fits more on one page'],
    developer: ['Developer', 'Monospace headings, for engineers'], executive: ['Executive', 'Centred name, for senior roles'] };
  var finishUp = function () {
    return '<span class="flabel">Template</span><div class="tplgal">' + TPLS.map(function (t) {
        return '<button type="button" class="tplcard' + (data.tpl === t ? ' on' : '') + '" data-pick="' + t + '"><span class="tplmini tpl-' + t + '"><b>Alex Example</b><i></i><i class="s"></i><u></u><i></i><i class="s"></i></span>'
          + '<span class="tpln"><b>' + TPL_NAMES[t][0] + '</b><span>' + TPL_NAMES[t][1] + '</span></span></button>';
      }).join('') + '</div>'
      + '<span class="flabel">Format</span><div class="fmtrow"><span>Text size</span><button class="btn ghost sm" type="button" data-fs="-1">A−</button><b id="rb-fs">' + (data.fs || 14) + '</b><button class="btn ghost sm" type="button" data-fs="1">A+</button>'
      + '<span>Spacing</span><button class="btn ghost sm" type="button" data-lh="-0.05">−</button><b id="rb-lh">' + (data.lh || 1.5).toFixed(2) + '</b><button class="btn ghost sm" type="button" data-lh="0.05">+</button></div>'
      + '<p class="note">One page is what most recruiters read: if the sheet runs over, make the text a little smaller or cut older jobs to a line each.</p>'
      + '<p class="rsec-dl"><button class="btn primary" type="button" id="rb-print2">Download PDF</button><button class="btn ghost" type="button" id="rb-doc2">Word</button></p>';
  };
  var linesOf = function (t) { return String(t || '').split('\n').map(function (l) { return l.replace(/^[-•*\s]+/, '').trim(); }).filter(Boolean); };
  var ulOf = function (t) { var lines = linesOf(t); return lines.length ? '<ul>' + lines.map(function (l) { return '<li>' + esc(l) + '</li>'; }).join('') + '</ul>' : ''; };
  var drawPreview = function () {
    var contact = [data.email, data.phone, data.place].concat(String(data.links || '').split(',').map(function (s) { return s.trim(); })).filter(Boolean).map(esc).join(' · ');
    var exp = data.exp.filter(function (x) { return x.role || x.org || x.text; }).map(function (x) {
      return '<div class="pv-item"><div class="pv-top"><strong>' + esc(x.role) + (x.org ? ', ' + esc(x.org) : '') + '</strong><span>' + esc(x.dates) + '</span></div>' + ulOf(x.text) + '</div>';
    }).join('');
    var proj = data.proj.filter(function (x) { return x.name || x.text; }).map(function (x) {
      return '<div class="pv-item"><div class="pv-top"><strong>' + esc(x.name) + '</strong><span>' + esc(x.link) + '</span></div>' + ulOf(x.text) + '</div>';
    }).join('');
    var cert = data.cert.filter(function (x) { return x.name; }).map(function (x) {
      return '<div class="pv-item"><div class="pv-top"><strong>' + esc(x.name) + (x.org ? ', ' + esc(x.org) : '') + '</strong><span>' + esc(x.date) + '</span></div></div>';
    }).join('');
    var lang = data.lang.filter(function (x) { return x.name; }).map(function (x) { return esc(x.name) + (x.level ? ' (' + esc(x.level) + ')' : ''); });
    var edu = data.edu.filter(function (x) { return x.what || x.org; }).map(function (x) {
      return '<div class="pv-item"><div class="pv-top"><strong>' + esc(x.what) + (x.org ? ', ' + esc(x.org) : '') + '</strong><span>' + esc(x.dates) + '</span></div></div>';
    }).join('');
    var skills = String(data.skills || '').split(',').map(function (s) { return s.trim(); }).filter(Boolean);
    $('rb-preview').innerHTML = (data.name || data.title || contact || exp || edu || skills.length || proj || cert || lang.length)
      ? '<h2 class="pv-name">' + esc(data.name || 'Your name') + '</h2>' + (data.title ? '<p class="pv-title">' + esc(data.title) + '</p>' : '') +
        (contact ? '<p class="pv-contact">' + contact + '</p>' : '') + (data.summary ? '<h3>Summary</h3><p>' + esc(data.summary) + '</p>' : '') +
        (exp ? '<h3>Experience</h3>' + exp : '') + (proj ? '<h3>Projects</h3>' + proj : '') + (edu ? '<h3>Education</h3>' + edu : '') + (cert ? '<h3>Certifications</h3>' + cert : '') +
        (skills.length ? '<h3>Skills</h3><p>' + skills.map(esc).join(' · ') + '</p>' : '') + (lang.length ? '<h3>Languages</h3><p>' + lang.join(' · ') + '</p>' : '')
      : '<p class="pane-empty">Start typing on the left. Your resume appears here.</p>';
    applyTpl();
  };
  // a Word file: the same page as simple HTML, which Word opens and saves as .docx
  // The same resume in the open JSON Resume format (jsonresume.org): a file other tools and AI assistants can read
  var jsonFile = function () {
    var out = window.HRNT.toJsonResume(data);
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
  var htimer;
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
    else if (t.id === 'rb-ren') { var nm = prompt('Name this resume (only you see the name):', labelOf(curItem())); if (nm != null) { curItem().label = nm.trim().slice(0, 60); keepSet(); drawSet(); } }
    else if (t.id === 'rb-delr') {
      if (SET.items.length < 2 || !confirm('Delete “' + labelOf(curItem()) + '” from this browser? The other resumes stay.')) return;
      SET.items = SET.items.filter(function (x) { return x.id !== SET.cur; });
      var nx = SET.items[0]; data = fill(nx.data); setJd(nx.jd); delete nx.data; delete nx.jd; SET.cur = nx.id; keepSet(); save(); redraw();
    }
    else if (t.closest && t.closest('[data-tab]')) setTab(t.closest('[data-tab]').getAttribute('data-tab'));
    else if (t.closest && t.closest('[data-pick]')) { data.tpl = t.closest('[data-pick]').getAttribute('data-pick'); save(); applyTpl(); }
    else if (t.getAttribute('data-fs')) { data.fs = Math.max(11, Math.min(16, (data.fs || 14) + Number(t.getAttribute('data-fs')) * 0.5)); save(); applyTpl(); $('rb-fs').textContent = data.fs; }
    else if (t.getAttribute('data-lh')) { data.lh = Math.max(1.2, Math.min(1.8, Math.round(((data.lh || 1.5) + Number(t.getAttribute('data-lh'))) * 100) / 100)); save(); applyTpl(); $('rb-lh').textContent = data.lh.toFixed(2); }
    else if (t.id === 'rb-print' || t.id === 'rb-print2') window.print();
    else if (t.id === 'rb-doc2') wordFile();
    else if (t.id === 'rb-doc') wordFile();
    else if (t.id === 'rb-json') jsonFile();
    else if (t.id === 'rb-paste') { var pb = $('rb-pastebox'); pb.hidden = !pb.hidden; if (!pb.hidden) $('rb-pastetext').focus(); }
    else if (t.id === 'rb-pasteread') { var txt = $('rb-pastetext').value; if (txt.trim()) useImport(window.HRNT.parseResume(txt), 'the pasted text'); }
    else if (t.id === 'rb-clear') { if (confirm('Erase this resume from this browser?')) { data = fill({ tpl: data.tpl }); save(); drawForm(); drawPreview(); } }
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
        + (m.missing.length ? '<p class="note">Skills the posting names and this resume does not. Add only the ones you have:</p><p class="rbc-add">' + m.missing.slice(0, 12).map(function (s) { return '<button class="chipbtn" type="button" data-addskill="' + esc(s) + '">+ ' + esc(s) + '</button>'; }).join('') + '</p>'
          : '<p class="note">Every skill the posting names is in this resume.</p>')
        + (m.terms.filter(function (t) { return !t.found; }).length ? '<p class="note">Its repeated words you do not use yet: ' + m.terms.filter(function (t) { return !t.found; }).slice(0, 6).map(function (t) { return '“' + esc(t.term) + '”'; }).join(', ') + '.</p>' : '');
    }
    html += '<details class="rbc-jd"' + (jd ? '' : ' open') + '><summary>' + (jd ? 'Change the posting' : 'Paste a posting') + '</summary><textarea id="rb-jd" rows="5" placeholder="Paste the full text of the job posting">' + esc(jd) + '</textarea>'
      + (jd ? '<button class="linkbtn" type="button" id="rb-jd-clear">Remove the posting</button>' : '') + '</details></div>' + titleSkills() + payLine(text) + aiLine(text);
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
  var roleEx = null, roleAsked = false;
  var titleSkills = function () {
    var t = String(data.title || '').toLowerCase();
    if (t.replace(/\s/g, '').length < 3) return '';
    if (!roleEx) {
      if (!roleAsked && window.fetch) { roleAsked = true; fetch(H.base + '/data/resume-examples.json').then(function (r) { return r.json(); }).then(function (d) { roleEx = d; drawCheck(); }).catch(function () {}); }
      return '';
    }
    var best = null, bestN = 0;
    Object.keys(roleEx).forEach(function (k) {
      var words = String(roleEx[k].title || '').toLowerCase().split(/[^a-z0-9+#]+/).filter(function (w) { return w.length > 1; });
      if (!words.length || words.some(function (w) { return t.indexOf(w) < 0; })) return;
      if (words.length > bestN) { best = k; bestN = words.length; }
    });
    if (!best) return '';
    var have = {}; String(data.skills || '').split(',').forEach(function (x) { x = x.trim().toLowerCase(); if (x) have[x] = 1; });
    var miss = String(roleEx[best].skills || '').split(',').map(function (x) { return x.trim(); }).filter(function (x) { return x && !have[x.toLowerCase()]; }).slice(0, 10);
    if (!miss.length) return '';
    return '<div class="rbc-sk"><p class="rbc-h"><b>Skills</b> employers ask for in ' + esc(roleEx[best].title) + ' jobs today</p><p class="note">Add the ones you have:</p><p class="rbc-add">'
      + miss.map(function (x) { return '<button class="chipbtn" type="button" data-addskill="' + esc(x) + '">+ ' + esc(x) + '</button>'; }).join('') + '</p></div>';
  };
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
    var text = [data.title, data.summary, data.skills].concat(data.exp.map(function (x) { return x.role + ' ' + x.text; }), data.proj.map(function (x) { return x.name + ' ' + x.text; })).join('\n');
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
    if (hasContent(data)) {                                 // a resume in progress is never replaced: the example opens as another resume
      if (!confirm('Open the example as a new resume? The one you have now stays in the list above the form.')) return;
      if (!addResume(Object.assign({ tpl: data.tpl }, ex), (ex.title || 'Example') + ' (example)')) return;
    } else { data = fill(Object.assign({ tpl: data.tpl }, copy(ex))); save(); }
    redraw();
    try { history.replaceState(null, '', location.pathname); } catch (e) {}
  }).catch(function () {});
})();
