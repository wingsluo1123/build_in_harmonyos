#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Test package for jpi-analyzer 0.2.0-git20260502.823a948"""

from conan import ConanFile
from conan.tools.build import can_run
import sys


class JpiAnalyzerTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"
    generators = "VirtualRunEnv"
    test_type = "explicit"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def test(self):
        if can_run(self):
            # Run the OHOS-specific end-to-end test script
            # (test() executes in test_package/ dir; conanrun env carries the
            # PYTHONPATH injected by the package and click)
            self.run(f'{sys.executable} test_ohos_jpi_analyzer.py', env="conanrun")
