"""Generate the static site into ./site from data/jobs.json (+ optional data/paid.json).

Closed jobs keep their pages forever (archive); only the JobPosting markup and the apply button are removed.
"""
import datetime, html, json, re, shutil
from collections import Counter, defaultdict
from pathlib import Path
from collect import CATS, OTHER, slugify

ROOT = Path(__file__).parent
OUT = ROOT / "site"
CFG = json.loads((ROOT / "config.json").read_text())
SITE, BASE, P = CFG["site_name"], CFG["base_url"].rstrip("/"), CFG.get("base_path", "").rstrip("/")
TODAY = datetime.date.today().isoformat()
e = html.escape
CAT = {s: n for s, n, _ in CATS} | {OTHER[0]: OTHER[1]}
MONTHS = "января февраля марта апреля мая июня июля августа сентября октября ноября декабря".split()
TAG_SLUG = {"Смарт-контракты": "smart-contracts", "Трейдинг": "trading", "ИИ": "ai", "C++": "cpp", "Node.js": "nodejs", "AML/KYC": "aml-kyc"}
CIS_RE = re.compile(r"kazakhstan|russia|armenia|ukraine|belarus|uzbekistan|kyrgyz|azerbaijan|moldova|\bcis\b|tbilisi|almaty|astana|yerevan|kyiv|minsk|tashkent|bishkek|baku|moscow|снг", re.I)
URLS = []


def rudate(iso):
    try:
        y, m, d = (int(x) for x in iso[:10].split("-"))
        return f"{d} {MONTHS[m - 1]} {y}"
    except Exception:
        return ""


def plural(n, one="вакансия", few="вакансии", many="вакансий"):
    a, b = n % 10, n % 100
    return one if a == 1 and b != 11 else few if 2 <= a <= 4 and not 12 <= b <= 14 else many


def write(path, content, sitemap=True):
    f = OUT / path / "index.html" if not path.endswith((".html", ".xml", ".txt", ".json")) else OUT / path
    f.parent.mkdir(parents=True, exist_ok=True)
    f.write_text(content, encoding="utf-8")
    if sitemap:
        URLS.append(path)


def page(path, title, desc, body, head="", sitemap=True):
    url = f"{BASE}{P}/{path}"
    write(path, f"""<!doctype html>
<html lang="ru"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>{e(title)}</title><meta name="description" content="{e(desc)}">
<link rel="canonical" href="{e(url)}">
<meta property="og:title" content="{e(title)}"><meta property="og:description" content="{e(desc)}">
<meta property="og:type" content="website"><meta property="og:url" content="{e(url)}"><meta property="og:site_name" content="{e(SITE)}">
<link rel="stylesheet" href="{P}/style.css">{head}</head><body>
<header class="site"><div class="wrap"><a class="logo" href="{P}/">{e(SITE)}</a><nav>
<a href="{P}/vakansii/">Все вакансии</a><a href="{P}/udalenno/">Удалённо</a><a href="{P}/kompanii/">Компании</a>
<a class="btn" href="{P}/razmestit/">Разместить вакансию</a></nav></div></header>
<main class="wrap">{body}</main>
<footer><div class="wrap"><p><a href="{P}/o-proekte/">О проекте</a><a href="{P}/arhiv/">Архив вакансий</a><a href="{P}/razmestit/">Работодателям</a></p>
<p>© {TODAY[:4]} {e(SITE)}. Вакансии собираются с официальных страниц компаний, отклик идёт на сайте работодателя.</p></div></footer>
</body></html>""", sitemap)


def card(j):
    b = []
    if j["featured"]: b.append('<span class="tag acc">Выделено</span>')
    if not j["active"]: b.append('<span class="tag">В архиве</span>')
    if j["remote"]: b.append('<span class="tag ok">Удалённо</span>')
    if j["salary"]: b.append(f'<span class="tag warn">{e(j["salary"])}</span>')
    if j["level"]: b.append(f'<span class="tag">{e(j["level"])}</span>')
    b += [f'<span class="tag">{e(t)}</span>' for t in j["tags"]]
    loc = f' · {e(j["location"])}' if j["location"] else ""
    return (f'<li class="job{" feat" if j["featured"] else ""}"><a class="t" href="{P}/vakansiya/{j["slug"]}/">{e(j["title"])}</a>'
            f'<div class="m"><a href="{P}/kompanii/{slugify(j["company"])}/">{e(j["company"])}</a>{loc}</div>'
            f'<div class="b">{"".join(b)}<time datetime="{j["posted"]}">{rudate(j["posted"])}</time></div></li>')


