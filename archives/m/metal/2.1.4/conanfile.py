#!/usr/bin/env python3
"""Conan recipe — metal 2.1.4 (header-only C++14 template metaprogramming library)

无编译阶段：源码包仅含头文件（include/metal.hpp 聚合头 + include/metal/**）。
"""
import os
from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.files import get, copy, apply_conandata_patches, export_conandata_patches
from conan.tools.cmake import cmake_layout


class MetalConan(ConanFile):
    name = "metal"
    version = "2.1.4"
    description = "Metal — C++14 template metaprogramming library"
    license = "MIT"
    homepage = "https://github.com/brunocodutra/metal"
    url = ""  # CI fills this

    package_type = "header-library"
    settings = "os", "arch", "compiler", "build_type"
    no_copy_source = True

    def configure(self):
        # R32 平台白名单：header-only 库理论平台无关，仍按规程校验。
        if self.settings.os not in ("Linux", "OHOS", "FreeBSD", "Macos", "Windows"):
            raise ConanInvalidConfiguration(
                "metal 只支持 Linux/OHOS/FreeBSD/Macos/Windows，当前: {}".format(self.settings.os))

    def export_sources(self):
        export_conandata_patches(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def layout(self):
        cmake_layout(self, src_folder=".")

    def build(self):
        # 补丁骨架：conandata.yml patches 为空，无实际补丁；header-only 无编译步骤
        apply_conandata_patches(self)

    def package(self):
        # 聚合头 include/metal.hpp 与 include/metal/** 全部安装到 include/。
        copy(
            self,
            "*.hpp",
            src=os.path.join(self.source_folder, "include"),
            dst=os.path.join(self.package_folder, "include"),
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
