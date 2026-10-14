#!/usr/bin/env python3
"""Conan recipe — opencl 3.0 (header-only, KhronosGroup/OpenCL-Headers)"""
import os
from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.files import get, copy, apply_conandata_patches


class OpenclConan(ConanFile):
    name = "opencl"
    version = "3.0"
    description = "OpenCL API C language headers (Khronos Group)"
    license = "Apache-2.0"
    homepage = "https://github.com/KhronosGroup/OpenCL-Headers"
    package_type = "header-library"
    settings = "os", "arch", "compiler", "build_type"
    no_copy_source = True

    def export_sources(self):
        # header-only：导出头文件目录便于离线构建（与 no_copy_source 配合）
        copy(self, "CL/*", src=self.recipe_folder, dst=self.export_sources_folder)

    def configure(self):
        # R32 平台检测：header-only 库理论平台无关，但仍遵守规程做白名单校验。
        if self.settings.os not in ("Linux", "OHOS", "FreeBSD", "Macos", "Windows"):
            raise ConanInvalidConfiguration(
                "opencl 只支持 Linux/OHOS/FreeBSD/Macos/Windows，当前: {}".format(self.settings.os))

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)
        apply_conandata_patches(self)

    def build(self):
        # header-only：无编译步骤
        pass

    def package(self):
        # OpenCL-Headers 源码的 CL/ 目录下即所有公开头文件，安装到 include/CL/。
        copy(
            self,
            "*.h",
            src=os.path.join(self.source_folder, "CL"),
            dst=os.path.join(self.package_folder, "include", "CL"),
        )
        copy(
            self,
            "LICENSE*",
            src=self.source_folder,
            dst=os.path.join(self.package_folder, "licenses"),
            keep_path=False,
        )

    def package_info(self):
        self.cpp_info.libs = []
        self.cpp_info.includedirs = ["include"]