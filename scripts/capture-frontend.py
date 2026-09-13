#!/usr/bin/env python3
"""Capture the visitor-facing screenshots from the live AlonePro demo site.

The widget shots must come from a real, fully-designed website rather than the
bare test install, so they are taken at https://alonepro.beplusthemes.com/ — a
live theme demo where the assistant actually runs.

Three images come out of this:
  10-widget-desktop.png  a real question and a real answer, in context
  11-widget-mobile.png   the same assistant at phone width
  12-lead-gate.png       the name + email screen a visitor meets first

Class names verified against the running widget: the launcher is `.bsa-fab`, the
panel gains `open`, the composer is `textarea.bsa-input`, send is `.bsa-send`,
the lead form is `.bsa-lead-name` / `.bsa-lead-email` / `.bsa-lead-submit`, and
messages are `.bsa-msg.bot` / `.bsa-msg.user`.

The launcher is clicked through JS because an ordinary click can land on the
hovering teaser bubble instead. The composer needs the native value setter plus
an `input` event; assigning `.value` alone does not reach the widget's state.
"""
import pathlib

from playwright.sync_api import sync_playwright

BASE = "https://alonepro.beplusthemes.com/"
OUT = pathlib.Path("/root/beplus-site-assistant-doc/public/img")
CHROME = "/root/.agent-browser/browsers/chrome-153.0.8010.36/chrome"

# A question this site genuinely answers, so the reply shows real content.
# Checked against the live demo: this one answers directly and its reply is short
# enough to be read inside the widget's fixed 540px panel, where some others run
# well past the visible area and would document a half-read answer.
QUESTION = "How do I contact you?"


def shot(page, name):
    """Screenshot the page.

    The theme demo shows a "Appearance" scheme switcher pinned to the right edge.
    A real visitor never sees it, and in a screenshot it reads as though the site
    were still in an editor, so it is hidden first.
    """
    page.evaluate(
        "() => { const s = document.querySelector('.scheme-switcher');"
        " if (s) s.style.display = 'none'; }"
    )
    page.wait_for_timeout(300)
    path = OUT / name
    page.screenshot(path=str(path))
    print(f"  {name:32s} {path.stat().st_size/1024:7.1f} KB")


def open_widget(page):
    page.evaluate("() => { const f = document.querySelector('.bsa-fab'); if (f) f.click(); }")
    page.wait_for_timeout(2200)
    return page.evaluate(
        "() => { const p = document.querySelector('.bsa-panel');"
        " return !!p && p.classList.contains('open'); }"
    )


def fill_lead(page):
    res = page.evaluate(
        """() => {
          const name = document.querySelector('.bsa-lead-name');
          const mail = document.querySelector('.bsa-lead-email');
          if (!name || !mail) return 'thieu o nhap';
          const set = (el, v) => {
            Object.getOwnPropertyDescriptor(window.HTMLInputElement.prototype, 'value')
              .set.call(el, v);
            el.dispatchEvent(new Event('input', { bubbles: true }));
            el.dispatchEvent(new Event('change', { bubbles: true }));
          };
          set(name, 'Alex Morgan');
          set(mail, 'alex@example.com');
          return 'ok';
        }"""
    )
    if res != "ok":
        print(f"    ! form: {res}")
        return False
    page.evaluate("() => { const b = document.querySelector('.bsa-lead-submit'); if (b) b.click(); }")
    page.wait_for_timeout(2500)
    return True


def ask(page, question):
    typed = page.evaluate(
        """(q) => {
          const box = document.querySelector('.bsa-input');
          if (!box) return false;
          Object.getOwnPropertyDescriptor(window.HTMLTextAreaElement.prototype, 'value')
            .set.call(box, q);
          box.dispatchEvent(new Event('input', { bubbles: true }));
          return true;
        }""",
        question,
    )
    if not typed:
        print("    ! khong thay o nhap")
        return False
    page.wait_for_timeout(700)
    page.evaluate("() => { const b = document.querySelector('.bsa-send'); if (b) b.click(); }")

    # Wait for the answer to appear and stop growing.
    last = ""
    for _ in range(45):
        page.wait_for_timeout(1000)
        cur = page.evaluate(
            "() => { const m = document.querySelector('.bsa-msg.bot');"
            " return m ? m.textContent.trim() : ''; }"
        )
        if cur and cur == last and len(cur) > 60:
            break
        last = cur
    print(f"    tra loi ({len(last)} ky tu): {last[:70]}...")

    # Long answers are collapsed behind "Show more". Expand it so the screenshot
    # shows the whole reply rather than a fade-out mid-sentence.
    expanded = page.evaluate(
        """() => {
          const b = document.querySelector('.bsa-show-more-btn');
          if (!b) return 'khong co nut';
          if (/show more/i.test(b.textContent || '')) { b.click(); return 'da bam'; }
          return 'da mo san';
        }"""
    )
    print(f"    mo rong: {expanded}")
    page.wait_for_timeout(1200)
    return True


def main():
    with sync_playwright() as p:
        browser = p.chromium.launch(
            executable_path=CHROME,
            args=["--no-sandbox", "--disable-gpu", "--disable-dev-shm-usage"],
        )
        # No WordPress cookies here: this is a visitor's browser, so no admin bar.
        ctx = browser.new_context(
            viewport={"width": 1440, "height": 900},
            device_scale_factor=2,
            ignore_https_errors=True,
        )
        page = ctx.new_page()
        page.goto(BASE, wait_until="domcontentloaded")
        page.wait_for_timeout(5000)

        print("mo widget:")
        print(f"    mo duoc: {open_widget(page)}")

        # 12 — the first screen a visitor sees.
        shot(page, "12-lead-gate.png")

        if fill_lead(page):
            print("    dat cau hoi that...")
            ask(page, QUESTION)
            shot(page, "10-widget-desktop.png")

            page.set_viewport_size({"width": 390, "height": 844})
            page.wait_for_timeout(2000)
            shot(page, "11-widget-mobile.png")

        browser.close()
    print("xong")


if __name__ == "__main__":
    main()
