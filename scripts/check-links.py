#!/usr/bin/env python3
"""Check every internal link on the documentation site.

We are about to point the WordPress.org listing at this site, so a dead link
here is a dead link in front of every prospective user. The site is small enough
to crawl completely rather than sample.

Only internal links are followed; external ones are reported but not fetched,
since a third-party site being slow or blocking us says nothing about our docs.
"""

import re
import sys
import urllib.error
import urllib.request
from collections import deque

BASE = "https://beplus-assistant-doc.beplus-agency.cloud"
UA = {"User-Agent": "Mozilla/5.0 (compatible; link-check/1.0)"}


def fetch(url):
    """Return (status, body) or (status, None) on error."""
    req = urllib.request.Request(url, headers=UA)
    try:
        with urllib.request.urlopen(req, timeout=25) as r:
            return r.status, r.read().decode("utf-8", "replace")
    except urllib.error.HTTPError as e:
        return e.code, None
    except Exception as e:
        return f"ERR({type(e).__name__})", None


def links_in(html):
    hrefs = re.findall(r'href="([^"]+)"', html)
    out = []
    for h in hrefs:
        h = h.strip()
        if h.startswith("#") or h.startswith("mailto:") or h.startswith("javascript:"):
            continue
        out.append(h)
    return out


def normalise(href):
    """Turn a link into an absolute URL, or the empty string if external."""
    if href.startswith("//"):
        return "https:" + href
    if href.startswith("http"):
        return href
    if href.startswith("/"):
        return BASE + href
    return BASE + "/" + href


def main():
    seen_pages, broken, external = set(), [], set()
    queue = deque(["/"])

    while queue:
        path = queue.popleft()
        if path in seen_pages:
            continue
        seen_pages.add(path)

        url = BASE + path
        status, body = fetch(url)
        mark = "ok" if status == 200 else "DEAD"
        print(f"  {mark:4s} {status!s:6s} {path}")
        if status != 200:
            broken.append((path, status))
            continue

        for href in links_in(body or ""):
            target = normalise(href)
            if not target.startswith(BASE):
                if target.startswith("http"):
                    external.add(target)
                continue
            clean = target[len(BASE):].split("#")[0].split("?")[0] or "/"
            if clean not in seen_pages and clean not in queue:
                queue.append(clean)

    print(f"\n  {len(seen_pages)} page(s) crawled, {len(broken)} broken, "
          f"{len(external)} external link(s) not fetched")

    if external:
        print("\n  external links found (not fetched):")
        for e in sorted(external)[:15]:
            print(f"    {e}")

    if broken:
        print("\n  BROKEN INTERNAL LINKS:")
        for path, status in broken:
            print(f"    {status}  {path}")
        sys.exit(1)

    print("\n  every internal link resolves")


if __name__ == "__main__":
    main()
