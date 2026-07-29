#!/usr/bin/env python3
"""Conan recipe for PROJ 9.3.1.

PROJ is a CMake-based geospatial projection library. Its build needs a native
sqlite3 executable to generate proj.db and a target sqlite3 library for libproj,
so the recipe wires sqlite3 as both a host dependency and a build tool.
"""
import os

from conan import ConanFile
from conan.errors import ConanException
from conan.tools.cmake import CMake, CMakeDeps, CMakeToolchain, cmake_layout
from conan.tools.files import apply_conandata_patches, export_conandata_patches, get


class ProjConan(ConanFile):
    name = "proj"
    version = "9.3.1"
    description = "Cartographic projections and coordinate transformation library"
    license = "MIT"
    homepage = "https://proj.org/"
    url = "https://github.com/OSGeo/PROJ"
    package_type = "library"

    settings = "os", "arch", "compiler", "build_type"
    options = {"shared": [True, False], "fPIC": [True, False]}
    default_options = {"shared": False, "fPIC": True}

    def export_sources(self):
        export_conandata_patches(self)

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
        cmake_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def generate(self):
        deps = CMakeDeps(self)
        deps.generate()

        sqlite_host = self.dependencies.host["sqlite3"].package_folder
        sqlite_build = self.dependencies.build["sqlite3"].package_folder
        sqlite_exe = self._sqlite3_executable(sqlite_build)
        sqlite_lib = self._sqlite3_library(sqlite_host)

        tc = CMakeToolchain(self)
        if self.settings.os == "OHOS":
            tc.cache_variables["CMAKE_SYSTEM_NAME"] = "Linux"
            tc.cache_variables["CMAKE_SYSTEM_PROCESSOR"] = "aarch64"
        tc.variables["BUILD_SHARED_LIBS"] = "ON" if self.options.shared else "OFF"
        tc.variables["BUILD_TESTING"] = "OFF"
        tc.variables["BUILD_EXAMPLES"] = "OFF"
        tc.variables["BUILD_APPS"] = "ON"
        tc.variables["BUILD_PROJSYNC"] = "OFF"
        tc.variables["ENABLE_TIFF"] = "OFF"
        tc.variables["ENABLE_CURL"] = "OFF"
        tc.variables["NLOHMANN_JSON_ORIGIN"] = "internal"
        tc.variables["CMAKE_POLICY_VERSION_MINIMUM"] = "3.5"
        tc.variables["CMAKE_INSTALL_LIBDIR"] = "lib"
        tc.variables["EXE_SQLITE3"] = sqlite_exe
        tc.variables["SQLite3_INCLUDE_DIR"] = os.path.join(sqlite_host, "include")
        tc.variables["SQLite3_LIBRARY"] = sqlite_lib
        tc.variables["SQLITE3_INCLUDE_DIR"] = os.path.join(sqlite_host, "include")
        tc.variables["SQLITE3_LIBRARY"] = sqlite_lib
        tc.generate()

    def build(self):
        apply_conandata_patches(self)
        cmake = CMake(self)
        cmake.configure()
        cmake.build(cli_args=["--parallel", "1"])

    def package(self):
        cmake = CMake(self)
        cmake.install()

    def package_info(self):
        self.cpp_info.libs = ["proj"]
        self.cpp_info.requires = ["sqlite3::sqlite3"]
        self.cpp_info.set_property("cmake_file_name", "PROJ")
        self.cpp_info.set_property("cmake_target_name", "PROJ::proj")
        self.cpp_info.set_property("pkg_config_name", "proj")
        if self.settings.os in ("Linux", "OHOS"):
            self.cpp_info.system_libs = ["m", "dl", "pthread"]

    @staticmethod
    def _sqlite3_executable(package_folder):
        bin_dir = os.path.join(package_folder, "bin")
        candidates = [
            os.path.join(bin_dir, "sqlite3"),
            os.path.join(bin_dir, "sqlite3.exe"),
        ]
        for candidate in candidates:
            if os.path.exists(candidate):
                return candidate
        checked = ", ".join(candidates)
        raise ConanException(f"sqlite3 executable not found; checked: {checked}")

    @staticmethod
    def _sqlite3_library(package_folder):
        lib_dir = os.path.join(package_folder, "lib")
        candidates = [
            os.path.join(lib_dir, "libsqlite3.a"),
            os.path.join(lib_dir, "sqlite3.lib"),
        ]
        for candidate in candidates:
            if os.path.exists(candidate):
                return candidate
        checked = ", ".join(candidates)
        raise ConanException(f"static sqlite3 library not found; checked: {checked}")
