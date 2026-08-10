#!/usr/bin/env python3
"""Consumer test for adplay (AdPlay/UNIX CLI player) on HarmonyOS PC."""

import os

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.build import can_run


class AdplayTestConan(ConanFile):
    settings = "os", "arch", "compiler", "build_type"
    generators = "VirtualRunEnv"
    test_type = "explicit"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def test(self):
        if not can_run(self):
            return
        bindirs = self.dependencies["adplay"].package_folder
        # adplay 是 CLI 播放器，验证可执行文件存在且能输出帮助信息。
        bash = os.environ.get("CONFIG_SHELL", "/data/service/hnp/bin/bash")
        test_script = os.path.join(self.source_folder, "test.sh")
        self.run(f'"{bash}" "{test_script}" "{bindirs}"', env="conanrun")
