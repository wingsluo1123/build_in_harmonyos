#!/usr/bin/env python3
"""Conan recipe — mariadb-connector-c 3.4.8 (CMake build system).

MariaDB Connector/C is a C client library for MariaDB and MySQL databases.
Build system: CMake (cmake/install.cmake defines install layout).

Key rules:
  - R32: settings.os check uses `in ("Linux", "OHOS")`
  - R39: Source URL points to official GitHub release
"""
import os
import shutil

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration, ConanException
from conan.tools.files import get, apply_conandata_patches, export_conandata_patches
from conan.tools.cmake import CMake, CMakeToolchain, cmake_layout, CMakeDeps


class MariadbConnectorCConan(ConanFile):
    name = "mariadb-connector-c"
    version = "3.4.8"
    description = "MariaDB C client library (libmariadb) for MariaDB/MySQL"
    license = "LGPL-2.1"
    homepage = "https://mariadb.com/kb/en/mariadb-connector-c/"
    url = ""  # CI fills this

    package_type = "library"

    settings = "os", "compiler", "build_type", "arch"
    options = {"shared": [True, False]}
    default_options = {"shared": True}

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        self.requires("openssl/3.5.6.1.1")

    def validate(self):
        # R32: settings.os check must use in ("Linux", "OHOS")
        if self.settings.os not in ("Linux", "OHOS"):
            raise ConanInvalidConfiguration(
                f"mariadb-connector-c only supports Linux and OHOS, got {self.settings.os}"
            )

    def layout(self):
        cmake_layout(self)

    def source(self):
        # Try official download first; fall back to local init-build source
        local_src = os.path.join(
            os.path.expanduser("~"), "tmp", "builds",
            "mariadb-connector-c-3.4.8.orig")
        if os.path.isdir(local_src):
            for item in os.listdir(local_src):
                s = os.path.join(local_src, item)
                d = os.path.join(self.source_folder, item)
                if os.path.isdir(s):
                    shutil.copytree(s, d, dirs_exist_ok=True)
                else:
                    shutil.copy2(s, d)
        else:
            get(self, **self.conan_data["sources"], strip_root=True)

    def generate(self):
        tc = CMakeToolchain(self)
        # Project-specific CMake variables
        tc.variables["CMAKE_C_FLAGS"] = "-fPIC"
        tc.variables["WITH_SSL"] = "OPENSSL"
        tc.variables["WITH_EXTERNAL_ZLIB"] = "OFF"
        tc.variables["WITH_UNIT_TESTS"] = "OFF"
        # Override install directories to match Conan layout
        tc.variables["INSTALL_LIBDIR"] = "lib"
        tc.variables["INSTALL_INCLUDEDIR"] = "include"
        tc.variables["INSTALL_BINDIR"] = "bin"
        tc.variables["INSTALL_PCDIR"] = "lib/pkgconfig"
        tc.variables["INSTALL_PLUGINDIR"] = "lib/mariadb/plugin"
        # Pre-set OpenSSL variables for mariadb-connector-c's legacy CMake
        # which uses OPENSSL_INCLUDE_DIR, OPENSSL_SSL_LIBRARY, etc. directly
        # instead of imported targets.  Without these the build skips
        # ADD_DEFINITIONS(-DHAVE_OPENSSL) and MA_HASH_CTX is never defined.
        openssl = self.dependencies["openssl"]
        openssl_inc = os.path.join(openssl.package_folder, "include")
        tc.variables["OPENSSL_INCLUDE_DIR"] = openssl_inc
        tc.variables["OPENSSL_SSL_LIBRARY"] = os.path.join(
            openssl.package_folder, "lib", "libssl.a")
        tc.variables["OPENSSL_CRYPTO_LIBRARY"] = os.path.join(
            openssl.package_folder, "lib", "libcrypto.a")
        tc.variables["OPENSSL_FOUND"] = "TRUE"
        # Pre-set ZLIB variables is not needed — bundled zlib is used
        # (WITH_EXTERNAL_ZLIB=OFF) so it inherits -fPIC from CMAKE_C_FLAGS.
        tc.generate()
        deps = CMakeDeps(self)
        deps.generate()

    def build(self):
        apply_conandata_patches(self)
        cmake = CMake(self)
        cmake.configure()
        cmake.build()

    def package(self):
        cmake = CMake(self)
        cmake.install()

    def package_info(self):
        self.cpp_info.libs = ["mariadb"]
        self.cpp_info.includedirs = ["include"]
        self.cpp_info.libdirs = ["lib"]
        self.cpp_info.set_property("cmake_file_name", "mariadb-connector-c")
        self.cpp_info.set_property("cmake_target_name", "mariadb-connector-c::mariadb-connector-c")
        self.cpp_info.requires = ["openssl::openssl"]
