"""Google's Indexing API for the job pages: tells Google about new jobs, so they reach Google Jobs sooner.

Why (owner, 20 Nov 2026, after adding the site to Search Console): Google reads the sitemaps on its own schedule; for job postings it
offers this API, the only pages besides live streams it accepts there. Its quota is 200 notifications a day by default (a day that ends
at midnight Pacific time), against tens of thousands of new jobs a day, so only the best few are sent. The sitemaps stay the way every
other job reaches Google.

Two senders, one record of what was sent (data/indexing_sent.json, carried from run to run in the Actions cache):
  - the hourly workflow (.github/workflows/indexing.yml, --live): the newest jobs of the live site, those posted in the last 48 hours
    first, never a talent pool or a posting 90+ days old (build.stale), each page opened first: it must answer 200 under its own address
    and carry valid JobPosting markup. It spreads the day's 200 over the hours left in Google's day, about 8 or 9 an hour.
  - the collecting run (update.yml, after its upload): the best jobs new in that run, but only when the hourly workflow has not run for
    two hours (its fallback), and never more than the day has left.
An address sent once is not sent again for 30 days, by either of them.
Until 27 Nov 2026 only the second one existed: it sent 20 a run, and only runs that collected and uploaded reached it (about 5 a day,
pushes cancel the rest), so Google got 20 to 100 a day of its 200 (380 in the week of 20 to 26 Nov).

The key is a Google Cloud service account's JSON key, kept by the owner as the repository secret GOOGLE_INDEXING_KEY; that account is
an owner of the site in Search Console. Without the secret nothing is sent.

    python3 indexing.py --snapshot          before collecting: the ids of the open jobs (data/indexing_prev.txt)
    python3 indexing.py                     after the upload: notify Google of the best new jobs (fallback, see above)
    python3 indexing.py --live              the hourly sender: the newest jobs of the live site, each page checked first
    python3 indexing.py --live --dry-run    the same, printing what it would send; needs no key and changes nothing
    python3 indexing.py --dry-run           the collecting run's choice, printed instead of sent
    python3 indexing.py --validate URL...   the JobPosting markup of these pages against Google's required and recommended fields
    python3 indexing.py --test              checks the signing, the choice, the markup reader and the day's budget on made-up data
    python3 indexing.py --check             with the key: is it right, and is the site ours in Search Console (nothing is sent)
"""
import base64, datetime, html.parser, json, math, os, re, subprocess, sys, tempfile, time, urllib.error, urllib.parse, urllib.request
from pathlib import Path

ROOT = Path(__file__).parent
JOBS = ROOT / "data" / "jobs.json"
PREV = ROOT / "data" / "indexing_prev.txt"
STATE = Path(os.environ.get("HRN_INDEXING_STATE") or ROOT / "data" / "indexing_sent.json")
SITE = json.loads((ROOT / "config.json").read_text()).get("base_url", "https://jobseveryhour.com").rstrip("/")
PER_RUN = int(os.environ.get("HRN_INDEXING_PER_RUN") or 20)     # the collecting run's most, when it sends at all (fallback)
# Google's default: publish requests a day per Cloud project. When Google grants more, the owner sets the repository variable
# HRN_INDEXING_DAILY (Settings > Secrets and variables > Actions > Variables) to the new number; both workflows pass it here.
DAILY = int(os.environ.get("HRN_INDEXING_DAILY") or 200)
LIVE_MAX = max(20, DAILY // 10)  # the hourly sender's most in one run (after skipped runs; normally the day's share, 8 or 9 at 200)
KEEP_DAYS = 30                 # an address sent is not sent again for this long
FRESH_H = 48                   # "fresh": posted in the last 48 hours
LONG_OPEN = 90                 # build.LONG_OPEN: a posting its employer dated this many days ago or more is stale (build.stale)
LIVE_GAP = 2 * 3600            # the collecting run sends only when the hourly sender has not run for this long
UA = "jobseveryhour-indexing/1.0 (+https://jobseveryhour.com/)"
SCOPE = "https://www.googleapis.com/auth/indexing"
TOKEN_URL = "https://oauth2.googleapis.com/token"
PUBLISH = "https://indexing.googleapis.com/v3/urlNotifications:publish"
try:
    from zoneinfo import ZoneInfo
    PACIFIC = ZoneInfo("America/Los_Angeles")      # Google's daily quotas end at midnight Pacific time
except Exception:                                  # no time zone data: Pacific standard time all year
    PACIFIC = datetime.timezone(datetime.timedelta(hours=-8))


def b64(data):
    return base64.urlsafe_b64encode(data).rstrip(b"=").decode()


def jwt(key, now=None):
    """A JSON Web Token signed with the service account's private key (RS256), by openssl: the runner has no crypto package."""
    now = int(now or time.time())
    head = b64(json.dumps({"alg": "RS256", "typ": "JWT"}).encode())
    claims = b64(json.dumps({"iss": key["client_email"], "scope": SCOPE, "aud": TOKEN_URL, "iat": now, "exp": now + 3600}).encode())
    with tempfile.NamedTemporaryFile("w", suffix=".pem", delete=False) as f:
        f.write(key["private_key"]); pem = f.name
    try:
        os.chmod(pem, 0o600)
        sig = subprocess.run(["openssl", "dgst", "-sha256", "-sign", pem], input=f"{head}.{claims}".encode(), capture_output=True, check=True).stdout
    finally:
        os.unlink(pem)
    return f"{head}.{claims}.{b64(sig)}"


def token(key):
    body = urllib.parse.urlencode({"grant_type": "urn:ietf:params:oauth:grant-type:jwt-bearer", "assertion": jwt(key)}).encode()
    with urllib.request.urlopen(urllib.request.Request(TOKEN_URL, data=body), timeout=30) as r:
        return json.loads(r.read())["access_token"]


# ---- what was sent: one record for both senders ----

def iso(ts):
    return time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime(ts))


