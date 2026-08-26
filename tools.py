"""
tools.py  —  Agent ke hathiyar (tools)
======================================
Yeh tools agent ko powerful banate hain. Agent inhe khud decide karke call karta hai.

Available tools:
  - web_search     : Google/DuckDuckGo se internet search
  - fetch_url      : kisi bhi webpage ka text nikalna (browser jaisa)
  - read_file      : local file parhna
  - write_file     : local file likhna / banana
  - list_dir       : directory ki listing
  - run_shell      : terminal command chalana (bahut powerful!)
  - calculator     : math hisaab
"""

import subprocess
import re
import html
import urllib.parse
import httpx
from bs4 import BeautifulSoup

# Real browser automation tools import
from browser import (
    browser_goto, browser_click, browser_type,
    browser_scroll, browser_press, browser_screenshot,
)


def web_search(query: str, num_results: int = 6) -> str:
    """DuckDuckGo se search (koi API key nahi chahiye)."""
    try:
        url = "https://html.duckduckgo.com/html/"
        headers = {"User-Agent": "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 "
                                 "(KHTML, like Gecko) Chrome/131.0 Safari/537.36"}
        r = httpx.post(url, data={"q": query}, headers=headers, timeout=20.0, follow_redirects=True)
        soup = BeautifulSoup(r.text, "html.parser")
        results = []
        for res in soup.select(".result"):
            title_tag = res.select_one(".result__a")
            snippet_tag = res.select_one(".result__snippet")
            if title_tag:
                title = title_tag.get_text(strip=True)
                link = title_tag.get("href", "")
                # DuckDuckGo redirect unwrap
                m = re.search(r"uddg=([^&]+)", link)
                if m:
                    link = urllib.parse.unquote(m.group(1))
                snippet = snippet_tag.get_text(strip=True) if snippet_tag else ""
                results.append(f"• {title}\n  {link}\n  {snippet}")
            if len(results) >= num_results:
                break
        if not results:
            return f"Search '{query}' ke liye koi result nahi mila."
        return "\n\n".join(results)
    except Exception as e:
        return f"Search error: {e}"


def fetch_url(url: str, max_chars: int = 4000) -> str:
    """Webpage download karke saaf text nikalta hai (browser automation ka simple version)."""
    try:
        headers = {"User-Agent": "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 "
                                 "(KHTML, like Gecko) Chrome/131.0 Safari/537.36"}
        r = httpx.get(url, headers=headers, timeout=20.0, follow_redirects=True)
        soup = BeautifulSoup(r.text, "html.parser")
        # scripts, styles hatao
        for tag in soup(["script", "style", "nav", "footer", "header", "aside"]):
            tag.decompose()
        text = soup.get_text(separator="\n", strip=True)
        # khali lines squeeze
        text = re.sub(r"\n{3,}", "\n\n", text)
        return text[:max_chars]
    except Exception as e:
        return f"Fetch error: {e}"


def read_file(path: str) -> str:
    try:
        with open(path, "r", encoding="utf-8", errors="ignore") as f:
            return f.read()[:5000]
    except Exception as e:
        return f"Error: {e}"


def write_file(path: str, content: str) -> str:
    try:
        with open(path, "w", encoding="utf-8") as f:
            f.write(content)
        return f"File likh di: {path} ({len(content)} chars)"
    except Exception as e:
        return f"Error: {e}"


def list_dir(path: str = ".") -> str:
    import os
    try:
        entries = os.listdir(path)
        return "\n".join(sorted(entries))
    except Exception as e:
        return f"Error: {e}"


def run_shell(command: str, timeout: int = 300) -> str:
    """Terminal command chalata hai. Installations ke liye timeout=600 do.
    Args: command (str), timeout (int seconds, default 300, max 900)."""
    timeout = min(int(timeout or 300), 900)
    try:
        out = subprocess.run(
            command, shell=True, capture_output=True, text=True, timeout=timeout
        )
        result = ""
        if out.stdout:
            result += out.stdout
        if out.stderr:
            result += ("\n[STDERR]\n" + out.stderr)
        return (result or "(no output)")[:5000]
    except subprocess.TimeoutExpired:
        return f"Timeout ({timeout}s) — command abhi chal rahi thi. Chhoti commands do ya timeout barhao."
    except Exception as e:
        return f"Error: {e}"


