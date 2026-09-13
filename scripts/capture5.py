#!/usr/bin/env python3
"""Re-capture every admin screenshot with infrastructure details redacted.

What gets replaced, and why:

  * visitor email addresses  -> reserved example.com addresses (real stranger's PII)
  * visitor IP addresses     -> 203.0.113.10 (RFC 5737 documentation range)
  * the WordPress hostname   -> your-wordpress.com (it encodes the server's IP)
  * a real visitor's name    -> a sample name

Everything else — columns, counts, buttons, layout, real topic data — is left
untouched, so each image still documents the actual screen. Text substitution is
used rather than blurring, because the redacted cells are the ones the images
exist to show.
"""
import pathlib

from playwright.sync_api import sync_playwright

BASE = "https://160-250-135-47.sslip.io"
OUT = pathlib.Path("/root/beplus-site-assistant-doc/public/img")
TOKEN = pathlib.Path("/tmp/bsa_qa_token.txt").read_text().strip()
CHROME = "/root/.agent-browser/browsers/chrome-153.0.8010.36/chrome"

REDACT = """
() => {
  const MAIL = /[\\w.+-]+@[\\w-]+\\.[\\w.]{2,}/g;
  // Replace the bare IPv4 before the hyphenated hostname: the server's own IP
  // is written with dots in the IP column, and doing it the other way round
  // leaves that value behind.
  const IP = /\\b\\d{1,3}\\.\\d{1,3}\\.\\d{1,3}\\.\\d{1,3}\\b/g;
  const HOST = /160-250-135-47\\.sslip\\.io/g;
  const emails = ['alex@example.com', 'sam@example.com', 'jo@example.com'];
  const names = ['Alex Morgan', 'Sam Reed', 'Jo Blake'];

  // scrub(el, sample, allowName)
  //   sample    - index into the sample name/email lists, or null to leave as is
  //   allowName - only the Visitor cell may have its name replaced, so a Page
  //               cell (also short text) is never overwritten by accident
  const scrub = (el, sample, allowName) => {
    const walk = (node) => {
      for (const child of [...node.childNodes]) {
        if (child.nodeType === 3) {
          let t = child.nodeValue;
          if (!t) continue;
          if (sample !== null) {
            const bare = t.trim();
            const hasMail = MAIL.test(bare);
            const looksLikeName =
              allowName && !hasMail && bare && bare.length < 40 &&
              !/[:@\\d\\/]/.test(bare) &&
              !/^(guest|visitor|page|name|actions)$/i.test(bare);
            if (hasMail) t = t.replace(MAIL, emails[sample % emails.length]);
            if (looksLikeName) t = t.replace(bare, names[sample % names.length]);
          }
          if (IP.test(t)) t = t.replace(IP, '203.0.113.10');
          if (HOST.test(t)) t = t.replace(HOST, 'your-wordpress.com');
          if (t !== child.nodeValue) child.nodeValue = t;
        } else if (child.nodeType === 1) {
          walk(child);
        }
      }
    };
    walk(el);
  };

  // Rows are handled one at a time so a visitor's name and email stay paired.
  let k = 0;
  [...document.querySelectorAll('table tr')].forEach((tr) => {
    if (tr.querySelector('th')) { scrub(tr, null, false); return; }  // heading row
    const cellWithMail = [...tr.querySelectorAll('td')].find(
      td => /[\\w.+-]+@[\\w-]+\\.[\\w.]{2,}/.test(td.innerText || '')
    );
    const idx = cellWithMail ? k++ : null;
    [...tr.querySelectorAll('td')].forEach(td => {
      scrub(td, idx, td === cellWithMail);   // only the Visitor cell may rename
    });
  });
  // Everything outside the table (cards, hints) gets the global scrubs only.
  scrub(document.body, null, false);
  return 'done';
}
"""

PAGES = [
    ("Settings", "beplus-site-assistant", [
        ("AI & Model", "01-settings-ai.png"),
        ("Knowledge Base", "02-settings-knowledge.png"),
        ("Appearance & FAQs", "03-settings-appearance.png"),
        ("Leads & Email", "04-settings-leads.png"),
        ("Security & Limits", "05-settings-security.png"),
    ]),
    ("Conversations", "beplus-site-assistant-live", [
        ("Live Sessions", "06-conversations-live.png"),
        ("SEO Insights", "07-conversations-seo.png"),
        ("Storage", "08-conversations-storage.png"),
    ]),
]

BLUR_CSS = """
() => {
  const style = document.createElement('style');
  style.textContent = '#bsa-endpoint, #bsa-key { filter: blur(6px) !important; }';
  document.head.appendChild(style);
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

        for page_label, slug, tabs in PAGES:
            print(f"{page_label}:")
            for label, fname in tabs:
                page.goto(
                    f"{BASE}/wp-admin/admin.php?page={slug}",
                    wait_until="networkidle",
                )
                page.wait_for_timeout(1200)
                try:
                    page.get_by_role("button", name=label, exact=False).first.click()
                    page.wait_for_timeout(2000)
                except Exception as exc:
                    print(f"    ! tab {label}: {exc}")
                page.evaluate(REDACT)
                if "AI & Model" in label:
                    page.evaluate(BLUR_CSS)
                page.wait_for_timeout(400)

                # Verify no real PII survived before saving.
                leaks = page.evaluate(
                    """() => {
                      const t = document.body.innerText;
                      const bad = [];
                      if (/160\\.250\\.135\\.47|160-250-135-47/.test(t)) bad.push('host');
                      if (/116\\.110\\.155\\.40/.test(t)) bad.push('visitor-ip');
                      const m = t.match(/[\\w.+-]+@(?!example\\.com)[\\w-]+\\.[\\w.]{2,}/g);
                      if (m) bad.push('email:' + m.slice(0,2).join());
                      return bad;
                    }"""
                )
                flag = "SACH" if not leaks else f"CON LOT: {leaks}"
                print(f"    {fname:32s} {flag}")
                if leaks:
                    print("    -> BO QUA anh nay, se xu ly lai")
                    continue
                shot(page, fname)

        # Embed Script screen.
        print("Embed Script:")
        page.goto(
            f"{BASE}/wp-admin/admin.php?page=beplus-site-assistant-embed",
            wait_until="networkidle",
        )
        page.wait_for_timeout(900)
        page.evaluate("() => document.querySelectorAll('details').forEach(d => d.open = true)")
        page.wait_for_timeout(700)
        page.evaluate(REDACT)
        page.wait_for_timeout(400)
        shot(page, "09-embed-script.png")

        browser.close()
    print("xong")


if __name__ == "__main__":
    main()
