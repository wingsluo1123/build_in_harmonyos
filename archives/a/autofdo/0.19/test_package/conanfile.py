#!/usr/bin/env python3
"""test_package — autofdo 0.19 消费者测试。

真实调用被测包提供的 7 个 CLI 工具（create_gcov / dump_gcov / sample_merger /
profile_merger / profile_diff / profile_update / create_llvm_prof），逐个运行
`--help`（断言 exit=1 + 输出含该工具 flag）与 `--version`（断言 exit=0 +
输出含工具名）；见 test_autofdo.sh。
"""
import os

from conan import ConanFile
from conan.tools.build import can_run


class TestPackageConan(ConanFile):
    settings = "os", "arch", "compiler", "build_type"
    generators = "VirtualRunEnv"
    test_type = "explicit"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def test(self):
        if not can_run(self):
            return
        # OHOS /system/bin/sh (mksh) 执行 ELF 不可靠（见本仓 aa3d/aaphoto 消费者
        # 测试同类处理）；用 bash 运行脚本，脚本内部再 exec 被测二进制，
        # PATH 由 VirtualRunEnv("conanrun") 注入包 bin/。
        bash = os.environ.get("CONFIG_SHELL", "/data/service/hnp/bin/bash")
        script = os.path.join(self.recipe_folder, "test_autofdo.sh")
        self.run(f'{bash} "{script}"', env="conanrun")