def quota_day(now):
    """The day of Google's quota: it starts at midnight Pacific time (08:00 UTC in winter)."""
    return datetime.datetime.fromtimestamp(now, PACIFIC).date().isoformat()


def hours_left(now):
    """Whole hours, at least 1, until Google's quota day ends."""
    local = datetime.datetime.fromtimestamp(now, PACIFIC)
    end = datetime.datetime.combine(local.date() + datetime.timedelta(days=1), datetime.time(), PACIFIC)
    return max(1, math.ceil((end.timestamp() - now) / 3600))


def load_state(path=None):
    """{"sent": {address: when}, "days": {quota day: how many}, "full": the quota day Google said was used up, "live_at": the hourly
    sender's last run}. Missing or unreadable: an empty record."""
    try: s = json.loads(Path(path or STATE).read_text())
    except (OSError, ValueError): s = {}
    if not isinstance(s, dict): s = {}
    s["sent"] = s.get("sent") if isinstance(s.get("sent"), dict) else {}
    s["days"] = s.get("days") if isinstance(s.get("days"), dict) else {}
    return s


def save_state(s, now, path=None):
    cut, cut_day = iso(now - KEEP_DAYS * 86400), quota_day(now - 7 * 86400)
    s["sent"] = {u: t for u, t in s["sent"].items() if t >= cut}
    s["days"] = {d: n for d, n in s["days"].items() if d >= cut_day}
    p = Path(path or STATE)
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(json.dumps(s, sort_keys=True, separators=(",", ":")))


def left_today(s, now):
    """How many the quota day has left by our own count (0 once Google answered "quota exceeded")."""
    day = quota_day(now)
    return 0 if s.get("full") == day else max(0, DAILY - int(s["days"].get(day) or 0))


def hourly_share(s, now, cap=LIVE_MAX):
    """This hour's part of what the day has left, less what either sender sent in the last 50 minutes: about 9 an hour, more after
    skipped runs, nothing for the second start of an hour that the first one served."""
    left = left_today(s, now)
    if not left: return 0
    recent = sum(1 for t in s["sent"].values() if t >= iso(now - 50 * 60))
    return max(0, min(cap, left, math.ceil(left / hours_left(now)) - recent))


def publish(urls, raw, s):
    """Sends the addresses one by one and notes each one sent in the record. Stops at "quota exceeded" (429, the day is marked used up),
    at a refused key or permission (401, 403: the next ones would fail too) and when Google cannot be reached."""
    bearer, sent, codes = token(json.loads(raw)), [], {}
    for u in urls:
        req = urllib.request.Request(PUBLISH, data=json.dumps({"url": u, "type": "URL_UPDATED"}).encode(),
                                     headers={"Authorization": f"Bearer {bearer}", "Content-Type": "application/json"})
        try:
            with urllib.request.urlopen(req, timeout=30) as r: code = r.status
        except urllib.error.HTTPError as e:
            codes[e.code] = codes.get(e.code, 0) + 1
            if e.code == 429:
                s["full"] = quota_day(time.time())
                print("indexing: Google's daily quota is used up (429), the rest wait for its next day (midnight Pacific time)"); break
            print(f"indexing: {u} answered {e.code}: {e.read()[:200]!r}")
            if e.code in (401, 403): break
            continue
        except (urllib.error.URLError, OSError) as ex:
            print(f"indexing: Google could not be reached ({type(ex).__name__}), stopping"); break
        codes[code] = codes.get(code, 0) + 1
        now = time.time()
        s["sent"][u] = iso(now)
        day = quota_day(now)
        s["days"][day] = int(s["days"].get(day) or 0) + 1
        sent.append(u)
        print(f"indexing: sent {u}")
    print("indexing: Google answered " + ", ".join(f"{n} x {c}" for c, n in sorted(codes.items())) if codes else "indexing: nothing was sent")
    return sent


# ---- the collecting run's choice (update.yml) ----

def eligible(j):
    """A job whose page carries Google's job markup, in the main: open, with its full text and a place (build.job_page's rule)."""
    return j.get("active") and not j.get("tg") and bool(j.get("desc")) and bool(j.get("location"))


def rank(j):
    """Best first: a stated salary, then an exact posting time, then the newest."""
    return (bool(j.get("salary")), bool(j.get("posted_at")), j.get("posted_at") or j.get("posted") or "", j.get("first_seen") or "")


