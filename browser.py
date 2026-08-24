"""
browser.py  —  Real Browser Automation (Playwright)
====================================================
Ek complete, persistent browser jo agent khud control karta hai.
Headless Chromium use karta hai — click karna, type karna, scrape karna,
form bharna, subscribe karna — sab mumkin.

Agent ke liye asaan banane ke liye har clickable element ko ek NUMBER (id)
diya jata hai, taake agent us number se click kar sake (selector yaad rakhne ki
zaroorat nahi).
"""

import os
import json

# Playwright optional rakha gaya hai — agar na ho to tools graceful fail karte hain
try:
    from playwright.sync_api import sync_playwright, TimeoutError as PWTimeout
    _HAS_PW = True
except Exception:
    _HAS_PW = False

_session = None


class BrowserSession:
    """Ek persistent browser session. Module-level singleton."""

    def __init__(self):
        self._pw = sync_playwright().start()
        args = ["--no-sandbox", "--disable-dev-shm-usage", "--disable-gpu"]
        self.browser = self._pw.chromium.launch(headless=True, args=args)
        ctx = self.browser.new_context(
            viewport={"width": 1280, "height": 900},
            user_agent=("Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 "
                        "(KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36"),
            locale="en-US",
        )
        self.page = ctx.new_page()
        self.page.set_default_timeout(20000)
        self._ctx = ctx

    # ---------- actions ----------
    def goto(self, url: str) -> str:
        self.page.goto(url, wait_until="domcontentloaded")
        self.page.wait_for_timeout(800)
        return self._snapshot()

    def click(self, target) -> str:
        """target: number id (1,2,3...) ya CSS selector."""
        sel = self._resolve_selector(target)
        self.page.click(sel)
        self.page.wait_for_timeout(1000)
        return self._snapshot()

    def type(self, target, text: str, submit: bool = False) -> str:
        sel = self._resolve_selector(target)
        self.page.fill(sel, text)
        if submit:
            self.page.press(sel, "Enter")
            self.page.wait_for_timeout(1500)
        else:
            self.page.wait_for_timeout(400)
        return self._snapshot()

    def press(self, key: str) -> str:
        self.page.keyboard.press(key)
        self.page.wait_for_timeout(800)
        return self._snapshot()

    def scroll(self, direction: str = "down", amount: int = 3) -> str:
        dy = 600 if direction == "down" else -600
        for _ in range(amount):
            self.page.mouse.wheel(0, dy)
        self.page.wait_for_timeout(500)
        return self._snapshot()

    def screenshot(self, path: str = "/tmp/agent_shot.png") -> str:
        self.page.screenshot(path=path, full_page=False)
        return f"Screenshot save ho gaya: {path}"

    def get_text(self, max_chars: int = 3500) -> str:
        return self._clean_text(self.page.inner_text("body"))[:max_chars]

    def close(self):
        try:
            self.browser.close()
            self._pw.stop()
        except Exception:
            pass

    # ---------- helpers ----------
    def _resolve_selector(self, target) -> str:
        # agar number diya to data-agent-id se resolve karo
        if isinstance(target, (int, str)) and str(target).strip().isdigit():
            return f'[data-agent-id="{int(str(target).strip())}"]'
        return str(target)

    def _snapshot(self) -> str:
        """Clickable elements ko number do aur page ka MAIN text return karo."""
        try:
            self.page.evaluate("""() => {
                const els = document.querySelectorAll('a, button, input[type=submit], input[type=button], [role=button], summary, [onclick]');
                let i = 1;
                els.forEach(el => {
                    // nav/header/footer/aside ke andar wale skip karo (sirf main content)
                    if (el.closest('nav, header, footer, aside, .sidebar, .navbox, .mw-jump-link')) return;
                    const r = el.getBoundingClientRect();
                    if (r.width === 0 || r.height === 0) return;
                    const t = (el.innerText || el.getAttribute('aria-label') || el.getAttribute('placeholder') || '').trim();
                    if (!t) return;
                    el.setAttribute('data-agent-id', i++);
                });
            }""")
        except Exception:
            pass

        # clickable list
        try:
            items = self.page.evaluate("""() => {
                const out = [];
                document.querySelectorAll('[data-agent-id]').forEach(el => {
                    const t = (el.innerText || el.getAttribute('aria-label') ||
                               el.getAttribute('placeholder') || el.getAttribute('title') || '').trim().slice(0, 50);
                    const tag = el.tagName.toLowerCase();
                    const href = el.getAttribute('href') || '';
                    out.push({id: el.getAttribute('data-agent-id'), tag, text: t, href});
                });
                return out.slice(0, 22);
            }""")
        except Exception:
            items = []

        title = self.page.title()
        url = self.page.url
        text = self._main_text()

        lines = [f"📄 TITLE: {title}", f"🔗 URL: {url}", ""]
        if items:
            lines.append("🖱️ CLICKABLE ELEMENTS (number se click karein):")
            for it in items:
                txt = it["text"] or "(no text)"
                href = f" → {it['href']}" if it["href"] else ""
                lines.append(f"  [{it['id']}] <{it['tag']}> {txt}{href}")
            lines.append("")
        lines.append("📝 PAGE TEXT:")
        lines.append(text)
        return "\n".join(lines)

    def _main_text(self) -> str:
        """Main article content nikalta hai — nav/header/footer hata kar."""
        try:
            text = self.page.evaluate("""() => {
                // nav/header/footer/aside/script/style hata do
                document.querySelectorAll('nav, header, footer, aside, script, style, noscript, .sidebar, .navbox').forEach(e => e.remove());
                // main content container dhoondo
                const main = document.querySelector('main, article, #content, #bodyContent, #mw-content-text, [role=main], #main') || document.body;
                return main ? main.innerText : document.body.innerText;
            }""")
        except Exception:
            text = self.page.inner_text("body")
        return self._clean_text(text)[:1200]

    def _clean_text(self, t: str) -> str:
        import re
        t = re.sub(r"\n{3,}", "\n\n", t).strip()
        return t


def get_session():
    """Singleton browser session lazily start karo."""
    global _session
    if not _HAS_PW:
        raise RuntimeError("Playwright install nahi hai. pip install playwright + playwright install chromium")
    if _session is None:
        _session = BrowserSession()
    return _session


# ---------- Tool wrappers (tools.py se register hote hain) ----------
def browser_goto(url: str) -> str:
    try:
        return get_session().goto(url)
    except Exception as e:
        return f"Browser error: {e}"

def browser_click(target) -> str:
    try:
        return get_session().click(target)
    except Exception as e:
        return f"Browser error: {e}"

def browser_type(target, text: str, submit: bool = False) -> str:
    try:
        return get_session().type(target, text, submit)
    except Exception as e:
        return f"Browser error: {e}"

def browser_scroll(direction: str = "down", amount: int = 3) -> str:
    try:
        return get_session().scroll(direction, amount)
    except Exception as e:
        return f"Browser error: {e}"

def browser_press(key: str) -> str:
    try:
        return get_session().press(key)
    except Exception as e:
        return f"Browser error: {e}"

def browser_screenshot(path: str = "/tmp/agent_shot.png") -> str:
    try:
        return get_session().screenshot(path)
    except Exception as e:
        return f"Browser error: {e}"
