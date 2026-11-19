import json, subprocess

UA = "Mozilla/5.0 (job-board aggregator)"


def get_text(url, timeout=30, accept="application/json", data=None, compressed=False):
    """Fetch a URL with curl and return the body as text, or None on any failure (a network error or an HTTP error status).
    With data (a dict) the request is a POST of that JSON, the way Workday's job lists are asked for. compressed asks for a gzip
    answer (HTML pages: about a quarter of the bytes for both sides)."""
    cmd = ["curl", "-s", "-4", "-L", "--fail", "--max-time", str(timeout), "-H", f"Accept: {accept}", "-A", UA]
    if compressed: cmd.append("--compressed")
    if data is not None: cmd += ["-H", "Content-Type: application/json", "--data-binary", json.dumps(data)]
    try:
        r = subprocess.run(cmd + [url], capture_output=True, timeout=timeout + 5)
        return r.stdout.decode("utf-8", "replace") if r.returncode == 0 else None
    except Exception:
        return None


def get_bytes(url, timeout=30):
    """Fetch a URL with curl and return the body as bytes (a picture), or None on any failure."""
    try:
        r = subprocess.run(["curl", "-s", "-4", "-L", "--fail", "--max-time", str(timeout), "--max-filesize", "700000", "-A", UA, url], capture_output=True, timeout=timeout + 5)
        return r.stdout if r.returncode == 0 and r.stdout else None
    except Exception:
        return None


def get_json(url, timeout=30):
    """Fetch a URL with curl and return parsed JSON, or None on any failure."""
    try:
        out = subprocess.run(
            ["curl", "-s", "-4", "-L", "--max-time", str(timeout), "-H", "Accept: application/json",
             "-A", UA, url],
            capture_output=True, timeout=timeout + 5,
        ).stdout
        return json.loads(out.decode("utf-8", "replace"))
    except Exception:
        return None


def post_json(url, data, timeout=30):
    """POST a JSON body and return the parsed JSON answer, or None on any failure."""
    try:
        return json.loads(get_text(url, timeout, data=data) or "")
    except Exception:
        return None
