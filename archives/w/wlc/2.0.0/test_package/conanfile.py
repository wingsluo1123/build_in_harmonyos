"""Exercise pagination through the installed Conan package and real loopback HTTP."""
import os
import shlex

from conan import ConanFile
from conan.errors import ConanException
from conan.tools.build import can_run
from conan.tools.layout import basic_layout


class WlcTest(ConanFile):
    settings = "os", "arch", "compiler", "build_type"
    test_type = "explicit"
    exports_sources = "consumer.py", "fixtures/*"
    generators = "VirtualRunEnv"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def layout(self):
        basic_layout(self)

    def test(self):
        if not can_run(self):
            raise ConanException("The target Python consumer cannot run")
        package = self.dependencies["wlc"].package_folder
        self.run(shlex.join([
            "python3.12", "-B", os.path.join(self.source_folder, "consumer.py"),
            package, os.path.join(self.source_folder, "fixtures"),
        ]), env="conanrun")
