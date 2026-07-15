#!/usr/bin/env python3
"""Conan recipe - spirv-headers latest (header-only, vulkan-sdk-1.3.296.0)"""
import os
from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.files import get, copy
from conan.tools.cmake import cmake_layout


class SpirvHeadersConan(ConanFile):
    name = "spirv-headers"
    version = "latest"
    description = "SPIR-V Headers - machine-readable files for the SPIR-V Registry (header-only)"
    license = "MIT-KhronosGroup"
    homepage = "https://github.com/KhronosGroup/SPIRV-Headers"
    package_type = "header-library"
    settings = "os", "arch", "compiler", "build_type"
    no_copy_source = True

    def configure(self):
        # header-only 库与平台无关，但仍做白名单校验。
        if self.settings.os not in ("Linux", "OHOS", "FreeBSD", "Macos", "Windows"):
            raise ConanInvalidConfiguration(
                "spirv-headers 仅支持 Linux/OHOS/FreeBSD/Macos/Windows，当前: {}".format(self.settings.os))

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def layout(self):
        cmake_layout(self, src_folder=".")

    def build(self):
        # header-only：无编译步骤
        pass

    def package(self):
        # SPIRV-Headers 源码 include/spirv/ 下即所有公开头文件，安装到 include/spirv/。
        copy(
            self,
            "*.h",
            src=os.path.join(self.source_folder, "include"),
            dst=os.path.join(self.package_folder, "include"),
        )
        copy(
            self,
            "*.hpp",
            src=os.path.join(self.source_folder, "include"),
            dst=os.path.join(self.package_folder, "include"),
        )

    def package_info(self):
        self.cpp_info.libs = []
        self.cpp_info.includedirs = ["include"]
