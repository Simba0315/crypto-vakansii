"""Jobs from public Telegram job channels (the owner's decision, 15 Nov 2026: "without asking, like Hirify").

How it reads: the public web preview of each channel, https://t.me/s/<channel>, which Telegram serves to anyone without an
account (t.me has no robots.txt rule against it). No account, no API, no bot. Each run reads the newest page of every channel
(about 20 posts) and older pages only until it reaches posts it has already seen; a channel read for the first time goes back
TG_DAYS days. Four channels at a time, a pause between pages, and a channel that answers with an error simply waits for the next
run.

What it keeps: the facts of each job post (title, company, place, remote or not, pay, skills), a short excerpt and the link to the
post. The full post is not copied: the job page names the channel and its "Apply" button opens the post, where the contact is.
Skipped: posts without a named company ("NDA", "a stable fintech project"), adverts, courses, résumés, digests of articles, and
jobs of a company whose own hiring system we already read (the employer's own feed is the better source). A channel whose owner
asks is switched off with "off": true in channels_tg.json, and its jobs close at the next run.

A Telegram post never says that the job is filled, so a job stays open TG_DAYS days after its post.

English only (the owner, 15 Nov 2026: "the site is international, the jobs must be in English"): a post written in Russian is
skipped. Measured that day: of 127 jobs posted in 3 days in 29 IT job channels, 1 was in English, and the English channels
mostly repeat large companies we already read from their own boards. So the Russian-language channels in channels_tg.json are
"off", kept for a Russian section should there ever be one. 26 Nov 2026: about 40 English job channels were checked; the only
active one whose posts name companies we do not read yet is cryptojobslist (62K subscribers; 4 jobs a month from Paradex,
Toobit, KCEX and the like), so it is on. remotejobss (163K) posts a template ("Replace with job title") and gives nothing.

    python3 telegram_jobs.py --test            parser checks on saved posts (tests/telegram/)
    python3 telegram_jobs.py <channel>         read one channel and print what would be taken
"""
import concurrent.futures as cf
import datetime, html, json, os, re, ssl, sys, time, urllib.request
from pathlib import Path

ROOT = Path(__file__).parent
TG_DAYS = int(os.environ.get("HRN_TG_DAYS") or 30)     # how long a post stays an open job (a smaller number for a quick local try)
UA = {"User-Agent": "Mozilla/5.0 (compatible; JobsEveryHour/1.0; +https://jobseveryhour.com/about/)"}

# ---------------------------------------------------------------------------------------------------------------- reading

def _ctx():
    for f in ("/etc/ssl/cert.pem", "/etc/ssl/certs/ca-certificates.crt"):     # the system's roots (python.org builds on macOS have none)
        if Path(f).exists(): return ssl.create_default_context(cafile=f)
    return ssl.create_default_context()


CTX = _ctx()


def get(url, timeout=25):
    with urllib.request.urlopen(urllib.request.Request(url, headers=UA), timeout=timeout, context=CTX) as r:
        return r.read().decode("utf-8", "replace")


def text_of(fragment):
    """The plain text of a message's HTML: line breaks kept, tags and entities gone."""
    t = re.sub(r"<br\s*/?>", "\n", fragment)
    t = re.sub(r"</(p|div|blockquote|li)>", "\n", t)
    t = re.sub(r"<[^>]+>", "", t)
    t = html.unescape(t).replace("\xa0", " ")
    return re.sub(r"[ \t]+\n", "\n", re.sub(r"\n{3,}", "\n\n", t)).strip()


def posts_of(page):
    """[{id, channel, date, text, links}] from one t.me/s/ page, oldest first; posts without text (photos only) are left out."""
    out = []
    for block in page.split('class="tgme_widget_message_wrap')[1:]:
        m = re.search(r'data-post="([^"/]+)/(\d+)"', block)
        if not m: continue
        body = block.split('class="tgme_widget_message_text js-message_text', 1)
        if len(body) < 2: continue
        frag = body[1].split(">", 1)[1]
        # the text ends at the div that closes it; a reply quote or a link preview comes after it
        depth, i, n = 1, 0, len(frag)
        for t in re.finditer(r"<(/?)div\b", frag):
            depth += -1 if t.group(1) else 1
            if depth == 0:
                frag = frag[:t.start()]; break
        d = re.search(r'<time datetime="([^"]+)"', block)
        out.append({"channel": m.group(1), "id": int(m.group(2)), "date": d.group(1) if d else "",
                    "text": text_of(frag), "links": re.findall(r'href="(https?://[^"]+)"', frag)})
    return out


