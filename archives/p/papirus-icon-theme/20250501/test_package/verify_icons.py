#!/usr/bin/env python3
"""Verify icons smoke test — papirus-icon-theme resource package.

Called by test_package/conanfile.py via self.run().
Performs minimal sanity checks on installed icon theme structure.
"""
import os
import sys


def verify(icons_root):
    errors = []

    # Check three index.theme exist
    for theme in ("Papirus", "Papirus-Dark", "Papirus-Light"):
        index = os.path.join(icons_root, theme, "index.theme")
        if not os.path.isfile(index):
            errors.append(f"Missing index.theme: {theme}")

    # Check at least one SVG exists
    for theme in ("Papirus",):
        theme_dir = os.path.join(icons_root, theme)
        svg_count = 0
        for root, _dirs, files in os.walk(theme_dir, followlinks=False):
            for f in files:
                if f.endswith(".svg"):
                    fp = os.path.join(root, f)
                    if os.path.islink(fp) and not os.path.exists(fp):
                        continue
                    svg_count += 1
        if svg_count == 0:
            errors.append(f"No readable SVGs in {theme}")
        break  # check only base Papirus

    if errors:
        for e in errors:
            print(f"ERROR: {e}")
        return 1
    print(f"OK: {icons_root} — icons verified")
    return 0


if __name__ == "__main__":
    icons_root = sys.argv[1] if len(sys.argv) > 1 else "/nonexistent"
    sys.exit(verify(icons_root))
