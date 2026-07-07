import os

from conan import ConanFile


class RlwrapTestConan(ConanFile):
    """test_package for rlwrap executable — verifies rlwrap --version."""
    settings = "os", "arch", "compiler", "build_type"
    generators = "VirtualRunEnv"
    test_type = "explicit"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def test(self):
        rlwrap_pkg = self.dependencies["rlwrap"]
        rlwrap_bin = os.path.join(rlwrap_pkg.package_folder, "bin", "rlwrap")
        test_script = os.path.join(self.source_folder, "test.sh")
        self.run(f'sh "{test_script}" "{rlwrap_bin}"')