def calculator(expression: str) -> str:
    """Safe math (sirf numbers aur operators)."""
    try:
        # sirf safe characters allow
        if not re.match(r"^[\d\s+\-*/().%<>=&|^~]*$", expression):
            return "Error: sirf math expression allow hai"
        result = eval(expression, {"__builtins__": {}}, {})
        return str(result)
    except Exception as e:
        return f"Error: {e}"


# ---------- NAYE TOOLS ----------

def http_request(url: str, method: str = "GET", body=None, headers=None) -> str:
    """Kisi bhi website/API ko HTTP request (GET/POST/PUT/DELETE).
    RESPONSE HEADERS bhi dikhata hai (Server, X-Powered-By, tech stack ke liye)."""
    try:
        h = headers if isinstance(headers, dict) else {}
        kwargs = {"headers": h, "timeout": 25.0, "follow_redirects": True}
        if isinstance(body, dict):
            kwargs["json"] = body
        elif isinstance(body, str) and body:
            kwargs["content"] = body
        r = httpx.request(method.upper(), url, **kwargs)
        # headers pehle (security/tech analysis ke liye zaroori)
        hdr = "\n".join(f"  {k}: {v}" for k, v in r.headers.items())
        return f"HTTP {r.status_code}\n\nHEADERS:\n{hdr}\n\nBODY:\n{r.text[:2200]}"
    except Exception as e:
        return f"Error: {e}"


def weather(city: str) -> str:
    """Kisi bhi city ka mausam (wttr.in, free)."""
    try:
        r = httpx.get(f"https://wttr.in/{city}?format=j1", timeout=20.0)
        cur = r.json().get("current_condition", [{}])[0]
        desc = cur.get("weatherDesc", [{}])[0].get("value", "")
        return (f"{city}: {cur.get('temp_C')}°C (feels {cur.get('FeelsLikeC')}°C), {desc}, "
                f"humidity {cur.get('humidity')}%, wind {cur.get('windspeedKmph')} km/h")
    except Exception as e:
        return f"Error: {e}"


def wikipedia_search(query: str) -> str:
    """Wikipedia par search karke articles dhundo."""
    try:
        r = httpx.get("https://en.wikipedia.org/w/api.php", params={
            "action": "query", "list": "search", "srsearch": query,
            "format": "json", "srlimit": 3}, timeout=20.0)
        results = r.json().get("query", {}).get("search", [])
        if not results:
            return f"'{query}' par kuch nahi mila"
        lines = []
        for s in results[:3]:
            lines.append(f"• {s['title']}\n  https://en.wikipedia.org/wiki/{s['title'].replace(' ', '_')}")
        return "\n".join(lines)
    except Exception as e:
        return f"Error: {e}"


def now() -> str:
    """Aaj ki date aur waqt (local timezone)."""
    from datetime import datetime
    return datetime.now().strftime("%A, %d %B %Y — %H:%M:%S")


# ---------- 🔥 POWER TOOLS (mere jaise) ----------

def generate_image(prompt: str, path: str = "image.jpg", width: int = 768, height: int = 768) -> str:
    """AI se image banao (Pollinations — free, no key). Prompt describe karo."""
    try:
        url = (f"https://image.pollinations.ai/prompt/{urllib.parse.quote(prompt[:300])}"
               f"?width={width}&height={height}&nologo=true")
        r = httpx.get(url, timeout=180.0, follow_redirects=True)
        if r.status_code == 200 and len(r.content) > 5000:
            with open(path, "wb") as f:
                f.write(r.content)
            return f"🖼️ Image ban gayi: {path} ({len(r.content)//1024} KB) — open_in_browser('{path}') se dekho"
        return f"Image error: HTTP {r.status_code}"
    except Exception as e:
        return f"Error: {e}"


