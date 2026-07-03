import os
from conan import ConanFile
from conan.tools.files import copy
from conan.tools.build import can_run


class CircumflexTestConan(ConanFile):
    settings = "os", "arch", "compiler", "build_type"
    test_type = "explicit"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def build(self):
        # Go binary is pre-built; no compilation needed for test
        pass

    def test(self):
        if can_run(self):
            # Verify the clx binary exists and is executable
            clx_bin = os.path.join(self.dependencies["circumflex"].package_folder, "bin", "clx")
            assert os.path.isfile(clx_bin), f"clx binary not found at {clx_bin}"
            # Run version check using full path
            self.run(f"{clx_bin} --help")
