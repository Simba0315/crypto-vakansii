"""The brand of Hiring Right Now (owner, 15 Nov 2026: "a corporate design of our own, like Indeed and other brands").

Three directions are defined here and shown side by side on /brand/directions/ (not indexed), so the owner can switch later;
the site uses the one marked "applied". Every logo file is drawn here: the letters of the wordmark are turned into outlines,
so the files look the same on a computer that does not have the font.

    python3 brand.py           writes assets/brand/*.svg (needs: pip install fonttools brotli)
    python3 brand.py --test    checks the colour contrast of every direction (no packages needed)

The build only copies assets/brand/ to the site; it does not need fonttools.
"""
import math
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent
OUT = ROOT / "assets" / "brand"
NAME = "Hiring Right Now"

FONTS = {   # family, file in assets/fonts (OFL-1.1, from Fontsource), weight used for headlines and the wordmark
    "schibsted": ("Schibsted Grotesk", "schibsted-latin.woff2", 800),
    "publicsans": ("Public Sans", "publicsans-latin.woff2", 800),
    "hanken": ("Hanken Grotesk", "hanken-latin.woff2", 800),
}

# mark: the colour of the mark and of large shapes; ui: buttons and link lines on light pages (white text on it passes 4.5:1);
# ui_dark: the same on dark pages, with dark text on it; ink, paper: text and page.
DIRECTIONS = {
    "persimmon": {
        "name": "Persimmon", "applied": True,
        "idea": "A clock set at 17 minutes past: the minute every employer’s careers page is read, every hour. Orange-red says “now” "
                "and stands apart from the blue of Indeed and LinkedIn, the green of Glassdoor, Upwork and ZipRecruiter, the yellow of "
                "Welcome to the Jungle and the red of Dice. It is also the colour our charts already use for the one mark that matters.",
        "mark": "#E8552B", "ui": "#C93F18", "ui_hover": "#A93210", "ui_dark": "#FF7A52", "ui_dark_hover": "#FF9466", "tint": "#FDEEE8", "tint_dark": "#3A1A10",
        "ink": "#121110", "paper": "#FFFFFF", "paper2": "#F6F4F1", "dark_bg": "#121110", "dark_card": "#1B1917",
        "head": "schibsted", "text": "publicsans"},
    "berry": {
        "name": "Berry", "applied": False,
        "idea": "An H whose bar is a dot: the live dot of a listing checked a minute ago. A deep berry is warm and human and is not "
                "used by any large job site.",
        "mark": "#B3245E", "ui": "#B3245E", "ui_hover": "#931B4C", "ui_dark": "#F47CA9", "ui_dark_hover": "#F79DBF", "tint": "#FBEAF1", "tint_dark": "#3A1226",
        "ink": "#14101A", "paper": "#FFFFFF", "paper2": "#F7F4F6", "dark_bg": "#141016", "dark_card": "#1D1820",
        "head": "hanken", "text": "hanken"},
    "brick": {
        "name": "Brick and sand", "applied": False,
        "idea": "Three rows of a list, the first one fresh: an index of jobs, set like a printed paper. Brick red on sand reads as "
                "editorial and calm.",
        "mark": "#A63A2B", "ui": "#A63A2B", "ui_hover": "#8A2F22", "ui_dark": "#E27A62", "ui_dark_hover": "#EA957F", "tint": "#F6E7E1", "tint_dark": "#36191A",
        "ink": "#1C1814", "paper": "#FBF8F2", "paper2": "#F3EDE2", "dark_bg": "#161310", "dark_card": "#201C18",
        "head": "schibsted", "text": "publicsans"},
}
APPLIED = next(k for k, d in DIRECTIONS.items() if d["applied"])


def mark(key, bg, fg):
    """The mark on a 32 x 32 grid: `bg` is the shape, `fg` the drawing on it."""
    if key == "persimmon":                         # a clock face: the hour hand at 12, the minute hand at 17 past
        a = math.radians(17 / 60 * 360)
        x, y = 16 + 9.6 * math.sin(a), 16 - 9.6 * math.cos(a)
        return (f'<circle cx="16" cy="16" r="16" fill="{bg}"/><path d="M16 16V8.6M16 16L{x:.2f} {y:.2f}" fill="none" stroke="{fg}" '
                f'stroke-width="3.4" stroke-linecap="round" stroke-linejoin="round"/>')
    if key == "berry":                             # an H whose bar is a dot
        return (f'<rect width="32" height="32" rx="8" fill="{bg}"/><rect x="8" y="7.5" width="3.8" height="17" rx="1.9" fill="{fg}"/>'
                f'<rect x="20.2" y="7.5" width="3.8" height="17" rx="1.9" fill="{fg}"/><circle cx="16" cy="16" r="3" fill="{fg}"/>')
    return (f'<rect width="32" height="32" rx="7" fill="{bg}"/><rect x="7" y="8.8" width="12.5" height="3.4" rx="1.7" fill="{fg}"/>'   # three list rows
            f'<circle cx="23.6" cy="10.5" r="2.5" fill="{fg}"/><rect x="7" y="14.3" width="18" height="3.4" rx="1.7" fill="{fg}" opacity=".78"/>'
            f'<rect x="7" y="19.8" width="11" height="3.4" rx="1.7" fill="{fg}" opacity=".56"/>')


