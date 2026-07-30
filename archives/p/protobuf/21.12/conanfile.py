#!/usr/bin/env python3
"""Conan CMake recipe for protobuf 21.12 (3.x LTS).

protobuf 21.12 is the last C++14-compatible release before the 4.21 threshold
after which protobuf requires C++17 + abseil-cpp. This version is chosen
specifically to keep the dependency chain minimal for brpc and other consumers
on OHOS aarch64.
"""
import os

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.build import check_min_cppstd
from conan.tools.cmake import CMake, CMakeToolchain, cmake_layout
from conan.tools.files import apply_conandata_patches, export_conandata_patches, get


class ProtobufConan(ConanFile):
    name = "protobuf"
    version = "21.12"
    description = "Google's language-neutral, platform-neutral, extensible mechanism for serializing structured data"
    license = "BSD-3-Clause"
    homepage = "https://protobuf.dev/"
    url = ""  # CI fills this
    package_type = "library"

    settings = "os", "arch", "compiler", "build_type"
    options = {
        "shared": [True, False],
        "fPIC": [True, False],
        "with_zlib": [True, False],
    }
    default_options = {
        "shared": False,
        "fPIC": True,
        "with_zlib": False,
    }

    def export_sources(self):
        export_conandata_patches(self)

    def config_options(self):
        if self.settings.os == "Windows":
            self.options.rm_safe("fPIC")

    def configure(self):
        if self.options.shared:
            self.options.rm_safe("fPIC")

    def validate(self):
        if self.settings.compiler.get_safe("cppstd"):
            check_min_cppstd(self, 14)

    def requirements(self):
        pass

    def layout(self):
        cmake_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def generate(self):
        tc = CMakeToolchain(self)
        tc.variables["protobuf_BUILD_TESTS"] = False
        tc.variables["protobuf_BUILD_SHARED_LIBS"] = "ON" if self.options.shared else "OFF"
        tc.variables["protobuf_BUILD_PROTOC_BINARIES"] = True
        tc.variables["protobuf_WITH_ZLIB"] = "ON" if self.options.with_zlib else "OFF"
        tc.variables["protobuf_ABSOLUTE_TEST_PLUGIN_PATH"] = False
        tc.variables["BUILD_SHARED_LIBS"] = "ON" if self.options.shared else "OFF"
        tc.generate()

    def build(self):
        apply_conandata_patches(self)
        cmake = CMake(self)
        cmake.configure()
        cmake.build()

    def package(self):
        cmake = CMake(self)
        cmake.install()
        # protobuf CMake install already handles bin/lib/include layouts.
        # Strip any stray .la files
        lib_dir = os.path.join(self.package_folder, "lib")
        if os.path.isdir(lib_dir):
            for name in os.listdir(lib_dir):
                if name.endswith(".la"):
                    path = os.path.join(lib_dir, name)
                    try:
                        os.remove(path)
                    except OSError:
                        pass

    def package_info(self):
        self.cpp_info.libs = ["protobuf", "protobuf-lite"]
        self.cpp_info.set_property("cmake_file_name", "protobuf")
        self.cpp_info.set_property("cmake_target_name", "protobuf::libprotobuf")
        if not self.options.shared:
            if self.settings.os in ("Linux", "OHOS"):
                self.cpp_info.system_libs.append("pthread")
                self.cpp_info.system_libs.append("dl")