def choose(jobs, prev, n=PER_RUN, skip=(), today=None):
    """The best n new jobs, one per company and title (a role posted in five cities is one notification), none of the addresses in skip,
    no talent pool and no posting its employer dated 90+ days ago (build.stale)."""
    old = ((today or datetime.date.today()) - datetime.timedelta(days=LONG_OPEN)).isoformat()
    out, seen = [], set()
    for j in sorted((j for j in jobs if j.get("id") not in prev and eligible(j) and not j.get("pool") and not (j.get("posted") or "9")[:10] < old
                     and f"{SITE}/job/{j.get('slug')}/" not in skip), key=rank, reverse=True):
        k = (j.get("company"), (j.get("title") or "").lower())
        if k in seen: continue
        seen.add(k); out.append(j)
        if len(out) >= n: break
    return out


def load():
    import jobsdb                                  # one record at a time, see jobsdb.py
    db = jobsdb.load(JOBS)
    return list(db.values()) if isinstance(db, dict) else db


# ---- the markup of a page: JSON-LD and microdata (build.job_page writes microdata when the page carries the full text) ----

VOID = {"area", "base", "br", "col", "embed", "hr", "img", "input", "link", "meta", "param", "source", "track", "wbr"}


class Tree(html.parser.HTMLParser):
    """The page as nested {"tag", "a" (attributes), "kids"}; enough of HTML for the site's own pages."""
    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.root = {"tag": "", "a": {}, "kids": []}
        self.stack = [self.root]

    def handle_starttag(self, tag, attrs):
        n = {"tag": tag, "a": dict(attrs), "kids": []}
        self.stack[-1]["kids"].append(n)
        if tag not in VOID: self.stack.append(n)

    def handle_startendtag(self, tag, attrs):
        self.stack[-1]["kids"].append({"tag": tag, "a": dict(attrs), "kids": []})

    def handle_endtag(self, tag):
        for i in range(len(self.stack) - 1, 0, -1):
            if self.stack[i]["tag"] == tag:
                del self.stack[i:]; break

    def handle_data(self, d):
        self.stack[-1]["kids"].append(d)


def _text(n, sep=""):
    return "".join(k if isinstance(k, str) else sep + _text(k, sep) + sep for k in n["kids"])


def _value(n):
    a, t = n["a"], n["tag"]
    if "itemscope" in a: return _item(n)
    if t == "meta": return a.get("content") or ""
    if t in ("a", "link", "area"): return a.get("href") or ""
    if t in ("img", "audio", "video", "source", "embed", "iframe", "track"): return a.get("src") or ""
    if t == "time" and a.get("datetime"): return a["datetime"]
    if t in ("data", "meter"): return a.get("value") or ""
    return " ".join(_text(n, " ").split())


def _props(n, out):
    for k in n["kids"]:
        if isinstance(k, str): continue
        for p in (k["a"].get("itemprop") or "").split(): out.setdefault(p, []).append(_value(k))
        if "itemscope" not in k["a"]: _props(k, out)


def _item(n):
    props = {}
    _props(n, props)
    return {"@type": (n["a"].get("itemtype") or "").rstrip("/").rsplit("/", 1)[-1], **{k: v[0] if len(v) == 1 else v for k, v in props.items()}}


def _kind(x):
    t = x.get("@type") if isinstance(x, dict) else None
    return [str(v).rsplit("/", 1)[-1] for v in (t if isinstance(t, list) else [t]) if v]


def job_items(page):
    """Every JobPosting of a page, from its JSON-LD blocks and its microdata, as JSON-LD-like dicts."""
    t = Tree()
    t.feed(page); t.close()
    found = []

    def walk(n):
        for k in n["kids"]:
            if isinstance(k, str): continue
            if k["tag"] == "script":
                if (k["a"].get("type") or "").strip().lower() == "application/ld+json":
                    try: todo = [json.loads(_text(k))]
                    except ValueError: continue
                    while todo:
                        x = todo.pop()
                        if isinstance(x, list): todo += x
                        elif isinstance(x, dict):
                            if isinstance(x.get("@graph"), list): todo += x["@graph"]
                            found.append(x)
            elif "itemscope" in k["a"] and "itemprop" not in k["a"]: found.append(_item(k))
            else: walk(k)
    walk(t.root)
    return [x for x in found if "JobPosting" in _kind(x)]


SALARY_UNITS = {"HOUR", "DAY", "WEEK", "MONTH", "YEAR"}
EMPLOYMENT = {"FULL_TIME", "PART_TIME", "CONTRACTOR", "TEMPORARY", "INTERN", "VOLUNTEER", "PER_DIEM", "OTHER"}


def _day(v):
    try: return datetime.date.fromisoformat(str(v)[:10])
    except ValueError: return None


