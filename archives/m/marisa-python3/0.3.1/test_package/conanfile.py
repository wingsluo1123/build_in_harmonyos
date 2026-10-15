import os
import shlex

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.build import can_run
from conan.tools.env import VirtualRunEnv


class MarisaPythonTest(ConanFile):
    settings = "os", "arch", "compiler", "build_type"
    test_type = "explicit"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def generate(self):
        VirtualRunEnv(self).generate()

    def test(self):
        package = self.dependencies["marisa-python3"].package_folder
        site = os.path.join(package, "lib", "python3.12", "site-packages")
        if not all(os.path.isfile(os.path.join(site, item)) for item in ("marisa.py", "_marisa.so")):
            raise ConanInvalidConfiguration("Installed binding files are absent")
        if can_run(self):
            python = self.dependencies["python"].package_folder
            command = ("PYTHONHOME=" + shlex.quote(python) + " PYTHONPATH=" + shlex.quote(site) + " " +
                       shlex.join([os.path.join(python, "bin", "python3.12"), "-B",
                                   os.path.join(self.source_folder, "test.py"), site]))
            self.run(command, env="conanrun")
