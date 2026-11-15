"""Jobs from Russia's federal job portal "Работа России" (trudvsem.ru), from its open data.

The portal publishes every vacancy as open data that anyone may reuse with a link to the source (trudvsem.ru/opendata).
Each job keeps the address of its card on trudvsem.ru, and the job page says where it came from (build.py, SOURCE_NAME).

What is taken (decided 15 Nov 2026, ROADMAP 112):
- only "Вакансия работодателя": a vacancy the employer itself posted. Vacancies the portal copied from other job sites
  ("Вакансия интернет ресурса", a third of the file) and agency vacancies are left out, as on the rest of the site;
- approved, visible, not deleted;
- office and professional work: whole fields (IT, accounting, banking, law, marketing, HR, administration, consulting, top management)
  and, in every other field, professional titles (engineer, programmer, accountant, manager, head of…), but not shop, warehouse,
  security-guard, cleaning or clinic work. The same rule as the other sources: mostly office and tech work.
- never a contact person, phone or e-mail: only the job, the employer, the place, the pay and the text. Sole traders (ИП) are left
  out, because their business name is a private person's full name;

The file (vacancy.csv, about 1.9 GB, "|"-separated) is read as a stream once a day by portals.py (.github/workflows/portals.yml);
the hourly run only applies the snapshot it leaves.
"""
import csv, io, json, os, re, subprocess, sys
from collections import Counter, defaultdict

CSV_URL = "https://opendata.trudvsem.ru/csv/vacancy.csv"
SOURCE = "Работа России"            # the board name in collect.py: its jobs close only when the daily file no longer has them

OFFICE = {"Информационные технологии, телекоммуникации, связь": "engineering", "Бухгалтерия, налоги, управленческий учет": "finance",
          "Банки, кредит, страхование, пенсионное обеспечение": "finance", "Юриспруденция": "compliance-legal", "Маркетинг, реклама, PR": "marketing",
          "Кадровая служба, управление персоналом": "people", "Административная работа, секретариат, АХО": "operations",
          "Консалтинг, стратегическое развитие, управление": "consulting", "Высший менеджмент": "operations"}
# the field of a professional title in another sphere, when the title alone does not say it
SPHERE_CAT = {"Образование, наука": "education", "Продажи, закупки, снабжение, торговля": "sales-bd", "Транспорт, автобизнес, логистика, склад, ВЭД": "supply-chain",
              "Здравоохранение и социальное обеспечение": "healthcare", "Туризм, гостиницы, рестораны": "retail", "Искусство, культура и развлечения": "marketing",
              "Государственная служба, некоммерческие организации": "operations"}
PROF = re.compile(r"инженер|программист|разработчик|аналитик|экономист|бухгалтер|юрист|юрисконсульт|менеджер|специалист|руководител|директор|начальник|заместител|"
                  r"главный|ведущий|технолог|конструктор|архитектор|дизайнер|маркетолог|научн|исследоват|переводчик|аудитор|системный администратор|логист|"
                  r"закупк|кадр|рекрутер|\bhr\b|data|devops|тестировщик|эколог|геолог|геодезист|метролог|сметчик|проектировщик|эксперт|консультант|"
                  r"\bit\b|1с|1c|smm|копирайтер|редактор|журналист|оператор пк", re.I)
NOT_OFFICE = re.compile(r"продав|кассир|грузчик|уборщ|дворник|охранник|сторож|водител|повар|официант|санитар|кладовщ|разнорабоч|подсобн|мерчендайзер|курьер|"
                        r"комплектовщ|упаковщ|фасовщ|горничн|мойщ|посудомо|сиделк|няня|медицинская сестра|медсестра|фельдшер|врач|младший воспитатель", re.I)
# Regions of Ukraine that the portal lists as Russian regions. A job there would be shown as "Russia" with the Russian flag, which the
# rest of the world does not recognise, so these vacancies are left out rather than labelled with a country we cannot defend.
OCCUPIED = re.compile(r"крым|севастопол|донецк|луганск|запорож|херсон", re.I)
SKIP_SPHERES = {"Здравоохранение и социальное обеспечение", "Работы, не требующие квалификации", "Домашний персонал", "Безопасность, службы охраны"}

FORMS = [("ОБЩЕСТВО С ОГРАНИЧЕННОЙ ОТВЕТСТВЕННОСТЬЮ", "ООО"), ("НЕПУБЛИЧНОЕ АКЦИОНЕРНОЕ ОБЩЕСТВО", "АО"), ("ПУБЛИЧНОЕ АКЦИОНЕРНОЕ ОБЩЕСТВО", "ПАО"),
         ("ЗАКРЫТОЕ АКЦИОНЕРНОЕ ОБЩЕСТВО", "ЗАО"), ("ОТКРЫТОЕ АКЦИОНЕРНОЕ ОБЩЕСТВО", "ОАО"), ("АКЦИОНЕРНОЕ ОБЩЕСТВО", "АО"),
         ("ИНДИВИДУАЛЬНЫЙ ПРЕДПРИНИМАТЕЛЬ", "ИП"), ("ОБЩЕСТВО С ДОПОЛНИТЕЛЬНОЙ ОТВЕТСТВЕННОСТЬЮ", "ОДО")]
