import os

from conan import ConanFile


class WirelessRegdbTestConan(ConanFile):
    """Test package for wireless-regdb — verifies regulatory database files exist."""
    settings = "os", "arch"
    generators = "VirtualRunEnv"
    test_type = "explicit"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def test(self):
        # Get the dependency's package folder via Conan 2.x API
        pkg_root = None
        if hasattr(self, "dependencies"):
            for name, dep in self.dependencies.items():
                if hasattr(dep, "package_folder") and dep.package_folder:
                    pkg_root = str(dep.package_folder)
                    break

        assert pkg_root, "Could not determine package_folder from dependencies"

        # Run test script (source file for CI L0c compliance)
        test_script = os.path.join(self.source_folder, "test_regulatory.sh")
        self.run(
            f'PKG_ROOT="{pkg_root}" bash "{test_script}"',
            env="conanrun"
        )
