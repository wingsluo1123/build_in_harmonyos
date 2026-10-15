import os

from conan import ConanFile


class MscompressTestConan(ConanFile):
    """test_package for mscompress executable — round-trip compress/expand."""
    settings = "os", "arch", "compiler", "build_type"
    generators = "VirtualRunEnv"
    test_type = "explicit"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def test(self):
        # OHOS: /system/bin/sh (mksh) may not execute ELF binaries reliably.
        # Use bash to wrap binary execution (same convention as aa3d).
        bash = os.environ.get("CONFIG_SHELL", "/data/service/hnp/bin/bash")
        self.run(f"{bash} test.sh", env="conanrun")