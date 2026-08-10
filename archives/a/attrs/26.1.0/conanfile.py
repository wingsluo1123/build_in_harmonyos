#!/usr/bin/env python3
"""Conan recipe for attrs 26.1.0 — pure Python library (setuptools/hatchling).

HarmonyOS PC adaptation: Python package with src/ layout,
copies the attr package into site-packages for import.
"""
import os
import shutil

from conan import ConanFile
from conan.errors import ConanException
from conan.tools.files import get, apply_conandata_patches, export_conandata_patches
from conan.tools.layout import basic_layout


class AttrsConan(ConanFile):
    name = "attrs"
    version = "26.1.0"
    description = "Python Classes Without Boilerplate"
    license = "MIT"
    homepage = "https://www.attrs.org/"
    url = "https://github.com/python-attrs/attrs"

    package_type = "python-require"

    settings = "os", "compiler", "build_type", "arch"
    options = {"shared": [True, False]}
    default_options = {"shared": False}

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        pass

    def layout(self):
        basic_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def build(self):
        apply_conandata_patches(self)
        # Pure Python package — src/attr must be present
        if not os.path.isdir(os.path.join(self.source_folder, "src", "attr")):
            raise ConanException("attr package directory not found in source")

    def package(self):
        pkg_dir = os.path.join(self.package_folder, "lib", "python3.12", "site-packages", "attr")
        os.makedirs(pkg_dir, exist_ok=True)
        src = os.path.join(self.source_folder, "src", "attr")
        for f in os.listdir(src):
            shutil.copy2(os.path.join(src, f), os.path.join(pkg_dir, f))

    def package_info(self):
        self.cpp_info.libs = []