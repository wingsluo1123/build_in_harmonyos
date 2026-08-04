import os

from conan import ConanFile


class AsciiquariumTestConan(ConanFile):
    """test_package for asciiquarium script — runs test.sh which verifies the script."""
    settings = "os", "arch", "compiler", "build_type"
    generators = "VirtualRunEnv"
    test_type = "explicit"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def test(self):
        # OHOS: /system/bin/sh (mksh) may not execute scripts reliably.
        # Use bash to wrap script execution.
        bash = os.environ.get("CONFIG_SHELL", "/data/service/hnp/bin/bash")
        self.run(f"{bash} test.sh", env="conanrun")
