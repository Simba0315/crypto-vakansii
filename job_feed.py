"""The XML feed for job search engines (Careerjet, Jobisjob, Adzuna, Jobrapido, Talent.com, Trovit), in the shape Indeed describes:
<source> with <publisher>, <publisherurl>, <lastBuildDate>, then one <job> per posting, every value in CDATA.

What goes in (26 Nov 2026, AGGREGATORS_RESEARCH.md and the owner's list): every open job whose page shows its full description and
whose place names a country. Left out: posts read from Telegram channels, talent pools (a standing invitation, not an opening; Indeed
asks to hide them, Jora does not take them) and a second job with the same page address. Jobs employers post in their account are
in only once they are live: the API exports no job that waits for review.

The fields of a job come from the same code as the job page (build.page_desc, build.job_addresses, build.etype_ld), so the feed says
what the page and its JobPosting markup say. A value the posting does not give is left out, never guessed.

The files, newest jobs first, at most PART jobs each (all open jobs with their full text are several GB):
    feeds/jobs-1.xml ... jobs-N.xml      the parts, each with a gzipped copy jobs-N.xml.gz
    feeds/jobs.xml (and .xml.gz)         the newest PART jobs: the same file as jobs-1.xml, kept for the address already handed out
    feeds/index.xml                      the list of parts, with the number of jobs and the size of each

Memory and time (the build runs on a runner with little to spare, see jobsdb.py): every job is written to the file as soon as it is
made, nothing holds a part in memory. A second thread compresses the .gz copy while the first writes the plain file. The gzip stream
is cut (a full flush) after each job whose number falls on a fixed mark, about one job in 32, so a group of jobs compresses to the same
bytes in every build wherever it stands in the file: rsync, which uploads the site, then sends mostly the new jobs, not every file again.

    python3 job_feed.py --test           writes made-up jobs, reads them back and checks them
    python3 job_feed.py site/feeds       checks the built files: well-formed, required fields, no control characters, .gz = plain
"""
import datetime, os, queue, re, shutil, sys, threading, zlib
import xml.etree.ElementTree as ET
from email.utils import format_datetime
from html import escape
from pathlib import Path

PART = 50000          # jobs per file
LEVEL = 4             # gzip level: 66 MB/s and 5.0 times smaller on the local record; level 6 is half as fast for 5% less
CUT = 32              # about one job in CUT ends a gzip block (see above)
MIN_FREE = 6 << 30    # no new file is started with less than this free on the disk: the rest of the build and the upload need room too
# characters XML 1.0 does not allow (C0 controls but tab and line ends, lone surrogates, U+FFFE/FFFF) and the C1 controls it allows
# but no reader expects: each becomes a space in every value (a vertical tab or U+0085 often stands between two words)
BAD = re.compile("[\x00-\x08\x0b\x0c\x0e-\x1f\x7f-\x9f\ud800-\udfff\ufffe\uffff]")
JOBTYPE = {"FULL_TIME": "fulltime", "PART_TIME": "parttime", "CONTRACTOR": "contract", "INTERN": "internship", "TEMPORARY": "temporary"}
REQUIRED = ("title", "date", "referencenumber", "url", "company", "country", "description")
ISO_TIME = re.compile(r"^\d{4}-\d\d-\d\dT\d\d:\d\d:\d\dZ$")
ISO_DAY = re.compile(r"^\d{4}-\d\d-\d\d$")


def cdata(v):
    """A value in CDATA; "]]>" inside it is split across two sections, the only way CDATA can carry it."""
    return "<![CDATA[" + BAD.sub(" ", str(v)).replace("]]>", "]]]]><![CDATA[>") + "]]>"


def place(j, b):
    """The first place of a posting that names its country, as the JobPosting markup writes it, or None."""
    return next((a for a in b.job_addresses(j.get("location")) if a.get("addressCountry")), None)


def posted(j):
    """When the employer published the job, in ISO 8601: the exact time when the hiring system gives one, else the day."""
    at = j.get("posted_at") or ""
    if ISO_TIME.match(at): return at
    day = (j.get("posted") or j.get("first_seen") or "")[:10]
    return day + "T00:00:00Z" if ISO_DAY.match(day) else ""


