#!/usr/bin/env python3
"""Conan test_package — ebtables 2.0.11（L1：消费者用例 + 交付形态自检）

消费者程序是交付库的**真实使用者**：它 find_package(ebtables CONFIG REQUIRED)
并链接 ebtables::ebtables（lib/libebtc.so.0），调用交付头 <ebtables_u.h> /
<ethernetdb.h> 里的公共 API，判据全部是外部可核对真值（内核 ABI 的标准判决名与
桥接 hook 顺序、libc inet_pton 交叉验证的 IPv4/IPv6 解析、上游 extensions/*.c
注册出来的扩展集合、IANA ethertype 值）。
"""
import os

from conan import ConanFile
from conan.tools.cmake import CMake, cmake_layout


class EbtablesTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"
    generators = "CMakeDeps", "CMakeToolchain", "PkgConfigDeps"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def layout(self):
        cmake_layout(self)

    def build(self):
        cmake = CMake(self)
        cmake.configure()
        cmake.build()

    def test(self):
        pkg = self.dependencies["ebtables"]
        ethertypes = os.path.join(pkg.package_folder, "etc", "ethertypes")
        exe = os.path.join(self.build_folder, "test_ebtables")
        # OHOS：/system/bin/sh（mksh）不执行 ELF，需经真 bash 转交（仓库 libarchive/
        # iptables 同款写法）。
        default_shell = ("/data/service/hnp/bin/bash" if str(self.settings.os) == "OHOS"
                         else "/bin/sh")
        bash = os.environ.get("CONFIG_SHELL", default_shell)
        self.run('{} -c "{} {}"'.format(bash, exe, ethertypes), env="conanrun")

        layout = os.path.join(self.source_folder, "test_layout.py")
        self.run('python3 "{}" --package-folder "{}" --os "{}" --arch "{}" '
                 '--version "{}" --generators-dir "{}" --build-dir "{}"'.format(
                     layout, pkg.package_folder, self.settings.os, self.settings.arch,
                     pkg.ref.version, self.generators_folder, self.build_folder),
                 env="conanrun")
