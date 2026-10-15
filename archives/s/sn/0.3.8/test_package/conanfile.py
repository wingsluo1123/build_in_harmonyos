#!/usr/bin/env python3

import os
import shutil

from conan import ConanFile


class SnTestConan(ConanFile):
    """test_package for sn -- runs test_sn.sh, which drives the 14 packaged
    binaries in their deterministic usage / spool-error paths (no network,
    no spool, no port binding).  On OHOS devices the binaries execute
    natively; under WSL qemu emulation the script preloads the guest's
    libfdchkshim.so for the __fd_chk symbol (see test_sn.sh header)."""
    settings = "os", "compiler", "build_type", "arch"
    generators = "VirtualRunEnv"
    test_type = "explicit"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def test(self):
        package_folder = self.dependencies["sn"].package_folder
        bin_dir = os.path.join(package_folder, "bin")
        assert os.path.isfile(os.path.join(bin_dir, "snscan")), \
            f"sn binaries not found in {bin_dir}"
        shell = (os.environ.get("CONFIG_SHELL")
                 or shutil.which("bash")
                 or shutil.which("sh")
                 or "/bin/sh")
        script = os.path.join(self.recipe_folder, "test_sn.sh")
        self.run(f'"{shell}" "{script}" "{bin_dir}"', env="conanrun")
