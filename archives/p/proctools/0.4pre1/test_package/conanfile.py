#!/usr/bin/env python3
"""Runtime tests for the OHOS proctools port."""

import os

from conan import ConanFile
from conan.tools.build import can_run


class ProctoolsTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"
    test_type = "explicit"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def test(self):
        if can_run(self):
            script = os.path.join(self.source_folder, "test_proctools.sh")
            self.run(
                'sh "{}" "{}"'.format(
                    script, self.dependencies["proctools"].package_folder
                ),
                env="conanrun",
            )
