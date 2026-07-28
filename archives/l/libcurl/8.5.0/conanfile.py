#!/usr/bin/env python3
"""Conan recipe — libcurl 8.5.0 (CMake)"""
import os, glob

from conan import ConanFile
from conan.tools.files import get, apply_conandata_patches, export_conandata_patches
from conan.tools.cmake import CMake, CMakeDeps, CMakeToolchain, cmake_layout


class LibcurlConan(ConanFile):
    name = "libcurl"
    version = "8.5.0"
    description = "Multiprotocol file transfer library"
    license = "curl"
    homepage = "https://curl.se"
    url = ""
    package_type = "library"
    settings = "os", "compiler", "build_type", "arch"
    options = {"shared": [True, False], "fPIC": [True, False]}
    default_options = {"shared": True, "fPIC": True}

    def config_options(self):
        if self.settings.os == "Windows":
            self.options.rm_safe("fPIC")

    def configure(self):
        if self.options.shared:
            self.options.rm_safe("fPIC")

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        self.requires("zlib/1.3.1")

    def layout(self):
        cmake_layout(self, src_folder=".")

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def generate(self):
        CMakeDeps(self).generate()
        tc = CMakeToolchain(self)
        tc.variables["BUILD_SHARED_LIBS"] = "ON" if self.options.shared else "OFF"
        tc.variables["BUILD_CURL_EXE"] = "OFF"
        tc.variables["BUILD_TESTING"] = "OFF"
        tc.variables["CURL_USE_OPENSSL"] = "OFF"
        tc.variables["CURL_ZLIB"] = "ON"
        if self.settings.os == "OHOS":
            # E091: Suppress sockaddr_storage redefinition from linux/socket.h
            tc.extra_cflags.append("-D_UAPI_LINUX_SOCKET_H")
        tc.variables["CURL_BROTLI"] = "OFF"
        tc.variables["CURL_ZSTD"] = "OFF"
        tc.variables["CURL_USE_LIBSSH2"] = "OFF"
        tc.variables["CURL_USE_LIBPSL"] = "OFF"
        tc.variables["CURL_USE_LIBIDN2"] = "OFF"
        tc.variables["USE_NGHTTP2"] = "OFF"
        tc.variables["BUILD_EXAMPLES"] = "OFF"
        tc.variables["CURL_ENABLE_EXPORT_TARGET"] = "ON"
        if self.settings.os == "OHOS":
            for lang in ("C", "CXX"):
                tc.variables[f"CMAKE_SHARED_LIBRARY_SONAME_{lang}_FLAG"] = "-Wl,-soname,"
                tc.variables[f"CMAKE_SHARED_LIBRARY_RUNTIME_{lang}_FLAG"] = "-Wl,-rpath,"
                tc.variables[f"CMAKE_SHARED_LIBRARY_RUNTIME_{lang}_FLAG_SEP"] = ":"
                tc.variables[f"CMAKE_SHARED_LIBRARY_RPATH_LINK_{lang}_FLAG"] = "-Wl,-rpath-link,"
            tc.variables["CMAKE_BUILD_RPATH_USE_ORIGIN"] = True
        tc.generate()

    def build(self):
        apply_conandata_patches(self)
        cmake = CMake(self)
        cmake.configure()
        cmake.build()

    def package(self):
        cmake = CMake(self)
        cmake.install()
        if self.settings.os == "OHOS" and self.options.shared:
            libdir = os.path.join(self.package_folder, "lib")
            sos = glob.glob(os.path.join(libdir, "**", "*.so*"), recursive=True)
            objcopy = "/data/service/hnp/bin/llvm-objcopy"
            signer = "/data/service/hnp/bin/binary-sign-tool"
            for so in sos:
                if os.path.islink(so):
                    continue
                self.run(f'{objcopy} --remove-section .codesign "{so}" 2>/dev/null || true')
                self.run(f'{signer} sign -inFile "{so}" -outFile "{so}" -selfSign 1')

    def package_info(self):
        self.cpp_info.libs = ["curl"]
        self.cpp_info.set_property("cmake_file_name", "CURL")
        self.cpp_info.set_property("cmake_target_name", "CURL::libcurl")
        self.cpp_info.set_property("pkg_config_name", "libcurl")
