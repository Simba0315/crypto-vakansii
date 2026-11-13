"""Post new jobs to the owner's own channels: Telegram and X.

Runs in the workflow after the site is deployed (the link in a post must open). It does nothing until the owner has
  1. created the channel and listed it in channels.json, and
  2. put the secret into the repository settings himself (nobody else handles his tokens):
     TELEGRAM_BOT_TOKEN                                 a bot made with @BotFather and added to the channel as an administrator
     X_API_KEY, X_API_SECRET, X_ACCESS_TOKEN, X_ACCESS_SECRET   an X developer app with read and write access
A channel with no secret is skipped with one line in the log; a failed post never fails the run.

What is posted: jobs the collector saw for the first time today, newest first, that pass the channel's filter, at most
"max_per_run" each time. data/posted.json remembers what went where, so nothing is posted twice; the workflow keeps that
file on the data branch next to the jobs database.

    python3 post.py --dry      print what would be posted, send nothing, change nothing
    python3 post.py --test     check the message builder and the request signing, no network
"""
import base64, datetime, hashlib, hmac, html, json, os, re, sys, time, urllib.parse, urllib.request
from pathlib import Path

ROOT = Path(__file__).parent
CFG = json.loads((ROOT / "config.json").read_text())
FULL = (CFG.get("base_url", "").rstrip("/") + CFG.get("base_path", "")).rstrip("/")
STATE = ROOT / "data" / "posted.json"
TODAY = datetime.date.today().isoformat()
KEEP_DAYS = 45            # how long an id stays in the state file; a job is only ever "new" on its first day


def passes(j, f):
    """A channel's filter: every key that is present must hold."""
    if f.get("remote") and not j.get("remote"): return False
    if f.get("crypto") and not j.get("crypto"): return False
    if f.get("cat") and j.get("cat") not in ([f["cat"]] if isinstance(f["cat"], str) else f["cat"]): return False
    if f.get("title") and not re.search(f["title"], j.get("title", ""), re.I): return False
    if f.get("min_usd") and not (j.get("usd") and j["usd"][1] >= f["min_usd"]): return False
    if f.get("entry") and not j.get("entry"): return False
    return True


def tags(j, limit=3):
    out = [re.sub(r"[^A-Za-z0-9]", "", t) for t in (j.get("tags") or [])[:limit]]
    return " ".join("#" + t for t in out if t and not t[0].isdigit())


def place(j):
    loc = (j.get("location") or "").strip()
    loc = loc if len(loc) <= 60 else loc[:57] + "…"
    return " · ".join(x for x in (loc, "Remote" if j.get("remote") and "remote" not in loc.lower() else "") if x)


def link(j):
    return f"{FULL}/job/{j['slug']}/"


def telegram_text(j):
    """HTML for sendMessage: title, employer and place, pay when stated, the link, up to three skill tags."""
    lines = [f"<b>{html.escape(j['title'])}</b>", html.escape(" · ".join(x for x in (j["company"], place(j)) if x))]
    if j.get("salary"): lines.append(html.escape(j["salary"]))
    lines.append(link(j))
    if tags(j): lines.append(tags(j))
    return "\n".join(lines)


def x_text(j, limit=280):
    """One post: a link counts as 23 characters on X whatever its length."""
    tail = "\n" + link(j)
    extra = " ".join(x for x in (j.get("salary") or "", tags(j, 2)) if x)
    head = f"{j['title']} at {j['company']}" + (f" · {place(j)}" if place(j) else "")
    room = limit - 24 - (len(extra) + 1 if extra else 0)
    if len(head) > room: head = head[:room - 1].rstrip() + "…"
    return head + ("\n" + extra if extra else "") + tail


def oauth1_header(method, url, params, key, secret, token, token_secret, nonce=None, stamp=None):
    """OAuth 1.0a header (HMAC-SHA1), as X requires for posting on behalf of an account. A JSON body is not part of the signature."""
    q = lambda s: urllib.parse.quote(str(s), safe="~")
    o = {"oauth_consumer_key": key, "oauth_nonce": nonce or base64.b16encode(os.urandom(16)).decode().lower(), "oauth_signature_method": "HMAC-SHA1",
         "oauth_timestamp": str(stamp or int(time.time())), "oauth_token": token, "oauth_version": "1.0"}
    allp = sorted((q(k), q(v)) for k, v in {**params, **o}.items())
    base = "&".join([method.upper(), q(url), q("&".join(f"{k}={v}" for k, v in allp))])
    sig = base64.b64encode(hmac.new(f"{q(secret)}&{q(token_secret)}".encode(), base.encode(), hashlib.sha1).digest()).decode()
    o["oauth_signature"] = sig
    return "OAuth " + ", ".join(f'{q(k)}="{q(v)}"' for k, v in sorted(o.items()))


def send(url, data=None, headers=None, body=None):
    req = urllib.request.Request(url, data=body if body is not None else urllib.parse.urlencode(data or {}).encode(), headers=headers or {}, method="POST")
    with urllib.request.urlopen(req, timeout=20) as r:
        return r.status, r.read().decode("utf-8", "replace")[:300]


POOL_RX = re.compile(r"talent (pool|community|network)|general (application|interest)|future (opportunit|opening)|expression of interest|don.t see|join our|open application", re.I)


def fresh(jobs):
    # a standing invitation to apply is not a job opening: it is never posted to a channel
    new = [j for j in jobs if j.get("active") and j.get("first_seen") == TODAY and not j.get("pool") and not POOL_RX.search(j.get("title", ""))]
    return sorted(new, key=lambda j: j.get("posted_at") or j.get("posted") or "", reverse=True)


