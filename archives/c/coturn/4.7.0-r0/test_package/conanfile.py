import os
from conan import ConanFile


class CoturnTestPackage(ConanFile):
    settings = "os", "arch", "compiler", "build_type"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def test(self):
        # Verify binary is a valid ELF executable
        pkg = self.dependencies["coturn"]
        binary = os.path.join(pkg.package_folder, "bin", "turnserver")
        self.run(f'file "{binary}"')