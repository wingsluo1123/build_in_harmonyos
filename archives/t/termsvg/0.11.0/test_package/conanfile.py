#!/usr/bin/env python3
"""Consumer test for termsvg/0.11.0 (R34 substantial verification).

termsvg ships an executable; the assertions live in test_termsvg.py so the
package ships a real test source file (CI L0c requires one; conanfile.py
alone does not count).  The test drives the real binary against a real
asciicast and validates the real SVG output.
"""
import os
import sys

from conan import ConanFile
from conan.tools.build import can_run
from conan.tools.layout import basic_layout


class TermsvgTestConan(ConanFile):
    settings = "os", "arch", "compiler", "build_type"
    test_type = "explicit"

    def layout(self):
        basic_layout(self)

    def requirements(self):
        self.requires(self.tested_reference_str)

    def generate(self):
        # Export the package folder so the test can locate bin/termsvg
        # without hard-coding a cache path.
        from conan.tools.env import Environment
        env = Environment()
        pkg = self.dependencies[self.tested_reference_str.split("/")[0]].package_folder
        env.define("TERMSVG_PACKAGE_ROOT", pkg)
        env.vars(self).save_script("termsvg_test_env")

    def test(self):
        if not can_run(self):
            return
        test_script = os.path.join(self.source_folder, "test_termsvg.py")
        self.run(f'"{sys.executable}" "{test_script}"',
                 env=["termsvg_test_env"])
