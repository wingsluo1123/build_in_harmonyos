# test_package/conanfile.py — irony-mode 1.6.1
# Conan L1 官方测试（CI 经 conan create 自动执行）
# 验证安装的 irony-server 可执行、能加载系统 SDK libclang（--version 输出
# 第二行是运行期 clang_getClangVersion() 的结果，链接失败会直接暴露）。
import os
import shutil

from conan import ConanFile


class IronyModeTestConan(ConanFile):
    settings = "os", "arch", "compiler", "build_type"
    generators = "VirtualRunEnv"
    test_type = "explicit"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def test(self):
        # OHOS: /system/bin/sh (mksh) cannot execute ELF binaries.
        # Use bash to wrap binary execution.
        bash = os.environ.get("CONFIG_SHELL") or shutil.which("bash") or "bash"
        self.run(f"{bash} test.sh", env="conanrun")
