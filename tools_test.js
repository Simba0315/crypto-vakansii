/* Node tests for the pure logic in assets/tools.js. Usage: node test_tools.js <path to tools.js> [path to skills.json] */
const path = require('path'), fs = require('fs');
const T = require(path.resolve(process.argv[2]));
let pass = 0, fail = 0;
function ok(name, cond, extra) { if (cond) pass++; else { fail++; console.log('FAIL: ' + name + (extra !== undefined ? '  -> ' + JSON.stringify(extra) : '')); } }
function eq(name, a, b) { ok(name, JSON.stringify(a) === JSON.stringify(b), { got: a, want: b }); }
function near(name, a, b, tol) { ok(name, typeof a === 'number' && Math.abs(a - b) <= (tol || 1e-9), { got: a, want: b }); }

/* numbers */
eq('num plain', T.num('85000'), 85000);
eq('num commas', T.num('85,000'), 85000);
eq('num $ and k', T.num('$85k'), 85000);
eq('num m', T.num('1.2m'), 1200000);
eq('num decimal comma', T.num('12,5'), 12.5);
eq('num percent', T.num('5%'), 5);
eq('num spaces', T.num(' 1 250 000 '), 1250000);
ok('num empty is NaN', isNaN(T.num('')));
ok('num junk is NaN', isNaN(T.num('abc')));
ok('num null is NaN', isNaN(T.num(null)));
eq('num negative', T.num('-3.5'), -3.5);
eq('num big commas + decimals', T.num('1,234,567.89'), 1234567.89);
eq('roundTo 1.005', T.roundTo(1.005, 2), 1.01);
eq('roundTo 2.675', T.roundTo(2.675, 2), 2.68);
eq('roundTo -1.005', T.roundTo(-1.005, 2), -1.01);
eq('roundTo tiny negative is 0 not -0', Object.is(T.roundTo(-0.0001, 2), 0), true);
eq('money', T.money(1234.5, '$', 2), '$1,234.50');
eq('money 0 dp', T.money(85000, '$', 0), '$85,000');
eq('money negative', T.money(-1200, '€', 0), '−€1,200');
eq('money NaN', T.money(NaN, '$', 0), '—');
eq('fmt', T.fmt(2080), '2,080');

/* pay converter */
let c = T.convertPay('50', 'hour', '40', '52', '5');
near('hourly 50 -> year', c.year, 104000);
near('hourly 50 -> month', c.month, 104000 / 12);
near('hourly 50 -> week', c.week, 2000);
near('hourly 50 -> day', c.day, 400);
c = T.convertPay('104000', 'year', 40, 52, 5);
near('year -> hour', c.hour, 50);
c = T.convertPay('6000', 'month', 37.5, 52, 5);
near('month -> year', c.year, 72000);
near('month -> hour (37.5h)', c.hour, 72000 / 1950);
c = T.convertPay('600', 'day', 40, 46, 5);
near('day rate, 46 weeks', c.year, 600 * 5 * 46);
near('day rate back to day', c.day, 600);
near('week from day rate', c.week, 3000);
c = T.convertPay('2000', 'week', 40, 52, 4);
near('4-day week: day', c.day, 500);
['hour', 'day', 'week', 'month', 'year'].forEach(function (p) {            // round trip in every unit
  const r = T.convertPay('77.77', p, 35, 48, 5), back = T.convertPay(String(r.year), 'year', 35, 48, 5);
  near('round trip ' + p, back[p], 77.77, 1e-6);
});
eq('converter: empty amount', T.convertPay('', 'hour', 40, 52, 5), null);
eq('converter: zero hours', T.convertPay('50', 'hour', 0, 52, 5), null);
eq('converter: 53 weeks rejected', T.convertPay('50', 'hour', 40, 53, 5), null);
eq('converter: 8 days rejected', T.convertPay('50', 'hour', 40, 52, 8), null);
eq('converter: negative amount', T.convertPay('-5', 'hour', 40, 52, 5), null);
near('converter: zero amount gives zeros', T.convertPay('0', 'hour', 40, 52, 5).year, 0);

/* raise */
let r = T.raise({ current: '50000', pct: '5', by: 'pct', periods: 12 });
near('raise 5% amount', r.amount, 2500); near('raise 5% new', r.next, 52500); near('raise per paycheck diff', r.payDiff, 2500 / 12);
r = T.raise({ current: '85,000', amount: '2550', by: 'amount', periods: 26 });
near('raise amount -> pct', r.pct, 3); near('biweekly before', r.payBefore, 85000 / 26); near('biweekly after', r.payAfter, 87550 / 26);
r = T.raise({ current: '72000', next: '80000', by: 'next', periods: 24 });
near('raise new -> pct', r.pct, 11.11111111, 1e-6); eq('raise pct shown to 2 places', T.plain(r.pct, 2), '11.11'); near('raise new -> amount', r.amount, 8000);
r = T.raise({ current: '60000', pct: '3', by: 'pct', inflation: '4' });
near('real raise below inflation', r.realPct, (1.03 / 1.04 - 1) * 100); ok('real raise negative', r.realPct < 0);
near('real amount', r.realAmount, 61800 / 1.04 - 60000);
r = T.raise({ current: '60000', pct: '0', by: 'pct' });
near('zero raise', r.next, 60000); ok('no inflation -> no real figure', r.realPct === undefined);
r = T.raise({ current: '60000', pct: '-10', by: 'pct' });
near('pay cut', r.next, 54000);
eq('raise: no current', T.raise({ current: '', pct: '5', by: 'pct' }), null);
eq('raise: zero current', T.raise({ current: '0', pct: '5', by: 'pct' }), null);
eq('raise: empty pct', T.raise({ current: '50000', pct: '', by: 'pct' }), null);
eq('raise: new salary below zero', T.raise({ current: '50000', amount: '-60000', by: 'amount' }), null);
eq('percent rounding 1/3', T.plain(T.raise({ current: '30000', amount: '100', by: 'amount' }).pct, 2), '0.33');
eq('percent rounding 4.995 -> 5', T.plain(T.raise({ current: '100000', amount: '4995', by: 'amount' }).pct, 2), '5');
eq('percent rounding 2/3 -> 0.67', T.plain(T.raise({ current: '30000', amount: '200', by: 'amount' }).pct, 2), '0.67');