def item(j, b, full, addr):
    """One <job> as text: the fields Indeed lists, plus <updated> (Jooble, Jobsora, Jobisjob ask for it). Empty values are left out."""
    tag = lambda k, v: f"<{k}>{cdata(v)}</{k}>" if v else ""
    kind = JOBTYPE.get(b.etype_ld(j, full) or "", "")
    return ("<job>" + tag("title", j["title"]) + tag("date", posted(j)) + tag("referencenumber", j["id"]) + tag("url", f'{b.FULL}/job/{j["slug"]}/')
            + tag("company", j["company"]) + tag("city", addr.get("addressLocality")) + tag("state", addr.get("addressRegion"))
            + tag("country", addr["addressCountry"]) + tag("postalcode", addr.get("postalCode")) + tag("streetaddress", addr.get("streetAddress"))
            + tag("description", full) + tag("salary", j.get("salary")) + tag("jobtype", kind)
            + tag("experience", f'{j["years"]}+ years' if (j.get("years") or 0) > 0 else "")
            + tag("category", "" if j.get("cat") == b.OTHER[0] else b.CAT.get(j.get("cat"), ""))
            + tag("remotetype", "Fully remote" if j.get("remote") else "Hybrid remote" if j.get("hybrid") else "")
            + tag("expirationdate", b.VALID_TO) + tag("updated", (j.get("last_seen") or "")[:10]) + "</job>\n")


class _Gz:
    """The .gz copy of one part, compressed by its own thread (zlib lets go of the interpreter lock while it compresses)."""

    def __init__(self, path, level):
        self.q, self.buf, self.err = queue.Queue(16), [], None
        self.t = threading.Thread(target=self._run, args=(path, level), daemon=True)
        self.t.start()

    def _run(self, path, level):
        try:
            c = zlib.compressobj(level, zlib.DEFLATED, 31)      # 31: a gzip header (time 0, so equal input gives equal bytes) and trailer
            with open(path, "wb") as f:
                while (chunk := self.q.get()) is not None:
                    f.write(c.compress(chunk))
                    f.write(c.flush(zlib.Z_FULL_FLUSH))
                f.write(c.flush())
        except BaseException as ex:                             # a full disk: keep taking chunks so the writer never waits forever
            self.err = ex
            while self.q.get() is not None: pass

    def add(self, data, cut):
        self.buf.append(data)
        if cut:
            self.q.put(b"".join(self.buf)); self.buf = []

    def close(self):
        if self.buf: self.q.put(b"".join(self.buf))
        self.q.put(None)
        self.t.join()
        if self.err: raise self.err


def write(out, jobs, b, part=PART, level=LEVEL):
    """Writes the parts, their .gz copies, jobs.xml and index.xml into the folder out. jobs: in the order of the feed (the site's own
    order, newest first). b: the build module. Returns the counts: jobs written, parts as (name, jobs, bytes, gzip bytes), and why
    open jobs were left out."""
    out = Path(out)
    out.mkdir(parents=True, exist_ok=True)
    for old in list(out.glob("jobs*.xml")) + list(out.glob("jobs*.xml.gz")): old.unlink()
    built = format_datetime(datetime.datetime.now(datetime.timezone.utc), usegmt=True)
    head = (f'<?xml version="1.0" encoding="UTF-8"?>\n<source>\n<publisher>{escape(b.SITE)}</publisher>\n<publisherurl>{escape(b.FULL)}/</publisherurl>\n'
            f"<lastBuildDate>{built}</lastBuildDate>\n").encode()
    parts, seen, left = [], set(), {"Telegram post": 0, "talent pool": 0, "no full description": 0, "no country": 0, "same page as another job": 0}
    state, places, stopped = {"f": None, "gz": None, "n": 0}, {}, ""

    def close():
        state["f"].write(b"</source>\n"); state["f"].close()
        state["gz"].add(b"</source>\n", True); state["gz"].close()
        name = f"jobs-{len(parts) + 1}.xml"
        parts.append((name, state["n"], (out / name).stat().st_size, (out / (name + ".gz")).stat().st_size))
        state.update(f=None, gz=None, n=0)

    def open_():
        name = f"jobs-{len(parts) + 1}.xml"
        state["f"], state["gz"] = open(out / name, "wb"), _Gz(out / (name + ".gz"), level)
        state["f"].write(head); state["gz"].add(head, False)

    try:
        for j in jobs:
            if not j.get("active"): continue
            why = ("Telegram post" if j.get("tg") else "talent pool" if j.get("pool") else "same page as another job" if j["slug"] in seen else "")
            full = "" if why else b.page_desc(j)
            if not why and not full: why = "no full description"
            if not why:
                loc = j.get("location") or ""
                addr = places[loc] if loc in places else places.setdefault(loc, place(j, b))      # many jobs share a place line
            else:
                addr = None
            if not why and not addr: why = "no country"
            if why:
                left[why] += 1; continue
            seen.add(j["slug"])
            if state["f"] is not None and state["n"] >= part:
                close()
                if shutil.disk_usage(out).free < MIN_FREE:     # a full disk stops the whole build: the feed stops short instead
                    stopped = f"stopped after {len(parts)} files: less than {MIN_FREE >> 30} GB free on the disk"
                    break
            if state["f"] is None: open_()
            data = item(j, b, full, addr).encode("utf-8")
            state["f"].write(data)
            state["gz"].add(data, zlib.crc32(j["id"].encode()) % CUT == 0)
            state["n"] += 1
        if not parts and state["f"] is None: open_()      # no job at all: an empty part, so jobs.xml still answers
        if state["f"] is not None: close()
    finally:
        if state["f"] is not None:                 # an error halfway: no thread is left waiting
            state["f"].close(); state["gz"].close()
    for ext in (".xml", ".xml.gz"):                # jobs.xml is part 1 itself: one file on disk, two addresses
        try: os.link(out / ("jobs-1" + ext), out / ("jobs" + ext))
        except OSError: shutil.copyfile(out / ("jobs-1" + ext), out / ("jobs" + ext))
    total = sum(p[1] for p in parts)
    (out / "index.xml").write_text(
        f'<?xml version="1.0" encoding="UTF-8"?>\n<feeds>\n<publisher>{escape(b.SITE)}</publisher>\n<publisherurl>{escape(b.FULL)}/</publisherurl>\n'
        f"<lastBuildDate>{built}</lastBuildDate>\n<jobs>{total}</jobs>\n"
        + "".join(f"<feed><url>{escape(b.FULL)}/feeds/{nm}</url><gzip>{escape(b.FULL)}/feeds/{nm}.gz</gzip><jobs>{k}</jobs><bytes>{sz}</bytes><gzipbytes>{gz}</gzipbytes></feed>\n"
                  for nm, k, sz, gz in parts) + "</feeds>\n", encoding="utf-8")
    return {"jobs": total, "parts": parts, "left": left, "stopped": stopped}