SMALL = {"и", "в", "на", "по", "с", "для", "при", "имени", "им.", "№", "из", "о", "об", "от", "до", "к", "у"}   # kept lower case inside a name


def company_name(full):
    """'ОБЩЕСТВО С ОГРАНИЧЕННОЙ ОТВЕТСТВЕННОСТЬЮ "РОМАШКА"' -> 'ООО «Ромашка»'; a long state form is shortened to its initials
    ('ФЕДЕРАЛЬНОЕ КАЗЕННОЕ УЧРЕЖДЕНИЕ "…"' -> 'ФКУ «…»'). Only the name changes case; the words stay the employer's own."""
    s = re.sub(r"\s+", " ", str(full or "")).strip().strip(",")
    if not s: return ""
    up = s.upper()
    form, rest = "", s
    for long, short in FORMS:
        if up.startswith(long):
            form, rest = short, s[len(long):].strip(); break
    if not form:
        q = re.search(r"[\"«]", s)
        head = s[:q.start()].strip() if q else ""
        if head and head.upper() == head and (len(head.split()) >= 2 or len(head) <= 6):   # a legal form in capitals ("ПАО", "МУНИЦИПАЛЬНОЕ …") before a quoted name
            form = head if len(head.split()) == 1 else "".join(w[0] for w in head.split() if w[0].isalpha()).upper()
            rest = s[q.start():]
    name = re.sub(r"\s+", " ", re.sub(r"[\"«»“”]", " ", rest)).strip()
    if name.upper() == name:                                              # SHOUTED -> Sentence case, keeping short abbreviations
        words = name.lower().split()
        name = " ".join(w if w in SMALL and i else w.upper() if not re.search("[аеёиоуыэюяaeiouy]", w) else w.capitalize() for i, w in enumerate(words))
    if len(name) > 90: name = name[:90].rsplit(" ", 1)[0] + "…"
    return f"{form} «{name}»" if form and name else (name or form)


SETTLEMENT = re.compile(r"^(г\.?|город|пгт\.?|рабочий поселок|п\.?|пос\.?|поселок|посёлок|с\.?|село|д\.?|деревня|ст-ца|станица|аул|х\.?|хутор)\s+(.+)$|"
                        r"^(.+?)\s+(город|рабочий поселок|поселок городского типа|поселок|посёлок|село|деревня|станица)$", re.I)


def place_of(region, address):
    """'Москва, Russia' or 'Зубово-Полянский район… → Ударный, Республика Мордовия, Russia': the settlement and the region, never the street."""
    region = re.sub(r"^город\s+", "", str(region or "").strip(), flags=re.I)
    city = ""
    for part in str(address or "").split(","):
        m = SETTLEMENT.match(part.strip())
        if m:
            city = (m.group(2) or m.group(3) or "").strip(); break
    parts = [p for p in (city, region) if p]
    if len(parts) == 2 and parts[0].lower() == parts[1].lower(): parts = parts[:1]
    return ", ".join(parts + ["Russia"])


def wanted(row):
    """Whether a vacancy is one the site takes (see the module text), and its field when the title alone does not tell it."""
    if (row.get("fullCompanyName") or "").upper().startswith("ИНДИВИДУАЛЬНЫЙ ПРЕДПРИНИМАТЕЛЬ"): return None   # a sole trader's name is a person's name: not made into a company page
    if row.get("sourceType") != "Вакансия работодателя" or row.get("status") != "Одобрено" or row.get("deleted") != "False": return None
    if row.get("visibility") not in ("Видно всем", ""): return None
    if OCCUPIED.search(row.get("regionName") or ""): return None
    sphere, title = row.get("professionalSphereName") or "", row.get("vacancyName") or ""
    if NOT_OFFICE.search(title): return None
    if sphere in OFFICE: return OFFICE[sphere]
    if sphere in SKIP_SPHERES or not PROF.search(title): return None
    return SPHERE_CAT.get(sphere, "manufacturing" if sphere else "other")


