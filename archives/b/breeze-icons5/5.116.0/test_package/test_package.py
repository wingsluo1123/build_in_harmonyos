#!/usr/bin/env python3
"""Standalone consumer validation for breeze-icons5 5.116.0 (data-only theme).

Invoked from test_package/conanfile.py test() via self.run(), satisfying the CI
gate that requires the test() method to actually execute a test program (a
data-only icon theme ships no compiled binary, so the "test program" is this
consumer validation script run on the build/target host).
"""
import os
import sys


def fail(msg):
    print(f"FAIL: {msg}")
    sys.exit(1)


def main():
    if len(sys.argv) < 2:
        fail("usage: test_package.py <package_folder>")
    pkg = sys.argv[1]
    icons = os.path.join(pkg, "share", "icons")
    breeze = os.path.join(icons, "breeze")
    breeze_dark = os.path.join(icons, "breeze-dark")

    for theme, root in (("breeze", breeze), ("breeze-dark", breeze_dark)):
        index = os.path.join(root, "index.theme")
        if not os.path.isfile(index):
            fail(f"missing {theme} index.theme ({index})")
        print(f"[ok] share/icons/{theme}/index.theme present")

    probe = os.path.join(breeze, "apps", "22", "kde.svg")
    if not os.path.isfile(probe):
        fail(f"missing representative icon {probe}")
    print("[ok] representative icon present: breeze/apps/22/kde.svg")

    count = 0
    for _root, _dirs, files in os.walk(breeze):
        count += sum(1 for f in files if f.endswith(".svg"))
    if count < 1000:
        fail(f"unexpectedly few breeze SVG icons: {count}")
    print(f"[ok] {count} SVG icons in breeze theme")

    dark = 0
    for _root, _dirs, files in os.walk(breeze_dark):
        dark += sum(1 for f in files if f.endswith(".svg"))
    if dark < 100:
        fail(f"unexpectedly few breeze-dark icons: {dark}")
    print(f"[ok] {dark} SVG icons in breeze-dark theme (incl. light fallbacks)")

    print("ALL CHECKS PASSED for breeze-icons5 5.116.0")
    return 0


if __name__ == "__main__":
    sys.exit(main())
