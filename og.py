"""Draws assets/og.jpg, the 1200x630 picture shown when a page of the site is shared.

Run `python3 og.py` (on a Mac with Google Chrome, or on the cloud machine with its Chromium) after a change of palette or wording: it writes a small HTML page that uses
the site's own fonts, photographs it with headless Chrome and saves the result as a JPEG. The daily build does not run this;
the picture is a committed file. No figures that change daily are drawn: social networks cache the picture for a long time.
"""
import subprocess, sys, tempfile
import brand
from pathlib import Path

ROOT = Path(__file__).parent
CHROMES = ["/Applications/Google Chrome.app/Contents/MacOS/Google Chrome", "/opt/pw-browsers/chromium-1243/chrome-linux64/chrome"]   # a Mac, or the cloud machine
ROWS = [("Senior Backend Engineer", "Remote · United States"), ("Product Designer", "London"), ("Data Engineer", "New York"), ("Security Analyst", "Berlin")]

HTML = """<!doctype html><html><head><meta charset="utf-8"><style>
@font-face{font-family:S;font-weight:400 900;src:url(FONTS/schibsted-latin.woff2) format("woff2")}
@font-face{font-family:P;font-weight:100 900;src:url(FONTS/publicsans-latin.woff2) format("woff2")}
*{box-sizing:border-box;margin:0}
body{width:1200px;height:630px;background:#ffffff;color:#121110;font-family:P,sans-serif;overflow:hidden;position:relative;-webkit-font-smoothing:antialiased;font-variant-numeric:tabular-nums}
.logo{position:absolute;left:64px;top:52px;display:flex;align-items:center;gap:14px;font:800 34px/1 S;letter-spacing:-.02em}
.logo svg{width:44px;height:44px}
h1{position:absolute;left:62px;top:150px;font:800 90px/.98 S;letter-spacing:-.035em;width:580px}
h1 span{background:linear-gradient(transparent 64%,#b7eec3 64%);padding:0 .06em}
p{position:absolute;left:64px;top:470px;font-size:26px;line-height:1.5;color:#5c5852;width:580px}
.board{position:absolute;left:650px;top:128px;width:486px;background:#121110;color:#f4f1ec;border-radius:16px;padding:22px 28px 14px}
.bh{font:600 20px P;color:#aca69c;padding-bottom:16px;border-bottom:1px solid #2a2723;display:flex;align-items:center;gap:10px}
.bh i{width:10px;height:10px;border-radius:50%;background:#5fd486}
.r{display:grid;grid-template-columns:78px 1fr;gap:6px;padding:15px 0;border-bottom:1px solid #24211e}
.r:last-child{border-bottom:0}
.r i{font:700 16px P;font-style:normal;color:#5fd486;padding-top:5px}
.r b{display:block;font:650 24px/1.2 P}
.r span{display:block;font:500 16px P;color:#aca69c;margin-top:4px}
hr{position:absolute;left:64px;right:64px;bottom:34px;border:0;border-top:2px solid #ebe8e3}
</style></head><body>
<div class="logo">MARK SITENAME</div>
<h1>Jobs that are <span>still open</span></h1>
<p>Read every hour from employers’ own pages.<br>A job the employer takes down leaves the list.</p>
<div class="board"><div class="bh"><i></i>Just posted</div>ROWS</div><hr>
</body></html>"""


SQUARE = """<!doctype html><html><head><meta charset="utf-8"><style>
@font-face{font-family:S;font-weight:400 900;src:url(FONTS/schibsted-latin.woff2) format("woff2")}
@font-face{font-family:P;font-weight:100 900;src:url(FONTS/publicsans-latin.woff2) format("woff2")}
*{box-sizing:border-box;margin:0}
body{width:1080px;height:1080px;background:#ffffff;color:#121110;font-family:P,sans-serif;overflow:hidden;position:relative;-webkit-font-smoothing:antialiased}
.logo{position:absolute;left:96px;top:100px;display:flex;align-items:center;gap:22px;font:800 56px/1 S;letter-spacing:-.02em}
.logo svg{width:72px;height:72px}
h1{position:absolute;left:92px;top:390px;font:800 150px/.98 S;letter-spacing:-.04em;width:900px}
h1 span{background:linear-gradient(transparent 62%,#b7eec3 62%);padding:0 .04em}
p{position:absolute;left:96px;top:880px;font-size:34px;line-height:1.4;color:#5c5852;width:820px}
</style></head><body>
<div class="logo">MARK SITENAME</div>
<h1>Jobs that are <span>still open</span></h1>
<p>From employers’ own careers pages. Free, no account. jobseveryhour.com</p>
</body></html>"""


