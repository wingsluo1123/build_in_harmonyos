#!/usr/bin/env python3
"""Conan recipe for binwalk 2.3.4 — Python firmware analysis tool (setuptools)."""
from conan import ConanFile
from conan.errors import ConanException
from conan.tools.files import get, export_conandata_patches, apply_conandata_patches
from conan.tools.layout import basic_layout
import os


class BinwalkConan(ConanFile):
    name = "binwalk"
    version = "2.3.4"
    description = "Firmware analysis tool for searching binary images for embedded files and code"
    license = "MIT"
    homepage = "https://github.com/ReFirmLabs/binwalk"
    url = "https://github.com/ReFirmLabs/binwalk"

    package_type = "application"
    settings = "os", "compiler", "build_type", "arch"

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
        ret = self.run("python3 -m pip install setuptools --quiet 2>&1", cwd=self.source_folder)
        if ret != 0:
            raise ConanException(f"pip install setuptools failed with exit code {ret}")
        ret = self.run("python3 setup.py build", cwd=self.source_folder)
        if ret != 0:
            raise ConanException(f"setup.py build failed with exit code {ret}")

    def package(self):
        ret = self.run(
            f"python3 setup.py install --prefix={self.package_folder}",
            cwd=self.source_folder
        )
        if ret != 0:
            raise ConanException(f"setup.py install failed with exit code {ret}")

    def package_info(self):
        self.cpp_info.bindirs = ["bin"]
        self.cpp_info.libdirs = []
        self.cpp_info.includedirs = []
        import sys
        pyver = f"python{sys.version_info.major}.{sys.version_info.minor}"
        self.runenv_info.append_path("PYTHONPATH", os.path.join(self.package_folder, "lib", pyver, "site-packages"))