/* offers */
let o = T.offer({ base: '120000', bonus: '10%', equity: '20000', signon: '15000', match: '4', other: '3000', pto: '25', cdays: '3', ccost: '20' });
near('offer bonus %', o.bonus, 12000); near('offer match', o.match, 4800); eq('offer work days', o.workDays, 235);
near('offer commute', o.commute, 3 * 20 * 235 / 5); near('offer yearly', o.yearly, 120000 + 12000 + 20000 + 4800 + 3000 - 2820);
near('offer first year', o.first, o.yearly + 15000); near('offer per day', o.perDay, o.yearly / 235);
o = T.offer({ base: '100000', bonus: '8000' });
near('offer bonus amount', o.bonus, 8000); near('offer no extras', o.yearly, 108000); eq('offer default work days', o.workDays, 260);
o = T.offer({});
eq('empty offer not filled', o.filled, false); near('empty offer yearly', o.yearly, 0);
o = T.offer({ base: '90000', pto: '400', cdays: '9', ccost: '10', match: '250' });
eq('pto capped', o.workDays, 0); eq('per day with no work days', o.perDay, 0); near('match capped at 100%', o.match, 90000);
let cmp = T.compareOffers([{ name: 'A', base: '100000' }, { name: 'B', base: '95000', bonus: '15%' }, {}]);
eq('compare best', cmp.best, 1); eq('compare count', cmp.count, 2); near('compare lead', cmp.lead, 9250); near('compare lead pct', cmp.leadPct, 9.25);
cmp = T.compareOffers([{ base: '100000', signon: '30000' }, { base: '110000' }]);
eq('best yearly', cmp.best, 1); eq('best first year differs', cmp.bestFirst, 0);
cmp = T.compareOffers([{ base: '100000', pto: '35' }, { base: '104000', pto: '10' }]);
eq('best per working day', cmp.bestDay, 0); eq('best yearly b', cmp.best, 1);
cmp = T.compareOffers([{}, {}]);
eq('compare nothing', cmp.best, -1);
cmp = T.compareOffers([{ base: '100000' }, {}]);
eq('compare single', [cmp.best, cmp.count, cmp.lead], [0, 1, 0]);

/* vesting and options */
eq('vest before cliff', T.vested(48000, 11, 48, 12), 0);
eq('vest at cliff', T.vested(48000, 12, 48, 12), 12000);
eq('vest month 30', T.vested(48000, 30, 48, 12), 30000);
eq('vest fully', T.vested(48000, 60, 48, 12), 48000);
eq('vest rounds down', T.vested(1000, 13, 48, 12), 270);
eq('vest no schedule', T.vested(1000, 0, 0, 0), 1000);
eq('vest no cliff', T.vested(1200, 1, 48, 0), 25);
eq('vest partial month ignored', T.vested(4800, 12.9, 48, 12), 1200);
let q = T.equity({ options: '10000', strike: '1', price: '5', fdShares: '10,000,000', multiples: ['1', '3', '10'], vestYears: '4', cliffMonths: '12', monthsIn: '24' });
near('paper value', q.paper, 40000); near('exercise cost', q.cost, 10000); near('ownership', q.ownership, 0.001); near('implied valuation', q.valuation, 50000000);
eq('vested half', q.vest.options, 5000); near('vested value', q.vest.value, 20000);
near('scenario 1x net', q.scenarios[0].net, 40000); near('scenario 3x net', q.scenarios[1].net, 140000); near('scenario 10x', q.scenarios[2].net, 490000);
near('scenario exit valuation', q.scenarios[1].exitValuation, 150000000); near('break-even multiple', q.breakEven, 0.2); near('per year', q.perYear, 10000);
q = T.equity({ options: '10000', strike: '1', price: '5', fdShares: '10000000', multiples: ['3'], rounds: '2', dilution: '20' });
near('retained after 2 rounds of 20%', q.retained, 0.64); near('diluted exit price', q.scenarios[0].price, 5 * 3 * 0.64);
near('diluted net', q.scenarios[0].net, 10000 * (9.6 - 1)); near('diluted ownership', q.scenarios[0].ownership, 0.00064); near('break-even with dilution', q.breakEven, 1 / 3.2);
q = T.equity({ mode: 'valuation', options: '20000', strike: '2', valuation: '100m', fdShares: '50m', multiples: ['0', '0.5', '1'] });
near('price from valuation', q.price, 2); near('at the money paper value', q.paper, 0);
near('0x exit', q.scenarios[0].net, 0); near('underwater exit is zero, not negative', q.scenarios[1].net, 0);
q = T.equity({ options: '1000', strike: '10', price: '4', multiples: ['1', '5'] });
near('underwater today', q.paper, 0); eq('no ownership without share count', q.ownership, null); eq('no valuation without share count', q.valuation, null);
near('underwater 5x', q.scenarios[1].net, 1000 * (20 - 10)); eq('no months -> no vesting block', q.vest, null);
eq('equity: no options', T.equity({ options: '', strike: '1', price: '5' }), null);
eq('equity: no price', T.equity({ options: '100', strike: '1', price: '' }), null);
eq('equity: valuation without shares', T.equity({ mode: 'valuation', options: '100', strike: '1', valuation: '1m' }), null);
q = T.equity({ options: '100', strike: '0', price: '5', multiples: ['abc', '', '2'] });
eq('bad multiples dropped', q.scenarios.length, 1); near('zero strike', q.paper, 500);
q = T.equity({ options: '100', strike: '1', price: '5', rounds: '3', dilution: '150', multiples: ['1'] });
ok('dilution capped below 100%', q.retained > 0 && q.retained < 1e-5);

