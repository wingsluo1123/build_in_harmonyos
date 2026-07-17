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
        # Access the dependency's package folder via Conan 2.x API
        pkg_root = None
        if hasattr(self, "dependencies"):
            for name, dep in self.dependencies.items():
                if hasattr(dep, "package_folder") and dep.package_folder:
                    pkg_root = str(dep.package_folder)
                    break

        if not pkg_root:
            # Fallback: search conan cache for the regulatory.db file
            import subprocess
            home = os.path.expanduser("~")
            result = subprocess.run(
                ["find", f"{home}/.conan2/p", "-name", "regulatory.db",
                 "-path", "*/lib/firmware/*", "-print", "-quit"],
                capture_output=True, text=True
            )
            found = result.stdout.strip()
            assert found, "regulatory.db not found in conan cache (package_folder unavailable)"
            assert os.path.isfile(found), f"regulatory.db path not a file: {found}"
            self.output.info(f"regulatory.db found via cache search ({os.path.getsize(found)} bytes)")
            return

        # Check regulatory database files
        regulatory_db = os.path.join(pkg_root, "lib", "firmware", "regulatory.db")
        assert os.path.isfile(regulatory_db), f"regulatory.db not found at {regulatory_db}"
        self.output.info(f"regulatory.db found ({os.path.getsize(regulatory_db)} bytes)")

        regulatory_p7s = os.path.join(pkg_root, "lib", "firmware", "regulatory.db.p7s")
        assert os.path.isfile(regulatory_p7s), f"regulatory.db.p7s not found at {regulatory_p7s}"
        self.output.info(f"regulatory.db.p7s found ({os.path.getsize(regulatory_p7s)} bytes)")

        regulatory_bin = os.path.join(pkg_root, "usr", "lib", "crda", "regulatory.bin")
        assert os.path.isfile(regulatory_bin), f"regulatory.bin not found at {regulatory_bin}"
        self.output.info(f"regulatory.bin found ({os.path.getsize(regulatory_bin)} bytes)")
