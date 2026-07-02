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
        # Use explicit binary path from the dependency package folder
        # (VirtualRunEnv PATH may not work reliably on HarmonyOS/HMDFS)
        rlwrap_pkg = self.dependencies["rlwrap"]
        rlwrap_bin = os.path.join(rlwrap_pkg.package_folder, "bin", "rlwrap")
        if not os.path.isfile(rlwrap_bin):
            raise Exception(f"rlwrap binary not found at {rlwrap_bin}")
        # HMDFS bless: re-create binary to ensure execute permission
        import shutil
        tmp = rlwrap_bin + ".bless"
        shutil.copy2(rlwrap_bin, tmp)
        os.remove(rlwrap_bin)
        shutil.copy2(tmp, rlwrap_bin)
        os.remove(tmp)
        os.chmod(rlwrap_bin, 0o755)
        self.run(f'"{rlwrap_bin}" --version')
