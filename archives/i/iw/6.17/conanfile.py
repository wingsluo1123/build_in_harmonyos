#!/usr/bin/env python3
"""Conan recipe for iw 6.17 — nl80211 based CLI configuration utility for wireless devices.

iw 是**纯 Makefile** 的 C 命令行工具（无 configure / 非 autotools），经
generic netlink 与内核 cfg80211/nl80211 通信，因此链接 libnl-3 + libnl-genl-3。

OHOS 适配三条机制（均在真机实测，见 manifest.yaml / notes.md）：
 1. **编译期**：musl 派生 sysroot 的 <linux/socket.h> 无条件重定义
    struct sockaddr_storage（<sys/socket.h> 已提供）。libnl 的
    <netlink/netlink.h> 先引 <sys/socket.h> 再引 <linux/netlink.h> ->
    <linux/socket.h>，故**每个** TU 都编译失败。修法 = 仓内 E119/E1604 惯用法
    （补丁 0001 Makefile + 0002 iw-libc-compat.h），与 batctl 2025.2 同形。
 2. **运行期**：app 沙箱在**创建** socket(AF_NETLINK, SOCK_RAW,
    NETLINK_GENERIC=16) 时即返回 EACCES(13)，而 NETLINK_ROUTE(0) 可创建可 bind
    ⇒ nl80211 命令面不可达；但 CLI 契约面（--version / usage / 命令表）完全可用。
 3. **测试口径**：上游注册自动化测试用例数 = 0（R51 六探针全 0 命中）；Makefile
    里唯一的 `check:` 目标是 sparse/cgcc **静态分析 lint**，不是测试套件，故
    不得作为"已执行的上游套件"申报，真实断言全部由 test_package 承担。
"""
import os

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.files import copy, get, apply_conandata_patches, export_conandata_patches
from conan.tools.gnu import PkgConfigDeps
from conan.tools.layout import basic_layout


class IwConan(ConanFile):
    name = "iw"
    version = "6.17"
    description = "nl80211 based CLI configuration utility for wireless devices"
    license = "ISC"
    homepage = "https://wireless.wiki.kernel.org/en/users/documentation/iw"
    url = "https://gitcode.com/OpenHarmonyPCDeveloper/build_in_harmonyos"

    # iw 产出可执行文件 iw（非库）——R38 要求软件级 commands.json，已提供。
    package_type = "application"
    settings = "os", "compiler", "build_type", "arch"

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        # nl80211 经 libnl 的 generic-netlink API 到达。制品仓 libnl 仅发布
        # 静态库（.a），故 iw 二进制把 libnl 静态链入，运行期只依赖 libc.so。
        self.requires("libnl/3.11.0")

    def validate(self):
        # R32：settings.os 判定必须用 in ("Linux", "OHOS")，不得 == "Linux"。
        if str(self.settings.os) not in ("Linux", "OHOS"):
            raise ConanInvalidConfiguration(
                f"iw only supports Linux/OHOS, got {self.settings.os}")

    def layout(self):
        basic_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def generate(self):
        # iw 的 Makefile 用 pkg-config 探测 libnl（--atleast-version=3.2
        # libnl-3.0）；PkgConfigDeps 把 libnl-3.0.pc / libnl-genl-3.0.pc 写进
        # generators_folder，build() 里把 PKG_CONFIG_PATH 指过去。
        deps = PkgConfigDeps(self)
        deps.generate()

    def build(self):
        apply_conandata_patches(self)
        # R33：编译器取自 Conan conf，不裸用 shell 环境变量。
        compilers = self.conf.get("tools.build:compiler_executables",
                                  default={}, check_type=dict) or {}
        cc = compilers.get("c", "clang")
        # 纯 Makefile：无 configure。PKG_CONFIG_PATH 必须能看到 conan 生成的
        # .pc，否则 Makefile 直接 $(error Cannot find development files for any
        # supported version of libnl)。-j1 避开 make jobserver（OHOS 沙箱无 mkfifo）。
        cmd = (f'CC="{cc}" PKG_CONFIG_PATH="{self.generators_folder}:$PKG_CONFIG_PATH" '
               f'make -j1')
        self.run(cmd, cwd=self.source_folder, env="conanbuild")

    def package(self):
        # OHOS 无 coreutils `install`（aa3d/ethtool 同类教训），且上游 install
        # 目标还要 gzip 手册页 ⇒ 这里手工落位，不依赖 make install。
        copy(self, "iw", src=self.source_folder,
             dst=os.path.join(self.package_folder, "bin"), keep_path=False)
        copy(self, "iw.8", src=self.source_folder,
             dst=os.path.join(self.package_folder, "share", "man", "man8"),
             keep_path=False)
        copy(self, "COPYING", src=self.source_folder,
             dst=os.path.join(self.package_folder, "licenses"), keep_path=False)

    def package_info(self):
        # 命令行工具，非库：无 libs 可链接。
        self.cpp_info.bindirs = ["bin"]
        self.cpp_info.libs = []
