#!/usr/bin/env python3
"""Conan test_package for pqiv — 实机运行安装后的可执行文件（R34）。

pqiv 是 GTK+3 命令行图像查看器：真正的功能（打开图像）需要显示后端，
在无显示器的 conan 测试环境无法可靠运行；因此消费者测试断言安装产物的
真实可执行性与命令行契约（版本号、帮助输出、错误选项退出码），由 test.sh
实际执行 bin/pqiv 完成。
"""
import os
from glob import glob

from conan import ConanFile


class PqivTestConan(ConanFile):
    settings = "os", "arch", "compiler", "build_type"
    generators = "VirtualRunEnv"
    test_type = "explicit"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def test(self):
        if self.settings.os == "OHOS":
            # 与 audiowmark/gtkmm/d11amp 先例同款：OHOS 动态库（含
            # libc++_shared.so 及部分系统运行库）在 SDK 的
            # llvm/lib/aarch64-linux-ohos 目录，加载器默认不搜该路径。
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
        self.run("{} test.sh".format(bash), env="conanrun")
