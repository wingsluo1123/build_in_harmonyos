"""One consumer of the actual installed Conan package."""
import os
import shlex

from conan import ConanFile
from conan.errors import ConanException
from conan.tools.build import can_run
from conan.tools.env import Environment
from conan.tools.layout import basic_layout


class MergedeepTestConan(ConanFile):
    settings = "os", "arch", "compiler", "build_type"
    test_type = "explicit"
    exports_sources = "consumer.py"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def layout(self):
        basic_layout(self)

    def generate(self):
        python = self.dependencies["python"].package_folder
        env = Environment()
        env.define("PYTHONHOME", python)
        env.prepend_path("LD_LIBRARY_PATH", os.path.join(python, "lib"))
        env.define("PYTHONPATH", os.path.join(
            self.dependencies["mergedeep"].package_folder, "lib", "python3.12", "site-packages"))
        env.vars(self).save_script("mergedeep-consumer")

    def test(self):
        if not can_run(self):
            raise ConanException("mergedeep target consumer cannot run in this environment")
        python = os.path.join(self.dependencies["python"].package_folder, "bin", "python3.12")
        command = [python, "-B", os.path.join(self.source_folder, "consumer.py"),
                   "--package-folder", self.dependencies["mergedeep"].package_folder]
        self.run(shlex.join(command), env="mergedeep-consumer")
