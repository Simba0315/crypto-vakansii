"""US metro areas: the towns around a city belong on that city's list and in a search for it.

27 Nov 2026: a job in Irving, Frisco, Arlington, Richardson, Garland, McKinney, Mansfield or Celina counted only as "Texas"; the Dallas
list and a search for "nurse Dallas" read just Dallas, Plano and Fort Worth, so about 450 nurse jobs around Dallas were out of sight.
Here every city, town, village, borough, township and census-designated place inside a metro area, as the US Census Bureau draws it,
names that metro's place page. The job keeps its own place line ("Irving, TX"): the metro only adds the page and the search filter.

The definition is the official one: OMB Bulletin 23-01 (July 2023), the Metropolitan Statistical Areas the Census Bureau publishes in
TIGERweb (tigerWMS_Current, layer "Metropolitan Statistical Areas"). The counties of each area are those whose interior point lies in
its outline; the places are the 2020 Census incorporated places and census-designated places whose interior point lies in it, and in
the states where towns and townships are the local government (New York, New Jersey, Pennsylvania, Massachusetts, New Hampshire,
Michigan, Minnesota, Wisconsin) the county subdivisions of those counties. A name is kept for a state only when it means one metro
there: every other place of that name in the state is outside all metros here and has a fifth of its people or fewer (2020 Census).
"Washington" townships in New Jersey, for one, are left out. A census-designated place or township under 1,000 people is left out.

    python3 metros.py --fetch     reads TIGERweb again and writes metros.json (about 150 requests, a few minutes)
    python3 metros.py             the checks

metro_of(location line, states_of) -> the metro slugs a location line names; states_of(part) gives the US states one part of the
line names (build.part_states). A town counts only when the same part of the line names its state ("Irving, TX", "TX-Irving",
"Irving, Texas 75039"); a bare "Arlington" could be Texas, Virginia or Massachusetts.
"""
import json, re, sys, time, unicodedata
from functools import lru_cache
from pathlib import Path

ROOT = Path(__file__).parent
DATA = ROOT / "metros.json"

# place page slug -> the Metropolitan Statistical Areas (CBSA codes, OMB 2023) it stands for
METRO_CBSA = {
    "dallas": ["19100"], "houston": ["26420"], "austin": ["12420"], "san-antonio": ["41700"], "new-york": ["35620"],
    "los-angeles": ["31080"], "chicago": ["16980"], "san-francisco": ["41860", "41940"], "seattle": ["42660"], "boston": ["14460"],
    "washington-dc": ["47900"], "atlanta": ["12060"], "miami": ["33100"], "phoenix": ["38060"], "denver": ["19740"],
    "philadelphia": ["37980"], "minneapolis": ["33460"], "detroit": ["19820"], "san-diego": ["41740"], "pittsburgh": ["38300"],
    "portland": ["38900"], "raleigh-durham": ["39580", "20500"],
}
MCD_STATES = {"36", "34", "42", "25", "33", "26", "27", "55"}        # where county subdivisions are local governments (FIPS)
FIPS = {"01": "AL", "02": "AK", "04": "AZ", "05": "AR", "06": "CA", "08": "CO", "09": "CT", "10": "DE", "11": "DC", "12": "FL", "13": "GA",
        "15": "HI", "16": "ID", "17": "IL", "18": "IN", "19": "IA", "20": "KS", "21": "KY", "22": "LA", "23": "ME", "24": "MD", "25": "MA",
        "26": "MI", "27": "MN", "28": "MS", "29": "MO", "30": "MT", "31": "NE", "32": "NV", "33": "NH", "34": "NJ", "35": "NM", "36": "NY",
        "37": "NC", "38": "ND", "39": "OH", "40": "OK", "41": "OR", "42": "PA", "44": "RI", "45": "SC", "46": "SD", "47": "TN", "48": "TX",
        "49": "UT", "50": "VT", "51": "VA", "53": "WA", "54": "WV", "55": "WI", "56": "WY"}
