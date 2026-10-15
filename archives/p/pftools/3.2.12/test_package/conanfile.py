#!/usr/bin/env python3
"""Consumer test for the packaged pftools executables (R34: 真实执行被测包）。"""

import os

from conan import ConanFile
from conan.tools.build import can_run


class PftoolsTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"
    test_type = "explicit"
    exports_sources = "test_pftools.sh"
    generators = "VirtualRunEnv"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def test(self):
        if not can_run(self):
            self.output.warning("Cannot run pftools executables in this environment")
            return

        pkg = self.dependencies[self.tested_reference_str].package_folder
        script = os.path.join(self.source_folder, "test_pftools.sh")
        self.run(
            f'sh "{script}" "{os.path.join(pkg, "bin")}" '
            f'"{os.path.join(pkg, "share", "examples")}"',
            env="conanrun",
        )
