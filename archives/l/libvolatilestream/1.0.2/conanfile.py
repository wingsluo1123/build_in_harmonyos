#!/usr/bin/env python3
"""Conan 2 recipe for libvolatilestream 1.0.2 (CMake-based C library).

libvolatilestream 实现 volatile stream：用 fopencookie(3) 把 stdio FILE*
绑定到一块动态分配的内存缓冲上（可写、可 seek、关闭时自动释放），
对外提供 volstream_open/volstream_trunc/volstream_getbuf 三个 API。

上游仅构建共享库（add_library(SHARED)，无 static 选项），无第三方依赖，
无上游测试目录。

OHOS 适配要点:
  - fopencookie/off64_t 依赖 _GNU_SOURCE，上游 CMakeLists.txt 已全局
    add_definitions(-D_GNU_SOURCE)，无需补丁。
  - 上游 project(VERSION) 仍为 1.0.1（tag 1.0.2 未同步该字段），包版本以
    tag 1.0.2 为准；共享库 SOVERSION=1。
  - HMDFS 不支持 symlink()（EPERM），VERSION/SOVERSION 的 .so.1 -> .so
    符号链接链无法创建；按 E330 家族既有做法输出无版本号共享库
    （CMAKE_PLATFORM_NO_VERSIONED_SONAME），并显式补上 SONAME 链接标志。
  - man 页目标依赖 pandoc，缺失时 man/Makefile 仅打印提示并正常退出；
    归档自带 volstream_open.3，不影响安装。
"""

import os

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.cmake import CMake, CMakeToolchain, cmake_layout
from conan.tools.files import (
    apply_conandata_patches,
    copy,
    export_conandata_patches,
    get,
)


class LibvolatilestreamConan(ConanFile):
    name = "libvolatilestream"
    version = "1.0.2"
    description = "FILE* stream as a temporary allocated memory buffer"
    license = "LGPL-2.1-or-later"
    homepage = "https://github.com/rd235/libvolatilestream"
    url = "https://gitcode.com/OpenHarmonyPCDeveloper/build_in_harmonyos"

    package_type = "shared-library"
    settings = "os", "compiler", "build_type", "arch"

    def export_sources(self):
        export_conandata_patches(self)

    def layout(self):
        cmake_layout(self)

    def configure(self):
        # OHOS profile 定义了 os.version，但本配方不使用该设置；
        # 移除后默认 profile（无 os.version）下 package_id 校验也能通过。
        if hasattr(self.settings, "os") and hasattr(self.settings.os, "version"):
            self.settings.rm_safe("os.version")

    def validate(self):
        # R32: settings.os 仅允许 Linux / OHOS
        if str(self.settings.os) not in ("Linux", "OHOS"):
            raise ConanInvalidConfiguration(
                "libvolatilestream 1.0.2 only supports Linux and OHOS, "
                f"got os={self.settings.os}"
            )

    def generate(self):
        tc = CMakeToolchain(self)
        # HMDFS 拒绝 symlink()（EPERM），VERSION/SOVERSION 的
        # libvolatilestream.so.1 -> .so 链接链无法创建；只输出无版本号的
        # 共享库（plasma-activities / kwidgetsaddons E330 先例）。
        tc.variables["CMAKE_PLATFORM_NO_VERSIONED_SONAME"] = "ON"
        tc.cache_variables["CMAKE_PLATFORM_NO_VERSIONED_SONAME"] = "ON"
        # CMake 没有 HarmonyOS 平台模块，CMAKE_SHARED_LIBRARY_SONAME_C_FLAG
        # 为空导致 lld 不写 DT_SONAME，消费者会把构建机绝对路径记进
        # DT_NEEDED；显式提供该标志（variable + cache 双通道）。
        tc.variables["CMAKE_SHARED_LIBRARY_SONAME_C_FLAG"] = "-Wl,-soname,"
        tc.cache_variables["CMAKE_SHARED_LIBRARY_SONAME_C_FLAG"] = "-Wl,-soname,"
        tc.generate()

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def build(self):
        apply_conandata_patches(self)
        cmake = CMake(self)
        cmake.configure()
        cmake.build()

    def package(self):
        cmake = CMake(self)
        cmake.install()
        copy(
            self,
            "COPYING",
            src=self.source_folder,
            dst=os.path.join(self.package_folder, "licenses"),
        )

    def package_info(self):
        self.cpp_info.libs = ["volatilestream"]
        self.cpp_info.set_property("cmake_file_name", "libvolatilestream")
        self.cpp_info.set_property(
            "cmake_target_name", "libvolatilestream::libvolatilestream"
        )
        # 上游 volatilestream.pc 的 Name 为 volatilestream
        self.cpp_info.set_property("pkg_config_name", "volatilestream")
