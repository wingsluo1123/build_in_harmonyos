#!/usr/bin/env python3
"""Conan recipe — ubridge 1.1.1 (plain Makefile, CLI application).

ubridge 是 GNS3 的桥接守护进程：把网络接口（真实口 / TAP / UDP 隧道 /
veth）互相桥接，并通过 TCP 控制端口接受 brctl、link 等模块的命令。
上游用裸 Makefile 构建，唯一的外部依赖是 libpcap，产物是单个可执行文件
ubridge，没有 configure、没有 make check、测试是 Python 黑盒套件。
"""

import os
import shutil

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.files import apply_conandata_patches, copy, export_conandata_patches, get
from conan.tools.layout import basic_layout


class UbridgeConan(ConanFile):
    name = "ubridge"
    version = "1.1.1"
    description = "GNS3 ubridge — bridge network interfaces to UDP tunnels (CLI daemon)"
    license = "GPL-3.0-or-later"
    homepage = "https://github.com/GNS3/ubridge"
    url = "https://gitcode.com/OpenHarmonyPCDeveloper/build_in_harmonyos"

    package_type = "application"

    settings = "os", "compiler", "build_type", "arch"

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        self.requires("libpcap/1.10.6")

    def layout(self):
        # 上游是裸 Makefile，源码即构建目录。
        basic_layout(self, src_folder=".")
        self.folders.build = "."

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def validate(self):
        if self.settings.os not in ("Linux", "OHOS"):
            raise ConanInvalidConfiguration(
                "ubridge %s only supports Linux and OHOS, got os=%s"
                % (self.version, self.settings.os)
            )

    def build(self):
        apply_conandata_patches(self)

        # R33: 编译器取自 Conan 配置，不用 shell 的 ${CC}/${CFLAGS}。
        compilers = self.conf.get("tools.build:compiler_executables", default={}, check_type=dict)
        cc = compilers.get("c", "clang")

        pcap = self.dependencies["libpcap"].cpp_info
        cppflags = " ".join("-I%s" % d for d in pcap.includedirs)
        ldflags = " ".join("-L%s" % d for d in pcap.libdirs)

        # 上游 Makefile 没有 .c.o 规则，走 make 内建规则（$(CC) $(CPPFLAGS)
        # $(CFLAGS) -c），因此用 CPPFLAGS 传 Conan 依赖的头文件目录，不会覆盖
        # Makefile 自己的 `CFLAGS += -Wall`；链接行是
        # `$(CC) $(CFLAGS) $(LDFLAGS) -o ubridge $(OBJ) $(LIBS)`，libpcap 已由
        # 上游放在 LIBS 里（-lpcap），这里只补 -L 指向 Conan 包。
        self.run('cd "%s" && make CC=%s "CPPFLAGS=%s" "LDFLAGS=%s" -j1'
                 % (self.source_folder, cc, cppflags, ldflags))

        self._run_upstream_tests()

    def _run_upstream_tests(self):
        """R51 第 2 步：实跑上游测试中无需 CAP_NET_ADMIN 的那一套。

        上游 1.1.1 的测试是 Python 黑盒套件 tests/brctl（7 套）与 tests/link
        （1 套），全部通过 TCP 控制端口驱动 ubridge。其中 7 套会真实创建内核
        bridge / veth 接口，需要 root + cap_net_admin + `ip` 工具——CI 沙箱和
        本机都不具备。tests/brctl/test_no_privs.py 正是为无特权场景写的：它启动
        刚编出来的二进制，断言 `hypervisor version` 有应答、所有变更命令被优雅
        拒绝且进程存活；若二进制恰好带 cap，它自跳过并返回 0。
        """
        if shutil.which("python3") is None:
            self.output.warning("python3 不可用，跳过上游 tests/brctl/test_no_privs.py")
            return
        self.run('cd "%s/tests/brctl" && python3 test_no_privs.py' % self.source_folder)

    def package(self):
        copy(self, "ubridge", src=self.source_folder,
             dst=os.path.join(self.package_folder, "bin"), keep_path=False)
        copy(self, "LICENSE", src=self.source_folder,
             dst=os.path.join(self.package_folder, "licenses"), keep_path=False)

    def package_info(self):
        self.cpp_info.bindirs = ["bin"]
