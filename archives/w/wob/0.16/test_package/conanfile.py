#!/usr/bin/env python3
"""wob test_package：OHOS aarch64 消费者验证 + 鸿蒙特有断言。

上游用例（meson test color）在 wob 配方 build() 内真实运行（见
MANIFEST.yml 声明）；本 test_package 承担消费者视角验证，核心是
test_wob_ohos.sh 中的 5 条 OHOS 专属断言（ABI/interpreter/seccomp
配置分支/真实执行签名与动态闭包）——非上游用例复用。
"""
import os

from conan import ConanFile


class TestPackageConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def test(self):
        pkg = self.dependencies["wob"].package_folder
        wob = os.path.join(pkg, "bin", "wob")
        found = os.path.isfile(wob)
        self.output.info(f"bin/wob found: {found} ({wob})")
        if not found:
            raise Exception("wob package missing bin/wob")
        # wayland 包 libdir 传给脚本：wob 动态链接 libwayland-client.so，
        # 运行期需 LD_LIBRARY_PATH（transitive_libs 已注入 conanrun，
        # 显式传参双保险）
        wl_libdir = ""
        wl = self.dependencies.get("wayland")
        if wl is not None and wl.package_folder is not None:
            wl_libdir = os.path.join(wl.package_folder, "lib")
        script = os.path.join(self.source_folder, "src", "test_wob_ohos.sh")
        self.run(f'bash "{script}" "{pkg}" "{wl_libdir}"', env="conanrun")
        self.output.info("wob test_package PASS")
