#!/usr/bin/env python3
"""Conan 配方 — tzc 2.6.16.1（Trivial Zephyr Client）HarmonyOS PC / aarch64。

tzc 是 Debian native 包：上游为 CMU cclub 的 zephyr-mode 附属工具，自 2004 年
后无新版本。它是单个 C 程序（tzc.c + lread.c），链接 Project Athena 的
Zephyr 通知服务客户端库 libzephyr，并使用 com_err（来自 e2fsprogs）报错。

适配要点（无补丁，纯构建参数覆盖）
--------------------------------
- 上游 Makefile 内 `CC = gcc` 是 Makefile 赋值，**环境变量无法覆盖**，但
  `make CC=clang` 属命令行变量，优先级高于 Makefile 赋值 —— 因此无需修改
  上游源码即可切换工具链（R6：不改源码）。
- 头/库路径经 `ZEPHYR_INCLUDES` / `ZEPHYR_LIBS` 命令行变量注入。
- com_err 由 e2fsprogs 以静态库 `libcom_err.a` 形式静态链入，故最终二进制
  DT_NEEDED 只有 `libzephyr.so.4` 与 `libc.so`。
- 上游无任何自动化测试套件（Makefile 目标仅 tzc / *.o / clean）。
- 运行需要 Zephyr HostManager 网络服务；无服务时 libzephyr 的
  `ZInitialize()` 失败并优雅退出（退出码 1），消费者用例据此验证闭包真实加载。
"""
import os

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.files import apply_conandata_patches, copy, export_conandata_patches, get
from conan.tools.layout import basic_layout


class TzcConan(ConanFile):
    name = "tzc"
    version = "2.6.16.1"
    description = "Trivial Zephyr Client (Debian native, CMU cclub upstream)"
    license = "GPL-2.0-only"
    homepage = "https://packages.debian.org/source/trixie/tzc"
    url = "https://gitcode.com/OpenHarmonyPCDeveloper/build_in_harmonyos"

    package_type = "application"

    settings = "os", "arch", "compiler", "build_type"

    def export_sources(self):
        # 与 conandata.yml 的 patches 段保持一致（当前为空，属显式声明）
        export_conandata_patches(self)

    def requirements(self):
        self.requires("zephyr/3.1.2", transitive_headers=True, transitive_libs=True)
        self.requires("e2fsprogs/1.47.4", transitive_headers=True, transitive_libs=True)

    def validate(self):
        if str(self.settings.os) not in ("Linux", "OHOS"):
            raise ConanInvalidConfiguration(
                f"tzc supports Linux and OHOS, not {self.settings.os}"
            )

    def layout(self):
        basic_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"][self.version], strip_root=True)

    def build(self):
        apply_conandata_patches(self)

        # R33 / E392：编译器只能从 Conan conf 取，且
        # tools.build:compiler_executables 是 dict（{'c':…,'cpp':…}）
        comp = self.conf.get("tools.build:compiler_executables", default={},
                             check_type=dict)
        cc = comp.get("c", "clang")

        zephyr = self.dependencies["zephyr"].cpp_info
        e2fs = self.dependencies["e2fsprogs"].cpp_info

        inc_flags = " ".join("-I%s" % d for d in zephyr.includedirs + e2fs.includedirs)
        lib_flags = " ".join("-L%s" % d for d in zephyr.libdirs + e2fs.libdirs)

        # 全程命令行变量覆盖，不改上游 Makefile（E392：raw makefile 须显式 cwd）
        self.run(
            f"make -j1 CC={cc} "
            f"ZEPHYR_LIBS=\"-lzephyr -lcom_err {lib_flags}\" "
            f"ZEPHYR_INCLUDES=\"{inc_flags}\"",
            cwd=self.source_folder,
        )

    def package(self):
        src = self.source_folder
        copy(self, "tzc", src, os.path.join(self.package_folder, "bin"))
        # 上游 man page 与许可证位于 debian/ 目录（Debian native 包布局）
        copy(self, "tzc.1", os.path.join(src, "debian", "man"),
             os.path.join(self.package_folder, "share", "man", "man1"))
        copy(self, "copyright", os.path.join(src, "debian"),
             os.path.join(self.package_folder, "licenses"))

    def package_info(self):
        self.cpp_info.libs = []
        self.cpp_info.bindirs = ["bin"]
        self.cpp_info.includedirs = []
        self.cpp_info.libdirs = []
