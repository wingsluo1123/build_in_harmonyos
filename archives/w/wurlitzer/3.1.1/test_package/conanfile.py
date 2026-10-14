import os
import shlex
import sys

from conan import ConanFile


class WurlitzerTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"
    test_type = "explicit"
    generators = "VirtualRunEnv"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def test(self):
        module_dir = os.path.join(
            self.dependencies[self.tested_reference_str].package_folder,
            "share", "wurlitzer")
        script = os.path.join(self.recipe_folder, "test_wurlitzer.py")
        self.run(f'{shlex.quote(sys.executable)} {shlex.quote(script)} '
                 f'{shlex.quote(module_dir)}', env="conanrun")
