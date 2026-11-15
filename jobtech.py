"""Jobs from Sweden's public employment service (Arbetsförmedlingen, Platsbanken), from its open data (JobTech JobSearch API).

The ads are published under CC0 (jobsearch.api.jobtechdev.se/swagger.json: "Ads are licensed under CC0"): no key, no condition.
The job page still names the source and links each ad's page on arbetsformedlingen.se (build.py, PORTAL_SOURCE).

What is taken (15 Nov 2026, ROADMAP 112), the same rule as for the other sources: office and professional work, no staffing agencies.
- occupation fields: IT, administration/finance/law, sales/purchasing/marketing (without shop staff), managers, technical work,
  culture/media/design, natural science. Healthcare, hotels and restaurants, transport and warehouses, building, cleaning and
  security are left out;
- employers whose name says staffing or recruitment ("bemanning", "rekrytering", the big agencies) are left out.
Read once a day by portals.py (.github/workflows/portals.yml), like Russia's portal; the hourly run applies the snapshot.
"""
import concurrent.futures as cf, json, os, re, sys

API = "https://jobsearch.api.jobtechdev.se/search"
SOURCE = "Platsbanken"
FIELDS = {"apaJ_2ja_LuF": "engineering", "X82t_awd_Qyc": "operations", "RPTn_bxG_ExZ": "sales-bd", "bh3H_Y3h_5eD": "operations",
          "6Hq3_tKo_V57": "engineering", "9puE_nYg_crq": "design", "kJeN_wmw_9wX": "data-research"}
REGIONS = ["01", "03", "04", "05", "06", "07", "08", "09", "10", "12", "13", "14", "17", "18", "19", "20", "21", "22", "23", "24", "25"]
SHOP = re.compile(r"butik|kassa|dagligvaru|fackhandel|apotek|bensinstation|telefonförsäljare", re.I)
AGENCY = re.compile(r"bemanning|rekrytering|staffing|recruit|academic work|adecco|manpower|randstad|proffice|poolia|studentconsulting|student consulting|"
                    r"lernia|uniflex|jurek|\btempo\b|dfind|experis|hays\b|perido|clockwork|ework|keystep|level recruitment|framtiden|personalpartner|"
                    r"konsultbolag|bemannings", re.I)


def get(params):
    import collect
    q = "&".join(f"{k}={v}" for k, v in params.items())
    return collect.get_json(f"{API}?{q}", 60)


def ads_of(field):
    """Every current ad in one occupation field: pages of 100 up to the API's 2,100, split by region when a field has more."""
    first = get({"occupation-field": field, "limit": 0})
    if not isinstance(first, dict): return None
    total = (first.get("total") or {}).get("value", 0)
    out = []
    for region in ([None] if total <= 2100 else REGIONS):
        off = 0
        while True:
            p = {"occupation-field": field, "limit": 100, "offset": off}
            if region: p["region"] = region
            d = get(p)
            if not isinstance(d, dict) or not isinstance(d.get("hits"), list): return None
            out += d["hits"]; off += 100
            if len(d["hits"]) < 100 or off > 2000: break
    return out


def to_job(h, field_cat):
    import collect
    title, url = (h.get("headline") or "").strip(), h.get("webpage_url") or ""
    company = ((h.get("employer") or {}).get("name") or "").strip()
    if not title or not company or not url.startswith("https://") or AGENCY.search(company): return None
    if SHOP.search(((h.get("occupation_group") or {}).get("label") or "") + " " + ((h.get("occupation") or {}).get("label") or "")): return None
    a = h.get("workplace_address") or {}
    city = (a.get("municipality") or a.get("city") or "").strip().title()
    loc = collect.place(city, a.get("region"), "Sweden")
    wm = ((h.get("workplace_model") or {}).get("label") or "").lower()
    remote, hybrid = "distans" in wm, "hybrid" in wm
    if remote: loc = collect.place("Remote", loc)
    d = h.get("description") or {}
    desc = d.get("text_formatted") or ""
    hours = ((h.get("working_hours_type") or {}).get("label") or "").lower()
    hint = "part-time" if "deltid" in hours else "full-time" if "heltid" in hours else ""
    if "tidsbegräns" in ((h.get("employment_type") or {}).get("label") or "").lower(): hint = "temporary"
    j = collect.norm(company, "platsbanken", h.get("id"), title, url, loc, remote, (h.get("occupation_field") or {}).get("label") or "",
                     str(h.get("publication_date") or "")[:10], d.get("text") or collect.strip_html(desc), "", hint, desc, hybrid)
    if j["cat"] == "other": j["cat"] = field_cat
    j["id"] = f"platsbanken-{h.get('id')}"           # the service's own ad number: stays the same if the employer's name is written differently
    j["src"] = SOURCE
    return j


def fetch():
    """Today's office and professional ads, or None when the service could not be read (the jobs from it then stay as they were)."""
    try:
        with cf.ThreadPoolExecutor(4) as ex:
            got = dict(zip(FIELDS, ex.map(ads_of, FIELDS)))
        if any(v is None for v in got.values()): return None
        seen, jobs = set(), []
        for field, hits in got.items():
            for h in hits:
                if h.get("id") in seen or h.get("removed"): continue
                seen.add(h.get("id"))
                j = to_job(h, FIELDS[field])
                if j: jobs.append(j)
        return jobs if len(jobs) >= 500 else None
    except Exception as ex:
        print(f"Platsbanken: {type(ex).__name__}: {ex}")
        return None


if __name__ == "__main__":
    from collections import Counter
    jobs = fetch() if len(sys.argv) < 2 else [j for h in json.load(open(sys.argv[1]))["hits"] for j in [to_job(h, "other")] if j]
    print(len(jobs or []), "jobs")
    if jobs:
        print(Counter(j["cat"] for j in jobs).most_common())
        print(len({j["company"] for j in jobs}), "employers")