FONTCSS = """@font-face{font-family:S;font-weight:400 900;src:url(FONTS/schibsted-latin.woff2) format("woff2")}
@font-face{font-family:P;font-weight:100 900;src:url(FONTS/publicsans-latin.woff2) format("woff2")}
*{box-sizing:border-box;margin:0}"""
XCOVER = """<!doctype html><html><head><meta charset="utf-8"><style>""" + FONTCSS + """
body{width:1500px;height:500px;background:#ffffff;color:#121110;font-family:P,sans-serif;overflow:hidden;position:relative;-webkit-font-smoothing:antialiased}
h1{position:absolute;left:96px;top:150px;font:800 84px/1 S;letter-spacing:-.035em}
h1 span{background:linear-gradient(transparent 62%,TINT 62%);padding:0 .04em}
p{position:absolute;left:98px;top:258px;font-size:28px;color:#5c5852}
.big{position:absolute;left:1040px;top:-40px;width:520px;height:520px}
</style></head><body><h1>Jobs that are <span>still open</span></h1><p>Read from employers’ own careers pages. Free, no account.</p>
<svg class="big" viewBox="0 0 32 32">BIGMARK</svg></body></html>"""
LICOVER = """<!doctype html><html><head><meta charset="utf-8"><style>""" + FONTCSS + """
body{width:1584px;height:396px;background:#121110;color:#f4f1ec;font-family:P,sans-serif;overflow:hidden;position:relative;-webkit-font-smoothing:antialiased}
h1{position:absolute;left:440px;top:100px;font:800 62px/1 S;letter-spacing:-.035em}
p{position:absolute;left:442px;top:186px;font-size:26px;color:#aca69c}
.big{position:absolute;left:1344px;top:118px;width:160px;height:160px}
</style></head><body><h1>Jobs that are still open</h1><p>Read from employers’ own careers pages · jobseveryhour.com</p>
<svg class="big" viewBox="0 0 32 32">DARKMARK</svg></body></html>"""


def shoot(html, w, h, out, jpeg=True):
    """Photographs one HTML page with headless Chrome at w×h and saves it to out (JPEG or PNG)."""
    with tempfile.TemporaryDirectory() as tmp:
        page, shot = Path(tmp) / "p.html", Path(tmp) / "p.png"
        mark = f'<svg viewBox="0 0 32 32">{brand.mark(brand.APPLIED, brand.DIRECTIONS[brand.APPLIED]["mark"], "#FFFFFF")}</svg>'
        d = brand.DIRECTIONS[brand.APPLIED]
        html = (html.replace("BIGMARK", brand.mark(brand.APPLIED, d["mark"], "#FFFFFF")).replace("DARKMARK", brand.mark(brand.APPLIED, d["ui_dark"], d["dark_bg"]))
                .replace("TINT", d["tint"]))
        page.write_text(html.replace("FONTS", (ROOT / "assets" / "fonts").as_uri()).replace("MARK", mark).replace("SITENAME", brand.NAME), encoding="utf8")
        subprocess.run([CHROMES[0], "--headless=new", "--disable-gpu", "--hide-scrollbars", "--force-device-scale-factor=1", f"--user-data-dir={tmp}/profile",
                        f"--window-size={w},{h}", "--virtual-time-budget=4000", f"--screenshot={shot}", page.as_uri()], check=True, capture_output=True, timeout=90)
        if jpeg: subprocess.run(["sips", "-s", "format", "jpeg", "-s", "formatOptions", "86", str(shot), "--out", str(out)], check=True, capture_output=True)
        else: Path(out).write_bytes(shot.read_bytes())


def main():
    rows = "".join(f'<div class="r"><i>Today</i><div><b>{t}</b><span>{p}</span></div></div>' for t, p in ROWS)
    with tempfile.TemporaryDirectory() as tmp:
        page, shot = Path(tmp) / "og.html", Path(tmp) / "og.png"
        mark = f'<svg viewBox="0 0 32 32">{brand.mark(brand.APPLIED, brand.DIRECTIONS[brand.APPLIED]["mark"], "#FFFFFF")}</svg>'
        page.write_text(HTML.replace("FONTS", (ROOT / "assets" / "fonts").as_uri()).replace("ROWS", rows).replace("MARK", mark).replace("SITENAME", brand.NAME), encoding="utf8")
        if not Path(CHROMES[0]).exists():                      # the cloud machine: Playwright's Chromium, driven from Node
            js = ("const{chromium}=require('playwright');(async()=>{const b=await chromium.launch();const p=await b.newPage({viewport:{width:1200,height:630}});"
                  f"await p.goto('{page.as_uri()}',{{waitUntil:'networkidle'}});await p.screenshot({{path:'{shot}'}});await b.close();}})();")
            subprocess.run(["node", "-e", js], check=True, capture_output=True, timeout=90)
        else: subprocess.run([CHROMES[0], "--headless=new", "--disable-gpu", "--hide-scrollbars", "--force-device-scale-factor=1", f"--user-data-dir={tmp}/profile",
                        "--window-size=1200,630", "--virtual-time-budget=4000", f"--screenshot={shot}", page.as_uri()], check=True, capture_output=True, timeout=90)
        if Path("/usr/bin/sips").exists():
            subprocess.run(["sips", "-s", "format", "jpeg", "-s", "formatOptions", "86", str(shot), "--out", str(ROOT / "assets" / "og.jpg")], check=True, capture_output=True)
        else:                                                   # elsewhere: Pillow
            from PIL import Image
            Image.open(shot).convert("RGB").save(ROOT / "assets" / "og.jpg", "JPEG", quality=86, optimize=True)
    print("assets/og.jpg written")


if __name__ == "__main__":
    if sys.argv[1:] == ["--banners"]:          # the three covers of the media kit, in the applied brand
        for tpl, w, h, name in ((SQUARE, 1080, 1080, "banner-square.png"), (XCOVER, 1500, 500, "banner-x.png"), (LICOVER, 1584, 396, "banner-linkedin.png")):
            shoot(tpl, w, h, ROOT / "assets" / "brand" / name, jpeg=False); print(f"assets/brand/{name} written")
    else:
        sys.exit(main())
