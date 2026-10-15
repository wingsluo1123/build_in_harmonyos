#!/usr/bin/env python3
"""Conan test_package - thrax 1.3.10 (HarmonyOS consumer test)."""
import os
import shlex
import shutil

from conan import ConanFile
from conan.tools.build import can_run


class ThraxTestConan(ConanFile):
    settings = "os", "arch"
    test_type = "explicit"
    generators = "VirtualRunEnv"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def test(self):
        dep = self.dependencies["thrax"]
        bindir = os.path.join(dep.package_folder, "bin")
        grammars = os.path.join(dep.package_folder, "share", "thrax", "grammars")
        libdir = os.path.join(dep.package_folder, "lib")
        header = os.path.join(dep.package_folder, "include", "thrax", "grm-manager.h")
        tools = [
            os.path.join(bindir, name)
            for name in ("thraxcompiler", "thraxrewrite-tester", "thraxrandom-generator")
        ]

        if not can_run(self):
            for path in tools + [header, grammars]:
                if not os.path.exists(path):
                    raise Exception(f"Missing packaged artifact: {path}")
            self.output.info("Cross-building; file layout check completed")
            return

        bash = shutil.which("bash") or os.environ.get("CONFIG_SHELL")
        if not bash:
            raise Exception("bash not found in PATH and CONFIG_SHELL is not set; cannot run test script")
        script = os.path.join(self.source_folder, "check_thrax.sh")
        args = " ".join(shlex.quote(path) for path in tools + [grammars, libdir])
        self.run(f"{shlex.quote(bash)} {shlex.quote(script)} {args}", env="conanrun")
