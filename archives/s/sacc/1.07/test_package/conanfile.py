"""Consumer checks for the installed sacc executable."""

import os
import shlex
import sys

from conan import ConanFile


class SaccTestConan(ConanFile):
    settings = "os", "arch", "compiler", "build_type"
    generators = "VirtualRunEnv"
    exports_sources = "test_gopher.py"
    test_type = "explicit"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def test(self):
        binary = os.path.join(self.dependencies["sacc"].package_folder, "bin", "sacc")
        self.run(
            f"SACC_BIN={shlex.quote(binary)} "
            f"{shlex.quote(sys.executable)} test_gopher.py",
            env="conanrun",
        )
