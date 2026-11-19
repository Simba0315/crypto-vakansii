"""Checks on the plain lines in skills_info.py (run: python3 skills_info_test.py).

Each line must stand alone: it is shown under one skill's name, so it may not point at another line ("such packages"),
and it may not list the skill itself as an example of its own group ("such as OneStream and ..." on OneStream's page)."""
import re
import sys

import skills_info

bad = []
for name, (group, line) in skills_info.INFO.items():
    if re.search(r"\bsuch\b(?! as\b)", line):
        bad.append((name, "'such' without 'as' points at another line"))
    if re.search(r"\b(the above|the same as|\(see |see also)", line):
        bad.append((name, "points at another line"))
    if group != "spoken" and re.search(r"\bsuch as\b.*(?<![\w-])" + re.escape(name) + r"(?![\w-])", line):
        bad.append((name, "names itself in its own list of examples"))
    if line != line.strip() or line.endswith("."):
        bad.append((name, "no full stop at the end: plain() adds it"))
    if group not in {g for g, _, _ in skills_info.GROUPS}:
        bad.append((name, "unknown group " + group))
for n, why in bad:
    print(f"{n}: {why}")
print(f"{len(skills_info.INFO)} lines, {len(bad)} problems")
sys.exit(1 if bad else 0)
