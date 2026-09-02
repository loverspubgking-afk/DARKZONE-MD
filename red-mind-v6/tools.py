"""
tools.py — RED-MIND v6 — naye tools, fresh implementations
==========================================================
Ek tool = ek chhota kaam. Sab kuch actually execute hota hai.
"""
import ast
import datetime
import json
import os
import platform
import re
import subprocess
import urllib.parse

import httpx

FILES_DIR = "files"
os.makedirs(FILES_DIR, exist_ok=True)

UA = {"User-Agent": "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0 Safari/537.36"}


# ---------------- SEARCH / WEB ----------------

def web_search(query: str, num_results: int = 6) -> str:
    """DuckDuckGo search. Args: query, num_results (optional)"""
    from bs4 import BeautifulSoup
    r = httpx.post("https://html.duckduckgo.com/html/", data={"q": query},
                   headers=UA, timeout=25.0, follow_redirects=True)
    soup = BeautifulSoup(r.text, "html.parser")
    out = []
    for res in soup.select(".result")[:int(num_results or 6)]:
        a = res.select_one(".result__a")
        sn = res.select_one(".result__snippet")
        if not a:
            continue
        link = a.get("href", "")
        m = re.search(r"uddg=([^&]+)", link)
        if m:
            link = urllib.parse.unquote(m.group(1))
        out.append(f"• {a.get_text(strip=True)}\n  {link}\n  {sn.get_text(strip=True) if sn else ''}")
    return "\n\n".join(out) or "[kuch nahi mila]"


def fetch_url(url: str, max_chars: int = 5000) -> str:
    """Webpage ka text nikalo. Args: url, max_chars (optional)"""
    from bs4 import BeautifulSoup
    r = httpx.get(url, headers=UA, timeout=25.0, follow_redirects=True)
    soup = BeautifulSoup(r.text, "html.parser")
    for t in soup(["script", "style", "noscript"]):
        t.decompose()
    text = soup.get_text(separator="\n", strip=True)
    text = re.sub(r"\n{3,}", "\n\n", text)
    return text[:int(max_chars or 5000)]


def http_request(url: str, method: str = "GET", body=None, headers=None) -> str:
    """Raw HTTP request (APIs ke liye). Args: url, method, body, headers"""
    h = dict(headers) if isinstance(headers, dict) else {}
    kw = {"headers": h, "timeout": 30.0, "follow_redirects": True}
    if body is not None:
        kw["json" if isinstance(body, (dict, list)) else "content"] = body
    r = httpx.request((method or "GET").upper(), url, **kw)
    return f"STATUS {r.status_code}\n\n{r.text[:3000]}"


def wikipedia_search(query: str) -> str:
    """Wikipedia search (3 results). Args: query"""
    r = httpx.get("https://en.wikipedia.org/w/api.php", params={
        "action": "query", "list": "search", "srsearch": query,
        "format": "json", "srlimit": 3}, timeout=20.0)
    rows = []
    for s in r.json().get("query", {}).get("search", []):
        rows.append(f"• {s['title']}\n  https://en.wikipedia.org/wiki/{s['title'].replace(' ', '_')}\n  {s.get('snippet', '')[:180]}")
    return "\n\n".join(rows) or "[nahi mila]"


def youtube_search(query: str, count: int = 5) -> str:
    """YouTube search. Args: query, count (optional)"""
    r = httpx.get(f"https://www.youtube.com/results?search_query={urllib.parse.quote(query)}",
                  headers=UA, timeout=20.0)
    m = re.search(r"var ytInitialData = ({.*?});</script>", r.text)
    if not m:
        return "[YouTube data parse fail]"
    data = json.loads(m.group(1))
    vids = data.get("contents", {}).get("twoColumnSearchResultsRenderer", {}) \
              .get("primaryContents", {}).get("sectionListRenderer", {}).get("contents", [])
    out = []
    for sec in vids:
        for v in sec.get("itemSectionRenderer", {}).get("contents", []):
            vr = v.get("videoRenderer")
            if vr and len(out) < int(count or 5):
                out.append(f"• {vr.get('title', {}).get('runs', [{}])[0].get('text', '?')}\n  https://youtube.com/watch?v={vr.get('videoId')}")
    return "\n".join(out) or "[kuch nahi mila]"


