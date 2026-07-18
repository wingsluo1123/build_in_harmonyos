#!/usr/bin/env python3
"""Conan recipe — nanopb 0.4.9.1 (CMake static runtime library)."""

import os
import shlex
import stat
import shutil
import sys

from conan import ConanFile
from conan.tools.cmake import CMake, CMakeToolchain, cmake_layout
from conan.tools.files import (
    apply_conandata_patches,
    export_conandata_patches,
    get,
    save,
)


class NanopbConan(ConanFile):
    name = "nanopb"
    version = "0.4.9.1"
    description = "Protocol Buffers implementation with small code size"
    license = "zlib"
    homepage = "https://jpa.kapsi.fi/nanopb/"
    url = "https://github.com/nanopb/nanopb"

    package_type = "static-library"
    settings = "os", "compiler", "build_type", "arch"

    def export_sources(self):
        export_conandata_patches(self)

    def layout(self):
        cmake_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def generate(self):
        tc = CMakeToolchain(self)
        tc.variables["BUILD_SHARED_LIBS"] = False
        tc.variables["BUILD_STATIC_LIBS"] = True
        tc.variables["nanopb_BUILD_RUNTIME"] = True
        tc.variables["nanopb_BUILD_GENERATOR"] = False

        # CMake does not recognize OHOS as a target platform. The Conan
        # profile still supplies the actual OHOS compiler and architecture.
        if self.settings.os in ("Linux", "OHOS"):
            tc.cache_variables["CMAKE_SYSTEM_NAME"] = "Linux"
            if self.settings.os == "OHOS":
                tc.cache_variables["CMAKE_SYSTEM_PROCESSOR"] = "aarch64"
        tc.generate()

    def build(self):
        apply_conandata_patches(self)

        cmake = CMake(self)
        cmake.configure()
        cmake.build()

        # Nanopb's upstream official suite is maintained as SCons tests.
        # Keep it in the Conan build so CI can verify the complete runtime.
        compilers = self.conf.get(
            "tools.build:compiler_executables", default={}, check_type=dict
        )
        cc = compilers.get("c", "cc") if compilers else "cc"
        cxx = compilers.get("cpp", "c++") if compilers else "c++"
        protoc_path = shutil.which("protoc")
        if protoc_path:
            protoc = protoc_path
        else:
            # SCons treats PROTOC as the path to one executable. Passing
            # "python -m grpc_tools.protoc" directly works in a shell, but
            # SCons then tries to execute the whole string as a file and
            # fails on clean OHOS workers. Create a tiny executable wrapper
            # in the Conan build folder so SCons gets a real path.
            protoc = os.path.join(self.build_folder, "nanopb-protoc")
            save(
                self,
                protoc,
                "#!/bin/sh\n"
                f"exec {shlex.quote(sys.executable)} -m grpc_tools.protoc \"$@\"\n",
            )
            os.chmod(
                protoc,
                os.stat(protoc).st_mode
                | stat.S_IXUSR
                | stat.S_IXGRP
                | stat.S_IXOTH,
            )
        tests_dir = shlex.quote(self.source_folder + "/tests")
        plugin = shlex.quote(
            "--plugin=protoc-gen-nanopb="
            + self.source_folder
            + "/generator/protoc-gen-nanopb "
        )
        command = (
            "{python} -m SCons -C {tests} CC={cc} CXX={cxx} PROTOC={protoc} "
            "PROTOCFLAGS={plugin} NOVALGRIND=1 NODEFARGS=1"
        ).format(
            python=shlex.quote(sys.executable),
            tests=tests_dir,
            cc=shlex.quote(str(cc)),
            cxx=shlex.quote(str(cxx)),
            protoc=shlex.quote(protoc),
            plugin=plugin,
        )
        self.run(command)

    def package(self):
        cmake = CMake(self)
        cmake.install()

    def package_info(self):
        self.cpp_info.includedirs = ["include/nanopb"]
        self.cpp_info.libs = ["protobuf-nanopb"]
        self.cpp_info.set_property("cmake_file_name", "nanopb")
        self.cpp_info.set_property(
            "cmake_target_name", "nanopb::protobuf-nanopb-static"
        )
