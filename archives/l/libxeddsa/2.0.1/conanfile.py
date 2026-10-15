#!/usr/bin/env python3
"""Conan recipe — libxeddsa 2.0.1 (CMake, portable XEdDSA/Ed25519 library).

libxeddsa is a portable C implementation of the XEdDSA signature scheme
(Ed25519 public keys derived from Curve25519 private keys) built with CMake.
It requires libsodium for the underlying primitives (find_package(Sodium)).

OHOS adaptations (see patches/ and notes.md):
  - 0001-CMakeLists.txt: upstream always builds a shared library
    (xeddsa_dynamic) that links libsodium; with a *static* libsodium the
    linker hits a duplicate `randombytes` symbol (ref10/fastrandombytes vs
    libsodium's randombytes.o). The registry only publishes the static
    libsodium variant for OHOS, so a XEDDSA_BUILD_DYNAMIC option lets the
    dynamic targets be disabled while keeping the static library.
  - 0002-ref10-CMakeLists.txt: ref10/CMakeLists.txt gates the whole
    configuration on `UNIX`; CMake does not classify HarmonyOS as UNIX, so
    the configure step aborted with "Unsupported operating system". The
    patch accepts CMAKE_SYSTEM_NAME=HarmonyOS in the platform checks.

Official upstream: https://github.com/Syndace/libxeddsa (v2.0.1)
License: MIT
"""
import os

from conan import ConanFile
from conan.tools.cmake import CMake, CMakeToolchain, cmake_layout
from conan.tools.files import (
    apply_conandata_patches,
    copy,
    export_conandata_patches,
    get,
)


class LibxeddsaConan(ConanFile):
    name = "libxeddsa"
    version = "2.0.1"
    description = (
        "Portable C implementation of XEdDSA: Ed25519 signatures with "
        "Curve25519 key pairs (Syndace/libxeddsa)"
    )
    license = "MIT"
    homepage = "https://github.com/Syndace/libxeddsa"
    url = "https://github.com/Syndace/libxeddsa"

    package_type = "library"

    settings = "os", "compiler", "build_type", "arch"

    # OHOS 仅静态: 制品仓只发布静态 libsodium, xeddsa_dynamic 与
    # ref10/fastrandombytes 的 randombytes 符号冲突, 故本包只产出
    # 静态库 libxeddsa.a（见 patches/0001 与 notes.md）。不提供 shared
    # 选项, 避免声明无效选项误导消费者。
    options = {"shared": ["False"]}
    default_options = {"shared": False}

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        # Upstream find_package(Sodium REQUIRED); registry publishes the
        # static variant for OHOS (see patch 0001 for the duplicate-symbol
        # interaction with a shared xeddsa_dynamic target).
        self.requires("libsodium/1.0.22")

    def layout(self):
        cmake_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def generate(self):
        tc = CMakeToolchain(self)
        tc.variables["XEDDSA_BUILD_DYNAMIC"] = "OFF"  # static libsodium conflict (patch 0001)
        tc.variables["sodium_USE_STATIC_LIBS"] = "ON"
        # Upstream FindSodium.cmake locates libsodium via pkg-config /
        # find_path / find_library; the Conan-built dependency is not on the
        # default search path, so inject its include/lib paths explicitly.
        sodium = self.dependencies["libsodium"]
        sodium_inc = os.path.join(sodium.package_folder, "include")
        sodium_lib = os.path.join(sodium.package_folder, "lib", "libsodium.a")
        tc.variables["sodium_INCLUDE_DIR"] = sodium_inc
        tc.variables["sodium_LIBRARY_RELEASE"] = sodium_lib
        tc.variables["sodium_LIBRARY_DEBUG"] = sodium_lib
        tc.generate()

    def build(self):
        apply_conandata_patches(self)
        cmake = CMake(self)
        cmake.configure()
        cmake.build()

    def package(self):
        cmake = CMake(self)
        cmake.install()
        # Upstream installs only libxeddsa.a, no headers; copy the public
        # header (xeddsa.h includes cross_platform.h from ref10/include).
        copy(self, "xeddsa.h", src=os.path.join(self.source_folder, "include"),
             dst=os.path.join(self.package_folder, "include"))
        copy(self, "cross_platform.h",
             src=os.path.join(self.source_folder, "ref10", "include"),
             dst=os.path.join(self.package_folder, "include"))

    def package_info(self):
        self.cpp_info.libs = ["xeddsa"]
        self.cpp_info.set_property("cmake_file_name", "libxeddsa")
        self.cpp_info.set_property("cmake_target_name", "libxeddsa::libxeddsa")
        self.cpp_info.set_property("pkg_config_name", "libxeddsa")
        self.cpp_info.requires = ["libsodium::libsodium"]
