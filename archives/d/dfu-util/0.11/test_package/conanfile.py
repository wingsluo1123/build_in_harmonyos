#!/usr/bin/env python3
"""Conan runtime test for the dfu-util command-line package."""

import os

from conan import ConanFile
from conan.tools.build import can_run


class DfuUtilTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"
    generators = "VirtualRunEnv"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def test(self):
        if can_run(self):
            script = os.path.join(self.source_folder, "test.sh")
            bash = os.environ.get("CONFIG_SHELL", "/data/service/hnp/bin/bash")
            self.run(f'{bash} "{script}"', env="conanrun")
