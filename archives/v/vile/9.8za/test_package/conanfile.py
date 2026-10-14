#!/usr/bin/env python3
"""Conan test_package for vile 9.8za."""

import os
import shlex
import sys

from conan import ConanFile
from conan.errors import ConanException
from conan.tools.build import can_run


class VileTestConan(ConanFile):
    settings = "os", "arch", "compiler", "build_type"
    generators = "VirtualRunEnv"
    test_type = "explicit"

    def requirements(self):
        self.requires(self.tested_reference_str, run=True)

    def _bindir(self):
        dep = self.dependencies.get("vile")
        if dep is None:
            raise ConanException("vile dependency missing from the graph")
        rel = "bin"
        try:
            if dep.cpp_info.bindirs:
                rel = dep.cpp_info.bindirs[0]
        except Exception:
            rel = "bin"
        return rel if os.path.isabs(rel) else os.path.join(dep.package_folder, rel)

    def test(self):
        bindir = self._bindir()
        binary = os.path.join(bindir, "vile")

        checker = os.path.join(self.recipe_folder, "ohos_abi_check.py")
        self.run(" ".join(shlex.quote(arg) for arg in (
            sys.executable, checker, "--binary", binary)))

        if not can_run(self):
            self.output.info(
                "cross-building: vile runtime smoke tests are skipped here "
                "and are exercised on the HarmonyOS CI worker; the ABI checks "
                "above did execute against the packaged binary")
            return

        script = os.path.join(self.recipe_folder, "test.sh")
        shell = os.environ.get("CONFIG_SHELL") or "/data/service/hnp/bin/bash"
        self.run(
            f"{shlex.quote(shell)} {shlex.quote(script)} {shlex.quote(bindir)}",
            env="conanrun",
        )
