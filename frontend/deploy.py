#!/usr/bin/env python3
"""RED-MIND frontend deploy — frontend/ se Vercel par.
Usage: VERCEL_TOKEN=<token> python3 frontend/deploy.py
(aggar token env mein nahi hai to niche wala default use hota hai)

AGENT-C addition: PWA assets (manifest.json, sw.js, icons/*.png) bhi upload
hote hain. Icons pure-stdlib PNG encoder se generate hote hain — koi Pillow /
NPM dependency nahi ($0).
"""
import hashlib, json, os, sys, time, urllib.request, urllib.error, zlib, struct

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

# ---------------------------------------------------------------------
# Pure-stdlib PNG icon generator — RED-MIND brand mark:
# dark backdrop + red ring + glowing white "mind" core.
# ---------------------------------------------------------------------
def _png(path, size, pixel_fn):
    def chunk(tag, data):
        c = struct.pack(">I", len(data)) + tag + data
        c += struct.pack(">I", zlib.crc32(tag + data) & 0xffffffff)
        return c
    ihdr = struct.pack(">IIBBBBB", size, size, 8, 6, 0, 0, 0)  # 8-bit RGBA
    raw = bytearray()
    for y in range(size):
        raw.append(0)  # filter: None
        for x in range(size):
            r, g, b, a = pixel_fn(x, y)
            raw += bytes((r & 255, g & 255, b & 255, a & 255))
    png = (b"\x89PNG\r\n\x1a\n" + chunk(b"IHDR", ihdr)
           + chunk(b"IDAT", zlib.compress(bytes(raw), 9)) + chunk(b"IEND", b""))
    with open(path, "wb") as f:
        f.write(png)

def _rm_pixel(size):
    def fn(x, y):
        cx = (x / float(size)) - 0.5
        cy = (y / float(size)) - 0.5
        d = (cx * cx + cy * cy) ** 0.5
        r, g, b = 10, 10, 14            # brand background
        ring = 0.36                     # red ring (brand colour)
        if abs(d - ring) < 0.045:
            t = 1.0 - abs(d - ring) / 0.045
            r, g, b = int(225 * t + 10 * (1 - t)), int(29 * t + 10 * (1 - t)), int(50 * t + 14 * (1 - t))
        if d < 0.22:                    # white-hot core
            k = 1.0 - (d / 0.22)        # 1 at centre -> 0 at edge
            # soft white core with a faint red inner glow toward the edge
            base = int(232 + 23 * k)
            warm = int(120 * (1 - k))   # red tint as it fades out
            r = base; g = int(base - (base - 20) * (1 - k)); b = int(base - (base - 20) * (1 - k))
            r = max(r, warm)
        return (r & 255, g & 255, b & 255, 255)
    return fn

def ensure_icons():
    os.makedirs(os.path.join(HERE, "icons"), exist_ok=True)
    made = []
    for size in (192, 512):
        p = os.path.join(HERE, "icons", f"icon-{size}.png")
        if not os.path.exists(p) or os.path.getsize(p) == 0 or os.path.getsize(p) < 500:
            _png(p, size, _rm_pixel(size))
            made.append(os.path.basename(p))
    return made

def main():
    made_icons = ensure_icons()
    print(f"icons generated: {made_icons or 'already present'}")
    tpl = open(os.path.join(HERE, "index.template.html"), "rb").read()
    files = {
        "index.html": tpl,
        "vercel.json": open(os.path.join(HERE, "vercel.json"), "rb").read(),
        "img/hero.jpg": open(os.path.join(HERE, "img", "hero.jpg"), "rb").read(),
        "img/core.jpg": open(os.path.join(HERE, "img", "core.jpg"), "rb").read(),
        "img/games.jpg": open(os.path.join(HERE, "img", "games.jpg"), "rb").read(),
        # --- PWA (AGENT-C) ---
        "manifest.json": open(os.path.join(HERE, "manifest.json"), "rb").read(),
        "sw.js": open(os.path.join(HERE, "sw.js"), "rb").read(),
        "icons/icon-192.png": open(os.path.join(HERE, "icons", "icon-192.png"), "rb").read(),
        "icons/icon-512.png": open(os.path.join(HERE, "icons", "icon-512.png"), "rb").read(),
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
