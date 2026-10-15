#!/usr/bin/env python3
"""Conan recipe for purl 1.6 (pure Python, upstream pytest suite)."""

import os
from pathlib import Path
import sys

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.env import Environment
from conan.tools.files import copy, get
from conan.tools.layout import basic_layout


class PurlConan(ConanFile):
    name = "purl"
    version = "1.6"
    description = "Immutable URL construction, manipulation and RFC 6570 templates"
    license = "MIT"
    homepage = "https://github.com/codeinthehole/purl"
    url = "https://gitcode.com/OpenHarmonyPCDeveloper/build_in_harmonyos"
    package_type = "unknown"
    settings = "os", "arch", "compiler", "build_type"
    generators = "VirtualBuildEnv", "VirtualRunEnv"
    no_copy_source = True

    def requirements(self):
        self.requires("six/1.17.0", headers=False, libs=False, run=True)

    def build_requirements(self):
        self.tool_requires("pytest/9.1.1")

    def layout(self):
        basic_layout(self)

    def validate(self):
        if self.settings.os not in ("Linux", "OHOS"):
            raise ConanInvalidConfiguration("purl supports Linux and OHOS")

    def package_id(self):
        # Ship Python sources, with no interpreter-specific bytecode or ABI.
        self.info.clear()

    def source(self):
        get(self, **self.conan_data["sources"][str(self.version)], strip_root=True)

    def build(self):
        staging = os.path.join(self.build_folder, "staging")
        copy(self, "*", src=self.source_folder, dst=staging)
        for module in (Path(staging) / "purl").glob("*.py"):
            compile(module.read_text(encoding="utf-8"), str(module), "exec")
        environment = Environment()
        environment.prepend_path("PYTHONPATH", staging)
        environment.define("PYTHONDONTWRITEBYTECODE", "1")
        environment.define("PYTEST_DISABLE_PLUGIN_AUTOLOAD", "1")
        with environment.vars(self).apply():
            # Preserve upstream pytest.ini: includes doctests and all test files.
            self.run(
                f'"{sys.executable}" -m pytest',
                cwd=staging,
                env=["conanbuild", "conanrun"],
            )

    def package(self):
        staging = os.path.join(self.build_folder, "staging")
        copy(
            self, "*.py", src=os.path.join(staging, "purl"),
            dst=os.path.join(self.package_folder, "lib", "python", "site-packages", "purl"),
        )
        copy(self, "LICENSE", src=staging, dst=os.path.join(self.package_folder, "licenses"))

    def package_info(self):
        site = os.path.join(self.package_folder, "lib", "python", "site-packages")
        self.buildenv_info.prepend_path("PYTHONPATH", site)
        self.runenv_info.prepend_path("PYTHONPATH", site)
        self.runenv_info.define_path("PURL_PACKAGE_ROOT", site)
        self.cpp_info.includedirs = []
        self.cpp_info.libdirs = []
        self.cpp_info.bindirs = []
        self.cpp_info.libs = []