STATE_NAMES = {"alabama", "alaska", "arizona", "arkansas", "california", "colorado", "connecticut", "delaware", "florida", "georgia", "hawaii",
               "idaho", "illinois", "indiana", "iowa", "kansas", "kentucky", "louisiana", "maine", "maryland", "massachusetts", "michigan",
               "minnesota", "mississippi", "missouri", "montana", "nebraska", "nevada", "new hampshire", "new jersey", "new mexico", "new york",
               "north carolina", "north dakota", "ohio", "oklahoma", "oregon", "pennsylvania", "rhode island", "south carolina", "south dakota",
               "tennessee", "texas", "utah", "vermont", "virginia", "washington", "west virginia", "wisconsin", "wyoming", "district of columbia"}
# names that are words in a location line before they are towns, and places whose name is a country's
STOP = STATE_NAMES | {"remote", "hybrid", "onsite", "on site", "usa", "us", "united states", "america", "north", "south", "east", "west", "central",
                      "downtown", "midtown", "uptown", "village", "city", "county", "center", "centre", "university", "college", "airport",
                      "hospital", "medical center", "main", "lake", "park", "heights", "hills", "valley", "beach", "bay", "island", "river",
                      "springs", "station", "home", "field", "office", "corporate", "headquarters", "hq", "campus", "store", "warehouse",
                      "mexico", "lebanon", "jordan", "poland", "peru", "cuba", "china", "india", "canada", "japan", "panama", "chile",
                      "brazil", "wales", "scotland", "ireland", "holland", "norway", "sweden", "denmark", "finland", "egypt", "georgia"}
# USPS city names used for addresses inside a principal city that are not Census places (the boroughs' and the Valley's own names),
# the military posts of Joint Base San Antonio, and a misspelling one large employer uses (23 open nurse jobs, "Forth Worth, TX", 27 Nov 2026)
EXTRA = {
    "new-york": ("NY", ["Flushing", "Jamaica", "Astoria", "Long Island City", "Forest Hills", "Bayside", "Elmhurst", "Jackson Heights",
                        "Ridgewood", "Far Rockaway", "Woodside", "Rego Park", "Fresh Meadows", "Kew Gardens", "Richmond Hill", "Ozone Park",
                        "South Ozone Park", "Howard Beach", "Whitestone", "College Point", "Corona", "East Elmhurst", "Sunnyside", "Maspeth",
                        "Middle Village", "Glen Oaks", "Bellerose", "Queens Village", "Hollis", "Saint Albans", "Springfield Gardens",
                        "Rosedale", "Cambria Heights", "Laurelton", "Arverne", "Rockaway Park", "Little Neck", "Oakland Gardens",
                        "Queens", "Bronx", "The Bronx", "Staten Island", "Brooklyn", "Manhattan"]),
    "los-angeles": ("CA", ["North Hollywood", "Van Nuys", "Sherman Oaks", "Encino", "Woodland Hills", "Canoga Park", "Northridge", "Reseda",
                           "Sylmar", "San Pedro", "Wilmington", "Hollywood", "Studio City", "Tarzana", "Chatsworth", "Panorama City",
                           "Playa Vista", "Venice", "Westwood", "Harbor City", "Sun Valley", "Granada Hills", "Mission Hills", "Pacoima",
                           "Winnetka", "West Hills", "Porter Ranch", "Eagle Rock", "Valley Village", "Toluca Lake", "Tujunga", "Sunland",
                           "North Hills", "Arleta", "Playa del Rey", "Westchester", "Brentwood", "Bel Air", "Century City"]),
    "houston": ("TX", ["Kingwood", "Cypress", "Clear Lake"]),
    "dallas": ("TX", ["Forth Worth", "DFW Airport", "DFW"]),
    "san-antonio": ("TX", ["Fort Sam Houston", "JBSA Fort Sam Houston", "Lackland AFB", "JBSA Lackland", "Randolph AFB", "JBSA Randolph"]),
}


