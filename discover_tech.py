"""Probe public ATS job-board APIs for tech companies; write the ones that respond to sources_tech.json."""
import json, re, sys, concurrent.futures as cf
from net import get_json

NAMES = """Stripe|Airbnb|Dropbox|Pinterest|Reddit|Discord|Figma|Notion|Airtable|Asana|GitLab|HashiCorp|Datadog|Cloudflare|Twilio|Okta|MongoDB|Elastic|Databricks|
Confluent|Cockroach Labs|PlanetScale|Vercel|Netlify|Supabase|Render|Fly.io:flyio|Railway|Linear|Retool|Webflow|Zapier|Calendly|Loom|Miro|Canva|Grammarly|Duolingo|
Coursera|Udemy|Khan Academy|Quizlet|Instacart|DoorDash|Lyft|Chime|Plaid|Brex|Ramp|Mercury|Gusto|Rippling|Deel|Remote|Oyster:oysterhr|Lattice|Culture Amp|
Intercom|Front|Gorgias|Klaviyo|Attentive|Braze|Iterable|Amplitude|Mixpanel|Heap|PostHog|Sentry|LaunchDarkly|PagerDuty|New Relic|Grafana Labs|Honeycomb|Chronosphere|
Snyk|Wiz:wizinc|Lacework|SentinelOne|1Password|Bitwarden|Tailscale|Vanta|Drata|Anthropic|OpenAI|Cohere|Hugging Face|Scale AI|Labelbox|Weights & Biases:wandb|
Runway:runwayml|Stability AI|Perplexity|Mistral AI:mistral|xAI|Character.AI:character|ElevenLabs|Replicate|Modal|Anyscale|Together AI|Pinecone|Weaviate|LangChain|
LlamaIndex|Cursor:anysphere|Replit|Sourcegraph|Postman|Kong|Apollo GraphQL|Hasura|Prisma|Temporal|dbt Labs|Fivetran|Airbyte|Hightouch|Census|Starburst|Dremio|
ClickHouse|SingleStore|Timescale|Neon|Redis|Yugabyte|Materialize|MotherDuck|Epic Games|Riot Games|Roblox|Unity|Niantic|Scopely|Twitch|Spotify|SoundCloud|
Peloton|Strava|Whoop|Oura|Calm|Headspace|Noom|Hims & Hers:hims|Ro|Oscar Health:oscar|Devoted Health:devoted|Cityblock Health:cityblock|Flatiron Health:flatironhealth|Tempus|Benchling|
Ginkgo Bioworks|Recursion|Zipline|Anduril|Shield AI|Skydio|Relativity Space|SpaceX|Planet|Rocket Lab|Waymo|Cruise|Aurora|Zoox|Nuro|Rivian|Lucid Motors:lucidmotors|
Samsara|Flexport|Shippo|Faire|BigCommerce|Squarespace|Chewy|StockX|GOAT:goatgroup|Poshmark|Depop|Vinted|Klarna|Affirm|Wise|Monzo|N26|Nubank|SoFi|Betterment|
Wealthfront|Carta|AngelList|Pilot|Expensify|Navan|Airwallex|Checkout.com:checkout|Adyen|Marqeta|Toast|Block:block|Opendoor|Zillow|Redfin|Compass|ClickUp|
monday.com:mondaycom|Smartsheet|Coda|DocuSign|Box|Egnyte|Zoom|Dialpad|Gong|Outreach|Salesloft|Apollo.io:apolloio|ZoomInfo|Clearbit|6sense|Demandbase|GitBook|ReadMe|
Mintlify|Stytch|Clerk|WorkOS|Descope|Algolia|Typesense|Contentful|Sanity|Strapi|Storyblok|Builder.io:builder|Framer|Pitch|Gamma|Descript|VEED|Kapwing|Synthesia|
HeyGen|Luma AI:lumalabs|Pika|Ideogram|Jasper|Copy.ai:copyai|Writer|Glean|Hebbia|Harvey|Ironclad|Clio|Everlaw|Palantir|C3 AI:c3ai|Dataiku|Alteryx|Sigma:sigmacomputing|
Hex:hextechnologies|Mode|ThoughtSpot|Domo|Monte Carlo:montecarlodata|Bigeye|Atlan|Alation|Collibra|Immuta|Cribl|Sumo Logic|Coralogix|Sysdig|Aqua Security:aquasecurity|
Orca Security:orca|Chainguard|Semgrep|Socket|Endor Labs|Doppler|Infisical|Teleport|StrongDM|Twingate|Netskope|Illumio|Abnormal Security:abnormalsecurity|
Expel|Huntress|Arctic Wolf:arcticwolf|Red Canary|Bugcrowd|HackerOne|Cobalt|Synack|Nutanix|Pure Storage|Cohesity|Rubrik|Druva|Wasabi|Backblaze|DigitalOcean|
CoreWeave|Lambda:lambdalabs|Crusoe|RunPod|Cerebras|SambaNova:sambanovasystems|Groq|Tenstorrent|SiFive|Lightmatter|PsiQuantum|IonQ|Rigetti|
Shopify|Atlassian|Wayfair|Etsy|Yelp|Nextdoor|Bumble|Hinge|Tinder|Match Group|Grindr|Snap|Patreon|Substack|Medium|Quora|Vimeo|Mux|Cloudinary|Imgix|Fastly|
Akamai|Bandwidth|Vonage|Sinch|MessageBird:bird|Customer.io:customerio|Mailchimp|ConvertKit:kit|Beehiiv|Ghost|WordPress VIP:automattic|Automattic|Wikimedia|Mozilla|
Signal|Proton|Brave|DuckDuckGo|Kagi|Arc:thebrowsercompany|Raycast|Obsidian|Todoist:doist|Doist|Basecamp:37signals|Toggl|Hotjar|Buffer|Hootsuite|Sprout Social|
Later|Typeform|Jotform|SurveyMonkey|Qualtrics|Medallia|UserTesting|Maze|Lyssna|Pendo|Appcues|WalkMe|Whatfix|Gainsight|ChurnZero|Totango|Vitally|Catalyst|
Productboard|Aha|Jira|Shortcut|Height|Plane|Zenhub|CircleCI|Buildkite|Harness|Octopus Deploy|Spacelift|env0|Pulumi|Upbound|Crossplane|Rancher|Mirantis|
D2iQ|Platform9|Loft|Akuity|Tetrate|Solo.io:soloio|Ambassador Labs|Isovalent|Cilium|Aviatrix|Alkira|Kentik|ThousandEyes|Catchpoint|Checkly|Better Stack|
Incident.io:incident|FireHydrant|Rootly|Blameless|Statuspage|Instatus|Zenduty|Squadcast|Opsgenie|Rundeck|StackHawk|Detectify|Intruder|Probely|Invicti|
Veracode|Checkmarx|Sonar:sonarsource|JFrog|Sonatype|Mend|FOSSA|Tidelift|Anchore|Stacklet|Fugue|Bridgecrew|Cyera|BigID|Securiti|OneTrust|TrustArc|Osano|
Ketch|Transcend|DataGrail|Skyflow|Very Good Security:verygoodsecurity|Evervault|Basis Theory:basistheory|Persona|Alloy|Sardine|Socure|Onfido|Veriff|Jumio|Trulioo|
Unit|Treasury Prime|Synctera|Column|Lithic|Highnote|Modern Treasury|Increase|Moov|Dwolla|Finix|Rainforest|Payabli|Tilled|Stax|Melio|Bill:billcom|Tipalti|
Airbase|Zip:ziphq|Coupa|Procurify|Vendr|Tropic|Sastrify|Cledara|Zluri|Torii|BetterCloud|Productiv|Lumos|Opal|ConductorOne|Veza|Oort|Astrix|Grip Security"""

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
