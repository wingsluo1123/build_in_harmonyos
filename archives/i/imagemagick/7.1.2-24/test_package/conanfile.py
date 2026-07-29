#!/usr/bin/env python3
"""Consumer smoke test for the packaged ImageMagick executable."""

import os

from conan import ConanFile
from conan.tools.build import can_run


class ImagemagickTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"
    generators = "VirtualRunEnv"
    test_type = "explicit"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def test(self):
        if can_run(self):
            bash = os.environ.get("CONFIG_SHELL", "bash")
            self.run(f"{bash} test.sh", env="conanrun")