def weather(city: str) -> str:
    """Mausam. Args: city"""
    r = httpx.get(f"https://wttr.in/{urllib.parse.quote(city)}?format=j1", timeout=20.0)
    c = r.json().get("current_condition", [{}])[0]
    return (f"{city}: {c.get('temp_C')}°C, feels {c.get('FeelsLikeC')}°C, "
            f"{c.get('weatherDesc', [{}])[0].get('value', '')}, humidity {c.get('humidity')}%, wind {c.get('windspeedKmph')} km/h")


# ---------------- SYSTEM / FILES ----------------

_KILL_GUARD = re.compile(
    r"rm\s+-rf\s+/(?:\s|$)|kill(all)?\s+(-9\s+)?(python|uvicorn|ollama|server|cloudflared)"
    r"|pkill\s+(python|uvicorn|ollama|server|cloudflared)"
    r"|shutdown|reboot|mkfs|:\(\)\{", re.I)


def run_shell(command: str, timeout: int = 300) -> str:
    """Terminal command. Installations ke liye timeout=600 do. Args: command, timeout (optional)"""
    if _KILL_GUARD.search(command or ""):
        return "[BLOCKED] Ye command server ko khud nuksan pahuncha sakti hai — allowed nahi."
    try:
        out = subprocess.run(command, shell=True, capture_output=True, text=True,
                              timeout=min(int(timeout or 300), 900))
        res = ""
        if out.stdout:
            res += out.stdout[:3500]
        if out.stderr:
            res += ("\n[STDERR]\n" + out.stderr[:1500])
        return (res or "[no output]").strip() + f"\n[exit {out.returncode}]"
    except subprocess.TimeoutExpired:
        return f"[TIMEOUT {timeout}s] Command chalti rahi — chhota task banao ya timeout barhao."


def read_file(path: str) -> str:
    """File parho. Args: path"""
    with open(path, "r", encoding="utf-8", errors="ignore") as f:
        return f.read()[:6000]


def write_file(path: str, content: str) -> str:
    """File likho. Args: path, content"""
    with open(path, "w", encoding="utf-8") as f:
        f.write(str(content))
    return f"OK — {path} mein {len(str(content))} chars likhe gaye"


def list_dir(path: str = ".") -> str:
    """Directory list. Args: path (optional)"""
    entries = sorted(os.listdir(path or "."))
    lines = []
    for e in entries[:80]:
        full = os.path.join(path or ".", e)
        tag = "/" if os.path.isdir(full) else f" ({os.path.getsize(full)} B)"
        lines.append(e + tag)
    return "\n".join(lines) or "[empty]"


def download_file(url: str, path: str = "") -> str:
    """File download. Args: url, path (optional)"""
    name = path or (url.split("/")[-1].split("?")[0] or "download.bin")
    name = os.path.join(FILES_DIR, os.path.basename(name))
    with httpx.stream("GET", url, timeout=180.0, follow_redirects=True) as r:
        if r.status_code != 200:
            return f"[HTTP {r.status_code}]"
        total = 0
        with open(name, "wb") as f:
            for chunk in r.iter_bytes():
                f.write(chunk)
                total += len(chunk)
    return f"OK — {name} ({total} bytes)"


