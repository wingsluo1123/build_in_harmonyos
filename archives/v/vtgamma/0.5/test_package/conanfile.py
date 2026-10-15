#!/usr/bin/env python3
import os
from conan import ConanFile
from conan.tools.build import can_run

class TestPackageConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"
    test_type = "explicit"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def test(self):
        pkg = self.dependencies[self.tested_reference_str].package_folder
        perl_pkg = self.dependencies["perl"].package_folder
        test_script = os.path.join(os.path.dirname(__file__), "test_vtgamma.py")
        can = "1" if can_run(self) else "0"
        self.run(f"python3 {test_script} {pkg} {perl_pkg} {can}", env="conanrun")
