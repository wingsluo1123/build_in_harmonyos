#!/usr/bin/env python3
"""Conan L1 test for the Dropbear command-line tools."""
import os

from conan import ConanFile
from conan.tools.build import cross_building


class DropbearTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"
    generators = "VirtualRunEnv"
    test_type = "explicit"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def test(self):
        dependency = self.dependencies["dropbear"]
        binary_dir = os.path.join(dependency.package_folder, "bin")
        if not os.path.isdir(binary_dir):
            raise RuntimeError(f"missing packaged binary directory: {binary_dir}")
        for program in ("dropbear", "dbclient", "dropbearkey", "dropbearconvert"):
            path = os.path.join(binary_dir, program)
            if not os.path.isfile(path):
                raise RuntimeError(f"missing packaged executable: {path}")

        if cross_building(self):
            self.output.info("cross-building: executable presence checks passed")
            return

        shell = os.environ.get("CONFIG_SHELL", "bash")
        self.run(f'{shell} test_dropbear.sh', env="conanrun")