def _same_bytes(a, c):
    """Whether two files hold the same bytes, read a piece at a time."""
    with open(a, "rb") as fa, open(c, "rb") as fc:
        while True:
            x, y = fa.read(1 << 20), fc.read(1 << 20)
            if x != y: return False
            if not x: return True


def _check_part(args):
    """One part: (problems, its reference numbers, its number of jobs). Runs in a process of its own when there are several parts."""
    path, want, full_url = args
    path, bad, ids, n, name = Path(path), [], [], 0, Path(path).name
    try:
        root = None
        for ev, el in ET.iterparse(path, events=("start", "end")):
            if root is None: root = el
            if ev != "end" or el.tag != "job": continue
            n += 1
            kids = {c.tag: (c.text or "") for c in el}
            where = f"{name}, job {n}"
            miss = [k for k in REQUIRED if not kids.get(k, "").strip()]
            if miss: bad.append(f"{where}: missing {', '.join(miss)}")
            if any(not v.strip() for v in kids.values()): bad.append(f"{where}: an empty field")
            if any(BAD.search(v) for v in kids.values()): bad.append(f"{where}: a control character")
            if not ISO_TIME.match(kids.get("date", "")): bad.append(f"{where}: date {kids.get('date')!r}")
            if not re.fullmatch(r"[A-Z]{2}", kids.get("country", "")): bad.append(f"{where}: country {kids.get('country')!r}")
            for k in ("expirationdate", "updated"):
                if k in kids and not ISO_DAY.match(kids[k]): bad.append(f"{where}: {k} {kids[k]!r}")
            if full_url and not kids.get("url", "").startswith(full_url + "/job/"): bad.append(f"{where}: url {kids.get('url')!r}")
            if re.search(r"<(?:script|style|iframe)\b", kids.get("description", ""), re.I): bad.append(f"{where}: script or style in the description")
            ids.append(kids.get("referencenumber"))
            root.clear()                             # the jobs read so far: nothing stays in memory
            if len(bad) > 50: return bad, ids, n
        if root is None or root.tag != "source": bad.append(f"{name}: the root is not <source>")
    except (OSError, ET.ParseError) as ex:
        return bad + [f"{name}: {ex}"], ids, n
    if str(n) != want: bad.append(f"{name}: {n} jobs, index.xml says {want}")
    if n > PART: bad.append(f"{name}: {n} jobs, more than {PART}")
    try:                                             # the .gz copy: unpacked piece by piece and compared with the plain file
        d = zlib.decompressobj(31)
        with open(path, "rb") as fp, open(path.with_name(name + ".gz"), "rb") as fz:
            same = True
            while same and (chunk := fz.read(1 << 20)):
                got = d.decompress(chunk)
                same = fp.read(len(got)) == got
            got = d.flush()
            same = same and d.eof and fp.read(len(got)) == got and fp.read(1) == b""
        if not same: bad.append(f"{name}.gz does not unpack to {name}")
    except (OSError, zlib.error) as ex:
        bad.append(f"{name}.gz: {ex}")
    return bad, ids, n


