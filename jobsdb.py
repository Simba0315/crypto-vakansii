"""Reads data/jobs.json one record at a time instead of as one big string.

Why (24 Nov 2026): at 2.16 GB the database no longer fitted in the runner's memory when read the plain way. json.loads(path.read_text())
first makes the whole file one Python string, and a single emoji anywhere in it makes CPython store every character in 4 bytes, so a
2.16 GB file became an 8.6 GB string before a single job was parsed. From 23 Nov 12:50 UTC every hourly run died within half a minute
of starting ("The runner has received a shutdown signal") and the site stopped updating. Here each record is parsed from its own few
lines, so the peak is the parsed jobs alone.

The file is written by collect.save_db: "{", then for each record a newline, the key, ": " and json.dumps(record, indent=0), records
separated by a comma, then "\n}". indent=0 puts every value on its own line, so a record ends at the first line that closes the
depth it opened. A file in any other shape is read the plain way.

    python3 jobsdb.py --test        checks the reader against json.loads on made-up records
    python3 jobsdb.py data/jobs.json  reads a file both ways and says whether they agree (needs memory for both)
"""
import json, sys
from pathlib import Path


def _records(f):
    """(key, record) pairs from a file in save_db's shape; raises ValueError on anything else."""
    first = f.readline()
    if first.strip() == "{}":
        return
    if first.rstrip("\n") != "{":
        raise ValueError("not save_db's shape")
    depth, key, buf = 0, None, []
    for raw in f:
        line = raw.rstrip("\n")
        if depth == 0:
            if line == "}":
                return
            if line.startswith('"') and line.rstrip(",").endswith(": {}"):
                yield json.loads(line.rstrip(",")[:-4]), {}
                continue
            if not (line.startswith('"') and line.endswith(": {")):
                raise ValueError("unexpected line between records")
            key, buf, depth = json.loads(line[:-3]), ["{"], 1
            continue
        t = line.rstrip(",")
        if t in ("}", "]"):
            depth -= 1
            if depth == 0:
                buf.append("}")
                yield key, json.loads("\n".join(buf))
                buf = []
                continue
        elif t.endswith(("{", "[")):
            depth += 1
        buf.append(line)
    raise ValueError("file ends inside a record")


def load(path):
    """The database as a dict, in file order, as json.loads would give it."""
    path = Path(path)
    try:
        with open(path, encoding="utf-8") as f:
            return dict(_records(f))
    except ValueError:
        return json.loads(path.read_text(encoding="utf-8"))


def _write(db, path):
    """save_db's writer, repeated here so the test does not need collect.py."""
    with open(path, "w", encoding="utf-8") as f:
        f.write("{")
        for i, (k, v) in enumerate(db.items()):
            f.write(("," if i else "") + "\n" + json.dumps(k, ensure_ascii=False) + ": " + json.dumps(v, ensure_ascii=False, indent=0))
        f.write("\n}" if db else "}")


def test():
    import tempfile, os
    db = {
        "a-1": {"id": "a-1", "title": "Engineer {remote}", "desc": "line one\nline two 😀 ends with {", "tags": [], "meta": {},
                "salary": {"min": 1, "max": 2, "cur": "USD"}, "locs": ["NY", "SF"], "nested": [{"x": [1, [2, {}]]}, {}], "active": True},
        "a-2": {"id": "a-2", "title": "Ends with brace [", "list": ["}", "]", "{", "["], "n": None, "f": 1.5},
        'we"ird': {"id": 'we"ird', "k": "  sep", "deep": {"a": {"b": {"c": []}}}},
    }
    ok = True
    with tempfile.TemporaryDirectory() as d:
        for case in (db, {}, {"only": {}}):
            p = os.path.join(d, "jobs.json")
            _write(case, p)
            got, want = load(p), json.loads(Path(p).read_text(encoding="utf-8"))
            same = got == want and list(got) == list(want)
            ok &= same
            print(f"{len(case)} records: {'same' if same else 'DIFFERENT'}")
        p = os.path.join(d, "plain.json")
        Path(p).write_text(json.dumps(db, indent=2), encoding="utf-8")
        same = load(p) == db
        ok &= same
        print(f"other shape read the plain way: {'same' if same else 'DIFFERENT'}")
    print("jobsdb: test passed" if ok else "jobsdb: TEST FAILED")
    return 0 if ok else 1


if __name__ == "__main__":
    if sys.argv[1:2] == ["--test"]:
        sys.exit(test())
    if sys.argv[1:2]:
        a = load(sys.argv[1])
        b = json.loads(Path(sys.argv[1]).read_text(encoding="utf-8"))
        print(f"{len(a):,} records; {'same' if a == b and list(a) == list(b) else 'DIFFERENT'}")
        sys.exit(0 if a == b else 1)
    print(__doc__)
