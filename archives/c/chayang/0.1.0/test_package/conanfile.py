#!/usr/bin/env python3
"""Consumer test for chayang 0.1.0.

chayang is a command line tool (package_type = application), so the consumer
contract is "the shipped binary runs and behaves like chayang". The assertions
are performed by src/test_chayang.sh against bin/chayang of the installed
package (R34: the test must exercise the package artifact — removing bin/
makes it fail).
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
        pkg = self.dependencies["chayang"].package_folder
        binary = os.path.join(pkg, "bin", "chayang")
        if not os.path.isfile(binary):
            raise ConanException(f"chayang: installed binary missing: {binary}")
        self.output.info(f"chayang: testing installed binary {binary}")

        script = os.path.join(self.source_folder, "src", "test_chayang.sh")
        if not os.path.isfile(script):
            raise ConanException(f"chayang: consumer test script missing: {script}")
        # env="conanrun" puts the dependency lib dirs on LD_LIBRARY_PATH so the
        # binary can resolve libwayland-client.so.0
        self.run(f'bash "{script}" "{binary}"', env="conanrun")
        self.output.info("chayang: consumer test finished")