def check(out, full_url=None, workers=4):
    """Reads every part named in index.xml back with a streaming parser and returns a list of problems (empty: all is well): the file
    is well-formed, each job has the required fields in their formats, no value holds a control character, numbers are unique, the
    count matches the index, the .gz copy unpacks to the same bytes, and jobs.xml is part 1. The parts are read side by side in
    `workers` processes (the runner has four processors; one process reads about 60 MB a second)."""
    out, bad = Path(out), []
    try:
        idx = ET.parse(out / "index.xml").getroot()
    except (OSError, ET.ParseError) as ex:
        return [f"index.xml: {ex}"]
    feeds = idx.findall("feed")
    if not feeds: bad.append("index.xml lists no part")
    tasks = []
    for fd in feeds:
        name = (fd.findtext("url") or "").rsplit("/", 1)[-1]
        if full_url and fd.findtext("url") != f"{full_url}/feeds/{name}": bad.append(f"index.xml: unexpected address {fd.findtext('url')}")
        tasks.append((str(out / name), fd.findtext("jobs"), full_url))
    results = None
    if workers > 1 and len(tasks) > 1:
        try:                                         # fork: check.py has no main guard, a fresh interpreter would run it again
            import multiprocessing
            from concurrent.futures import ProcessPoolExecutor
            with ProcessPoolExecutor(min(workers, len(tasks)), mp_context=multiprocessing.get_context("fork")) as ex:
                results = list(ex.map(_check_part, tasks))
        except Exception:                            # no fork here, or a worker died: read them one after another
            results = None
    if results is None: results = [_check_part(t) for t in tasks]
    seen, n_all = set(), 0
    for bad_, ids_, n in results:
        bad += bad_
        n_all += n
        for rid in ids_:
            if rid in seen: bad.append(f"referencenumber {rid} twice")
            seen.add(rid)
    if str(n_all) != idx.findtext("jobs"): bad.append(f"index.xml: {idx.findtext('jobs')} jobs, the parts hold {n_all}")
    for ext in (".xml", ".xml.gz"):
        a, c = out / ("jobs" + ext), out / ("jobs-1" + ext)
        if not a.is_file() or not c.is_file() or not (os.path.samefile(a, c) or _same_bytes(a, c)):
            bad.append(f"jobs{ext} is not jobs-1{ext}")
    return bad


