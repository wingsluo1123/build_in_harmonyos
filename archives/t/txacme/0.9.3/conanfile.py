#!/usr/bin/env python3
"""Conan recipe for txacme 0.9.3 — pure-Python ACME protocol implementation for Twisted.

HarmonyOS PC adaptation: the upstream source tree contains **0** C/C++/Cython
files (pure Python; only setuptools packaging), so this recipe ships the import
packages directly instead of compiling anything:

  * ``txacme``            — the ACME client library
  * ``twisted.plugins``   — the ``txacme_endpoint`` Twisted endpoint plugin
  * ``integration``       — the integration helper package

Runtime dependencies (acme / attrs / eliot / josepy / pem / treq / twisted[tls] /
txsni / pyopenssl) are PyPI packages provided by pip in the consumer
environment: no conan recipes exist for them in the OHOS registry, so they are
deliberately **not** declared in ``requirements()`` (see notes.md).

The upstream test suite (``trial``) sources are shipped under
``share/txacme/upstream-tests`` so the consumer / CI can re-run them.
"""
import os
import shutil

from conan import ConanFile
from conan.errors import ConanException
from conan.tools.files import get, apply_conandata_patches, export_conandata_patches
from conan.tools.layout import basic_layout

_SITE = os.path.join("lib", "python3.12", "site-packages")


def _copytree(src, dst):
    shutil.copytree(
        src, dst,
        ignore=shutil.ignore_patterns("__pycache__", "*.pyc", "*.pyo"))


class TxacmeConan(ConanFile):
    name = "txacme"
    version = "0.9.3"
    description = "ACME protocol implementation for Twisted (Let's Encrypt client)"
    license = "Expat"
    homepage = "https://github.com/mithrandi/txacme"
    url = "https://github.com/mithrandi/txacme"

    package_type = "python-require"

    settings = "os", "arch", "compiler", "build_type"
    options = {"shared": [True, False]}
    default_options = {"shared": False}

    def export_sources(self):
        export_conandata_patches(self)

    def layout(self):
        basic_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def build(self):
        apply_conandata_patches(self)
        if not os.path.isdir(os.path.join(self.source_folder, "src", "txacme")):
            raise ConanException("src/txacme package directory not found in source")

    def package(self):
        src = os.path.join(self.source_folder, "src")
        site = os.path.join(self.package_folder, _SITE)
        os.makedirs(site, exist_ok=True)

        # import packages
        _copytree(os.path.join(src, "txacme"), os.path.join(site, "txacme"))
        plugin_dir = os.path.join(site, "twisted", "plugins")
        os.makedirs(plugin_dir, exist_ok=True)
        shutil.copy2(
            os.path.join(src, "twisted", "plugins", "txacme_endpoint.py"),
            os.path.join(plugin_dir, "txacme_endpoint.py"))
        _copytree(os.path.join(src, "integration"), os.path.join(site, "integration"))

        # upstream test suite (re-runnable by test_package / CI)
        tests_dir = os.path.join(self.package_folder, "share", "txacme", "upstream-tests")
        _copytree(os.path.join(src, "txacme", "test"),
                  os.path.join(tests_dir, "txacme", "test"))
        _copytree(os.path.join(src, "integration"),
                  os.path.join(tests_dir, "integration"))
        shutil.copy2(os.path.join(src, "txacme", "__init__.py"),
                     os.path.join(tests_dir, "txacme", "__init__.py"))
        shutil.copy2(os.path.join(src, "txacme", "_version.py"),
                     os.path.join(tests_dir, "txacme", "_version.py"))

    def package_info(self):
        self.cpp_info.libs = []
