#!/usr/bin/env python3
"""Runtime checks for the packaged abcmidi tools."""

import os

from conan import ConanFile
from conan.tools.build import can_run


class AbcmidiTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"
    test_type = "explicit"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def test(self):
        if can_run(self):
            script = os.path.join(self.source_folder, "test_abcmidi.sh")
            self.run(
                'sh "{}" "{}"'.format(script, self.dependencies["abcmidi"].package_folder),
                env="conanrun",
            )