def norm(s):
    """The one spelling a name is looked up by: lower case, no accents or dots, "Saint"/"Mount"/"Fort" as "st"/"mt"/"ft", "township" as "twp"."""
    s = unicodedata.normalize("NFKD", s or "").encode("ascii", "ignore").decode().lower()
    s = re.sub(r"[.']", "", s).replace("-", " ").replace("&", " and ")
    s = re.sub(r"\bsaint\b", "st", s)
    s = re.sub(r"\bmount\b", "mt", s)
    s = re.sub(r"\bfort\b", "ft", s)
    s = re.sub(r"\btownship\b", "twp", s)
    return " ".join(s.split())


# ---- reading TIGERweb ------------------------------------------------------------------------------------------------------------------
TW = "https://tigerweb.geo.census.gov/arcgis/rest/services/TIGERweb"


def _get(url, params, tries=2):
    """One query of a TIGERweb layer, sent as a form with curl (Python's own HTTPS fails on certificates on some Macs; net.py does the same)."""
    import subprocess, urllib.parse
    q = urllib.parse.urlencode(params)
    for i in range(tries):
        r = subprocess.run(["curl", "-s", "-4", "--fail", "--max-time", "180", "-A", "Mozilla/5.0 (job-board aggregator)",
                            "--data-binary", "@-", "-H", "Content-Type: application/x-www-form-urlencoded", url + "/query"],
                           input=q.encode(), capture_output=True, timeout=200)
        try:
            d = json.loads(r.stdout) if r.returncode == 0 else {"error": f"curl {r.returncode}"}
        except ValueError:
            d = {"error": "not JSON"}
        if "error" not in d:
            time.sleep(0.3)
            return d
        if i == tries - 1: raise OSError(f"TIGERweb: {str(d['error'])[:300]}")
        time.sleep(5)


def _all(url, where, fields):
    """Every row of a layer that matches, page by page (TIGERweb answers at most its maxRecordCount rows a request)."""
    rows, off = [], 0
    while True:
        d = _get(url, {"where": where, "outFields": fields, "returnGeometry": "false", "resultOffset": off, "resultRecordCount": 5000,
                       "orderByFields": "OBJECTID", "f": "json"})
        rows += [f["attributes"] for f in d.get("features", [])]
        if not d.get("exceededTransferLimit") or not d.get("features"): return rows
        off += len(d["features"])


def _inside(x, y, rings):
    """Even-odd test of a point against every ring of an outline (holes and islands included)."""
    hit = False
    for ring in rings:
        j = len(ring) - 1
        for i in range(len(ring)):
            xi, yi, xj, yj = ring[i][0], ring[i][1], ring[j][0], ring[j][1]
            if (yi > y) != (yj > y) and x < (xj - xi) * (y - yi) / (yj - yi) + xi: hit = not hit
            j = i
    return hit