def read_channel(ch, since_id=0, oldest=""):
    """Posts newer than since_id (or, for a channel read for the first time, newer than the date `oldest`), newest pages first."""
    got, before = [], None
    for _ in range(12 if not since_id else 6):
        page = get(f"https://t.me/s/{ch}" + (f"?before={before}" if before else ""))
        ps = posts_of(page)
        if not ps: break
        got += [p for p in ps if p["id"] > since_id and (since_id or p["date"][:10] >= oldest)]
        first = min(p["id"] for p in ps)
        if first <= since_id or (not since_id and min(p["date"][:10] for p in ps if p["date"]) < oldest) or first <= 1: break
        before = first
        time.sleep(1.0)
    return sorted({p["id"]: p for p in got}.values(), key=lambda p: p["id"])

# ---------------------------------------------------------------------------------------------------------------- parsing

SKIP_POST = re.compile(r"\berid\b|#реклама|#ad\b|на правах рекламы|#резюме|#ищуработу|#cv\b|\bищу (?:удал[её]нную |новую )?работу\b|"
                       r"в поиске новых проектов|\bрезюме:\s*https?|#looking_for_job|#opentowork|open to work", re.I)
COURSE = re.compile(r"\bкурс(?:ы|а|е)?\b|буткемп|вебинар|интенсив|обучени[ея] (?:с нуля|профессии)|онлайн-школ|marathon|bootcamp|webinar", re.I)
JOB_MARK = re.compile(r"ваканси|vacanc|\bhiring\b|ищем\b|требовани|обязанност|зарплат|\bзп\b|з/п|вилк[аи]|salary|requirements|responsibilit|we.re looking|откликнуться|отклик", re.I)
JOB_WORD = re.compile(r"developer|engineer|programmer|architect|analyst|scientist|designer|manager|lead\b|head of|director|officer|"
                      r"tester|\bqa\b|devops|\bsre\b|administrator|admin\b|specialist|consultant|recruiter|\bhr\b|marketer|writer|editor|"
                      r"producer|artist|animator|owner|intern|support|sales|account|operator|researcher|cto|cpo|cmo|ceo|coordinator|"
                      r"разработчик|программист|инженер|архитектор|аналитик|дизайнер|менеджер|руководител|директор|тестировщик|"
                      r"администратор|специалист|консультант|рекрутер|маркетолог|копирайтер|редактор|продюсер|художник|аниматор|"
                      r"стаж[её]р|стажировк|тимлид|лид\b|техлид|продакт|проджект|оунер|эксперт|автор|методолог|бухгалтер|юрист|"
                      r"\b(?:junior|middle|senior|lead|head|principal|staff)\b", re.I)
LABEL = r"\s*[:：—–-]\s*"
FIELD = {
    "title": re.compile(r"^(?:вакансия|позиция|должность|position|role|job title|vacancy)" + LABEL + r"(.+)$", re.I | re.M),
    "company": re.compile(r"^(?:компания|company|работодатель|employer|наниматель)" + LABEL + r"(.+)$", re.I | re.M),
    "location": re.compile(r"^(?:локация|город|location|место работы|место|офис|страна|country|city|регион|region)" + LABEL + r"(.+)$", re.I | re.M),
    "format": re.compile(r"^(?:формат(?: работы)?|format|work format|work type|тип работы|режим работы|занятость|employment|schedule)" + LABEL + r"(.+)$", re.I | re.M),
    "salary": re.compile(r"^(?:зп|з/п|зарплата|заработная плата|вилка|оклад|доход|компенсация|оплата|salary|compensation|pay|rate|ставка|budget|бюджет)" + LABEL + r"(.+)$", re.I | re.M),
}
NOT_COMPANY = re.compile(r"^(?:nda|н/д|не указан|undisclosed|confidential|компания|крупн|стабильн|международн|российск|продуктов|финтех|"
                         r"it[- ]компани|ит[- ]компани|команд|проект|отдел|направлени|банк\b|холдинг|агентств|студи[юя] |контакт|telegram|телеграм|"
                         r"linkedin|hh\.ru|geekjob|habr|хабр|getmatch|удал[её]н|офис|гибрид|полн|частич|remote|office|hybrid|full[- ]time|part[- ]time|"
                         r"зарплат|опыт|требовани|обязанност|услови|мы\b|о нас|о компании|описание|подробнее|отклик|ищет|ищем|we\b|about|"
                         r"location|локаци|формат|format|salary|занятость|график|schedule|контакты|contacts)|"
                         r"стартап|startup\b(?! \w)|компани[яию]\b|проект\b", re.I)
