#!/usr/bin/env python3
"""Test qpack's native Conan package with the published Python runtime."""
import os
import shlex

from conan import ConanFile
from conan.errors import ConanException
from conan.tools.build import can_run
from conan.tools.env import Environment
from conan.tools.layout import basic_layout


class QpackTestConan(ConanFile):
    settings = "os", "arch", "compiler", "build_type"
    test_type = "explicit"
    exports_sources = "functional.py", "upstream_tests/**"
    generators = "VirtualRunEnv"

    def requirements(self):
        self.requires(self.tested_reference_str)
        self.requires("python/3.12.9#d8eda770878152bea40b42db9f7024cd", run=True)

    def layout(self):
        basic_layout(self)

    def test(self):
        if not can_run(self):
            raise ConanException("the target Python runtime cannot run")
        python_home = self.dependencies["python"].package_folder
        command = [os.path.join(python_home, "bin", "python3"), "-B",
                   os.path.join(self.source_folder, "functional.py"),
                   self.dependencies["qpack"].package_folder,
                   os.path.join(self.source_folder, "upstream_tests"),
                   os.path.join(self.build_folder, "functional-results.json")]
        environment = Environment()
        environment.define_path("PYTHONHOME", python_home)
        with environment.vars(self, scope="run").apply():
            self.run(shlex.join(command), env="conanrun")
