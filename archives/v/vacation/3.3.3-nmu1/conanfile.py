#!/usr/bin/env python3
"""Conan recipe for vacation 3.3.3-nmu1."""

import os

from conan import ConanFile
from conan.tools.files import (
    apply_conandata_patches,
    copy,
    export_conandata_patches,
    get,
)


class VacationConan(ConanFile):
    name = "vacation"
    version = "3.3.3-nmu1"
    description = "Automatic mail responder with reply throttling"
    license = "BSD-3-Clause"
    homepage = "https://packages.debian.org/source/sid/vacation"
    url = "https://salsa.debian.org/debian/vacation"
    topics = ("mail", "auto-responder", "berkeley-db", "cli")

    package_type = "application"
    settings = "os", "compiler", "build_type", "arch"

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        self.requires("db1-compat/2.1.3")

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def build(self):
        apply_conandata_patches(self)
        dep = self.dependencies["db1-compat"]
        include_dir = dep.cpp_info.includedirs[0]
        lib_dir = dep.cpp_info.libdirs[0]
        self.run("make clean CFLAGS= LDFLAGS=")
        self.run(
            "make -j1 "
            f"CPPFLAGS='-I{include_dir}' "
            "CFLAGS='-O2 -fPIE -Wall -Wextra' "
            f"LDFLAGS='-L{lib_dir}' "
            "LIBS='-ldb'"
        )

    def package(self):
        copy(self, "vacation", src=self.source_folder,
             dst=os.path.join(self.package_folder, "bin"))
        copy(self, "vacation.1", src=self.source_folder,
             dst=os.path.join(self.package_folder, "share", "man", "man1"))
        copy(self, "copyright", src=os.path.join(self.source_folder, "debian"),
             dst=os.path.join(self.package_folder, "licenses"))

    def package_info(self):
        self.cpp_info.bindirs = ["bin"]
        self.cpp_info.libdirs = []
