import os

from conan import ConanFile
from conan.tools.build import can_run


class BlockhashTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"
    generators = "VirtualRunEnv"
    test_type = "explicit"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def test(self):
        if can_run(self):
            # R34: test must actually execute the packaged binary
            # Use env="conanrun" to source VirtualRunEnv (adds bindirs to PATH)
            self.run("blockhash --version", env="conanrun")
