#!/usr/bin/env python3
"""Conan recipe — chkrootkit 0.59 (Makefile, CLI tool)"""
import os

from conan import ConanFile
from conan.tools.files import get, copy, save, export_conandata_patches, apply_conandata_patches
from conan.tools.layout import basic_layout


class ChkrootkitConan(ConanFile):
    name = "chkrootkit"
    version = "0.59"
    description = "chkrootkit locally checks for signs of a rootkit"
    license = "BSD-2-Clause"
    homepage = "https://www.chkrootkit.org/"
    url = ""

    package_type = "application"
    settings = "os", "compiler", "build_type", "arch"

    def export_sources(self):
        export_conandata_patches(self)

    def layout(self):
        basic_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def build(self):
        apply_conandata_patches(self)

        # R33: Get compiler from Conan conf, never from shell env vars
        compilers = self.conf.get("tools.build:compiler_executables", default={}, check_type=dict) or {}
        cc = compilers.get("c", "clang")

        # chkrootkit uses a custom Makefile (no configure, no install target)
        # CC: override 'cc' (not available on OHOS)
        # STATIC=: disable -static (incompatible with musl libc on OHOS)
        # CFLAGS: include -DHAVE_LASTLOG_H (Makefile's += is overridden by command-line)
        self.run(f'make -C {self.source_folder} sense CC={cc} STATIC= CFLAGS="-DHAVE_LASTLOG_H -fPIC -O2" -j1')

    def package(self):
        # Install layout: bin/chkrootkit (wrapper) + libexec/chkrootkit/ (all tools)
        libexec_dir = os.path.join(self.package_folder, "libexec", "chkrootkit")
        src = self.source_folder

        # Copy compiled C tools
        for tool in ["chklastlog", "chkwtmp", "chkproc", "chkdirs",
                      "check_wtmpx", "strings-static", "chkutmp"]:
            copy(self, tool, src, libexec_dir)

        # Copy main chkrootkit shell script
        copy(self, "chkrootkit", src, libexec_dir)

        # Create wrapper script (chkrootkit uses ./ to reference tools)
        wrapper = '#!/bin/sh\ncd "$(dirname "$0")/../libexec/chkrootkit" && ./chkrootkit "$@"\n'
        wrapper_path = os.path.join(self.package_folder, "bin", "chkrootkit")
        save(self, wrapper_path, wrapper)
        os.chmod(wrapper_path, 0o755)

        # Copy documentation
        doc_dir = os.path.join(self.package_folder, "share", "doc", "chkrootkit")
        copy(self, "README", src, doc_dir)
        copy(self, "COPYRIGHT", src, doc_dir)
        copy(self, "ACKNOWLEDGMENTS", src, doc_dir)

    def package_info(self):
        self.cpp_info.bindirs = ["bin"]
        self.cpp_info.libdirs = []