def problems(ld, today=None):
    """(errors, warnings) of one JobPosting against Google's job posting documentation: errors for the required properties (title,
    description, datePosted, hiringOrganization with its name, jobLocation, or for a remote job jobLocationType TELECOMMUTE with
    applicantLocationRequirements) and for values Google cannot use (an expired validThrough, a salary without currency or unit);
    warnings for the recommended ones it lacks (validThrough, baseSalary, employmentType, identifier, directApply, the logo)."""
    today = today or datetime.date.today()
    err, warn = [], []
    many = lambda v: v if isinstance(v, list) else [v] if v not in (None, "") else []
    text = lambda v: v.strip() if isinstance(v, str) else ""
    if not text(ld.get("title")): err.append("title is missing")
    d = ld.get("description")
    d = d if isinstance(d, str) else ""
    if not d.strip(): err.append("description is missing")
    elif len(re.sub(r"<[^>]+>", " ", d).split()) < 30: warn.append("description is very short: Google wants the full text of the job")
    posted = _day(ld.get("datePosted") or "")
    if not ld.get("datePosted"): err.append("datePosted is missing")
    elif not posted: err.append(f"datePosted is no ISO 8601 date: {ld['datePosted']!r}")
    elif posted > today + datetime.timedelta(days=1): err.append(f"datePosted is in the future: {ld['datePosted']}")
    org = ld.get("hiringOrganization")
    org = org[0] if isinstance(org, list) and org else org
    if not org: err.append("hiringOrganization is missing")
    elif isinstance(org, dict):
        if not text(org.get("name")): err.append("hiringOrganization.name is missing")
        if not org.get("logo"): warn.append("hiringOrganization.logo is missing")
        if not org.get("sameAs"): warn.append("hiringOrganization.sameAs is missing")
    remote = "TELECOMMUTE" in [str(x).upper() for x in many(ld.get("jobLocationType"))]
    places = many(ld.get("jobLocation"))
    lands = many(ld.get("applicantLocationRequirements"))
    if remote and not lands: err.append("a remote job (jobLocationType TELECOMMUTE) needs applicantLocationRequirements")
    if not places and not remote: err.append("jobLocation is missing (or jobLocationType TELECOMMUTE for a remote job)")
    for p in places:
        a = p.get("address") if isinstance(p, dict) else None
        a = a[0] if isinstance(a, list) and a else a
        if not isinstance(a, dict): err.append("jobLocation has no address"); continue
        if not a.get("addressCountry"): warn.append("jobLocation.address.addressCountry is missing")
        if not (a.get("addressLocality") or a.get("addressRegion")): warn.append("jobLocation.address has neither addressLocality nor addressRegion")
    for c in lands:
        if not (isinstance(c, dict) and text(c.get("name"))): err.append("applicantLocationRequirements without a name")
    if not ld.get("validThrough"): warn.append("validThrough is missing")
    else:
        until = _day(ld["validThrough"])
        if not until: err.append(f"validThrough is no ISO 8601 date: {ld['validThrough']!r}")
        elif until < today: err.append(f"validThrough is past ({ld['validThrough']}): Google treats the job as expired")
    pay = ld.get("baseSalary")
    if not pay: warn.append("baseSalary is missing")
    else:
        pay = pay[0] if isinstance(pay, list) else pay
        val = pay.get("value") if isinstance(pay, dict) else None
        if not (isinstance(pay, dict) and re.fullmatch(r"[A-Z]{3}", str(pay.get("currency") or ""))): err.append("baseSalary.currency is no ISO 4217 code")
        if isinstance(val, dict):
            num = lambda k: float(val[k]) if str(val.get(k, "")).replace(".", "", 1).isdigit() else None
            lo, hi, one = num("minValue"), num("maxValue"), num("value")
            if one is None and lo is None: err.append("baseSalary.value has neither value nor minValue")
            if lo is not None and hi is not None and lo > hi: err.append("baseSalary minValue is above maxValue")
            if str(val.get("unitText") or "").upper() not in SALARY_UNITS: err.append(f"baseSalary unitText is not one of {sorted(SALARY_UNITS)}")
        elif not str(val or "").replace(".", "", 1).isdigit(): err.append("baseSalary.value is missing")
    kinds = [str(x).upper() for x in many(ld.get("employmentType"))]
    if not kinds: warn.append("employmentType is missing")
    elif not set(kinds) <= EMPLOYMENT: err.append(f"employmentType {kinds} is not Google's")
    if not ld.get("identifier"): warn.append("identifier is missing")
    if ld.get("directApply") in (None, ""): warn.append("directApply is missing")
    return err, warn


def fetch(url, timeout=30):
    """(status, final address, headers, text) of a GET; HTTP errors raise."""
    req = urllib.request.Request(url, headers={"User-Agent": UA, "Accept": "text/html,application/json;q=0.9,*/*;q=0.5"})
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return r.status, r.geturl(), r.headers, r.read(4_000_000).decode("utf-8", "replace")


def page_check(url, today=None):
    """None when the job page is fit to be sent to Google, else why not: it must answer 200 under its own address (no redirect, canonical
    itself, no noindex) and carry JobPosting markup with nothing required missing."""
    try:
        code, final, head, page = fetch(url)
    except urllib.error.HTTPError as e:
        return f"answered {e.code}"
    except (urllib.error.URLError, OSError) as ex:
        return f"did not answer ({type(ex).__name__})"
    if code != 200: return f"answered {code}"
    if final != url: return f"redirects to {final}"
    if "noindex" in (head.get("X-Robots-Tag") or "").lower() or re.search(r'<meta[^>]+name="robots"[^>]+noindex', page, re.I): return "noindex"
    canon = re.search(r'<link rel="canonical" href="([^"]+)"', page)
    if canon and canon.group(1) != url: return f"names {canon.group(1)} as its canonical page"
    items = job_items(page)
    if not items: return "no JobPosting markup (closed, or no full text or country)"
    err = problems(items[0], today)[0]
    return "markup: " + "; ".join(err) if err else None


