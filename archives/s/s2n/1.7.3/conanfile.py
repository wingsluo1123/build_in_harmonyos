#!/usr/bin/env python3
"""Conan recipe for s2n 1.7.3.

s2n-tls is a C99 implementation of the TLS protocol from AWS.
Build system: CMake, depends on OpenSSL libcrypto.
"""

from conan import ConanFile
from conan.tools.files import get, apply_conandata_patches, export_conandata_patches
from conan.tools.cmake import CMake, CMakeToolchain, cmake_layout


class S2nConan(ConanFile):
    name = "s2n"
    version = "1.7.3"
    description = "AWS s2n TLS library - a C99 implementation of the TLS protocol"
    license = "Apache-2.0"
    homepage = "https://github.com/aws/s2n-tls"
    url = "https://github.com/aws/s2n-tls"

    package_type = "library"
    settings = "os", "compiler", "build_type", "arch"
    options = {"shared": [True, False]}
    default_options = {"shared": False}

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        self.requires("openssl/3.5.6.1")

    def layout(self):
        cmake_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def generate(self):
        tc = CMakeToolchain(self)
        tc.variables["BUILD_SHARED_LIBS"] = "ON" if self.options.shared else "OFF"
        tc.variables["BUILD_TESTING"] = "OFF"
        tc.variables["S2N_INTERN_LIBCRYPTO"] = "OFF"
        tc.generate()

    def build(self):
        apply_conandata_patches(self)
        cmake = CMake(self)
        prefix_paths = [d.package_folder for d in self.dependencies.values() if hasattr(d, 'package_folder') and d.package_folder]
        vars_dict = {"CMAKE_PREFIX_PATH": ";".join(prefix_paths)} if prefix_paths else {}
        cmake.configure(variables=vars_dict)
        cmake.build()

    def package(self):
        cmake = CMake(self)
        cmake.install()
        # s2n installs cmake config to lib/s2n/cmake/ (non-standard)
        # Move to lib/cmake/s2n/ so find_package(s2n) works via CMAKE_PREFIX_PATH
        import os, shutil
        src = os.path.join(self.package_folder, "lib", "s2n", "cmake")
        dst = os.path.join(self.package_folder, "lib", "cmake", "s2n")
        if os.path.isdir(src):
            os.makedirs(os.path.dirname(dst), exist_ok=True)
            shutil.copytree(src, dst, dirs_exist_ok=True)
            shutil.rmtree(src)

    def package_info(self):
        self.cpp_info.libs = ["s2n"]
        self.cpp_info.system_libs = ["pthread"]