def fetch():
    cur, c20 = TW + "/tigerWMS_Current/MapServer", TW + "/tigerWMS_Census2020/MapServer"
    msa = {}                    # cbsa -> (name, rings, bbox)
    for slug, codes in METRO_CBSA.items():
        for code in codes:
            d = _get(cur + "/93", {"where": f"CBSA='{code}'", "outFields": "CBSA,NAME", "returnGeometry": "true", "outSR": 4326,
                                   "maxAllowableOffset": 0.0002, "geometryPrecision": 5, "f": "json"})
            f = d["features"][0]
            rings = f["geometry"]["rings"]
            xs, ys = [p[0] for r in rings for p in r], [p[1] for r in rings for p in r]
            msa[code] = (f["attributes"]["NAME"].replace(" Metro Area", ""), rings, (min(xs), min(ys), max(xs), max(ys)))
            print(f"{slug}: {msa[code][0]}, {sum(len(r) for r in rings):,} points", flush=True)
    slug_of = {code: slug for slug, codes in METRO_CBSA.items() for code in codes}

    def where_is(lat, lon):
        for code, (_, rings, (x0, y0, x1, y1)) in msa.items():
            if x0 <= lon <= x1 and y0 <= lat <= y1 and _inside(lon, lat, rings): return code
        return None

    counties = {}               # (state fips, county fips) -> (cbsa, name)
    for code, (_, rings, (x0, y0, x1, y1)) in msa.items():
        d = _get(c20 + "/82", {"geometry": f"{x0},{y0},{x1},{y1}", "geometryType": "esriGeometryEnvelope", "inSR": 4326,
                               "spatialRel": "esriSpatialRelIntersects", "outFields": "STATE,COUNTY,BASENAME,NAME,INTPTLAT,INTPTLON",
                               "returnGeometry": "false", "f": "json"})
        for a in (f["attributes"] for f in d["features"]):
            if _inside(float(a["INTPTLON"]), float(a["INTPTLAT"]), rings): counties[(a["STATE"], a["COUNTY"])] = (code, a["NAME"])
    states = sorted({st for st, _ in counties})
    print(f"{len(counties)} counties in {len(states)} states", flush=True)

    entries = {}                # (state code, key) -> [(slug or None, population, display name, kind)]
    def add(st, name, slug, pop, kind):
        k = norm(name)
        if len(k) < 3 or k in STOP: return
        entries.setdefault((FIPS[st], k), []).append((slug, pop or 0, name, kind))

    for st in states:
        for layer, kind in (("26", "place"), ("28", "cdp")):
            for a in _all(c20 + "/" + layer, f"STATE='{st}'", "STATE,BASENAME,NAME,LSADC,FUNCSTAT,POP100,INTPTLAT,INTPTLON"):
                code = where_is(float(a["INTPTLAT"]), float(a["INTPTLON"]))
                add(st, a["BASENAME"], slug_of.get(code), a["POP100"], kind)
        if st in MCD_STATES:
            for a in _all(c20 + "/20", f"STATE='{st}'", "STATE,COUNTY,BASENAME,NAME,LSADC,FUNCSTAT,POP100"):
                if a["FUNCSTAT"] not in ("A", "B", "C") or not a["BASENAME"] or a["BASENAME"].lower().startswith("county subdivisions not"): continue
                code = counties.get((st, a["COUNTY"]), (None,))[0]
                add(st, a["BASENAME"], slug_of.get(code), a["POP100"], "mcd")
                if "township" in (a["NAME"] or "").lower(): add(st, a["BASENAME"] + " Township", slug_of.get(code), a["POP100"], "mcd")
        print(f"state {FIPS[st]}: {sum(1 for s_, _ in entries if s_ == FIPS[st]):,} names", flush=True)
    for (st, co), (code, name) in counties.items():              # "Collin County", "Fairfax County": a county is in one metro
        add(st, name, slug_of[code], 10 ** 7, "county")
        if name.endswith(" County"): add(st, name[:-7] + " Co", slug_of[code], 10 ** 7, "county")

    names, dropped = {}, []
    for (st, k), es in sorted(entries.items()):
        best = max(es, key=lambda x: x[1])
        if not best[0]: continue
        others = [x for x in es if x[0] != best[0]]
        if others and best[1] < 5 * max(x[1] for x in others):
            dropped.append(f"{best[2]}, {st} ({best[0]} {best[1]:,} vs {max(x[1] for x in others):,})")
            continue
        if best[3] in ("cdp", "mcd") and best[1] < 1000: continue
        names.setdefault(st, {})[k] = [best[0], best[2]]
    out = {"source": "US Census Bureau TIGERweb: Metropolitan Statistical Areas of OMB Bulletin 23-01 (tigerWMS_Current), counties, "
                     "incorporated places, census-designated places and county subdivisions of the 2020 Census (tigerWMS_Census2020)",
           "read": time.strftime("%Y-%m-%d"),
           "metros": {slug: {"areas": [msa[c][0] for c in codes], "cbsa": codes,
                             "counties": sorted(f"{n}, {FIPS[s]}" for (s, _), (c, n) in counties.items() if c in codes),
                             "names": sum(1 for st in names for v in names[st].values() if v[0] == slug)}
                      for slug, codes in METRO_CBSA.items()},
           "names": names}
    DATA.write_text(json.dumps(out, ensure_ascii=False, sort_keys=True, separators=(",", ":")) + "\n")
    print(f"metros.json: {sum(len(v) for v in names.values()):,} names, {len(dropped):,} left out as meaning more than one place, e.g. "
          + "; ".join(dropped[:12]))


