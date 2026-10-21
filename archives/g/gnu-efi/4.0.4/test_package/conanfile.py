#!/usr/bin/env python3
import os
import sys

from conan import ConanFile
from conan.tools.layout import basic_layout


class GnuEfiTestConan(ConanFile):
    settings = "os", "arch", "compiler", "build_type"
    test_type = "explicit"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def layout(self):
        basic_layout(self)

    def test(self):
        dep = self.dependencies[self.tested_reference_str]
        script = os.path.join(self.recipe_folder, "test_gnuefi.py")
        self.run('"%s" "%s" "%s"' % (sys.executable, script, dep.package_folder))
