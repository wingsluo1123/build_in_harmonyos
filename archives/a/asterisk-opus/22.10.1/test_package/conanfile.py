#!/usr/bin/env python3
"""Conan test_package for asterisk-opus — runs the R34 consumer check."""
import os
import sys

from conan import ConanFile
from conan.tools.build import can_run


class TestPackageConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"
    test_type = "explicit"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def build_requirements(self):
        if can_run(self):
            self.tool_requires("asterisk/22.10.1")

    def test(self):
        if can_run(self):
            pkg = self.dependencies["asterisk-opus"].package_folder
            test_script = os.path.join(os.path.dirname(__file__),
                                       "test_asterisk_opus.py")
            self.run(f'{sys.executable} "{test_script}" "{pkg}"',
                     env="conanrun")
            consumer_script = os.path.join(os.path.dirname(__file__),
                                           "test_opus_sdp.py")
            core = self.dependencies.build["asterisk"].package_folder
            signing = " --sign" if self.settings.os == "OHOS" else ""
            self.run(f'{sys.executable} "{consumer_script}" "{pkg}" "{core}"{signing}',
                     env="conanrun")
