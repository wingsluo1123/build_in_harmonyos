#!/usr/bin/env python3
"""Consumer test: run the installed edid-decode binary on real EDID samples."""

import os
import sys

from conan import ConanFile
from conan.tools.cmake import cmake_layout


class EdidDecodeTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"
    test_type = "explicit"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def layout(self):
        cmake_layout(self)

    def test(self):
        dep = self.dependencies[self.tested_reference_str]
        executable = os.path.join(dep.package_folder, "bin", "edid-decode")
        script = os.path.join(self.recipe_folder, "test_edid_decode.py")
        fixtures = os.path.join(self.recipe_folder, "fixtures")
        self.run(
            '"{}" "{}" "{}" "{}"'.format(
                sys.executable, script, executable, fixtures
            ),
            env="conanrun",
        )
