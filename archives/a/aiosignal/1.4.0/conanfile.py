#!/usr/bin/env python3
"""Conan recipe for aiosignal 1.4.0 — pure Python library (setuptools).

HarmonyOS PC adaptation: Python package at top level (aiosignal/),
copies the aiosignal package into site-packages for import.
Requires frozenlist (published in main).
"""
import os
import shutil

from conan import ConanFile
from conan.errors import ConanException
from conan.tools.files import get, apply_conandata_patches, export_conandata_patches
from conan.tools.layout import basic_layout


class AiosignalConan(ConanFile):
    name = "aiosignal"
    version = "1.4.0"
    description = "aiosignal: a list of registered asynchronous callbacks"
    license = "Apache-2.0"
    homepage = "https://github.com/aio-libs/aiosignal"
    url = "https://github.com/aio-libs/aiosignal"

    package_type = "python-require"

    settings = "os", "arch", "compiler", "build_type"
    options = {"shared": [True, False]}
    default_options = {"shared": False}

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        self.requires("frozenlist/1.8.0")

    def layout(self):
        basic_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def build(self):
        apply_conandata_patches(self)
        if not os.path.isdir(os.path.join(self.source_folder, "aiosignal")):
            raise ConanException("aiosignal package directory not found in source")

    def package(self):
        pkg_dir = os.path.join(self.package_folder, "lib", "python3.12", "site-packages", "aiosignal")
        os.makedirs(pkg_dir, exist_ok=True)
        src = os.path.join(self.source_folder, "aiosignal")
        for f in os.listdir(src):
            fpath = os.path.join(src, f)
            if os.path.isdir(fpath):
                continue
            shutil.copy2(fpath, os.path.join(pkg_dir, f))

    def package_info(self):
        self.cpp_info.libs = []