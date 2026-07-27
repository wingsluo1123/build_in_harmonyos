#!/usr/bin/env python3
"""Conan test_package — cdo 2.6.3.

R34: Test actually executes cdo binary to verify it works.
"""
import os
import shutil

from conan import ConanFile
from conan.tools.build import can_run


class CdoTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"
    generators = "VirtualRunEnv"
    test_type = "explicit"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def _resolve_bash(self):
        for candidate in [
            os.environ.get("CONFIG_SHELL"),
            shutil.which("bash"),
            "/data/service/hnp/bin/bash",
            "/storage/Users/currentUser/usr/local/bin/bash",
            "/usr/bin/bash",
            "/bin/bash",
        ]:
            if candidate and os.path.isabs(candidate) and os.path.isfile(candidate) and os.access(candidate, os.X_OK):
                return candidate
            if candidate and not os.path.isabs(candidate):
                resolved = shutil.which(candidate)
                if resolved:
                    return resolved
        raise RuntimeError("No usable bash found for cdo test_package")

    def test(self):
        if can_run(self):
            cdo_bin = os.path.join(self.dependencies["cdo"].package_folder, "bin", "cdo")
            if not os.path.isfile(cdo_bin):
                raise FileNotFoundError(f"cdo binary not found at {cdo_bin}")
            bash = self._resolve_bash()
            script = os.path.join(self.source_folder, "test.sh")
            self.run(f'CDO_BIN="{cdo_bin}" "{bash}" "{script}"', env="conanrun")
            self.output.success("Conan test_package: success")
