"""Exercise installed mblaze commands as a package consumer."""

import os

from conan import ConanFile


class MblazeTestConan(ConanFile):
    settings = "os", "arch", "compiler", "build_type"
    generators = "VirtualRunEnv"
    exports_sources = "test.sh"
    test_type = "explicit"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def test(self):
        package = self.dependencies["mblaze"].package_folder
        bindir = os.path.join(package, "bin")
        shell = (os.environ.get("CONFIG_SHELL", "/data/service/hnp/bin/bash")
                 if self.settings.os == "OHOS" else "/bin/sh")
        self.run(f'MBLAZE_BIN="{bindir}" "{shell}" test.sh', env="conanrun")
