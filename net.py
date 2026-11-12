import json, subprocess

def get_json(url, timeout=30):
    """Fetch a URL with curl and return parsed JSON, or None on any failure."""
    try:
        out = subprocess.run(
            ["curl", "-s", "-4", "-L", "--max-time", str(timeout), "-H", "Accept: application/json",
             "-A", "Mozilla/5.0 (job-board aggregator)", url],
            capture_output=True, timeout=timeout + 5,
        ).stdout
        return json.loads(out.decode("utf-8", "replace"))
    except Exception:
        return None
