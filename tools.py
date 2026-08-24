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


def run_shell(command: str, timeout: int = 30) -> str:
    """Terminal command chalata hai. Powerful hai — ehtiyat se."""
    try:
        out = subprocess.run(
            command, shell=True, capture_output=True, text=True, timeout=timeout
        )
        result = ""
        if out.stdout:
            result += out.stdout
        if out.stderr:
            result += ("\n[STDERR]\n" + out.stderr)
        return (result or "(no output)")[:4000]
    except subprocess.TimeoutExpired:
        return f"Timeout ({timeout}s) — command ruk gaya"
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
                  "desc": "Terminal/shell command chalana (bahut powerful). Args: command (str)."},
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
}
