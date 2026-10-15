#!/usr/bin/env python3
import os
import shutil

from conan import ConanFile
from conan.tools.build import can_run


class UuidgenTestConan(ConanFile):
    settings = "os", "arch", "compiler", "build_type"
    generators = "VirtualRunEnv"
    test_type = "explicit"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def test(self):
        if not can_run(self):
            self.output.info("Skipping uuidgen consumer test: target binaries cannot run in this context")
            return

        package_folder = self.dependencies["uuidgen"].package_folder
        uuidgen = os.path.join(package_folder, "bin", "uuidgen")
        assert os.path.isfile(uuidgen), f"uuidgen missing: {uuidgen}"

        shell = os.environ.get("CONFIG_SHELL") or shutil.which("sh") or "/bin/sh"
        script = os.path.join(self.source_folder, "test_uuidgen.sh")
        self.run(f'"{shell}" "{script}" "{uuidgen}"', env=["conanrun"])
