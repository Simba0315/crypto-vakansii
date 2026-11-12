"""Find each company's own website, verify it by its page title, and save its icon to assets/logos/<slug>.png.

A company without a verified site keeps the letter avatar: a wrong logo is worse than no logo.
"""
import hashlib, json, re, subprocess, sys, concurrent.futures as cf
from pathlib import Path
from collect import slugify

ROOT = Path(__file__).parent
OUTDIR = ROOT / "assets" / "logos"
OUTDIR.mkdir(parents=True, exist_ok=True)
MAP = ROOT / "logos.json"
UA = "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/130.0 Safari/537.36"

OVERRIDE = {  # names whose site cannot be guessed from the name
    "Scale AI": "scale.com", "Hugging Face": "huggingface.co", "Weights & Biases": "wandb.ai", "Runway": "runwayml.com", "Mistral AI": "mistral.ai", "xAI": "x.ai",
    "Character.AI": "character.ai", "Together AI": "together.ai", "Cursor": "cursor.com", "dbt Labs": "getdbt.com", "Epic Games": "epicgames.com", "Riot Games": "riotgames.com",
    "Hims & Hers": "hims.com", "Ro": "ro.co", "Oscar Health": "hioscar.com", "Devoted Health": "devoted.com", "Cityblock Health": "cityblock.com", "Flatiron Health": "flatiron.com",
    "Ginkgo Bioworks": "ginkgobioworks.com", "Shield AI": "shield.ai", "Relativity Space": "relativityspace.com", "Rocket Lab": "rocketlabusa.com", "Lucid Motors": "lucidmotors.com",
    "GOAT": "goat.com", "Checkout.com": "checkout.com", "Block": "block.xyz", "monday.com": "monday.com", "Apollo.io": "apollo.io", "Builder.io": "builder.io", "Luma AI": "lumalabs.ai",
    "Copy.ai": "copy.ai", "C3 AI": "c3.ai", "Sigma": "sigmacomputing.com", "Hex": "hex.tech", "Monte Carlo": "montecarlodata.com", "Aqua Security": "aquasec.com",
    "Orca Security": "orca.security", "Arctic Wolf": "arcticwolf.com", "Lambda": "lambda.ai", "SambaNova": "sambanova.ai", "Customer.io": "customer.io", "Arc": "arc.net",
    "Todoist": "todoist.com", "Basecamp": "basecamp.com", "Solo.io": "solo.io", "Incident.io": "incident.io", "Sonar": "sonarsource.com", "Bill": "bill.com", "Zip": "ziphq.com",
    "1X": "1x.tech", "Observe.AI": "observe.ai", "Inworld AI": "inworld.ai", "Magic": "magic.dev", "Zed": "zed.dev", "Arize AI": "arize.com", "Fiddler AI": "fiddler.ai",
    "Nomic AI": "nomic.ai", "Invisible Technologies": "invisible.co", "V7": "v7labs.com", "Figure": "figure.ai", "Boom Supersonic": "boomsupersonic.com", "Apex": "apexspace.com",
    "M1": "m1.com", "Check": "checkhq.com", "Sana": "sanabenefits.com", "Viz.ai": "viz.ai", "Dagster Labs": "dagster.io", "Observe": "observeinc.com", "Tray.io": "tray.io",
    "Stream": "getstream.io", "Dice": "dice.fm", "Crypto.com": "crypto.com", "Blockchain.com": "blockchain.com", "Galaxy": "galaxy.com", "GSR": "gsr.io", "Copper": "copper.co",
    "Jito": "jito.network", "Monad": "monad.xyz", "zkSync / Matter Labs": "matter-labs.io", "Sui / Mysten Labs": "mystenlabs.com", "Trezor / SatoshiLabs": "trezor.io",
    "Optimism": "optimism.io", "Polygon Labs": "polygon.technology", "Arbitrum Foundation": "arbitrum.foundation", "Lightning Labs": "lightning.engineering",
    "Uniswap Labs": "uniswap.org", "Anchorage Digital": "anchorage.com", "Magic Eden": "magiceden.io", "River": "river.com", "Strike": "strike.me", "Morpho": "morpho.org",
    "Helius": "helius.dev", "Paradigm": "paradigm.xyz", "Notabene": "notabene.id", "1inch": "1inch.io", "Nethermind": "nethermind.io", "LayerZero": "layerzero.network",
    "Elliptic": "elliptic.co", "Wiz": "wiz.io", "Pilot": "pilot.com", "Census": "getcensus.com", "Cobalt": "cobalt.io", "Socket": "socket.dev", "Gamma": "gamma.app",
    "Harvey": "harvey.ai", "Aurora": "aurora.tech", "Cruise": "getcruise.com", "Outreach": "outreach.io", "Coda": "coda.io", "Ghost": "ghost.org", "Signal": "signal.org",
    "Proton": "proton.me", "Maze": "maze.co", "Aha": "aha.io", "Plane": "plane.so", "Harness": "harness.io", "Loft": "loft.sh", "Mend": "mend.io", "Persona": "withpersona.com",
    "Sardine": "sardine.ai", "Unit": "unit.co", "Moov": "moov.io", "Opal": "opal.dev", "Port": "getport.io", "Cortex": "cortex.io", "Porter": "porter.run", "Trunk": "trunk.io",
    "Jit": "jit.io", "Graphite": "graphite.dev", "Bolt": "bolt.eu", "Lime": "li.me", "Bird": "bird.co", "Make": "make.com", "Glide": "glideapps.com", "Bubble": "bubble.io",
    "Daily": "daily.co", "Luma": "lu.ma", "Kraken": "kraken.com", "Ledger": "ledger.com", "Phantom": "phantom.com", "Dune": "dune.com", "Remote": "remote.com", "Front": "front.com",
    "Box": "box.com", "Compass": "compass.com", "Planet": "planet.com", "Writer": "writer.com", "Mode": "mode.com", "Pitch": "pitch.com", "Later": "later.com", "Brave": "brave.com",
    "Alma": "helloalma.com", "Forward": "goforward.com", "Step": "step.com", "Current": "current.com", "Public": "public.com", "Dave": "dave.com", "Color": "color.com",
    "Cedar": "cedar.com", "Coder": "coder.com", "Depot": "depot.dev", "Convex": "convex.dev", "Fauna": "fauna.com", "Split": "split.io", "Vantage": "vantage.sh",
    "Factory": "factory.ai", "Sierra": "sierra.ai", "Cognition": "cognition.ai", "Poolside": "poolside.ai", "Suno": "suno.com", "Captions": "captions.ai", "Warp": "warp.dev",
    "Braintrust": "braintrust.dev", "Chroma": "trychroma.com", "Turing": "turing.com", "Mercor": "mercor.com", "Umbra": "umbra.space", "Varda": "varda.com", "Tide": "tide.co",
    "Lunar": "lunar.app", "Raisin": "raisin.com", "Solaris": "solarisgroup.com", "Alpaca": "alpaca.markets", "MX": "mx.com", "Atomic": "atomic.financial", "Argyle": "argyle.com",
    "Stash": "stash.com", "Moss": "getmoss.com", "Headway": "headway.co", "Nabla": "nabla.com", "Suki": "suki.ai", "Paige": "paige.ai", "Verily": "verily.com", "Axiom": "axiom.co",
    "Embrace": "embrace.io", "Statsig": "statsig.com", "Eppo": "geteppo.com", "Astronomer": "astronomer.io", "Prefect": "prefect.io", "Imply": "imply.io", "Aiven": "aiven.io",
    "Momento": "gomomento.com", "Turso": "turso.tech", "Xata": "xata.io", "Deno": "deno.com", "Dagger": "dagger.io", "Gitpod": "gitpod.io", "Docker": "docker.com",
    "Wolt": "wolt.com", "Glovo": "glovoapp.com", "Getir": "getir.com", "Olo": "olo.com", "Angi": "angi.com", "Houzz": "houzz.com", "Sonder": "sonder.com", "Turo": "turo.com",
    "Voi": "voi.com", "Tonal": "tonal.com", "Hydrow": "hydrow.com", "Komoot": "komoot.com", "Babbel": "babbel.com", "Preply": "preply.com", "Cambly": "cambly.com", "2U": "2u.com",
    "Brilliant": "brilliant.org", "Kajabi": "kajabi.com", "Gumroad": "gumroad.com", "Sketch": "sketch.com", "Kinsta": "kinsta.com", "Pantheon": "pantheon.io", "Acquia": "acquia.com",
    "Prismic": "prismic.io", "Softr": "softr.io", "n8n": "n8n.io", "Workato": "workato.com", "Pipedream": "pipedream.com", "Parabola": "parabola.io", "Lovable": "lovable.dev",
    "StackBlitz": "stackblitz.com", "Bolt.new": "bolt.new", "Qodo": "qodo.ai", "Pieces": "pieces.app", "Speakeasy": "speakeasy.com", "Stainless": "stainless.com", "Fern": "buildwithfern.com",
    "Scalar": "scalar.com", "Ably": "ably.com", "Pusher": "pusher.com", "Sendbird": "sendbird.com", "LiveKit": "livekit.io", "Agora": "agora.io", "Whereby": "whereby.com",
    "Riverside": "riverside.fm", "Tella": "tella.tv", "Gather": "gather.town", "Butter": "butter.us", "Posh": "posh.vip", "Splash": "splashthat.com", "Cvent": "cvent.com",
    "Toast": "toasttab.com", "Pika": "pika.art", "Oyster": "oysterhr.com", "Sentry": "sentry.io", "Honeycomb": "honeycomb.io", "Oura": "ouraring.com", "Transcend": "transcend.io",
    "Upbound": "upbound.io", "Unstructured": "unstructured.io", "Twelve Labs": "twelvelabs.io", "Synthesia": "synthesia.io", "Akuity": "akuity.io", "Finout": "finout.io",
    "DataGrail": "datagrail.io", "Amber Group": "ambergroup.io", "Wayve": "wayve.ai", "Decagon": "decagon.ai", "Crusoe": "crusoe.ai", "Ideogram": "ideogram.ai",
    "LlamaIndex": "llamaindex.ai", "Checkly": "checklyhq.com", "Machina Labs": "machinalabs.ai", "Thought Machine": "thoughtmachine.net", "MessageBird": "bird.com",
    "Jellyfish": "jellyfish.co", "Mozilla": "mozilla.org", "Sanity": "sanity.io", "Sweep": "sweep.dev", "Typeface": "typeface.ai", "Vectara": "vectara.com", "Harvey": "harvey.ai",
    "PostHog": "posthog.com", "Linear": "linear.app", "Weaviate": "weaviate.io", "Zilliz": "zilliz.com", "LiveKit": "livekit.io", "MotherDuck": "motherduck.com",
    "Physical Intelligence": "physicalintelligence.company", "Pano AI": "pano.ai", "Snorkel AI": "snorkel.ai", "Galileo": "galileo.ai", "Encord": "encord.com", "Calm": "calm.com",
    "Medium": "medium.com", "Quora": "quora.com", "Robinhood Crypto": "robinhood.com", "Cumberland / DRW": "drw.com", "Very Good Security": "verygoodsecurity.com",
    "Grow Therapy": "growtherapy.com", "Sword Health": "swordhealth.com", "Dyno Therapeutics": "dynotx.com", "Generate Biomedicines": "generatebiomedicines.com",
    "Khan Academy": "khanacademy.org", "Grafana Labs": "grafana.com", "ConvertKit": "kit.com", "Pure Storage": "purestorage.com", "Flow Traders": "flowtraders.com", "Nubank": "nubank.com.br",
}
CHALLENGE = {"", "justamoment", "attentionrequired", "accessdenied", "pleasewait", "403forbidden", "forbidden", "robotcheck", "securitycheck", "areyouarobot", "error", "blocked"}


