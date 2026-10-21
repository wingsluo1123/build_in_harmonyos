import os
import shlex
import sys
from conan import ConanFile

class RNAhybridTest(ConanFile):
    settings = "os", "arch", "compiler", "build_type"
    test_type = "explicit"
    generators = "VirtualRunEnv"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def test(self):
        dep = self.dependencies[self.tested_reference_str]
        self.run(shlex.join([sys.executable, os.path.join(self.source_folder, "check_rna.py"), dep.package_folder]), env="conanrun")
