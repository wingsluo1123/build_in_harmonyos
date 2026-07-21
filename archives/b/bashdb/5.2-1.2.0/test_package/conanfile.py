import os

from conan import ConanFile
from conan.tools.build import cross_building


class BashdbTestConan(ConanFile):
    """test_package for bashdb — runs bashdb --version to verify install."""
    settings = "os", "arch", "compiler", "build_type"
    generators = "VirtualRunEnv"
    test_type = "explicit"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def test(self):
        # bashdb is a pure bash script; skip on cross-compile builds
        # where the target bash cannot run on the build host.
        if cross_building(self):
            return
        self.run("bashdb --version", env="conanrun")