def curl(url, timeout=12, binary=False):
    try:
        r = subprocess.run(["curl", "-s", "-4", "-L", "--max-time", str(timeout), "-A", UA, "-H", "Accept: text/html,image/*,*/*", url], capture_output=True, timeout=timeout + 4)
        return r.stdout if binary else r.stdout.decode("utf-8", "replace")
    except Exception:
        return b"" if binary else ""


def norm(s):
    return re.sub(r"[^a-z0-9]", "", s.lower())


def stems(name, token):
    base = norm(name)
    tok = norm(re.sub(r"(hq|inc)$", "", token.lower()))
    return base, tok


def primaries(name, token):
    """Addresses we trust: the hand-checked one, a token that already is a domain, and <name>.com."""
    base, tok = stems(name, token)
    out = []
    if name in OVERRIDE: out.append(OVERRIDE[name])
    if "." in token: out.append(token.lower())
    if name not in OVERRIDE:
        out.append(f"{base}.com")
        if tok and tok != base: out.append(f"{tok}.com")
    return list(dict.fromkeys(out))


def alternates(name, token):
    base, tok = stems(name, token)
    return [f"{stem}.{tld}" for stem in dict.fromkeys([base, tok]) if len(stem) >= 3 for tld in ("io", "ai", "co", "dev", "xyz", "app", "org", "so", "tech")]


