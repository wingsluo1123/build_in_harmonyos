#!/usr/bin/env python3
"""Conan test package for autotrace 0.31.10."""
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
        pkg = self.dependencies[self.tested_reference_str].package_folder
        compilers = self.conf.get("tools.build:compiler_executables", default={}, check_type=dict) or {}
        cc = compilers.get("c") or os.environ.get("CC") or "cc"
        run_binary = "1" if can_run(self) else "0"
        script = os.path.join(self.source_folder, "test_autotrace.py")
        self.run(f'"{sys.executable}" "{script}" "{pkg}" "{cc}" "{run_binary}"', env="conanrun")
