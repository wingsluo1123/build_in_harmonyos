#!/usr/bin/env python3
"""Conan test_package — libaccounts-qt 1.13.

Verifies that libaccounts-qt (Accounts::Manager) can be linked and used.
libaccounts-qt is a static library built via manual moc + clang++ (qmake's
QMAKE_MKSPECS is baked to a build dir inside the qt5-qtbase package, so the
module system is bypassed). This test compiles a small program directly.
"""
import os

from conan import ConanFile


class LibAccountsQtTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def _cc(self):
        compilers = self.conf.get(
            "tools.build:compiler_executables", default={}, check_type=dict
        ) or {}
        return compilers.get("cpp") or compilers.get("cxx") or "clang++"

    def _include_flags(self):
        flags = []
        for _name, dep in self.dependencies.items():
            base = os.path.join(dep.package_folder, "include")
            if os.path.isdir(base):
                flags.append(f"-I{base}")
                for entry in sorted(os.listdir(base)):
                    p = os.path.join(base, entry)
                    if os.path.isdir(p):
                        flags.append(f"-I{p}")
        return " ".join(flags)

    def _libdir_flags(self):
        flags = []
        for _name, dep in self.dependencies.items():
            libdir = os.path.join(dep.package_folder, "lib")
            if os.path.isdir(libdir):
                flags.append(f"-L{libdir}")
        return " ".join(flags)

    def build(self):
        cc = self._cc()
        inc = self._include_flags()
        libdirs = self._libdir_flags()
        # 静态库链接：按依赖顺序给出，--as-needed 裁剪未引用符号
        libs = (
            "-laccounts-qt5 -lQt5Core -laccounts-glib "
            "-lglib-2.0 -lgobject-2.0 -lgio-2.0 -lxml2 -lsqlite3 "
            "-lz -lpcre2-8 -lffi -lm -lpthread -ldl"
        )
        self.run(
            f'"{cc}" -std=c++17 {inc} "{self.source_folder}/test.cpp" '
            f'-o "{self.build_folder}/test_libaccounts_qt" '
            f"{libdirs} {libs} -Wl,--as-needed"
        )

    def test(self):
        self.run(f'"{os.path.join(self.build_folder, "test_libaccounts_qt")}"')
