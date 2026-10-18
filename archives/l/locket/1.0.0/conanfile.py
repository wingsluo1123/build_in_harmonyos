#!/usr/bin/env python3
"""Pure Python locket with all upstream process-lock tests."""

import os
from pathlib import Path
import sys

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.env import Environment
from conan.tools.files import apply_conandata_patches, copy, get
from conan.tools.layout import basic_layout


class LocketConan(ConanFile):
    name = "locket"
    version = "1.0.0"
    description = "File-based locks for Python threads and processes"
    license = "BSD-2-Clause"
    homepage = "https://github.com/mwilliamson/locket.py"
    url = "https://gitcode.com/OpenHarmonyPCDeveloper/build_in_harmonyos"
    package_type = "unknown"
    settings = "os", "arch", "compiler", "build_type"
    generators = "VirtualBuildEnv", "VirtualRunEnv"
    no_copy_source = True
    exports_sources = "patches/*"

    def build_requirements(self):
        self.tool_requires("pytest/9.1.1")

    def layout(self):
        basic_layout(self)

    def validate(self):
        if self.settings.os not in ("Linux", "OHOS"):
            raise ConanInvalidConfiguration("locket supports Linux and OHOS")

    def package_id(self):
        # The installed files are Python sources and a license, with no ABI.
        self.info.clear()

    def source(self):
        get(self, **self.conan_data["sources"][str(self.version)], strip_root=True)
        apply_conandata_patches(self)
        # Official upstream test helper; not a locket runtime dependency.
        get(
            self, **self.conan_data["test_sources"]["spur.local/0.3.7"],
            strip_root=True, destination="test-tools/spur-local",
        )

    def build(self):
        staging = os.path.join(self.build_folder, "staging")
        copy(self, "*", src=self.source_folder, dst=staging)
        for module in (Path(staging) / "locket").glob("*.py"):
            compile(module.read_text(encoding="utf-8"), str(module), "exec")
        environment = Environment()
        environment.prepend_path("PYTHONPATH", os.path.join(staging, "test-tools", "spur-local"))
        environment.prepend_path("PYTHONPATH", staging)
        environment.define("PYTHONDONTWRITEBYTECODE", "1")
        environment.define("PYTEST_DISABLE_PLUGIN_AUTOLOAD", "1")
        with environment.vars(self).apply():
            self.run(
                f'"{sys.executable}" -m pytest -v tests',
                cwd=staging, env=["conanbuild", "conanrun"],
            )

    def package(self):
        staging = os.path.join(self.build_folder, "staging")
        copy(
            self, "*.py", src=os.path.join(staging, "locket"),
            dst=os.path.join(self.package_folder, "lib", "python", "site-packages", "locket"),
        )
        copy(self, "LICENSE", src=staging, dst=os.path.join(self.package_folder, "licenses"))

    def package_info(self):
        site = os.path.join(self.package_folder, "lib", "python", "site-packages")
        self.buildenv_info.prepend_path("PYTHONPATH", site)
        self.runenv_info.prepend_path("PYTHONPATH", site)
        self.runenv_info.define_path("LOCKET_PACKAGE_ROOT", site)
        self.cpp_info.includedirs = []
        self.cpp_info.libdirs = []
        self.cpp_info.bindirs = []
        self.cpp_info.libs = []
