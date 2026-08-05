import os

from conan import ConanFile


class AsciiquariumTestConan(ConanFile):
    """test_package for asciiquarium — verifies the Perl script is correctly packaged."""
    settings = "os", "arch", "compiler", "build_type"
    generators = "VirtualRunEnv"
    test_type = "explicit"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def test(self):
        # R34: genuinely exercises the tested package's binary.
        # Use bash to run the test script (OHOS /system/bin/sh may not handle all cases)
        bash = os.environ.get("CONFIG_SHELL", "/data/service/hnp/bin/bash")
        self.run(f"{bash} test.sh", env="conanrun")
