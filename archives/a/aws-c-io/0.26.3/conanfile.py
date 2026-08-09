#!/usr/bin/env python3
"""Conan recipe for aws-c-io 0.26.3 — AWS I/O Library.

Provides platform-independent I/O abstractions including event loops,
streaming, TLS, and socket APIs. Uses aws-c-cal as the crypto backend
with BYO_CRYPTO=ON to avoid s2n dependency on OHOS.

Patch: The CMakeLists.txt uses `if (WIN32)` and `elseif (APPLE)` for
platform detection. On OHOS (CMAKE_SYSTEM_NAME=HarmonyOS), CMake 4.x
evaluates `if (WIN32)` as true even though WIN32 is empty, causing the
Windows branch to be entered instead of the Linux/HarmonyOS branch.
We replace these with explicit CMAKE_SYSTEM_NAME checks.
"""
import os

from conan import ConanFile
from conan.tools.files import get, apply_conandata_patches, export_conandata_patches, replace_in_file, save
from conan.tools.cmake import CMake, CMakeToolchain, CMakeDeps, cmake_layout


class AwscioConan(ConanFile):
    name = "aws-c-io"
    version = "0.26.3"
    description = "AWS I/O Library — event loops, streaming, TLS, socket APIs"
    license = "Apache-2.0"
    homepage = "https://github.com/awslabs/aws-c-io"
    url = "https://github.com/awslabs/aws-c-io"

    package_type = "library"

    settings = "os", "compiler", "build_type", "arch"
    options = {"shared": [True, False]}
    default_options = {"shared": False}

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        self.requires("aws-c-common/0.14.3")
        self.requires("aws-c-cal/0.9.13")
        self.requires("aws-c-compression/0.3.2")

    def layout(self):
        cmake_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def generate(self):
        tc = CMakeToolchain(self)
        tc.variables["BUILD_SHARED_LIBS"] = "ON" if self.options.shared else "OFF"
        tc.variables["BUILD_TESTING"] = "OFF"
        tc.variables["BYO_CRYPTO"] = "ON"
        tc.generate()

        deps = CMakeDeps(self)
        deps.set_property("aws-c-common", "cmake_target_name", "AWS::aws-c-common")
        deps.set_property("aws-c-cal", "cmake_target_name", "AWS::aws-c-cal")
        deps.set_property("aws-c-compression", "cmake_target_name", "AWS::aws-c-compression")
        deps.generate()

    def build(self):
        apply_conandata_patches(self)
        # Fix platform detection for OHOS:
        # 1. if(WIN32) evaluates true on OHOS with CMake 4.x — replace with explicit check
        # 2. Original source lacks "HarmonyOS" in the Linux/Android elseif — add it
        cmake_file = os.path.join(self.source_folder, "CMakeLists.txt")
        replace_in_file(self, cmake_file,
                        "if (WIN32)",
                        'if (CMAKE_SYSTEM_NAME STREQUAL "Windows")')
        replace_in_file(self, cmake_file,
                        'elseif (CMAKE_SYSTEM_NAME STREQUAL "Linux" OR CMAKE_SYSTEM_NAME STREQUAL "Android")',
                        'elseif (CMAKE_SYSTEM_NAME STREQUAL "Linux" OR CMAKE_SYSTEM_NAME STREQUAL "Android" OR CMAKE_SYSTEM_NAME STREQUAL "HarmonyOS")')
        replace_in_file(self, cmake_file,
                        "elseif (APPLE)",
                        'elseif (CMAKE_SYSTEM_NAME STREQUAL "Darwin")')
        # Add stub for aws_tls_handler_protocol when BYO_CRYPTO=ON
        # This function is normally defined in s2n/darwin/windows TLS code,
        # but with BYO_CRYPTO=ON, those sources are not compiled.
        # aws-c-http references this symbol, so we provide a stub.
        stub_path = os.path.join(self.source_folder, "source", "byo_crypto_stub.c")
        save(self, stub_path,
             '#include <aws/io/tls_channel_handler.h>\n'
             '#include <aws/common/byte_buf.h>\n'
             'struct aws_byte_buf aws_tls_handler_protocol(struct aws_channel_handler *handler) {\n'
             '    struct aws_byte_buf empty = {0};\n'
             '    return empty;\n'
             '}\n')
        replace_in_file(self, cmake_file,
                        "if (BYO_CRYPTO)\n    set(USE_S2N OFF)",
                        'if (BYO_CRYPTO)\n    set(USE_S2N OFF)\n    list(APPEND AWS_IO_TLS_SRC "${CMAKE_CURRENT_SOURCE_DIR}/source/byo_crypto_stub.c")')
        cmake = CMake(self)
        aws_common = self.dependencies["aws-c-common"]
        modules_dir = os.path.join(
            aws_common.package_folder,
            "lib", "cmake", "aws-c-common", "modules",
        )
        cmake.configure(variables={"CMAKE_MODULE_PATH": modules_dir})
        cmake.build()

    def package(self):
        cmake = CMake(self)
        cmake.install()

    def package_info(self):
        self.cpp_info.libs = ["aws-c-io"]
        self.cpp_info.includedirs = ["include"]
        if self.settings.os in ("Linux", "OHOS"):
            self.cpp_info.system_libs = ["pthread", "dl", "rt"]
