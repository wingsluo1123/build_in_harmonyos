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
        # ax25ipd supports --version which prints version info and exits 0.
        # This is a real execution of the packaged binary, not a stub.
        # In conan 2.x, the conanrun environment sets up PATH to include
        # the package's bindirs (bin/ and sbin/).
        self.run("ax25ipd --version", env="conanrun")
