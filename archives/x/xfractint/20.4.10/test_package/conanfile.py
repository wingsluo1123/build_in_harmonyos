#!/usr/bin/env python3
"""test_package for xfractint 20.4.10 — executes the installed OHOS binary."""

import os

from conan import ConanFile


class XfractintTestConan(ConanFile):
    settings = "os", "arch", "compiler", "build_type"
    generators = "VirtualRunEnv"
    test_type = "explicit"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def test(self):
        bash = os.environ.get("CONFIG_SHELL", "/data/service/hnp/bin/bash")
        test_sh = os.path.join(os.path.dirname(os.path.abspath(__file__)), "test_xfractint.sh")
        # Explicit self.run() so the CI L1 gate records the executed test.
        self.run(f"{bash} {test_sh}", env="conanrun")
