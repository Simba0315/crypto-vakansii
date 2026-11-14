"""The old address after the move: GitHub Pages keeps serving simba0315.github.io/crypto-vakansii/, but every page there now sends the
visitor (and search engines) to the same page on the new domain.

    python3 pages_redirect.py            reads site/ (built for the new domain), writes pages_site/ for the GitHub Pages deploy

GitHub Pages cannot answer with a real 301, so each old page is a tiny HTML page with a canonical link to the new address, an
immediate meta refresh (which Google treats as a permanent redirect) and a script for browsers. Any old address not in the list
(a job that closed long ago, an address with a query) gets the same treatment from 404.html. Files other sites may load from
the old address keep working there: the job widget scripts, the embed page and the JSON API.
"""
import html, json, os, shutil, sys
from pathlib import Path

ROOT = Path(__file__).parent
SITE, OUT = ROOT / "site", ROOT / "pages_site"
CFG = json.loads((ROOT / "config.json").read_text())
NEW = CFG["base_url"].rstrip("/") + CFG.get("base_path", "").rstrip("/")       # https://jobseveryhour.com
OLD_PATH = os.environ.get("HRN_OLD_PATH", "/crypto-vakansii")                  # where the site lived on github.io
KEEP = ["widget.js", "widgets.js", "embed", "api", "hiring-badge.svg", "favicon.svg"]   # loaded by other sites from the old address


def page(target):
    t = html.escape(target, quote=True)
    return (f'<!doctype html><html lang="en"><head><meta charset="utf-8"><title>Moved to {html.escape(NEW.split("//")[-1])}</title>'
            f'<link rel="canonical" href="{t}"><meta http-equiv="refresh" content="0; url={t}">'
            f'<script>location.replace({json.dumps(target)}+location.search+location.hash)</script></head>'
            f'<body><p>This page has moved to <a href="{t}">{t}</a>.</p></body></html>')


def paths():
    """Every address of the built site: the folders with an index.html, and the job pages named in the sitemaps (with job records
    they are not files)."""
    seen = {"" if p.parent == SITE else p.parent.relative_to(SITE).as_posix() for p in SITE.rglob("index.html")}
    for sm in (SITE / "sitemaps").glob("jobs-*.xml"):
        txt = sm.read_text(encoding="utf-8")
        for chunk in txt.split("<loc>")[1:]:
            u = chunk.split("</loc>", 1)[0]
            if u.startswith(NEW + "/"): seen.add(u[len(NEW) + 1:].rstrip("/"))
    return sorted(p.strip("/") for p in seen)


def main():
    if NEW.startswith("https://simba0315.github.io"): sys.exit("config.json still points at github.io: nothing to redirect")
    if OUT.exists(): shutil.rmtree(OUT)
    OUT.mkdir()
    ps = paths()
    for p in ps:
        d = OUT / p if p else OUT
        d.mkdir(parents=True, exist_ok=True)
        (d / "index.html").write_text(page(f"{NEW}/{p}/" if p else f"{NEW}/"), encoding="utf-8")
    # anything else under the old address: the same page on the new domain
    old_rx = OLD_PATH.replace("/", "\\/")
    (OUT / "404.html").write_text(
        '<!doctype html><html lang="en"><head><meta charset="utf-8"><title>Moved</title><meta name="robots" content="noindex">'
        f'<script>location.replace({json.dumps(NEW)}+location.pathname.replace(/^{old_rx}/,"")+location.search+location.hash)</script></head>'
        f'<body><p>This site has moved to <a href="{html.escape(NEW)}/">{html.escape(NEW.split("//")[-1])}</a>.</p></body></html>', encoding="utf-8")
    (OUT / "robots.txt").write_text("User-agent: *\nAllow: /\n", encoding="utf-8")       # crawlers must see the redirects to follow them
    (OUT / ".nojekyll").write_text("")
    for k in KEEP:
        src = SITE / k
        if src.is_dir(): shutil.copytree(src, OUT / k, dirs_exist_ok=True)
        elif src.is_file(): shutil.copy2(src, OUT / k)
    size = sum(f.stat().st_size for f in OUT.rglob("*") if f.is_file())
    print(f"{len(ps):,} old addresses now send visitors to {NEW}; pages_site/ is {size / 2**20:.0f} MiB")


if __name__ == "__main__":
    main()