def to_job(row, field):
    """One vacancy as a job record (collect.norm); None when it lacks a title, an employer or a link."""
    import collect
    title, url = (row.get("vacancyName") or "").strip(), row.get("vacancyUrl") or ""
    company = company_name(row.get("fullCompanyName") or "")
    if not company:
        try: company = company_name(json.loads(row.get("company") or "{}").get("name") or "")
        except ValueError: company = ""
    if not title or not company or not url.startswith("https://trudvsem.ru/"): return None
    title = title[0].upper() + title[1:]
    blocks = [("Обязанности", row.get("responsibilities")), ("Требования", row.get("positionRequirements") or row.get("qualifications")),
              ("Дополнительно", row.get("additionalRequirements")), ("Условия", " ".join(filter(None, [row.get("conditions") if row.get("conditions") not in ("Оптимальные", "Допустимые") else "", row.get("benefit") or ""])))]
    desc = "".join(f"<h3>{h}</h3><p>{collect.html.escape(t.strip())}</p>" for h, t in blocks if t and t.strip())
    lo, hi = row.get("salaryMin") or "", row.get("salaryMax") or ""
    sal = collect.pay(lo, hi or lo, "RUB", "month") if lo else ""
    hint = {"Полная занятость": "full-time", "Частичная занятость": "part-time", "Временная": "temporary", "Стажировка": "internship",
            "Сезонная": "temporary", "Удаленная": ""}.get(row.get("busyType") or "", "")
    remote = (row.get("busyType") or "") == "Удаленная" or "удален" in (row.get("scheduleType") or "").lower()
    j = collect.norm(company, "trudvsem", row.get("id"), title, url, place_of(row.get("regionName"), row.get("vacancyAddress")), remote,
                     row.get("professionalSphereName") or "", (row.get("datePublished") or row.get("creationDate") or "")[:10],
                     collect.strip_html(desc), sal, hint, desc, posted_at=row.get("datePublished"))
    if j["cat"] == "other": j["cat"] = field
    j["id"] = f"trudvsem-{row.get('id')}"          # the portal's own id: stays the same when the employer's shown name changes
    j["src"] = SOURCE
    return j


def _job(item):
    row, field = item
    j = to_job(row, field)
    if j:
        try: j["_ogrn"] = json.loads(row.get("company") or "{}").get("ogrn") or ""
        except ValueError: j["_ogrn"] = ""
    return j


KEEP = ("id", "vacancyName", "vacancyUrl", "fullCompanyName", "company", "regionName", "vacancyAddress", "professionalSphereName", "datePublished",
        "creationDate", "responsibilities", "positionRequirements", "qualifications", "additionalRequirements", "conditions", "benefit",
        "salaryMin", "salaryMax", "busyType", "scheduleType")


def read(stream, limit=None):
    """The wanted vacancies of a vacancy.csv stream as job records, newest first, at most `limit`.
    The rows are chosen and sorted first (cheap); only the kept ones are read into job records, on every CPU core (about 20 ms each).
    Employers that share one name ('ООО «Альфа»' exists in many towns) get their town added, so two firms never merge into one page."""
    import multiprocessing
    csv.field_size_limit(1 << 30)
    rows = csv.reader(stream, delimiter="|")
    hdr = next(rows)
    picked = []
    for r in rows:
        if len(r) != len(hdr): continue
        row = dict(zip(hdr, r))
        field = wanted(row)
        if field is not None: picked.append(({k: row.get(k, "") for k in KEEP}, field))
    picked.sort(key=lambda x: x[0].get("datePublished") or x[0].get("creationDate") or "", reverse=True)
    if limit: picked = picked[:limit]
    if len(picked) > 2000:
        with multiprocessing.get_context("fork").Pool() as pool:
            jobs = [j for j in pool.map(_job, picked, chunksize=500) if j]
    else:
        jobs = [j for j in map(_job, picked) if j]
    firms = defaultdict(set)
    for j in jobs: firms[j["company"]].add(j["_ogrn"])
    for j in jobs:
        if len(firms[j["company"]]) > 1:
            town = j["location"].split(",")[0].strip()
            j["company"] = f"{j['company']} ({town})" if town and town != "Russia" else j["company"]
        j.pop("_ogrn", None)
    return jobs


def fetch(limit=None):
    """Download and read the daily file; None when it cannot be read (the jobs from it then stay as they were)."""
    limit = limit or int(os.environ.get("HRN_TRUDVSEM_MAX") or 60000)
    if os.environ.get("HRN_TRUDVSEM_FILE"):                    # a copy of the file already on disk (for measuring a build locally)
        return read(open(os.environ["HRN_TRUDVSEM_FILE"], encoding="utf-8", errors="replace", newline=""), limit)
    try:
        # at most 40 minutes (portals.yml runs apart from the hourly run), and given up if it crawls below 100 KB/s for two minutes
        p = subprocess.Popen(["curl", "-s", "-4", "--fail", "--connect-timeout", "30", "--speed-limit", "100000", "--speed-time", "120", "--max-time", "2400",
                              "-A", "Mozilla/5.0 (job-board aggregator)", CSV_URL], stdout=subprocess.PIPE)
        jobs = read(io.TextIOWrapper(p.stdout, encoding="utf-8", errors="replace", newline=""), limit)
        if p.wait() != 0 or len(jobs) < 1000: return None          # a cut-off download must not close the jobs it no longer lists
        return jobs
    except Exception as ex:
        print(f"Работа России: {type(ex).__name__}: {ex}")
        return None


if __name__ == "__main__":                                      # python3 trudvsem.py [file.csv]: what would be taken, by field and region
    src = open(sys.argv[1], encoding="utf-8", errors="replace", newline="") if len(sys.argv) > 1 else None
    jobs = read(src) if src else fetch()
    print(len(jobs or []), "jobs")
    if jobs:
        print(Counter(j["cat"] for j in jobs).most_common())
        print(Counter(j["location"].split(", ")[-2] if j["location"].count(",") else j["location"] for j in jobs).most_common(15))
        print(len({j["company"] for j in jobs}), "employers")
