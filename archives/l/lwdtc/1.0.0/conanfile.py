#!/usr/bin/env python3
"""Conan recipe for lwdtc 1.0.0 — Lightweight Date, Time & Cron utility.

lwdtc 上游为 CMake INTERFACE 库（library.cmake 将 lwdtc.c 以
target_sources INTERFACE 形式并入消费者），不产出静态库制品。
本配方用最小 CMake wrapper 将 lwdtc.c 编译为静态库并安装头文件。

OHOS 适配点：上游默认 LWDTC_CFG_GET_LOCALTIME 使用 Windows 专用
localtime_s，OHOS (musl libc) 无此符号；generate() 生成注入
lwdtc_opts.h 改用 POSIX localtime_r（参数重排），随包安装为默认用户配置。
"""
import os

from conan import ConanFile
from conan.tools.cmake import CMake, CMakeToolchain, cmake_layout
from conan.tools.files import get, save, copy, apply_conandata_patches, export_conandata_patches


class LwdtcConan(ConanFile):
    name = "lwdtc"
    version = "1.0.0"
    description = "Lightweight Date, Time & Cron utility library"
    license = "MIT"
    homepage = "https://github.com/MaJerle/lwdtc"
    url = "https://github.com/MaJerle/lwdtc"
    package_type = "library"

    settings = "os", "compiler", "build_type", "arch"
    options = {"shared": [True, False], "fPIC": [True, False]}
    default_options = {"shared": False, "fPIC": True}

    def configure(self):
        if self.options.shared:
            self.options.rm_safe("fPIC")

    def export_sources(self):
        export_conandata_patches(self)

    def layout(self):
        cmake_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def generate(self):
        # OHOS/musl 无 localtime_s，注入 POSIX localtime_r 用户配置头
        opts = "\n".join(
            [
                "#ifndef LWDTC_OPTS_HDR_H",
                "#define LWDTC_OPTS_HDR_H",
                "",
                "#include <time.h>",
                "",
                "#ifndef LWDTC_CFG_GET_LOCALTIME",
                "#define LWDTC_CFG_GET_LOCALTIME(_struct_tm_ptr_, _const_time_t_ptr_) \\",
                "    (void)localtime_r((_const_time_t_ptr_), (_struct_tm_ptr_))",
                "#endif",
                "",
                "#endif",
                "",
            ]
        )
        gen_dir = os.path.join(self.build_folder, "gen")
        os.makedirs(gen_dir, exist_ok=True)
        save(self, os.path.join(gen_dir, "lwdtc_opts.h"), opts)
        # 最小 CMake wrapper：将上游 lwdtc.c 编译为静态/共享库并安装
        src = self.source_folder.replace(os.sep, "/")
        cmake_lists = "\n".join(
            [
                "cmake_minimum_required(VERSION 3.15)",
                "project(lwdtc_build C)",
                f"add_library(lwdtc {'SHARED' if self.options.shared else 'STATIC'} {src}/lwdtc/src/lwdtc/lwdtc.c)",
                "target_include_directories(lwdtc PUBLIC",
                f"    {src}/lwdtc/src/include",
                '    "${CMAKE_CURRENT_BINARY_DIR}/gen")',
                "if(BUILD_SHARED_LIBS)",
                '    set_target_properties(lwdtc PROPERTIES OUTPUT_NAME "lwdtc")',
                "endif()",
                "install(TARGETS lwdtc ARCHIVE DESTINATION lib LIBRARY DESTINATION lib)",
                f"install(DIRECTORY {src}/lwdtc/src/include/ DESTINATION include)",
                'install(FILES "${CMAKE_CURRENT_BINARY_DIR}/gen/lwdtc_opts.h" DESTINATION include)',
                "",
            ]
        )
        # 写入 source_folder 子目录，供 CMake.configure(build_script_folder=...) 定位
        save(self, os.path.join(self.source_folder, "lwdtc_cmake", "CMakeLists.txt"), cmake_lists)
        tc = CMakeToolchain(self)
        tc.variables["BUILD_SHARED_LIBS"] = bool(self.options.shared)
        tc.variables["CMAKE_POSITION_INDEPENDENT_CODE"] = (
            True if self.options.get_safe("fPIC") else False
        )
        tc.generate()

    def build(self):
        apply_conandata_patches(self)
        cmake = CMake(self)
        cmake.configure(build_script_folder="lwdtc_cmake")
        cmake.build()

    def package(self):
        cmake = CMake(self)
        cmake.install()
        copy(
            self,
            "LICENSE",
            src=self.source_folder,
            dst=os.path.join(self.package_folder, "licenses"),
        )

    def package_info(self):
        self.cpp_info.libs = ["lwdtc"]
        self.cpp_info.set_property("cmake_file_name", "lwdtc")
        self.cpp_info.set_property("cmake_target_name", "lwdtc::lwdtc")