#!/usr/bin/env python3
"""Conan recipe — apitrace 14.0 (CMake)

API call tracing framework for OpenGL, Direct3D and other graphics APIs.
Builds the egltrace.so wrapper for EGL/OpenGL ES tracing on HarmonyOS.
"""
import os

from conan import ConanFile
from conan.tools.cmake import CMake, CMakeToolchain, cmake_layout
from conan.tools.files import (
    apply_conandata_patches,
    export_conandata_patches,
    get,
)


class ApitraceConan(ConanFile):
    name = "apitrace"
    version = "14.0"
    description = "API call tracing framework for OpenGL, Direct3D and other graphics APIs"
    license = "MIT"
    homepage = "https://github.com/apitrace/apitrace"
    url = "https://gitcode.com/OpenHarmonyPCDeveloper/build_in_harmonyos"

    package_type = "application"
    settings = "os", "compiler", "build_type", "arch"

    def export_sources(self):
        export_conandata_patches(self)

    def layout(self):
        cmake_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)
        # GitHub tarball does not include git submodules; fetch them individually.
        # Commit hashes are pinned to the 14.0 tag's submodule state.
        submodules = [
            ("thirdparty/brotli", "https://github.com/google/brotli/archive/ed738e842d2fbdf2d6459e39267a633c4a9b2f5d.tar.gz"),
            ("thirdparty/gtest", "https://github.com/google/googletest/archive/52eb8108c5bdec04579160ae17225d66034bd723.tar.gz"),
            ("thirdparty/libbacktrace", "https://github.com/ianlancetaylor/libbacktrace/archive/793921876c981ce49759114d7bb89bb89b2d3a2d.tar.gz"),
            ("thirdparty/libpng", "https://github.com/apitrace/libpng/archive/2b978915d82377df13fcbb1fb56660195ded868a.tar.gz"),
            ("thirdparty/snappy", "https://github.com/google/snappy/archive/6af9287fbdb913f0794d0148c6aa43b58e63c8e3.tar.gz"),
            ("thirdparty/zlib", "https://github.com/madler/zlib/archive/51b7f2abdade71cd9bb0e7a373ef2610ec6f9daf.tar.gz"),
            ("thirdparty/zstd", "https://github.com/facebook/zstd/archive/f8745da6ff1ad1e7bab384bd1f9d742439278e99.tar.gz"),
            ("thirdparty/directxmath", "https://github.com/microsoft/DirectXMath/archive/56206b1916646b29b37e1eac56e96e2008d6c71f.tar.gz"),
            ("frametrim/tests", "https://github.com/apitrace/gltrim-tests/archive/12ceee777636bfca4a35390697e8e702254a82b2.tar.gz"),
        ]
        for dest, url in submodules:
            dest_path = os.path.join(self.source_folder, dest)
            os.makedirs(dest_path, exist_ok=True)
            # Use curl with retries; fall back to ghfast.top mirror if direct fails
            self.run(
                f"curl -fsSL --connect-timeout 60 --retry 3 '{url}' | "
                f"tar xzf - -C '{dest_path}' --strip-components=1 || "
                f"curl -fsSL --connect-timeout 60 --retry 3 'https://ghfast.top/{url}' | "
                f"tar xzf - -C '{dest_path}' --strip-components=1"
            )

    def generate(self):
        tc = CMakeToolchain(self)
        tc.variables["CMAKE_BUILD_TYPE"] = "Release"
        tc.variables["CMAKE_SYSTEM_NAME"] = "Linux"
        tc.variables["ENABLE_GUI"] = "OFF"
        tc.variables["ENABLE_X11"] = "OFF"
        tc.variables["ENABLE_EGL"] = "ON"
        tc.variables["ENABLE_WAFFLE"] = "OFF"
        tc.variables["ENABLE_TESTS"] = "OFF"
        tc.variables["BUILD_TESTING"] = "OFF"
        tc.variables["ENABLE_STATIC_SNAPPY"] = "ON"
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
        self.cpp_info.bindirs = ["bin"]
        self.cpp_info.libdirs = ["lib"]
