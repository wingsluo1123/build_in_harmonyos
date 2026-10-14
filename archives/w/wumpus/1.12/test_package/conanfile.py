#!/usr/bin/env python3
"""Consumer test for the installed Wumpus command-line executables."""

import os
import shlex

from conan import ConanFile


class WumpusTestConan(ConanFile):
    settings = "os", "arch", "compiler", "build_type"
    generators = "VirtualRunEnv"
    test_type = "explicit"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def test(self):
        bash = os.environ.get("CONFIG_SHELL", "/data/service/hnp/bin/bash")
        self.run(f"{shlex.quote(bash)} test.sh", env="conanrun")
