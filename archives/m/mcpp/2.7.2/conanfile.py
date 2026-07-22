#!/usr/bin/env python3
"""Conan recipe — mcpp 2.7.2 (Autotools project).

MCPP is a C/C++ preprocessor implementing C90, C99 and C++98.
Source: https://sourceforge.net/projects/mcpp/
"""
from conan import ConanFile
from conan.tools.files import get, apply_conandata_patches, export_conandata_patches
from conan.tools.gnu import Autotools, AutotoolsToolchain
from conan.tools.layout import basic_layout


class McppConan(ConanFile):
    name = "mcpp"
    version = "2.7.2"
    description = "MCPP is a C/C++ preprocessor with the highest conformance"
    license = "BSD-2-Clause"
    homepage = "https://mcpp.sourceforge.net/"
    url = ""  # CI fills this

    package_type = "application"

    settings = "os", "compiler", "build_type", "arch"
    options = {"shared": [True, False], "enable_mcpp_lib": [True, False]}
    default_options = {"shared": False, "enable_mcpp_lib": False}

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        # mcpp has no external dependencies
        pass

    def layout(self):
        basic_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def generate(self):
        tc = AutotoolsToolchain(self)
        # R32: support both Linux and OHOS
        if self.options.enable_mcpp_lib:
            tc.configure_args.append("--enable-mcpp-lib")
        # R26: static build for system-name libraries
        if not self.options.shared:
            tc.configure_args.append("--enable-static")
            tc.configure_args.append("--disable-shared")
        tc.generate()

    def build(self):
        apply_conandata_patches(self)
        autotools = Autotools(self)
        autotools.configure()
        autotools.make(args=["-j1"])

    def package(self):
        autotools = Autotools(self)
        autotools.install()

    def package_info(self):
        self.cpp_info.bindirs = ["bin"]
        # mcpp 默认构建为 standalone 二进制；仅当 --enable-mcpp-lib 时构建 libmcpp
        if self.options.enable_mcpp_lib:
            self.cpp_info.libs = ["mcpp"]
            self.cpp_info.libdirs = ["lib"]
            self.cpp_info.includedirs = ["include"]
            self.cpp_info.set_property("cmake_find_mode", "both")
            self.cpp_info.set_property("pkg_config_name", "mcpp")