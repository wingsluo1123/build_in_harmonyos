#!/usr/bin/env python3
"""Consumer test for the installed IGMPlot executable."""

import os

from conan import ConanFile


class IgmplotTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"
    generators = "VirtualRunEnv"
    test_type = "explicit"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def test(self):
        dep = self.dependencies["igmplot"]
        binary = os.path.join(dep.package_folder, "bin", "IGMPLOT")
        self.run(f'IGMPLOT_BIN="{binary}" sh test.sh', env="conanrun")
