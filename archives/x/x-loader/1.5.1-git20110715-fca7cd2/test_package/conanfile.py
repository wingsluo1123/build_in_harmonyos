#!/usr/bin/env python3
"""Consumer tests for the x-loader bootloader package."""

import os
import shlex

from conan import ConanFile


class XLoaderTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"
    generators = "VirtualRunEnv"
    test_type = "explicit"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def test(self):
        package = self.dependencies["x-loader"].package_folder
        script = os.path.join(self.source_folder, "test_x_loader.py")
        self.run(
            "python3 {} {}".format(shlex.quote(script), shlex.quote(package)),
            env="conanrun",
        )

        if str(self.settings.os) == "OHOS":
            ohos_script = os.path.join(self.source_folder, "test_ohos_x_loader.py")
            self.run(
                "python3 {} {}".format(
                    shlex.quote(ohos_script), shlex.quote(package)
                ),
                env="conanrun",
            )