# ---- the hourly sender: the newest jobs of the live site ----

def candidates(get=None, want=250):
    """The newest open jobs: /api/latest (those live.py found since the last upload first, then the record's newest), then pages of the
    search list of jobs posted in the last two days, newest first (/api/search?list=1, rows as search_engine.row writes them), until
    there are `want`. As [{slug, title, company, salary, posted, t, pool}]; a source that fails is left out."""
    get = get or (lambda u: json.loads(fetch(u)[3]))
    out, errors = [], []
    try:
        out += [{"slug": j.get("slug"), "title": j.get("title") or "", "company": j.get("company") or "", "salary": j.get("salary") or "",
                 "posted": j.get("posted") or "", "t": int(j.get("t") or 0), "pool": bool(j.get("pool"))}
                for j in get(f"{SITE}/api/latest?limit=100").get("jobs") or [] if j.get("slug")]
    except Exception as ex:                         # noqa: BLE001  (any failure of one source: the other may still answer)
        errors.append(f"/api/latest: {type(ex).__name__}")
    for off in range(0, 5000, 50):
        if len(out) >= want: break
        try:
            rows = get(f"{SITE}/api/search?list=1&sort=new&age=2&offset={off}").get("jobs") or []
        except Exception as ex:                     # noqa: BLE001
            errors.append(f"/api/search: {type(ex).__name__}"); break
        for r in rows:
            if not isinstance(r, list) or len(r) < 15: continue
            p = str(r[9] or "")
            out.append({"slug": r[0], "title": r[1] or "", "company": r[2] or "", "salary": r[8] or "", "pool": bool(int(r[4] or 0) & 16),
                        "posted": f"{p[:4]}-{p[4:6]}-{p[6:8]}" if len(p) == 8 else "", "t": int(r[14] or 0) * 60})
        if not rows: break
    return out, errors