def speak(text: str, lang: str = "ur", path: str = "speech.mp3") -> str:
    """Text ko AWAAZ mein badlo (Google TTS free). lang: ur (Urdu), en, hi..."""
    try:
        q = urllib.parse.quote(text[:200])
        url = f"https://translate.google.com/translate_tts?ie=UTF-8&q={q}&tl={lang}&client=tw-ob"
        r = httpx.get(url, timeout=30.0, headers={"User-Agent": "Mozilla/5.0 (Windows NT 10.0)"})
        if r.status_code == 200 and len(r.content) > 500:
            with open(path, "wb") as f:
                f.write(r.content)
            return f"🔊 Audio ban gaya: {path} ({len(r.content)//1024} KB) — open_in_browser('{path}') se suno"
        return f"TTS error: HTTP {r.status_code}"
    except Exception as e:
        return f"Error: {e}"


def download_file(url: str, path: str = "downloaded_file") -> str:
    """Internet se koi bhi file download karo."""
    try:
        with httpx.stream("GET", url, timeout=180.0, follow_redirects=True) as r:
            if r.status_code != 200:
                return f"HTTP {r.status_code}"
            total = 0
            with open(path, "wb") as f:
                for chunk in r.iter_bytes():
                    f.write(chunk)
                    total += len(chunk)
        return f"⬇️ Download complete: {path} ({total//1024} KB)"
    except Exception as e:
        return f"Error: {e}"


def youtube_search(query: str, count: int = 5) -> str:
    """YouTube par videos search karo (titles + links)."""
    try:
        headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"}
        r = httpx.get(f"https://www.youtube.com/results?search_query={urllib.parse.quote(query)}",
                      headers=headers, timeout=20.0)
        m = re.search(r"var ytInitialData = ({.*?});</script>", r.text)
        if not m:
            return "YouTube parse error"
        import json as _json
        data = _json.loads(m.group(1))
        out = []

        def _find(obj):
            if isinstance(obj, dict):
                if "videoRenderer" in obj and len(out) < count:
                    vr = obj["videoRenderer"]
                    title = ""
                    runs = vr.get("title", {}).get("runs", [])
                    if runs:
                        title = runs[0].get("text", "")
                    vid = vr.get("videoId", "")
                    if title and vid:
                        out.append(f"• {title}\n  https://www.youtube.com/watch?v={vid}")
                for v in obj.values():
                    _find(v)
            elif isinstance(obj, list):
                for v in obj:
                    _find(v)

        _find(data)
        return "\n".join(out) if out else "kuch nahi mila"
    except Exception as e:
        return f"Error: {e}"


def system_info() -> str:
    """System ki poori info (OS, CPU, RAM, disk)."""
    try:
        import platform, shutil, os
        du = shutil.disk_usage(os.getcwd())
        return (f"OS: {platform.system()} {platform.release()} ({platform.machine()})\n"
                f"Python: {platform.python_version()}\n"
                f"CPU cores: {os.cpu_count()}\n"
                f"Disk free: {du.free//(1024**3)}GB / total {du.total//(1024**3)}GB\n"
                f"Folder: {os.getcwd()}")
    except Exception as e:
        return f"Error: {e}"


def open_in_browser(target: str) -> str:
    """Browser mein kholo (file ya URL) — image/audio/results dikhane ke liye."""
    try:
        import webbrowser, os
        if not target.startswith("http") and os.path.exists(target):
            url = f"http://localhost:8000/files/{os.path.basename(target)}"
        else:
            url = target
        webbrowser.open(url)
        return f"✅ Browser mein khul gaya: {url}"
    except Exception as e:
        return f"Error: {e}"


def pdf_read(path: str) -> str:
    """PDF file ka text nikaalo (pypdf chahiye: pip install pypdf)."""
    try:
        from pypdf import PdfReader
        reader = PdfReader(path)
        text = ""
        for page in reader.pages[:10]:
            text += (page.extract_text() or "") + "\n"
        return text[:3000] if text else "PDF mein text nahi mila"
    except ImportError:
        return "[pypdf install nahi — run_shell('pip install pypdf') karo pehle]"
    except Exception as e:
        return f"Error: {e}"


