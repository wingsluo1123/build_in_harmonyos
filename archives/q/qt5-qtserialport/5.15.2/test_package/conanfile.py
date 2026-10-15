#!/usr/bin/env python3
"""Consumer test for qt5-qtserialport on HarmonyOS PC.

模式与已通过 CI 的 qtserialport-opensource-src/5.15.15、
qt5-qtcharts/5.15.2.1 test_package 一致：
- CMakeDeps 生成 per-component 配置（直接依赖场景），
  避开 qt5-qtbase 包内 lib/cmake 残留的构建机路径；
- qt5-qtbase 声明为直接依赖（传递依赖场景下聚合 config 会丢组件信息）；
- OHOS 下强制 CMAKE_SYSTEM_NAME=Linux 双覆盖（NAME+PROCESSOR）：
  OHOS 适配版 conan 默认生成 HarmonyOS/unknown，导致 CMake 的 OHOS 分支
  探测与 find_library 命中错误——覆盖为 Linux/aarch64 走 POSIX 路径
  （adios2/any-lite 先例）；
- 运行时手动设置 LD_LIBRARY_PATH 指向两个包的 lib 目录。
"""

import os

from conan import ConanFile
from conan.tools.cmake import CMake, CMakeToolchain, cmake_layout


class Qt5QtserialportTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"
    generators = "CMakeDeps"

    def requirements(self):
        self.requires(self.tested_reference_str)
        # 直接依赖 qt5-qtbase：CMakeDeps 生成完整 per-component 配置
        # (Qt5CoreConfig.cmake)，Qt5::Core 携带正确 include 与库
        self.requires("qt5-qtbase/5.15.2.2")

    def layout(self):
        cmake_layout(self)

    def generate(self):
        tc = CMakeToolchain(self)
        # CMAKE_SYSTEM_NAME=Linux 强制双覆盖（NAME + PROCESSOR）
        if self.settings.os in ("Linux", "OHOS"):
            tc.cache_variables["CMAKE_SYSTEM_NAME"] = "Linux"
            tc.cache_variables["CMAKE_SYSTEM_PROCESSOR"] = (
                "aarch64" if str(self.settings.arch) == "armv8" else str(self.settings.arch)
            )
        tc.generate()

    def build(self):
        cmake = CMake(self)
        variables = {}
        if str(self.settings.os) == "OHOS":
            compilers = self.conf.get(
                "tools.build:compiler_executables", default={}, check_type=dict
            ) or {}
            compiler = compilers.get("cpp") or compilers.get("cxx")
            if compiler:
                compiler_dir = os.path.dirname(os.path.realpath(compiler))
                variables["OHOS_CXX_RUNTIME_DIR"] = os.path.join(
                    compiler_dir, "..", "lib", "aarch64-linux-ohos"
                )
        cmake.configure(variables=variables)
        cmake.build()

    def test(self):
        # 直接运行测试二进制，LD_LIBRARY_PATH 指向包 lib 目录
        # (OHOS conanrun 环境不设置它们)
        serialport = self.dependencies["qt5-qtserialport"]
        qtbase = self.dependencies["qt5-qtbase"]
        sp_libdir = os.path.join(
            serialport.package_folder, serialport.cpp_info.libdirs[0]
        )
        qtbase_libdir = os.path.join(qtbase.package_folder, "lib")
        library_paths = [sp_libdir, qtbase_libdir, os.environ.get("LD_LIBRARY_PATH")]
        os.environ["LD_LIBRARY_PATH"] = ":".join(
            path for path in library_paths if path
        )
        test_bin = os.path.join(
            self.cpp.build.bindirs[0] if self.cpp.build.bindirs else ".",
            "test_qtserialport",
        )
        self.run(test_bin, ignore_errors=False)
