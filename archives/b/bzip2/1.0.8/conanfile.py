#!/usr/bin/env python3
"""Conan recipe for bzip2 1.0.8 — Makefile build system.

bzip2 is a data compression library and tool set.
Build: make && make -f Makefile-libbz2_so && make install
"""
import os

from conan import ConanFile
from conan.tools.files import get, apply_conandata_patches, export_conandata_patches
from conan.tools.layout import basic_layout


class Bzip2Conan(ConanFile):
    name = "bzip2"
    version = "1.0.8"
    description = "High-quality data compression library and tools."
    license = "BSD-4-Clause"
    homepage = "https://sourceware.org/bzip2/"
    url = ""  # CI fills this

    settings = "os", "compiler", "build_type", "arch"
    options = {"shared": [True, False]}
    default_options = {"shared": False}

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        pass

    def layout(self):
        basic_layout(self)
        # bzip2 builds in-source (Makefile in source dir)
        self.folders.build = "."

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def build(self):
        apply_conandata_patches(self)

        # R33: Get compiler/linker from Conan conf
        compilers = self.conf.get("tools.build:compiler_executables", default={}, check_type=dict)
        cc = compilers.get("c", "clang") if compilers else "clang"
        cxx = compilers.get("cpp", "clang++") if compilers else "clang++"

        # R5: OHOS has no /bin/sh, use CONFIG_SHELL from profile [buildenv]
        config_shell = os.environ.get("CONFIG_SHELL", "/data/service/hnp/bin/bash")

        # Build static library and tools
        self.run(f"make CC={cc} CXX={cxx} AR=llvm-ar RANLIB=llvm-ranlib SHELL={config_shell} -j1", cwd=self.source_folder)

        # Build shared library if requested
        if self.options.shared:
            # On OHOS, ln -sf has a bug: need rm before ln.
            # Makefile-libbz2_so uses ln -sf for libbz2.so.1.0.8 -> libbz2.so.1.0
            # The patch (0001) already works around this in the main Makefile.
            # For the shared Makefile, we override SHELL and use rm+ln approach.
            self.run(f"make -f Makefile-libbz2_so CC={cc} CXX={cxx} AR=llvm-ar RANLIB=llvm-ranlib SHELL={config_shell} -j1", cwd=self.source_folder)

    def package(self):
        # Install to Conan package folder via PREFIX
        # PREFIX is honored by bzip2's Makefile install target
        pkg = self.package_folder
        self.run(f"make install PREFIX={pkg} SHELL=/data/service/hnp/bin/bash", cwd=self.source_folder)

        if self.options.shared:
            # Shared library is built in current directory as libbz2.so.1.0.8
            # Copy manually since Makefile-libbz2_so has no install target
            lib_dir = os.path.join(pkg, "lib")
            os.makedirs(lib_dir, exist_ok=True)
            self.run(f"cp -P libbz2.so* {lib_dir}", cwd=self.source_folder)

    def package_info(self):
        self.cpp_info.libs = ["bz2"]
        if self.settings.os in ("Linux", "OHOS"):
            self.cpp_info.system_libs = ["pthread", "dl"]
