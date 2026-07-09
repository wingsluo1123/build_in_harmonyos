#!/usr/bin/env python3
"""Conan recipe for sqlite3 3.49.1 — manual build (autosetup incompatible with HMDFS).

sqlite3 autoconf uses autosetup, whose bootstrap TCL interpreter (jimsh0)
cannot exec subprocesses on HarmonyOS HMDFS. This recipe builds manually
using clang, equivalent to Makefile.fallback.

sqlite3 is NOT a system same-name library (no /lib/libsqlite3.so), so
shared linking is acceptable (R26 does not apply).
"""
import os

from conan import ConanFile
from conan.tools.files import get, copy, apply_conandata_patches, export_conandata_patches
from conan.tools.layout import basic_layout


class Sqlite3Conan(ConanFile):
    name = "sqlite3"
    version = "3.49.1"
    description = "Self-contained, serverless, zero-configuration SQL database engine"
    license = "Public-Domain"
    homepage = "https://www.sqlite.org/"
    url = ""  # CI fills this

    settings = "os", "compiler", "build_type", "arch"

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        pass

    def layout(self):
        basic_layout(self)
        self.folders.build = "."

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def generate(self):
        # No Autotools/CMake — manual build.
        # R33: compiler must come from Conan conf, not shell env vars.
        pass

    def build(self):
        apply_conandata_patches(self)

        # R33: Get compiler from Conan conf
        compilers = self.conf.get("tools.build:compiler_executables", default={}, check_type=dict)
        cc = compilers.get("c", "clang") if compilers else "clang"
        ar = self.conf.get("tools.gnu:gcc:ar", default="llvm-ar", check_type=str)

        # Feature define (matching upstream autoconf defaults)
        defines = [
            "-DSQLITE_ENABLE_RTREE",
            "-DSQLITE_ENABLE_FTS5",
            "-DSQLITE_ENABLE_COLUMN_METADATA",
            "-DSQLITE_ENABLE_UNLOCK_NOTIFY",
            "-DSQLITE_SECURE_DELETE",
            "-DSQLITE_ENABLE_DBSTAT_VTAB",
            "-DSQLITE_THREADSAFE=1",
            "-DSQLITE_DEFAULT_MEMSTATUS=0",
        ]
        cflags = ["-fPIC", "-O2", "-I."] + defines
        libs = ["-lpthread", "-ldl"]

        # Build shared library
        self.run(f"{cc} {' '.join(cflags)} -shared -o libsqlite3.so sqlite3.c {' '.join(libs)}")

        # Build static library
        self.run(f"{cc} {' '.join(cflags)} -c sqlite3.c -o sqlite3.o")
        self.run("llvm-ar rcs libsqlite3.a sqlite3.o")

        # Build CLI binary
        self.run(f"{cc} {' '.join(cflags)} -o sqlite3 shell.c sqlite3.c {' '.join(libs)}")

    def package(self):
        # Install headers
        copy(self, "sqlite3.h", src=self.build_folder, dst=os.path.join(self.package_folder, "include"))
        copy(self, "sqlite3ext.h", src=self.build_folder, dst=os.path.join(self.package_folder, "include"))
        # Install libraries
        copy(self, "libsqlite3.so", src=self.build_folder, dst=os.path.join(self.package_folder, "lib"))
        copy(self, "libsqlite3.a", src=self.build_folder, dst=os.path.join(self.package_folder, "lib"))
        # Install CLI binary
        copy(self, "sqlite3", src=self.build_folder, dst=os.path.join(self.package_folder, "bin"))

    def package_info(self):
        self.cpp_info.libs = ["sqlite3"]
        self.cpp_info.set_property("cmake_file_name", "sqlite3")
        self.cpp_info.set_property("cmake_target_name", "sqlite3::sqlite3")
        self.cpp_info.set_property("pkg_config_name", "sqlite3")
