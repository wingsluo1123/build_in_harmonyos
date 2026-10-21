#!/usr/bin/env python3
"""Conan recipe — lwgps 2.4.0 (CMake, header + single C file library).

上游 CMake 无 install 规则（顶层构建仅装配测试目标），故 package()
手工复制头文件与静态库（参考 libsodium 无 install 规则先例）。
"""
import os
import shutil

from conan import ConanFile
from conan.tools.cmake import CMake, CMakeToolchain, cmake_layout
from conan.tools.files import apply_conandata_patches, copy, get


class LwgpsConan(ConanFile):
    name = "lwgps"
    version = "2.4.0"
    description = "Lightweight GPS NMEA parser library (MaJerle)"
    license = "MIT"
    homepage = "https://github.com/MaJerle/lwgps"
    url = ""  # CI fills this

    package_type = "library"

    settings = "os", "compiler", "build_type", "arch"
    options = {"shared": [True, False]}
    default_options = {"shared": False}

    def export_sources(self):
        apply_conandata_patches(self)

    def requirements(self):
        pass

    def layout(self):
        cmake_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def generate(self):
        tc = CMakeToolchain(self)
        # R26: 系统同名库默认静态；lwgps 非系统同名，按 shared 选项
        tc.variables["BUILD_SHARED_LIBS"] = "ON" if self.options.shared else "OFF"
        tc.generate()

    def build(self):
        apply_conandata_patches(self)
        cmake = CMake(self)
        # 只构建 lwgps 库子目录：顶层 CMakeLists 会把 tests/test_parse_sat_det
        # 的 lwgps_opts.h（LWGPS_CFG_STATEMENT_GPGSV_SAT_DET=1）注入库编译，
        # 造成库与消费者头文件结构体布局错位（test_package 段错误实测）。
        # 独立构建使用默认 opts，与打包头文件一致。
        cmake.configure(build_script_folder="lwgps")
        cmake.build()

    def package(self):
        # 上游无 install 规则：手工复制头文件 + 静态库
        inc_src = os.path.join(self.source_folder, "lwgps", "src", "include", "lwgps")
        inc_dst = os.path.join(self.package_folder, "include", "lwgps")
        copy(self, "*.h", src=inc_src, dst=inc_dst, keep_path=False)
        copy(self, "lwgps.hpp", src=inc_src, dst=inc_dst, keep_path=False)
        # lwgps_opt.h 会 #include "lwgps_opts.h"：以官方模板产出默认配置头
        copy(self, "lwgps_opts_template.h", src=inc_src, dst=inc_dst, keep_path=False)
        shutil.copy(
            os.path.join(inc_dst, "lwgps_opts_template.h"),
            os.path.join(inc_dst, "lwgps_opts.h"),
        )
        # 静态库（library-only 构建产物位于构建目录根）
        lib_src = os.path.join(self.build_folder, "liblwgps.a")
        if not os.path.exists(lib_src):
            raise ConanException(f"构建产物缺失: {lib_src}")
        copy(self, "liblwgps.a", src=os.path.dirname(lib_src),
             dst=os.path.join(self.package_folder, "lib"), keep_path=False)

    def package_info(self):
        self.cpp_info.libs = ["lwgps"]
        self.cpp_info.includedirs = ["include"]