# ---- reading a location line -----------------------------------------------------------------------------------------------------------
_N = {}
PARTS = re.compile(r";|\||/| or | and |•")
SEGS = re.compile(r",|\(|\)| - | – | — |:|\s@\s")
CANADA = re.compile(r"\bcanada\b|,\s*(?:AB|BC|MB|NB|NL|NS|NT|NU|ON|PE|QC|SK|YT)\b|\b(?:ontario|british columbia|qu[eé]bec|alberta|manitoba|saskatchewan|nova scotia)\b", re.I)
_CODES = set(FIPS.values()) | {"DC"}
_TAIL = re.compile(r"\s+(?:\d{5}(?:\s?\d{4})?|usa?|united states)$")
_LEAD = re.compile(r"^(?:usa?\s)?([a-z]{2})\s(?=[a-z])")


def names():
    """state code -> {name key: [slug, name as the Census writes it]}, and every key -> {state: slug}, read once."""
    if not _N:
        d = json.loads(DATA.read_text()) if DATA.exists() else {"names": {}, "metros": {}}
        for slug, (st, xs) in EXTRA.items():          # the postal names, kept here so a change needs no new read of TIGERweb
            for x in xs: d["names"].setdefault(st, {}).setdefault(norm(x), [slug, x])
        by_key = {}
        for st, ks in d["names"].items():
            for k, (slug, _) in ks.items(): by_key.setdefault(k, {})[st] = slug
        _N.update(by_state=d["names"], by_key=by_key, metros=d.get("metros", {}), longest=max((len(k.split()) for k in by_key), default=0))
    return _N


def _keys(seg):
    """The name keys one segment of a part can be: "Irving", "Irving TX 75039", "TX-Irving", "US-TX-Irving"."""
    k = norm(seg)
    if not k: return ()
    for _ in range(3):
        k2 = _TAIL.sub("", k)
        m = re.search(r"\s([a-z]{2})$", k2)
        if m and m.group(1).upper() in _CODES: k2 = k2[:m.start()]
        for nm in ("texas", "new york", "new jersey", "pennsylvania", "california", "illinois", "indiana", "washington", "massachusetts",
                   "new hampshire", "virginia", "maryland", "georgia", "florida", "arizona", "colorado", "delaware", "minnesota",
                   "wisconsin", "michigan", "oregon", "north carolina", "west virginia"):
            if k2.endswith(" " + nm): k2 = k2[:-len(nm) - 1]; break
        m = _LEAD.match(k2)
        if m and m.group(1).upper() in _CODES: k2 = k2[m.end():]
        if k2 == k: break
        k = k2.strip()
    return (k,) if k else ()


@lru_cache(maxsize=300000)
def metro_of(loc, states_of):
    """((slug, town, state), ...) for every town of a metro the line names with its state: "Irving, TX; Remote" -> (("dallas", "Irving",
    "TX"),). Kept for the lines read most (the same place line stands on many jobs, and the place pages ask again for the towns)."""
    n = names()
    if not loc or not n["by_key"]: return ()
    out = []
    for part in PARTS.split(loc):
        if CANADA.search(part): continue
        sts = None
        for seg in SEGS.split(part):
            for k in _keys(seg):
                hit = n["by_key"].get(k)
                if not hit: continue
                if sts is None: sts = states_of(part)
                for st in sts:
                    if st in hit and (hit[st], n["by_state"][st][k][1], st) not in out: out.append((hit[st], n["by_state"][st][k][1], st))
    return tuple(out)


