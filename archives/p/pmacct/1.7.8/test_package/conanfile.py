from conan import ConanFile
import os
import shlex
import sys


class PmacctTestConan(ConanFile):
    settings = "os", "arch", "compiler", "build_type"
    generators = "VirtualRunEnv"
    test_type = "explicit"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def test(self):
        package = self.dependencies[self.tested_reference_str].package_folder
        script = os.path.join(self.recipe_folder, "test_pmacct.py")
        self.run(f"{shlex.quote(sys.executable)} {shlex.quote(script)} "
                 f"{shlex.quote(package)}", env="conanrun")
