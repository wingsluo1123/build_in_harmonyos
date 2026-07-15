#!/usr/bin/env python3
"""test_package for daemontools — runs test.sh which exercises the tai64n/tai64nlocal/svstat binaries."""
import os

from conan import ConanFile


class DaemontoolsTestConan(ConanFile):
    settings = "os", "arch", "compiler", "build_type"
    generators = "VirtualRunEnv"
    test_type = "explicit"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def test(self):
        # conanrun env puts the package's bin/ on PATH, so binaries resolve.
        bash = os.environ.get("CONFIG_SHELL", "/data/service/hnp/bin/bash")
        self.run(f"{bash} test.sh", env="conanrun")
