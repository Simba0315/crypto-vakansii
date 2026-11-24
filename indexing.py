"""Google's Indexing API for the job pages: tells Google about jobs new since the last run, so they reach Google Jobs sooner.

Why (owner, 20 Nov 2026, after adding the site to Search Console): Google reads the sitemaps on its own schedule; for job postings it
offers this API, the only pages besides live streams it accepts there. Its quota is 200 notifications a day by default, against
hundreds of thousands of open jobs, so each run sends the best few of the jobs it found new (PER_RUN), and stops at the first
"quota exceeded" answer. The sitemaps stay the way every other job reaches Google.

The key is a Google Cloud service account's JSON key, kept by the owner as the repository secret GOOGLE_INDEXING_KEY; that account is
an owner of the site in Search Console. Without the secret nothing is sent.

    python3 indexing.py --snapshot          before collecting: the ids of the open jobs (data/indexing_prev.txt)
    python3 indexing.py                     after the upload: notify Google of the best new jobs
    python3 indexing.py --dry-run           the same, printing the addresses instead of sending them
    python3 indexing.py --test              checks the signing and the choice on made-up data
    python3 indexing.py --check             with the key: is it right, and is the site ours in Search Console (nothing is sent)
"""
import base64, json, os, subprocess, sys, tempfile, time, urllib.error, urllib.parse, urllib.request
from pathlib import Path
import jobsdb

ROOT = Path(__file__).parent
JOBS = ROOT / "data" / "jobs.json"
PREV = ROOT / "data" / "indexing_prev.txt"
SITE = json.loads((ROOT / "config.json").read_text()).get("base_url", "https://jobseveryhour.com").rstrip("/")
PER_RUN = int(os.environ.get("HRN_INDEXING_PER_RUN") or 20)     # about ten collecting runs a day: 200, Google's daily default
SCOPE = "https://www.googleapis.com/auth/indexing"
TOKEN_URL = "https://oauth2.googleapis.com/token"
PUBLISH = "https://indexing.googleapis.com/v3/urlNotifications:publish"


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


def eligible(j):
    """A job whose page carries Google's job markup, in the main: open, with its full text and a place (build.job_page's rule)."""
    return j.get("active") and not j.get("tg") and bool(j.get("desc")) and bool(j.get("location"))


def rank(j):
    """Best first: a stated salary, then an exact posting time, then the newest."""
    return (bool(j.get("salary")), bool(j.get("posted_at")), j.get("posted_at") or j.get("posted") or "", j.get("first_seen") or "")


def choose(jobs, prev, n=PER_RUN):
    """The best n new jobs, one per company and title (a role posted in five cities is one notification)."""
    out, seen = [], set()
    for j in sorted((j for j in jobs if j.get("id") not in prev and eligible(j)), key=rank, reverse=True):
        k = (j.get("company"), (j.get("title") or "").lower())
        if k in seen: continue
        seen.add(k); out.append(j)
        if len(out) >= n: break
    return out


def load():
    db = jobsdb.load(JOBS)                         # one record at a time, see jobsdb.py
    return list(db.values()) if isinstance(db, dict) else db


def main(argv):
    if argv[:1] == ["--snapshot"]:
        if JOBS.exists(): PREV.write_text("\n".join(j["id"] for j in load() if j.get("active")))
        print(f"indexing: {sum(1 for _ in PREV.open()) if PREV.exists() else 0:,} open jobs noted before collecting")
        return 0
    if argv[:1] == ["--test"]: return test()
    if argv[:1] == ["--check"]: return check()
    raw = os.environ.get("GOOGLE_INDEXING_KEY", "").strip()
    if not raw and "--dry-run" not in argv:
        print("indexing: no GOOGLE_INDEXING_KEY secret, nothing sent"); return 0
    if not PREV.exists():
        print("indexing: no snapshot from before collecting (a run that did not collect), nothing new to send"); return 0
    prev = set(PREV.read_text().split())
    pick = choose(load(), prev)
    urls = [f"{SITE}/job/{j['slug']}/" for j in pick]
    if "--dry-run" in argv:
        print("\n".join(urls)); return 0
    key = json.loads(raw)
    bearer, sent = token(key), 0
    for u in urls:
        req = urllib.request.Request(PUBLISH, data=json.dumps({"url": u, "type": "URL_UPDATED"}).encode(),
                                     headers={"Authorization": f"Bearer {bearer}", "Content-Type": "application/json"})
        try:
            with urllib.request.urlopen(req, timeout=30): sent += 1
        except urllib.error.HTTPError as e:
            if e.code == 429: print("indexing: Google's daily quota is used up, the rest wait for tomorrow's runs"); break
            print(f"indexing: {u} answered {e.code}: {e.read()[:200]!r}")
            if e.code in (401, 403): break          # the key or the Search Console permission is wrong: the next ones would fail too
    print(f"indexing: {sent} of {len(urls)} new jobs sent to Google ({len(prev):,} were open before this run)")
    return 0


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
    assert [j["id"] for j in choose(jobs, {"d"}, 5)] == ["a", "f", "b"], [j["id"] for j in choose(jobs, {"d"}, 5)]
    print("indexing.py: all checks passed")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
