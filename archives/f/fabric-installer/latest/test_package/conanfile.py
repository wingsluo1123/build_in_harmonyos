import os
from conan import ConanFile


class FabricInstallerTestConan(ConanFile):
    settings = "os", "arch"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def test(self):
        pkg_folder = self.dependencies["fabric-installer"].package_folder
        bin_dir = os.path.join(pkg_folder, "bin")
        # R34: exercise the packaged artifact — verify the script exists,
        # has a valid shebang, passes bash syntax check, and responds to --help.
        self.run(f"bash test_fabric_installer.sh {bin_dir}", env="conanrun")
        self.output.info("fabric-installer: OK")