def order(jobs):
    return sorted(jobs, key=lambda j: (not j["featured"], -int((j["posted"] or j["first_seen"]).replace("-", "") or 0)))


def crumbs(*parts):
    items = [f'<a href="{P}/">Главная</a>'] + [f'<a href="{P}/{u}">{e(n)}</a>' if u else e(n) for n, u in parts]
    return f'<div class="crumbs">{" › ".join(items)}</div>'


def listing(path, h1, title, desc, jobs, intro="", trail=(), per=100, extra=""):
    jobs = order(jobs)
    pages = max(1, -(-len(jobs) // per))
    for n in range(1, pages + 1):
        chunk = jobs[(n - 1) * per:n * per]
        pager = ""
        if pages > 1:
            links = [f"<b>{i}</b>" if i == n else f'<a href="{P}/{path}{"" if i == 1 else f"{i}/"}">{i}</a>' for i in range(1, pages + 1)]
            pager = f'<div class="pager">{"".join(links)}</div>'
        body = (crumbs(*trail, (h1, "")) + f"<h1>{e(h1)}</h1>" + (f'<p class="lead">{intro}</p>' if intro and n == 1 else "")
                + (extra if n == 1 else "")
                + (f'<ul class="jobs">{"".join(card(j) for j in chunk)}</ul>' if chunk else '<p class="lead">Сейчас здесь пусто. Загляните позже: список обновляется каждый день.</p>')
                + pager)
        page(path if n == 1 else f"{path}{n}/", title if n == 1 else f"{title} — страница {n}", desc, body)


def top_companies(jobs, k=5):
    return ", ".join(c for c, _ in Counter(j["company"] for j in jobs).most_common(k))


def intro_for(jobs, what):
    if not jobs: return ""
    r = sum(j["remote"] for j in jobs)
    return (f"{len(jobs)} {plural(len(jobs), 'открытая вакансия', 'открытые вакансии', 'открытых вакансий')} {what}. "
            f"Больше всего позиций у компаний: {e(top_companies(jobs))}. " + (f"Удалённых — {r}. " if 0 < r < len(jobs) else "") + "Список обновляется каждый день.")


def job_page(j, active_by_cat):
    canonical = f"{BASE}{P}/vakansiya/{j['slug']}/"
    rows = [("Компания", f'<a href="{P}/kompanii/{slugify(j["company"])}/">{e(j["company"])}</a>')]
    if j["location"]: rows.append(("Локация", e(j["location"])))
    if j["remote"]: rows.append(("Формат", "Удалённо"))
    rows.append(("Направление", f'<a href="{P}/vakansii/{j["cat"]}/">{e(CAT[j["cat"]])}</a>'))
    if j["level"]: rows.append(("Уровень", e(j["level"])))
    if j["salary"]: rows.append(("Зарплата", e(j["salary"])))
    if j["posted"]: rows.append(("Опубликована", rudate(j["posted"])))
    if j["tags"]: rows.append(("Навыки", " ".join(f'<a class="tag" href="{P}/navyk/{TAG_SLUG.get(t, slugify(t))}/">{e(t)}</a>' for t in j["tags"])))
    meta = "".join(f"<dt>{k}</dt><dd>{v}</dd>" for k, v in rows)
    head = ""
    if j["active"]:
        ld = {"@context": "https://schema.org", "@type": "JobPosting", "title": j["title"], "description": j["excerpt"] or j["title"],
              "datePosted": j["posted"] or j["first_seen"], "hiringOrganization": {"@type": "Organization", "name": j["company"]},
              "directApply": False, "url": canonical}
        if j["location"]:
            ld["jobLocation"] = {"@type": "Place", "address": {"@type": "PostalAddress", "addressLocality": j["location"]}}
        if j["remote"]:
            ld["jobLocationType"] = "TELECOMMUTE"
        head = '<script type="application/ld+json">' + json.dumps(ld, ensure_ascii=False).replace("</", "<\\/") + "</script>"
        action = (f'<p class="cta"><a class="btn" href="{e(j["url"])}" target="_blank" rel="nofollow noopener">Откликнуться на сайте компании</a></p>'
                  '<p class="note">Отклик и полное описание — на официальной странице работодателя. Мы не берём денег с соискателей.</p>')
    else:
        action = f'<div class="banner">Вакансия в архиве{" с " + rudate(j["closed"]) if j.get("closed") else ""}. Компания закрыла набор, откликнуться уже нельзя. Ниже — похожие открытые вакансии.</div>'
    pool = [x for x in active_by_cat[j["cat"]] if x["id"] != j["id"]]
    similar = sorted(pool, key=lambda x: (x["company"] != j["company"], -int((x["posted"] or "0").replace("-", "") or 0)))[:6]
    sim = f'<h2>Похожие вакансии</h2><ul class="jobs">{"".join(card(x) for x in similar)}</ul>' if similar else ""
    desc_block = f'<h2>О вакансии</h2><p>{e(j["excerpt"])}</p><p class="note">Фрагмент описания на языке оригинала.</p>' if j["excerpt"] else ""
    body = (crumbs((CAT[j["cat"]], f"vakansii/{j['cat']}/"), (j["title"], "")) + f"<h1>{e(j['title'])}</h1>"
            + (action if not j["active"] else "") + f'<div class="card"><dl class="meta">{meta}</dl></div>' + desc_block
            + (action if j["active"] else "") + sim)
    where = j["location"] or ("удалённо" if j["remote"] else "")
    title = f"{j['title']} — вакансия в {j['company']}" + (" (архив)" if not j["active"] else "")
    desc = (f"Вакансия {j['title']} в {j['company']}" + (f", {where}" if where else "") + f". Направление: {CAT[j['cat']]}."
            + (" Удалённая работа." if j["remote"] else "") + (" Вакансия в архиве." if not j["active"] else " Отклик на сайте компании."))
    page(f"vakansiya/{j['slug']}/", title, desc, body, head)


def main():
    if OUT.exists(): shutil.rmtree(OUT)
    OUT.mkdir()
    db = json.loads((ROOT / "data" / "jobs.json").read_text())
    jobs = list(db.values())
    paid_file = ROOT / "data" / "paid.json"
    for p in (json.loads(paid_file.read_text()) if paid_file.exists() else []):
        base = f"{slugify(p['title'])}-{slugify(p['company'])}"
        jobs.append({"id": "paid-" + base, "slug": base, "location": "", "remote": False, "dept": "", "excerpt": "", "level": "", "tags": [],
                     "russian": False, "salary": "", "posted": TODAY, "first_seen": TODAY, "cat": OTHER[0],
                     "active": p.get("expires", "9999") >= TODAY, **p})
    for j in jobs:
        j["featured"] = bool(j.get("featured_until", "") >= TODAY and j["active"])
        j["sng"] = bool(j["russian"] or CIS_RE.search(j["title"] + " " + j["location"]))
    active = [j for j in jobs if j["active"]]
    archived = [j for j in jobs if not j["active"]]
    by_cat = defaultdict(list)
    for j in active: by_cat[j["cat"]].append(j)
    companies = defaultdict(list)
    for j in jobs: companies[j["company"]].append(j)
    n, m = len(active), len({j["company"] for j in active})

    # Home
    cats = "".join(f'<li><a href="{P}/vakansii/{s}/">{e(CAT[s])}<span>{len(by_cat[s])}</span></a></li>' for s in CAT if by_cat[s])
    quick = [("Удалённая работа", "udalenno/", sum(j["remote"] for j in active)), ("СНГ и русскоязычные", "sng/", sum(j["sng"] for j in active)),
             ("С указанной зарплатой", "s-zarplatoj/", sum(bool(j["salary"]) for j in active)),
             ("Junior и стажировки", "uroven/junior/", sum(j["level"] in ("Junior", "Стажёр") for j in active))]
    quick_html = "".join(f'<li><a href="{P}/{u}">{e(t)}<span>{c}</span></a></li>' for t, u, c in quick if c)
    strip = (f'<div class="card strip"><div><strong>Нанимаете в крипто-проект?</strong><br><span class="note">Размещение бесплатно, выделение — от 30 USDT. '
             f'Оплата в USDT, BTC, ETH.</span></div><a class="btn" href="{P}/razmestit/">Разместить вакансию</a></div>')
    home = (f"<h1>Работа в крипте и web3</h1><p class=\"lead\">{n} {plural(n, 'открытая вакансия', 'открытые вакансии', 'открытых вакансий')} "
            f"в {m} компаниях: биржи, кошельки, блокчейн-инфраструктура, DeFi. Обновляется каждый день.</p>"
            f'<form class="search" action="{P}/vakansii/" method="get"><input type="search" name="q" placeholder="Должность, навык или компания" aria-label="Поиск вакансий"><button class="btn">Найти</button></form>'
            f'<h2>Быстрые подборки</h2><ul class="grid">{quick_html}</ul><h2>Направления</h2><ul class="grid">{cats}</ul>{strip}'
            f'<h2>Новые вакансии</h2><ul class="jobs">{"".join(card(j) for j in order(active)[:40])}</ul>'
            f'<p><a href="{P}/vakansii/">Все {n} {plural(n)} →</a></p>')
    page("", f"Работа в крипте и web3 — {n} {plural(n)} в {m} компаниях | {SITE}",
         f"{n} {plural(n)} в крипто- и web3-компаниях: разработка, маркетинг, аналитика, поддержка. Удалённая работа, фильтры, ежедневное обновление.", home)

    # Search page
    opts = "".join(f'<option value="{s}">{e(CAT[s])}</option>' for s in CAT if by_cat[s])
    search = (crumbs(("Все вакансии", "")) + "<h1>Все вакансии в крипте и web3</h1>"
              f'<div id="search" data-base="{P}"><div class="search"><input type="search" id="q" placeholder="Должность, навык или компания" aria-label="Поиск вакансий">'
              f'<select id="cat" aria-label="Направление"><option value="">Все направления</option>{opts}</select></div>'
              '<div class="filters"><label><input type="checkbox" id="f-remote"> Удалённо</label><label><input type="checkbox" id="f-sng"> СНГ и русскоязычные</label>'
              '<label><input type="checkbox" id="f-sal"> С зарплатой</label></div>'
              '<p class="note" id="count">Загрузка…</p><ul class="jobs" id="results"></ul><p><button class="btn" id="more" hidden>Показать ещё</button></p></div>'
              f'<noscript><p>Для поиска нужен JavaScript. Направления:</p><ul class="grid">{cats}</ul></noscript><script src="{P}/app.js" defer></script>')
    page("vakansii/", f"Все вакансии в крипте и web3 — поиск по {n} вакансиям | {SITE}",
         "Поиск вакансий в крипто-компаниях по должности, навыку и компании. Фильтры: удалённо, СНГ, с зарплатой.", search)

    # Listings
    for s, name in CAT.items():
        js = by_cat[s]
        if not js: continue
        listing(f"vakansii/{s}/", f"{name}: вакансии в крипте и web3", f"{name} — вакансии в крипте и web3: {len(js)} {plural(len(js))} | {SITE}",
                f"{len(js)} {plural(len(js))} по направлению «{name}» в крипто- и web3-компаниях. Удалённая работа и офисы, ежедневное обновление.",
                js, intro_for(js, f"по направлению «{e(name)}» в крипто- и web3-компаниях"), trail=(("Все вакансии", "vakansii/"),))
        rj = [j for j in js if j["remote"]]
        if len(rj) >= 5:
            listing(f"udalenno/{s}/", f"{name}: удалённая работа в крипте", f"{name} — удалённые вакансии в крипте: {len(rj)} | {SITE}",
                    f"{len(rj)} {plural(len(rj), 'удалённая вакансия', 'удалённые вакансии', 'удалённых вакансий')} по направлению «{name}» в крипто-компаниях.",
                    rj, intro_for(rj, f"с удалённым форматом по направлению «{e(name)}»"), trail=(("Удалённо", "udalenno/"),))
    remote = [j for j in active if j["remote"]]
    rcats = "".join(f'<li><a href="{P}/udalenno/{s}/">{e(CAT[s])}<span>{c}</span></a></li>' for s in CAT
                    if (c := sum(j["remote"] for j in by_cat[s])) >= 5)
    listing("udalenno/", "Удалённая работа в крипте и web3", f"Удалённая работа в крипте и web3 — {len(remote)} {plural(len(remote))} | {SITE}",
            f"{len(remote)} удалённых вакансий в крипто-компаниях: разработка, маркетинг, поддержка, аналитика. Работа из любой страны.",
            remote, intro_for(remote, "с удалённым форматом в крипто- и web3-компаниях"), extra=f'<ul class="grid">{rcats}</ul><h2>Все удалённые вакансии</h2>')
    sng = [j for j in active if j["sng"]]
    listing("sng/", "Крипто-вакансии для СНГ и русскоязычных", f"Крипто-вакансии для СНГ и русскоязычных — {len(sng)} | {SITE}",
            "Вакансии крипто-компаний в странах СНГ и позиции, где нужен русский язык.", sng,
            intro_for(sng, "в странах СНГ или с требованием русского языка"))
    sal = [j for j in active if j["salary"]]
    listing("s-zarplatoj/", "Крипто-вакансии с указанной зарплатой", f"Крипто-вакансии с указанной зарплатой — {len(sal)} | {SITE}",
            "Вакансии в крипто- и web3-компаниях, где работодатель сразу указал зарплатную вилку.", sal, intro_for(sal, "с открытой зарплатной вилкой"))
    jr = [j for j in active if j["level"] in ("Junior", "Стажёр")]
    listing("uroven/junior/", "Работа в крипте без опыта: junior и стажировки", f"Работа в крипте без опыта: junior и стажировки — {len(jr)} | {SITE}",
            "Стажировки и junior-позиции в крипто-компаниях: вход в web3 без большого опыта.", jr, intro_for(jr, "для начинающих: стажировки и junior-позиции"))
    by_tag = defaultdict(list)
    for j in active:
        for t in j["tags"]: by_tag[t].append(j)
    for t, js in by_tag.items():
        listing(f"navyk/{TAG_SLUG.get(t, slugify(t))}/", f"Вакансии {t} в крипте и web3", f"Вакансии {t} в крипте и web3 — {len(js)} | {SITE}",
                f"{len(js)} {plural(len(js))} в крипто-компаниях, где требуется {t}.", js, intro_for(js, f"где в требованиях есть {e(t)}"))

    # Companies
    comp_items = sorted(companies.items(), key=lambda kv: -sum(j["active"] for j in kv[1]))
    grid = "".join(f'<li><a href="{P}/kompanii/{slugify(c)}/">{e(c)}<span>{sum(j["active"] for j in js)}</span></a></li>' for c, js in comp_items)
    page("kompanii/", f"Крипто-компании, которые нанимают — {len(companies)} работодателей | {SITE}",
         "Список крипто- и web3-компаний с открытыми вакансиями: биржи, кошельки, инфраструктура, DeFi.",
         crumbs(("Компании", "")) + f'<h1>Крипто-компании, которые нанимают</h1><p class="lead">{len(companies)} работодателей. Число — открытые вакансии сейчас.</p><ul class="grid">{grid}</ul>')
    for c, js in companies.items():
        act, arc = [j for j in js if j["active"]], [j for j in js if not j["active"]]
        extra = f'<h2>Архив вакансий {e(c)}</h2><ul class="jobs">{"".join(card(j) for j in order(arc)[:200])}</ul>' if arc else ""
        jobs_sorted = order(act)
        body = (crumbs(("Компании", "kompanii/"), (c, "")) + f"<h1>Вакансии {e(c)}</h1>"
                + f'<p class="lead">{intro_for(act, f"в {e(c)}") or "Сейчас открытых вакансий нет. Ниже — архив."}</p>'
                + (f'<ul class="jobs">{"".join(card(j) for j in jobs_sorted)}</ul>' if act else "") + extra)
        page(f"kompanii/{slugify(c)}/", f"Вакансии {c} — {len(act)} {plural(len(act), 'открытая', 'открытые', 'открытых')} | {SITE}",
             f"Все вакансии {c}: {len(act)} открытых" + (f" и {len(arc)} в архиве" if arc else "") + ". Направления, локации, удалённая работа.", body)

    # Job pages + archive
    for j in jobs: job_page(j, by_cat)
    listing("arhiv/", "Архив крипто-вакансий", f"Архив крипто-вакансий — {len(archived)} закрытых | {SITE}",
            "Закрытые вакансии крипто-компаний: кого и на каких условиях искали раньше.", archived,
            "Закрытые вакансии остаются в архиве: по ним видно, кого компании искали раньше.")

    # Employers
    rows = "".join(f"<tr><td><strong>{e(p['name'])}</strong></td><td>{e(p['price'])}</td><td>{e(p['what'])}</td></tr>" for p in CFG["prices"])
    wallets = [w for w in CFG["wallets"] if w["address"]]
    contact = " ".join(x for x in [f'Telegram: <a href="https://t.me/{e(CFG["contact_telegram"])}">@{e(CFG["contact_telegram"])}</a>' if CFG["contact_telegram"] else "",
                                   f'почта: <a href="mailto:{e(CFG["contact_email"])}">{e(CFG["contact_email"])}</a>' if CFG["contact_email"] else ""] if x)
    if wallets and contact:
        pay = ("<h2>Как разместить</h2><ol><li>Пришлите ссылку на вакансию или её текст: " + contact + ".</li>"
               "<li>Для платных тарифов переведите сумму на один из адресов ниже и пришлите хеш транзакции.</li>"
               "<li>Вакансия появится на сайте в течение суток после проверки платежа.</li></ol>"
               '<div class="tablewrap"><table><tr><th>Монета</th><th>Сеть</th><th>Адрес</th></tr>'
               + "".join(f"<tr><td>{e(w['coin'])}</td><td>{e(w['network'])}</td><td class=\"addr\">{e(w['address'])}</td></tr>" for w in wallets) + "</table></div>")
    else:
        pay = '<div class="banner">Приём заявок откроется в ближайшие дни. Загляните на эту страницу позже.</div>'
    page("razmestit/", f"Разместить вакансию в крипте — оплата в USDT, BTC, ETH | {SITE}",
         "Размещение вакансий для крипто- и web3-компаний. Обычное размещение бесплатно, выделение от 30 USDT. Оплата криптовалютой.",
         crumbs(("Работодателям", "")) + "<h1>Разместить вакансию</h1>"
         f'<p class="lead">На сайте {n} {plural(n)} от {m} крипто-компаний. Соискатели приходят сюда именно за работой в web3.</p>'
         f'<div class="tablewrap"><table><tr><th>Тариф</th><th>Цена</th><th>Что входит</th></tr>{rows}</table></div>{pay}'
         "<h2>Частые вопросы</h2><h3>Как вы принимаете оплату?</h3><p>Только криптовалютой: USDT, BTC или ETH. Карты и банковские переводы не принимаем.</p>"
         "<h3>Что будет с вакансией после закрытия?</h3><p>Она переедет в архив с пометкой «в архиве». Страница остаётся на сайте.</p>"
         "<h3>Можно ли вернуть деньги?</h3><p>Да, если вакансия ещё не опубликована. После публикации оплата не возвращается.</p>")
    page("o-proekte/", f"О проекте | {SITE}", "Откуда берутся вакансии, как часто обновляется список и как связаться.",
         crumbs(("О проекте", "")) + "<h1>О проекте</h1>"
         f"<p>{e(SITE)} собирает открытые вакансии с официальных страниц найма крипто- и web3-компаний и показывает их в одном списке с фильтрами.</p>"
         "<h2>Откуда вакансии</h2><p>Из открытых лент найма самих компаний. На каждой странице есть ссылка на оригинал, отклик идёт там.</p>"
         "<h2>Как часто обновляется</h2><p>Раз в день. Закрытые вакансии не удаляются, а переходят в архив.</p>"
         "<h2>Для соискателей</h2><p>Сайт бесплатный. Мы не просим денег за отклик и не собираем резюме.</p>"
         f'<h2>Для работодателей</h2><p>Вакансию можно добавить и выделить: <a href="{P}/razmestit/">условия размещения</a>.</p>')
    page("404.html", f"Страница не найдена | {SITE}", "Страница не найдена.",
         f'<h1>Страница не найдена</h1><p class="lead">Возможно, адрес изменился. Попробуйте <a href="{P}/vakansii/">поиск по вакансиям</a>.</p>', sitemap=False)

    # Data + static files
    idx = [[j["slug"], j["title"], j["company"], j["location"], int(j["remote"]), j["cat"], j["level"], j["tags"], j["salary"], rudate(j["posted"]),
            int(j["sng"]), int(j["featured"])] for j in order(active)]
    write("data/index.json", json.dumps(idx, ensure_ascii=False, separators=(",", ":")), sitemap=False)
    for f in ("style.css", "app.js"):
        shutil.copy(ROOT / "assets" / f, OUT / f)
    (OUT / ".nojekyll").write_text("")
    sm = "".join(f"<url><loc>{e(BASE + P + '/' + u)}</loc><lastmod>{TODAY}</lastmod></url>" for u in URLS)
    write("sitemap.xml", f'<?xml version="1.0" encoding="UTF-8"?><urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">{sm}</urlset>', sitemap=False)
    write("robots.txt", f"User-agent: *\nAllow: /\nSitemap: {BASE}{P}/sitemap.xml\n", sitemap=False)
    print(f"built {len(URLS)} pages: {n} active jobs, {len(archived)} archived, {len(companies)} companies")


if __name__ == "__main__":
    main()
