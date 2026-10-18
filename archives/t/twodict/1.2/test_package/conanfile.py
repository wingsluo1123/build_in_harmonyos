import os
import shlex

from conan import ConanFile
from conan.tools.env import VirtualBuildEnv, VirtualRunEnv


class TwodictTestConan(ConanFile):
    settings = "os", "arch", "compiler", "build_type"

    def requirements(self):
        self.requires(self.tested_reference_str, run=True)

    def build_requirements(self):
        self.tool_requires("python/3.12.9")

    def generate(self):
        VirtualBuildEnv(self).generate()
        VirtualRunEnv(self).generate()

    def test(self):
        interpreter = os.path.join(self.dependencies.build["python"].package_folder,
                                   "bin", "python3")
        script = os.path.join(self.source_folder, "consumer.py")
        package_dir = os.path.join(self.dependencies["twodict"].package_folder,
                                   "lib", "python")
        self.run("{} -B {} {}".format(shlex.quote(interpreter), shlex.quote(script),
                                      shlex.quote(package_dir)),
                 env=["conanbuild", "conanrun"])
