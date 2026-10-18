#!/usr/bin/env python3
"""Standalone consumer validation for qqc2-desktop-style5 5.116.0.

Invoked from test_package/conanfile.py test() via self.run(), satisfying the CI
gate that requires the test() method to actually execute a test program.
Verifies the org.kde.qqc2desktopstyle QML style module (qmldir + plugin) is
installed.
"""
import glob
import os
import sys


def fail(msg):
    print(f"FAIL: {msg}")
    sys.exit(1)


def main():
    if len(sys.argv) < 2:
        fail("usage: test_package.py <package_folder>")
    pkg = sys.argv[1]

    candidates = glob.glob(os.path.join(pkg, "lib", "*", "qml")) + \
                 [os.path.join(pkg, "lib", "qml"), os.path.join(pkg, "qml")]
    qml_root = next((c for c in candidates if os.path.isdir(c)), None)
    if not qml_root:
        fail(f"no QML module dir found under {pkg}/lib")

    module = os.path.join(qml_root, "org", "kde", "qqc2desktopstyle")
    if not os.path.isdir(module):
        fail(f"missing QML style module dir: {module}")

    qmldir_files = glob.glob(os.path.join(module, "**", "qmldir"), recursive=True)
    if not qmldir_files:
        fail(f"no qmldir under {module}")
    for qmldir in qmldir_files:
        print(f"[ok] qmldir present: {os.path.relpath(qmldir, qml_root)}")

    plugins = glob.glob(os.path.join(module, "**", "*.so"), recursive=True)
    if not plugins:
        fail(f"no style plugin shared object under {module}")
    print(f"[ok] style plugin present: {os.path.basename(plugins[0])}")

    print("ALL CHECKS PASSED for qqc2-desktop-style5 5.116.0")
    return 0


if __name__ == "__main__":
    sys.exit(main())
