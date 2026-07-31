#!/usr/bin/env python3
"""Conan recipe for the H2O HTTP server 2.2.6 on OpenHarmony."""

from conan import ConanFile
from conan.tools.build import can_run
from conan.tools.cmake import CMake, CMakeDeps, CMakeToolchain, cmake_layout
from conan.tools.files import get
from conan.tools.gnu import PkgConfigDeps


class H2OConan(ConanFile):
    name = "h2o"
    version = "2.2.6"
    description = "Optimized HTTP server with HTTP/2 support"
    license = "MIT"
    homepage = "https://github.com/h2o/h2o"
    url = "https://github.com/h2o/h2o"
    package_type = "application"

    settings = "os", "compiler", "build_type", "arch"
    options = {"shared": [True, False]}
    default_options = {"shared": False}

    def requirements(self):
        self.requires("libuv/1.52.1")
        self.requires("openssl/3.5.6")
        self.requires("zlib/1.3.1")

    def build_requirements(self):
        # The upstream `check` target invokes Perl's prove runner.
        self.tool_requires("perl/5.42.2")

    def layout(self):
        cmake_layout(self, src_folder=".")

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def generate(self):
        CMakeDeps(self).generate()
        PkgConfigDeps(self).generate()
        toolchain = CMakeToolchain(self)
        toolchain.variables["BUILD_SHARED_LIBS"] = self.options.shared
        toolchain.variables["WITH_BUNDLED_SSL"] = False
        toolchain.variables["WITH_MRUBY"] = False
        toolchain.variables["WITH_PICOTLS"] = True
        toolchain.generate()

    def build(self):
        cmake = CMake(self)
        cmake.configure()
        cmake.build()
        # H2O's upstream test entry is the custom CMake `check` target.
        if can_run(self):
            cmake.build(target="check")

    def package(self):
        CMake(self).install()

    def package_info(self):
        self.cpp_info.bindirs = ["bin"]
        self.cpp_info.libs = ["h2o", "h2o-evloop"]
        self.cpp_info.includedirs = ["include"]
        self.cpp_info.set_property("pkg_config_name", "libh2o")
