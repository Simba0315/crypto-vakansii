"""speedlab.py OUT_JSON [--runs N] [--net lh|raw] [--cpu 4] [--shots DIR] [--mod FILE.py] name=URL [name=URL ...]

Page speed on a phone, measured here when the PageSpeed Insights API's free daily quota is used up (26 Nov 2026). Needs Google
Chrome, websocket-client and Pillow; not used by the build. Example:
    python3 speedlab.py /tmp/speed.json --runs 3 home=https://jobseveryhour.com/ job=https://jobseveryhour.com/job/<slug>/
--mod FILE.py: FILE defines mod(url, resource_type, text) -> new text or None; responses are rewritten before the browser reads
them (try a change on the live pages before building it). The 8 GB Mac: one headless Chrome at a time, closed after each run.

Cold-load lab test in ONE headless Chrome (closed at the end). Each run uses a fresh browser context (empty cache, no
service worker). Phone: 412x823, DPR 2, mobile UA, touch, CPU throttled x4.
Network: --net lh (default) = Lighthouse's "devtools" values for 150 ms RTT / 1.6 Mbps (request latency 562.5 ms,
1.47 Mbps down, 675 kbps up); --net raw = 150 ms latency, 1.6 Mbps down, 750 kbps up.
Collects FCP, LCP (+element), CLS (session windows), TBT (long tasks after FCP), Speed Index (screencast histograms,
speedline method), TTFB, DCL, load, request count and transfer bytes (Network domain), render-blocking resources.
Prints a table and a Lighthouse-style score (v10 mobile curves and weights)."""
import base64, io, json, math, os, statistics, subprocess, sys, tempfile, time, urllib.request, shutil
import websocket
from PIL import Image

args = sys.argv[1:]
out = args.pop(0)
runs, net, cpu, shots, mod = 2, "lh", 4.0, None, None
pages = []
while args:
    a = args.pop(0)
    if a == "--runs": runs = int(args.pop(0))
    elif a == "--net": net = args.pop(0)
    elif a == "--cpu": cpu = float(args.pop(0))
    elif a == "--shots": shots = args.pop(0); os.makedirs(shots, exist_ok=True)
    elif a == "--mod":     # a python file defining mod(url, rtype, text) -> new text or None (rewrites live responses)
        _ns = {}; exec(open(args.pop(0)).read(), _ns); mod = _ns["mod"]
    else:
        k, v = a.split("=", 1); pages.append((k, v))

OBS = r"""
(()=>{const P=window.__perf={lcp:[],ls:[],lt:[],paint:{}};
try{new PerformanceObserver(l=>{for(const e of l.getEntries()){let el=e.element,d='';
 if(el){d=el.tagName.toLowerCase()+(el.id?'#'+el.id:'')+(el.className&&typeof el.className=='string'?'.'+el.className.trim().split(/\s+/).join('.'):'');
 d+=' '+(el.textContent||'').trim().slice(0,60).replace(/\s+/g,' ');}
 P.lcp.push({t:e.startTime,size:e.size,url:e.url||'',el:d,rt:e.renderTime,lt:e.loadTime});}}).observe({type:'largest-contentful-paint',buffered:true});}catch(e){}
try{new PerformanceObserver(l=>{for(const e of l.getEntries()){if(!e.hadRecentInput){let s=(e.sources||[]).map(x=>x.node?(x.node.nodeName+(x.node.className&&typeof x.node.className=='string'?'.'+x.node.className.trim().split(/\s+/)[0]:'')):'').join(',');P.ls.push({t:e.startTime,v:e.value,s:s});}}}).observe({type:'layout-shift',buffered:true});}catch(e){}
try{new PerformanceObserver(l=>{for(const e of l.getEntries())P.lt.push({t:e.startTime,d:e.duration,a:(e.attribution||[]).map(x=>x.containerSrc||x.name).join(',')});}).observe({type:'longtask',buffered:true});}catch(e){}
try{new PerformanceObserver(l=>{for(const e of l.getEntries())P.paint[e.name]=e.startTime;}).observe({type:'paint',buffered:true});}catch(e){}
})();
"""
COLLECT = r"""
(()=>{const P=window.__perf||{};const n=performance.getEntriesByType('navigation')[0]||{};
const res=performance.getEntriesByType('resource').map(e=>({u:e.name,ty:e.initiatorType,tr:e.transferSize,enc:e.encodedBodySize,dec:e.decodedBodySize,rb:e.renderBlockingStatus||'',s:e.startTime,e:e.responseEnd}));
return JSON.stringify({P:P,origin:performance.timeOrigin,nav:{ttfb:n.responseStart,dcl:n.domContentLoadedEventEnd,load:n.loadEventEnd,tr:n.transferSize,dec:n.decodedBodySize,rb:n.renderBlockingStatus},res:res,
 dom:document.getElementsByTagName('*').length,h:document.documentElement.scrollHeight});})()
"""

