#!/usr/bin/env python3
"""Run deterministic integration tests against the installed SOAPsnp CLI."""
import os
import shlex
import sys

from conan import ConanFile
from conan.tools.build import can_run
from conan.tools.layout import basic_layout


class SoapsnpTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"
    test_type = "explicit"
    generators = "VirtualRunEnv"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def layout(self):
        basic_layout(self, build_folder="build")

    def test(self):
        if can_run(self):
            binary = os.path.join(self.dependencies["soapsnp"].package_folder,
                                  "bin", "soapsnp")
            script = os.path.join(self.source_folder, "test_cli.py")
            self.run("{} {} {}".format(shlex.quote(sys.executable),
                                      shlex.quote(script), shlex.quote(binary)),
                     env="conanrun")
