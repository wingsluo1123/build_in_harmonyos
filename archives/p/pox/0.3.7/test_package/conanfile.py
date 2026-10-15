#!/usr/bin/env python3
"""Consumer test for pox/0.3.7.

The assertions live in test_pox.py so the package ships a real test source
file (CI L0c requires one; conanfile.py alone does not count).
"""
import os
import sys

from conan import ConanFile
from conan.tools.build import can_run


class PoxTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"
    test_type = "explicit"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def test(self):
        if not can_run(self):
            return
        test_script = os.path.join(self.source_folder, "test_pox.py")
        self.run('"%s" "%s"' % (sys.executable, test_script), env="conanrun")
