import json, multiprocessing, subprocess
from urllib.parse import urlsplit

# At most this many requests at once to one host. The hiring systems below serve thousands of small company boards from one
# address; 20 workers hitting it together is what gets a crawler rate-limited (Workable answers 429 to that). Hosts not listed:
# no limit beyond the worker pool.
PER_HOST = {"apply.workable.com": 4, "api.smartrecruiters.com": 8, "ats.rippling.com": 6, "opendata.trudvsem.ru": 4}
# made at import, before collect.py may fork worker processes (HRN_PROCS), so threads and processes share the same limits
_gates = {h: multiprocessing.BoundedSemaphore(n) for h, n in PER_HOST.items()}


def _gate(url):
    return _gates.get((urlsplit(url).hostname or "").lower())


def get_text(url, timeout=30, accept="application/json"):
    """Fetch a URL with curl and return the body as text, or None on any failure (network error, or an HTTP error status)."""
    gate = _gate(url)
    try:
        if gate: gate.acquire()
        res = subprocess.run(
            ["curl", "-s", "-4", "-L", "--fail", "--max-time", str(timeout), "-H", f"Accept: {accept}",
             "-A", "Mozilla/5.0 (job-board aggregator)", url],
            capture_output=True, timeout=timeout + 5,
        )
        return res.stdout.decode("utf-8", "replace") if res.returncode == 0 else None
    except Exception:
        return None
    finally:
        if gate: gate.release()


def get_json(url, timeout=30):
    """Fetch a URL with curl and return parsed JSON, or None on any failure."""
    gate = _gate(url)
    try:
        if gate: gate.acquire()
        out = subprocess.run(
            ["curl", "-s", "-4", "-L", "--max-time", str(timeout), "-H", "Accept: application/json",
             "-A", "Mozilla/5.0 (job-board aggregator)", url],
            capture_output=True, timeout=timeout + 5,
        ).stdout
        return json.loads(out.decode("utf-8", "replace"))
    except Exception:
        return None
    finally:
        if gate: gate.release()
