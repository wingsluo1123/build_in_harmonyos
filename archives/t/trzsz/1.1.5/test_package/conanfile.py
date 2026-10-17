import os
import shlex

from conan import ConanFile


class TrzszTestConan(ConanFile):
    settings = "os", "arch", "compiler", "build_type"
    generators = "VirtualRunEnv"
    test_type = "explicit"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def test(self):
        python = os.path.join(self.dependencies["python"].package_folder, "bin", "python3")
        for name in ("trz", "tsz"):
            self.run(name + " --help", env="conanrun")
        for script in ("functional.py", "upstream_tests.py", "progress_regression.py"):
            self.run(shlex.quote(python) + " " + shlex.quote(os.path.join(self.source_folder, script)),
                     env="conanrun")
