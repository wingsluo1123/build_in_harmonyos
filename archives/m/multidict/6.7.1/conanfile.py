#!/usr/bin/env python3
"""Conan recipe for multidict 6.7.1 — Python library (setuptools + optional C extension).

HarmonyOS PC adaptation: packages the pure-Python fallback of multidict
(the _multidict C extension is optional; __init__.py degrades gracefully).
Requires typing-extensions (published in main).
"""
import os
import shutil

from conan import ConanFile
from conan.errors import ConanException
from conan.tools.files import get, apply_conandata_patches, export_conandata_patches
from conan.tools.layout import basic_layout


class MultidictConan(ConanFile):
    name = "multidict"
    version = "6.7.1"
    description = "multidict implementation"
    license = "Apache-2.0"
    homepage = "https://github.com/aio-libs/multidict"
    url = "https://github.com/aio-libs/multidict"

    package_type = "python-require"

    settings = "os", "compiler", "build_type", "arch"
    options = {"shared": [True, False]}
    default_options = {"shared": False}

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        self.requires("typing-extensions/4.16.0")

    def layout(self):
        basic_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def build(self):
        apply_conandata_patches(self)
        if not os.path.isdir(os.path.join(self.source_folder, "multidict")):
            raise ConanException("multidict package directory not found in source")

    def package(self):
        pkg_dir = os.path.join(self.package_folder, "lib", "python3.12", "site-packages", "multidict")
        os.makedirs(pkg_dir, exist_ok=True)
        src = os.path.join(self.source_folder, "multidict")
        for f in os.listdir(src):
            fpath = os.path.join(src, f)
            if os.path.isdir(fpath):
                continue  # skip subdirs (e.g. _multilib C headers)
            if f.endswith((".pyx", ".pxd", ".c", ".h")):
                continue  # C/Cython sources not needed; pure-Python fallback used
            shutil.copy2(fpath, os.path.join(pkg_dir, f))

    def package_info(self):
        self.cpp_info.libs = []