def run(dry=False):
    cfg_file = ROOT / "channels.json"
    ch = json.loads(cfg_file.read_text()) if cfg_file.exists() else {}
    jobs = json.loads((ROOT / "data" / "jobs.json").read_text())
    jobs = jobs if isinstance(jobs, list) else list(jobs.values())
    state = json.loads(STATE.read_text()) if STATE.exists() else {}
    cut = (datetime.date.today() - datetime.timedelta(days=KEEP_DAYS)).isoformat()
    new, sent = fresh(jobs), 0
    tg_token = os.environ.get("TELEGRAM_BOT_TOKEN", "")
    for c in ch.get("telegram", []):
        chat, done = c["chat"], state.setdefault("tg:" + c["chat"], {})
        if not tg_token and not dry:
            print(f"telegram {chat}: no TELEGRAM_BOT_TOKEN in the repository secrets, skipped"); continue
        todo = [j for j in new if j["id"] not in done and passes(j, c.get("filter", {}))][:c.get("max_per_run", 10)]
        for j in todo:
            if dry: print(f"--- telegram {chat}\n{telegram_text(j)}\n"); continue
            try:
                send(f"https://api.telegram.org/bot{tg_token}/sendMessage", {"chat_id": chat, "text": telegram_text(j), "parse_mode": "HTML"})
                done[j["id"]] = TODAY; sent += 1
                time.sleep(3.2)                      # a bot may post about 20 messages a minute to one channel
            except Exception as ex:                  # a failed post must never stop the run or the others
                print(f"telegram {chat}: {type(ex).__name__} for {j['id']}"); break
        print(f"telegram {chat}: {len(todo)} {'to post' if dry else 'posted'}")
    xc = ch.get("x") or {}
    if xc.get("enabled"):
        keys = [os.environ.get(k, "") for k in ("X_API_KEY", "X_API_SECRET", "X_ACCESS_TOKEN", "X_ACCESS_SECRET")]
        done = state.setdefault("x", {})
        if not all(keys) and not dry:
            print("x: the four X_* secrets are not all set, skipped")
        else:
            todo = [j for j in new if j["id"] not in done and passes(j, xc.get("filter", {}))][:xc.get("max_per_run", 2)]
            for j in todo:
                if dry: print(f"--- x\n{x_text(j)}\n"); continue
                url = "https://api.twitter.com/2/tweets"
                try:
                    send(url, headers={"Authorization": oauth1_header("POST", url, {}, *keys), "Content-Type": "application/json"}, body=json.dumps({"text": x_text(j)}).encode())
                    done[j["id"]] = TODAY; sent += 1
                    time.sleep(5)
                except Exception as ex:
                    print(f"x: {type(ex).__name__} for {j['id']}"); break
            print(f"x: {len(todo)} {'to post' if dry else 'posted'}")
    if not dry:
        for k in state: state[k] = {i: d for i, d in state[k].items() if d >= cut}
        STATE.parent.mkdir(exist_ok=True)
        STATE.write_text(json.dumps(state, separators=(",", ":")))
    print(f"channels: {len(new)} new jobs today, {sent} posts sent")


def test():
    j = {"id": "x-1", "slug": "senior-data-analyst-example", "title": "Senior Data Analyst <Growth>", "company": "Example & Co", "location": "Berlin, Germany", "remote": True,
         "salary": "$120K - $150K", "tags": ["SQL", "Python", "dbt", "Looker"], "usd": [120000, 150000], "cat": "data-research", "active": True, "first_seen": TODAY}
    t = telegram_text(j)
    assert "<b>Senior Data Analyst &lt;Growth&gt;</b>" in t and "Example &amp; Co · Berlin, Germany · Remote" in t and "$120K - $150K" in t and t.count("\n") == 4, t
    assert "#SQL #Python #dbt" in t and link(j) in t
    long = dict(j, title="Principal Staff Senior Lead " * 12)
    x = x_text(long)
    assert len(x) - len(link(long)) + 23 <= 280 and x.endswith(link(long)) and "…" in x, len(x)
    assert passes(j, {"remote": True, "min_usd": 140000, "cat": ["data-research"], "title": "analyst"}) and not passes(j, {"min_usd": 200000}) and not passes(j, {"crypto": True})
    # the worked example from the OAuth 1.0a documentation of X (the "creating a signature" page)
    h = oauth1_header("POST", "https://api.twitter.com/1.1/statuses/update.json", {"include_entities": "true", "status": "Hello Ladies + Gentlemen, a signed OAuth request!"},
                      "xvz1evFS4wEEPTGEFPHBog", "kAcSOqF21Fu85e7zjz7ZN2U4ZRhfV3WpwPAoE3Z7kBw", "370773112-GmHxMAgYyLbNEtIKZeRNFsMKPR9EyMZeS9weJAEb", "LswwdoUaIvS8ltyTt5jkRh4J50vUPVVHtR2YPi5kE",
                      nonce="kYjzVBB8Y0ZFabxSWbWovY3uYSQ2pTgmZeNu2VS4cg", stamp=1318622958)
    assert 'oauth_signature="hCtSmYh%2BiHYCEqBWrE7C7hYmtUk%3D"' in h, h
    assert [x["id"] for x in fresh([j, dict(j, id="old", first_seen="2020-01-01"), dict(j, id="pool", pool=True)])] == ["x-1"]
    print("post.py: all checks passed")


if __name__ == "__main__":
    if "--test" in sys.argv: test()
    else: run(dry="--dry" in sys.argv)
