#!/usr/bin/env python3
"""lddtreepax test_package — Conan L1 消费者测试 (R34 实质依赖被测包).

无编译脚本工具：test() 用 python 执行 test_lddtreepax.py，传入被测包与
pyelftools 两个 package_folder，由测试脚本以显式路径直接执行已安装
lddtreepax（shebang #!/usr/bin/env python3）解析真实 aarch64 ELF /bin/sh
并做实质断言。不依赖 conanrun PATH 注入（与 pyelftools test_package 先例
一致：显式路径，稳健）。
"""
import os
import sys

from conan import ConanFile
from conan.tools.build import can_run


class TestPackageConan(ConanFile):
    settings = "os", "arch", "compiler", "build_type"
    test_type = "explicit"

    def requirements(self):
        self.requires(self.tested_reference_str)
        # 显式引入 pyelftools 以取得其 package_folder（构造 PYTHONPATH）。
        # run=True：python-require 包不声明 run 会被 conan skip（见主配方
        # requirements() 注释），skip 后 package_folder=None 取不到路径。
        self.requires("pyelftools/0.33", run=True)

    def test(self):
        if can_run(self):
            ldd_pkg = self.dependencies["lddtreepax"].package_folder
            pyelf_pkg = self.dependencies["pyelftools"].package_folder
            test_script = os.path.join(os.path.dirname(__file__),
                                       "test_lddtreepax.py")
            # 沙箱 PATH 无 python3——绝对路径（同 pyelftools test_package 先例）
            py = "/data/service/hnp/bin/python3" \
                if os.path.isfile("/data/service/hnp/bin/python3") \
                else sys.executable
            self.run(f'{py} "{test_script}" "{ldd_pkg}" "{pyelf_pkg}"')