def system_info() -> str:
    """Server report. Args: (koi nahi)"""
    import shutil
    disk = shutil.disk_usage("/")
    return (f"OS: {platform.system()} {platform.release()}\nCPU: {os.cpu_count()} cores"
            f"\nRAM ~free: {open('/proc/meminfo').readline().strip() if os.path.exists('/proc/meminfo') else '?'}"
            f"\nDisk: {disk.free // (1024**3)}/{disk.total // (1024**3)} GB free"
            f"\nPython: {platform.python_version()}\nTime: {datetime.datetime.now()}")


def now() -> str:
    """Abhi ka time. Args: (koi nahi)"""
    return datetime.datetime.now().strftime("%A, %d %B %Y — %H:%M:%S")


# ---------------- CALC (safe AST) ----------------

def calculator(expression: str) -> str:
    """Math calculate. Args: expression (jaise 2+2*10)"""
    expr = re.sub(r"[^0-9+\-*/().% ]", "", expression)
    if not expr.strip():
        return "[invalid expression]"
    try:
        tree = ast.parse(expr, mode="eval")
        for node in ast.walk(tree):
            if not isinstance(node, (ast.Expression, ast.BinOp, ast.UnaryOp, ast.Constant,
                                    ast.Add, ast.Sub, ast.Mult, ast.Div, ast.Mod, ast.USub, ast.UAdd)):
                return "[sirf + - * / % allowed]"
        val = eval(compile(tree, "<calc>", "eval"), {"__builtins__": {}}, {})
        return f"{expression} = {val}"
    except Exception as e:
        return f"[calc error] {e}"


# ---------------- CREATIVE ----------------

def generate_image(prompt: str, width: int = 768, height: int = 768) -> str:
    """AI image banao (files/ folder mein save hoti hai). Args: prompt (English best), width, height (optional)"""
    url = (f"https://image.pollinations.ai/prompt/{urllib.parse.quote(prompt[:300])}"
           f"?width={int(width or 768)}&height={int(height or 768)}&nologo=true")
    r = httpx.get(url, timeout=180.0, follow_redirects=True)
    if r.status_code == 200 and len(r.content) > 5000:
        fname = f"img_{int(datetime.datetime.now().timestamp())}.jpg"
        with open(os.path.join(FILES_DIR, fname), "wb") as f:
            f.write(r.content)
        return f"Image ban gayi: {fname}"
    return f"[image error] HTTP {r.status_code}"


def speak(text: str, lang: str = "ur") -> str:
    """Text ko awaaz mein badlo (Urdu default). Args: text, lang (optional: ur/en/hi)"""
    q = urllib.parse.quote(text[:200])
    r = httpx.get(f"https://translate.google.com/translate_tts?ie=UTF-8&q={q}&tl={lang}&client=tw-ob",
                  headers={"User-Agent": "Mozilla/5.0 (Windows NT 10.0)"}, timeout=30.0)
    if r.status_code == 200 and len(r.content) > 500:
        fname = f"speech_{int(datetime.datetime.now().timestamp())}.mp3"
        with open(os.path.join(FILES_DIR, fname), "wb") as f:
            f.write(r.content)
        return f"Awaaz ban gayi: {fname}"
    return f"[tts error] HTTP {r.status_code}"


# ---------------- BROWSER (Playwright, optional) ----------------

_BROWSER = {"pw": None}

def _get_browser():
    if _BROWSER["pw"] is not None:
        return _BROWSER["pw"]
    try:
        from playwright.sync_api import sync_playwright
        _BROWSER["pw"] = {"pw": sync_playwright(), "br": None, "elems": {}}
        return _BROWSER["pw"]
    except Exception:
        return None


def browser_open(url: str) -> str:
    """Browser mein page kholo. Args: url"""
    b = _get_browser()
    if not b:
        return "[Playwright installed nahi hai — install_ho to browser tools available]"
    if not b.get("br"):
        b["br"] = b["pw"].chromium.launch(headless=True)
    if not b.get("pg"):
        b["pg"] = b["br"].new_page()
    b["pg"].goto(url, timeout=45000)
    b["elems"] = {}
    return f"OK — {url} khula. Page elements: browser_list dekho"


