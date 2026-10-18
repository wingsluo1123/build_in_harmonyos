#!/usr/bin/env python3
"""Conan test_package for adriconf — GUI 实机验证 (R34).

adriconf 是 GTK4 GUI 应用（Mesa drirc 配置器），test_package 验证安装产物：
1. bin/adriconf 存在且为 ELF 可执行文件（magic 校验）
2. adriconf --help 帮助输出可读（无显示环境允许非零退出，d11amp 先例）
"""
import os
from glob import glob

from conan import ConanFile


class AdriconfTestConan(ConanFile):
    settings = "os", "arch", "compiler", "build_type"
    generators = "VirtualRunEnv"
    test_type = "explicit"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def test(self):
        if self.settings.os == "OHOS":
            # OHOS 动态库（含 libc++_shared.so）在 SDK 的 llvm/lib/
            # aarch64-linux-ohos 目录，加载器默认不搜该路径（d11amp/gtkmm
            # 先例）：注入 LD_LIBRARY_PATH 以解析 C++ runtime 依赖。
            sdk_lib = os.environ.get("OHOS_SDK_LIB")
            if not sdk_lib:
                candidates = glob(
                    "/data/service/hnp/ohos-sdk.org/*/"
                    "ohos/native/llvm/lib/aarch64-linux-ohos"
                )
                if candidates:
                    sdk_lib = candidates[0]
            if sdk_lib:
                os.environ["LD_LIBRARY_PATH"] = (
                    sdk_lib
                    + os.pathsep
                    + os.environ.get("LD_LIBRARY_PATH", "")
                )
        # OHOS /system/bin/sh (mksh) 无法执行 ELF；用 bash 驱动测试脚本
        bash = os.environ.get("CONFIG_SHELL", "/data/service/hnp/bin/bash")
        self.run(f"{bash} test_adriconf.sh", env="conanrun")
