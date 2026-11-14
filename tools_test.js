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

/* ================================================================ tools added 2026-11-13 ================================================================ */

/* calendar dates and the last working day (16 November 2026 is a Monday) */
eq('long date', T.longDate('2026-11-30'), 'November 30, 2026');
eq('long date with the day', T.longDate('2026-11-30', true), 'Monday, November 30, 2026');
eq('leap day', T.longDate('2024-02-29', true), 'Thursday, February 29, 2024');
eq('29 February in a common year is not a date', T.longDate('2025-02-29'), '');
eq('junk is not a date', [T.longDate(''), T.longDate('30/11/2026'), T.longDate('0026-11-30'), T.dayName('x')], ['', '', '', '']);
eq('add days across a year end', T.addDays('2026-12-25', 14), '2027-01-08');
let ld = T.lastDay({ date: '2026-11-16', amount: '2', unit: 'weeks' });
eq('2 weeks from a Monday, starting the next day', [ld.first, ld.end, ld.last, ld.workDays, ld.calendarDays, ld.endsOnWeekend], ['2026-11-17', '2026-11-30', '2026-11-30', 10, 14, false]);
ld = T.lastDay({ date: '2026-11-16', amount: '2', unit: 'weeks', from: 'same' });
eq('2 weeks counted from the day itself end on a Sunday', [ld.first, ld.end, ld.last, ld.endsOnWeekend, ld.workDays], ['2026-11-16', '2026-11-29', '2026-11-27', true, 10]);
eq('10 working days equal 2 weeks', T.lastDay({ date: '2026-11-16', amount: '10', unit: 'workdays' }).last, '2026-11-30');
eq('10 working days counted from the day itself', T.lastDay({ date: '2026-11-16', amount: '10', unit: 'workdays', from: 'same' }).last, '2026-11-27');
eq('1 working day after a Friday is Monday', T.lastDay({ date: '2026-11-13', amount: '1', unit: 'workdays' }).last, '2026-11-16');
ld = T.lastDay({ date: '2026-11-14', amount: '1', unit: 'workdays', from: 'same' });
eq('notice on a Saturday: the weekend is skipped and flagged', [ld.last, ld.givenOnWeekend, ld.workDays], ['2026-11-16', true, 1]);
eq('working days never end on a weekend', [1, 2, 3, 4, 5, 6, 7, 23, 64].every(function (n) { const x = T.lastDay({ date: '2026-11-11', amount: String(n), unit: 'workdays' }); return !x.endsOnWeekend && x.workDays === n; }), true);
ld = T.lastDay({ date: '2026-01-31', amount: '1', unit: 'months' });
eq('1 month from 31 January ends on the last day of February, a Saturday', [ld.end, ld.last, ld.endsOnWeekend], ['2026-02-28', '2026-02-27', true]);
eq('…and on 29 February in a leap year', T.lastDay({ date: '2024-01-31', amount: '1', unit: 'months' }).end, '2024-02-29');
eq('1 month counted from the day itself', T.lastDay({ date: '2026-11-16', amount: '1', unit: 'months', from: 'same' }).end, '2026-12-15');
ld = T.lastDay({ date: '2026-11-30', amount: '3', unit: 'months' });
eq('3 months across the year end, ending on a Sunday', [ld.end, ld.last], ['2027-02-28', '2027-02-26']);
eq('2 weeks across the year end', T.lastDay({ date: '2026-12-21', amount: '2', unit: 'weeks' }).last, '2027-01-04');
eq('30 calendar days', T.lastDay({ date: '2026-11-16', amount: '30', unit: 'days' }).end, '2026-12-16');
ld = T.lastDay({ date: '2026-11-16', amount: '0', unit: 'weeks' });
eq('no notice: the job ends that day', [ld.end, ld.last, ld.workDays, ld.calendarDays], ['2026-11-16', '2026-11-16', 0, 0]);
ld = T.lastDay({ date: '2026-11-13', amount: '2', unit: 'days' });
eq('a notice period that covers only a weekend has no working day in it', [ld.end, ld.last, ld.workDays, ld.endsOnWeekend], ['2026-11-15', '2026-11-13', 0, true]);
eq('half weeks: 1,5 weeks is 11 days', T.lastDay({ date: '2026-11-16', amount: '1,5', unit: 'weeks' }).end, '2026-11-27');
eq('an unknown unit is read as weeks', T.lastDay({ date: '2026-11-16', amount: '1', unit: 'fortnights' }).end, '2026-11-23');
eq('last day: nothing typed', [T.lastDay({}), T.lastDay({ date: '2026-11-16', amount: '' }), T.lastDay({ date: '', amount: '2' })], [null, null, null]);
eq('last day: impossible date, negative or absurd notice', [T.lastDay({ date: '2026-02-30', amount: '2' }), T.lastDay({ date: '2026-11-16', amount: '-1' }), T.lastDay({ date: '2026-11-16', amount: '521', unit: 'weeks' }), T.lastDay({ date: '2026-11-16', amount: '99999', unit: 'workdays' })], [null, null, null, null]);
ok('last day: ten years of notice is still counted', T.lastDay({ date: '2026-11-16', amount: '520', unit: 'weeks' }).end === '2036-11-03');
ok('working days left are Mondays to Fridays only', T.lastDay({ date: '2026-11-16', amount: '52', unit: 'weeks' }).workDays === 260);

/* job search funnel */
eq('rate: percent forms', [T.rate('8').pct, T.rate('7,5%').pct, T.rate(' 20 % ').pct, T.rate('0').pct], [8, 7.5, 20, 0]);
eq('rate: counts', [T.rate('3 of 40').pct, T.rate('3/40').pct, T.rate('3 out of 40').pct, T.rate('1 from 5').pct, T.rate('0 of 12').pct], [7.5, 7.5, 7.5, 20, 0]);
eq('rate: the count is remembered', T.rate('3 of 40').from, 40);
ok('rate: impossible values', [T.rate('50 of 40'), T.rate('120'), T.rate(''), T.rate('abc'), T.rate('3 of 0'), T.rate('-5')].every(function (x) { return isNaN(x.pct); }));
let fu = T.funnel({ perWeek: '10', weeks: '8', reply: '3 of 40', offer: '1 of 5' });
near('funnel applications', fu.applications, 80); near('funnel interviews', fu.interviews, 6); near('funnel offers', fu.offers, 1.2);
near('funnel applications per offer', fu.perOffer, 1 / (0.075 * 0.2)); near('funnel applications per interview', fu.perInterview, 40 / 3); near('funnel weeks to one offer', fu.weeksToOffer, 1 / (0.075 * 0.2) / 10);
near('funnel chance of at least one offer', fu.chance, (1 - Math.pow(1 - 0.015, 80)) * 100); eq('funnel remembers small counts', [fu.replyFrom, fu.offerFrom], [40, 5]);
eq('funnel: rounded as on the tile', [T.fmt(fu.perOffer, 0), T.fmt(fu.interviews, 1), T.fmt(fu.offers, 2)], ['67', '6', '1.2']);
fu = T.funnel({ perWeek: '5', weeks: '4', reply: '0', offer: '25' });
eq('funnel: a zero rate gives no offer and no division by zero', [fu.perOffer, fu.perInterview, fu.weeksToOffer, fu.offers, fu.chance], [null, null, null, 0, 0]);
fu = T.funnel({ perWeek: '1', weeks: '1', reply: '100', offer: '100' });
eq('funnel: certain rates', [fu.perOffer, fu.offers, fu.chance], [1, 1, 100]);
eq('funnel: missing or impossible input', [T.funnel({}), T.funnel({ perWeek: '0', weeks: '8', reply: '5', offer: '5' }), T.funnel({ perWeek: '10', weeks: '', reply: '5', offer: '5' }), T.funnel({ perWeek: '10', weeks: '8', reply: '150', offer: '5' }), T.funnel({ perWeek: '10', weeks: '8', reply: '5', offer: '' })], [null, null, null, null, null]);
fu = T.funnel({ perWeek: '1,000', weeks: '52', reply: '2,5', offer: '10%' });
near('funnel: large numbers and a decimal comma', fu.offers, 52000 * 0.025 * 0.1); ok('funnel: the chance never passes 100', fu.chance <= 100 && fu.chance > 99.9);

/* remote work savings */
let rs = T.remoteSavings({ minutes: '45', cost: '12', lunch: '14', lunchHome: '5', home: '2', hourly: '30', daysNow: '5', daysNew: '0', weeks: '46' });
eq('remote: the example', [rs.days, rs.hours, rs.travel, rs.food, rs.homeCost, rs.money, rs.timeValue, rs.total], [230, 345, 2760, 2070, 460, 4370, 10350, 14720]);
near('remote: per month', rs.month, 4370 / 12); near('remote: working weeks', rs.workWeeks, 345 / 40);
rs = T.remoteSavings({ minutes: '30', cost: '10', daysNow: '5', daysNew: '2', weeks: '46' });
eq('remote: hybrid, three days fewer', [rs.days, rs.hours, rs.money, rs.timeValue], [138, 138, 1380, null]);
rs = T.remoteSavings({ minutes: '30', cost: '10', daysNow: '0', daysNew: '3', weeks: '48' });
eq('remote: more office days give a cost', [rs.days, rs.hours, rs.money], [-144, -144, -1440]);
eq('remote: defaults are 5 days, none after, 46 weeks', T.remoteSavings({ minutes: '60' }).hours, 460);
eq('remote: same days, nothing changes', T.remoteSavings({ minutes: '60', daysNow: '3', daysNew: '3' }).hours, 0);
near('remote: decimal comma in a price', T.remoteSavings({ cost: '12,50' }).travel, 2875);
near('remote: lunch at home dearer than at work counts against the saving', T.remoteSavings({ lunch: '5', lunchHome: '8', daysNow: '1', weeks: '10' }).money, -30);
eq('remote: nothing typed, or impossible figures', [T.remoteSavings({}), T.remoteSavings({ minutes: '45', daysNow: '8' }), T.remoteSavings({ minutes: '45', weeks: '60' }), T.remoteSavings({ minutes: '45', weeks: '0' }), T.remoteSavings({ minutes: '900' })], [null, null, null, null, null]);

