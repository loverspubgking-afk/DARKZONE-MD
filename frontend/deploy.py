#!/usr/bin/env python3
"""RED-MIND frontend deploy — frontend/ se Vercel par.
Usage: VERCEL_TOKEN=<token> python3 frontend/deploy.py
(aggar token env mein nahi hai to niche wala default use hota hai)
"""
import hashlib, json, os, sys, time, urllib.request, urllib.error

HERE = os.path.dirname(os.path.abspath(__file__))
TOKEN = os.environ.get("VERCEL_TOKEN", "")
if not TOKEN: sys.exit("VERCEL_TOKEN env var do (brief mein hai)")
API = "https://api.vercel.com"

def api(path, data=None, method="GET", headers=None, raw=False):
    h = {"Authorization": "Bearer " + TOKEN}
    if headers: h.update(headers)
    body = None
    if data is not None:
        body = data if raw else json.dumps(data).encode()
        if not raw: h["Content-Type"] = "application/json"
    req = urllib.request.Request(API + path, data=body, headers=h, method=method)
    try:
        with urllib.request.urlopen(req, timeout=90) as r:
            rr = r.read().decode()
            try: return r.status, json.loads(rr)
            except: return r.status, rr[:200]
    except urllib.error.HTTPError as e:
        return e.code, e.read().decode()[:800]

def main():
    # index.html = template (woh already img/*.jpg refer karta hai)
    tpl = open(os.path.join(HERE, "index.template.html"), "rb").read()
    files = {
        "index.html": tpl,
        "vercel.json": open(os.path.join(HERE, "vercel.json"), "rb").read(),
        "img/hero.jpg": open(os.path.join(HERE, "img", "hero.jpg"), "rb").read(),
        "img/core.jpg": open(os.path.join(HERE, "img", "core.jpg"), "rb").read(),
        "img/games.jpg": open(os.path.join(HERE, "img", "games.jpg"), "rb").read(),
    }
    manifest = []
    for name, content in files.items():
        sha = hashlib.sha1(content).hexdigest()
        st, _ = api("/v2/files", data=content, method="POST",
                    headers={"Content-Type": "application/octet-stream", "x-vercel-digest": sha}, raw=True)
        print(f"upload {name}: {st} ({len(content)//1024} KB)")
        if st >= 400: sys.exit(f"upload fail: {name}")
        manifest.append({"file": name, "sha": sha})
    st, resp = api("/v13/deployments", data={"name": "redminde", "files": manifest, "target": "production"}, method="POST")
    print("deploy:", st)
    if st >= 400: sys.exit(str(resp)[:400])
    dep = resp["id"]
    for i in range(40):
        time.sleep(2)
        _, r2 = api("/v13/deployments/" + dep)
        state = r2.get("readyState") if isinstance(r2, dict) else "?"
        if state in ("READY", "ERROR", "CANCELED"): break
    print("state:", state, "| https://redminde.vercel.app")

if __name__ == "__main__":
    main()