EMOJI = re.compile("[\U0001F000-\U0001FAFF☀-➿⬀-⯿️‍•▪▶►➔➡]+")
URL = re.compile(r"https?://\S+")


def clean(s):
    s = EMOJI.sub(" ", s or "")
    s = URL.sub(" ", s)
    s = re.sub(r"#\w+|\$[A-Za-z]\w*", " ", s)
    s = re.sub(r"\*\*|__|`", "", s)
    return re.sub(r"\s+", " ", s).strip(" .,;:—–-•|/>»«\"'")


def role_ok(title):
    """A job title: a role word and at least two words ("$Lead" or "Senior" alone is not a title)."""
    return bool(JOB_WORD.search(title)) and len(re.findall(r"[A-Za-zА-Яа-яЁё]{2,}", title)) >= 2 and len(title) <= 120 \
        and not re.match(r"(?:вилка|вилки|зарплат|зп\b|з/п|salary|salaries)", title, re.I) \
        and not re.match(r"[А-ЯЁ][а-яё]+ [А-ЯЁ][а-яё]+,", title) \
        and not re.search(r"\b(?:is|are|we|our|you|мы|это|ищет|ищем|ищут|упал[иа]?|выросл[иа]?|hiring|looking for)\b", title, re.I)


def company_of(c):
    c = re.split(r"\s+[|(—–/-]\s+|\s+\(|:\s|,\s|\s+—|\s+–|\.\s", c.strip())[0]
    c = re.split(r"\s+(?:в|во|at)\s+", c)[-1]                   # "Ryze AI в Ryze AI"
    return c.strip(" .,:;!>»«\"'")


def split_title_company(line, nxt="", top=False):
    """(title, company) from one line of a post, or None:
    "Middle+ Python Developer в Avito" / "Data Engineer at Revolut" / "Бизнес-аналитик / Норникель (удалёнка)",
    or a title line followed by "в Banco Plata — a fintech platform …"."""
    line = clean(line)
    if not line or len(line) > 140: return None
    title = comp = ""
    if m := re.match(r"^(.{3,110}?)\s+(?:в|во|at|@)\s+(.{2,80})$", line):
        title, comp = m.group(1), m.group(2)
    elif (m := re.match(r"^(.{3,110})\s+/\s+([^/]{2,60})$", line)) and not JOB_WORD.search(re.sub(r"\(.*?\)", "", m.group(2))):
        title, comp = m.group(1), m.group(2)
    elif nxt and (m := re.match(r"^(?:в|во|at)\s+(?:компани[юи]\s+)?(.{2,})$", clean(nxt))):
        title, comp = line, m.group(1)
    elif top and nxt and (m := re.match(r"^([A-ZА-ЯЁ0-9][^—–]{1,50}?)\s*(?:[—–]\s+.*)?$", clean(nxt))) and not JOB_WORD.search(m.group(1)):
        title, comp = line, m.group(1)          # "Миддл .NET Разработчик" / "Bakai Bank — a commercial bank"; "Global Partnerships BD Lead" / "Fuku"
    if not title and (m := re.match(r"^(.{2,50}?)\s+(?:is|are)\s+hiring(?:\s+for)?\s+(?:an?\s+)?(.{3,110})$", line, re.I)):
        comp, title = m.group(1), m.group(2)
    if not title: return None
    title = re.sub(r"\s+(?:в|во|into|to join)\s+(?:команд[уые]|отдел|проект|направлени[ея]|группу|team)\b.*$", "", title, flags=re.I)
    title = re.sub(r"\s+\|\s+.*$", "", title).strip(" ,.-–—")
    comp = company_of(comp)
    if title.count("(") != title.count(")") or not role_ok(title) or not good_company(comp): return None
    return title, comp