def erf(x):
    return math.erf(x)

def lhscore(value, p10, median):
    if value <= 0: return 1.0
    INV = 0.9061938024368232
    x = math.log(max(value / median, 1e-300)) * INV / (-math.log(p10 / median))
    s = (1 - erf(x)) / 2
    return min(1.0, max(0.0, s))

CURVES = {"fcp": (1800, 3000, .10), "si": (3387, 5800, .10), "lcp": (2500, 4000, .25), "tbt": (200, 600, .30), "cls": (0.1, 0.25, .25)}

def score(m):
    tot = 0
    for k, (p10, med, w) in CURVES.items():
        tot += w * lhscore(m[k], p10, med)
    return round(tot * 100)

def hist(img):
    h = img.convert("RGB").histogram()
    return [h[0:256], h[256:512], h[512:768]]

def progress(cur, ini, tgt):
    total = match = 0
    for c in range(3):
        for v in range(256):
            cd = abs(cur[c][v] - ini[c][v]); td = abs(tgt[c][v] - ini[c][v])
            match += min(cd, td); total += td
    return 1.0 if total == 0 else match / total

port = 9561
prof = tempfile.mkdtemp(prefix="cdpperf")
chrome = subprocess.Popen(["/Applications/Google Chrome.app/Contents/MacOS/Google Chrome", "--headless=new", "--hide-scrollbars",
                           "--no-first-run", "--no-default-browser-check", "--disable-extensions", "--mute-audio",
                           f"--user-data-dir={prof}", f"--remote-debugging-port={port}", "about:blank"],
                          stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
results = {}
try:
    ver = None
    for _ in range(100):
        try:
            ver = json.load(urllib.request.urlopen(f"http://127.0.0.1:{port}/json/version")); break
        except Exception: time.sleep(0.2)
    ws = websocket.create_connection(ver["webSocketDebuggerUrl"], timeout=120, max_size=None)
    seq = [0]; events = []
    def call(method, sid=None, **params):
        seq[0] += 1; msg = {"id": seq[0], "method": method, "params": params}
        if sid: msg["sessionId"] = sid
        ws.send(json.dumps(msg))
        while True:
            m = json.loads(ws.recv())
            if m.get("id") == seq[0]:
                if "error" in m: raise RuntimeError(f"{method}: {m['error']}")
                return m.get("result", {})
            events.append(m)
    def pump(timeout):
        ws.settimeout(timeout)
        try:
            m = json.loads(ws.recv()); events.append(m); return m
        except websocket.WebSocketTimeoutException:
            return None
        finally:
            ws.settimeout(120)

    for name, url in pages:
        allruns = []
        for r in range(runs):
            events.clear()
            ctx = call("Target.createBrowserContext", disposeOnDetach=True)["browserContextId"]
            tid = call("Target.createTarget", url="about:blank", browserContextId=ctx)["targetId"]
            sid = call("Target.attachToTarget", targetId=tid, flatten=True)["sessionId"]
            call("Page.enable", sid); call("Network.enable", sid)
            call("Emulation.setDeviceMetricsOverride", sid, width=412, height=823, deviceScaleFactor=2, mobile=True)
            call("Emulation.setTouchEmulationEnabled", sid, enabled=True, maxTouchPoints=5)
            call("Emulation.setUserAgentOverride", sid, userAgent="Mozilla/5.0 (Linux; Android 11; moto g power (2022)) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/130.0.0.0 Mobile Safari/537.36")
            call("Emulation.setCPUThrottlingRate", sid, rate=cpu)
            if net == "lh":
                call("Network.emulateNetworkConditions", sid, offline=False, latency=562.5, downloadThroughput=1474.56 * 1024 / 8, uploadThroughput=675 * 1024 / 8)
            else:
                call("Network.emulateNetworkConditions", sid, offline=False, latency=150, downloadThroughput=1.6 * 1024 * 1024 / 8, uploadThroughput=750 * 1024 / 8)
            call("Page.addScriptToEvaluateOnNewDocument", sid, source=OBS)
            if mod:
                call("Fetch.enable", sid, patterns=[{"urlPattern": "*", "requestStage": "Response"}])
            call("Page.startScreencast", sid, format="jpeg", quality=50, maxWidth=206, maxHeight=412, everyNthFrame=1)
            frames = []; reqs = {}; done = {}
            t_start = time.time()
            seq[0] += 1; ws.send(json.dumps({"id": seq[0], "method": "Page.navigate", "sessionId": sid, "params": {"url": url}}))   # no wait: a paused response would block it
            loaded = None; last_net = time.time()
            def handle(m):
                meth = m.get("method", "")
                p = m.get("params", {})
                if m.get("sessionId") != sid: return
                if meth == "Fetch.requestPaused":
                    rid = p["requestId"]; new = None
                    try:
                        if p.get("responseStatusCode") == 200 and p.get("resourceType") in ("Document", "Stylesheet", "Script"):
                            b = call("Fetch.getResponseBody", sid, requestId=rid)
                            txt = base64.b64decode(b["body"]).decode("utf-8") if b.get("base64Encoded") else b["body"]
                            new = mod(p["request"]["url"], p["resourceType"], txt)
                    except Exception as ex: print("mod error", ex)
                    if new is None: call("Fetch.continueRequest", sid, requestId=rid)
                    else:
                        hd = [h for h in p.get("responseHeaders", []) if h["name"].lower() not in ("content-encoding", "content-length")]
                        call("Fetch.fulfillRequest", sid, requestId=rid, responseCode=200, responseHeaders=hd, body=base64.b64encode(new.encode()).decode())
                elif meth == "Page.screencastFrame":
                    frames.append((p["metadata"]["timestamp"], p["data"]))
                    ws.send(json.dumps({"id": 10**9 + len(frames), "method": "Page.screencastFrameAck", "sessionId": sid, "params": {"sessionId": p["sessionId"]}}))
                elif meth == "Network.requestWillBeSent":
                    reqs[p["requestId"]] = {"url": p["request"]["url"], "type": p.get("type", ""), "prio": p["request"].get("initialPriority", "")}
                elif meth == "Network.responseReceived":
                    reqs.setdefault(p["requestId"], {})["status"] = p["response"].get("status"); reqs[p["requestId"]]["mime"] = p["response"].get("mimeType")
                    reqs[p["requestId"]]["type"] = p.get("type", reqs[p["requestId"]].get("type", ""))
                elif meth == "Network.loadingFinished":
                    done[p["requestId"]] = p.get("encodedDataLength", 0)
                elif meth == "Network.loadingFailed":
                    done[p["requestId"]] = 0; reqs.setdefault(p["requestId"], {})["failed"] = p.get("errorText")
            i = 0
            while True:
                while i < len(events):
                    m = events[i]; i += 1
                    handle(m)
                    if m.get("method") == "Page.loadEventFired" and m.get("sessionId") == sid and loaded is None: loaded = time.time()
                    if m.get("method", "").startswith("Network.") and m.get("sessionId") == sid: last_net = time.time()
                now = time.time()
                if loaded and now - loaded > 5 and now - last_net > 3: break
                if now - t_start > 45: break
                pump(0.5)
            # drain
            while i < len(events): handle(events[i]); i += 1
            call("Page.stopScreencast", sid)
            raw = call("Runtime.evaluate", sid, expression=COLLECT, returnByValue=True)["result"]["value"]
            while i < len(events): handle(events[i]); i += 1
            d = json.loads(raw)
            P = d["P"]; origin = d["origin"]
            fcp = P.get("paint", {}).get("first-contentful-paint", 0)
            lcp_e = P["lcp"][-1] if P["lcp"] else {"t": fcp, "el": "?", "url": "", "size": 0}
            # CLS: session windows (gap < 1 s, window < 5 s), max window
            cls = 0; win = 0; ws_start = None; prev = None
            for e in sorted(P["ls"], key=lambda e: e["t"]):
                if prev is not None and (e["t"] - prev > 1000 or e["t"] - ws_start > 5000):
                    win = 0; ws_start = e["t"]
                if ws_start is None: ws_start = e["t"]
                win += e["v"]; prev = e["t"]; cls = max(cls, win)
            tbt = sum(max(0, lt["d"] - 50) for lt in P["lt"] if lt["t"] + lt["d"] > fcp)
            # Speed Index
            si = 0
            try:
                if frames:
                    imgs = [(ts * 1000 - origin, Image.open(io.BytesIO(base64.b64decode(b)))) for ts, b in frames]
                    imgs = [(t, im) for t, im in imgs if t >= 0]
                    white = Image.new("RGB", imgs[-1][1].size, (255, 255, 255)) if imgs else None
                    if imgs:
                        tgt = hist(imgs[-1][1]); ini = hist(white)
                        pts = [(0.0, 0.0)] + [(t, progress(hist(im), ini, tgt)) for t, im in imgs]
                        for (t0, p0), (t1, _) in zip(pts, pts[1:]):
                            si += (1 - p0) * (t1 - t0)
            except Exception as ex:
                si = -1; print("SI error", ex)
            si = max(si, fcp)
            total_bytes = sum(done.get(k, 0) for k in reqs)
            bytypes = {}
            for k, q in reqs.items():
                ty = q.get("type", "?"); bytypes.setdefault(ty, [0, 0]); bytypes[ty][0] += 1; bytypes[ty][1] += done.get(k, 0)
            rb = [x["u"] for x in d["res"] if x.get("rb") == "blocking"]
            m = {"fcp": fcp, "lcp": lcp_e["t"], "cls": cls, "tbt": tbt, "si": si, "ttfb": d["nav"]["ttfb"], "dcl": d["nav"]["dcl"], "load": d["nav"]["load"],
                 "html_tr": d["nav"]["tr"], "html_dec": d["nav"]["dec"], "reqs": len(reqs), "bytes": total_bytes, "types": bytypes, "blocking": rb,
                 "lcp_el": lcp_e.get("el", ""), "lcp_url": lcp_e.get("url", ""), "lcp_size": lcp_e.get("size", 0),
                 "longtasks": sorted(P["lt"], key=lambda x: -x["d"])[:8], "shifts": sorted(P["ls"], key=lambda x: -x["v"])[:6],
                 "dom": d["dom"], "height": d["h"],
                 "reqlist": sorted([(done.get(k, 0), q.get("type"), q.get("url", "")[:140], q.get("prio", "")) for k, q in reqs.items()], reverse=True)[:40]}
            m["score"] = score(m)
            if shots and r == 0:
                try:
                    s = call("Page.captureScreenshot", sid, format="png")
                    open(os.path.join(shots, f"{name}.png"), "wb").write(base64.b64decode(s["data"]))
                except Exception as ex: print("shot error", ex)
            allruns.append(m)
            print(f"{name:10} run{r+1} score {m['score']:3}  FCP {fcp/1000:.2f}  LCP {m['lcp']/1000:.2f}  SI {si/1000:.2f}  TBT {tbt:.0f}  CLS {cls:.3f}  "
                  f"TTFB {m['ttfb']:.0f}  req {m['reqs']}  {total_bytes/1024:.0f} KB  html {m['html_tr']/1024:.0f}/{m['html_dec']/1024:.0f} KB  LCP={m['lcp_el'][:50]}", flush=True)
            try: call("Target.closeTarget", targetId=tid)
            except Exception: pass
            try: call("Target.disposeBrowserContext", browserContextId=ctx)
            except Exception: pass
        med = {k: statistics.median([x[k] for x in allruns]) for k in ("fcp", "lcp", "cls", "tbt", "si", "ttfb", "reqs", "bytes", "html_tr", "html_dec", "score")}
        results[name] = {"url": url, "median": med, "runs": allruns}
finally:
    try: ws.close()
    except Exception: pass
    chrome.terminate()
    try: chrome.wait(8)
    except Exception: chrome.kill()
    shutil.rmtree(prof, ignore_errors=True)

json.dump({"net": net, "cpu": cpu, "runs": runs, "pages": results}, open(out, "w"), indent=1)
print("\nmedians (" + net + f", cpu x{cpu:g}, {runs} runs)")
print(f"{'page':10} {'score':>5} {'FCP':>5} {'LCP':>5} {'SI':>5} {'TBT':>5} {'CLS':>6} {'TTFB':>5} {'req':>4} {'KB':>5} {'html KB':>9}")
for name, r in results.items():
    m = r["median"]
    print(f"{name:10} {m['score']:5.0f} {m['fcp']/1000:5.2f} {m['lcp']/1000:5.2f} {m['si']/1000:5.2f} {m['tbt']:5.0f} {m['cls']:6.3f} {m['ttfb']:5.0f} {m['reqs']:4.0f} {m['bytes']/1024:5.0f} {m['html_tr']/1024:4.0f}/{m['html_dec']/1024:<4.0f}")
