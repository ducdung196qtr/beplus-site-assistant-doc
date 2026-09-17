#!/usr/bin/env python3
"""Capture clean documentation screenshots with subtle, authentic blur on WordPress chrome.

Applies:
- Top admin bar (#wpadminbar): subtle blur (3.5px) + dimming (0.55 opacity) so it remains
  visibly WordPress without attracting the eye to site names or personal logins.
- Left admin menu (#adminmenu): all other plugin/theme menu items blurred (3.5px) + dimmed (0.45 opacity).
- Plugin's own menu item (Site Assistant + Settings, Conversations, Embed Script): 100% sharp and clear.
- Main settings/conversations panel: 100% sharp and high-res.
- Sensitive credentials (API key, internal IP/endpoint): securely blurred/redacted.
"""
import json
import pathlib
from PIL import Image
from playwright.sync_api import sync_playwright

BASE = "https://160-250-135-47.sslip.io"
CHROME = "/root/.agent-browser/browsers/chrome-153.0.8010.36/chrome"
OUT_DIR = pathlib.Path("/root/beplus-site-assistant-doc/public/img")
COOKIE_FILE = pathlib.Path("/tmp/sufe_wp_cookies.json")

BLUR_CHROME_CSS = """
() => {
  const style = document.createElement('style');
  style.id = 'bsa-doc-blur-chrome';
  style.textContent = `
    /* Top admin bar: authentic softened blur */
    #wpadminbar {
      filter: blur(3.5px) opacity(0.6) !important;
      pointer-events: none !important;
    }

    /* Left menu: blur unrelated items, keep Site Assistant 100% sharp */
    #adminmenu > li:not(.toplevel_page_beplus-site-assistant) {
      filter: blur(3.5px) opacity(0.45) !important;
      pointer-events: none !important;
    }
    #collapse-menu {
      filter: blur(2.5px) opacity(0.3) !important;
    }

    /* Keep credentials blurred */
    #bsa-endpoint, #bsa-key, [id*="endpoint"], [id*="api-key"], [id*="bsa-key"] {
      filter: blur(6px) !important;
    }
  `;
  document.head.appendChild(style);
}
"""

REDACT_JS = """
() => {
  const MAIL = /[\\w.+-]+@[\\w-]+\\.[\\w.]{2,}/g;
  const IP = /\\b\\d{1,3}\\.\\d{1,3}\\.\\d{1,3}\\.\\d{1,3}\\b/g;
  const HOST = /160-250-135-47\\.sslip\\.io/g;
  const emails = ['alex@example.com', 'sam@example.com', 'jo@example.com'];
  const names = ['Alex Morgan', 'Sam Reed', 'Jo Blake'];

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

  let k = 0;
  [...document.querySelectorAll('table tr')].forEach((tr) => {
    if (tr.querySelector('th')) { scrub(tr, null, false); return; }
    const cellWithMail = [...tr.querySelectorAll('td')].find(
      td => /[\\w.+-]+@[\\w-]+\\.[\\w.]{2,}/.test(td.innerText || '')
    );
    const idx = cellWithMail ? k++ : null;
    [...tr.querySelectorAll('td')].forEach(td => {
      scrub(td, idx, td === cellWithMail);
    });
  });
  scrub(document.body, null, false);
}
"""

def prepare_page(page):
    page.evaluate(BLUR_CHROME_CSS)
    page.evaluate(REDACT_JS)
    page.wait_for_timeout(300)

def optimize_image(path):
    with Image.open(path) as im:
        im = im.convert("RGB")
        if im.width > 1600:
            new_h = round(im.height * 1600 / im.width)
            resample = getattr(Image, 'Resampling', Image).LANCZOS
            im = im.resize((1600, new_h), resample)
        im.save(path, "PNG", optimize=True)

def main():
    with open(COOKIE_FILE) as f:
        auth = json.load(f)

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
        ctx.add_cookies([
            {
                "name": auth["logged_in_name"],
                "value": auth["logged_in_val"],
                "domain": "160-250-135-47.sslip.io",
                "path": "/",
                "httpOnly": True,
                "secure": True,
                "sameSite": "Lax",
            },
            {
                "name": auth["secure_name"],
                "value": auth["secure_val"],
                "domain": "160-250-135-47.sslip.io",
                "path": "/wp-admin",
                "httpOnly": True,
                "secure": True,
                "sameSite": "Lax",
            },
        ])
        page = ctx.new_page()

        # 1. Settings tabs
        settings_tabs = [
            ("AI & Model", "01-settings-ai.png"),
            ("Knowledge Base", "02-settings-knowledge.png"),
            ("Appearance & FAQs", "03-settings-appearance.png"),
            ("Leads & Email", "04-settings-leads.png"),
            ("Security & Limits", "05-settings-security.png"),
        ]

        for tab_name, fname in settings_tabs:
            print(f"Capturing Settings -> {tab_name} ({fname})...")
            page.goto(f"{BASE}/wp-admin/admin.php?page=beplus-site-assistant", wait_until="networkidle")
            page.wait_for_timeout(800)
            try:
                page.get_by_role("button", name=tab_name, exact=False).first.click()
                page.wait_for_timeout(1000)
            except Exception as e:
                print(f"  Warning clicking tab {tab_name}: {e}")
            prepare_page(page)
            out_path = OUT_DIR / fname
            page.screenshot(path=str(out_path))
            optimize_image(out_path)
            print(f"  Saved {fname} ({out_path.stat().st_size} bytes)")

        # 2. Conversations tabs
        conv_tabs = [
            ("Live Sessions", "06-conversations-live.png"),
            ("SEO Insights", "07-conversations-seo.png"),
            ("Storage", "08-conversations-storage.png"),
        ]
        for tab_name, fname in conv_tabs:
            print(f"Capturing Conversations -> {tab_name} ({fname})...")
            page.goto(f"{BASE}/wp-admin/admin.php?page=beplus-site-assistant-live", wait_until="networkidle")
            page.wait_for_timeout(800)
            try:
                page.get_by_role("button", name=tab_name, exact=False).first.click()
                page.wait_for_timeout(1500)
            except Exception as e:
                print(f"  Warning clicking tab {tab_name}: {e}")
            prepare_page(page)
            out_path = OUT_DIR / fname
            page.screenshot(path=str(out_path))
            optimize_image(out_path)
            print(f"  Saved {fname} ({out_path.stat().st_size} bytes)")

        # 3. Embed Script page
        print("Capturing Embed Script (09-embed-script.png)...")
        page.goto(f"{BASE}/wp-admin/admin.php?page=beplus-site-assistant-embed", wait_until="networkidle")
        page.wait_for_timeout(1000)
        prepare_page(page)
        out_path = OUT_DIR / "09-embed-script.png"
        page.screenshot(path=str(out_path))
        optimize_image(out_path)
        print(f"  Saved 09-embed-script.png ({out_path.stat().st_size} bytes)")

        # 4. Export dialog
        print("Capturing Export dialog (13-export.png)...")
        page.goto(f"{BASE}/wp-admin/admin.php?page=beplus-site-assistant-live", wait_until="networkidle")
        page.wait_for_timeout(1200)
        try:
            page.get_by_role("button", name="Export", exact=False).first.click()
            page.wait_for_timeout(1200)
        except Exception as e:
            print(f"  Warning clicking Export: {e}")
        prepare_page(page)
        out_path = OUT_DIR / "13-export.png"
        page.screenshot(path=str(out_path))
        optimize_image(out_path)
        print(f"  Saved 13-export.png ({out_path.stat().st_size} bytes)")

        browser.close()
    print("All captures completed successfully!")

if __name__ == "__main__":
    main()