def test():
    def st(part):                                     # a plain stand-in for build.part_states
        got = {m for m in re.findall(r"(?:^|[,\s(-])([A-Z]{2})(?![A-Za-z])", part) if m in _CODES}
        got |= {c for nm, c in (("texas", "TX"), ("virginia", "VA"), ("new york", "NY"), ("minnesota", "MN")) if nm in part.lower() and not "west virginia" in part.lower()}
        return got
    slugs = lambda loc: {s for s, _, _ in metro_of(loc, st)}
    n = names()
    assert n["by_key"], "metros.json is missing: python3 metros.py --fetch"
    assert norm("St. Paul") == norm("Saint Paul") == "st paul" and norm("Fort Worth") == norm("Ft. Worth") and norm("Edison Township") == "edison twp"
    for town in ("Irving", "Frisco", "Arlington", "Richardson", "Garland", "McKinney", "Mansfield", "Celina", "Denton", "Grand Prairie", "Mesquite", "Allen"):
        assert slugs(f"{town}, TX") == {"dallas"}, (town, slugs(f"{town}, TX"))
    assert slugs("Irving, Texas, United States") == slugs("TX-Irving") == slugs("US-TX-Irving") == slugs("Irving TX 75039") == {"dallas"}
    assert slugs("IRVING, TX, US") == slugs("Irving, TX 75062 Vizient Corporate HQ") == slugs("Forth Worth, TX, US") == {"dallas"}
    assert slugs("Arlington, VA") == {"washington-dc"} and slugs("Arlington, MA") == {"boston"} and slugs("Arlington") == set()
    assert slugs("Pasadena, TX") == {"houston"} and slugs("Pasadena, CA") == {"los-angeles"} and slugs("The Woodlands, TX") == {"houston"}
    assert slugs("Sugar Land, TX") == slugs("Katy, TX") == {"houston"} and slugs("New Braunfels, TX") == {"san-antonio"}
    assert slugs("Round Rock, TX") == slugs("San Marcos, TX") == {"austin"} and slugs("Fort Sam Houston, Texas") == {"san-antonio"}
    assert slugs("Jersey City, NJ") == slugs("Hoboken, NJ") == slugs("Yonkers, NY") == slugs("Flushing, NY") == {"new-york"}
    assert slugs("Naperville, IL") == slugs("Gary, IN") == {"chicago"} and slugs("Tacoma, WA") == slugs("Bellevue, WA") == {"seattle"}
    assert slugs("King of Prussia, PA") == slugs("Camden, NJ") == slugs("Wilmington, DE") == {"philadelphia"}
    assert slugs("Bloomington, MN") == slugs("St. Paul, MN") == slugs("Saint Paul, Minnesota") == {"minneapolis"}
    assert slugs("Troy, MI") == slugs("Dearborn, MI") == slugs("Southfield, MI") == {"detroit"}
    assert slugs("Fort Lauderdale, FL") == slugs("Boca Raton, FL") == {"miami"} and slugs("Mesa, AZ") == slugs("Chandler, AZ") == {"phoenix"}
    assert slugs("Aurora, CO") == slugs("Centennial, CO") == {"denver"} and slugs("Aurora, IL") == {"chicago"}
    assert slugs("Hillsboro, OR") == slugs("Vancouver, WA") == {"portland"} and slugs("Cary, NC") == slugs("Chapel Hill, NC") == {"raleigh-durham"}
    assert slugs("Richmond, BC, CA") == set() and slugs("Richmond, CA") == {"san-francisco"} and slugs("Fremont, CA") == {"san-francisco"}
    assert slugs("Collin County, TX") == {"dallas"} and slugs("Fairfax County, VA") == {"washington-dc"} and slugs("Montgomery County, PA") == {"philadelphia"}
    assert slugs("Austin, TX") == {"austin"} and slugs("Paris, TX") == set() and slugs("Lubbock, TX") == set() and slugs("Remote - TX") == set()
    assert metro_of("Irving, TX; Frisco, TX", st) == (("dallas", "Irving", "TX"), ("dallas", "Frisco", "TX"))
    m = n["metros"]
    assert m["dallas"]["areas"] == ["Dallas-Fort Worth-Arlington, TX"] and len(m["dallas"]["counties"]) >= 11, m["dallas"]
    assert all(m[s]["names"] >= 20 for s in METRO_CBSA), {s: m[s]["names"] for s in METRO_CBSA}
    print(f"metros: {len(METRO_CBSA)} metro areas, {sum(len(v) for v in n['by_state'].values()):,} town names, all checks passed")


if __name__ == "__main__":
    fetch() if "--fetch" in sys.argv else test()
