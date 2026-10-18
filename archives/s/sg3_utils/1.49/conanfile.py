#!/usr/bin/env python3
"""Conan recipe — sg3_utils 1.49（SCSI generic 工具集 + libsgutils2），HarmonyOS PC。

构建系统选择
    上游 1.49 自 1.44 起同时维护 Autotools 与 CMake 两套构建系统。官方 GitHub tag 归档
    不含预生成的 configure，构建机（含 CI）也无 automake/libtool，因此统一走上游自带
    CMake，无需 autoreconf。

鸿蒙适配要点（详见 notes.md）
    上游 CMake 以 `CMAKE_SYSTEM_NAME STREQUAL "Linux"` 判定 Linux 专属的 pass-through（PT）
    实现。HarmonyOS 上该条件不成立 → 落入 `SG_LIB_LINUX=0` 的降级分支：
    PT 全部编成 PT_DUMMY 空实现，且依赖真实 PT 的 14 个可执行文件直接不构建
    （SG3_UTILS_LINUX_ONLY 的 13 个 + sg_scan；实测可执行文件 70/84，其中 sg_* 工具 61/72。
    注意 sg_raw/sg_read_buffer 在 src/CMakeLists.txt 属无条件构建，不在此列）。
    补丁 0001 把 HarmonyOS/OHOS 并入 Linux 分支——sysroot 已具备
    scsi/sg.h、linux/bsg.h、linux/nvme_ioctl.h，真实 PT 可编译，故为真实实现而非桩（R40）。

发布形态
    库名上游为 libsgutils2-<ver>.a / libsgutils2-1.49.so.2（OUTPUT_NAME 内嵌版本），
    且上游 install(TARGETS) 只声明 LIBRARY DESTINATION、静态库不会被安装。package()
    统一成 libsgutils2.a / libsgutils2.so 惯例名，供下游 -lsgutils2 直接解析。
"""
import os

from conan import ConanFile
from conan.tools.cmake import CMake, CMakeToolchain, cmake_layout
from conan.tools.files import (
    apply_conandata_patches,
    copy,
    export_conandata_patches,
    get,
    rename,
    rm,
)


class Sg3UtilsConan(ConanFile):
    name = "sg3_utils"
    version = "1.49"
    description = "SCSI generic (sg) utilities and libsgutils2 library for HarmonyOS PC"
    license = "GPL-2.0-or-later"
    homepage = "https://sg.danny.cz/sg/sg3_utils.html"
    url = "https://github.com/doug-gilbert/sg3_utils"

    package_type = "library"

    settings = "os", "compiler", "build_type", "arch"
    options = {"shared": [True, False]}
    default_options = {"shared": False}

    def export_sources(self):
        export_conandata_patches(self)

    # requirements(): 无第三方库依赖，仅 libc + pthread（W0 结论见 notes.md）

    def layout(self):
        cmake_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def generate(self):
        tc = CMakeToolchain(self)
        tc.variables["BUILD_SHARED_LIBS"] = bool(self.options.shared)
        # 显式关闭 PT_DUMMY：降级分支必须不生效（补丁 0001 已让 HarmonyOS 走 Linux 分支）
        tc.variables["ENABLE_PT_DUMMY"] = False
        # 下游可能把静态库链进共享对象，统一开 PIC
        tc.variables["CMAKE_POSITION_INDEPENDENT_CODE"] = True
        tc.generate()

    def build(self):
        apply_conandata_patches(self)
        cmake = CMake(self)
        cmake.configure()
        cmake.build()

    def package(self):
        copy(
            self,
            "COPYING",
            src=self.source_folder,
            dst=os.path.join(self.package_folder, "licenses"),
        )
        cmake = CMake(self)
        cmake.install()

        libdir = os.path.join(self.package_folder, "lib")
        if not self.options.shared:
            # 上游 install(TARGETS) 未声明 ARCHIVE DESTINATION，静态库不会进 package，
            # 从构建目录补齐，并归一为常规名 libsgutils2.a
            copy(
                self,
                f"libsgutils2-{self.version}.a",
                src=os.path.join(self.build_folder, "lib"),
                dst=libdir,
            )
            rename(
                self,
                os.path.join(libdir, f"libsgutils2-{self.version}.a"),
                os.path.join(libdir, "libsgutils2.a"),
            )
            # 静态构建下上游仍无条件创建指向 .so 的开发符号链接，此处为悬空链接，删除
            rm(self, "libsgutils2.so*", libdir)

    def package_info(self):
        self.cpp_info.libs = ["sgutils2"]
        self.cpp_info.includedirs = ["include"]
        self.cpp_info.bindirs = ["bin"]
        self.cpp_info.system_libs = ["pthread"]
        # CLI 工具（72 个，见 commands.json）加入运行环境 PATH
        self.runenv_info.prepend_path("PATH", os.path.join(self.package_folder, "bin"))
