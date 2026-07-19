"""Conan recipe for percona-server 8.0.36 - Percona Server for MySQL client library.

Builds only the client library (libperconaserverclient), not the full database server.
Used by qt-percona-server as the MySQL protocol backend.

Build system: CMake
Produces: libperconaserverclient.so (and .a)

Dependencies: boost (header-only), openssl, zlib
"""
import os

from conan import ConanFile
from conan.tools.cmake import CMake, CMakeToolchain, cmake_layout
from conan.tools.files import get, apply_conandata_patches, copy


class PerconaServerConan(ConanFile):
    name = "percona-server"
    version = "8.0.36"
    description = "Percona Server for MySQL client library (libperconaserverclient)"
    license = "GPL-2.0-only"
    homepage = "https://www.percona.com/"
    url = ""  # CI fills this

    package_type = "library"
    options = {"shared": [True, False]}
    default_options = {"shared": True}

    settings = "os", "arch", "compiler", "build_type"

    exports_sources = "conandata.yml"

    def requirements(self):
        self.requires("openssl/1.1.1w")
        self.requires("zlib/1.3.1")
        self.requires("boost/1.90.0")

    def layout(self):
        cmake_layout(self, src_folder="src")

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def generate(self):
        tc = CMakeToolchain(self)
        # Build client library only, not the full server
        tc.variables["WITHOUT_SERVER"] = "ON"
        # Use Conan-provided OpenSSL and zlib, set explicit paths
        tc.variables["WITH_SSL"] = "system"
        tc.variables["OPENSSL_ROOT_DIR"] = self.dependencies["openssl"].package_folder
        tc.variables["WITH_ZLIB"] = "system"
        tc.variables["ZLIB_ROOT"] = self.dependencies["zlib"].package_folder
        # Use Conan boost package instead of CMake DOWNLOAD_BOOST (more reliable)
        tc.variables["WITH_BOOST"] = self.dependencies["boost"].package_folder
        # ARM64 specific: use -fPIC for shared library compatibility
        tc.variables["CMAKE_POSITION_INDEPENDENT_CODE"] = "ON"
        tc.generate()

    def build(self):
        apply_conandata_patches(self)
        cmake = CMake(self)
        cmake.configure()
        # Build only the mysqlclient target (client library), not the whole server
        cmake.build(target="mysqlclient")

    def package(self):
        # Install source headers (top-level include/)
        copy(self, "*.h", dst=os.path.join(self.package_folder, "include"),
             src=os.path.join(self.source_folder, "include"))
        # Install build-generated headers (my_config.h, mysql_version.h etc.)
        copy(self, "*.h", dst=os.path.join(self.package_folder, "include"),
             src=os.path.join(self.build_folder, "include"))
        # Install client library (MySQL builds into libmysql/ subdirectory)
        copy(self, "*perconaserverclient*", dst=os.path.join(self.package_folder, "lib"),
             src=self.build_folder, keep_path=False)
        copy(self, "*mysqlclient*", dst=os.path.join(self.package_folder, "lib"),
             src=self.build_folder, keep_path=False)
        # Clean up unwanted files
        for pattern in ["*.la", "*.dylib"]:
            copy(self, pattern, dst=os.path.join(self.package_folder, "lib"),
                 src=os.path.join(self.package_folder, "lib"), keep_path=False, delete=True)

    def package_info(self):
        self.cpp_info.libs = ["perconaserverclient"]
        self.cpp_info.includedirs = ["include"]
        # Propagate dependencies to consumers (e.g. qt-percona-server)
        self.cpp_info.requires = ["openssl::openssl", "zlib::zlib"]