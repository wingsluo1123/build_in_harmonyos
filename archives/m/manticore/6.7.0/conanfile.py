#!/usr/bin/env python3
"""Conan recipe for Manticore Search — a fast, open-source full-text search engine.

Manticore Search is a C++ search database with real-time indexing and SQL support.
This recipe builds the search engine (searchd, indexer, indextool, etc.) and the
internal static library (lmanticore).

Dependencies managed by Conan: boost, openssl, zlib, curl, expat, libiconv
Dependencies built from source by manticore's build system: ICU, RE2, stemmer, columnar
"""
from conan import ConanFile
from conan.tools.files import get, apply_conandata_patches, export_conandata_patches
from conan.tools.cmake import CMake, CMakeToolchain, cmake_layout


class ManticoreConan(ConanFile):
    name = "manticore"
    version = "6.7.0"
    description = "Manticore Search — a fast, open-source full-text search engine with multi-core parallelism"
    license = "GPL-2.0-or-later"
    homepage = "https://manticoresearch.com/"
    url = ""  # CI fills this

    package_type = "application"

    settings = "os", "compiler", "build_type", "arch"
    options = {
        "shared": [True, False],
        "with_icu": [True, False],
        "with_re2": [True, False],
        "with_expat": [True, False],
    }
    default_options = {
        "shared": False,
        "with_icu": True,
        "with_re2": True,
        "with_expat": True,
    }

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        self.requires("boost/1.90.0@ohpcd/stable")
        self.requires("openssl/3.5.6.1")
        self.requires("zlib/1.3.1.1")
        self.requires("curl/8.15.0@ohpcd/stable")
        self.requires("expat/2.8.2@ohpcd/stable")
        self.requires("libiconv/1.17")

    def layout(self):
        cmake_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def generate(self):
        tc = CMakeToolchain(self)
        # Build type
        tc.variables["CMAKE_BUILD_TYPE"] = "Release"
        # Disable Galera (not supported on OHOS)
        tc.variables["WITH_GALERA"] = "OFF"
        # ICU: build from source (default WITH_ICU_FORCE_STATIC=1)
        # The build system downloads ICU 65.1 and builds it as ExternalProject
        if self.options.with_icu:
            tc.variables["WITH_ICU"] = "ON"
            tc.variables["WITH_ICU_FORCE_STATIC"] = "ON"
        else:
            tc.variables["WITH_ICU"] = "OFF"
        # RE2: build from source (default WITH_RE2_FORCE_STATIC=1)
        if self.options.with_re2:
            tc.variables["WITH_RE2"] = "ON"
            tc.variables["WITH_RE2_FORCE_STATIC"] = "ON"
        else:
            tc.variables["WITH_RE2"] = "OFF"
        # Expat and Iconv
        if self.options.with_expat:
            tc.variables["WITH_EXPAT"] = "ON"
        else:
            tc.variables["WITH_EXPAT"] = "OFF"
        # SSL
        tc.variables["WITH_SSL"] = "ON"
        # CURL
        tc.variables["WITH_CURL"] = "ON"
        # ZSTD - disabled (not available in Conan remote)
        tc.variables["WITH_ZSTD"] = "OFF"
        # ODBC, MySQL, PostgreSQL - disabled
        tc.variables["WITH_ODBC"] = "OFF"
        tc.variables["WITH_MYSQL"] = "OFF"
        tc.variables["WITH_POSTGRESQL"] = "OFF"
        # Static binary
        tc.variables["STATIC_BINARY"] = "OFF"
        # Enable testing
        tc.variables["BUILD_TESTING"] = "ON"
        # R26: System-name libraries default to static
        tc.variables["BUILD_SHARED_LIBS"] = "ON" if self.options.shared else "OFF"
        tc.generate()

    def build(self):
        apply_conandata_patches(self)
        cmake = CMake(self)
        cmake.configure()
        cmake.build()
        # Run upstream tests (CI L1 gate check)
        cmake.test()

    def package(self):
        cmake = CMake(self)
        cmake.install()

    def package_info(self):
        self.cpp_info.libs = ["manticore"]
        self.cpp_info.bindirs = ["bin"]
