#!/usr/bin/env python3
"""Conan test_package — karabo-bridge 0.6.2 消费者验证.

test_type="explicit": 由 `conan test test_package karabo-bridge/0.6.2` 驱动.
test() 内调用 test.sh (R34: test() 必须调用 self.run, 实质性依赖被测包).

PYTHONPATH 由 conanfile.py 的 package_info() 通过 runenv_info.append_path
注入; test.sh 内通过 VirtualRunEnv 环境获得.
"""
from conan import ConanFile
from conan.tools.build import can_run


class KaraboBridgeTestConan(ConanFile):
    settings = "os", "arch"
    generators = "VirtualRunEnv"
    test_type = "explicit"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def test(self):
        if can_run(self):
            self.run("bash test.sh", env="conanrun", cwd=self.source_folder)
