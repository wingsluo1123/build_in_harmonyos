#!/usr/bin/env python3
"""Conan test package for autotrace homebrew."""
import os
import sys

from conan import ConanFile
from conan.tools.build import can_run
from conan.tools.layout import basic_layout


class AutotraceTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"
    test_type = "explicit"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def layout(self):
        basic_layout(self)

    def test(self):
        if not can_run(self):
            return
        pkg = self.dependencies[self.tested_reference_str].package_folder
        script = os.path.join(self.source_folder, "test_autotrace.py")
        self.run(f'"{sys.executable}" "{script}" "{pkg}"', env="conanrun")