/* time zones */
const jan = new Date(Date.UTC(2026, 0, 15, 12)), jul = new Date(Date.UTC(2026, 6, 15, 12));
eq('UTC offset', T.tzOffset('UTC', jan), 0);
eq('Kolkata +5:30', T.tzOffset('Asia/Kolkata', jan), 330);
eq('Kathmandu +5:45', T.tzOffset('Asia/Kathmandu', jan), 345);
eq('New York winter', T.tzOffset('America/New_York', jan), -300);
eq('New York summer', T.tzOffset('America/New_York', jul), -240);
eq('Berlin winter', T.tzOffset('Europe/Berlin', jan), 60);
eq('Berlin summer', T.tzOffset('Europe/Berlin', jul), 120);
eq('St Johns half hour west', T.tzOffset('America/St_Johns', jan), -210);
eq('Adelaide summer +10:30', T.tzOffset('Australia/Adelaide', jan), 630);
eq('Kiritimati +14', T.tzOffset('Pacific/Kiritimati', jan), 840);
eq('Chatham +13:45 in January', T.tzOffset('Pacific/Chatham', jan), 825);
eq('day interval simple', T.dayIntervals(540, 1020, 0), [[540, 1020]]);
eq('day interval wraps UTC midnight', T.dayIntervals(540, 1020, -480), [[1020, 1440], [0, 60]]);
eq('overnight shift', T.dayIntervals(1320, 360, 0), [[1320, 1440], [0, 360]]);
eq('same start and end', T.dayIntervals(540, 540, 0), []);
eq('full day', T.dayIntervals(0, 1440, 120), [[0, 1440]]);
eq('half-hour offset interval', T.dayIntervals(540, 1020, 330), [[210, 690]]);
let ov = T.overlap([{ start: 540, end: 1020, off: 60 }, { start: 540, end: 1020, off: -300 }]);       // Berlin 9–17 and New York 9–17 in winter
eq('Berlin/NY minutes', ov.minutes, 120); eq('Berlin/NY utc', ov.utc, [[840, 960]]);
eq('Berlin/NY in Berlin time', T.hm(ov.blocks[0].start + 60) + '-' + T.hm(ov.blocks[0].start + ov.blocks[0].len + 60), '15:00-17:00');
eq('Berlin/NY in NY time', T.hm(ov.blocks[0].start - 300) + '-' + T.hm(ov.blocks[0].start + ov.blocks[0].len - 300), '09:00-11:00');
ov = T.overlap([{ start: 540, end: 1080, off: 330 }, { start: 480, end: 1020, off: 0 }]);               // Kolkata 9–18 and London 8–17
eq('Kolkata/London minutes (half-hour zone)', ov.minutes, 270); eq('Kolkata/London utc', ov.utc, [[480, 750]]);
eq('Kolkata local start', T.hm(ov.blocks[0].start + 330), '13:30');
ov = T.overlap([{ start: 540, end: 1080, off: -480 }, { start: 420, end: 960, off: 660 }]);             // Los Angeles 9–18 and Sydney 7–16: shared time runs through midnight UTC
eq('LA/Sydney minutes', ov.minutes, 360); eq('LA/Sydney two UTC pieces', ov.utc, [[0, 120], [1200, 1440]]);
eq('LA/Sydney one block across midnight', ov.blocks, [{ start: 1200, len: 360 }]);
eq('LA/Sydney LA local', T.hm(ov.blocks[0].start - 480) + '-' + T.hm(ov.blocks[0].start + ov.blocks[0].len - 480), '12:00-18:00');
eq('LA/Sydney Sydney local', T.hm(ov.blocks[0].start + 660) + '-' + T.hm(ov.blocks[0].start + ov.blocks[0].len + 660), '07:00-13:00');
ov = T.overlap([{ start: 540, end: 1020, off: 540 }, { start: 540, end: 1020, off: -300 }]);            // Tokyo and New York: none
eq('Tokyo/NY none', [ov.minutes, ov.blocks.length], [0, 0]);
ov = T.overlap([{ start: 540, end: 1020, off: 60 }, { start: 540, end: 1020, off: 0 }, { start: 480, end: 960, off: -300 }]);   // three zones
eq('three zones', [ov.minutes, ov.utc], [180, [[780, 960]]]);
ov = T.overlap([{ start: 1320, end: 360, off: 0 }, { start: 540, end: 1020, off: 600 }]);               // night shift in UTC with Brisbane day
eq('night shift overlap', ov.minutes, 420); eq('night shift blocks', ov.blocks, [{ start: 1380, len: 420 }]);
ov = T.overlap([{ start: 540, end: 1020, off: 345 }, { start: 540, end: 1020, off: 330 }]);             // Kathmandu and Kolkata: 15 minutes apart
eq('quarter-hour zones', ov.minutes, 465);
ov = T.overlap([{ start: 540, end: 540, off: 0 }, { start: 540, end: 1020, off: 0 }]);
eq('zero-length day', ov.minutes, 0);
eq('shift to local splits at midnight', T.shift([[600, 900]], 660), [[0, 120], [1260, 1440]]);
eq('shift joins up across UTC midnight', T.shift([[0, 120], [1200, 1440]], 660), [[420, 660], [660, 780]]);
eq('shift no split', T.shift([[840, 960]], -300), [[540, 660]]);
eq('hm 24h', T.hm(810), '13:30'); eq('hm 12h', T.hm(810, true), '1:30 pm'); eq('hm midnight 12h', T.hm(0, true), '12 am'); eq('hm noon 12h', T.hm(720, true), '12 pm'); eq('hm wraps', T.hm(1500), '01:00'); eq('hm negative', T.hm(-30), '23:30');
eq('dur', [T.dur(210), T.dur(60), T.dur(120), T.dur(45), T.dur(0)], ['3 h 30 min', '1 hour', '2 hours', '45 min', '0 min']);
eq('utc label', [T.utcLabel(330), T.utcLabel(-300), T.utcLabel(0), T.utcLabel(-210), T.utcLabel(825)], ['UTC+5:30', 'UTC−5', 'UTC+0', 'UTC−3:30', 'UTC+13:45']);

/* résumé match */
const pats = T.compilePats(process.argv[3] ? JSON.parse(fs.readFileSync(process.argv[3], 'utf8')) : [['Python', 'python'], ['PostgreSQL', 'postgres'], ['Kubernetes', 'kubernetes|\\bk8s\\b'], ['AWS', '\\baws\\b'], ['Go', 'golang|\\bgo[,/)]|[,/(] ?go\\b'], ['Kafka', '\\bkafka\\b'], ['bad', '(']]);
ok('bad pattern skipped, good ones kept', pats.length >= 6 && pats.every(function (p) { return p[1] instanceof RegExp; }));
const JD = 'Senior Backend Engineer\nWe are looking for a backend engineer to build data pipelines and payment systems. You will design data pipelines in Python and Go, run them on Kubernetes and AWS, and own payment systems end to end.\n' +
  'Requirements:\n- 5+ years building distributed systems\n- Python, PostgreSQL, Kafka\n- Experience with payment systems and distributed systems\n- Mentoring engineers, code review, on-call rotation\nNice to have: on-call rotation experience in fintech.';
