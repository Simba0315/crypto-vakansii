/* Node tests for the "posted 20 minutes ago" labels in assets/site.js. Usage: node fresh_test.js [path to site.js]
   site.js is one browser script, so the functions under test are cut out of it by name and run here against a small stand-in for the page. */
const fs = require('fs'), path = require('path');
const src = fs.readFileSync(path.resolve(process.argv[2] || path.join(__dirname, 'assets', 'site.js')), 'utf8');
function cut(name) {            // a top-level function of site.js: one line, or "  function name(" up to its closing "  }"
  const at = src.indexOf('\n  function ' + name + '(');
  if (at < 0) throw new Error('site.js has no function ' + name);
  const first = src.slice(at + 1, src.indexOf('\n', at + 1));
  if (first.split('{').length === first.split('}').length) return first;
  const end = src.indexOf('\n  }\n', at);
  if (end < 0) throw new Error('site.js: cannot find the end of ' + name);
  return src.slice(at + 1, end + 4);
}
let pass = 0, fail = 0;
function eq(name, got, want) { if (JSON.stringify(got) === JSON.stringify(want)) pass++; else { fail++; console.log('FAIL: ' + name + '  -> ' + JSON.stringify({ got: got, want: want })); } }

/* a stand-in for <time data-t> elements and for the page that holds them */
function el(attrs, text) {
  const a = Object.assign({}, attrs), cls = {};
  return { textContent: text, cls: cls, getAttribute: (k) => (k in a ? a[k] : null), hasAttribute: (k) => k in a, setAttribute: (k, v) => { a[k] = String(v); },
    removeAttribute: (k) => { delete a[k]; }, classList: { add: (c) => { cls[c] = 1; } } };
}
let clock = 1800000000000, page = [];
class Clock extends Date { constructor(...a) { if (a.length) super(...a); else super(clock); } static now() { return clock; } }   // the test sets the time
const doc = { querySelectorAll: (sel) => (sel === 'time[data-t]' ? page : []) };
const S = new Function('document', 'Date', 'P', "var MONTHS = ['Jan','Feb','Mar','Apr','May','Jun','Jul','Aug','Sep','Oct','Nov','Dec'];" +
  'var flagsOk = true; var mySkills = [], cvText = "", cvSkillsLine = {}, haveMemo = {}, knowsSkills = false;' +
  ['esc', 'slugOf', 'hue', 'avatar', 'expand', 'ageOf', 'ago', 'freshen', 'flag', 'flags', 'have', 'skillFit', 'tagPills', 'card'].map(cut).join('\n') +
  '\nreturn { ago: ago, freshen: freshen, expand: expand, card: card };')(doc, Clock, '');
const now = () => Math.floor(clock / 1000);

/* ago(): the words */
eq('under a minute', S.ago(0), 'now');
eq('59 seconds', S.ago(59), 'now');
eq('one minute', S.ago(60), '1 min');
eq('20 minutes', S.ago(20 * 60 + 30), '20 min');
eq('59 minutes', S.ago(3599), '59 min');
eq('one hour', S.ago(3600), '1 h');
eq('3 hours and a half', S.ago(3.5 * 3600), '3 h');
eq('just under a day', S.ago(86399), '23 h');
eq('a day old keeps the day label', S.ago(86400), '');
eq('ten days old', S.ago(864000), '');
eq('in the future is "now", never negative', S.ago(-5), 'now');
eq('far in the future is still "now"', S.ago(-9e6), 'now');
eq('not a number', S.ago(NaN), '');
eq('nothing', S.ago(undefined), '');
eq('sentence: under a minute', S.ago(10, true), 'just now');
eq('sentence: in the future', S.ago(-600, true), 'just now');
eq('sentence: one minute', S.ago(60, true), '1 minute ago');
eq('sentence: 35 minutes', S.ago(35 * 60, true), '35 minutes ago');
eq('sentence: one hour', S.ago(3600, true), '1 hour ago');
eq('sentence: 3 hours', S.ago(3 * 3600 + 59, true), '3 hours ago');
eq('sentence: a day old', S.ago(86400, true), '');
let longest = '', minus = false;
for (let s = -120; s < 86400; s += 30) { const l = S.ago(s); if (l.length > longest.length) longest = l; if (/-/.test(l + S.ago(s, true))) minus = true; }
eq('row labels fit the 44px age column (6 characters of 12px mono): longest is "' + longest + '"', longest.length <= 6, true);
eq('no label has a minus sign', minus, false);