def variants(key):
    """(file suffix, shape colour, drawing colour, text colour, page the file is meant for)"""
    d = DIRECTIONS[key]
    return [("", d["mark"], "#FFFFFF", d["ink"], "light"), ("-dark", d["ui_dark"], d["dark_bg"], "#FFFFFF", "dark"),
            ("-mono", d["ink"], "#FFFFFF", d["ink"], "light"), ("-mono-white", "#FFFFFF", d["ink"], "#FFFFFF", "dark")]


def outline(text, font_file, wght, size, tracking=-0.015):
    """The text as one SVG path at `size` px (cap height around 0.7 x size), and its width. Pair kerning is not applied: the
    tracking is set by eye for the name."""
    from fontTools.ttLib import TTFont
    from fontTools.varLib.instancer import instantiateVariableFont
    from fontTools.pens.svgPathPen import SVGPathPen
    from fontTools.pens.transformPen import TransformPen
    font = instantiateVariableFont(TTFont(ROOT / "assets" / "fonts" / font_file), {"wght": wght})
    upm, cmap, gs, hmtx = font["head"].unitsPerEm, font.getBestCmap(), font.getGlyphSet(), font["hmtx"]
    asc = font["hhea"].ascent
    s, x, parts = size / upm, 0.0, []
    for ch in text:
        g = cmap[ord(ch)]
        pen = SVGPathPen(gs)
        gs[g].draw(TransformPen(pen, (s, 0, 0, -s, x, asc * s)))
        parts.append(pen.getCommands())
        x += hmtx[g][0] * s + tracking * size
    return " ".join(p for p in parts if p), x - tracking * size, asc * s


def write_all():
    OUT.mkdir(parents=True, exist_ok=True)
    made = []
    for key, d in DIRECTIONS.items():
        fam, ffile, wght = FONTS[d["head"]]
        path, w, asc = outline(NAME, ffile, wght, 40)
        for sfx, bg, fg, ink, _ in variants(key):
            (OUT / f"{key}-mark{sfx}.svg").write_text(f'<svg xmlns="http://www.w3.org/2000/svg" width="256" height="256" viewBox="0 0 32 32" role="img" aria-label="{NAME}">{mark(key, bg, fg)}</svg>\n')
            # the lockup: the mark 48 px high, a 14 px gap, the name; the text sits on the mark's optical middle
            W, H = 48 + 14 + w + 2, 56
            (OUT / f"{key}-logo{sfx}.svg").write_text(
                f'<svg xmlns="http://www.w3.org/2000/svg" width="{W:.0f}" height="{H}" viewBox="0 0 {W:.1f} {H}" role="img" aria-label="{NAME}">'
                f'<g transform="translate(0 4) scale(1.5)">{mark(key, bg, fg)}</g>'
                f'<path transform="translate(62 {28 - asc * 0.62:.2f})" d="{path}" fill="{ink}"/></svg>\n')
            made += [f"{key}-mark{sfx}.svg", f"{key}-logo{sfx}.svg"]
        (OUT / f"{key}-wordmark.svg").write_text(f'<svg xmlns="http://www.w3.org/2000/svg" width="{w + 2:.0f}" height="{asc * 1.25:.0f}" viewBox="0 0 {w + 2:.1f} {asc * 1.25:.1f}" role="img" aria-label="{NAME}">'
                                                 f'<path d="{path}" fill="{d["ink"]}"/></svg>\n')
        made.append(f"{key}-wordmark.svg")
    print(f"{len(made)} files in {OUT.relative_to(ROOT)}")


def contrast(a, b):
    def lum(h):
        r, g, b_ = (int(h.lstrip("#")[i:i + 2], 16) / 255 for i in (0, 2, 4))
        f = lambda c: c / 12.92 if c <= 0.03928 else ((c + 0.055) / 1.055) ** 2.4
        return 0.2126 * f(r) + 0.7152 * f(g) + 0.0722 * f(b_)
    hi, lo = sorted((lum(a), lum(b)), reverse=True)
    return (hi + 0.05) / (lo + 0.05)


def _test():
    for key, d in DIRECTIONS.items():
        assert contrast(d["ui"], "#FFFFFF") >= 4.5, (key, "white text on the button")
        assert contrast(d["ui"], d["paper"]) >= 4.5, (key, "a link in the brand colour on the page")
        assert contrast(d["ui_dark"], d["dark_bg"]) >= 4.5 and contrast(d["ui_dark"], d["dark_card"]) >= 4.5, (key, "the brand colour on dark pages")
        assert contrast(d["dark_bg"], d["ui_dark"]) >= 4.5, (key, "dark text on the dark-mode button")
        assert contrast(d["mark"], d["paper"]) >= 3, (key, "the mark against the page")
        assert contrast(d["ink"], d["paper"]) >= 12, (key, "text")
    assert sum(d["applied"] for d in DIRECTIONS.values()) == 1
    print(f"brand: {len(DIRECTIONS)} directions pass the contrast checks; applied: {APPLIED}")


if __name__ == "__main__":
    if sys.argv[1:] == ["--test"]: _test()
    else: _test(); write_all()