def good_company(c):
    """A company name: capitalised, short, not a generic phrase ("NDA", "a fintech startup") and not a place ("в Москве")."""
    return bool(c) and 2 <= len(c) <= 50 and not NOT_COMPANY.search(c) and (c[0].isupper() or c[0].isdigit()) \
        and len(c.split()) <= 5 and c.count("(") == c.count(")") and re.search(r"[A-ZА-ЯЁ]", c) and not re.fullmatch(r"Q[1-4]\W*.*|H[12]\b.*|\d{4}.*", c) and re.fullmatch(r"[\w .&'’+!()-]+", c) and not re.search(r"[.!?]$|https?://|@|\d[\d\s]*(?:₽|руб|\$|€|к\b|k\b)", c) and not re.fullmatch(r"[\d\s.,]+", c) \
        and not any(re.match(rx, c, re.I) for rx, _ in RU_PLACES)


RU_PLACES = [   # Russian place names -> the English line the site understands (city, country)
    (r"москв|мск\b", "Moscow, Russia"), (r"санкт-петербург|петербург|\bспб\b|\bпитер", "Saint Petersburg, Russia"),
    (r"новосибирск", "Novosibirsk, Russia"), (r"екатеринбург|екб\b", "Yekaterinburg, Russia"), (r"\bказан[ьи]\b", "Kazan, Russia"),
    (r"нижн(?:ий|ем) новгород", "Nizhny Novgorod, Russia"), (r"краснодар", "Krasnodar, Russia"), (r"самар", "Samara, Russia"),
    (r"ростов", "Rostov-on-Don, Russia"), (r"пермь|перми", "Perm, Russia"), (r"томск", "Tomsk, Russia"), (r"иннополис", "Innopolis, Russia"),
    (r"воронеж", "Voronezh, Russia"), (r"уф[аеы]\b", "Ufa, Russia"), (r"челябинск", "Chelyabinsk, Russia"), (r"калининград", "Kaliningrad, Russia"),
    (r"росси[яию]\b|\bрф\b", "Russia"),
    (r"минск", "Minsk, Belarus"), (r"беларус|белорус", "Belarus"),
    (r"алмат", "Almaty, Kazakhstan"), (r"астан", "Astana, Kazakhstan"), (r"казахстан", "Kazakhstan"),
    (r"ташкент", "Tashkent, Uzbekistan"), (r"узбекистан", "Uzbekistan"), (r"бишкек", "Bishkek, Kyrgyzstan"), (r"кыргызстан|киргиз", "Kyrgyzstan"),
    (r"ереван", "Yerevan, Armenia"), (r"армени", "Armenia"), (r"тбилиси", "Tbilisi, Georgia (country)"), (r"батуми", "Batumi, Georgia (country)"), (r"грузи[яию]\b", "Georgia (country)"),
    (r"баку", "Baku, Azerbaijan"), (r"азербайджан", "Azerbaijan"),
    (r"белград", "Belgrade, Serbia"), (r"нови сад", "Novi Sad, Serbia"), (r"серби", "Serbia"), (r"черногори|подгориц|будва", "Montenegro"),
    (r"лимассол", "Limassol, Cyprus"), (r"ларнак", "Larnaca, Cyprus"), (r"никоси", "Nicosia, Cyprus"), (r"кипр", "Cyprus"),
    (r"стамбул", "Istanbul, Turkey"), (r"анталь", "Antalya, Turkey"), (r"турци", "Turkey"),
    (r"дуба[йи]", "Dubai, United Arab Emirates"), (r"оаэ|эмират", "United Arab Emirates"),
    (r"бангкок", "Bangkok, Thailand"), (r"пхукет", "Phuket, Thailand"), (r"таиланд|тайланд", "Thailand"), (r"бали\b|индонези", "Indonesia"),
    (r"варшав", "Warsaw, Poland"), (r"польш", "Poland"), (r"берлин", "Berlin, Germany"), (r"германи", "Germany"),
    (r"амстердам", "Amsterdam, Netherlands"), (r"нидерланд", "Netherlands"), (r"лиссабон", "Lisbon, Portugal"), (r"португали", "Portugal"),
    (r"испани|барселон|мадрид", "Spain"), (r"\bриг[аеу]\b|латви", "Latvia"), (r"вильнюс|литв", "Lithuania"), (r"таллин|эстони", "Estonia"),
    (r"лондон", "London, United Kingdom"), (r"великобритани|англи[яию]\b", "United Kingdom"), (r"кишин[её]в|молдов", "Moldova"),
]
REMOTE = re.compile(r"удал[её]н|удал[её]нк|дистанц|remote|из любой точки|anywhere|#remote|#удаленка|#удалёнка", re.I)
HYBRID = re.compile(r"гибрид|hybrid", re.I)
OFFICE = re.compile(r"\bофис|office|on-?site", re.I)
WORLD = re.compile(r"\(мир\)|по всему миру|из любой (?:точки|страны)|worldwide|anywhere", re.I)