/* cost per hire */
let ch = T.costPerHire({ ads: '3,000', agency: '18,000', recHours: '120', recRate: '45', intHours: '90', intRate: '70', tools: '2,400', other: '1,500', hires: '6' });
eq('cost per hire: the example', [ch.total, ch.perHire, ch.outside, ch.time, ch.hours, ch.hoursPerHire, ch.top.name, ch.unpriced], [36600, 6100, 24900, 11700, 210, 35, 'Agency and recruiter fees', false]);
near('cost per hire: shares add up to 100', ch.parts.reduce(function (s, p) { return s + p.share; }, 0), 100);
eq('cost per hire: tile figures', [T.plain(ch.top.share, 0), T.plain(ch.time / ch.total * 100, 0)], ['49', '32']);
near('cost per hire: a part per hire', ch.parts[2].perHire, 900);
ch = T.costPerHire({ ads: '500', hires: '' });
eq('cost per hire: total without a number of hires', [ch.total, ch.perHire, ch.hires, ch.parts[0].perHire], [500, null, null, null]);
eq('cost per hire: zero hires is not divided', T.costPerHire({ ads: '500', hires: '0' }).perHire, null);
eq('cost per hire: nothing spent', [T.costPerHire({}), T.costPerHire({ hires: '3' }), T.costPerHire({ ads: '0', hires: '3' })], [null, null, null]);
ch = T.costPerHire({ ads: '100', recHours: '40', hires: '1' });
eq('cost per hire: hours without an hourly cost are flagged and not counted', [ch.unpriced, ch.total, ch.time], [true, 100, 0]);
ch = T.costPerHire({ agency: '1.2m', ads: '250.000', hires: '40' });
eq('cost per hire: large and European figures', [ch.total, ch.perHire], [1450000, 36250]);
eq('cost per hire: negative amounts count as zero', T.costPerHire({ ads: '-500', tools: '200', hires: '2' }).total, 200);

/* interview scorecard */
const CRIT = [{ name: 'Technical skills', weight: '30' }, { name: 'Problem solving', weight: '25' }, { name: 'Communication', weight: '20' }, { name: 'Teamwork', weight: '15' }, { name: 'Motivation for the role', weight: '10' }, { name: '', weight: '' }];
let sc = T.scorecard({ role: 'Senior Backend Engineer', max: '5', criteria: CRIT, candidates: [{ name: '', ratings: ['4', '5', '3', '4', '4', ''] }, { name: 'Candidate B', ratings: ['5', '3', '4', '3', '5', ''] }, { name: 'Candidate C', ratings: ['3', '4', '5', '5', '3', ''] }] });
near('scorecard: A', sc.candidates[0].score, 4.05); near('scorecard: B', sc.candidates[1].score, 4); near('scorecard: C', sc.candidates[2].score, 3.95);
eq('scorecard: best, no tie, weights add up', [sc.best, sc.tie, sc.sum100, sc.equal, sc.criteria.length, sc.candidates[0].name], [0, false, true, false, 5, 'Candidate A']);
near('scorecard: percent of the maximum', sc.candidates[0].pct, 81);
ok('scorecard: text sheet has the role, every criterion and the formula', /^Interview scorecard: Senior Backend Engineer\n/.test(sc.text) && CRIT.slice(0, 5).every(function (c) { return sc.text.indexOf(c.name) > 0; }) && /Technical skills \(weight 30%\)/.test(sc.text) && /sum of \(rating × weight\) ÷ sum of weights/.test(sc.text), sc.text);
eq('scorecard: legend of a 5-point scale has a middle', sc.legend, '1 = well below what the role needs, 3 = meets it, 5 = well above');
sc = T.scorecard({ criteria: [{ name: 'A' }, { name: 'B' }, { name: 'C' }], candidates: [{ ratings: ['5', '3', '1'] }] });
eq('scorecard: no weights means equal weights', [sc.equal, sc.candidates[0].score], [true, 3]); near('scorecard: equal shares', sc.criteria[0].share, 100 / 3);
sc = T.scorecard({ criteria: [{ name: 'A', weight: '3' }, { name: 'B', weight: '1' }], candidates: [{ ratings: ['4', '2'] }, { ratings: ['4', ''] }, { ratings: ['9', '2'] }, { ratings: ['', ''] }] });
eq('scorecard: weights that do not add up to 100 are shares', [sc.sum100, sc.criteria[0].share, sc.candidates[0].score], [false, 75, 3.5]);
eq('scorecard: a half-rated candidate is not complete and not the best', [sc.candidates[1].complete, sc.candidates[1].rated, sc.candidates[1].of, sc.candidates[1].score, sc.best], [false, 1, 2, 4, 0]);
eq('scorecard: a rating outside the scale is left out and counted', [sc.candidates[2].bad, sc.candidates[2].score, sc.candidates[2].complete], [1, 2, false]);
eq('scorecard: an unrated candidate has no score', [sc.candidates[3].score, sc.candidates[3].pct], [null, null]);
sc = T.scorecard({ max: '10', criteria: [{ name: 'A', weight: '50' }, { name: 'B', weight: '50' }, { name: 'C', weight: '' }], candidates: [{ ratings: ['8', '6', '1'] }, { ratings: ['6', '8', '10'] }] });
eq('scorecard: a tie, a 10-point scale, an unweighted criterion', [sc.tie, sc.best, sc.max, sc.unweighted, sc.candidates[0].score, sc.candidates[0].of], [true, 0, 10, ['C'], 7, 2]);
eq('scorecard: decimal comma in a rating', T.scorecard({ criteria: [{ name: 'A', weight: '1' }], candidates: [{ ratings: ['3,5'] }] }).candidates[0].score, 3.5);
eq('scorecard: unknown scale falls back to 5, a 4-point legend has no middle', [T.scorecard({ max: '7' }).max, T.scorecard({ max: '4' }).legend], [5, '1 = well below what the role needs, 4 = well above']);
sc = T.scorecard({});
eq('scorecard: empty', [sc.criteria, sc.candidates, sc.best, sc.text], [[], [], -1, '']);

