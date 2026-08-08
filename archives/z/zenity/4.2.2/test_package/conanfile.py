#!/usr/bin/env python3
"""Consumer test for zenity 4.2.2.

R34: test must actually exercise the package's binary.
Runs test.sh which invokes `zenity --version` and verifies
the output contains the expected version string.
Full dialog tests require a display server (not available
in terminal/headless environments).
"""

import os

from conan import ConanFile
from conan.tools.build import can_run


class ZenityTestConan(ConanFile):
    settings = "os", "arch", "compiler", "build_type"
    generators = "VirtualRunEnv"
    test_type = "explicit"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def test(self):
        if not can_run(self):
            self.output.info(
                "Cross-building: zenity binary runs on OHOS device"
            )
            return
        # R34: actually run the zenity binary via test.sh
        bash = os.environ.get(
            "CONFIG_SHELL", "/data/service/hnp/bin/bash"
        )
        self.run(f"{bash} test.sh", env="conanrun")
