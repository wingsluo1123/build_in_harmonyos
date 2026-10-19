import os
import shlex
from conan import ConanFile
from conan.tools.build import can_run
from conan.tools.env import VirtualRunEnv


class UcgTest(ConanFile):
    settings = "os", "arch", "compiler", "build_type"
    test_type = "explicit"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def generate(self):
        VirtualRunEnv(self).generate()

    def test(self):
        if can_run(self):
            binary = os.path.join(self.dependencies["ucg"].package_folder, "bin", "ucg")
            self.run('python3 ' + shlex.quote(os.path.join(self.source_folder, 'test.py'))
                     + ' ' + shlex.quote(binary), env="conanrun")