/* freshen(): what happens to the elements */
const row = el({ 'data-t': now() - 20 * 60 }, 'Today'), line = el({ 'data-t': now() - 3 * 3600, 'data-long': '' }, ''), old = el({ 'data-t': now() - 30 * 3600 }, '1d'),
  ahead = el({ 'data-t': now() + 600 }, 'Today'), junk = el({ 'data-t': 'soon' }, 'Today'), empty = el({ 'data-t': '' }, '3d');
page = [row, line, old, ahead, junk, empty];
S.freshen();
eq('a row 20 minutes old', [row.textContent, row.cls.new, row.getAttribute('data-day')], ['20 min', 1, 'Today']);
eq('the job page line, 3 hours old', [line.textContent, line.cls.new], ['3 hours ago', 1]);
eq('30 hours old: left as written, not marked', [old.textContent, old.cls.new, old.hasAttribute('data-day')], ['1d', undefined, false]);
eq('a time in the future', ahead.textContent, 'now');
eq('an unreadable time is left alone', [junk.textContent, junk.cls.new], ['Today', undefined]);
eq('an empty time is left alone', empty.textContent, '3d');
clock += 60000; S.freshen();
eq('a minute later', [row.textContent, row.getAttribute('data-day')], ['21 min', 'Today']);
clock += 40 * 60000; S.freshen();
eq('after an hour', row.textContent, '1 h');
clock += 23 * 3600000; S.freshen();
eq('a day old: the label it was written with comes back', [row.textContent, row.hasAttribute('data-day'), line.textContent], ['Today', false, '']);
const part = el({ 'data-t': now() - 300 }, 'Today');
S.freshen({ querySelectorAll: () => [part] });
eq('works on one part of the page', part.textContent, '5 min');

/* expand() and card(): the index row carries the exact time in minutes, the row's <time> carries it in seconds */
const idx = (rows) => ({ c: ['Acme'], k: ['engineering'], l: ['', 'Intern', 'Junior', 'Senior', 'Lead'], t: ['Python'], p: [], x: [], e: [''], g: [0], r: rows });
const base = [0, 'Engineer', 0, 'Remote', 1, 0, 3, [0], '$100K - $120K', 20270115, 120000, [], [], 0];
const rows = S.expand(idx([base.concat([30000000]), base.concat([0]), base]));
eq('expand keeps the minutes', rows[0][23], 30000000);
eq('expand: 0 stays 0', rows[1][23], 0);
eq('expand: an index written before this field existed', rows[2][23], 0);
eq('card with an exact time', /<time data-t="1800000000"[ >]/.test(S.card(rows[0])), true);
eq('card without one has no data-t', /data-t=/.test(S.card(rows[1]) + S.card(rows[2])), false);


/* skills on your resume / to grow: the resume made in the builder marks a job's skills */
const R = new Function('esc', "var mySkills = ['SQL'], cvText = 'backend engineer\\nbuilt a payments api in python on aws\\ngo-to-market with c++ and node.js', cvSkillsLine = { python: 1, r: 1 }, haveMemo = {}, knowsSkills = true;" +
  ['have', 'tagPills'].map(cut).join('\n') + '\nreturn { have: have, tagPills: tagPills };')(function (x) { return String(x); });
eq('resume: a skill named in the text', [R.have('Python'), R.have('AWS'), R.have('C++'), R.have('Node.js')], [true, true, true, true]);
eq('resume: a skill picked in the answers', R.have('SQL'), true);
eq('resume: a two-letter name only from the skills line ("go-to-market" is not Go)', [R.have('Go'), R.have('R')], [false, true]);
eq('resume: not there', [R.have('Java'), R.have('Kubernetes')], [false, false]);
eq('resume: the skills you have first, the rest "to grow"', R.tagPills(['Go', 'Java', 'Python', 'AWS']),
  '<span class="pill have" title="On your resume">✓ Python</span><span class="pill have" title="On your resume">✓ AWS</span><span class="pill grow" title="To grow: not on your resume yet">Go</span>');
console.log('\n' + pass + ' passed, ' + fail + ' failed');
process.exit(fail ? 1 : 0);
