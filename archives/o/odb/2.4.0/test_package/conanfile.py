#!/usr/bin/env python3
"""Consumer test for the odb 2.4.0 package.

The package ships the ODB compiler (bin/odb) plus the core runtime
(libodb) and the SQLite backend (libodb-sqlite). The consumer test
opens an in-memory SQLite database through odb::sqlite::database, runs
CREATE TABLE / INSERT through odb::database::execute() inside an
odb::transaction, reads the row back through the sqlite3 handle of the
transaction's odb::sqlite::connection and asserts the roundtrip value,
covering the full runtime chain libodb-sqlite -> libodb -> sqlite3.

The test binary is built for and runs on the build target itself: on
the CI worker that is the OHOS device (native aarch64); on a WSL host
the aarch64 binary runs under qemu user emulation (binfmt). The test
must not be skipped on the cross target: the CI worker executes it
natively, and skipping it makes the L1e negative test (R34) report a
fake test.
"""
import os

from conan import ConanFile
from conan.tools.cmake import CMake, CMakeDeps, CMakeToolchain
from conan.tools.layout import basic_layout


class OdbTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"
    test_type = "explicit"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def configure(self):
        # ODB 2.4.0 headers use C++11-era constructs removed in C++17.
        self.settings.compiler.cppstd = "14"

    def layout(self):
        basic_layout(self)

    def generate(self):
        # The downloaded registry dependencies (sqlite3/3.49.1,
        # libcutl/1.11.0) do not propagate include directories through
        # CMakeDeps (empty INTERFACE_INCLUDE_DIRECTORIES in the
        # generated targets), while <odb/sqlite/database.hxx> includes
        # <sqlite3.h> unconditionally. Pass the sqlite3 package's
        # include dir to CMake explicitly — the same package_folder
        # pattern the odb recipe itself uses for its dependencies.
        sqlite3 = self.dependencies["sqlite3"]
        tc = CMakeToolchain(self)
        tc.variables["SQLITE3_INCLUDE_DIR"] = os.path.join(
            sqlite3.package_folder, "include")
        tc.generate()
        CMakeDeps(self).generate()

    def build(self):
        cmake = CMake(self)
        cmake.configure()
        cmake.build()

    def test(self):
        self.run(os.path.join(self.cpp.build.bindir, "test_odb"), env="conanrun")
