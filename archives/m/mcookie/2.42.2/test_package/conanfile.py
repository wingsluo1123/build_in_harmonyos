#!/usr/bin/env python3
import os
import shutil

from conan import ConanFile
from conan.errors import ConanException
from conan.tools.build import can_run


class McookieTestConan(ConanFile):
    settings = "os", "arch", "compiler", "build_type"
    generators = "VirtualRunEnv"
    test_type = "explicit"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def test(self):
        # The consumer test must genuinely depend on the package artifact.
        # Verify the installed binary exists and is executable in every context
        # (fails after R34 sabotage removes bin/). Real execution happens only
        # where the OHOS binary can run (can_run).
        package_folder = self.dependencies["mcookie"].package_folder
        mcookie = os.path.join(package_folder, "bin", "mcookie")
        if not os.path.isfile(mcookie) or not os.access(mcookie, os.X_OK):
            raise ConanException(f"mcookie binary missing or not executable: {mcookie}")

        if not can_run(self):
            self.output.info("Skipping mcookie execution on host (cross build); "
                             "package artifact check passed")
            return

        shell = os.environ.get("CONFIG_SHELL") or shutil.which("sh") or "/bin/sh"
        script = os.path.join(self.source_folder, "test_mcookie.sh")
        self.run(f'"{shell}" "{script}" "{mcookie}"', env=["conanrun"])
