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
})();