const CV = 'Alex Morgan, Backend Engineer. I build payment systems in Python and PostgreSQL. At Acme I designed data pipelines processing 2 million events a day, cut costs by 30%, and ran services on AWS for 400,000 users. ' +
  'I mentor engineers and lead code review. Earlier I worked on billing and reporting tools, wrote integration tests, and improved deployment speed by 3x for a team of 12 engineers across two offices in Berlin and Lisbon.';
let mr = T.matchResume(CV, JD, pats, 'Senior Backend Engineer');
ok('match has score', mr.score > 0 && mr.score <= 100, mr.score);
ok('matched skills include Python, PostgreSQL, AWS', ['Python', 'PostgreSQL', 'AWS'].every(function (s) { return mr.matched.indexOf(s) >= 0; }), mr.matched);
ok('missing skills include Kafka and Kubernetes', ['Kafka', 'Kubernetes'].every(function (s) { return mr.missing.indexOf(s) >= 0; }), mr.missing);
ok('no skill both matched and missing', mr.matched.every(function (s) { return mr.missing.indexOf(s) < 0; }));
const termNames = mr.terms.map(function (t) { return t.term; });
ok('repeated phrase found: payment systems', termNames.indexOf('payment systems') >= 0, termNames);
ok('repeated phrase found: data pipelines', termNames.indexOf('data pipelines') >= 0, termNames);
ok('repeated phrase found: distributed systems', termNames.indexOf('distributed systems') >= 0, termNames);
ok('skills are not repeated as terms', termNames.indexOf('python') < 0, termNames);
ok('stop words are not terms', termNames.every(function (t) { return ['experience', 'requirements', 'you', 'we'].indexOf(t) < 0; }), termNames);
ok('payment systems marked found', mr.terms.filter(function (t) { return t.term === 'payment systems'; })[0].found === true);
ok('distributed systems marked missing', mr.terms.filter(function (t) { return t.term === 'distributed systems'; })[0].found === false);
ok('title fix mentions senior', mr.fixes.some(function (f) { return /Echo the job title/.test(f.t) && /senior/.test(f.d); }), mr.fixes);
ok('numbers are recognised (no "add numbers" fix)', !mr.fixes.some(function (f) { return /numbers/.test(f.t); }), mr.figures);
ok('fix lists missing skills', mr.fixes.some(function (f) { return /Kafka/.test(f.d); }));
const same = T.matchResume(JD, JD, pats, '');
eq('identical texts score 100', same.score, 100);
eq('identical texts: nothing missing', [same.missing.length, same.terms.filter(function (t) { return !t.found; }).length], [0, 0]);
const none = T.matchResume('I am a pastry chef with ten years of work in hotel kitchens. I bake bread, laminate dough, plan menus, order stock, train junior cooks and keep the kitchen spotless during service every single day of the week.', JD, pats, '');
ok('unrelated résumé scores low', none.score < 20, none.score);
eq('short résumé', T.matchResume('too short', JD, pats).error, 'resume');
eq('short posting', T.matchResume(CV, 'short', pats).error, 'jd');
eq('empty inputs', T.matchResume('', '', pats).error, 'resume');
const noPats = T.matchResume(CV, JD, [], '');
ok('works without the skills list', noPats.score >= 0 && noPats.jdSkills === 0, noPats);
eq('stemming', [T.stem('managing'), T.stem('managed'), T.stem('manages'), T.stem('manage')], ['manag', 'manag', 'manag', 'manag']);
eq('stemming plurals', [T.stem('pipelines'), T.stem('pipeline'), T.stem('apis'), T.stem('running'), T.stem('status'), T.stem('front-end')], ['pipelin', 'pipelin', 'api', 'run', 'status', 'frontend']);
const fe = T.matchResume('I am a frontend engineer. ' + CV, 'We need a front end engineer. The front end engineer owns the design system and the design system tooling for all thirty of our product squads and partner agencies in this growing regional business unit today.', pats, '');
ok('"front end" matches "frontend"', fe.terms.some(function (t) { return /front end/.test(t.term) && t.found; }), fe.terms);

