#!/usr/bin/env python3
"""Downscale and optimise the documentation screenshots.

Captured at 2x for sharpness, but shipping 2x PNGs at ~2.5 MB each would make
the docs slow. Scale to a sane width and save optimised PNG.
"""
import pathlib

from PIL import Image

IMG = pathlib.Path("/root/beplus-site-assistant-doc/public/img")
MAX_W = 1600


def main():
    total_before = total_after = 0
    for path in sorted(IMG.glob("*.png")):
        before = path.stat().st_size
        total_before += before
        with Image.open(path) as im:
            im = im.convert("RGB")
            if im.width > MAX_W:
                h = round(im.height * MAX_W / im.width)
                im = im.resize((MAX_W, h), Image.LANCZOS)
            im.save(path, "PNG", optimize=True)
        after = path.stat().st_size
        total_after += after
        print(f"  {path.name:34s} {before/1024:7.1f} -> {after/1024:6.1f} KB")
    print(f"\n  tong: {total_before/1024/1024:.1f} MB -> {total_after/1024/1024:.1f} MB")


if __name__ == "__main__":
    main()
