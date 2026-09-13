#!/usr/bin/env python3
"""Re-capture the Conversations screens with visitor PII redacted.

The live install contains a real visitor's email address and the server's own IP
in every row. Those must not be published, so before capture the text of the
Visitor, IP and Page cells is replaced in the DOM with clearly fictional sample
values. Everything else — the columns, the layout, the buttons, the real counts —
is untouched, so the screenshot still documents the actual screen.

Playwright's element screenshot has no redaction primitive, and blurring the
columns would hide the very thing the image exists to show; substituting the
values is the honest option, and it is noted in the docs.
"""
import pathlib

from playwright.sync_api import sync_playwright

BASE = "https://160-250-135-47.sslip.io"
OUT = pathlib.Path("/root/beplus-site-assistant-doc/public/img")
TOKEN = pathlib.Path("/tmp/bsa_qa_token.txt").read_text().strip()
CHROME = "/root/.agent-browser/browsers/chrome-153.0.8010.36/chrome"

# Replace real visitor details with obvious sample values.
REDACT = """
() => {
  const IP = /\\b\\d{1,3}\\.\\d{1,3}\\.\\d{1,3}\\.\\d{1,3}\\b/g;
  const MAIL = /[\\w.+-]+@[\\w-]+\\.[\\w.]{2,}/g;
  const names = ['alex@example.com', 'sam@example.com', 'jo@example.com'];
  let emailIdx = 0;
  const walk = (node) => {
    for (const child of [...node.childNodes]) {
      if (child.nodeType === 3) {
        let t = child.nodeValue;
        if (!t) continue;
        if (MAIL.test(t)) {
          t = t.replace(MAIL, () => names[emailIdx++ % names.length]);
        }
        if (IP.test(t)) {
          t = t.replace(IP, '203.0.113.10');
        }
        if (t !== child.nodeValue) child.nodeValue = t;
      } else if (child.nodeType === 1) {
        walk(child);
      }
    }
  };
  walk(document.body);
  return document.body.innerText.match(/\\d{1,3}\\.\\d{1,3}\\.\\d{1,3}\\.\\d{1,3}/g) || 'clean';
}
"""


def shot(page, name):
    path = OUT / name
    page.screenshot(path=str(path))
    print(f"  {name:34s} {path.stat().st_size/1024:7.1f} KB")


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
        page.goto(f"{BASE}/?bsa_qa_gate={TOKEN}", wait_until="domcontentloaded")

        tabs = [
            ("Live Sessions", "06-conversations-live.png"),
            ("SEO Insights", "07-conversations-seo.png"),
            ("Storage", "08-conversations-storage.png"),
        ]
        for label, fname in tabs:
            page.goto(
                f"{BASE}/wp-admin/admin.php?page=beplus-site-assistant-live",
                wait_until="networkidle",
            )
            page.wait_for_timeout(1200)
            try:
                page.get_by_role("button", name=label, exact=False).first.click()
                page.wait_for_timeout(2200)
            except Exception as exc:
                print(f"    ! tab {label}: {exc}")

            leftover = page.evaluate(REDACT)
            print(f"    {label}: IP con lai -> {leftover}")
            page.wait_for_timeout(400)
            shot(page, fname)

        browser.close()
    print("xong")


if __name__ == "__main__":
    main()
