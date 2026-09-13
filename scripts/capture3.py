#!/usr/bin/env python3
"""Third pass: the export dialog, and the SEO gap report with real data.

The gap card is empty until an analysis has been run, so this script presses
Analyse first, waits for it to finish, and only then captures — an empty card
would document nothing.
"""
import pathlib

from playwright.sync_api import sync_playwright

BASE = "https://160-250-135-47.sslip.io"
OUT = pathlib.Path("/root/beplus-site-assistant-doc/public/img")
TOKEN = pathlib.Path("/tmp/bsa_qa_token.txt").read_text().strip()
CHROME = "/root/.agent-browser/browsers/chrome-153.0.8010.36/chrome"


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

        # ---------- SEO tab: run the analysis, then capture ----------
        print("mo SEO Insights:")
        page.goto(
            f"{BASE}/wp-admin/admin.php?page=beplus-site-assistant-live",
            wait_until="networkidle",
        )
        page.wait_for_timeout(1500)
        try:
            page.get_by_role("button", name="SEO Insights", exact=False).first.click()
            page.wait_for_timeout(2500)
        except Exception as exc:
            print(f"    ! tab SEO: {exc}")

        # Press Analyse and wait for it to settle.
        try:
            btn = page.get_by_role("button", name="Analyse", exact=False).first
            if btn and btn.is_visible():
                print("    bam Analyse...")
                btn.click()
                for i in range(90):
                    page.wait_for_timeout(2000)
                    busy = page.evaluate(
                        """() => {
                          const t = document.body.innerText;
                          return /analysing|analyzing|working|\\.\\.\\./i.test(t)
                            && !/analysed/i.test(t.split('·').slice(-1)[0] || '');
                        }"""
                    )
                    if not busy and i > 3:
                        break
                page.wait_for_timeout(2500)
            else:
                print("    ! khong thay nut Analyse")
        except Exception as exc:
            print(f"    ! Analyse: {exc}")

        page.wait_for_timeout(1500)
        shot(page, "07-conversations-seo.png")
        shot(page, "14-seo-gaps.png")

        # ---------- Export dialog ----------
        print("mo hop thoai Export:")
        page.goto(
            f"{BASE}/wp-admin/admin.php?page=beplus-site-assistant-live",
            wait_until="networkidle",
        )
        page.wait_for_timeout(2000)
        try:
            page.get_by_role("button", name="Export", exact=False).first.click()
            page.wait_for_timeout(1800)
            shot(page, "13-export.png")
        except Exception as exc:
            print(f"    ! Export: {exc}")

        browser.close()
    print("xong")


if __name__ == "__main__":
    main()