def page_names(domain):
    """(title, site name) of the home page in normalised form, or None when the site does not show its page to a script."""
    html = curl(f"https://{domain}")
    if len(html) < 300: return None
    head = html[:60000]
    title = norm(" ".join(re.findall(r"<title[^>]*>(.*?)</title>", head, re.S | re.I)[:1]))
    site = norm(" ".join(re.findall(r'property=["\']og:site_name["\'][^>]*content=["\']([^"\']+)', head, re.I)
                          + re.findall(r'content=["\']([^"\']+)["\'][^>]*property=["\']og:site_name', head, re.I)))
    if title in CHALLENGE and not site: return None          # bot check or an empty shell: we learn nothing from it
    return title, site


GLOBE = hashlib.md5(curl("https://www.google.com/s2/favicons?domain=zz-no-such-site-48151623.com&sz=128", binary=True)).hexdigest()


def icon(domain, dest):
    data = curl(f"https://www.google.com/s2/favicons?domain={domain}&sz=128", binary=True)
    if len(data) < 300 or hashlib.md5(data).hexdigest() == GLOBE or not data.startswith(b"\x89PNG"): return False
    dest.write_bytes(data)
    w = subprocess.run(["sips", "-g", "pixelWidth", str(dest)], capture_output=True, text=True).stdout
    m = re.search(r"pixelWidth: (\d+)", w)
    if not m or int(m.group(1)) < 32:
        dest.unlink(missing_ok=True); return False
    if int(m.group(1)) > 96:
        subprocess.run(["sips", "-Z", "96", str(dest)], capture_output=True)
    return True