def place_of(text):
    """(location line in English, remote, hybrid) from the place and format lines of a post, or from the whole post."""
    lines = [m.group(1) for k in ("location", "format") for m in FIELD[k].finditer(text)]
    tags = " ".join(re.findall(r"#(\w+)", text))
    pool = " ".join(lines) + " " + tags
    hits = [en for rx, en in RU_PLACES if re.search(rx, pool, re.I)] or [en for rx, en in RU_PLACES if re.search(rx, text[:600], re.I)]
    seen, places = set(), []
    for h in hits:                                    # "Moscow, Russia" makes a bare "Russia" redundant
        c = h.split(", ")[-1]
        if h == c and any(p.endswith(", " + c) for p in hits): continue
        if h not in seen: seen.add(h); places.append(h)
    scope = pool if lines or tags else text
    remote = bool(REMOTE.search(scope)) and not re.search(r"удал[её]нки нет|без удал[её]нки|no remote|не удал[её]н", scope, re.I)
    hybrid = bool(HYBRID.search(scope))
    loc = "; ".join(places[:3])
    if remote:
        loc = ("Remote, worldwide" if WORLD.search(scope) else "Remote") + (f" ({loc})" if loc else "")
    elif hybrid and loc:
        loc = f"Hybrid, {loc}"
    return loc, remote and not (hybrid and not REMOTE.search(" ".join(lines))), hybrid


CUR = [(r"₽|руб|rub\b|р\.(?!\w)|\bр\b", "RUB"), (r"\$|usd|долл", "USD"), (r"€|eur|евро", "EUR"), (r"₸|тенге|kzt", "KZT"),
       (r"usdt", "USDT"), (r"£|gbp", "GBP"), (r"byn|бел\.? ?руб", "BYN"), (r"сум\b|uzs", "UZS")]
SYM = {"RUB": "₽", "USD": "$", "EUR": "€", "GBP": "£", "KZT": "₸"}
NUM = re.compile(r"(\d{1,3}(?:[  .,]\d{3})+|\d+(?:[.,]\d+)?)\s*(к|k|тыс\.?|т\.р\.?|млн)?(?![\d%])", re.I)
SAL_HINT = re.compile(r"зп|з/п|зарплат|вилк|оклад|доход|компенсац|оплат|salary|compensation|ставк|\bот\s*\d|\bдо\s*\d|gross|net|на руки", re.I)


def pay_of(text):
    """The pay a post names, as one short line ("₽200,000 - ₽300,000 a month", "$3,000 - $4,000 a month", "$120K - $150K"), or ""."""
    lines = [m.group(1) for m in FIELD["salary"].finditer(text)]
    lines += [l for l in text.split("\n") if SAL_HINT.search(l) and NUM.search(l) and any(re.search(rx, l, re.I) for rx, _ in CUR)]
    for line in lines:
        cur = next((code for rx, code in CUR if re.search(rx, line, re.I)), "")
        if not cur: continue
        vals = []
        for n, mult in NUM.findall(line):
            v = float(re.sub(r"[  ]", "", n).replace(",", ".") if re.fullmatch(r"\d+[.,]\d{1,2}", n.replace(" ", "")) else re.sub(r"[  .,]", "", n))
            m = (mult or "").lower()
            v *= 1_000_000 if m == "млн" else 1000 if m in ("к", "k", "тыс", "тыс.", "т.р", "т.р.") else 1
            vals.append(v)
        hour = re.search(r"/\s?ч(?:ас)?\b|в час|per hour|/h\b|hourly", line, re.I)
        vals = [v for v in vals if v >= (5 if hour else 100)]
        if not vals: continue
        lo, hi = vals[0], vals[1] if len(vals) > 1 and vals[1] >= vals[0] else vals[0]
        frm = re.search(r"\bот\b|\bfrom\b", line, re.I) and len(vals) == 1
        upto = re.search(r"\bдо\b|\bup to\b", line, re.I) and len(vals) == 1
        sym = SYM.get(cur, cur + " ")
        year = re.search(r"в год|/\s?год|per year|annual|/y\b|yearly", line, re.I) or (cur in ("USD", "EUR", "GBP") and lo >= 20000 and not hour)
        if cur == "RUB" and not (20_000 <= lo <= 3_000_000): continue
        if cur in ("USD", "EUR", "GBP", "USDT") and not hour and not year and not (300 <= lo <= 30_000): continue
        if year and cur in SYM:
            rng = f"{sym}{lo / 1000:,.0f}K" + (f" - {sym}{hi / 1000:,.0f}K" if hi > lo else "")
        else:
            rng = f"{sym}{lo:,.0f}" + (f" - {sym}{hi:,.0f}" if hi > lo else "")
            rng += " an hour" if hour else "" if year else " a month"
        return ("from " if frm else "up to " if upto else "") + rng
    return ""


