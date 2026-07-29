#!/usr/bin/env python3
"""Conan recipe for PROJ 9.3.1."""

import os

from conan import ConanFile
from conan.tools.cmake import CMake, CMakeDeps, CMakeToolchain, cmake_layout
from conan.tools.env import VirtualBuildEnv
from conan.tools.files import collect_libs, copy, get, replace_in_file


class ProjConan(ConanFile):
    name = "proj"
    version = "9.3.1"
    description = "Cartographic projections and coordinate transformations"
    license = "MIT"
    homepage = "https://proj.org/"
    url = "https://github.com/OSGeo/PROJ"
    package_type = "library"
    settings = "os", "compiler", "build_type", "arch"
    options = {"shared": [True, False], "fPIC": [True, False]}
    default_options = {"shared": False, "fPIC": True}

    def config_options(self):
        if self.settings.os == "Windows":
            self.options.rm_safe("fPIC")

    def configure(self):
        if self.options.shared:
            self.options.rm_safe("fPIC")

    def requirements(self):
        self.requires("sqlite3/3.49.1")

    def build_requirements(self):
        self.tool_requires("sqlite3/3.49.1")

    def layout(self):
        cmake_layout(self, src_folder="src")

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def generate(self):
        VirtualBuildEnv(self).generate()
        CMakeDeps(self).generate()
        toolchain = CMakeToolchain(self)
        toolchain.variables["BUILD_SHARED_LIBS"] = bool(self.options.shared)
        toolchain.variables["BUILD_TESTING"] = False
        toolchain.variables["BUILD_CCT"] = False
        toolchain.variables["BUILD_CS2CS"] = False
        toolchain.variables["BUILD_GEOD"] = False
        toolchain.variables["BUILD_GIE"] = False
        toolchain.variables["BUILD_PROJ"] = False
        toolchain.variables["BUILD_PROJINFO"] = False
        toolchain.variables["BUILD_PROJSYNC"] = False
        toolchain.variables["ENABLE_TIFF"] = False
        toolchain.variables["ENABLE_CURL"] = False
        toolchain.variables["ENABLE_IPO"] = False
        toolchain.variables["NLOHMANN_JSON_ORIGIN"] = "internal"
        toolchain.variables["CMAKE_POLICY_VERSION_MINIMUM"] = "3.5"
        toolchain.generate()

    def build(self):
        cmakelists = os.path.join(self.source_folder, "CMakeLists.txt")
        replace_in_file(
            self,
            cmakelists,
            "find_package(Sqlite3 REQUIRED)",
            "find_package(sqlite3 CONFIG REQUIRED)",
        )
        replace_in_file(self, cmakelists, "SQLITE3_FOUND", "sqlite3_FOUND")
        replace_in_file(self, cmakelists, "SQLITE3_VERSION", "sqlite3_VERSION")
        replace_in_file(
            self,
            os.path.join(self.source_folder, "src", "lib_proj.cmake"),
            "target_include_directories(proj PRIVATE ${SQLITE3_INCLUDE_DIR})\n"
            "target_link_libraries(proj PRIVATE ${SQLITE3_LIBRARY})",
            "target_link_libraries(proj PRIVATE sqlite3::sqlite3)",
        )
        cmake = CMake(self)
        cmake.configure()
        cmake.build()

    def package(self):
        copy(
            self,
            "COPYING",
            src=self.source_folder,
            dst=os.path.join(self.package_folder, "licenses"),
        )
        CMake(self).install()

    def package_info(self):
        self.cpp_info.libs = collect_libs(self)
        self.cpp_info.requires = ["sqlite3::sqlite3"]
        self.cpp_info.set_property("cmake_file_name", "PROJ")
        self.cpp_info.set_property("cmake_target_name", "PROJ::proj")
        self.cpp_info.set_property("pkg_config_name", "proj")
        if self.settings.os in ("Linux", "OHOS"):
            self.cpp_info.system_libs = ["m", "pthread"]
        self.runenv_info.prepend_path(
            "PROJ_DATA", os.path.join(self.package_folder, "share", "proj")
        )
