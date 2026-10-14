#!/usr/bin/env python3
"""test_package/conanfile.py — jaraco.stream 消费者测试驱动。

沿用本仓库纯 Python 包的范式（anytree / kconfiglib）：test_type = "explicit"，
用 VirtualRunEnv 生成 conanrun 环境，再以子进程运行消费者断言脚本。

⚠ 这里刻意**不手工拼 PYTHONPATH** —— 走 conanrun，才能顺带验证本配方
package_info() 导出的 PYTHONPATH（含替代 more-itertools 补挂的那一段）确实生效。
"""
import os
import sys

from conan import ConanFile
from conan.errors import ConanException


class JaracoStreamTestConan(ConanFile):
    settings = "os", "arch", "compiler", "build_type"
    test_type = "explicit"
    generators = "VirtualRunEnv"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def test(self):
        pkg = self.dependencies[self.tested_reference_str].package_folder
        py_ver = f"python{sys.version_info.major}.{sys.version_info.minor}"
        site = os.path.join(pkg, "lib", py_ver, "site-packages")
        if not os.path.isdir(os.path.join(site, "jaraco", "stream")):
            raise ConanException(f"jaraco.stream 未安装到 {site}")

        script = os.path.join(self.recipe_folder, "test_jaraco_stream.py")
        if not os.path.isfile(script):
            raise ConanException(f"消费者测试脚本缺失：{script}")

        self.run(f'"{sys.executable}" "{script}" "{site}"', env="conanrun")
