#!/usr/bin/env python3
"""Conan recipe for acme-tiny 5.0.1 — Python ACME client for Let's Encrypt (setuptools)."""
import os
import sys

from conan import ConanFile
from conan.errors import ConanException
from conan.tools.files import get, export_conandata_patches, apply_conandata_patches
from conan.tools.layout import basic_layout


class AcmeTinyConan(ConanFile):
    name = "acme-tiny"
    version = "5.0.1"
    description = "A tiny script to issue and renew TLS certs from Let's Encrypt"
    license = "MIT"
    homepage = "https://github.com/diafygi/acme-tiny"
    url = "https://github.com/diafygi/acme-tiny"

    package_type = "application"
    settings = "os", "compiler", "build_type", "arch"

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        self.requires("openssl/3.5.6")

    def layout(self):
        basic_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def build(self):
        apply_conandata_patches(self)
        # Install setuptools and setuptools_scm (build dependencies)
        ret = self.run("python3 -m pip install setuptools setuptools_scm --quiet 2>&1", cwd=self.source_folder)
        if ret != 0:
            raise ConanException(f"pip install setuptools failed with exit code {ret}")
        # setuptools_scm needs a git repo or pretend version env var
        ret = self.run(
            "SETUPTOOLS_SCM_PRETEND_VERSION_FOR_ACME_TINY=5.0.1 python3 setup.py build",
            cwd=self.source_folder
        )
        if ret != 0:
            raise ConanException(f"setup.py build failed with exit code {ret}")

    def package(self):
        ret = self.run(
            f"SETUPTOOLS_SCM_PRETEND_VERSION_FOR_ACME_TINY=5.0.1 python3 setup.py install --prefix={self.package_folder}",
            cwd=self.source_folder
        )
        if ret != 0:
            raise ConanException(f"setup.py install failed with exit code {ret}")

    def package_info(self):
        self.cpp_info.bindirs = ["bin"]
        self.cpp_info.libdirs = []
        self.cpp_info.includedirs = []
        # Add site-packages to PYTHONPATH so acme-tiny script can find its module
        pyver = f"python{sys.version_info.major}.{sys.version_info.minor}"
        self.runenv_info.append_path("PYTHONPATH", os.path.join(self.package_folder, "lib", pyver, "site-packages"))
