import os

from conan import ConanFile


class BisonTestConan(ConanFile):
    """test_package for GNU bison 2.7 — verifies the packaged bison binary
    runs and produces a parser from a grammar file."""
    settings = "os", "arch", "compiler", "build_type"
    generators = "VirtualRunEnv"
    test_type = "explicit"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def test(self):
        # Use the absolute path of the packaged bison binary so the L1e
        # negative test (R34) genuinely detects dependency on this package
        # rather than any system bison.
        bison_bin = os.path.join(self.dependencies["bison"].package_folder,
                                 "bin", "bison")
        bash = os.environ.get("CONFIG_SHELL", "/data/service/hnp/bin/bash")
        self.run(f'export BISON_BIN="{bison_bin}" && {bash} test.sh',
                 env="conanrun")
