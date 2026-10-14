#!/usr/bin/env python3
"""Conan test_package for greenlet 3.5.6 — consumer check.

Runs test_greenlet.py (standalone test source, satisfies L0c) via self.run with
env="conanrun" so the conanrun PYTHONPATH injection is available.

Note: this package is a compiled C++ extension, so merely importing it in the
test proves the extension resolved its Python symbols (the `_Py_IsFinalizing`
link issue that musl exposes) — see notes.md.
"""
import os

from conan import ConanFile
from conan.errors import ConanException


class GreenletTestConan(ConanFile):
    settings = "os", "arch", "compiler", "build_type"
    test_type = "explicit"
    generators = "VirtualRunEnv"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def test(self):
        pkg = self.dependencies["greenlet"].package_folder
        site = os.path.join(pkg, "lib", "python3.12", "site-packages")
        if not os.path.isdir(os.path.join(site, "greenlet")):
            raise ConanException(f"greenlet package missing under {site}")
        exts = [f for f in os.listdir(os.path.join(site, "greenlet"))
                if f.endswith(".so")]
        if not exts:
            raise ConanException(f"greenlet extension (.so) missing under {site}")
        test_script = os.path.join(os.path.dirname(__file__),
                                   "test_greenlet.py")
        if not os.path.isfile(test_script):
            raise ConanException(f"test_greenlet.py missing: {test_script}")
        self.run(f"python3 '{test_script}' '{site}'", env="conanrun")