def browser_list() -> str:
    """Page ke clickable elements ki numbered list. Args: (koi nahi)"""
    b = _get_browser()
    if not b or not b.get("pg"):
        return "[pehle browser_open karo]"
    items = b["pg"].query_selector_all("a, button, input, select, textarea, [onclick]")
    b["elems"] = {}
    lines = []
    for i, el in enumerate(items[:40], 1):
        txt = (el.inner_text() or el.get_attribute("value") or el.get_attribute("placeholder") or "").strip()[:40]
        tag = el.evaluate("e => e.tagName.toLowerCase()")
        b["elems"][i] = el
        lines.append(f"{i}. [{tag}] {txt}")
    return "\n".join(lines) or "[koi element nahi mila]"


def browser_click(target: int) -> str:
    """Element pe click (number browser_list se). Args: target (number)"""
    b = _get_browser()
    el = (b or {}).get("elems", {}).get(int(target))
    if not el:
        return f"[element {target} nahi mila — browser_list se number lo]"
    try:
        el.click(timeout=10000)
        return "OK — click hua"
    except Exception as e:
        return f"[click error] {e}"


def browser_type(target: int, text: str) -> str:
    """Input field mein likho. Args: target (browser_list number), text"""
    b = _get_browser()
    el = (b or {}).get("elems", {}).get(int(target))
    if not el:
        return f"[element {target} nahi mila — browser_list se number lo]"
    try:
        el.fill(str(text), timeout=10000)
        return "OK — type hua"
    except Exception as e:
        return f"[type error] {e}"


def browser_read() -> str:
    """Abhi ke page ka text. Args: (koi nahi)"""
    b = _get_browser()
    if not b or not b.get("pg"):
        return "[pehle browser_open karo]"
    return b["pg"].inner_text()[:4000]


def browser_close() -> str:
    """Browser band karo. Args: (koi nahi)"""
    b = _get_browser()
    if b and b.get("br"):
        try:
            b["br"].close()
        except Exception:
            pass
        b["br"] = None
        b["pg"] = None
    return "OK — browser band"



# ---------------- MEMORY (agent khud yaad rakhta hai) ----------------

def save_memory(fact: str) -> str:
    """Important cheez hamesha ke liye yaad karo (user ki pasand/naam/kaam). Args: fact"""
    from memory import add_fact
    return add_fact(fact)


def recall() -> str:
    """Apni sari yaad dekho (jo tumne save kiya + jo user ne bataya). Args: none"""
    from memory import get_user_memory
    return get_user_memory() or "[abhi kuch yaad nahi]"

# ---------------- REGISTRY ----------------

TOOL_REGISTRY = {
    "web_search":       "DuckDuckGo web search — kisi bhi topic ki info. args: query",
    "fetch_url":        "Webpage ka pura text. args: url",
    "http_request":     "Raw HTTP API call. args: url, method(optional), body(optional), headers(optional)",
    "wikipedia_search": "Wikipedia. args: query",
    "youtube_search":   "YouTube videos. args: query",
    "weather":          "Mausam. args: city",
    "run_shell":        "Terminal command (asli Linux). Install ke liye timeout=600. args: command, timeout(optional)",
    "read_file":        "File parho. args: path",
    "write_file":       "File likho. args: path, content",
    "list_dir":         "Folder ki list. args: path(optional)",
    "download_file":    "Internet se file download. args: url, path(optional)",
    "system_info":      "Server ki report (RAM/disk/CPU). args: none",
    "now":              "Abhi ka time/date. args: none",
    "calculator":       "Math. args: expression",
    "generate_image":   "AI image banao. args: prompt (English), width(optional), height(optional)",
    "speak":            "Text ko Urdu/Hindi/English awaaz. args: text, lang(optional ur/en/hi)",
    "browser_open":     "Real browser mein page kholo. args: url",
    "browser_list":     "Page ke clickable elements (numbered). args: none",
    "browser_click":    "Number wale element pe click. args: target",
    "browser_type":     "Input field mein likho. args: target, text",
    "browser_read":     "Current page ka text. args: none",
    "browser_close":    "Browser band. args: none",
}

