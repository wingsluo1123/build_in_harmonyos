#!/usr/bin/env python3
"""Consumer test for mrbuild: build a real mini C project with the installed
Makefile templates using the OHOS cross toolchain, then verify the produced
shared-library symlink chain and ELF artifacts.

MRBUILD_DIR / MRBUILD_BINDIR come from the package buildenv (merged into
conanbuild); this test only adds CC/CXX pointing at the OHOS cross toolchain.
"""

import os
import shutil

from conan import ConanFile
from conan.tools.env import Environment


class MrbuildTestConan(ConanFile):
    settings = "os", "arch", "compiler", "build_type"
    test_type = "explicit"

    def build_requirements(self):
        self.tool_requires(self.tested_reference_str)

    def generate(self):
        compilers = self.conf.get("tools.build:compiler_executables",
                                  default={}, check_type=dict) or {}
        env = Environment()
        env.define("CC", self._compiler(compilers, "c", "clang"))
        env.define("CXX", self._compiler(compilers, "cpp", "clang++"))
        env.vars(self).save_script("testenv")

    def test(self):
        self.run("sh test.sh", env=["testenv", "conanbuild"])

    @staticmethod
    def _compiler(compilers, key, fallback):
        command = compilers.get(key)
        if command:
            first = command.split()[0]
            if (os.path.isabs(first) and os.path.isfile(first)) or shutil.which(first):
                return command
        return fallback
