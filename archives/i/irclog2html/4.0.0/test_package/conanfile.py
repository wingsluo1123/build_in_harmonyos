from conan import ConanFile
from conan.errors import ConanException
from conan.tools.build import can_run
from conan.tools.layout import basic_layout
import os
import sys


class Irclog2htmlTestConan(ConanFile):
    settings = "os", "arch", "compiler", "build_type"
    test_type = "explicit"
    exports_sources = "functional.py"
    generators = "VirtualRunEnv"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def layout(self):
        basic_layout(self)

    def test(self):
        if not can_run(self):
            raise ConanException("target runtime unavailable; consumer was not run")
        script = os.path.join(self.source_folder, "functional.py")
        package = self.dependencies["irclog2html"].package_folder
        self.run(f'"{sys.executable}" "{script}" "{package}"', env="conanrun")
