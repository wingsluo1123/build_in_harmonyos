#!/usr/bin/env python3
"""Consumer test for tofi 0.9.1.

tofi is a command line tool (package_type = application), so the consumer
contract is "the shipped binary runs and behaves like tofi". The assertions
are performed by src/test_tofi.sh against bin/tofi of the installed package
(R34: the test must exercise the package artifact — removing bin/ makes it
fail).
"""
import os

from conan import ConanFile
from conan.errors import ConanException


class TestPackageConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"
    test_type = "explicit"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def test(self):
        pkg = self.dependencies["tofi"].package_folder
        binary = os.path.join(pkg, "bin", "tofi")
        if not os.path.isfile(binary):
            raise ConanException(f"tofi: installed binary missing: {binary}")
        self.output.info(f"tofi: testing installed binary {binary}")

        script = os.path.join(self.source_folder, "src", "test_tofi.sh")
        if not os.path.isfile(script):
            raise ConanException(f"tofi: consumer test script missing: {script}")
        # env="conanrun" puts the dependency lib dirs on LD_LIBRARY_PATH so the
        # binary can resolve libwayland-client.so.0 / libcairo.so.2
        self.run(f'bash "{script}" "{pkg}"', env="conanrun")
        self.output.info("tofi: consumer test finished")