EN_HINT = [   # Russian job words -> English, only to put a Russian title in the right category and level
    (r"бэкенд|бекенд|back-?end", "backend engineer"), (r"фронтенд|фронт-?енд|front-?end", "frontend engineer"), (r"фулстек|full-?stack", "full-stack engineer"),
    (r"информационн\w* безопасност|\bиб\b|пентест|безопасност", "security engineer"),
    (r"разработчик|программист", "software engineer"), (r"инженер", "engineer"), (r"архитектор", "architect"), (r"девопс", "devops engineer"), (r"тестировщик|тестирован|\bqa\b", "qa engineer"),
    (r"аналитик данных", "data analyst"), (r"системн\w* аналитик", "systems analyst"), (r"бизнес-?аналитик", "business analyst"),
    (r"продуктов\w* аналитик", "product analyst"), (r"аналитик", "analyst"), (r"data scientist|дата-?сайентист", "data scientist"),
    (r"ml|машинн\w* обучени", "machine learning engineer"), (r"дизайнер", "designer"), (r"менеджер продукта|продакт|product owner", "product manager"),
    (r"менеджер проект|проджект|руководител\w* проект", "project manager"), (r"комьюнити|influence|инфлюенс", "community marketing"),
    (r"трафик|\bua\b|user acquisition|performance", "growth marketing"), (r"привлечени|кредитовани|по работе с клиентами|продаж", "sales account manager"),
    (r"налог", "tax finance"), (r"маркетолог|маркетинг|smm", "marketing manager"), (r"рекрутер|hr\b|эйчар", "recruiter"),
    (r"продаж", "sales manager"), (r"поддержк", "support specialist"), (r"администратор|сисадмин", "systems administrator"),
    (r"художник|аниматор|3d|видеомонтаж|креативн|арт-директор", "creative illustrator motion designer"), (r"копирайтер|редактор|контент", "content writer"),
    (r"юрист", "lawyer counsel"), (r"бухгалтер|финанс", "finance accountant"), (r"руководител|директор|head", "head of"),
    (r"стаж[её]р|стажировк", "intern"), (r"младш|джуниор|джун\b", "junior"), (r"миддл|мидл", "mid-level"), (r"старш|ведущ", "senior"), (r"тимлид|техлид|лид\b", "lead"),
]


def english_hint(title):
    return " ".join(en for rx, en in EN_HINT if re.search(rx, title, re.I)) + " " + title


def lines_of(text):
    """The post's lines with leading marks taken off ("✅Вакансия: …" -> "Вакансия: …"), hashtags and @names kept."""
    return [re.sub(r"^[^\w#@$(«\"]+", "", l).strip() for l in text.split("\n")]


def english(text):
    """True when a post (or one job's lines) is written in English: almost no Cyrillic letters."""
    lat, cyr = len(re.findall(r"[A-Za-z]", text)), len(re.findall(r"[А-Яа-яЁё]", text))
    return lat >= 10 and cyr <= 0.05 * (lat + cyr)