/* cover letter */
const full = { name: 'Alex Morgan', title: 'Senior Backend Engineer', company: 'Acme', manager: 'Dana Lee', source: 'Hiring Right Now', current: 'backend engineer', years: '8', skills: 'Python, PostgreSQL, Kafka', achievement: 'I cut page load time from 4 s to 1.2 s', why: 'your API is the one my team chose after testing four', contact: 'alex@example.com' };
['direct', 'warm', 'formal'].forEach(function (tone) {
  const L = T.coverLetter(Object.assign({}, full, { tone: tone }));
  ok('letter ' + tone + ' has no undefined/NaN/placeholder', !/undefined|NaN|\[/.test(L), L);
  ok('letter ' + tone + ' has no double spaces or space before punctuation', !/ {2}| [.,]/.test(L), L);
  ok('letter ' + tone + ' mentions the facts', ['Alex Morgan', 'Senior Backend Engineer', 'Acme', 'Dana Lee', 'Python, PostgreSQL and Kafka', '8 years', '1.2 s.', 'alex@example.com'].every(function (s) { return L.indexOf(s) >= 0; }), L);
  ok('letter ' + tone + ' uses "a backend engineer"', /\ba backend engineer\b/.test(L), L);
  ok('letter ' + tone + ' ends with the name', /\nAlex Morgan$/.test(L));
  const E = T.coverLetter({ tone: tone });
  ok('empty letter ' + tone + ' uses placeholders, nothing broken', /\[job title\]/.test(E) && /\[company\]/.test(E) && /\[Your name\]$/.test(E) && !/undefined|NaN| {2}/.test(E), E);
  ok('empty letter ' + tone + ' has greeting, opening, closing, sign-off only', E.split('\n\n').length === 4, E.split('\n\n').length);
});
ok('tones differ', T.coverLetter(Object.assign({}, full, { tone: 'warm' })) !== T.coverLetter(Object.assign({}, full, { tone: 'formal' })));
ok('unknown tone falls back to direct', T.coverLetter(Object.assign({}, full, { tone: 'zzz' })) === T.coverLetter(Object.assign({}, full, { tone: 'direct' })));
eq('articles', [T.article('engineer'), T.article('SRE'), T.article('UX designer'), T.article('iOS developer'), T.article('user researcher'), T.article('product manager'), T.article('HR partner')], ['an', 'an', 'a', 'an', 'a', 'a', 'an']);
ok('1 year is singular', /with 1 year of experience/.test(T.coverLetter(Object.assign({}, full, { years: '1' }))));
ok('"8+ years" typed in full is not doubled', /8\+ years of experience/.test(T.coverLetter(Object.assign({}, full, { years: '8+ years' }))));
ok('achievement keeps its own full stop', !/\.\./.test(T.coverLetter(Object.assign({}, full, { achievement: 'I shipped it.' }))));
eq('andList', [T.andList([]), T.andList(['a']), T.andList(['a', 'b']), T.andList(['a', 'b', 'c'])], ['', 'a', 'a and b', 'a, b and c']);

/* negotiation email */
['counter', 'raise', 'time'].forEach(function (sc) {
  ['collaborative', 'firm', 'brief'].forEach(function (tone) {
    const m = T.negotiationEmail({ scenario: sc, tone: tone, name: 'Alex', to: 'Dana', company: 'Acme', title: 'Staff Engineer', offer: '150000', target: '165,000', cur: '$', reasons: '- Led the payments rewrite\n2. Two competing offers', extras: ['a sign-on bonus', 'extra paid days off'], deadline: 'Friday, 20 November' });
    ok('email ' + sc + '/' + tone + ' clean', !/undefined|NaN|\[| {2}/.test(m.text) && /^Subject: /.test(m.text) && /\nAlex$/.test(m.text), m.text);
    if (sc !== 'time') ok('email ' + sc + '/' + tone + ' has both figures', m.text.indexOf('$150,000') >= 0 && m.text.indexOf('$165,000') >= 0, m.text);
    if (sc !== 'time') ok('email ' + sc + '/' + tone + ' has reasons without bullet marks doubled', /Led the payments rewrite/.test(m.text) && /Two competing offers/.test(m.text) && !/- - |2\. Two/.test(m.text), m.text);
    ok('email ' + sc + '/' + tone + ' mentions the date', m.text.indexOf('Friday, 20 November') >= 0, m.text);
    const e = T.negotiationEmail({ scenario: sc, tone: tone });
    ok('empty email ' + sc + '/' + tone + ' uses placeholders', !/undefined|NaN| {2}/.test(e.text) && /\[Your name\]$/.test(e.text), e.text);
  });
});
let ne = T.negotiationEmail({ scenario: 'raise', offer: '80000', target: '86600' });
near('raise percent', ne.pct, 8.25); ok('raise percent in text, one decimal', /an increase of 8\.3%/.test(ne.text), ne.text); near('gap', ne.gap, 6600);
ne = T.negotiationEmail({ scenario: 'counter', offer: '', target: '' });
eq('no figures -> no percent', [ne.pct, ne.gap], [null, null]);
ok('extras joined with "or"', /a sign-on bonus, additional equity or extra paid days off/.test(T.negotiationEmail({ extras: ['a sign-on bonus', 'additional equity', 'extra paid days off'], offer: '1', target: '2' }).text));
ok('currency symbol is used', /€70,000/.test(T.negotiationEmail({ offer: '70000', target: '76000', cur: '€' }).text));

/* job description checker */
const GOOD = 'Senior Backend Engineer (Payments)\n\nAbout the role\nYou will build and run the services that move money for our customers. You will work with four other engineers and a product manager, ship every week, and take part in the on-call rota one week in six. ' +
  'You will write Go and SQL, review code, and help plan the next quarter of work with the team.\n\nWhat you will do\n- Design and build payment services in Go\n- Keep the ledger correct and fast\n- Review code and share what you learn\n- Talk to customers when a payment goes wrong\n\n' +
  'Requirements\n- Three or more years building backend services\n- Good knowledge of SQL and of one compiled language\n- Experience running services in production\n- Clear written English\n\nNice to have\n- Experience with card payments or bank transfers\n- Kubernetes\n\n' +
  'Salary and benefits\nThe salary range is $150,000 to $185,000 per year, depending on experience. You get 28 days of paid time off, health insurance for you and your family, equity, and a learning budget of $2,000 a year.\n\n' +
  'Location\nRemote within Europe, or hybrid from our Lisbon office two days a week.\n\nHow to apply\nSend your CV through the form. There are three interviews: an intro call, a paired coding session and a talk with the team. You will hear back within a week at each step. ' +
  'We reply to every application. If you need any adjustments to the interview process, tell us and we will arrange them. We are a team of forty people in nine countries and we have been profitable since last year. Our customers are small online shops that sell across borders, and you will talk to them often. ' +
  'The work is steady rather than frantic: we plan in six-week cycles, we write things down, and we do not expect anyone to answer messages outside their working hours. You will have a mentor for your first three months and a clear plan for what to learn. ' +
  'Most of the code is in Go, with PostgreSQL for storage and a small amount of TypeScript for internal tools. We deploy many times a day and every engineer can deploy. Tests run in under ten minutes. You will join the team that owns the ledger and the payment integrations, the part of the product that customers rely on most.';
let jd = T.checkJD(GOOD);
ok('good posting scores high', jd.score >= 85, { score: jd.score, items: jd.items.filter(function (i) { return i.level !== 'ok'; }) });
eq('good posting: must-haves counted under the heading', jd.mustHaves, 4);
eq('good posting: nice-to-haves', jd.niceToHaves, 2);
ok('good posting: salary found', jd.items.some(function (i) { return i.level === 'ok' && /Salary range is stated/.test(i.t); }));
ok('good posting: label', jd.label === 'Ready to post');
const BAD = 'We are a fast-paced, world-class unicorn startup looking for a rockstar ninja developer who is a digital native and a native English speaker. We want an aggressive, competitive, dominant, fearless self-starter who can hit the ground running and wear many hats. ' +
  'We offer a competitive salary. Our company is disruptive and our culture is work hard play hard. We need someone who will crush it. We are the best. We are growing. Our mission is big and our team is the best team in the industry by a wide margin and we know it.\n' +
  'Requirements:\n- 10+ years of experience\n- Must know Java\n- Must know Python\n- Must know Go\n- Must know Rust\n- Must know C++\n- Must know SQL\n- Must know AWS\n- Must know GCP\n- Must know Azure\n- Must know Kubernetes\n- Must know Terraform\n- Must know Kafka\n- Must have a degree';
jd = T.checkJD(BAD);
ok('bad posting scores low', jd.score < 40, jd.score);
ok('bad: no salary, "competitive salary" called out', jd.items.some(function (i) { return i.level === 'fix' && /Competitive salary/.test(i.t); }), jd.items.map(function (i) { return i.t; }));
eq('bad: 14 must-haves', jd.mustHaves, 14);
ok('bad: exclusionary terms', ['rockstar', 'ninja', 'digital native', 'native english', 'work hard play hard', 'crush it'].every(function (t) { return jd.exclusionary.some(function (x) { return x.term === t; }); }), jd.exclusionary);
ok('bad: masculine-coded lean', jd.items.some(function (i) { return /masculine-coded/.test(i.t) && i.level === 'warn'; }));
ok('bad: "competitive salary" not counted as masculine-coded twice', jd.masculine.filter(function (x) { return x.term === 'competitive'; })[0].n === 1, jd.masculine);
ok('bad: buzzwords', ['fast-paced', 'world-class', 'self-starter', 'hit the ground running', 'wear many hats', 'disruptive'].every(function (t) { return jd.jargon.some(function (x) { return x.term === t; }); }), jd.jargon);
ok('bad: 10+ years flagged', jd.items.some(function (i) { return /10\+ years/.test(i.t); }));
ok('bad: no location / benefits flagged', jd.items.some(function (i) { return /where the work happens/.test(i.t); }) && jd.items.some(function (i) { return /No benefits/.test(i.t); }));
ok('bad: fixes come first', jd.items[0].level === 'fix');
eq('too short', T.checkJD('Hiring a developer.').error, 'short');
eq('empty', T.checkJD('').error, 'short');
ok('score never negative', T.checkJD(BAD + ' ' + BAD.replace(/\n/g, ' ')).score >= 0);
jd = T.checkJD(GOOD.replace('The salary range is $150,000 to $185,000 per year, depending on experience.', 'You will manage a budget of $5M to $10M.'));
ok('a budget range is not mistaken for a salary', jd.items.some(function (i) { return i.level === 'fix' && /No salary range/.test(i.t); }), jd.items.map(function (i) { return i.t; }));
jd = T.checkJD(GOOD.replace('$150,000 to $185,000 per year', '€90k–€110k'));
ok('k-style range with euro sign', jd.items.some(function (i) { return /Salary range is stated/.test(i.t); }));
jd = T.checkJD(GOOD.replace('The salary range is $150,000 to $185,000 per year, depending on experience.', 'The salary is $150,000 per year.'));
ok('single figure -> warn', jd.items.some(function (i) { return i.level === 'warn' && /One pay figure/.test(i.t); }), jd.items.map(function (i) { return i.t; }));
ok('data-driven is not masculine-coded "driven"', T.checkJD(GOOD + ' We are a data-driven team and we keep sensitive data confidential with deterministic builds on Heroku.').masculine.length === 0);
eq('syllables (vowel-group estimate)', ['cat', 'engineer', 'the', 'payment', 'salary', 'required', 'code'].map(T.syllables), [1, 3, 1, 2, 3, 2, 1]);
let rd = T.readability('The cat sat on the mat. The dog ran.');
eq('readability counts', [rd.words, rd.sentences], [9, 2]); near('reading ease of very simple text', rd.ease, 206.835 - 1.015 * 4.5 - 84.6 * 1, 1e-9);
eq('readability empty', T.readability('').ease, null);

/* JobPosting */
const base = { title: 'Senior Backend Engineer', description: 'You will build payment services.\n\nWhat you will do\n- Design services\n- Review code\n\n' + 'More words about the job and the team. '.repeat(10), datePosted: '2026-11-12', validThrough: '2026-12-31',
  employmentType: ['FULL_TIME'], orgName: 'Acme GmbH', orgUrl: 'https://acme.example', orgLogo: 'https://acme.example/logo.png', locType: 'onsite', street: '1 Main St', city: 'Berlin', region: 'BE', postal: '10115', country: 'DE',
  salaryCurrency: 'eur', salaryMin: '90,000', salaryMax: '110000', salaryUnit: 'YEAR', identifier: 'BE-42', directApply: 'true' };
let jp = T.jobPosting(base, '2026-11-12');
eq('complete posting: no errors, no warnings', [jp.errors, jp.warnings], [[], []]);
ok('complete posting parses as JSON', (function () { try { return JSON.parse(jp.json)['@type'] === 'JobPosting'; } catch (e) { return false; } })());
eq('salary object', jp.data.baseSalary, { '@type': 'MonetaryAmount', currency: 'EUR', value: { '@type': 'QuantitativeValue', minValue: 90000, maxValue: 110000, unitText: 'YEAR' } });
eq('address', jp.data.jobLocation, { '@type': 'Place', address: { '@type': 'PostalAddress', streetAddress: '1 Main St', addressLocality: 'Berlin', addressRegion: 'BE', postalCode: '10115', addressCountry: 'DE' } });
eq('employment type single', jp.data.employmentType, 'FULL_TIME');
eq('direct apply boolean', jp.data.directApply, true);
eq('identifier', jp.data.identifier, { '@type': 'PropertyValue', name: 'Acme GmbH', value: 'BE-42' });
ok('description is HTML with a list', /^<p>You will build payment services\.<\/p><p>What you will do<\/p><ul><li>Design services<\/li><li>Review code<\/li><\/ul><p>/.test(jp.data.description), jp.data.description);
ok('script wrapper', /^<script type="application\/ld\+json">\n\{/.test(jp.script) && /\}\n<\/script>$/.test(jp.script));
jp = T.jobPosting({}, '2026-11-12');
eq('empty form: five required fields missing', jp.errors.length, 5);
ok('empty form: names every required field', ['title', 'description', 'datePosted', 'hiringOrganization', 'jobLocation'].every(function (k) { return jp.errors.some(function (e) { return e.indexOf(k) === 0; }); }), jp.errors);
eq('empty form is invalid', jp.valid, false);
jp = T.jobPosting(Object.assign({}, base, { locType: 'remote', street: '', city: '', region: '', postal: '', country: '', remoteCountries: 'USA, Canada' }), '2026-11-12');
eq('remote: valid', jp.errors, []); eq('remote: type', jp.data.jobLocationType, 'TELECOMMUTE'); eq('remote: no jobLocation', jp.data.jobLocation, undefined);
eq('remote: countries', jp.data.applicantLocationRequirements, [{ '@type': 'Country', name: 'USA' }, { '@type': 'Country', name: 'Canada' }]);
jp = T.jobPosting(Object.assign({}, base, { locType: 'remote', street: '', city: '', region: '', postal: '', country: '', remoteCountries: '' }), '2026-11-12');
ok('remote without a country is an error', jp.errors.length === 1 && /country/.test(jp.errors[0]), jp.errors);
jp = T.jobPosting(Object.assign({}, base, { country: '' }), '2026-11-12');
ok('on-site without country is an error', jp.errors.some(function (e) { return /addressCountry/.test(e); }));
jp = T.jobPosting(Object.assign({}, base, { validThrough: '2026-11-01' }), '2026-11-12');
ok('closing date before posting date is an error', jp.errors.some(function (e) { return /earlier/.test(e); }));
jp = T.jobPosting(Object.assign({}, base, { datePosted: '2026-10-01', validThrough: '2026-11-01' }), '2026-11-12');
ok('expired posting is a warning', jp.warnings.some(function (e) { return /past/.test(e); }) && jp.valid);
jp = T.jobPosting(Object.assign({}, base, { datePosted: '12/11/2026' }), '2026-11-12');
ok('bad date format', jp.errors.some(function (e) { return /YYYY-MM-DD/.test(e); }));
jp = T.jobPosting(Object.assign({}, base, { datePosted: '2026-02-30' }), '2026-11-12');
ok('impossible date', jp.errors.some(function (e) { return /YYYY-MM-DD/.test(e); }));
jp = T.jobPosting(Object.assign({}, base, { salaryMin: '120000', salaryMax: '100000' }), '2026-11-12');
ok('min above max', jp.errors.some(function (e) { return /minimum is higher/.test(e); }));
jp = T.jobPosting(Object.assign({}, base, { salaryMin: '55', salaryMax: '', salaryUnit: 'HOUR', salaryCurrency: 'USD' }), '2026-11-12');
eq('single salary value', jp.data.baseSalary.value, { '@type': 'QuantitativeValue', value: 55, unitText: 'HOUR' });
jp = T.jobPosting(Object.assign({}, base, { salaryCurrency: 'dollars' }), '2026-11-12');
ok('bad currency code', jp.errors.some(function (e) { return /currency code/.test(e); }));
jp = T.jobPosting(Object.assign({}, base, { salaryMin: '', salaryMax: '', identifier: '', validThrough: '', employmentType: [], directApply: '' }), '2026-11-12');
eq('recommended fields missing -> 5 warnings, still valid', [jp.warnings.length, jp.valid], [5, true]);
jp = T.jobPosting(Object.assign({}, base, { employmentType: ['FULL_TIME', 'CONTRACTOR'] }), '2026-11-12');
eq('several employment types', jp.data.employmentType, ['FULL_TIME', 'CONTRACTOR']);
jp = T.jobPosting(Object.assign({}, base, { description: 'Great job </script><script>alert(1)</script> & more. ' + 'word '.repeat(60) }), '2026-11-12');
ok('markup in the description cannot close the script tag', jp.script.split('</script>').length === 2 && jp.json.indexOf('<') < 0 && JSON.parse(jp.json).description.indexOf('&lt;/script&gt;') > 0, jp.json.slice(0, 300));
jp = T.jobPosting(Object.assign({}, base, { title: 'Senior Engineer - $200k!!! APPLY NOW' }), '2026-11-12');
ok('noisy title warned', jp.warnings.some(function (e) { return /^title/.test(e); }));
eq('descHtml empty', T.descHtml(''), '');
eq('descHtml escapes and breaks lines', T.descHtml('a < b\nc & d'), '<p>a &lt; b<br>c &amp; d</p>');

/* boolean search */
let bs = T.booleanSearch({ titles: 'Software Engineer, Backend Developer', must: 'Python\nmachine learning', any: 'AWS, GCP, Azure', not: 'recruiter, intern', place: 'Berlin' });
eq('boolean string', bs.boolean, '("Software Engineer" OR "Backend Developer") AND Python AND "machine learning" AND (AWS OR GCP OR Azure) NOT (recruiter OR intern)');
eq('linkedin x-ray', bs.linkedin, 'site:linkedin.com/in ("Software Engineer" OR "Backend Developer") Python "machine learning" (AWS OR GCP OR Azure) "Berlin" -recruiter -intern');
eq('github x-ray (no titles)', bs.github, 'site:github.com Python "machine learning" (AWS OR GCP OR Azure) "Berlin" -recruiter -intern');
ok('brackets and quotes balanced', [bs.boolean, bs.linkedin, bs.github].every(function (s) { return (s.match(/\(/g) || []).length === (s.match(/\)/g) || []).length && (s.match(/"/g) || []).length % 2 === 0; }));
bs = T.booleanSearch({ titles: 'DevOps Engineer' });
eq('single title, nothing else', [bs.boolean, bs.linkedin, bs.github], ['"DevOps Engineer"', 'site:linkedin.com/in "DevOps Engineer"', '']);
bs = T.booleanSearch({ must: 'C++, C#, .NET, Node.js, "already quoted", rust, Rust' });
eq('special characters quoted, duplicates dropped, stray quotes removed', bs.boolean, '"C++" AND "C#" AND ".NET" AND "Node.js" AND "already quoted" AND rust');
eq('empty form', T.booleanSearch({}).empty, true);
eq('only exclusions is still empty', T.booleanSearch({ not: 'intern' }).empty, true);
bs = T.booleanSearch({ any: 'React' , not: 'junior' });
eq('one any-of term, one exclusion', bs.boolean, 'React NOT junior');
eq('title variants: frontend engineer', T.titleVariants('Frontend Engineer'), ['Frontend Engineer', 'Front-end Engineer', 'Front end Engineer', 'Frontend Developer', 'Front-end Developer', 'Front end Developer']);
eq('title variants: nothing to vary', T.titleVariants('Product Manager'), ['Product Manager']);
eq('title variants: full stack developer', T.titleVariants('full stack developer'), ['full stack developer', 'fullstack developer', 'full-stack developer', 'fullstack engineer', 'full-stack engineer', 'full stack engineer']);
bs = T.booleanSearch({ titles: 'Backend Engineer', variants: true });
eq('variants in the string', bs.boolean, '("Backend Engineer" OR "Back-end Engineer" OR "Back end Engineer" OR "Backend Developer" OR "Back-end Developer" OR "Back end Developer")');
eq('word count ignores operators', T.booleanSearch({ titles: 'a b, c', must: 'd', any: 'e, f', not: 'g' }).words, 8);

/* contractor rate */
let cr = T.contractorRate({ income: '100000', overhead: '25', costs: '5000', daysOff: '35', billable: '80', hours: '8' });
near('contractor revenue', cr.revenue, 130000); near('contractor billable days', cr.days, 180); near('contractor day rate', cr.day, 130000 / 180); near('contractor hourly', cr.hour, 130000 / 180 / 8);
cr = T.contractorRate({ income: '104000' });
near('contractor defaults: 260 days, 8 hours, no extras', cr.day, 400); near('contractor defaults hourly', cr.hour, 50); eq('contractor uplift zero', cr.upliftPct, 0);
cr = T.contractorRate({ income: '100000', overhead: '30', daysOff: '40', billable: '75' });
near('contractor uplift vs salaried hourly', cr.upliftPct, (130000 / (220 * 0.75 * 8)) / (100000 / 2080) * 100 - 100, 1e-9);
eq('contractor: no income', T.contractorRate({ income: '' }), null);
eq('contractor: all days off', T.contractorRate({ income: '100000', daysOff: '260' }), null);
eq('contractor: zero billable share', T.contractorRate({ income: '100000', billable: '0' }), null);
near('contractor: billable share capped at 100', T.contractorRate({ income: '104000', billable: '150' }).day, 400);

/* salary checker */
const QS = [0, 5, 10, 20, 25, 30, 40, 50, 60, 70, 75, 80, 90, 95, 100], VALS = [80, 95, 100, 115, 120, 125, 135, 150, 160, 175, 180, 190, 220, 250, 400].map(function (v) { return v * 1000; });
eq('percentile below the lowest', T.percentile(QS, VALS, 50000), 0);
eq('percentile at the lowest', T.percentile(QS, VALS, 80000), 0);
eq('percentile at the median', T.percentile(QS, VALS, 150000), 50);
near('percentile between points', T.percentile(QS, VALS, 155000), 55);
eq('percentile at the top', T.percentile(QS, VALS, 400000), 100);
eq('percentile above the top', T.percentile(QS, VALS, 900000), 100);
near('percentile near top', T.percentile(QS, VALS, 325000), 97.5);
const FLAT = [100, 100, 100, 100, 100, 120, 120, 120, 120, 150, 150, 150, 150, 150, 150].map(function (v) { return v * 1000; });
eq('percentile on a flat stretch takes its upper end', T.percentile(QS, FLAT, 100000), 25);
near('percentile after a flat stretch', T.percentile(QS, FLAT, 110000), 27.5);
eq('percentile at flat top', T.percentile(QS, FLAT, 150000), 100);
ok('percentile is monotonic', (function () { let p = -1; for (let x = 70000; x <= 420000; x += 1000) { const v = T.percentile(QS, VALS, x); if (v < p) return false; p = v; } return true; })());
ok('percentile of NaN is 0', T.percentile(QS, VALS, NaN) === 0);
const DATA = { q: QS, g: { 'engineering|Senior|': [492, 150, 210].concat(VALS.map(function (v) { return v / 1000; })) } };
const g = T.salaryGroup(DATA, 'engineering', 'Senior', '');
eq('salary group', [g.n, g.low, g.high, g.median, g.p25, g.p75, g.p10, g.p90, g.min, g.max], [492, 150000, 210000, 150000, 120000, 180000, 100000, 220000, 80000, 400000]);
eq('missing salary group', T.salaryGroup(DATA, 'design', 'Junior', ''), null);
eq('no data', T.salaryGroup(null, '', '', ''), null);

/* audit 2026-11-13: slips found by the review */
eq('num: dot as thousands separator', T.num('150.000'), 150000);
eq('num: European thousands with decimals', T.num('1.250.000,50'), 1250000.5);
eq('num: a plain decimal is still a decimal', T.num('12.5'), 12.5);
eq('num: 1.2m still works', T.num('1.2m'), 1200000);
eq('equity: more options than shares gives no ownership figure', T.equity({ options: '2000000', strike: '1', price: '10', fdShares: '100000', multiples: ['2'] }).ownership, null);
near('equity: a normal stake is kept', T.equity({ options: '10000', strike: '1', price: '10', fdShares: '10000000', multiples: ['2'] }).ownership, 0.001);
let jdA = T.checkJD('About us\nWe were founded 15 years ago and have been 12 years in business.\n\nRequirements\n- 3+ years of Python\n- SQL\n' + 'You will build services that customers rely on every day. '.repeat(12));
eq('jd: "founded 15 years ago" is not a requirement', JSON.stringify(jdA).indexOf('15+ years') < 0, true);
eq('jd: a real requirement is still found', JSON.stringify(jdA).indexOf('3+ years') >= 0, true);

console.log('\n' + pass + ' passed, ' + fail + ' failed');
process.exit(fail ? 1 : 0);
