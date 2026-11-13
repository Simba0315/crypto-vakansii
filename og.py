"""Draws assets/og.jpg, the 1200x630 picture shown when a page of the site is shared.

Run `python3 og.py` on a Mac with Google Chrome after a change of palette or wording: it writes a small HTML page that uses
the site's own fonts, photographs it with headless Chrome and saves the result as a JPEG. The daily build does not run this;
the picture is a committed file. No figures that change daily are drawn: social networks cache the picture for a long time.
"""
import subprocess, sys, tempfile
from pathlib import Path

ROOT = Path(__file__).parent
CHROME = "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome"
ROWS = [("Senior Backend Engineer", "Remote · United States"), ("Product Designer", "London"), ("Data Engineer", "New York"), ("Security Analyst", "Berlin")]

HTML = """<!doctype html><html><head><meta charset="utf-8"><style>
@font-face{font-family:B;font-weight:700 800;src:url(FONTS/bricolage-latin.woff2) format("woff2")}
@font-face{font-family:I;font-weight:400 700;src:url(FONTS/inter-latin.woff2) format("woff2")}
@font-face{font-family:M;font-weight:500 700;src:url(FONTS/jbmono-latin.woff2) format("woff2")}
*{box-sizing:border-box;margin:0}
body{width:1200px;height:630px;background:#f6f5f0;color:#0e0e0c;font-family:I,sans-serif;overflow:hidden;position:relative;-webkit-font-smoothing:antialiased}
.logo{position:absolute;left:64px;top:52px;display:flex;align-items:center;gap:14px;font:800 36px/1 B;letter-spacing:-.02em}
.logo i{width:18px;height:18px;border-radius:50%;background:#3ecf5f}
h1{position:absolute;left:62px;top:150px;font:800 92px/.98 B;letter-spacing:-.04em;width:560px}
h1 span{background:linear-gradient(transparent 62%,#b7eec3 62%);padding:0 .06em}
p{position:absolute;left:64px;top:446px;font-size:26px;line-height:1.5;color:#55534c;width:560px}
.board{position:absolute;left:650px;top:128px;width:486px;background:#0e0e0c;color:#f3f2ec;border-radius:10px;border-top:6px solid #7ee39a;padding:22px 28px 14px}
.bh{font:500 20px I;color:#a5a399;padding-bottom:16px;border-bottom:1px solid #2b2b27}
.r{display:grid;grid-template-columns:78px 1fr;gap:6px;padding:15px 0;border-bottom:1px solid #22221f}
.r:last-child{border-bottom:0}
.r i{font:500 16px M;font-style:normal;color:#7ee39a;padding-top:5px}
.r b{display:block;font:600 24px/1.2 I}
.r span{display:block;font:500 15.5px M;color:#a5a399;margin-top:4px}
hr{position:absolute;left:64px;right:64px;bottom:34px;border:0;border-top:2px solid #e2dfd5}
</style></head><body>
<div class="logo"><i></i>Hiring Right Now</div>
<h1>Tech jobs that are <span>still open</span></h1>
<p>Read every morning from company career pages.<br>Closed roles leave the list the same day.</p>
<div class="board"><div class="bh">Just posted</div>ROWS</div><hr>
</body></html>"""


def main():
    rows = "".join(f'<div class="r"><i>Today</i><div><b>{t}</b><span>{p}</span></div></div>' for t, p in ROWS)
    with tempfile.TemporaryDirectory() as tmp:
        page, shot = Path(tmp) / "og.html", Path(tmp) / "og.png"
        page.write_text(HTML.replace("FONTS", (ROOT / "assets" / "fonts").as_uri()).replace("ROWS", rows), encoding="utf8")
        subprocess.run([CHROME, "--headless=new", "--disable-gpu", "--hide-scrollbars", "--force-device-scale-factor=1", f"--user-data-dir={tmp}/profile",
                        "--window-size=1200,630", "--virtual-time-budget=4000", f"--screenshot={shot}", page.as_uri()], check=True, capture_output=True, timeout=90)
        subprocess.run(["sips", "-s", "format", "jpeg", "-s", "formatOptions", "86", str(shot), "--out", str(ROOT / "assets" / "og.jpg")], check=True, capture_output=True)
    print("assets/og.jpg written")


if __name__ == "__main__":
    sys.exit(main())
