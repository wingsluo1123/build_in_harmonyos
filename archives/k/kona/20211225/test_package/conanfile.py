#!/usr/bin/env python3
"""test_package for kona interpreter — runs test.sh which exercises the k binary."""
import os

from conan import ConanFile


class KonaTestConan(ConanFile):
    settings = "os", "arch", "compiler", "build_type"
    generators = "VirtualRunEnv"
    test_type = "explicit"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def test(self):
        bin_path = os.path.join(self.dependencies["kona"].package_folder, "bin", "k")
        bash = os.environ.get("CONFIG_SHELL", "/data/service/hnp/bin/bash")
        self.run(f'{bash} test.sh "{bin_path}"', env="conanrun")
