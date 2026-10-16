#!/usr/bin/env python3
"""Conan test_package for libhinoko 1.0.3.

实质消费被测库（R34/L0c/L0d）：
1. 交叉编译场景：编译 test_hinoko.c（链接 libhinoko 及传递依赖
   libhinawa/libgobject/libglib、调用 hinoko API），验证 include/lib 交付
   可被下游真实链接。
2. 本机运行场景：直接运行包内编译出的测试二进制。
"""
import os

from conan import ConanFile
from conan.tools.build import cross_building


class LibHinokoTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"
    generators = "PkgConfigDeps", "VirtualRunEnv", "VirtualBuildEnv"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def _dep_libdirs(self):
        """收集所有依赖（含 transitive 的 libhinawa/glib）的绝对 libdir
        （build()/test() 共用）。"""
        libdirs = []
        for _dep in self.dependencies.values():
            libdirs += _dep.cpp_info.libdirs
        return [d for d in dict.fromkeys(libdirs) if d and os.path.isabs(d)]

    def build(self):
        libdirs = self._dep_libdirs()
        incdirs = []
        for _dep in self.dependencies.values():
            incdirs += _dep.cpp_info.includedirs
            # glib 头文件布局：include/glib-2.0 + lib/glib-2.0/include
            # （glibconfig.h 在后者）
            if str(_dep.ref).startswith("glib/"):
                root = _dep.package_folder
                incdirs.append(os.path.join(root, "include", "glib-2.0"))
                incdirs.append(os.path.join(root, "lib", "glib-2.0", "include"))
        cc = os.environ.get("CC", "clang")
        inc = " ".join("-I" + d for d in incdirs if d)
        # libhinoko 是 GObject 库且依赖 libhinawa：其符号表引用
        # gobject/glib，公共头 hinoko.h include <hinawa.h> 并暴露
        # HinawaCycleTime——下游链接时需同时链 hinawa + gobject/glib
        # （与 pkg-config Requires 语义一致）。
        # ohpcd 制品仓的 glib2/2.88.0 只发布 static（shared: False），
        # 其 libgobject-2.0.a 引用 libffi（ffi_*）、libglib-2.0.a 引用
        # proxy-libintl（g_libintl_*）与 pcre2（pcre2_*_8）——手动链接
        # 必须显式带上这些静态依赖库（旧版 glib/2.84.0.2 是 shared，
        # 无需；glib2 迁移后必须），并用 --start-group 规避静态库
        # 循环引用/顺序敏感。
        link = " ".join(["-L" + d for d in libdirs]
                        + ["-Wl,--start-group",
                           "-lhinoko", "-lhinawa",
                           "-lgobject-2.0", "-lglib-2.0",
                           "-lffi", "-lintl", "-lpcre2-8", "-lz",
                           "-Wl,--end-group"]
                        + ["-Wl,-rpath," + d for d in libdirs])
        test_src = os.path.join(os.path.dirname(__file__), "test_hinoko.c")
        # R34: self.run 实质编译链接并消费 libhinoko 符号
        self.run(f"{cc} '{test_src}' -o test_hinoko_probe {inc} {link}")

    def test(self):
        if cross_building(self):
            self.output.info("cross-building: compile+link against libhinoko verified")
            return
        # 实际运行包内编译出的消费者二进制（LD_LIBRARY_PATH 指向依赖 libdir，
        # 含 libhinawa + glib；OHOS musl loader 不消费 DT_RUNPATH 之外的路径）
        env_ld = ":".join(self._dep_libdirs())
        self.run(f"LD_LIBRARY_PATH='{env_ld}' "
                 + os.path.join(".", "test_hinoko_probe"))
        self.output.info("[PASS] test_hinoko_probe ran (linked against libhinoko)")
