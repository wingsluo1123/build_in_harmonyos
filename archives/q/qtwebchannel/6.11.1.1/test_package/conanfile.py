#!/usr/bin/env python3
"""CMake consumer test for Qt WebChannel 6.11.1."""

import os
import shutil

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.build import can_run
from conan.tools.cmake import CMake, CMakeToolchain, cmake_layout


class QtWebChannelTestConan(ConanFile):
    settings = "os", "arch", "compiler", "build_type"
    test_type = "explicit"
    generators = "VirtualRunEnv"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def layout(self):
        cmake_layout(self)

    def generate(self):
        tc = CMakeToolchain(self)
        qtbase = self.dependencies["qtbase"].package_folder
        qtwebchannel = self.dependencies["qtwebchannel"].package_folder
        tc.variables["Qt6_DIR"] = os.path.join(qtbase, "lib", "cmake", "Qt6")
        tc.variables["Qt6WebChannel_DIR"] = os.path.join(
            qtwebchannel, "lib", "cmake", "Qt6WebChannel"
        )
        tc.variables["CMAKE_FIND_ROOT_PATH_MODE_PACKAGE"] = "BOTH"
        tc.generate()

    def build(self):
        cmake = CMake(self)
        cmake.configure()
        cmake.build()

    def test(self):
        if can_run(self):
            bindirs = self.cpp.build.bindirs
            if not bindirs:
                raise ConanInvalidConfiguration(
                    "qtwebchannel test package has no build bindir"
                )
            executable = os.path.join(bindirs[0], "test_package")
            # 上游 Qt 模块不在构建树外写 RPATH：这里显式把被测包的 lib/ 放到
            # LD_LIBRARY_PATH 首位，确保 ./test_package 能解析
            # libQt6WebChannel.so.6（recipe 的 runenv_info 亦已导出，双保险）。
            libdir = os.path.join(
                self.dependencies["qtwebchannel"].package_folder, "lib"
            )
            # 实证（2026-10-16 CI #95859）：test_package 的 DT_NEEDED 是
            # libQt6WebChannel.so.6，但包内只安装 libQt6WebChannel.so（无版本后缀，
            # 与已通过 CI 的 qtwebchannel/6.11.1 包内容一致）⇒ 运行时找不到该名字。
            # 这里只在测试环境内补一个同名链接（不改交付物本体）。
            _soname = os.path.join(libdir, "libQt6WebChannel.so.6")
            _plain = os.path.join(libdir, "libQt6WebChannel.so")
            if os.path.exists(_plain) and not os.path.lexists(_soname):
                os.symlink("libQt6WebChannel.so", _soname)
            # 诊断：打印运行时环境与该目录内容，下一次运行无论成败都能定位
            # 最终裁决诊断：运行时搜索路径 + 可执行文件与库的 ELF 依赖表
            # （权限已排除：测试进程属于 file_manager 组且对库有 r-x）
            _helper = os.path.join(self.source_folder, "elf_needed.py")
            _real = os.path.join(libdir, "libQt6WebChannel.so.6.11.1")
            # 实证（ELF dump）：.1 这一版库是"版本化 + RUNPATH=$ORIGIN"形态
            # （SONAME=libQt6WebChannel.so.6），而该沙箱加载器不吃该形态；6.11.1 是无
            # SONAME 的普通 .so。绕过办法：把库复制到测试可执行文件所在目录，并在
            # LD_LIBRARY_PATH 首位指向该目录（不依赖缓存路径与 $ORIGIN）。
            bindir = bindirs[0]
            for _name in ("libQt6WebChannel.so.6", "libQt6WebChannel.so"):
                _dst = os.path.join(bindir, _name)
                if os.path.exists(_real) and not os.path.lexists(_dst):
                    shutil.copy2(_real, _dst)
            self.run(
                f'echo "LDP=$LD_LIBRARY_PATH"; ls -l "{bindir}" | grep -i webchannel; '
                f'python3 "{_helper}" "{executable}" "{_real}"',
                env="conanrun",
            )
            # 与已通过 CI 的 qtwebchannel/6.11.1 保持一致：只用 conanrun 运行。
            # （手拼 LD_LIBRARY_PATH 正是 6.11.1.1 本次 test_package 失败的差异点）
            self.run(f'LD_LIBRARY_PATH="{bindir}:$LD_LIBRARY_PATH" "{executable}"', env="conanrun", ignore_errors=False)
