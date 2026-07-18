#!/usr/bin/env python3
"""Conan recipe for Qt HTTP Server 6.11.1 on HarmonyOS PC."""

from conan import ConanFile
from conan.tools.cmake import CMake, CMakeToolchain, cmake_layout
from conan.tools.files import get


class QtHttpServerConan(ConanFile):
    name = "qthttpserver"
    version = "6.11.1"
    description = "Qt framework for embedding an HTTP server"
    license = "GPL-3.0-only AND BSD-3-Clause"
    homepage = "https://www.qt.io/"
    package_type = "library"
    settings = "os", "compiler", "build_type", "arch"
    options = {"shared": [True, False]}
    default_options = {"shared": True}

    def requirements(self):
        self.requires("qtbase/6.11.1")

    def layout(self):
        cmake_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def generate(self):
        tc = CMakeToolchain(self)
        # Qt modules use qtbase's native Qt6Config.cmake and BuildInternals
        # files.  Point CMake at the dependency package instead of generating
        # an incomplete replacement config with CMakeDeps.
        qtbase_prefix = self.dependencies["qtbase"].package_folder
        tc.cache_variables["CMAKE_PREFIX_PATH"] = qtbase_prefix
        tc.variables.update(
            {
                "QT_BUILD_TESTS": False,
                "QT_BUILD_EXAMPLES": False,
                "QT_BUILD_BENCHMARKS": False,
                "QT_BUILD_DOCS": False,
                "BUILD_SHARED_LIBS": bool(self.options.shared),
                "QT_QMAKE_TARGET_MKSPEC": "harmonyos-clang",
            }
        )
        tc.generate()

    def build(self):
        cmake = CMake(self)
        cmake.configure()
        cmake.build()

    def package(self):
        cmake = CMake(self)
        cmake.install()

    def package_info(self):
        self.cpp_info.libs = ["Qt6HttpServer"]
        # The package installs Qt's own Qt6HttpServerConfig.cmake.  Consumers
        # should use that native config together with qtbase's Qt6Config.cmake.
        self.cpp_info.set_property("cmake_find_mode", "none")
        self.cpp_info.set_property("cmake_target_name", "Qt6::HttpServer")
