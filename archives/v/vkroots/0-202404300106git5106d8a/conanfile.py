#!/usr/bin/env python3
"""Conan recipe for vkroots — a header-only framework for writing Vulkan layers.

上游 meson.build 只做三件事：install_headers('vkroots.h')、
declare_dependency(include_directories: '.')、生成 pkgconfig —— **不产出任何编译产物**，
故本配方 package_type = "header-library"。build() 不编译任何东西，只做实质性校验
（不得伪造编译日志 —— R34；仓库既有做法同 archives/v/vkfft）。

⚠️ 版本锁定：本配方锁定上游 commit 5106d8a（2024-04-30 快照）。
上游 main 已使用 std::format / std::format_string / std::ranges::any_of，
OHOS 工具链 libc++ 15 不含 std::format，实测编译失败（5 处 error），故不可指向 main。
"""
import os

from conan import ConanFile
from conan.errors import ConanException
from conan.tools.files import apply_conandata_patches, copy, export_conandata_patches, get
from conan.tools.layout import basic_layout


class VkrootsConan(ConanFile):
    name = "vkroots"
    version = "0-202404300106git5106d8a"
    description = "vkroots — a simple framework for writing Vulkan layers (header-only)"
    license = "Apache-2.0 OR MIT"
    homepage = "https://github.com/Joshua-Ashton/vkroots"
    url = "https://gitcode.com/OpenHarmonyPCDeveloper/build_in_harmonyos"

    package_type = "header-library"

    settings = "os", "compiler", "build_type", "arch"

    no_copy_source = True

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        # vkroots.h 直接 include <vulkan/vk_layer.h> 与 <vulkan/vulkan.h>。
        # OHOS SDK sysroot 只提供 vulkan.h / vulkan_core.h / vulkan_ohos.h，
        # **不提供 vk_layer.h** —— 故必须依赖上游 Vulkan-Headers。
        # 传递性由 package_info() 的 cpp_info.requires 显式声明（仓库既有写法，见 vkfft / abpoa）。
        # visible=True 是必需的：vulkan-headers 的 package_type 为 "build-scripts"，
        # Conan 会据此自动把该依赖置为不可见（visible=False），进而使 cpp_info.requires
        # 校验报 "not a direct requirement of the recipe"；显式声明可见性后消费者才能拿到其头文件。
        self.requires("vulkan-headers/vulkan-sdk-1.4.357.0", visible=True)

    def layout(self):
        basic_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def build(self):
        # header-only：没有编译阶段（不伪造编译日志，R34）。
        # 此处只做实质性校验：vkroots.h 必须存在于源码树，否则安装出来的是空包。
        apply_conandata_patches(self)
        header = os.path.join(self.source_folder, "vkroots.h")
        if not os.path.isfile(header):
            raise ConanException(f"vkroots.h missing under {self.source_folder}")

    def package(self):
        # 变体 A（header-only 库）：只装头文件 + 许可证
        copy(self, "vkroots.h", src=self.source_folder,
             dst=os.path.join(self.package_folder, "include"))
        copy(self, "LICENSE", src=self.source_folder,
             dst=os.path.join(self.package_folder, "licenses"), keep_path=False)
        copy(self, "LICENSES/*", src=self.source_folder,
             dst=os.path.join(self.package_folder, "licenses"), keep_path=False)

    def package_id(self):
        # 无编译产物：os/compiler/build_type 不影响制品内容 → 单一 package_id
        self.info.clear()

    def package_info(self):
        # vulkan-headers 的 package_type 为 "build-scripts"，Conan 不会通过 cpp_info
        # 导出其 include 目录（该配方的 package_info 仅打印 CPATH=...，实测生成的
        # vulkan-headers_INCLUDE_DIRS_RELEASE 为空）。而 vkroots.h 直接 include
        # <vulkan/vk_layer.h> 与 <vulkan/vulkan.h>，消费者（如 test_package）必须能
        # 解析到该目录，故在此显式补上依赖的 include 路径。
        # 说明：该路径来源于依赖包的 package_folder，随 Conan 缓存位置而变；
        # C++ 编译发生在各消费者本地，故可接受（已在 notes.md 声明该取舍）。
        vulkan_headers_inc = os.path.join(
            self.dependencies["vulkan-headers"].package_folder, "include")
        self.cpp_info.includedirs = ["include", vulkan_headers_inc]
        # vkroots 的公开头文件 include 了 <vulkan/vk_layer.h>，故必须把
        # vulkan-headers 作为传递依赖暴露给消费者（否则消费端 CMakeDeps 不会
        # 生成 vulkan-headers 的 config）。
        # 仓库既有写法：无组件的依赖写作 "包名::包名"（见 vkfft / abpoa）。
        self.cpp_info.requires = ["vulkan-headers::vulkan-headers"]
        # 上游 meson default_options 要求 cpp_std=c++20；用 cpp_info.cxxflags 向下游传递
        # （仓库既有做法，见 archives/a/async_simple/1.4、archives/g/glaze/8.3.0）
        self.cpp_info.cxxflags = ["-std=c++20"]
        self.cpp_info.set_property("cmake_file_name", "vkroots")
        self.cpp_info.set_property("cmake_target_name", "vkroots::vkroots")
        self.cpp_info.set_property("pkg_config_name", "vkroots")
