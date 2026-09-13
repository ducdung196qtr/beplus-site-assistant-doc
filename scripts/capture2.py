#!/usr/bin/env python3
"""Front-end shots: lead gate, a real answered chat, and mobile.

Uses a context with NO WordPress cookies, so the admin toolbar never appears and
the page looks exactly as a visitor sees it.

Interaction notes (verified against the live DOM):
  - The launcher is `.bsa-fab`; the panel gains the class `open` when clicked.
  - A normal Playwright click can be intercepted by the hovering teaser bubble,
    so the launcher is clicked through JS, which is deterministic.
  - The lead form (`.bsa-lead-submit`) is only visible once the panel is open.
"""
import pathlib

from playwright.sync_api import sync_playwright

BASE = "https://160-250-135-47.sslip.io"
OUT = pathlib.Path("/root/beplus-site-assistant-doc/public/img")
CHROME = "/root/.agent-browser/browsers/chrome-153.0.8010.36/chrome"

QUESTION = "What does MRS Group do?"


def shot(page, name):
    path = OUT / name
    page.screenshot(path=str(path))
    print(f"  {name:34s} {path.stat().st_size/1024:7.1f} KB")


def open_widget(page):
    """Click the launcher through JS — a real click can hit the teaser bubble."""
    page.evaluate("() => { const f = document.querySelector('.bsa-fab'); if (f) f.click(); }")
    page.wait_for_timeout(1800)
    return page.evaluate(
        "() => { const p = document.querySelector('.bsa-panel');"
        " return !!p && p.classList.contains('open'); }"
    )


def fill_lead(page):
    """Fill the name/email start screen and submit it."""
    ok = page.evaluate(
        """() => {
          const panel = document.querySelector('.bsa-panel');
          if (!panel) return 'khong co panel';
          const inputs = [...panel.querySelectorAll('input')];
          const name = inputs.find(i => /name|ten/i.test(i.placeholder || '') ) || inputs[0];
          const mail = inputs.find(i => i.type === 'email' || /mail/i.test(i.placeholder || ''))
                     || inputs[1];
          if (!name || !mail) return 'thieu o nhap';
          const set = (el, v) => {
            const proto = el.tagName === 'TEXTAREA'
              ? window.HTMLTextAreaElement.prototype : window.HTMLInputElement.prototype;
            Object.getOwnPropertyDescriptor(proto, 'value').set.call(el, v);
            el.dispatchEvent(new Event('input', { bubbles: true }));
            el.dispatchEvent(new Event('change', { bubbles: true }));
          };
          set(name, 'Alex Morgan');
          set(mail, 'alex@example.com');
          return 'ok';
        }"""
    )
    print(f"    dien form: {ok}")
    if ok != "ok":
        return False
    page.evaluate(
        "() => { const b = document.querySelector('.bsa-lead-submit'); if (b) b.click(); }"
    )
    page.wait_for_timeout(2000)
    return True


def ask(page, question):
    """Type a real question and wait for the assistant to answer."""
    typed = page.evaluate(
        """(q) => {
          const panel = document.querySelector('.bsa-panel');
          const box = panel && panel.querySelector('textarea, input[type=text], .bsa-input');
          if (!box) return false;
          const proto = box.tagName === 'TEXTAREA'
            ? window.HTMLTextAreaElement.prototype : window.HTMLInputElement.prototype;
          Object.getOwnPropertyDescriptor(proto, 'value').set.call(box, q);
          box.dispatchEvent(new Event('input', { bubbles: true }));
          return true;
        }""",
        question,
    )
    if not typed:
        return False
    page.wait_for_timeout(500)
    page.evaluate("() => { const b = document.querySelector('.bsa-send'); if (b) b.click(); }")

    # Wait for a bot bubble to appear, then let it finish streaming.
    for _ in range(45):
        page.wait_for_timeout(1000)
        n = page.evaluate(
            """() => document.querySelectorAll(
                 '.bsa-panel [class*="bot"], .bsa-panel [class*="assistant"]'
               ).length"""
        )
        if n:
            break
    page.wait_for_timeout(5000)
    return True


def main():
    with sync_playwright() as p:
        browser = p.chromium.launch(
            executable_path=CHROME,
            args=["--no-sandbox", "--disable-gpu", "--disable-dev-shm-usage"],
        )
        ctx = browser.new_context(
            viewport={"width": 1440, "height": 900},
            device_scale_factor=2,
            ignore_https_errors=True,
        )
        page = ctx.new_page()
        page.goto(BASE, wait_until="domcontentloaded")
        page.wait_for_timeout(4000)

        print("mo widget:")
        print(f"    mo duoc: {open_widget(page)}")
        page.wait_for_timeout(900)

        # 12 — the start screen a visitor sees first (name + email).
        shot(page, "12-lead-gate.png")

        if fill_lead(page):
            print("    da qua man hinh xin lien he, dat cau hoi that...")
            ask(page, QUESTION)
            shot(page, "10-widget-desktop.png")

        page.set_viewport_size({"width": 390, "height": 844})
        page.wait_for_timeout(1800)
        shot(page, "11-widget-mobile.png")

        browser.close()
    print("xong")


if __name__ == "__main__":
    main()
