#!/usr/bin/env python3
"""Conan test_package for garcon 4.20.0 — consumer smoke test.

上游 garcon 4.20.0 的 tests/ 三程序（test-menu-parser / test-menu-spec /
test-display-menu-gtk3）均为 noinst_PROGRAMS，未接入 make check（N=0
注册用例，逐文件审计见 MANIFEST.yml）。本消费者测试承担全部验证：
编译+链接（含 glib/gtk 闭包）+ 运行断言（沙箱可运行时）。

裸 clang 编译范式（libxfce4util 4.20.1 / glib test_package 同款）：
- 不用 CMakeDeps（避免组件名/别名陷阱），直接消费 garcon 制品 + 全部
  传递依赖的 include/lib 目录；
- 链接行显式 -lintl（glib 包内 proxy-libintl，SONAME libintl.so.8）：
  OHOS lld --no-allow-shlib-undefined 下 g_libintl_* 符号的提供者；
- R33: 编译器取自 conan conf，不裸用 ${CC}。
"""
import os

from conan import ConanFile
from conan.tools.build import can_run, cross_building


class GarconTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"
    generators = "VirtualRunEnv"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def build(self):
        # 头闭包：被测包 + 全部依赖（glib 的 include 含 proxy libintl.h）；
        # 跳过未下载二进制的图节点（Skipped binaries 的 package_folder=None）
        incs = []
        libdirs = []
        for _ref, dep in self.dependencies.items():
            if dep.package_folder is None:
                continue
            dirs = list(dep.cpp_info.includedirs)
            for _comp_name, comp in dep.cpp_info.components.items():
                dirs += list(comp.includedirs)
            for p in dirs:
                if not p:
                    continue
                if not os.path.isabs(p):
                    p = os.path.join(dep.package_folder, p)
                if p not in incs:
                    incs.append(p)
            for p in dep.cpp_info.libdirs:
                if not p:
                    continue
                if not os.path.isabs(p):
                    p = os.path.join(dep.package_folder, p)
                if p not in libdirs:
                    libdirs.append(p)
            # glib/gio/gtk 的版本化 include 子目录（gio/gio.h、glibconfig.h、
            # pango/cairo/gdk-pixbuf 头）——.pc 携带但 cpp_info 根目录不含
            for sub in ("include/glib-2.0", "lib/glib-2.0/include",
                        "include/gtk-3.0", "include/pango-1.0",
                        "include/cairo", "include/gdk-pixbuf-2.0",
                        "include/atk-1.0", "include/harfbuzz",
                        "include/freetype2"):
                r = os.path.join(dep.package_folder, sub)
                if os.path.isdir(r) and r not in incs:
                    incs.append(r)
        # garcon 头装在 include/garcon-1/ 下（#include <garcon/garcon.h>）
        gp = self.dependencies["garcon"].package_folder
        r = os.path.join(gp, "include", "garcon-1")
        if os.path.isdir(r) and r not in incs:
            incs.append(r)
        inc = " ".join("-I" + d for d in incs)
        lib = " ".join("-L" + d for d in libdirs)
        self._libdirs = list(libdirs)

        # R33: compiler from Conan conf, not bare ${CC}
        ce = self.conf.get("tools.build:compiler_executables", default={},
                           check_type=dict) or {}
        cc = ce.get("c") or "clang"

        # -lintl: glib proxy-libintl 提供 g_libintl_*（-Wl,--no-allow-shlib-undefined
        # 链接期必须显式见到）；-lm/pthread/dl: glib 组件声明的 system_libs
        self.run(
            f"{cc} test.c -o garcon-smoke {inc} {lib} "
            f"-lgarcon-1 -lgio-2.0 -lgobject-2.0 -lglib-2.0 "
            f"-lintl -lm -lpthread -ldl"
        )

    def test(self):
        # 交叉构建/沙箱不能跑目标 ELF 时退化为编译+链接验证（glib/expat 同款）
        if cross_building(self) or not can_run(self):
            self.output.info("cross-building / cannot run：只验编译+链接")
            return
        # OHOS 加载器忽略 DT_RUNPATH：显式注入依赖库目录 + 系统 /system/lib64
        # （C++ 运行时 libc++_shared.so 仅系统提供，gtk→harfbuzz 链 NEED 它，
        # kakoune-lsp/wlopm test.sh 先例）。env=None 不再叠加 env 文件，
        # 直接用下面的 LD_LIBRARY_PATH。
        ld = ":".join(["/system/lib64"] + list(self._libdirs))
        prev = os.environ.get("LD_LIBRARY_PATH", "")
        os.environ["LD_LIBRARY_PATH"] = ld + (":" + prev if prev else "")
        self.run("./garcon-smoke", env=None)
