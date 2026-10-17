#!/usr/bin/env python3
"""Consumer test for the installed pem command."""
import os
import sys

from conan import ConanFile
from conan.tools.build import can_run


class PemTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"
    generators = "VirtualRunEnv"
    test_type = "explicit"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def test(self):
        if not can_run(self):
            return
        bash = os.environ.get("CONFIG_SHELL", "/data/service/hnp/bin/bash")
        self.run('%s test.sh' % bash, env="conanrun")
        self.run('"%s" test_pem_consumer.py' % sys.executable, env="conanrun")
