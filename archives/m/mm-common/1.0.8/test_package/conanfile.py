import sys

from conan import ConanFile


class TestPackageConan(ConanFile):
    """Consumer-side check: run the installed helpers the way a *mm module does."""

    settings = "os", "arch", "compiler", "build_type"
    test_type = "explicit"

    def requirements(self):
        self.tool_requires(self.tested_reference_str)

    def test(self):
        self.run(f'"{sys.executable}" test_mm_common.py', env="conanbuild")
