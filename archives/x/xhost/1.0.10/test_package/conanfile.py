#!/usr/bin/env python3
"""Consumer test for the installed xhost application."""

import os
import sys

from conan import ConanFile


class XhostTestConan(ConanFile):
    settings = "os", "arch", "compiler", "build_type"
    generators = "VirtualRunEnv"
    test_type = "explicit"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def test(self):
        executable = os.path.join(
            self.dependencies["xhost"].package_folder, "bin", "xhost"
        )
        script = os.path.join(self.source_folder, "test_xhost.py")
        self.run(
            f'"{sys.executable}" "{script}" "{executable}"',
            env="conanrun",
        )