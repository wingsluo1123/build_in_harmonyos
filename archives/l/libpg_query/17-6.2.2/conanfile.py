import os

from conan import ConanFile
from conan.tools.files import get, copy, apply_conandata_patches, export_conandata_patches
from conan.tools.layout import basic_layout


class LibpgqueryConan(ConanFile):
    name = "libpg_query"
    version = "17-6.2.2"
    description = "C library for accessing the PostgreSQL parser outside of the server environment"
    license = "BSD-3-Clause"
    homepage = "https://github.com/pganalyze/libpg_query"
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

        compilers = self.conf.get("tools.build:compiler_executables", default={}, check_type=dict) or {}
        cc = compilers.get("c", "clang")

        # Only build the static library target ("build"), not "all" which
        # includes examples/tests requiring the linker (fails on OHOS due to
        # lld missing libxml2.so.16)
        self.run(f'make build CC="{cc}" -j1', cwd=self.source_folder)

    def package(self):
        # Static library
        copy(self, "libpg_query.a", self.source_folder, os.path.join(self.package_folder, "lib"))
        # Headers
        copy(self, "pg_query.h", self.source_folder, os.path.join(self.package_folder, "include"))
        copy(self, "postgres_deparse.h", self.source_folder, os.path.join(self.package_folder, "include"))
        # Protobuf definition
        copy(self, "pg_query.proto", os.path.join(self.source_folder, "protobuf"), os.path.join(self.package_folder, "include", "pg_query"))

    def package_info(self):
        self.cpp_info.libs = ["pg_query"]
        self.cpp_info.system_libs = ["pthread"]
