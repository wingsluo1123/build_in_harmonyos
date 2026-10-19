#!/usr/bin/env python3
"""Standalone consumer validation for kquickcharts5 5.116.0.

Invoked from test_package/conanfile.py test() via self.run(), satisfying the CI
gate that requires the test() method to actually execute a test program.
Verifies the QML chart modules are installed and their plugins are loadable
shared objects.
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

    # Locate the QML module dir (KDE_INSTALL_QMLDIR is lib/qt5/qml or lib/qml).
    candidates = glob.glob(os.path.join(pkg, "lib", "*", "qml")) + \
                 [os.path.join(pkg, "lib", "qml"), os.path.join(pkg, "qml")]
    qml_root = next((c for c in candidates if os.path.isdir(c)), None)
    if not qml_root:
        fail(f"no QML module dir found under {pkg}/lib")

    for uri in ("org.kde.quickcharts", "org.kde.quickcharts.controls"):
        mdir = os.path.join(qml_root, *uri.split("."))
        qmldir = os.path.join(mdir, "qmldir")
        if not os.path.isfile(qmldir):
            fail(f"missing qmldir for {uri}: {qmldir}")
        with open(qmldir, encoding="utf-8", errors="replace") as f:
            content = f.read()
        if "plugin" not in content.lower() and "classname" not in content.lower():
            fail(f"qmldir for {uri} declares no plugin: {content[:120]!r}")
        plugins = glob.glob(os.path.join(mdir, "*.so")) + \
                  glob.glob(os.path.join(mdir, "lib*.so"))
        if not plugins:
            fail(f"no plugin shared object under {mdir}")
        print(f"[ok] QML module {uri}: qmldir + plugin ({os.path.basename(plugins[0])})")

    print("ALL CHECKS PASSED for kquickcharts5 5.116.0")
    return 0


if __name__ == "__main__":
    sys.exit(main())
