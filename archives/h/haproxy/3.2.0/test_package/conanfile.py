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
        test_cfg = os.path.join(self.source_folder, "test_config.cfg")
        bash = os.environ.get("CONFIG_SHELL", "/data/service/hnp/bin/bash")
        self.run(f'{bash} test_haproxy.sh "{haproxy_bin}" "{test_cfg}"', env="conanrun")
