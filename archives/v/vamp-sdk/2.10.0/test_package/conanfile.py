#!/usr/bin/env python3
"""Two independent consumers of the installed Vamp SDK package."""

import os
from pathlib import Path

from conan import ConanFile
from conan.tools.env import Environment


class VampSdkTestConan(ConanFile):
    settings = "os", "arch", "compiler", "build_type"
    test_type = "explicit"
    exports_sources = "test_vamp_consumer.cpp"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def build(self):
        dependency = self.dependencies["vamp-sdk"]
        package = Path(dependency.package_folder)
        compilers = self.conf.get("tools.build:compiler_executables",
                                  default={}, check_type=dict) or {}
        cxx = compilers.get("cpp", "clang++")
        package_libs = " ".join(str(package / "lib" / f"lib{name}.a")
                                for name in dependency.cpp_info.libs)
        system_libs = " ".join(f"-l{name}" for name in
                               dependency.cpp_info.system_libs)
        self.run(
            f"{cxx} -std=c++17 -I{package / 'include'} "
            f"{Path(self.source_folder) / 'test_vamp_consumer.cpp'} "
            f"{package_libs} {system_libs} "
            f"-o {Path(self.build_folder) / 'test_vamp_consumer'}"
        )

    def test(self):
        package = Path(self.dependencies["vamp-sdk"].package_folder)
        env = Environment()
        env.define("VAMP_PATH", str(package / "lib" / "vamp"))
        env.define("VAMP_OHOS_TEST_DIR", self.build_folder)
        with env.vars(self).apply():
            self.run("./test_vamp_consumer portable", cwd=self.build_folder)
            if str(self.settings.os) == "OHOS":
                self.run("./test_vamp_consumer ohos-storage", cwd=self.build_folder)
