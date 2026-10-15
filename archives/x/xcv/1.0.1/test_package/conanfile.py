#!/usr/bin/env python3
"""Consumer test for xcv: run the installed xcv in a real cut/copy/paste workflow."""
import os

from conan import ConanFile
from conan.errors import ConanException


class XcvTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"
    test_type = "explicit"
    generators = "VirtualRunEnv"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def test(self):
        xcv = os.path.join(self.dependencies["xcv"].package_folder, "bin", "xcv")
        if not os.path.isfile(xcv):
            raise ConanException(f"xcv not found: {xcv}")
        # OHOS: /bin/bash does not exist, drive the test with the hnp bash.
        bash = os.environ.get("CONFIG_SHELL", "/data/service/hnp/bin/bash")
        script = os.path.join(self.recipe_folder, "test_xcv.sh")
        self.run(f'"{bash}" "{script}" "{xcv}"', env="conanrun")