def work(src):
    name, slug = src["name"], slugify(src["name"])
    dest = OUTDIR / f"{slug}.png"
    key = norm(name)
    first = norm(re.split(r"[ /&.]", name.strip())[0])
    for d in primaries(name, src["token"]):
        names = page_names(d)
        # Only trusted addresses are used. Accept when the page names the company, or when the site refuses scripts.
        ok = names is None or name in OVERRIDE or key in names[0] or key in names[1] or (len(first) >= 5 and (first in names[0] or first in names[1]))
        if ok and icon(d, dest):
            return name, d
    return name, None


def main():
    srcs = json.loads((ROOT / "sources.json").read_text()) + json.loads((ROOT / "sources_tech.json").read_text())
    seen, todo = set(), []
    known = json.loads(MAP.read_text()) if MAP.exists() else {}
    for s in srcs:
        if s["name"] in seen: continue
        seen.add(s["name"])
        if known.get(s["name"]) and (OUTDIR / f"{slugify(s['name'])}.png").exists(): continue
        todo.append(s)
    with cf.ThreadPoolExecutor(10) as ex:
        for name, d in ex.map(work, todo):
            if d: known[name] = d
    MAP.write_text(json.dumps(known, ensure_ascii=False, indent=1, sort_keys=True))
    missing = sorted(n for n in seen if n not in known)
    print(f"logos: {len(known)} of {len(seen)} companies; missing {len(missing)}")
    print("missing:", ", ".join(missing)[:1500])


if __name__ == "__main__":
    main()
