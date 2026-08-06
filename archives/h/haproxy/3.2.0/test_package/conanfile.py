#!/usr/bin/env python3
import os
from conan import ConanFile

class HaproxyTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"
    generators = "VirtualBuildEnv", "VirtualRunEnv"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def build(self):
        pass

    def test(self):
        haproxy_bin = os.path.join(self.dependencies["haproxy"].package_folder, "sbin", "haproxy")
        self.run(f'"{haproxy_bin}" -vv', env="conanrun")
        test_cfg = os.path.join(self.source_folder, "test_config.cfg")
        self.run(f'"{haproxy_bin}" -c -f "{test_cfg}"', env="conanrun")
