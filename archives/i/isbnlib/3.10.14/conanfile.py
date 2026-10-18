#!/usr/bin/env python3
"""Pure Python isbnlib with standard-library plugin discovery."""

import os
from pathlib import Path
import sys

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.env import Environment
from conan.tools.files import apply_conandata_patches, copy, export_conandata_patches, get
from conan.tools.layout import basic_layout


class IsbnlibConan(ConanFile):
    name = "isbnlib"
    version = "3.10.14"
    description = "Validate, convert, hyphenate and retrieve metadata for ISBNs"
    license = "LGPL-3.0-or-later"
    homepage = "https://github.com/xlcnd/isbnlib"
    url = "https://gitcode.com/OpenHarmonyPCDeveloper/build_in_harmonyos"
    package_type = "unknown"
    settings = "os", "arch", "compiler", "build_type"
    options = {"network_tests": [True, False]}
    default_options = {"network_tests": False}
    generators = "VirtualBuildEnv", "VirtualRunEnv"
    no_copy_source = True

    def build_requirements(self):
        self.tool_requires("pytest/9.1.1")

    def export_sources(self):
        export_conandata_patches(self)

    def layout(self):
        basic_layout(self)

    def validate(self):
        if sys.version_info < (3, 10):
            raise ConanInvalidConfiguration("Building with pytest 9 requires Python 3.10 or newer")
        if self.settings.os not in ("OHOS", "Linux"):
            raise ConanInvalidConfiguration("Validated platforms are OHOS and Linux")

    def package_id(self):
        self.info.clear()

    def source(self):
        get(self, **self.conan_data["sources"][str(self.version)], strip_root=True)
        apply_conandata_patches(self)

    def build(self):
        staging = os.path.join(self.build_folder, "staging")
        copy(self, "*", src=self.source_folder, dst=staging)
        for module in (Path(staging) / "isbnlib").rglob("*.py"):
            compile(module.read_text(encoding="utf-8-sig"), str(module), "exec")
        environment = Environment()
        environment.prepend_path("PYTHONPATH", staging)
        environment.define("PYTHONDONTWRITEBYTECODE", "1")
        environment.define("PYTEST_DISABLE_PLUGIN_AUTOLOAD", "1")
        selection = "" if self.options.network_tests else ' -m "not network"'
        if not self.options.network_tests:
            self.output.warning("Live-network upstream tests deselected; see full-device report")
        with environment.vars(self).apply():
            # Coverage is optional instrumentation; all test assertions stay intact.
            self.run(
                f'"{sys.executable}" -B -m pytest -o addopts= -ra{selection}',
                cwd=staging, env=["conanbuild", "conanrun"],
            )

    def package(self):
        staging = os.path.join(self.build_folder, "staging")
        copy(self, "*.py", src=os.path.join(staging, "isbnlib"),
             dst=os.path.join(self.package_folder, "lib", "python", "site-packages", "isbnlib"),
             excludes=("test/*", "__pycache__/*"))
        copy(self, "LICENSE*", src=staging,
             dst=os.path.join(self.package_folder, "licenses"), keep_path=False)

    def package_info(self):
        site = os.path.join(self.package_folder, "lib", "python", "site-packages")
        self.buildenv_info.prepend_path("PYTHONPATH", site)
        self.runenv_info.prepend_path("PYTHONPATH", site)
        self.runenv_info.define_path("ISBNLIB_PACKAGE_ROOT", site)
        self.cpp_info.includedirs = []
        self.cpp_info.libdirs = []
        self.cpp_info.bindirs = []
        self.cpp_info.libs = []
