#!/usr/bin/env python3
"""Conan recipe — graphqlite (Makefile-based SQLite extension).

Builds the GraphQLite SQLite extension (.so) using vendored SQLite headers.
The extension is a loadable .so that resolves SQLite symbols at runtime.
"""
import os

from conan import ConanFile
from conan.tools.files import get, copy, apply_conandata_patches, export_conandata_patches
from conan.tools.layout import basic_layout


class GraphqliteConan(ConanFile):
    name = "graphqlite"
    version = "0.6.0"
    description = "A SQLite extension that adds graph database capabilities with Cypher query language"
    license = "MIT"
    homepage = "https://github.com/colliery-io/graphqlite"
    url = ""  # CI fills this

    package_type = "library"

    settings = "os", "compiler", "build_type", "arch"
    options = {"shared": [True, False]}
    default_options = {"shared": False}

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        pass

    def layout(self):
        basic_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def build(self):
        apply_conandata_patches(self)

        # R33: Get compiler from Conan conf, never from shell env vars
        # tools.build:compiler_executables is a JSON dict in the profile
        cc = "clang"
        ar = "llvm-ar"
        ranlib = "llvm-ranlib"
        try:
            execs = self.conf.get("tools.build:compiler_executables", default={}, check_type=dict)
            cc = execs.get("c", "clang")
        except Exception:
            pass

        # Build the SQLite extension (.so) — uses vendored SQLite headers
        # R9: Always use -j1
        # Makefile is in source_folder, not build_folder
        self.run(f"make CC={cc} AR={ar} RANLIB={ranlib} -j1 extension",
                 cwd=self.source_folder)

    def package(self):
        # Copy extension library
        copy(self, "*.so*", os.path.join(self.source_folder, "build"),
             os.path.join(self.package_folder, "lib"))
        # Copy headers
        copy(self, "*.h", os.path.join(self.source_folder, "src", "include"),
             os.path.join(self.package_folder, "include"))

    def package_info(self):
        self.cpp_info.libs = ["graphqlite"]