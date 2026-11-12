"""Probe public ATS job-board APIs for tech companies; write the ones that respond to sources_tech.json."""
import json, re, sys, concurrent.futures as cf
from net import get_json

NAMES = """Adept|Imbue|Sierra|Decagon|Cresta|Observe.AI:observeai|AssemblyAI|Deepgram|Speechmatics|Suno|Captions|Typeface|Tavus|Hume AI|Inworld AI:inworldai|Poolside|Magic:magic.dev|Cognition|Factory|Codeium|Tabnine|Warp|Zed:zed|
Fireworks AI|Baseten|Lightning AI|Predibase|Arize AI:arizeai|Fiddler AI:fiddlerlabs|Galileo|Humanloop|Braintrust|Vectara|Qdrant|Chroma|Zilliz|Unstructured|Twelve Labs|Nomic AI:nomic|Snorkel AI|Surge AI|
Invisible Technologies:invisibletech|Turing|Mercor|Encord|V7:v7labs|Roboflow|Landing AI|Covariant|Physical Intelligence|Figure:figureai|1X:1x|Agility Robotics|Apptronik|Boston Dynamics|Skild AI|Wayve|Applied Intuition|
Gatik|Kodiak|May Mobility|Motional|Serve Robotics|Carbon Robotics|Formic|Machina Labs|Hadrian|Saronic|Epirus|Castelion|Hermeus|Boom Supersonic:boom|Astranis|Varda|Stoke Space|Firefly Aerospace|Impulse Space|K2 Space|
Apex:apexspace|True Anomaly|Umbra|Capella Space|Pano AI|Dave|MoneyLion|Varo|Current|Step|Greenlight|Acorns|Stash|Public|M1:m1finance|Wealthsimple|Trade Republic|Qonto|Pleo|Spendesk|Payhawk|Moss|Mollie|SumUp|
GoCardless|Zopa|Starling Bank|Tide|Lunar|Scalable Capital|Raisin|Mambu|Thought Machine|10x Banking|Solaris|Upvest|Alpaca|DriveWealth|MX|Method Financial|Atomic|Pinwheel|Argyle|Truework|Check:checkhq|Justworks|
Papaya Global|Multiplier|Velocity Global|BambooHR|HiBob|Personio|Factorial|Leapsome|15Five|Betterworks|Bonusly|Lyra Health|Spring Health|Headway|Grow Therapy|Alma|Talkspace|Modern Health|Hinge Health|Sword Health|
Omada Health|Virta Health|Carbon Health|Forward|Maven Clinic|Kindbody|Carrot Fertility|Thirty Madison|Brightline|Cedar|Collective Health|Garner Health|Included Health|Transcarent|Sana:sanabenefits|Abridge|
Ambience Healthcare|Nabla|Suki|DeepScribe|OpenEvidence|Hippocratic AI|Viz.ai:vizai|PathAI|Paige|Freenome|Color|Verily|Insitro|Generate Biomedicines|Isomorphic Labs|EvolutionaryScale|Chai Discovery|Dyno Therapeutics|
Docker|Gitpod|Coder|Depot|Dagger|Deno|Convex|Xata|Turso|Fauna|EdgeDB|SurrealDB|Upstash|Momento|Aiven|Redpanda|WarpStream|StreamNative|Decodable|Tinybird|Imply|Firebolt|CelerData|Onehouse|Dagster Labs:dagsterlabs|
Prefect|Astronomer|RudderStack|Snowplow|mParticle|Statsig|Eppo|GrowthBook|Optimizely|Split|LogRocket|FullStory|Observe:observeinc|Edge Delta|Mezmo|Axiom|SigNoz|Rollbar|Instabug|Embrace|Kubecost|Cast AI|Vantage|
CloudZero|Finout|Port|Cortex|OpsLevel|Humanitec|Qovery|Northflank|Porter|Okteto|Graphite|Trunk|LinearB|Swarmia|Jellyfish|Code Climate|Codacy|DeepSource|Aikido Security|Jit|Upwind|Tigera|
Hopper|GetYourGuide|Omio|Bolt|Wolt|Glovo|Deliveroo|Getir|Gopuff|Grubhub|ChowNow|Olo|SevenRooms|Thumbtack|Taskrabbit|Angi|Houzz|Offerpad|Pacaso|Vacasa|Sonder|Outdoorsy|Turo|Getaround|Lime|Bird|Tier|Voi|
Rad Power Bikes|Tonal|Hydrow|AllTrails|Komoot|Babbel|Preply|Cambly|Outschool|2U|Udacity|Codecademy|DataCamp|Brilliant|MasterClass|Skillshare|Teachable|Thinkific|Kajabi|Gumroad|Linktree|Sketch|WP Engine|Kinsta|
Pantheon|Acquia|Hygraph|Prismic|Plasmic|Appsmith|Budibase|Glide|Softr|Bubble|FlutterFlow|Make|n8n|Tray.io:trayio|Workato|Pipedream|Parabola|
Cursor AI:cursor|Lovable|Bolt.new:stackblitz|StackBlitz|Supermaven|Sweep|Greptile|CodeRabbit|Qodo|Sourcery|Pieces|Mintlify|Speakeasy|Stainless|Fern|Scalar|Liveblocks|PartyKit|Ably|Pusher|Stream:getstream|
Sendbird|Daily|LiveKit|Agora|100ms|Whereby|Riverside|Descript|Loom|Tella|mmhmm|Around|Gather|Kumospace|Butter|Luma|Partiful|Posh|Dice:dicefm|Eventbrite|Splash|Hopin|Airmeet|Goldcast|Zuddl|Bizzabo|Cvent"""

def tokens(entry):
    name, _, explicit = entry.partition(":")
    base = re.sub(r"[^a-z0-9]", "", name.lower())
    toks = [explicit] if explicit else []
    toks += [base, re.sub(r"[^a-z0-9]+", "-", name.lower()).strip("-")]
    if base.endswith(("labs", "ai", "inc", "hq")) is False:
        toks += [base + "hq", base + "inc"]
    seen, out = set(), []
    for t in toks:
        if t and t not in seen: seen.add(t); out.append(t)
    return name.strip(), out[:4]

def check(item):
    name, tok = item
    found = []
    d = get_json(f"https://boards-api.greenhouse.io/v1/boards/{tok}/jobs", 15)
    if isinstance(d, dict) and d.get("jobs"): found.append(("greenhouse", tok, len(d["jobs"])))
    d = get_json(f"https://api.lever.co/v0/postings/{tok}?mode=json&limit=300", 15)
    if isinstance(d, list) and d: found.append(("lever", tok, len(d)))
    d = get_json(f"https://api.ashbyhq.com/posting-api/job-board/{tok}", 15)
    if isinstance(d, dict) and d.get("jobs"): found.append(("ashby", tok, len(d["jobs"])))
    return name, found

entries = [tokens(x) for x in NAMES.replace("\n", "").split("|") if x.strip()]
items = [(n, t) for n, ts in entries for t in ts]
out = {}
with cf.ThreadPoolExecutor(24) as ex:
    for name, found in ex.map(check, items):
        for f in found: out.setdefault(name, []).append(f)
res = []
for name, fs in sorted(out.items()):
    best = max(fs, key=lambda f: f[2])
    res.append({"name": name, "ats": best[0], "token": best[1], "count": best[2]})
json.dump(res, open(sys.argv[1], "w"), ensure_ascii=False, indent=1)
print(f"{len(entries)} candidates -> {len(res)} companies, {sum(r['count'] for r in res)} jobs")