def live_rank(j, now):
    """None for a job not to send (a talent pool, a posting dated 90+ days ago: build.stale), else its order, best first: posted in the last
    48 hours, a stated salary (Google Jobs shows it), an exact posting time, the newest."""
    if j["pool"]: return None
    today = datetime.datetime.fromtimestamp(now, datetime.timezone.utc).date()
    day = _day(j["posted"]) if j["posted"] else None
    if day and day < today - datetime.timedelta(days=LONG_OPEN): return None
    fresh = now - j["t"] <= FRESH_H * 3600 if j["t"] else bool(day and day >= today - datetime.timedelta(days=FRESH_H // 24))
    return (fresh, bool(j["salary"]), bool(j["t"]), j["t"] or (day.toordinal() if day else 0))


def live_choose(jobs, skip, now):
    """In order, the jobs worth sending: not sent in the last 30 days, one per company and title, at most two per company a run."""
    ranked = sorted(((r, j) for j in jobs for r in [live_rank(j, now)] if r is not None and f"{SITE}/job/{j['slug']}/" not in skip),
                    key=lambda x: x[0], reverse=True)
    out, roles, per = [], set(), {}
    for _, j in ranked:
        k = (j["company"].lower(), j["title"].lower())
        if k in roles or per.get(k[0], 0) >= 2: continue
        roles.add(k); per[k[0]] = per.get(k[0], 0) + 1; out.append(j)
    return out


def live(argv):
    dry = "--dry-run" in argv
    raw = os.environ.get("GOOGLE_INDEXING_KEY", "").strip()
    if not raw and not dry:
        print("indexing: no GOOGLE_INDEXING_KEY secret, nothing sent"); return 0
    now = time.time()
    s = load_state()
    n = hourly_share(s, now)
    day = quota_day(now)
    print(f"indexing: Google's day {day} (Pacific time), {hours_left(now)} h left: {s['days'].get(day, 0)} of {DAILY} sent so far"
          + (", Google said the quota is used up" if s.get("full") == day else "") + f"; this run's share: {n}"
          + f" ({len(s['sent']):,} addresses sent in the last {KEEP_DAYS} days are skipped)")
    jobs, errors = candidates(want=max(250, 10 * n))
    if errors: print("indexing: could not read " + ", ".join(errors))
    if not jobs:
        print("indexing: the live site gave no jobs, nothing sent"); return 0
    if not dry:
        s["live_at"] = iso(now)                   # the collecting run's fallback stays out while this one works
    pick, why = [], {}
    if n:
        today = datetime.date.fromtimestamp(now)
        for j in live_choose(jobs, set(s["sent"]), now)[:3 * n + 10]:
            u = f"{SITE}/job/{j['slug']}/"
            bad = page_check(u, today)
            if bad:
                why[bad.split(":")[0]] = why.get(bad.split(":")[0], 0) + 1
                print(f"indexing: skipped {u}: {bad}")
                continue
            pick.append((u, j))
            if len(pick) >= n: break
    fresh = sum(1 for j in jobs if (live_rank(j, now) or (False,))[0])
    print(f"indexing: {len(jobs)} newest jobs read ({fresh} posted in the last {FRESH_H} h), {len(pick)} pages checked good"
          + (" (skipped: " + ", ".join(f"{k} {v}" for k, v in why.items()) + ")" if why else ""))
    if dry:
        for u, j in pick: print(f"would send {u}   [{j['posted'] or 'no date'}{', ' + j['salary'] if j['salary'] else ''}]")
        return 0
    try:
        sent = publish([u for u, _ in pick], raw, s) if pick else []
    finally:
        save_state(s, now)
    print(f"indexing: {len(sent)} of {len(pick)} sent to Google; {s['days'].get(day, 0)} of {DAILY} today")
    return 0


def main(argv):
    if argv[:1] == ["--snapshot"]:
        if JOBS.exists(): PREV.write_text("\n".join(j["id"] for j in load() if j.get("active")))
        print(f"indexing: {sum(1 for _ in PREV.open()) if PREV.exists() else 0:,} open jobs noted before collecting")
        return 0
    if argv[:1] == ["--test"]: return test()
    if argv[:1] == ["--check"]: return check()
    if argv[:1] == ["--validate"]: return validate(argv[1:])
    if "--live" in argv: return live(argv)
    raw = os.environ.get("GOOGLE_INDEXING_KEY", "").strip()
    if not raw and "--dry-run" not in argv:
        print("indexing: no GOOGLE_INDEXING_KEY secret, nothing sent"); return 0
    if not PREV.exists():
        print("indexing: no snapshot from before collecting (a run that did not collect), nothing new to send"); return 0
    now = time.time()
    s = load_state()
    if s.get("live_at") and s["live_at"] >= iso(now - LIVE_GAP):
        print(f"indexing: the hourly sender (indexing.yml) last ran at {s['live_at']}: it sends the new jobs, this run sends none"); return 0
    n = min(PER_RUN, left_today(s, now))
    if not n:
        print(f"indexing: Google's day {quota_day(now)} has no notifications left ({DAILY} a day), nothing sent"); return 0
    prev = set(PREV.read_text().split())
    urls = []
    for j in choose(load(), prev, 3 * n + 10, skip=set(s["sent"])):       # each page opened first, as the hourly sender does
        u = f"{SITE}/job/{j['slug']}/"
        bad = page_check(u)
        if bad: print(f"indexing: skipped {u}: {bad}"); continue
        urls.append(u)
        if len(urls) >= n: break
    if "--dry-run" in argv:
        print("\n".join(urls)); return 0
    try:
        sent = publish(urls, raw, s) if urls else []
    finally:
        save_state(s, now)
    print(f"indexing: {len(sent)} of {len(urls)} new jobs sent to Google ({len(prev):,} were open before this run)")
    return 0


def validate(urls):
    """The markup of each page, against Google's required (errors) and recommended (warnings) fields. Exit 1 on any error."""
    bad = 0
    for u in urls:
        try:
            code, final, _, page = fetch(u)
        except Exception as ex:                   # noqa: BLE001
            print(f"{u}\n  could not be read: {type(ex).__name__} {getattr(ex, 'code', '')}"); bad += 1; continue
        items = job_items(page)
        print(f"{u}\n  {code}{'' if final == u else ' -> ' + final}, {len(items)} JobPosting")
        for ld in items:
            err, warn = problems(ld)
            org = ld.get("hiringOrganization") if isinstance(ld.get("hiringOrganization"), dict) else {}
            print(f"  title: {ld.get('title')!r}; datePosted {ld.get('datePosted')}; validThrough {ld.get('validThrough')}; organization {org.get('name')!r}; "
                  f"jobLocationType {ld.get('jobLocationType', '-')}; employmentType {ld.get('employmentType', '-')}")
            print(f"  baseSalary: {json.dumps(ld.get('baseSalary')) if ld.get('baseSalary') else '-'}")
            print(f"  jobLocation: {json.dumps(ld.get('jobLocation'), ensure_ascii=False)}")
            if ld.get("applicantLocationRequirements"): print(f"  applicantLocationRequirements: {json.dumps(ld['applicantLocationRequirements'], ensure_ascii=False)}")
            print(f"  description: {len((ld.get('description') or '').split())} words")
            for x in err: print(f"  ERROR    {x}")
            for x in warn: print(f"  warning  {x}")
            bad += bool(err)
        bad += not items
    return 1 if bad else 0


def check():
    """Is the key right, and is its account an owner of the site in Search Console? Asks Google what it knows of one address,
    which uses no publishing quota: 404 (never notified) or 200 mean yes; 403 means the Search Console permission is missing."""
    raw = os.environ.get("GOOGLE_INDEXING_KEY", "").strip()
    if not raw: print("check: no GOOGLE_INDEXING_KEY secret"); return 1
    try: key = json.loads(raw)
    except ValueError: print("check: the secret is not the JSON key file's text"); return 1
    if not key.get("client_email") or not key.get("private_key"): print("check: the secret lacks client_email or private_key"); return 1
    try: bearer = token(key)
    except Exception as ex: print(f"check: Google refused the key ({type(ex).__name__}: {getattr(ex, 'code', '')}); is the Indexing API enabled?"); return 1
    url = "https://indexing.googleapis.com/v3/urlNotifications/metadata?url=" + urllib.parse.quote(SITE + "/", safe="")
    try:
        with urllib.request.urlopen(urllib.request.Request(url, headers={"Authorization": f"Bearer {bearer}"}), timeout=30) as r:
            print("check: OK, the key works and the site is ours (200)"); return 0
    except urllib.error.HTTPError as e:
        body = e.read()[:300].decode("utf-8", "replace")
        if e.code == 404: print("check: OK, the key works and the site is ours (404: nothing sent for this address yet)"); return 0
        if e.code == 403: print("check: the key works, but the account is not an owner of the site in Search Console: " + body); return 1
        print(f"check: {e.code} {body}"); return 1


def test():
    d = Path(tempfile.mkdtemp())
    subprocess.run(["openssl", "genrsa", "-out", str(d / "k.pem"), "2048"], capture_output=True, check=True)
    subprocess.run(["openssl", "rsa", "-in", str(d / "k.pem"), "-pubout", "-out", str(d / "p.pem")], capture_output=True, check=True)
    key = {"client_email": "jobs-indexing@example.iam.gserviceaccount.com", "private_key": (d / "k.pem").read_text()}
    t = jwt(key, now=1_800_000_000)
    head, claims, sig = t.split(".")
    pad = lambda s: base64.urlsafe_b64decode(s + "=" * (-len(s) % 4))
    c = json.loads(pad(claims))
    assert json.loads(pad(head)) == {"alg": "RS256", "typ": "JWT"} and c["scope"] == SCOPE and c["exp"] - c["iat"] == 3600
    (d / "sig").write_bytes(pad(sig))
    ok = subprocess.run(["openssl", "dgst", "-sha256", "-verify", str(d / "p.pem"), "-signature", str(d / "sig")], input=f"{head}.{claims}".encode(), capture_output=True)
    assert ok.returncode == 0, ok.stdout
    jobs = [{"id": "a", "active": True, "desc": "<p>x</p>", "location": "Austin, TX", "salary": "$90K", "posted": "2026-11-20", "slug": "a", "company": "Beta", "title": "Nurse"},
            {"id": "b", "active": True, "desc": "<p>x</p>", "location": "Austin, TX", "posted": "2026-11-20", "slug": "b", "company": "Beta", "title": "Driver"},
            {"id": "c", "active": True, "desc": "", "location": "Austin, TX", "slug": "c"},
            {"id": "d", "active": True, "desc": "<p>x</p>", "location": "Remote", "salary": "$1", "slug": "d"},
            {"id": "e", "active": False, "desc": "<p>x</p>", "location": "Austin, TX", "slug": "e"},
            {"id": "f", "active": True, "desc": "<p>x</p>", "location": "Dallas, TX", "salary": "$90K", "posted": "2026-11-19", "slug": "f", "company": "Acme", "title": "Cook"},
            {"id": "g", "active": True, "desc": "<p>x</p>", "location": "Austin, TX", "salary": "$90K", "posted": "2026-11-19", "slug": "g", "company": "Acme", "title": "Cook"}]
    day = datetime.date(2026, 11, 27)
    assert [j["id"] for j in choose(jobs, {"d"}, 5, today=day)] == ["a", "f", "b"], [j["id"] for j in choose(jobs, {"d"}, 5, today=day)]
    assert [j["id"] for j in choose(jobs, {"d"}, 5, skip={f"{SITE}/job/a/"}, today=day)] == ["f", "b"]
    jobs[0]["pool"], jobs[5]["posted"] = True, "2026-08-01"                                  # a talent pool, a posting 90+ days old
    assert [j["id"] for j in choose(jobs, {"d"}, 5, today=day)] == ["g", "b"]

    # the day's budget: Google's day ends at midnight Pacific time; 200 spread over the hours left, less the last 50 minutes' sends
    now = datetime.datetime(2026, 11, 27, 8, 30, tzinfo=datetime.timezone.utc).timestamp()      # 00:30 in Los Angeles (PST)
    assert quota_day(now) == "2026-11-27" and quota_day(now - 3600) == "2026-11-26" and hours_left(now) == 24
    s = {"sent": {}, "days": {}}
    assert hourly_share(s, now) == 9                                   # ceil(200 / 24)
    s["sent"].update({f"u{i}": iso(now - 600) for i in range(9)}); s["days"]["2026-11-27"] = 9
    assert hourly_share(s, now) == 0                                   # the hour's second start: the first one sent them
    assert hourly_share(s, now + 3600) == 9 and hourly_share(s, now + 23 * 3600) == 20        # ceil(191/23); the last hour: capped at 20
    s["full"] = "2026-11-27"
    assert hourly_share(s, now + 3600) == 0 and left_today(s, now + 24 * 3600) == 200          # 429: nothing until Google's next day
    s = {"sent": {"old": iso(now - 31 * 86400), "new": iso(now - 86400)}, "days": {"2026-11-01": 5, "2026-11-26": 3}}
    save_state(s, now, d / "st.json")
    s = load_state(d / "st.json")
    assert list(s["sent"]) == ["new"] and list(s["days"]) == ["2026-11-26"], s
    assert load_state(d / "missing.json") == {"sent": {}, "days": {}}

    # the hourly choice: no talent pool, nothing 90+ days old, fresh first, then a salary; one per role, two per company
    now = datetime.datetime(2026, 11, 27, 12, tzinfo=datetime.timezone.utc).timestamp()
    J = lambda slug, co, title, posted="2026-11-27", t=0, salary="", pool=False: {"slug": slug, "company": co, "title": title, "posted": posted, "t": t, "salary": salary, "pool": pool}
    jobs = [J("pool", "A", "Pool", pool=True), J("old", "B", "Old", posted="2026-08-01"), J("week", "C", "Week", posted="2026-11-20"),
            J("fresh", "D", "Fresh"), J("paid", "E", "Paid", salary="$90K"), J("exact", "F", "Exact", t=int(now) - 3600),
            J("e2", "E", "Paid"), J("e3", "E", "Other"), J("e4", "E", "Third"), J("sent", "G", "Sent")]
    got = [j["slug"] for j in live_choose(jobs, {f"{SITE}/job/sent/"}, now)]
    assert got == ["paid", "exact", "fresh", "e3", "week"], got

    # the markup reader: microdata as build.job_page writes it, and JSON-LD
    micro = ('<div itemscope itemtype="https://schema.org/JobPosting"><meta itemprop="title" content="Nurse &amp; Aide"><meta itemprop="datePosted" content="2026-11-27">'
             '<span itemprop="hiringOrganization" itemscope itemtype="https://schema.org/Organization"><meta itemprop="name" content="Beta"></span>'
             '<span itemprop="jobLocation" itemscope itemtype="https://schema.org/Place"><span itemprop="address" itemscope itemtype="https://schema.org/PostalAddress">'
             '<meta itemprop="addressLocality" content="Austin"><meta itemprop="addressRegion" content="TX"><meta itemprop="addressCountry" content="US"></span></span>'
             '<span itemprop="baseSalary" itemscope itemtype="https://schema.org/MonetaryAmount"><meta itemprop="currency" content="USD">'
             '<span itemprop="value" itemscope itemtype="https://schema.org/QuantitativeValue"><meta itemprop="minValue" content="90000"><meta itemprop="maxValue" content="110000">'
             '<meta itemprop="unitText" content="YEAR"></span></span><meta itemprop="validThrough" content="2026-12-27"><h2>About</h2>'
             '<div class="prose desc" itemprop="description"><p>' + "Care for patients on the ward. " * 8 + '<br>More.</p><ul><li>One</li></ul></div></div>')
    ld = job_items(f'<html><body><p>Open<p>{micro}<script type="application/ld+json">{{"@type":"BreadcrumbList"}}</script></body></html>')
    assert len(ld) == 1 and ld[0]["title"] == "Nurse & Aide" and ld[0]["hiringOrganization"]["name"] == "Beta", ld
    assert ld[0]["jobLocation"]["address"]["addressRegion"] == "TX" and ld[0]["baseSalary"]["value"]["unitText"] == "YEAR"
    assert ld[0]["description"].startswith("Care for patients") and ld[0]["description"].endswith("More. One"), ld[0]["description"]
    err, warn = problems(ld[0], datetime.date(2026, 11, 27))
    assert not err and "employmentType is missing" in warn and "baseSalary is missing" not in warn, (err, warn)
    assert "validThrough is past" in problems(ld[0], datetime.date(2027, 1, 2))[0][0]
    remote = {"@context": "https://schema.org", "@type": "JobPosting", "title": "Dev", "description": "<p>x</p>", "datePosted": "2026-11-27",
              "hiringOrganization": {"@type": "Organization", "name": "Acme"}, "jobLocationType": "TELECOMMUTE", "validThrough": "2026-12-27"}
    page = f'<script type="application/ld+json">{json.dumps({"@graph": [remote]})}</script>'
    assert job_items(page)[0]["title"] == "Dev"
    assert problems(remote, datetime.date(2026, 11, 27))[0] == ["a remote job (jobLocationType TELECOMMUTE) needs applicantLocationRequirements"]
    remote["applicantLocationRequirements"] = {"@type": "Country", "name": "Canada"}
    remote["baseSalary"] = {"@type": "MonetaryAmount", "currency": "usd", "value": {"@type": "QuantitativeValue", "value": 40, "unitText": "HOURLY"}}
    assert problems(remote, datetime.date(2026, 11, 27))[0] == ["baseSalary.currency is no ISO 4217 code", "baseSalary unitText is not one of ['DAY', 'HOUR', 'MONTH', 'WEEK', 'YEAR']"]
    assert not job_items('<div itemscope itemtype="https://schema.org/Organization"><meta itemprop="name" content="x"></div>')

    # the sources: /api/latest's records and the search list's rows
    feed = {f"{SITE}/api/latest?limit=100": {"jobs": [{"slug": "a", "title": "A", "company": "X", "posted": "2026-11-27", "t": 5, "pool": False, "salary": ""}]},
            f"{SITE}/api/search?list=1&sort=new&age=2&offset=0": {"jobs": [["b", "B", "Y", "Austin", 16, "eng", "", [], "$1", 20261126, 0, [], [], "", 7, [], 0, 0]]},
            f"{SITE}/api/search?list=1&sort=new&age=2&offset=50": {"jobs": []}}
    got, errs = candidates(lambda u: feed[u])
    assert not errs and got[0]["slug"] == "a" and got[1] == {"slug": "b", "title": "B", "company": "Y", "salary": "$1", "pool": True, "posted": "2026-11-26", "t": 420}, got
    print("indexing.py: all checks passed")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
