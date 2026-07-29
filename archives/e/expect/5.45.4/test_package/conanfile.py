import os

from conan import ConanFile


class ExpectTestConan(ConanFile):
    """test_package for expect — runs test_expect.sh which invokes the binary."""
    settings = "os", "arch", "compiler", "build_type"
    generators = "VirtualRunEnv"
    test_type = "explicit"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def test(self):
        # Get the bin path from the dependency's package
        bin_dir = self.dependencies["expect"].cpp_info.bindirs[0]
        expect_bin = os.path.join(bin_dir, "expect")

        # Verify expect binary exists
        self.run(f'test -x "{expect_bin}"', env="conanrun")

        # Run full smoke test suite via test_expect.sh
        # OHOS: /system/bin/sh (mksh) cannot execute ELF binaries.
        # Use bash to wrap binary execution.
        bash = os.environ.get("CONFIG_SHELL", "/data/service/hnp/bin/bash")
        self.run(f'EXPECT_BIN="{expect_bin}" {bash} test_expect.sh', env="conanrun")
