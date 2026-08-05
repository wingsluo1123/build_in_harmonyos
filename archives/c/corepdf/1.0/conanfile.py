#!/usr/bin/env python3
"""Conan recipe — corepdf 1.0 (cmake, Qt6 + poppler-qt6)"""
import os
from conan import ConanFile
from conan.tools.files import get, apply_conandata_patches, export_conandata_patches
from conan.tools.cmake import CMake, CMakeToolchain, CMakeDeps, cmake_layout


# CMakeLists.txt content (replaces qmake build system for conan-managed deps)
_CMAKELISTS_TXT = """cmake_minimum_required(VERSION 3.16)
project(corepdf VERSION 1.0 LANGUAGES CXX)

set(CMAKE_CXX_STANDARD 17)
set(CMAKE_CXX_STANDARD_REQUIRED ON)
set(CMAKE_AUTOMOC ON)

find_package(Qt6 REQUIRED COMPONENTS Widgets)
find_package(poppler REQUIRED)

add_library(qpdf STATIC
    qpdflib/qpdfwidget.cpp
    qpdflib/qpdfwidget.h
)
target_include_directories(qpdf PUBLIC
    ${CMAKE_CURRENT_SOURCE_DIR}/qpdflib
)
target_link_libraries(qpdf PUBLIC
    Qt6::Widgets
    poppler::poppler
)
target_compile_definitions(qpdf PRIVATE QPDFLIB_BUILD)

add_executable(corepdf
    corepdf/corepdf.cpp
    corepdf/corepdf.h
    corepdf/main.cpp
)
target_include_directories(corepdf PRIVATE
    ${CMAKE_CURRENT_SOURCE_DIR}/corepdf
    ${CMAKE_CURRENT_SOURCE_DIR}/qpdflib
)
target_link_libraries(corepdf PRIVATE
    qpdf
    Qt6::Widgets
    poppler::poppler
)

install(TARGETS corepdf DESTINATION bin)
"""


class CorepdfConan(ConanFile):
    name = "corepdf"
    version = "1.0"
    description = "A PDF viewer built with Qt6 and poppler-qt6"
    license = "MIT"
    homepage = "https://github.com/rahmanshaber/corepdf"
    url = "https://gitcode.com/OpenHarmonyPCDeveloper/build_in_harmonyos"

    package_type = "application"

    settings = "os", "compiler", "build_type", "arch"

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        self.requires("qtbase/6.11.1")
        self.requires("poppler/25.12.0.3")

    def layout(self):
        cmake_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def generate(self):
        tc = CMakeToolchain(self)
        tc.variables["CMAKE_AUTOMOC"] = "ON"
        tc.generate()
        CMakeDeps(self).generate()
        # Bridge qtbase find_package to Qt6 cmake configs
        qtbase_path = self.dependencies["qtbase"].package_folder
        redirect = os.path.join(self.generators_folder, "qtbase-config.cmake")
        with open(redirect, "w") as f:
            f.write("set(qtbase_FOUND TRUE)\n")
            f.write('list(PREPEND CMAKE_PREFIX_PATH "{}")\n'.format(qtbase_path))
            f.write("find_package(Qt6 REQUIRED COMPONENTS Core Gui Widgets)\n")
            f.write("if(NOT TARGET qtbase::qtbase)\n")
            f.write("  add_library(qtbase::qtbase INTERFACE IMPORTED)\n")
            f.write('  set_target_properties(qtbase::qtbase PROPERTIES\n')
            f.write('    INTERFACE_LINK_LIBRARIES "Qt6::Core;Qt6::Gui;Qt6::Widgets"\n')
            f.write("  )\n")
            f.write("endif()\n")
        ver = os.path.join(self.generators_folder, "qtbaseConfigVersion.cmake")
        with open(ver, "w") as f:
            f.write('set(PACKAGE_VERSION "6.11.1")\n')
            f.write("set(PACKAGE_VERSION_EXACT TRUE)\n")
            f.write("set(PACKAGE_VERSION_COMPATIBLE TRUE)\n")

    def build(self):
        apply_conandata_patches(self)
        # Write CMakeLists.txt (conan-managed build, replaces qmake)
        with open(os.path.join(self.source_folder, "CMakeLists.txt"), "w") as f:
            f.write(_CMAKELISTS_TXT)
        cmake = CMake(self)
        qtbase_path = self.dependencies["qtbase"].package_folder
        gen_folder = self.generators_folder
        cmake.configure(variables={"CMAKE_PREFIX_PATH": qtbase_path + ";" + gen_folder})
        cmake.build()

    def package(self):
        cmake = CMake(self)
        cmake.install()

    def package_info(self):
        self.cpp_info.bindirs = ["bin"]