# Tool registry — agent yeh se call karta hai
TOOL_REGISTRY = {
    "web_search": {"fn": web_search,
                   "desc": "Internet par search karna. Args: query (str), num_results (int, default 6)."},
    "fetch_url": {"fn": fetch_url,
                  "desc": "Kisi URL ka text download karna. Args: url (str)."},
    "read_file": {"fn": read_file,
                  "desc": "Local file parhna. Args: path (str)."},
    "write_file": {"fn": write_file,
                   "desc": "File banana/likhna. Args: path (str), content (str)."},
    "list_dir": {"fn": list_dir,
                 "desc": "Directory listing. Args: path (str, default '.')."},
    "run_shell": {"fn": run_shell,
                  "desc": "Terminal/shell command chalana (bahut powerful — pip install, scripts, kuch bhi). Installations ke liye timeout=600 pass karo. Args: command (str), timeout (int seconds, default 300)."},
    "calculator": {"fn": calculator,
                   "desc": "Math calculation. Args: expression (str)."},
    # ===== REAL BROWSER AUTOMATION (Playwright) =====
    "browser_goto": {"fn": browser_goto,
                     "desc": "Real browser mein URL kholna. Clickable elements number ke saath list milte hain. Args: url (str)."},
    "browser_click": {"fn": browser_click,
                      "desc": "Browser mein kisi element pe click. target = number (jaise 5) ya CSS selector. Args: target (int/str)."},
    "browser_type": {"fn": browser_type,
                     "desc": "Browser mein kisi field mein type karna. target=number/selector, submit=True se Enter. Args: target, text (str), submit (bool)."},
    "browser_scroll": {"fn": browser_scroll,
                       "desc": "Page scroll karna. Args: direction (str down/up default down), amount (int default 3)."},
    "browser_press": {"fn": browser_press,
                      "desc": "Keyboard key press karna (Enter, Tab, Escape, ArrowDown). Args: key (str)."},
    "browser_screenshot": {"fn": browser_screenshot,
                           "desc": "Current page ka screenshot lena. Args: path (str default /tmp/agent_shot.png)."},
    # ===== NAYE TOOLS =====
    "http_request": {"fn": http_request,
                     "desc": "Kisi bhi website/API ko HTTP request bhejna (GET/POST/PUT/DELETE). Automation aur API kaam ke liye. Args: url (str), method (str default GET), body (dict/str, optional), headers (dict, optional)."},
    "weather": {"fn": weather,
                "desc": "Kisi city ka current mausam. Args: city (str)."},
    "wikipedia_search": {"fn": wikipedia_search,
                         "desc": "Wikipedia par articles dhundna. Args: query (str)."},
    "now": {"fn": now,
            "desc": "Aaj ki date aur current time (koi args nahi)."},
    # ===== 🔥 POWER TOOLS =====
    "generate_image": {"fn": generate_image,
                       "desc": "AI se image banana (free, no key). Prompt se picture banti hai. Args: prompt (str, English mein describe karo), path (str default image.jpg), width/height (int default 768)."},
    "speak": {"fn": speak,
              "desc": "Text ko AWAAZ (speech audio) mein convert karna. Args: text (str), lang (str: 'ur' Urdu, 'en' English, 'hi' Hindi), path (str default speech.mp3)."},
    "download_file": {"fn": download_file,
                      "desc": "Internet se koi bhi file download karna. Args: url (str), path (str — jahan save karni hai)."},
    "youtube_search": {"fn": youtube_search,
                       "desc": "YouTube par videos search karna (titles + links). Args: query (str), count (int default 5)."},
    "system_info": {"fn": system_info,
                    "desc": "System ki info (OS, CPU, disk). Koi args nahi."},
    "open_in_browser": {"fn": open_in_browser,
                        "desc": "File ya URL browser mein kholna (user ko dikhane ke liye). Args: target (str — file path ya http URL)."},
    "pdf_read": {"fn": pdf_read,
                 "desc": "PDF file ka text nikaalna. Args: path (str)."},
}