def jobs_in(post):
    """Every job one post offers: [{title, company, location, remote, hybrid, salary}] (empty for adverts, résumés and the like)."""
    t = post["text"]
    if not t or SKIP_POST.search(t): return []
    if COURSE.search(t) and not JOB_MARK.search(t): return []
    lines = lines_of(t)
    t = "\n".join(lines)
    found = []
    # 1. one job per line ("Title в Company", "Title / Company"), its place and pay on the next lines — channels that list several jobs
    heads = []
    for i, l in enumerate(lines):
        if not l or FIELD["title"].match(l) or FIELD["company"].match(l): continue
        h = split_title_company(l, lines[i + 1] if i + 1 < len(lines) else "", top=i <= 2)
        if h: heads.append((i, h))
    if len(heads) >= 2 or (len(heads) == 1 and not FIELD["company"].search(t)):
        for k, (i, (title, comp)) in enumerate(heads):
            end = min(heads[k + 1][0] if k + 1 < len(heads) else len(lines), i + 5)       # its own few lines, never the next job
            chunk = "\n".join(l for l in lines[i:end] if not re.fullmatch(r"(?i)подробнее|откликнуться|read more|apply|more", l))
            loc, remote, hybrid = place_of(chunk)
            found.append(dict(title=title, company=comp, location=loc, remote=remote, hybrid=hybrid, salary=pay_of(chunk), k=k, text=chunk))
        return found
    # 2. one job per post, with labels ("Вакансия:", "Компания:", "Локация:", "ЗП:") or a first line that names it
    if not JOB_MARK.search(t) and not FIELD["title"].search(t): return []
    title = comp = ""
    if m := FIELD["title"].search(t): title = clean(m.group(1))
    if m := FIELD["company"].search(t): comp = company_of(clean(m.group(1)))
    if not title:
        for l in lines[:6]:
            c = clean(l)
            if c and len(c) <= 90 and role_ok(c) and not re.search(r"[.!?]$", c):
                title = c; break
    if not comp:
        NAME = r"[«\"]?([A-ZА-ЯЁ0-9][\w.&+-]*(?:[ \t]+[A-ZА-ЯЁ0-9][\w.&+-]*){0,3})"
        for rx in (r"(?:в компани[юи]|join)[ \t]+" + NAME, r"(?m)^Мы,?[ \t]*[—–-]?[ \t]*" + NAME, r"(?m)^О компании[ \t]*[:—–-]?[ \t]*" + NAME,
                   r"(?m)^" + NAME + r"[ \t]+(?:ищет|ищут|is hiring|hiring)\b"):
            m = re.search(rx, t)
            if m and good_company(company_of(m.group(1))):
                comp = company_of(m.group(1)); break
    title = re.sub(r"^(?:вакансия|ищем|we are hiring|hiring|открыта вакансия)\s*[:：—–-]?\s*", "", title, flags=re.I)
    if not role_ok(title) or not good_company(comp): return []
    loc, remote, hybrid = place_of(t)
    return [dict(title=title[:110], company=comp, location=loc, remote=remote, hybrid=hybrid, salary=pay_of(t), k=0, text=t)]


# ---------------------------------------------------------------------------------------------------------------- collecting

TRANS = dict(zip("абвгдеёжзийклмнопрстуфхцчшщъыьэюя", "a b v g d e e zh z i y k l m n o p r s t u f kh ts ch sh shch - y - e yu ya".split()))


TRANS["ъ"] = TRANS["ь"] = ""


def translit(s):
    return "".join(TRANS.get(ch, ch) for ch in s.lower())


def channels():
    f = ROOT / "channels_tg.json"
    return [c for c in (json.loads(f.read_text()) if f.exists() else []) if isinstance(c, dict) and c.get("channel")]


