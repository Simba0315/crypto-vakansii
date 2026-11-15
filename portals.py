"""Snapshots of the public employment portals, made once a day apart from the hourly run.

    python3 portals.py            # read every portal, write data/portals/<name>.json.gz for each one that answered
    python3 portals.py trudvsem   # one of them

Russia's file is 1.9 GB and Sweden's service needs about 150 calls, which would not fit in the hourly run's 20 minutes; so
.github/workflows/portals.yml runs this every day and keeps the snapshots on the one-commit branch "portals". The hourly run
restores them and collect.py reads them with load(): a few seconds. A portal that fails keeps yesterday's snapshot.
"""
import concurrent.futures as cf, datetime, gzip, json, sys
from pathlib import Path

import jobtech, trudvsem

ROOT = Path(__file__).parent
DIR = ROOT / "data" / "portals"
MODULES = {"trudvsem": trudvsem, "jobtech": jobtech}
STALE_DAYS = 4          # an older snapshot is not used: its jobs then stay exactly as they were, as for a feed that failed


def path(name):
    return DIR / f"{name}.json.gz"


def load(name):
    """The jobs of a portal's latest snapshot, or None when there is none or it is too old to trust."""
    f = path(name)
    if not f.exists(): return None
    try:
        snap = json.loads(gzip.decompress(f.read_bytes()))
        made = datetime.date.fromisoformat(snap["date"])
    except (OSError, ValueError, KeyError):
        return None
    if (datetime.date.today() - made).days > STALE_DAYS:
        print(f"{name}: snapshot of {made} is older than {STALE_DAYS} days, not used"); return None
    return snap["jobs"]


def main(names):
    DIR.mkdir(parents=True, exist_ok=True)
    with cf.ThreadPoolExecutor(len(names)) as ex:
        got = dict(zip(names, ex.map(lambda n: MODULES[n].fetch(), names)))
    bad = 0
    for n, jobs in got.items():
        if not jobs:
            print(f"{n}: no answer, yesterday's snapshot stays"); bad += 1; continue
        path(n).write_bytes(gzip.compress(json.dumps({"date": datetime.date.today().isoformat(), "source": MODULES[n].SOURCE, "jobs": jobs},
                                                     ensure_ascii=False, separators=(",", ":")).encode(), 9))
        print(f"{n}: {len(jobs):,} jobs from {len({j['company'] for j in jobs}):,} employers, {path(n).stat().st_size / 2**20:.1f} MiB")
    return bad


if __name__ == "__main__":
    sys.exit(1 if main(sys.argv[1:] or list(MODULES)) == len(sys.argv[1:] or MODULES) else 0)