_FUNCS = {
    "web_search": web_search, "fetch_url": fetch_url, "http_request": http_request,
    "wikipedia_search": wikipedia_search, "youtube_search": youtube_search,
    "weather": weather, "run_shell": run_shell, "read_file": read_file,
    "write_file": write_file, "list_dir": list_dir, "download_file": download_file,
    "system_info": system_info, "now": now, "calculator": calculator,
    "generate_image": generate_image, "speak": speak,
    "browser_open": browser_open, "browser_list": browser_list,
    "browser_click": browser_click, "browser_type": browser_type,
    "browser_read": browser_read, "browser_close": browser_close, "save_memory": save_memory, "recall": recall,
}

# name aliases (model galat naam bole to)
_ALIASES = {
    "search": "web_search", "google": "web_search", "ddg": "web_search",
    "open_url": "fetch_url", "browse": "fetch_url", "get": "http_request",
    "shell": "run_shell", "bash": "run_shell", "terminal": "run_shell", "exec": "run_shell",
    "calc": "calculator", "image": "generate_image", "img": "generate_image", "draw": "generate_image",
    "tts": "speak", "voice": "speak", "browser": "browser_open", "open": "browser_open",
    "goto": "browser_open", "click": "browser_click", "type": "browser_type",
    "read_page": "browser_read", "ls": "list_dir", "cat": "read_file", "save": "write_file",
}

# arg aliases — har tool ka primary arg
_ARG_HINTS = {
    "web_search": ("query", ["q", "search", "search_query", "text", "keyword", "for"]),
    "fetch_url": ("url", ["link", "website", "address", "page", "site"]),
    "http_request": ("url", ["link", "endpoint", "api"]),
    "wikipedia_search": ("query", ["q", "search", "term"]),
    "youtube_search": ("query", ["q", "search", "term"]),
    "weather": ("city", ["place", "location", "town"]),
    "run_shell": ("command", ["cmd", "shell", "bash", "line", "script"]),
    "calculator": ("expression", ["expr", "eq", "math", "problem", "input"]),
    "generate_image": ("prompt", ["text", "description", "what"]),
    "speak": ("text", ["content", "say", "words", "message"]),
    "browser_open": ("url", ["link", "site", "address"]),
    "browser_click": ("target", ["index", "id", "number", "element", "n"]),
    "browser_type": ("target", ["index", "id", "number", "field"]),
    "read_file": ("path", ["file", "filename", "name", "filepath"]),
    "write_file": ("path", ["file", "filename", "name"]),
    "list_dir": ("path", ["dir", "folder", "directory"]),
    "download_file": ("url", ["link", "from"]),
}


def _normalize(name: str, args: dict) -> tuple:
    name = _ALIASES.get(name, name)
    args = dict(args) if isinstance(args, dict) else {}
    # _raw shorthand → primary arg
    if "_raw" in args:
        hint = _ARG_HINTS.get(name)
        if hint:
            args[hint[0]] = args.pop("_raw")
        else:
            args.pop("_raw", None)
    if name in _ARG_HINTS:
        primary, alts = _ARG_HINTS[name]
        for alt in alts:
            if alt in args and primary not in args:
                args[primary] = args.pop(alt)
    return name, args


def execute(name: str, args: dict):
    name, args = _normalize(name, args)
    fn = _FUNCS.get(name)
    if not fn:
        return f"[tool '{name}' nahi hai] Available: {', '.join(TOOL_REGISTRY)}"
    import inspect
    sig = inspect.signature(fn)
    clean = {k: v for k, v in args.items() if k in sig.parameters}
    return fn(**clean)
