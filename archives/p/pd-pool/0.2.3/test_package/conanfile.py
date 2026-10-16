import os
import shlex
import sys
from conan import ConanFile

class PoolTest(ConanFile):
    settings = "os", "arch", "compiler", "build_type"
    test_type = "explicit"
    generators = "VirtualRunEnv"

    def requirements(self):
        self.requires(self.tested_reference_str)
        self.requires("puredata/0.54.1")

    def test(self):
        dep = self.dependencies[self.tested_reference_str]
        pd = os.path.join(self.dependencies["puredata"].package_folder, "bin", "pd")
        script = os.path.join(self.source_folder, "check_pool.py")
        self.run(shlex.join([sys.executable, script, pd, os.path.join(dep.package_folder, "lib", "pd-externals")]), env="conanrun")
