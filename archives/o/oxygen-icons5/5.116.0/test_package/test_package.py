#!/usr/bin/env python3
"""Standalone consumer validation for oxygen-icons5 5.116.0 (data-only theme).

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
    oxygen = os.path.join(pkg, "share", "icons", "oxygen")
    base = os.path.join(oxygen, "base")

    index = os.path.join(oxygen, "index.theme")
    if not os.path.isfile(index):
        fail(f"missing {index}")
    print("[ok] share/icons/oxygen/index.theme present")

    sizes = ("8x8", "16x16", "22x22", "32x32", "48x48", "64x64", "128x128", "256x256")
    for s in sizes:
        if not os.path.isdir(os.path.join(base, s)):
            fail(f"missing size directory base/{s}")
    print(f"[ok] all size directories present: {', '.join(sizes)}")

    probe = os.path.join(base, "48x48", "apps", "kde.png")
    if not os.path.exists(probe):
        fail(f"missing representative icon {probe}")
    print("[ok] representative icon present: base/48x48/apps/kde.png")

    count = 0
    links = 0
    for root, _dirs, files in os.walk(base):
        for f in files:
            if f.lower().endswith(".png"):
                count += 1
            if os.path.islink(os.path.join(root, f)):
                links += 1
    if count < 1000:
        fail(f"unexpectedly few PNG icons under base/: {count}")
    print(f"[ok] {count} PNG icons under base/ ({links} symlink aliases preserved)")

    print("ALL CHECKS PASSED for oxygen-icons5 5.116.0")
    return 0


if __name__ == "__main__":
    sys.exit(main())
