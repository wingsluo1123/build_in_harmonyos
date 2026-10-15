#!/usr/bin/env python3
"""Conan test_package — megadepth 1.2.0 (consumer-perspective verification).

驱动 test_megadepth.sh，对 *已安装* 的二进制（取自被测包 bindirs）执行真实
功能断言：解析 BAM、跑 --annotation/--auc/--fits 计算并与上游期望输出逐行
比对。断言依赖打包产物本身，非空壳测试（R34；CI L1e 破坏性反向验证兜底：
移走 bindirs 后 megadepth 不可执行 → 测试必然失败）。
"""
import os

from conan import ConanFile


class MegadepthTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"
    test_type = "explicit"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def test(self):
        # OHOS: /system/bin/sh (mksh) 无法执行部分 ELF 包装，用 hnp bash 驱动
        bash = os.environ.get("CONFIG_SHELL", "/data/service/hnp/bin/bash")
        bindir = self.dependencies[self.tested_reference_str].cpp_info.bindirs[0]
        megadepth = os.path.join(bindir, "megadepth")
        script = os.path.join(os.path.dirname(__file__), "test_megadepth.sh")
        # R10: 测试产物写入 TMPDIR 语义的临时目录，不落在归档目录内
        #（OHOS 的 /tmp 只读，故先取 TMPDIR，再退化为 $HOME/tmp）
        tmp_root = os.environ.get("TMPDIR") or os.path.join(
            os.path.expanduser("~"), "tmp")
        os.makedirs(tmp_root, exist_ok=True)
        workdir = os.path.join(tmp_root, "megadepth-test-{}".format(os.getpid()))
        # conanrun env: 被测包 bindirs 进入 PATH，共享库目录进入 LD_LIBRARY_PATH
        self.run('"{}" "{}" "{}" "{}"'.format(
            bash, script, megadepth, workdir), env="conanrun")
