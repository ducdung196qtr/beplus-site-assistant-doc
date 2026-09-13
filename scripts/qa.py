#!/usr/bin/env python3
"""QA the deployed docs site at several viewports.

Two things this deliberately does NOT flag, because both are correct behaviour
and flagging them drowns out real problems:

  * Wide tables and code blocks that scroll inside their own container. Nextra
    wraps them in an overflow-x box, so the inner rows are wider than the screen
    while the page itself never scrolls sideways. Only page-level overflow is a
    defect.
  * Images below the fold. They use loading="lazy", so naturalWidth is 0 until
    they are scrolled into view — the image URL is fetched directly to prove it
    actually resolves.

Run: python3 scripts/qa.py
"""
import json
import pathlib
import urllib.request

from playwright.sync_api import sync_playwright

BASE = "https://beplus-site-assistant-docs.vercel.app"
OUT = pathlib.Path("/tmp/doc-qa")
OUT.mkdir(exist_ok=True)
CHROME = "/root/.agent-browser/browsers/chrome-153.0.8010.36/chrome"

PAGES = [
    "/",
    "/installation",
    "/ai-settings",
    "/knowledge",
    "/appearance",
    "/leads-and-email",
    "/embed-script",
    "/embed-script/add-website",
    "/embed-script/snippet",
    "/embed-script/accepted",
    "/embed-script/rejected",
    "/embed-script/https",
    "/embed-script/manage",
    "/embed-script/bridge",
    "/conversations",
    "/seo-insights",
    "/storage",
    "/security",
    "/troubleshooting",
    "/changelog",
    "/about",
]

VIEWPORTS = [("desktop", 1440, 900), ("laptop", 1280, 800), ("mobile", 390, 844)]

MEASURE = """
() => {
  const de = document.documentElement;

  // An element is only a problem if it escapes the page AND is not inside
  // something that scrolls horizontally on purpose.
  const inScroller = (el) => {
    let n = el.parentElement;
    while (n && n !== document.body) {
      const ox = getComputedStyle(n).overflowX;
      if (ox === 'auto' || ox === 'scroll' || ox === 'hidden') return true;
      n = n.parentElement;
    }
    return false;
  };

  const escapees = [];
  document.querySelectorAll('article *').forEach(el => {
    const r = el.getBoundingClientRect();
    if (r.width > 0 && r.right > de.clientWidth + 1 && !inScroller(el)) {
      escapees.push({
        tag: el.tagName,
        cls: (el.className || '').toString().slice(0, 40),
        right: Math.round(r.right), vw: de.clientWidth,
      });
    }
  });

  const imgs = [...document.querySelectorAll('article img')].map(i => ({
    src: i.currentSrc || i.src,
    loading: i.loading,
    w: i.naturalWidth,
    alt: i.alt,
  }));

  return {
    vw: de.clientWidth,
    docScrollW: de.scrollWidth,
    pageOverflows: de.scrollWidth > de.clientWidth + 1,
    escapees: escapees,
    tables: document.querySelectorAll('article table').length,
    images: imgs,
    // is each table scrollable if it needs to be?
    tableScrollable: [...document.querySelectorAll('article table')].every(
      t => t.scrollWidth <= t.clientWidth + 1 || getComputedStyle(t).overflowX === 'auto'
        || getComputedStyle(t).overflowX === 'scroll'
    ),
  };
}
"""


def fetch_ok(url):
    try:
        req = urllib.request.Request(url, headers={"User-Agent": "docs-qa"})
        with urllib.request.urlopen(req, timeout=25) as r:
            return r.status, len(r.read())
    except Exception as exc:
        return 0, str(exc)


def main():
    problems = []
    checked = 0
    seen_images = {}
    with sync_playwright() as p:
        browser = p.chromium.launch(
            executable_path=CHROME,
            args=["--no-sandbox", "--disable-gpu", "--disable-dev-shm-usage"],
        )
        for name, w, h in VIEWPORTS:
            ctx = browser.new_context(
                viewport={"width": w, "height": h}, ignore_https_errors=True
            )
            page = ctx.new_page()
            for path in PAGES:
                checked += 1
                url = BASE + path
                try:
                    resp = page.goto(url, wait_until="networkidle", timeout=45000)
                    status = resp.status if resp else 0
                except Exception as exc:
                    problems.append(f"FAIL {name} {path} load: {exc}")
                    continue
                if status != 200:
                    problems.append(f"FAIL {name} {path} HTTP {status}")
                    continue

                m = page.evaluate(MEASURE)
                if m["pageOverflows"]:
                    problems.append(
                        f"FAIL {name} {path} page scrolls sideways "
                        f"({m['docScrollW']} > {m['vw']})"
                    )
                if m["escapees"]:
                    problems.append(
                        f"FAIL {name} {path} {len(m['escapees'])} element(s) escape the "
                        f"page (not in a scroller): {m['escapees'][:2]}"
                    )
                if not m["tableScrollable"]:
                    problems.append(f"FAIL {name} {path} a wide table cannot scroll")
                for img in m["images"]:
                    seen_images.setdefault(img["src"], {"alt": img["alt"], "loaded": img["w"] > 0})
                    if img["w"] == 0 and img["loading"] != "lazy":
                        problems.append(f"FAIL {name} {path} eager image has no pixels: {img['src'][-50:]}")
            ctx.close()
        browser.close()

    # Fetch every referenced image once, to prove the URLs really resolve.
    broken = 0
    for src, meta in seen_images.items():
        if meta["loaded"]:
            continue
        status, size = fetch_ok(src)
        if status != 200 or not isinstance(size, int) or size < 1000:
            broken += 1
            problems.append(f"FAIL image does not resolve: {src[-70:]} -> {status}")
    print(f"page views checked: {checked}")
    print(f"distinct images referenced: {len(seen_images)}, broken: {broken}")
    print(f"problems: {len(problems)}")
    for pr in problems:
        print(" ", pr)
    (OUT / "report.json").write_text(json.dumps({"problems": problems}, indent=1))


if __name__ == "__main__":
    main()