/* thank-you email */
const TY = { to: 'Dana', name: 'Alex Morgan', role: 'Senior Backend Engineer', company: 'Acme', when: 'this morning', topic: 'The move from monthly releases to weekly ones.', add: 'it is the kind of change I led in my last job' };
['short', 'warm', 'formal'].forEach(function (tone) {
  const m = T.thankYou(Object.assign({}, TY, { tone: tone }));
  ok('thank-you ' + tone + ' clean', !/undefined|NaN|\[| {2}| [.,]|\.\./.test(m.text) && /^Subject: Thank you for the Senior Backend Engineer interview\n\n/.test(m.text) && /\nAlex Morgan$/.test(m.text), m.text);
  ok('thank-you ' + tone + ' has the facts', ['Dana', 'Senior Backend Engineer', 'at Acme', 'this morning', 'the move from monthly releases to weekly ones', 'It is the kind of change I led in my last job.'].every(function (x) { return m.text.indexOf(x) >= 0; }), m.text);
  const e = T.thankYou({ tone: tone });
  ok('empty thank-you ' + tone + ' uses placeholders', /\[job title\]/.test(e.text) && /\[one thing you discussed\]/.test(e.text) && /\[Your name\]$/.test(e.text) && !/undefined|NaN| {2}/.test(e.text) && e.subject === 'Thank you for the interview', e.text);
});
{
  const base = { name: 'Alex', to: 'Ms Rivera', role: 'Product Designer', company: 'Acme', start: 'Monday, 4 January', by: 'Friday', reason: 'I chose another role' };
  const acc = T.offerResponse(Object.assign({}, base, { mode: 'accept' })), dec = T.offerResponse(Object.assign({}, base, { mode: 'decline' })), tim = T.offerResponse(Object.assign({}, base, { mode: 'time' }));
  ok('offer response: accept says yes and the start date', /delighted to accept/.test(acc.body) && /Monday, 4 January/.test(acc.body) && /^Offer acceptance/.test(acc.subject));
  ok('offer response: decline says no clearly', /decided not to accept/.test(dec.body) && /I chose another role\./.test(dec.body));
  ok('offer response: time names the date', /until Friday/.test(tim.body));
  ok('offer response: unknown mode accepts', T.offerResponse({ mode: 'x' }).text === T.offerResponse({ mode: 'accept' }).text);
  ok('offer response: empty fields leave brackets', /\[job title\]/.test(T.offerResponse({}).text) && /\[start date\]/.test(T.offerResponse({}).text));
  const r1 = T.rejection({ stage: 'application', candidate: 'Jordan', role: 'AE', company: 'Acme', from: 'Sam' }), r2 = T.rejection({ stage: 'final', keep: 'yes', feedback: 'others had more hospital sales' });
  ok('rejection: application thanks for applying', /applying for the AE position at Acme/.test(r1.body) && !/keep your details/.test(r1.body));
  ok('rejection: final round, feedback and keep', /every stage/.test(r2.body) && /Others had more hospital sales\./.test(r2.body) && /keep your details/.test(r2.body));
}
{
  const r = T.costOfVacancy({ revenue: '12,000,000', staff: '80', days: '45', extra: '6,000' }), q = T.costOfVacancy({ salary: '95000', mult: '1.5', days: '7' });
  ok('cost of vacancy: revenue per employee per working day', Math.round(r.perDay) === 577 && r.method === 'revenue');
  ok('cost of vacancy: 45 days = 32 working days plus cover', Math.round(r.workDays) === 32 && Math.round(r.total) === Math.round(577 * 0 + r.perDay * 45 * 5 / 7 + 6000));
  ok('cost of vacancy: from pay with a multiple', q.method === 'salary' && Math.round(q.perDay) === Math.round(95000 * 1.5 / 260));
  ok('cost of vacancy: nothing to go on', T.costOfVacancy({ days: '10' }) === null);
}
ok('thank-you tones differ', T.thankYou(Object.assign({}, TY, { tone: 'warm' })).body !== T.thankYou(Object.assign({}, TY, { tone: 'formal' })).body);
ok('thank-you: unknown tone is the short one', T.thankYou(Object.assign({}, TY, { tone: 'x' })).text === T.thankYou(Object.assign({}, TY, { tone: 'short' })).text);
ok('thank-you: short is the shortest', T.wordCount(T.thankYou(Object.assign({}, TY, { tone: 'short' })).body) < T.wordCount(T.thankYou(Object.assign({}, TY, { tone: 'warm' })).body));

/* resignation letter */
const RS = { name: 'Alex Morgan', to: 'Dana Lee', title: 'Senior Backend Engineer', company: 'Acme Inc.', lastDay: '2026-11-27', date: '2026-11-13', notice: "2 weeks' notice", thanks: true, thanksFor: 'The chance to lead the payments project.', handover: true, handoverWhat: 'finish the release notes' };
let rl = T.resignation(RS);
ok('resignation email clean', !/undefined|NaN|\[| {2}|\.\./.test(rl.text) && /^Subject: Resignation: Alex Morgan\n\nDear Dana Lee,\n\n/.test(rl.text) && /Best regards,\nAlex Morgan$/.test(rl.text), rl.text);
ok('resignation: last day written out with its weekday', rl.text.indexOf('My last working day will be Friday, November 27, 2026, which gives 2 weeks of notice.') > 0, rl.text);
ok('resignation: thanks and handover', rl.text.indexOf('and in particular for the chance to lead the payments project.') > 0 && rl.text.indexOf('Before my last day I can finish the release notes.') > 0, rl.text);
eq('resignation: days between the letter and the last day', rl.days, 14);
rl = T.resignation(Object.assign({}, RS, { format: 'letter', thanks: false, handover: false, notice: 'one month' }));
ok('resignation letter: date on top, no subject, no thanks, neutral close', /^November 13, 2026\n\nDear Dana Lee,/.test(rl.text) && !/Subject|Thank you|handover/.test(rl.text) && /Please let me know what you need from me before I leave\.\n\nSincerely,\nAlex Morgan$/.test(rl.text) && /one month of notice/.test(rl.text), rl.text);
rl = T.resignation({});
ok('empty resignation uses placeholders', ['[manager’s name]', '[job title]', '[company]', '[last working day]', '[Your name]'].every(function (x) { return rl.text.indexOf(x) >= 0; }) && !/undefined|NaN| {2}/.test(rl.text) && rl.days === null, rl.text);
eq('resignation: an impossible date is a blank, not a wrong date', /\[last working day\]/.test(T.resignation({ lastDay: '2026-02-31' }).text), true);
eq('resignation: a last day before the letter is reported', T.resignation({ date: '2026-11-13', lastDay: '2026-11-01' }).days, -12);

/* raise request */
const RR = { to: 'Dana', name: 'Alex Morgan', title: 'Support Team Lead', since: 'In March 2025.', current: '80,000', target: '88k', cur: '$', achievements: '- Cut reply time from two days to nine hours\n2. Trained four new team members\n\n• Wrote the help articles', market: '$85,000 to $92,000', source: 'advertised salaries on Hiring Right Now.' };
let rq = T.raiseRequest(RR);
ok('raise request clean', !/undefined|NaN|\[| {2}|\.\./.test(rq.text) && /^Subject: Request to review my pay\n\nHi Dana,/.test(rq.text) && /Thank you,\nAlex Morgan$/.test(rq.text), rq.text);
eq('raise request: percent, per year, per month', [rq.pct, rq.diff, rq.perYear, T.roundTo(rq.perMonth, 2)], [10, 8000, 8000, 666.67]);
ok('raise request: both figures and the percent in the text', rq.text.indexOf('My pay is $80,000 a year. I am asking for $88,000, an increase of 10%.') > 0, rq.text);
ok('raise request: results as a clean list', /\n- Cut reply time from two days to nine hours\n- Trained four new team members\n- Wrote the help articles\n/.test(rq.text) && !/- - |2\. Trained|•/.test(rq.text), rq.text);
ok('raise request: when the pay last changed, and the market figure with its source', rq.text.indexOf('It last changed in March 2025.') > 0 && rq.text.indexOf('is $85,000 to $92,000 (source: advertised salaries on Hiring Right Now).') > 0, rq.text);
rq = T.raiseRequest({ current: '5000', target: '5400', period: 'month', cur: '€', market: '5.500' });
eq('raise request: monthly pay', [rq.pct, rq.perMonth, rq.perYear], [8, 400, 4800]);
ok('raise request: currency, period and a market figure typed as a number', /€5,000 a month/.test(rq.text) && /an increase of 8%/.test(rq.text) && /is €5,500\./.test(rq.text), rq.text);
rq = T.raiseRequest({ current: '90000', target: '85000' });
ok('raise request: a lower figure is not called an increase', rq.pct < 0 && !/increase/.test(rq.text));
rq = T.raiseRequest({});
ok('empty raise request uses placeholders', /\[current pay\]/.test(rq.text) && /\[the pay you are asking for\]/.test(rq.text) && /\[Add two or three results/.test(rq.text) && rq.pct === null && rq.perMonth === null && !/undefined|NaN| {2}/.test(rq.text), rq.text);
eq('raise request: rounding of a third of a percent', /an increase of 3\.3%/.test(T.raiseRequest({ current: '60000', target: '62000' }).text), true);

/* reference request */
const RF = { to: 'Sam', name: 'Alex Morgan', role: 'Engineering Manager', company: 'Acme', by: 'the end of next week', relation: 'You managed me at Example Co from 2021 to 2023.', points: 'The payments rewrite\nHow I worked with support', attach: true };
['warm', 'formal', 'short'].forEach(function (tone) {
  ['call', 'letter', 'form', 'linkedin'].forEach(function (how) {
    const m = T.referenceRequest(Object.assign({}, RF, { tone: tone, how: how }));
    ok('reference ' + tone + '/' + how + ' clean', !/undefined|NaN|\[| {2}| [.,]|\.\./.test(m.text) && /^Subject: /.test(m.text) && /\nAlex Morgan$/.test(m.text), m.text);
    ok('reference ' + tone + '/' + how + ' has the facts', ['Sam', 'an Engineering Manager role at Acme', 'We worked together when you managed me at Example Co from 2021 to 2023', 'the end of next week', '- The payments rewrite', 'attached'].every(function (x) { return m.text.indexOf(x) >= 0; }), m.text);
  });
});
ok('reference: each way of giving it has its own sentence', ['call', 'letter', 'form', 'linkedin'].map(function (h) { return T.referenceRequest(Object.assign({}, RF, { how: h })).body; }).filter(function (b, i, a) { return a.indexOf(b) === i; }).length === 4);
let rf = T.referenceRequest({});
ok('empty reference request is still a whole email', /a new role/.test(rf.text) && /\[Your name\]$/.test(rf.text) && !/undefined|NaN| {2}|attached|these are the points/.test(rf.text), rf.text);
ok('reference: company without a role', /applying for a role at Acme/.test(T.referenceRequest({ company: 'Acme' }).text));

/* LinkedIn headline and About */
let li = T.linkedin({ role: 'Senior Backend Engineer', years: '8', strengths: 'Python, PostgreSQL, payments', next: 'Senior backend roles at product companies.', result: 'I cut page load time from 4 s to 1.2 s' });
eq('linkedin: three headlines', li.headlines.map(function (h) { return h.text; }), ['Senior Backend Engineer | Python | PostgreSQL | payments', 'Senior Backend Engineer with 8 years of experience in Python, PostgreSQL and payments',
  'Senior Backend Engineer | Python, PostgreSQL, payments | Open to Senior backend roles at product companies']);
eq('linkedin: counters', li.headlines.map(function (h) { return [h.length, h.left]; }), [[56, 164], [85, 135], [106, 114]]);
eq('linkedin: About paragraph', li.about, 'I am a Senior Backend Engineer with 8 years of experience. My strongest areas are Python, PostgreSQL and payments. I cut page load time from 4 s to 1.2 s. I am now looking for Senior backend roles at product companies. The best way to reach me is a message here on LinkedIn.');
eq('linkedin: About length is counted', li.aboutLength, li.about.length);
const LONG = 'a very long strength that goes on and on about one particular field of work and its many branches';
li = T.linkedin({ role: 'Principal Engineer', strengths: [LONG, LONG + ' two', LONG + ' three', LONG + ' four', 'fifth'].join(', '), next: LONG + ' ' + LONG });
ok('linkedin: every headline stays inside 220 characters', li.headlines.length >= 2 && li.headlines.every(function (h) { return h.length <= 220 && h.length === h.text.length && h.left === 220 - h.length; }), li.headlines);
ok('linkedin: strengths are dropped from the end, the title stays', li.headlines.every(function (h) { return h.text.indexOf('Principal Engineer') === 0; }) && li.headlines[0].text.indexOf(' four') < 0, li.headlines);
eq('linkedin: at most four strengths are used', li.strengths.length, 4);
li = T.linkedin({ role: 'x'.repeat(300) });
ok('linkedin: a title longer than the limit is cut to it', li.headlines.length === 1 && li.headlines[0].length === 220);
li = T.linkedin({ role: 'Nurse' });
eq('linkedin: identical variants are shown once', [li.headlines.length, li.headlines[0].text, li.about], [1, 'Nurse', 'I work as a Nurse. The best way to reach me is a message here on LinkedIn.']);
eq('linkedin: empty form', [T.linkedin({}).empty, T.linkedin({ role: 'Nurse' }).empty, T.linkedin({}).headlines[0].text], [true, false, '[Your job title]']);
ok('linkedin: one strength, no years', /^Analyst focused on SQL$/.test(T.linkedin({ role: 'Analyst', strengths: 'SQL' }).headlines[1].text) && /My strongest area is SQL\./.test(T.linkedin({ role: 'Analyst', strengths: 'SQL' }).about));
eq('linkedin: the limits', [T.HEADLINE_MAX, T.ABOUT_MAX], [220, 2600]);

/* interview answer (STAR) */
const STAR = { situation: 'Last year our support team at Example Co was answering about 900 tickets a week, and a third of them were the same question about failed card payments. Replies were taking two days.',
  task: 'As the team lead, I was asked to bring the reply time under one day without hiring more people.',
  action: 'I read 200 of the payment tickets and grouped them by cause. I found that most came from one unclear error message, so I wrote a clearer message and asked the product team to ship it. I also wrote a help article and a saved reply for my team, and I checked the numbers every Monday for six weeks.',
  result: 'Payment tickets fell from about 300 to 90 a week, and our average reply time dropped from two days to nine hours.', learned: 'It taught me to look for the cause of a problem before asking for more people.' };
let st = T.star(STAR);
eq('star: the example is 149 words, 64 seconds', [st.words, st.seconds, st.time, st.fixes, st.complete], [149, 64, '1 min 4 s', 0, true]);
eq('star: words per part', [st.parts.situation, st.parts.task, st.parts.action, st.parts.result], [33, 19, 59, 22]);
eq('star: five paragraphs in order', st.text.split('\n\n').map(function (p) { return p.split(' ')[0]; }), ['Last', 'As', 'I', 'Payment', 'It']);
ok('star: every check passes', st.checks.length === 4 && st.checks.every(function (c) { return c.level === 'ok'; }), st.checks);
eq('star: speaking time', [T.speak(0), T.speak(45), T.speak(60), T.speak(64), T.speak(125.4)], ['0 s', '45 s', '1 min', '1 min 4 s', '2 min 5 s']);
eq('star: 140 words take one minute', Math.round(140 / T.WPM * 60), 60);
st = T.star(Object.assign({}, STAR, { result: '' }));
ok('star: a missing result is the first thing to fix', st.checks[0].level === 'fix' && /The result is missing/.test(st.checks.map(function (c) { return c.t; }).join('|')) && st.complete === false, st.checks);
st = T.star(Object.assign({}, STAR, { action: 'We read the tickets and we grouped them by cause, i.e. by the message shown. Then we wrote a clearer message and we shipped it.' }));
ok('star: an action without “I” is flagged, and “i.e.” is not an “I”', st.checks.some(function (c) { return c.level === 'fix' && /never says “I”/.test(c.t) && /“We” appears 4 times/.test(c.d); }), st.checks);
st = T.star(Object.assign({}, STAR, { action: 'We read the tickets. We grouped them. I wrote a clearer message and we shipped it together with the product team after a review.' }));
ok('star: more “we” than “I”', st.checks.some(function (c) { return c.level === 'warn' && /More “we” than “I”/.test(c.t); }), st.checks);
ok('star: a setup longer than the action is flagged', st.checks.some(function (c) { return /setup is longer/.test(c.t); }));
st = T.star(Object.assign({}, STAR, { result: 'Customers were happier and the team was calmer.' }));
ok('star: no number in the result', st.checks.some(function (c) { return c.level === 'warn' && /No number in the result/.test(c.t); }));
ok('star: a number word counts', T.star(Object.assign({}, STAR, { result: 'Reply time fell by half.' })).checks.some(function (c) { return /result has a number/.test(c.t); }));
st = T.star({ situation: 'It was busy.', task: 'I had to help.', action: 'I helped.', result: 'It worked.' });
ok('star: a very short answer', st.seconds < 45 && st.checks.some(function (c) { return c.level === 'fix' && /Too short/.test(c.t); }), st);
st = T.star(Object.assign({}, STAR, { action: (STAR.action + ' ').repeat(5) }));
ok('star: a very long answer', st.seconds > 120 && st.checks.some(function (c) { return c.level === 'fix' && /Too long/.test(c.t); }), st.seconds);
st = T.star(Object.assign({}, STAR, { learned: '', action: STAR.action.replace(' and I checked the numbers every Monday for six weeks', '') }));
ok('star: 45 to 59 seconds is marked to check', st.seconds >= 45 && st.seconds < 60 && st.checks.some(function (c) { return c.level === 'warn' && /A little short/.test(c.t); }), st.seconds);
eq('star: empty', [T.star({}).empty, T.star({}).words, T.star({ learned: '  ' }).empty], [true, 0, true]);
ok('star: sentences get a capital and a full stop', T.star({ action: 'i called the customer' }).text === 'I called the customer.');

/* resume bullet point */
let bp = T.bullet({ verb: 'rebuilt', what: 'The checkout flow in React.', result: 'Cut failed payments by 30%.' });
eq('bullet: three variants', bp.variants.map(function (v) { return v.text; }), ['Rebuilt the checkout flow in React, which cut failed payments by 30%', 'Rebuilt the checkout flow in React and cut failed payments by 30%', 'Cut failed payments by 30% by rebuilding the checkout flow in React']);
eq('bullet: lengths and lines', bp.variants.map(function (v) { return [v.length, v.lines]; }), [[68, 1], [65, 1], [67, 1]]);
eq('bullet: all four checks pass', [bp.passed, bp.of, bp.kind, bp.checks.map(function (c) { return c.level; }).join()], [4, 4, 'verb', 'ok,ok,ok,ok']);
eq('bullet: -ing forms', ['Built', 'cut', 'Led', 'Managed', 'shipped', 'Simplified', 'Set up', 'agreed', 'Xyz', ''].map(T.gerund), ['building', 'cutting', 'leading', 'managing', 'shipping', 'simplifying', 'setting up', 'agreeing', '', '']);
ok('bullet: every verb on the list has an -ing form', T.STRONG.length > 90 && T.STRONG.every(function (v) { return /ing$/.test(T.gerund(v)); }), T.STRONG.filter(function (v) { return !/ing$/.test(T.gerund(v)); }));
ok('bullet: the list has no duplicates and is in past tense', T.STRONG.filter(function (v, i, a) { return a.indexOf(v) !== i; }).length === 0);
bp = T.bullet({ verb: 'Responsible', what: 'for the checkout page', result: '' });
ok('bullet: a weak opener, duty wording and a missing result are fixes', ['weak way to start', 'Duty wording: “responsible for”', 'No result'].every(function (x) { return bp.checks.some(function (c) { return c.level === 'fix' && c.t.indexOf(x) >= 0; }); }) && bp.variants.length === 1 && bp.passed === 0, bp.checks);
bp = T.bullet({ verb: 'Refurbished', what: 'three shop floors', result: '30% more visitors' });
eq('bullet: a result that is not a verb phrase gets neutral joins', bp.variants.map(function (v) { return v.text; }), ['Refurbished three shop floors: 30% more visitors', 'Refurbished three shop floors; 30% more visitors', '30% more visitors after refurbishing three shop floors']);
ok('bullet: an unlisted verb is a note, not a fault', bp.checks.some(function (c) { return c.level === 'info' && /not on our verb list/.test(c.t); }) && bp.checks.some(function (c) { return c.level === 'info' && /past-tense verb/.test(c.t); }) && bp.passed === bp.of, bp.checks);
bp = T.bullet({ verb: 'Led', what: 'a team of six', result: 'raising sales in the region' });
eq('bullet: an -ing result is joined with a comma', bp.variants.map(function (v) { return v.text; }), ['Led a team of six, raising sales in the region']);
ok('bullet: “six” counts as a number', bp.checks.some(function (c) { return c.t === 'Has a number'; }));
bp = T.bullet({ verb: 'Managed', what: 'my team and I worked on the roadmap', result: 'improved morale' });
ok('bullet: no number, “worked on” and “I” are all reported', bp.checks.some(function (c) { return c.level === 'warn' && c.t === 'No number'; }) && bp.checks.some(function (c) { return /worked on/.test(c.t); }) && bp.checks.some(function (c) { return /Leave out “I”/.test(c.t); }), bp.checks);
bp = T.bullet({ verb: 'Built', what: 'x '.repeat(120).trim(), result: 'saved 5 hours a week' });
ok('bullet: a line of more than 200 characters is long', bp.variants[0].lines === 3 && bp.checks.some(function (c) { return c.level === 'warn' && /^Long: /.test(c.t); }), bp.variants[0].length);
ok('bullet: a very short line', T.bullet({ verb: 'Cut', what: 'costs', result: 'saved 5%' }).checks.some(function (c) { return /^Short: /.test(c.t); }));
eq('bullet: empty', [T.bullet({}).empty, T.bullet({}).variants.length, T.bullet({ verb: ' ' }).empty], [true, 0, true]);
ok('bullet: fixes come first', T.bullet({ verb: 'Helped', what: 'with reports', result: 'saved 5 hours' }).checks[0].level === 'fix');

/* date ranges in text, and gaps */
const NOW = '2026-11-13', lab = function (r) { return T.monthLabel(r.start) + '..' + T.monthLabel(r.end); };
eq('ranges: month names', T.dateRanges('Developer, Acme\nJan 2021 – Mar 2023', NOW).map(lab), ['Jan 2021..Mar 2023']);
eq('ranges: full month names and a hyphen', T.dateRanges('January 2021 - March 2023', NOW).map(lab), ['Jan 2021..Mar 2023']);
eq('ranges: “Sept.” and “Present”', T.dateRanges('Sept. 2019 to Present', NOW).map(function (r) { return [lab(r), r.open]; }), [['Sep 2019..Nov 2026', true]]);
eq('ranges: years only run from January to December', T.dateRanges('BSc, Example University, 2019–2021', NOW).map(function (r) { return [lab(r), r.years]; }), [['Jan 2019..Dec 2021', true]]);
eq('ranges: month/year', T.dateRanges('03/2020 - present', NOW).map(lab), ['Mar 2020..Nov 2026']);
eq('ranges: year-month and dotted forms', T.dateRanges('2020-03 – 2022-11 and 03.2020 — 11.2022', NOW).map(lab), ['Mar 2020..Nov 2022', 'Mar 2020..Nov 2022']);
eq('ranges: mixed ends and other words for today', ['Mar 2020 – 2022', '2018 until now', '2024 to date', 'June 2025 through current'].map(function (s) { return T.dateRanges(s, NOW).map(lab)[0]; }), ['Mar 2020..Dec 2022', 'Jan 2018..Nov 2026', 'Jan 2024..Nov 2026', 'Jun 2025..Nov 2026']);
eq('ranges: the line and its number are kept', T.dateRanges('a\nb\nEngineer, 2019 - 2021 (Berlin)', NOW).map(function (r) { return [r.at, r.line]; }), [[2, 'Engineer, 2019 - 2021 (Berlin)']]);
eq('ranges: a year in progress ends today, not in December', T.dateRanges('2024 – 2026', NOW).map(lab), ['Jan 2024..Nov 2026']);
eq('ranges: not dates', ['2000-2500 users', '13/2020 - 01/2021', 'Mar 2023 – Jan 2021', '2031 – 2033', 'call 555-2019', 'May the 4th', 'present – 2021', '1200 - 1500 requests', ''].map(function (s) { return T.dateRanges(s, NOW).length; }), [0, 0, 0, 0, 0, 0, 0, 0, 0]);
const R = function (text) { return T.dateRanges(text, NOW); };
eq('gaps: six empty months are not a gap', T.gaps(R('Jan 2021 – Mar 2023\nOct 2023 – present'), NOW).length, 0);
let gp = T.gaps(R('Nov 2023 – present\nJan 2021 – Mar 2023'), NOW);
eq('gaps: seven empty months are, in any order of the lines', gp.map(function (g) { return [g.months, T.monthLabel(g.from), T.monthLabel(g.to), g.after.line, g.before.line]; }), [[7, 'Apr 2023', 'Oct 2023', 'Jan 2021 – Mar 2023', 'Nov 2023 – present']]);
eq('gaps: years only, a whole year missing', T.gaps(R('2015 – 2017\n2019 – 2021\n2021 – present'), NOW).map(function (g) { return g.months; }), [12]);
eq('gaps: years only, touching years are not a gap', T.gaps(R('2015 – 2017\n2018 – present'), NOW).length, 0);
eq('gaps: a long job covers a short break inside it', T.gaps(R('2015 – present\nJan 2016 – Mar 2016\nJan 2020 – Feb 2020'), NOW).length, 0);
gp = T.gaps(R('Jan 2019 – Feb 2021\n03/2022 - 01/2025'), NOW);
eq('gaps: time since the last entry counts', gp.map(function (g) { return [g.months, !!g.before]; }), [[12, true], [22, false]]);
eq('gaps: a job that ended four months ago is not a gap', T.gaps(R('Jan 2019 – Jul 2026'), NOW).length, 0);
eq('gaps: nothing to compare', [T.gaps([], NOW).length, T.gaps(null, NOW).length], [0, 0]);
eq('gaps: another threshold', T.gaps(R('Jan 2021 – Mar 2023\nOct 2023 – present'), NOW, 3).length, 1);

/* resume review */
const WEAK_CV = 'Jordan Example\nSoftware Developer\njordan@example.com · Springfield\n\nAbout me\nI am a passionate and hard-working developer who loves technology and is always eager to learn new things. I have worked in many different teams and on many ' +
  'different projects over the years, and I believe that communication and teamwork are the key to success. I am looking for a company where I can grow, take on new challenges and make a real difference with my skills.\n\n' +
  'Skills\nPython, Django, JavaScript, React, PostgreSQL, MySQL, MongoDB, Redis, Docker, Kubernetes, AWS, Terraform, Jenkins, Git, Linux, Kafka, GraphQL, Elasticsearch, TypeScript, Go, Rust, PHP\n\n' +
  'Experience\nSoftware Developer, Example Shop Ltd\n03/2022 - present\n- Responsible for the backend of the online store\n- Worked on the checkout and the payment pages\n' +
  '- Built a Python service that sends order emails and cut failed deliveries from 4% to 1%\n- Participated in code reviews and daily meetings\n\nJunior Developer, Sample Agency\nJan 2019 – Feb 2021\n- Helped with websites for clients of the agency\n' +
  '- Duties included fixing bugs, writing tests and updating old pages when clients asked for changes to their content or their design, and talking to clients on the phone about what they wanted to change, which often took most of the day\n' +
  '- Moved 12 client sites from PHP to Django\n\nEducation\nBSc Computer Science, Example University\n2015 – 2018';
let rv = T.resumeReview(WEAK_CV, NOW);
const pts = function (r) { const o = {}; r.checks.forEach(function (c) { o[c.id] = c.points; }); return o; };
eq('review: the example scores 2 out of 10', [rv.score, rv.verdict], [2, 'Hard to skim: start with the first fixes on the list']);
eq('review: points of each check', pts(rv), { screen: 0, wording: 0, numbers: 1, skills: 0, gaps: 0.5, length: 0.5 });
eq('review: the six checks are worth 10 points', [rv.checks.map(function (c) { return c.max; }), rv.checks.reduce(function (s, c) { return s + c.max; }, 0)], [[2, 2, 2, 1.5, 1, 1.5], 10]);
eq('review: the score is the sum of the checks', rv.score, rv.checks.reduce(function (s, c) { return s + c.points; }, 0));
eq('review: what was counted', [rv.words, rv.firstJob, rv.summaryWords, rv.bullets, rv.withNumbers, rv.skills.length, rv.unused.length, rv.duty, rv.ranges.length, rv.gaps.length], [220, 13, 67, 7, 2, 22, 19, 5, 3, 1]);
eq('review: the gap is the year between the two jobs', [rv.gaps[0].months, T.monthLabel(rv.gaps[0].from), T.monthLabel(rv.gaps[0].to)], [12, 'Mar 2021', 'Feb 2022']);
const fixOf = function (r, rx) { return r.fixes.filter(function (f) { return rx.test(f.t); })[0]; };
ok('review: duty lines are quoted in the visitor’s own words', fixOf(rv, /describe duties/).q.join('|').indexOf('- Responsible for the backend of the online store|- Worked on the checkout') === 0 && fixOf(rv, /describe duties/).q.length === 5, fixOf(rv, /describe duties/));
ok('review: the gap quotes both date lines', JSON.stringify(fixOf(rv, /A break of 12 months/).q) === JSON.stringify(['Jan 2019 – Feb 2021', '03/2022 - present']));
ok('review: the long line is quoted, shortened', /^- Duties included fixing bugs.*…$/.test(fixOf(rv, /longer than two lines/).q[0]) && fixOf(rv, /longer than two lines/).q[0].length <= 140);
ok('review: first-screen findings quote the summary and the skills line', /^I am a passionate/.test(fixOf(rv, /summary runs to 67 words/).q[0]) && /^Python, Django/.test(fixOf(rv, /22 skills are listed before any job/).q[0]) && !!fixOf(rv, /first job starts on line 13/));
ok('review: unused skills are named', /JavaScript, React, PostgreSQL/.test(fixOf(rv, /19 of 22 listed skills/).d) && rv.unused.indexOf('Python') < 0 && rv.unused.indexOf('Django') < 0 && rv.unused.indexOf('PHP') < 0, rv.unused);
ok('review: bullets without a number are quoted', fixOf(rv, /2 of 7 bullet points/).q.length === 3);
ok('review: the costliest checks come first', /first job|summary|skills are listed/.test(rv.fixes[0].t) && /break of/.test(rv.fixes[rv.fixes.length - 1].t), rv.fixes.map(function (f) { return f.t; }));
eq('review: weaknesses are the checks that lost points, strengths the rest', [rv.weaknesses.length, rv.strengths.length], [6, 0]);
const GOOD_CV = 'Alex Morgan\nSenior Backend Engineer\nalex@example.com · Berlin\n\nSummary\nBackend engineer with 8 years of experience building payment APIs and data pipelines in Python and Go.\n\n' +
  'Experience\nSenior Backend Engineer, Example Co\nMar 2021 – present\n- Built a payments API in Python and PostgreSQL that handles 4 million requests a day\n- Cut p95 latency from 900 ms to 250 ms by adding Redis caching\n' +
  '- Moved 30 services to Kubernetes on AWS with Terraform\n- Mentored four engineers who now run the on-call rota\n- Wrote the runbooks that the support team uses during incidents\n\n' +
  'Backend Engineer, Sample Ltd\nJun 2017 – Feb 2021\n- Wrote REST and GraphQL services in Python for 200 business customers\n- Set up CI/CD with GitHub Actions and cut release time from 2 hours to 15 minutes\n' +
  '- Rebuilt the billing export in Go, which removed 12 hours of manual work a month\n- Led the move from MySQL to PostgreSQL without downtime for customers\n\n' +
  'Junior Developer, Demo Studio\nJul 2014 – May 2017\n- Built internal tools in Python for a team of 25 people\n- Automated the weekly sales report, saving 6 hours a week\n- Fixed bugs in the customer portal and wrote the first test suite for it\n' +
  '- Trained two interns who later joined the team as developers\n\nEducation\nBSc Computer Science, Example University\n2010 – 2014\n\nSkills\nPython, Go, PostgreSQL, Redis, Kubernetes, AWS, Terraform, GraphQL, CI/CD\n\n' +
  'Projects\nOpen-source rate limiter for Python web services, used by three small companies in production since 2022. I maintain the project, review contributions and write the release notes. ' +
  'Speaker at two local meetups about running PostgreSQL at scale, with slides and recordings published online for anyone to read and reuse in their own teams and study groups.';
rv = T.resumeReview(GOOD_CV, NOW);
eq('review: a sound resume gets full points', [rv.score, rv.verdict, rv.fixes.length, rv.weaknesses.length, rv.strengths.length], [10, 'Reads well on a first skim', 0, 0, 6]);
eq('review: what was counted in it', [rv.firstJob <= 12, rv.bullets, rv.withNumbers, rv.skills.length, rv.unused.length, rv.ranges.length, rv.gaps.length, rv.pages], [true, 13, 8, 9, 0, 4, 0, 'about one page']);
ok('review: strengths name their check', rv.strengths.map(function (s) { return s.name; }).join() === 'First screen,Wording,Numbers,Skills,Gaps,Length');
rv = T.resumeReview(GOOD_CV.replace('Mar 2021 – present', 'Spring 2021 onwards').replace('Jun 2017 – Feb 2021', 'four years').replace('Jul 2014 – May 2017', 'three years').replace('2010 – 2014', 'class of 2014').replace('since 2022', 'for years'), NOW);
eq('review: unreadable dates are said plainly and cost half a point', [pts(rv).gaps, !!fixOf(rv, /dates could not be read/), rv.ranges.length], [0.5, true, 0]);
rv = T.resumeReview(GOOD_CV.replace('\n\nSkills\nPython, Go, PostgreSQL, Redis, Kubernetes, AWS, Terraform, GraphQL, CI/CD', ''), NOW);
eq('review: no skills line', [pts(rv).skills, !!fixOf(rv, /No skills line found/)], [0.5, true]);
rv = T.resumeReview(GOOD_CV.replace('Skills\nPython, Go,', 'Skills: Python, Go,').replace('GraphQL, CI/CD', 'GraphQL, CI/CD\nLanguages: English (fluent), German'), NOW);
eq('review: an inline “Skills:” line and a labelled line inside the block are both read', [rv.skills.slice(0, 2), rv.skills.indexOf('German') > 0, rv.skills.indexOf('English') > 0, pts(rv).skills], [['Python', 'Go'], true, true, 1.5]);
rv = T.resumeReview(GOOD_CV.replace('Mar 2021 – present', 'Mar 2022 – present'), NOW);
eq('review: one gap costs half a point', [pts(rv).gaps, rv.gaps.length, rv.score], [0.5, 1, 9.5]);
rv = T.resumeReview(GOOD_CV.replace('- Built a payments API', '- Responsible for a payments API'), NOW);
eq('review: one duty line costs one point', [pts(rv).wording, rv.duty, rv.score], [1, 1, 9]);
rv = T.resumeReview(GOOD_CV.replace('Experience\n', '').replace('Summary\n', ''), NOW);
eq('review: without headings the first dated line starts the experience', [rv.firstJob != null, pts(rv).wording, rv.bullets], [true, 2, 13]);
rv = T.resumeReview('Pat Example. I am a baker with many years of work in kitchens of every size and kind. '.repeat(8), NOW);
eq('review: text with no job, no dates and no bullets', [pts(rv), rv.firstJob, rv.words], [{ screen: 0, wording: 2, numbers: 0, skills: 0.5, gaps: 0.5, length: 0.5 }, null, 144]);
eq('review: too little text', [T.resumeReview('Alex Morgan, engineer.').error, T.resumeReview('').error, T.resumeReview(null).words], ['short', 'short', 0]);
rv = T.resumeReview(GOOD_CV + ('\n- Shipped one more feature for 10 customers and wrote the notes for the release that followed it').repeat(80), NOW);
eq('review: a very long resume loses the length point', [pts(rv).length, rv.pages, !!fixOf(rv, /more than two pages/)], [0.5, 'more than two pages', true]);
eq('review: the thresholds are the ones printed on the page', T.REVIEW, { screen: 12, summary: 60, before: 10, list: 20, gap: 6, onePage: 650, twoPages: 1300, thin: 250, least: 150 });

/* LinkedIn profile review */
const levels = function (r) { const o = {}; r.items.forEach(function (i) { o[i.level] = (o[i.level] || 0) + 1; }); return o; };
const item = function (r, rx) { return r.items.filter(function (i) { return rx.test(i.t); })[0]; };
let lr = T.linkedinReview({ headline: 'OPEN TO WORK 🚀🚀🚀 | Passionate, results-driven guru | Dream big!',
  about: 'PASSIONATE ABOUT TECHNOLOGY!!! Jordan is a hard-working team player and a true thought leader with a proven track record. Jordan thinks outside the box and always gives everything. Jordan has worked in many companies and loves new challenges.' });
eq('linkedin review: the example has ten things to fix', [lr.fixes, lr.notes, lr.headline, lr.about, levels(lr)], [10, 0, 66, 242, { fix: 1, warn: 9, ok: 1 }]);
ok('linkedin review: “open to work” alone is the first fix and quotes the headline', lr.items[0].level === 'fix' && /only says you are looking/.test(lr.items[0].t) && /^OPEN TO WORK/.test(lr.items[0].q[0]), lr.items[0]);
ok('linkedin review: buzzwords are named', /passionate, results-driven, guru/.test(item(lr, /in the headline: /).t) && /6 buzzwords/.test(item(lr, /in the About text: /).t) && item(lr, /in the About text: /).q.length === 2);
ok('linkedin review: third person, capitals, no number, no contact line', /^Jordan is a hard-working/.test(item(lr, /first person/).q[0]) && item(lr, /Capital letters/).q[0] === 'PASSIONATE ABOUT TECHNOLOGY' && !!item(lr, /No number/) && /loves new challenges\.$/.test(item(lr, /No ask/).q[0]));
ok('linkedin review: three emoji in a headline are counted', /^3 emoji/.test(item(lr, /emoji in the headline/).t));
lr = T.linkedinReview({ headline: 'Senior Backend Engineer | Python, PostgreSQL | Payments',
  about: 'I am a backend engineer with 8 years of experience building payment systems for online shops. I help product teams ship reliable APIs: at Example Co I cut failed charges by 30% for two million users. My strongest areas are Python, PostgreSQL and Kafka. I am now looking for senior backend roles at product companies. The best way to reach me is a message here on LinkedIn.' });
eq('linkedin review: a sound profile has nothing to fix', [lr.fixes, lr.notes, levels(lr)], [0, 0, { ok: 7 }]);
ok('linkedin review: the opening is at most 300 characters and ends at a word', lr.opening.length <= 300 && lr.more === true && lr.about.indexOf === undefined && /\w$/.test(lr.opening), lr.opening);
lr = T.linkedinReview({ headline: 'Engineer '.repeat(30).trim(), about: '' });
ok('linkedin review: a headline over 220 characters quotes what is cut off', lr.headline === 269 && /49 over the limit/.test(lr.items[0].t) && lr.items[0].q[0].length === 49 && !!item(lr, /No About text/), lr.items[0]);
eq('linkedin review: a bare job title is a note, not a fault', T.linkedinReview({ headline: 'Engineer' }).items.filter(function (i) { return i.level === 'info'; }).map(function (i) { return i.t; }), ['The headline uses 8 of 220 characters', 'A job title, but no field or specialty']);
ok('linkedin review: a slogan has no job title', !!item(T.linkedinReview({ headline: 'Helping brands dream bigger every single day' }), /No job title found/));
ok('linkedin review: a company name is not a field', !!item(T.linkedinReview({ headline: 'Manager at Acme Widgets' }), /no field or specialty/));
ok('linkedin review: a headline in capitals', !!item(T.linkedinReview({ headline: 'SENIOR ACCOUNTANT FOR SMALL BUSINESSES' }), /capital letters/));
lr = T.linkedinReview({ headline: 'Nurse | Intensive care', about: 'I am a nurse. '.repeat(200) });
ok('linkedin review: an About text over 2,600 characters', /over the limit/.test(item(lr, /About text is/).t) && lr.about > 2600);
lr = T.linkedinReview({ headline: 'Data analyst | SQL, Python', about: 'I am a data analyst and I turn raw sales tables into weekly reports that people read. Over five years I have built 40 dashboards. '.repeat(3) + 'Message me here.' });
ok('linkedin review: an opening that does not say for whom is a note', item(lr, /who you do it for/).level === 'info' && lr.fixes === 0, lr.items.map(function (i) { return i.level + ' ' + i.t; }));
lr = T.linkedinReview({ about: '⭐ I help teams ⭐ ship ⭐ faster ⭐ for 10 clients ⭐ every year ⭐ write to me ⭐' });
ok('linkedin review: emoji overload in the About text, and a missing headline', /^7 emoji/.test(item(lr, /emoji in the About/).t) && !!item(lr, /No headline/));
eq('linkedin review: empty', [T.linkedinReview({}).empty, T.linkedinReview({ headline: '  ', about: '\n' }).empty, T.linkedinReview({}).fixes], [true, true, 0]);

/* offer check */
const OD = { q: QS, min: 20, date: 'Nov 13, 2026', g: {
  '||': [900, 120, 170].concat(VALS.map(function (v) { return v / 1000; })),
  'engineering||': [500, 130, 180].concat(VALS.map(function (v) { return v / 1000 + 10; })),
  'engineering|Senior|': [200, 150, 210].concat(VALS.map(function (v) { return v / 1000 + 30; })),
  '|Junior|': [60, 70, 95].concat(VALS.map(function (v) { return v / 1000 - 50; })) } };
let oc = T.offerCheck(OD, '151,200', 'engineering', 'Senior');           // this group: median 180, quarters 150 and 210
eq('offer check: 16% below the median, on the lower quarter line', [oc.group.median, oc.group.p25, oc.group.p75, oc.zone, Math.round(oc.diff), oc.wider, oc.verdict], [180000, 150000, 210000, 'mid', -16, false, '16% below the median, inside the middle half: there is room to ask']);
oc = T.offerCheck(OD, '140k', 'engineering', 'Senior');
eq('offer check: below the lower quarter', [oc.pay, oc.zone, oc.verdict, oc.group.n], [140000, 'low', '22% below the median: worth asking for more', 200]);
oc = T.offerCheck(OD, '185000', 'engineering', 'Senior');
eq('offer check: close to the median', [oc.zone, oc.verdict], ['mid', 'Close to the median: in line with what postings advertise']);
eq('offer check: above the median, inside the middle half', T.offerCheck(OD, '200000', 'engineering', 'Senior').verdict, '11% above the median, inside the middle half');
oc = T.offerCheck(OD, '260000', 'engineering', 'Senior');
eq('offer check: above the upper quarter', [oc.zone, oc.verdict], ['high', '44% above the median: higher than three quarters of the advertised ranges']);
ok('offer check: the position among postings', T.offerCheck(OD, '180000', 'engineering', 'Senior').pct === 50 && T.offerCheck(OD, '50000', 'engineering', 'Senior').pct === 0 && T.offerCheck(OD, '900000', 'engineering', 'Senior').pct === 100);
oc = T.offerCheck(OD, '100000', 'engineering', 'Junior');
eq('offer check: too few postings, every category at the same level is used first', [oc.cat, oc.lvl, oc.wider, oc.mixesLevels, oc.mixesCategories, oc.group.n, oc.group.median, oc.verdict], ['', 'Junior', true, false, true, 60, 100000, 'Close to the median of the wider group']);
eq('offer check: …and the same category at any level is given as a second yardstick', [oc.also.cat, oc.also.lvl, oc.also.group.n, oc.also.group.median], ['engineering', '', 500, 160000]);
oc = T.offerCheck(OD, '60000', 'design', 'Junior');
eq('offer check: a low offer in a wider group is not told to ask for more', [oc.cat, oc.lvl, oc.zone, oc.also, oc.verdict], ['', 'Junior', 'low', null, '40% below the median of the wider group: low for that group, which is only a rough guide']);
oc = T.offerCheck(OD, '100000', 'engineering', 'Lead');
eq('offer check: then the same category at any level, said to mix levels', [oc.cat, oc.lvl, oc.wider, oc.mixesLevels, oc.mixesCategories, oc.group.n, oc.also], ['engineering', '', true, true, false, 500, null]);
oc = T.offerCheck(OD, '100000', 'design', 'Lead');
eq('offer check: then all postings', [oc.cat, oc.lvl, oc.wider, oc.mixesLevels, oc.mixesCategories, oc.group.n], ['', '', true, true, true, 900]);
eq('offer check: a wider group gets the position without the advice', [T.offerCheck(OD, '85000', 'design', 'Junior').verdict, T.offerCheck(OD, '300000', 'design', 'Junior').verdict], ['15% below the median of the wider group, inside the middle half', '200% above the median of the wider group: higher than three quarters of its advertised ranges']);
eq('offer check: a category with too few postings, any level', [T.offerCheck(OD, '100000', 'design', '').cat, T.offerCheck(OD, '100000', 'design', '').mixesLevels], ['', false]);
eq('offer check: all categories, any level is not “wider”', T.offerCheck(OD, '150000', '', '').wider, false);
eq('offer check: nothing typed, junk, zero', [T.offerCheck(OD, '', 'engineering', 'Senior'), T.offerCheck(OD, 'abc', '', ''), T.offerCheck(OD, '0', '', '')], [null, null, null]);
eq('offer check: no data at all', [T.offerCheck(null, '150000', '', '').group, T.offerCheck({ q: QS, g: {} }, '150000', 'engineering', 'Senior').group], [null, null]);
eq('offer check: a European figure', T.offerCheck(OD, '150.000', '', '').pay, 150000);

// ---- an old resume read back into the builder
const CV1 = ['JANE DOE', 'Senior Backend Engineer', 'Berlin, Germany | jane.doe@mail.com | +49 151 2345 6789 | linkedin.com/in/janedoe', '',
  'SUMMARY', 'Backend engineer with 8 years in payments. Built systems that handle 2M transactions a day.', '',
  'EXPERIENCE', 'Senior Backend Engineer', 'Stripe, Berlin\tJan 2021 – Present', '• Led the move to event sourcing, cutting incidents by 40%', '• Mentored 5 engineers',
  'Backend Engineer at N26', '2017 - 2020', '- Built the card ledger in Go', '- Reduced latency 30%', '',
  'Education:', 'B.Sc. Computer Science', 'TU Munich, 2013 – 2017', '', 'SKILLS', 'Languages: Go, Python, SQL', 'Tools: Kafka, PostgreSQL, AWS, Go'].join('\r\n');
const R1 = T.parseResume(CV1);
eq('import: name from capitals, headline, place', [R1.name, R1.title, R1.place], ['Jane Doe', 'Senior Backend Engineer', 'Berlin, Germany']);
eq('import: contacts', [R1.email, R1.phone, R1.links], ['jane.doe@mail.com', '+49 151 2345 6789', 'linkedin.com/in/janedoe']);
eq('import: summary', R1.summary, 'Backend engineer with 8 years in payments. Built systems that handle 2M transactions a day.');
eq('import: two jobs, title and company on separate lines or with "at"', R1.exp.map(function (x) { return [x.role, x.org, x.dates]; }),
  [['Senior Backend Engineer', 'Stripe, Berlin', 'Jan 2021 – Present'], ['Backend Engineer', 'N26', '2017 – 2020']]);
eq('import: bullet points become lines, without the bullet', R1.exp[0].text, 'Led the move to event sourcing, cutting incidents by 40%\nMentored 5 engineers');
eq('import: education, degree first', R1.edu, [{ what: 'B.Sc. Computer Science', org: 'TU Munich', dates: '2013 – 2017' }]);
eq('import: skills without their labels and without repeats', R1.skills, 'Go, Python, SQL, Kafka, PostgreSQL, AWS');
const R2 = T.parseResume('Max Mustermann\nmax@example.org\n\nWork Experience\nAcme GmbH — Data Analyst (03/2019 – 06/2023)\nBuilt the weekly sales report used by 40 managers.\nAutomated invoice checks in Python.\n\nEducation\nUniversity of Vienna\nMaster of Science, Statistics, 2018\n');
eq('import: "Company — Role (dates)" turned round, and sentences without bullets', R2.exp.map(function (x) { return [x.role, x.org, x.dates, x.text.split('\n').length]; }), [['Data Analyst', 'Acme GmbH', '03/2019 – 06/2023', 2]]);
eq('import: school line, then the degree with a year', R2.edu, [{ what: 'Master of Science, Statistics', org: 'University of Vienna', dates: '2018' }]);
eq('import: no headline invented from an email line', [R2.name, R2.title], ['Max Mustermann', '']);
eq('import: nothing to read', T.parseResume('').exp, []);
const own = { basics: { name: 'Alex Morgan', label: 'Data Analyst', email: 'a@b.co', phone: '', summary: 'S', location: { address: 'Lisbon, Portugal' }, profiles: [{ network: 'github.com', url: 'https://github.com/alexm' }] },
  work: [{ name: 'Acme', position: 'Analyst', summary: '2021 – now', highlights: ['Cut costs 10%'] }], education: [{ institution: 'Uni', area: 'Economics', studyType: '', endDate: '2020' }], skills: [{ name: 'SQL' }, { name: 'Excel', keywords: ['Power Query'] }] };
const J = T.fromJsonResume(own);
eq('import JSON Resume: our own download comes back the same', [J.name, J.title, J.place, J.links, J.exp, J.edu, J.skills],
  ['Alex Morgan', 'Data Analyst', 'Lisbon, Portugal', 'github.com/alexm', [{ role: 'Analyst', org: 'Acme', dates: '2021 – now', text: 'Cut costs 10%' }], [{ what: 'Economics', org: 'Uni', dates: '2020' }], 'SQL, Excel, Power Query']);
eq('import JSON Resume: standard dates', T.fromJsonResume({ basics: {}, work: [{ name: 'X', position: 'Y', startDate: '2019-01', endDate: '', summary: 'Ran the team.' }] }).exp[0], { role: 'Y', org: 'X', dates: '2019-01 – now', text: 'Ran the team.' });
eq('import JSON Resume: not a resume', [T.fromJsonResume({ a: 1 }), T.fromJsonResume(null)], [null, null]);


// ---- hints under each line of a job in the resume builder
const lh = function (l) { const r = T.lineHints(l); return r ? [r.ok, r.hints.map(function (h) { return h.level; })] : null; };
eq('line hints: a strong line passes', lh('Built a payments API used by 40 banks, cutting settlement time by 12%'), [true, []]);
eq('line hints: duty wording is a fix', lh('Responsible for the payments API and its 3 integrations with partner banks')[1][0], 'fix');
eq('line hints: a weak first word is a fix', T.lineHints('Helped the team ship 4 releases of the mobile app this year').hints[0].level, 'fix');
eq('line hints: no verb, no number, short', lh('Payments API'), [false, ['warn', 'warn', 'warn']]);
eq('line hints: present tense for the current job is fine', lh('Lead a team of 6 engineers who ship the mobile app every week'), [true, []]);
eq('line hints: "Manages" and "Plan" count as verbs', [lh('Manages a budget of $2M across three regions and two product lines')[0], lh('Plan the quarterly roadmap with 5 product managers and sales')[0]], [true, true]);
eq('line hints: "I" and "we" are only a note', lh('Led the launch where we grew sign-ups by 30% in two months')[1], ['info']);
eq('line hints: a year is not a result number', lh('Launched the new onboarding flow for customers in 2023 with the design team')[1], ['warn']);
eq('line hints: a number in words counts', lh('Doubled weekly active users of the reporting dashboard after the redesign')[0], true);
eq('line hints: bullets stripped, empty lines skipped', [T.lineHints('- Cut cloud costs by 18% by moving batch jobs to spot instances').text, T.lineHints('   '), T.lineHints(null)], ['Cut cloud costs by 18% by moving batch jobs to spot instances', null, null]);
eq('line hints: over two lines of the page', T.lineHints('Built ' + 'a very long description of the work and its many parts '.repeat(4) + 'for 10 teams').hints.some(function (h) { return /^Long/.test(h.t); }), true);

// ---- the summary request for an AI assistant, in four tones
const tones = T.TONES.map(function (t) { return T.summaryAsk('CV TEXT', t[0]); });
eq('summary ask: four different requests', new Set(tones).size, 4);
eq('summary ask: every tone forbids inventing and carries the resume', tones.every(function (t) { return /Do not add anything that is not in my resume/.test(t) && /MY RESUME:\nCV TEXT$/.test(t); }), true);
eq('summary ask: an unknown tone falls back to plain', T.summaryAsk('X', 'shouty'), T.summaryAsk('X', 'plain'));
eq('summary ask: the short tone names the length', /under 35 words/.test(T.summaryAsk('X', 'short')), true);
eq('summary ask: a target posting is included', /JOB POSTING:\nPOST TEXT\n\nMY RESUME:\nX$/.test(T.summaryAsk('X', 'warm', 'POST TEXT')), true);

// ---- projects, certificates and languages: JSON Resume out and back, and read from an old resume
const fullCv = { name: 'Alex Morgan', title: 'Data Analyst', email: 'a@b.co', phone: '', place: 'Lisbon', links: 'github.com/alexm', summary: 'S', skills: 'SQL, Excel',
  exp: [{ role: 'Analyst', org: 'Acme', dates: '2021 – now', text: '- Cut costs 10%\nBuilt the weekly report' }], edu: [{ what: 'Economics', org: 'Uni', dates: '2020' }],
  proj: [{ name: 'Rent tracker', link: 'github.com/alexm/rent', text: 'Charts rents in 12 cities\nUsed by 300 people' }, { name: '', link: '', text: '' }],
  cert: [{ name: 'Google Data Analytics', org: 'Coursera', date: '2022' }], lang: [{ name: 'English', level: 'Fluent' }, { name: 'Portuguese', level: 'Native' }] };
const jout = T.toJsonResume(fullCv);
eq('JSON Resume out: projects, certificates, languages in the schema names', [jout.projects, jout.certificates, jout.languages],
  [[{ name: 'Rent tracker', url: 'https://github.com/alexm/rent', highlights: ['Charts rents in 12 cities', 'Used by 300 people'] }], [{ name: 'Google Data Analytics', issuer: 'Coursera', date: '2022' }],
   [{ language: 'English', fluency: 'Fluent' }, { language: 'Portuguese', fluency: 'Native' }]]);
eq('JSON Resume out: bullet marks dropped from highlights', jout.work[0].highlights, ['Cut costs 10%', 'Built the weekly report']);
const back = T.fromJsonResume(JSON.parse(JSON.stringify(jout)));
eq('JSON Resume: out and back gives the same resume', [back.exp, back.edu, back.proj, back.cert, back.lang, back.skills],
  [[{ role: 'Analyst', org: 'Acme', dates: '2021 – now', text: 'Cut costs 10%\nBuilt the weekly report' }], fullCv.edu, [{ name: 'Rent tracker', link: 'github.com/alexm/rent', text: 'Charts rents in 12 cities\nUsed by 300 people' }], fullCv.cert, fullCv.lang, 'SQL, Excel']);
eq('JSON Resume out: an old resume without the new sections', [T.toJsonResume({ name: 'X', exp: 'broken' }).projects, T.toJsonResume({}).work], [[], []]);
const CV3 = ['Sam Lee', 'Frontend Developer', 'sam@lee.dev', '', 'Experience', 'Frontend Developer at Shopline', '2021 – present', '- Built the checkout in React, lifting conversion 8%', '',
  'Projects', 'Budget Buddy — github.com/samlee/budget-buddy', '- A budgeting app in React Native with 2,000 downloads', 'Open-source date picker', 'Used by 40 projects on npm.', '',
  'Certifications', 'AWS Certified Developer – Associate, Amazon Web Services, 2023', 'Google UX Design Certificate — Coursera (2021)', 'Scrum Master', '',
  'Languages', 'English (native), Spanish – B2, JavaScript', '', 'Skills', 'React, TypeScript, CSS'].join('\n');
const R3 = T.parseResume(CV3);
eq('import: projects with a link and their lines', R3.proj, [{ name: 'Budget Buddy', link: 'github.com/samlee/budget-buddy', text: 'A budgeting app in React Native with 2,000 downloads' },
  { name: 'Open-source date picker', link: '', text: 'Used by 40 projects on npm.' }]);
eq('import: certificates with issuer and year', R3.cert, [{ name: 'AWS Certified Developer – Associate', org: 'Amazon Web Services', date: '2023' },
  { name: 'Google UX Design Certificate', org: 'Coursera', date: '2021' }, { name: 'Scrum Master', org: '', date: '' }]);
eq('import: spoken languages with level; a programming language goes to the skills', [R3.lang, R3.skills], [[{ name: 'English', level: 'native' }, { name: 'Spanish', level: 'B2' }], 'React, TypeScript, CSS, JavaScript']);
eq('import: the job is still read', R3.exp.map(function (x) { return [x.role, x.org]; }), [['Frontend Developer', 'Shopline']]);
eq('import: no new sections in an old resume', [R1.proj, R1.cert, R1.lang], [[], [], []]);

console.log('\n' + pass + ' passed, ' + fail + ' failed');
process.exit(fail ? 1 : 0);
