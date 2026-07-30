#!/usr/bin/env python3
"""Conan test_package for smpeg2 2.0.0."""

import os
import tempfile

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.build import can_run
from conan.tools.env import Environment
from conan.tools.gnu import PkgConfigDeps


class Smpeg2TestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"
    generators = "VirtualBuildEnv", "VirtualRunEnv"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def generate(self):
        PkgConfigDeps(self).generate()

    def _test_executable(self):
        suffix = ".exe" if self.settings.os == "Windows" else ""
        return os.path.join(tempfile.gettempdir(), "conan-smpeg2-test", "test_smpeg2" + suffix)

    def build(self):
        compiler_executables = self.conf.get(
            "tools.build:compiler_executables", default={}, check_type=dict
        )
        cxx = compiler_executables.get("cpp") or os.environ.get("CXX") or "c++"
        bin_path = self._test_executable()
        os.makedirs(os.path.dirname(bin_path), exist_ok=True)
        source = os.path.join(self.source_folder, "test_smpeg2.cpp")
        pkg_config_env = Environment()
        pkg_config_env.prepend_path("PKG_CONFIG_PATH", self.generators_folder)
        with pkg_config_env.vars(self).apply():
            self.run(
                f'{cxx} "{source}" -std=c++17 -o "{bin_path}" '
                "$(pkg-config --cflags --libs smpeg2)",
                env="conanbuild",
            )

    def test(self):
        bin_path = self._test_executable()
        if not os.path.isfile(bin_path):
            raise ConanInvalidConfiguration(f"Missing built test executable: {bin_path}")
        if can_run(self):
            self.run(bin_path, env="conanrun")
