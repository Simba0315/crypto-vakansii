"""Checks that a job page built from its record is the page the static build wrote, byte for byte.

    HRN_RECORDS=both python3 build.py    # the records and the pages, from the same build
    python3 records_test.py              # every job; ends with "0 different"
    python3 records_test.py 500          # a random 500
"""
import random, sys, time
from pathlib import Path

ROOT = Path(__file__).parent
sys.path.insert(0, str(ROOT))
import build, records                    # noqa: E402

store = records.Store(ROOT / "data" / "jobs.db", build)       # as of the build, not as of now: the files were written then
slugs = sorted(store.slugs())
if len(sys.argv) > 1: slugs = random.Random(7).sample(slugs, min(int(sys.argv[1]), len(slugs)))
files = {p.parent.name for p in (build.OUT / "job").glob("*/index.html")}
t0, diff, missing, shown = time.time(), 0, 0, 0
for s in slugs:
    f = build.OUT / "job" / s / "index.html"
    if not f.is_file():
        missing += 1
        continue
    got, want = store.page(s), f.read_text(encoding="utf-8")
    if got != want:
        diff += 1
        if shown < 3:
            shown += 1
            i = next((k for k in range(min(len(got), len(want))) if got[k] != want[k]), min(len(got), len(want)))
            print(f"different: {s}\n  record: …{got[max(0, i - 80):i + 80]!r}\n  file:   …{want[max(0, i - 80):i + 80]!r}")
took = time.time() - t0
print(f"{len(slugs):,} job pages built from records in {took:.1f} s ({1000 * took / max(1, len(slugs)):.1f} ms each): "
      f"{diff} different, {missing} with no file, {len(files - set(store.slugs())) if len(sys.argv) == 1 else 0} files with no record")
sys.exit(1 if diff or missing else 0)
