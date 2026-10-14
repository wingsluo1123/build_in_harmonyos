import os
import shlex
import sys
from conan import ConanFile
from conan.tools.build import can_run
from conan.tools.env import VirtualRunEnv


class QuorumTest(ConanFile):
    settings = "os", "arch", "compiler", "build_type"
    test_type = "explicit"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def generate(self):
        VirtualRunEnv(self).generate()

    def test(self):
        if can_run(self):
            package = self.dependencies["quorum"].package_folder
            perl = os.path.join(self.dependencies["perl"].package_folder, "bin", "perl")
            self.run(shlex.quote(sys.executable) + " " + shlex.quote(os.path.join(self.source_folder, "test.py"))
                     + " " + shlex.quote(package) + " " + shlex.quote(perl), env="conanrun")