def test():
    """Made-up jobs through write() and check(), with the cases that break feeds: "]]>", control characters, a lone surrogate, the
    jobs that must stay out, and a part limit of 2 so that the parts and the index are tested too."""
    import tempfile
    sys.path.insert(0, str(Path(__file__).parent))
    import build as b
    base = dict(active=True, company="Example Co", remote=False, hybrid=False, salary="", etype="", years=0, cat=b.OTHER[0], posted="2026-11-20",
                first_seen="2026-11-20", last_seen="2026-11-25", level="", title="Engineer")
    desc = "<p>Build things.</p><ul><li>Python</li></ul>"
    jobs = [dict(base, id="t-1", slug="a", location="Austin, TX", desc="<p>Text with ]]> inside and a\x0bcontrol\x85char\ud800.</p>", title="Data ]]> Engineer",
                 posted_at="2026-11-20T09:05:52Z", etype="Full-time", salary="$100K - $120K", years=3, remote=True),
            dict(base, id="t-2", slug="b", location="Minneapolis, MN, 55401", desc=desc, hybrid=True),
            dict(base, id="t-3", slug="c", location="Bengaluru, Karnataka, India", desc=desc),
            dict(base, id="t-4", slug="d", location="Remote - US", desc="<p>Job type: Part-time. Work from home.</p>"),
            dict(base, id="t-5", slug="e", location="Berlin, Germany", desc=desc, tg="somechannel"),
            dict(base, id="t-6", slug="f", location="Berlin, Germany", desc=desc, pool=True),
            dict(base, id="t-7", slug="g", location="Berlin, Germany", desc=""),
            dict(base, id="t-8", slug="h", location="Remote", desc=desc),
            dict(base, id="t-9", slug="a", location="Paris, France", desc=desc),
            dict(base, id="t-10", slug="i", location="Paris, France", desc="<p>x</p><script>alert(1)</script>"),
            dict(base, id="t-11", slug="j", location="London, UK", desc=desc, active=False)]
    ok = True
    with tempfile.TemporaryDirectory() as d:
        got = write(Path(d), jobs, b, part=2)
        problems = check(Path(d), b.FULL)
        for p in problems: print("  problem:", p)
        ok &= not problems
        ok &= got["jobs"] == 4 and [p[1] for p in got["parts"]] == [2, 2]
        ok &= got["left"] == {"Telegram post": 1, "talent pool": 1, "no full description": 2, "no country": 1, "same page as another job": 1}
        rows = [{c.tag: c.text for c in el} for k in (1, 2) for el in ET.parse(Path(d) / f"jobs-{k}.xml").getroot().iter("job")]
        a, mn, bl, rem = rows
        ok &= a["title"] == "Data ]]> Engineer" and a["description"] == "<p>Text with ]]> inside and a control char .</p>"
        ok &= (a["date"], a["city"], a["state"], a["country"], a["jobtype"], a["salary"], a["experience"], a["remotetype"], a["updated"]) == \
              ("2026-11-20T09:05:52Z", "Austin", "TX", "US", "fulltime", "$100K - $120K", "3+ years", "Fully remote", "2026-11-25")
        ok &= (mn["city"], mn["state"], mn["postalcode"], mn["remotetype"], mn["date"], mn["expirationdate"]) == ("Minneapolis", "MN", "55401", "Hybrid remote", "2026-11-20T00:00:00Z", b.VALID_TO)
        ok &= (bl["city"], bl["state"], bl["country"]) == ("Bengaluru", "Karnataka", "IN") and "category" not in bl and "salary" not in bl
        ok &= (rem.get("city"), rem["country"], rem["jobtype"]) == (None, "US", "parttime")
        ok &= (Path(d) / "jobs.xml").read_bytes() == (Path(d) / "jobs-1.xml").read_bytes()
        idx = ET.parse(Path(d) / "index.xml").getroot()
        ok &= [f.findtext("url") for f in idx.iter("feed")] == [f"{b.FULL}/feeds/jobs-1.xml", f"{b.FULL}/feeds/jobs-2.xml"]
        # too little room on the disk: the feed stops after a whole file, and what is written is still a valid feed
        global MIN_FREE
        keep, MIN_FREE = MIN_FREE, 1 << 62
        try:
            low = write(Path(d), jobs, b, part=2)
        finally:
            MIN_FREE = keep
        ok &= low["jobs"] == 2 and len(low["parts"]) == 1 and low["stopped"].startswith("stopped after 1 files") and not check(Path(d), b.FULL)
        write(Path(d), jobs, b, part=2)
        # a broken copy is noticed
        (Path(d) / "jobs-2.xml.gz").write_bytes(zlib.compress(b"x"))
        ok &= any("jobs-2.xml.gz" in p for p in check(Path(d), b.FULL))
        # a gzip group compresses to the same bytes wherever it stands (what keeps the uploads small)
        co1, co2 = zlib.compressobj(LEVEL, zlib.DEFLATED, 31), zlib.compressobj(LEVEL, zlib.DEFLATED, 31)
        co1.compress(b"first group " * 50); co1.flush(zlib.Z_FULL_FLUSH)
        co2.compress(b"another, longer first group " * 80); co2.flush(zlib.Z_FULL_FLUSH)
        same = b"<job>the same group of jobs</job>" * 40
        ok &= (co1.compress(same) + co1.flush(zlib.Z_FULL_FLUSH)) == (co2.compress(same) + co2.flush(zlib.Z_FULL_FLUSH))
    print("job_feed: test passed" if ok else "job_feed: TEST FAILED")
    return 0 if ok else 1


if __name__ == "__main__":
    if sys.argv[1:2] == ["--test"]:
        sys.exit(test())
    if sys.argv[1:2]:
        problems = check(Path(sys.argv[1]))
        for p in problems[:50]: print(p)
        print("job feed: OK" if not problems else f"job feed: {len(problems)} problems")
        sys.exit(1 if problems else 0)
    print(__doc__)
