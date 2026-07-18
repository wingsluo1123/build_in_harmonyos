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
        expected = {
            "dropbear": "bin",
            "dbclient": "bin",
            "dropbearkey": "bin",
            "dropbearconvert": "bin",
        }
        for program, directory in expected.items():
            path = os.path.join(dependency.package_folder, directory, program)
            if not os.path.isfile(path):
                raise RuntimeError(f"missing packaged executable: {path}")

        if cross_building(self):
            self.output.info("cross-building: executable presence checks passed")
            return

        shell = os.environ.get("CONFIG_SHELL", "bash")
        self.run(f'{shell} test_dropbear.sh', env="conanrun")
