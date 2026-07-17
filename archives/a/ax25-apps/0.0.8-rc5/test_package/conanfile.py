import os

from conan import ConanFile
from conan.tools.layout import basic_layout


class Ax25AppsTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"
    test_type = "explicit"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def layout(self):
        basic_layout(self)

    def test(self):
        # R34: Execute the packaged binary to verify it is functional.
        # Run the test script that checks all 6 binaries (call, listen,
        # ax25ipd, ax25rtd, ax25rtctl, ax25mond) for ELF execution.
        self.run(f"sh {os.path.join(self.source_folder, 'test_ax25ipd.sh')}", env="conanrun")
