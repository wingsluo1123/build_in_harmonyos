#!/usr/bin/env python3
"""Conan recipe — ktx 4.4.2 (Khronos KTX texture library, CMake)."""
from conan import ConanFile
from conan.tools.cmake import CMake, CMakeToolchain, cmake_layout
from conan.tools.files import get, apply_conandata_patches, export_conandata_patches


class KtxConan(ConanFile):
    name = "ktx"
    version = "4.4.2"
    description = "Libraries and tools to create and read KTX image texture files"
    license = "Apache-2.0"
    homepage = "https://github.com/KhronosGroup/KTX-Software"
    url = ""

    package_type = "library"
    settings = "os", "compiler", "build_type", "arch"
    options = {"shared": [True, False]}
    default_options = {"shared": True}

    def export_sources(self):
        export_conandata_patches(self)

    def layout(self):
        cmake_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def generate(self):
        tc = CMakeToolchain(self)
        # Disable platform-specific features not available on OHOS
        tc.cache_variables["KTX_FEATURE_VK_UPLOAD"] = "OFF"
        tc.cache_variables["KTX_FEATURE_GL_UPLOAD"] = "OFF"
        tc.cache_variables["KTX_FEATURE_JNI"] = "OFF"
        tc.cache_variables["KTX_FEATURE_PY"] = "OFF"
        tc.cache_variables["KTX_FEATURE_DOC"] = "OFF"
        tc.cache_variables["KTX_FEATURE_TESTS"] = "OFF"
        tc.cache_variables["KTX_FEATURE_LOADTEST_APPS"] = ""
        tc.cache_variables["KTX_FEATURE_TOOLS"] = "OFF"
        tc.cache_variables["KTX_FEATURE_TOOLS_CTS"] = "OFF"
        # Avoid try-link on OHOS
        tc.cache_variables["CMAKE_TRY_COMPILE_TARGET_TYPE"] = "STATIC_LIBRARY"
        tc.generate()

    def build(self):
        apply_conandata_patches(self)
        cmake = CMake(self)
        cmake.configure()
        cmake.build()

    def package(self):
        cmake = CMake(self)
        cmake.install()

    def package_info(self):
        self.cpp_info.libs = ["ktx"]
        self.cpp_info.set_property("cmake_file_name", "KTX")
        self.cpp_info.set_property("cmake_target_name", "ktx")
