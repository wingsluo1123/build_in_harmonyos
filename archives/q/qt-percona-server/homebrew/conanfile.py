from conan import ConanFile
from conan.tools.cmake import CMake, CMakeToolchain, cmake_layout
from conan.tools.files import get, apply_conandata_patches, export_conandata_patches, copy
import os


class QtPerconaServerConan(ConanFile):
    name = "qt-percona-server"
    version = "homebrew"
    description = "Qt6 SQL driver plugin for Percona Server (QMYSQLDriver)"
    license = "LGPL-3.0-only"
    homepage = "https://www.qt.io/"
    url = ""

    package_type = "shared-library"

    settings = "os", "compiler", "build_type", "arch"

    exports_sources = "conandata.yml"

    def requirements(self):
        self.requires("qtbase/6.11.1")
        self.requires("percona-server/8.0.36")

    def layout(self):
        cmake_layout(self, src_folder="src")

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def generate(self):
        tc = CMakeToolchain(self)
        # Only build mysql driver, disable all other SQL drivers
        tc.variables["FEATURE_sql_ibase"] = "OFF"
        tc.variables["FEATURE_sql_mysql"] = "ON"
        tc.variables["FEATURE_sql_oci"] = "OFF"
        tc.variables["FEATURE_sql_odbc"] = "OFF"
        tc.variables["FEATURE_sql_psql"] = "OFF"
        tc.variables["FEATURE_sql_sqlite"] = "OFF"
        # Point to percona-server client library
        tc.variables["MySQL_LIBRARY"] = "libperconaserverclient"
        tc.generate()

    def build(self):
        apply_conandata_patches(self)
        cmake = CMake(self)
        # Build from src/plugins/sqldrivers subdirectory
        cmake.configure(build_script_folder=os.path.join(self.source_folder, "src", "plugins", "sqldrivers"))
        cmake.build()

    def package(self):
        cmake = CMake(self)
        cmake.install()

    def package_info(self):
        self.cpp_info.libs = []
        self.cpp_info.bindirs = []
        # Plugin is loaded via dlopen by Qt at runtime
        self.cpp_info.includedirs = []