def collect(db, used_slugs, indexed, stats, norm, slugify, excerpt, classify, level, etype, today, now):
    """Adds and updates Telegram jobs in db (collect.py passes its own helpers so a record looks like every other one)."""
    chans = channels()
    on = {c["channel"].lower(): c for c in chans if not c.get("off")}
    oldest = (datetime.date.fromisoformat(today) - datetime.timedelta(days=TG_DAYS)).isoformat()
    last = {}
    for j in db.values():
        if j.get("tg"): last[j["tg"].lower()] = max(last.get(j["tg"].lower(), 0), int(j.get("tg_post") or 0))

    def read(c):
        try:
            return c["channel"], read_channel(c["channel"], last.get(c["channel"].lower(), 0), oldest)
        except Exception as ex:
            print(f"telegram: {c['channel']}: {type(ex).__name__}: {ex}")
            return c["channel"], None

    with cf.ThreadPoolExecutor(4) as ex:
        results = list(ex.map(read, on.values()))
    open_keys = {(j["company"].lower(), j["title"].lower()) for j in db.values() if j.get("active")}
    added = failed = 0
    for ch, posts in results:
        if posts is None:
            failed += 1; continue
        for p in posts:
            for job in jobs_in(p):
                if not english(job["title"] + "\n" + job["text"]): continue        # the site is in English: Russian-language posts wait for a Russian section
                if on.get(ch.lower(), {}).get("remote") and not job["location"]:
                    job.update(location="Remote", remote=True)          # a channel of remote jobs only
                key = (job["company"].lower(), job["title"].lower())
                if job["company"].lower() in indexed or key in open_keys: continue
                open_keys.add(key)
                hint = english_hint(job["title"])
                j = norm(job["company"], "tg", f"{slugify(ch)}-{p['id']}-{job['k']}", job["title"], f"https://t.me/{p['channel']}/{p['id']}",
                         job["location"], job["remote"], "", p["date"][:10], job["text"], "", "", "", job["hybrid"], p["date"])
                j.pop("_crypto", None)
                j.update(cat=classify(hint), level=level(hint), etype=etype(hint), salary=job["salary"], desc="", excerpt=excerpt(job["text"], 300),
                         crypto=False, tg=p["channel"], tg_post=p["id"], last_seen=today, active=True)
                if j["id"] in db: continue
                base = f"{slugify(translit(job['title']))}-{slugify(translit(job['company']))}"
                slug, i = base, 2
                while slug in used_slugs:
                    slug, i = f"{base}-{i}", i + 1
                used_slugs.add(slug)
                j.update(slug=slug, first_seen=today, first_seen_at=now)
                db[j["id"]] = j
                stats["new"] += 1; added += 1
    closed = 0
    for j in db.values():
        if j.get("tg") and j["active"] and ((j.get("posted") or today) < oldest or j["tg"].lower() not in on):
            j.update(active=False, closed=today); closed += 1; stats["closed"] += 1
    # last_seen stays the day the post was read (26 Nov 2026): a post is never read again, so "Last checked" on its page and "re-checked
    # today" on /status/ must not move every hour as if it were (they did, even in a run where the channel did not answer).
    live = sum(1 for j in db.values() if j.get("tg") and j["active"])
    print(f"telegram: {len(on)} channels, {failed} did not answer, {added} new jobs, {closed} closed, {live} open")

# ---------------------------------------------------------------------------------------------------------------- checks

def _test():
    import collect as C
    cases = json.loads((ROOT / "tests" / "telegram" / "cases.json").read_text())
    bad = 0
    for c in cases:
        got = [{k: v for k, v in j.items() if k not in ("k", "text")} for j in jobs_in({"text": c["text"]})]
        want = c["want"]
        for w in want:
            if not any(all(g.get(k) == v for k, v in w.items()) for g in got):
                bad += 1; print("MISSING", c["name"], w, "got", got)
        if not want and got:
            bad += 1; print("UNWANTED", c["name"], got)
    for s, want in [("от 3 000 до 4 000$", "$3,000 - $4,000 a month"), ("ЗП: 200 000 – 300 000 ₽", "₽200,000 - ₽300,000 a month"),
                    ("Зарплата: до 250к руб", "up to ₽250,000 a month"), ("Salary: $120k-150k", "$120K - $150K"), ("ЗП: от 150 000 руб. на руки", "from ₽150,000 a month"),
                    ("Вилка: 2500-3500 USD net", "$2,500 - $3,500 a month"), ("Ставка: 25 $/час", "$25 an hour"), ("Вилка: обсуждается", "")]:
        if pay_of(s) != want: bad += 1; print("PAY", repr(s), "->", repr(pay_of(s)), "want", repr(want))
    print(f"{len(cases)} posts and 8 pay lines checked, {bad} wrong")
    return bad


if __name__ == "__main__":
    if sys.argv[1:] == ["--test"]:
        sys.exit(1 if _test() else 0)
    for ch in sys.argv[1:]:
        for p in read_channel(ch, 0, (datetime.date.today() - datetime.timedelta(days=3)).isoformat()):
            for j in jobs_in(p):
                print(f"{p['id']:>6} {j['title'][:60]:<60} | {j['company'][:25]:<25} | {j['location'][:40]:<40} | {j['salary']}")
