import os

from conan import ConanFile


class DdateTestConan(ConanFile):
    """test_package for ddate executable — runs test.sh which invokes the binary."""
    settings = "os", "arch", "compiler", "build_type"
    generators = "VirtualRunEnv"
    test_type = "explicit"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def test(self):
        # Use conanrun env so PATH includes the installed bin directory
        self.run("sh test.sh", env="conanrun")
