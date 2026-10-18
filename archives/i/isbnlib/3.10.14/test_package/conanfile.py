"""Consumer tests against the installed Conan payload."""

import os
import sys

from conan import ConanFile
from conan.tools.build import can_run


class IsbnlibTestConan(ConanFile):
    settings = "os", "arch", "compiler", "build_type"
    generators = "VirtualRunEnv"
    test_type = "explicit"

    def requirements(self):
        self.requires(self.tested_reference_str, headers=False, libs=False, run=True)

    def test(self):
        if can_run(self):
            script = os.path.join(self.source_folder, "test_isbnlib.py")
            self.run(f'"{sys.executable}" -I -S "{script}"', env="conanrun")
