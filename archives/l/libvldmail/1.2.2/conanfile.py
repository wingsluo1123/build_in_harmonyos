#!/usr/bin/env python3
"""Conan 2 recipe for libvldmail 1.2.2 (CMake-based C library)."""

from conan import ConanFile
from conan.tools.cmake import CMake, CMakeToolchain, cmake_layout
from conan.tools.files import (
    apply_conandata_patches,
    export_conandata_patches,
    get,
)


class LibvldmailConan(ConanFile):
    name = "libvldmail"
    version = "1.2.2"
    description = "Your friendly e-mail address validation library"
    license = "MIT"
    homepage = "https://code.rosaelefanten.org/libvldmail/dir"
    url = "https://github.com/dertuxmalwieder/libvldmail"
    package_type = "static-library"

    settings = "os", "compiler", "build_type", "arch"

    def export_sources(self):
        export_conandata_patches(self)

    def layout(self):
        cmake_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def generate(self):
        toolchain = CMakeToolchain(self)
        # 上游默认关闭 LIBVLDMAIL_TESTS（测试编译为独立 vldmailtest 目标），
        # 库构建保持 OFF，测试见 test_package/ 与上游测试台账。
        toolchain.variables["LIBVLDMAIL_TESTS"] = False
        toolchain.generate()

    def build(self):
        apply_conandata_patches(self)
        cmake = CMake(self)
        cmake.configure()
        cmake.build()

    def package(self):
        CMake(self).install()

    def package_info(self):
        self.cpp_info.libs = ["vldmail"]
        self.cpp_info.set_property("cmake_file_name", "libvldmail")
        self.cpp_info.set_property("cmake_target_name", "libvldmail::libvldmail")
