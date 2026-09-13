#!/usr/bin/env python3
"""Capture documentation screenshots from the live WordPress install.

Reads the QA gate token from /tmp/bsa_qa_token.txt, logs in through the
temporary gate, then screenshots each admin tab and the front-end widget.

Privacy: the API endpoint and API key fields are blurred before capture, and
visitor names/emails are never included in a shot.
"""
import pathlib
import sys

from playwright.sync_api import sync_playwright

BASE = "https://160-250-135-47.sslip.io"
OUT = pathlib.Path("/root/beplus-site-assistant-doc/public/img")
TOKEN = pathlib.Path("/tmp/bsa_qa_token.txt").read_text().strip()

# Blur anything that would leak internal addresses, keys or visitor details.
BLUR_CSS = """
() => {
  const style = document.createElement('style');
  style.textContent = `
    #bsa-endpoint, #bsa-key, [id*="endpoint"], [id*="api-key"], [id*="bsa-key"] {
      filter: blur(6px) !important;
    }
    .bsa-live-row td:nth-child(3), .bsa-live-row td:nth-child(4) {
      filter: blur(5px) !important;
    }
  `;
  document.head.appendChild(style);
}
"""


def blur(page):
    try:
        page.evaluate(BLUR_CSS)
    except Exception:
        pass


def shot(page, name, full=False):
    path = OUT / name
    page.screenshot(path=str(path), full_page=full)
    size = path.stat().st_size
    print(f"  {name:34s} {size/1024:7.1f} KB")


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    with sync_playwright() as p:
        browser = p.chromium.launch(
            executable_path="/root/.agent-browser/browsers/chrome-153.0.8010.36/chrome",
            args=["--no-sandbox", "--disable-gpu", "--disable-dev-shm-usage"],
        )
        ctx = browser.new_context(
            viewport={"width": 1440, "height": 900},
            device_scale_factor=2,
            ignore_https_errors=True,
        )
        page = ctx.new_page()

        print("dang nhap qua gate...")
        page.goto(f"{BASE}/?bsa_qa_gate={TOKEN}", wait_until="domcontentloaded")

        # ---------- admin: settings tabs ----------
        tabs = [
            ("AI & Model", "01-settings-ai.png"),
            ("Knowledge Base", "02-settings-knowledge.png"),
            ("Appearance & FAQs", "03-settings-appearance.png"),
            ("Leads & Email", "04-settings-leads.png"),
            ("Security & Limits", "05-settings-security.png"),
        ]
        print("chup cac tab Settings:")
        for label, fname in tabs:
            page.goto(
                f"{BASE}/wp-admin/admin.php?page=beplus-site-assistant",
                wait_until="networkidle",
            )
            try:
                page.get_by_role("button", name=label, exact=False).first.click()
                page.wait_for_timeout(1200)
            except Exception as exc:
                print(f"    ! khong bam duoc tab {label}: {exc}")
            blur(page)
            shot(page, fname)

        # ---------- admin: conversations ----------
        print("chup tab Conversations:")
        conv = [
            ("Live Sessions", "06-conversations-live.png"),
            ("SEO Insights", "07-conversations-seo.png"),
            ("Storage", "08-conversations-storage.png"),
        ]
        for label, fname in conv:
            page.goto(
                f"{BASE}/wp-admin/admin.php?page=beplus-site-assistant-live",
                wait_until="networkidle",
            )
            try:
                page.get_by_role("button", name=label, exact=False).first.click()
                page.wait_for_timeout(2000)
            except Exception as exc:
                print(f"    ! khong bam duoc tab {label}: {exc}")
            blur(page)
            shot(page, fname)

        # ---------- admin: embed script ----------
        print("chup trang Embed Script:")
        page.goto(
            f"{BASE}/wp-admin/admin.php?page=beplus-site-assistant-embed",
            wait_until="networkidle",
        )
        page.wait_for_timeout(800)
        shot(page, "09-embed-script.png")

        # ---------- front-end widget ----------
        print("chup widget truoc site:")
        page.goto(BASE, wait_until="networkidle")
        page.wait_for_timeout(1500)
        # Open the widget.
        for sel in [
            'button[aria-label*="assistant" i]',
            ".bsa-fab",
            "[class*='bsa-widget'] button",
        ]:
            try:
                el = page.query_selector(sel)
                if el:
                    el.click()
                    page.wait_for_timeout(1200)
                    break
            except Exception:
                continue
        shot(page, "10-widget-desktop.png")
        page.set_viewport_size({"width": 390, "height": 844})
        page.wait_for_timeout(800)
        shot(page, "11-widget-mobile.png")
        page.set_viewport_size({"width": 1440, "height": 900})

        browser.close()
    print("\nxong. Anh trong", OUT)


if __name__ == "__main__":
    sys.exit(main())
