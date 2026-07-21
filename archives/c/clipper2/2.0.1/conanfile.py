#!/usr/bin/env python3
"""Conan recipe — clipper2 2.0.1 (CMake C++17 polygon clipping library).

Clipper2 是高性能多边形布尔运算和偏移库, 无第三方依赖, 使用 CMake 构建。
输出两个静态库: Clipper2 (标准) 和 Clipper2Z (带 z 坐标)。
"""
from conan import ConanFile
from conan.tools.files import get, apply_conandata_patches, export_conandata_patches
from conan.tools.cmake import CMake, CMakeToolchain, cmake_layout


class Clipper2Conan(ConanFile):
    name = "clipper2"
    version = "2.0.1"
    description = "C++17 polygon clipping and offsetting library"
    license = "BSL-1.0"
    homepage = "https://github.com/AngusJohnson/Clipper2"
    url = "https://gitcode.com/OpenHarmonyPCDeveloper/build_in_harmonyos"

    package_type = "library"

    settings = "os", "compiler", "build_type", "arch"
    options = {
        "shared": [True, False],
        "fPIC": [True, False],
    }
    default_options = {
        "shared": False,
        "fPIC": True,
    }

    def export_sources(self):
        export_conandata_patches(self)

    def config_options(self):
        if self.settings.os == "Windows":
            del self.options.fPIC

    def configure(self):
        if self.options.shared:
            self.options.rm_safe("fPIC")

    def layout(self):
        cmake_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def generate(self):
        tc = CMakeToolchain(self)
        # E092: CMake does not recognize OHOS as a target platform
        if self.settings.os in ("Linux", "OHOS"):
            tc.cache_variables["CMAKE_SYSTEM_NAME"] = "Linux"
            tc.cache_variables["CMAKE_SYSTEM_PROCESSOR"] = "aarch64"
        # Default to static library
        tc.variables["BUILD_SHARED_LIBS"] = "ON" if self.options.shared else "OFF"
        # Disable tests/examples/utils (tests require googletest git clone)
        tc.variables["CLIPPER2_TESTS"] = "OFF"
        tc.variables["CLIPPER2_EXAMPLES"] = "OFF"
        tc.variables["CLIPPER2_UTILS"] = "OFF"
        tc.generate()

    def build(self):
        apply_conandata_patches(self)
        cmake = CMake(self)
        cmake.configure(build_script_folder="CPP")
        cmake.build()

    def package(self):
        cmake = CMake(self)
        cmake.install()

    def package_info(self):
        self.cpp_info.set_property("cmake_file_name", "Clipper2")
        self.cpp_info.set_property("pkg_config_name", "Clipper2")

        clipper2 = self.cpp_info.components["clipper2"]
        clipper2.set_property("cmake_target_name", "Clipper2::Clipper2")
        clipper2.libs = ["Clipper2"]

        clipper2z = self.cpp_info.components["clipper2z"]
        clipper2z.set_property("cmake_target_name", "Clipper2::Clipper2Z")
        clipper2z.libs = ["Clipper2Z"]
