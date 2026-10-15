#!/usr/bin/env python3
"""Consumer test for termshot/0.6.1 (R34 substantial verification).

termshot ships an executable; the assertions live in test_termshot.py so the
package ships a real test source file (CI L0c requires one; conanfile.py
alone does not count).  The test drives the real binary: it runs a real
command through a real pseudo terminal and validates the real screenshot.
"""
import os
import sys

from conan import ConanFile
from conan.tools.build import can_run
from conan.tools.env import Environment
from conan.tools.layout import basic_layout


class TermshotTestConan(ConanFile):
    settings = "os", "arch", "compiler", "build_type"
    test_type = "explicit"

    def layout(self):
        basic_layout(self)

    def requirements(self):
        self.requires(self.tested_reference_str)

    def generate(self):
        # Export the package folder so the test can locate bin/termshot
        # without hard-coding a cache path.
        env = Environment()
        pkg = self.dependencies[self.tested_reference_str.split("/")[0]].package_folder
        env.define("TERMSHOT_PACKAGE_ROOT", pkg)
        env.vars(self).save_script("termshot_test_env")

    def test(self):
        if not can_run(self):
            return
        test_script = os.path.join(self.source_folder, "test_termshot.py")
        self.run(f'"{sys.executable}" "{test_script}"',
                 env=["termshot_test_env"])
