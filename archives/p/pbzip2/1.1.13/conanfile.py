#!/usr/bin/env python3
"""Conan recipe — pbzip2 1.1.13 (Makefile)"""

import os

from conan import ConanFile
from conan.tools.files import get, copy, apply_conandata_patches, export_conandata_patches
from conan.tools.layout import basic_layout


class Pbzip2Conan(ConanFile):
    name = "pbzip2"
    version = "1.1.13"
    description = "并行BZIP2文件压缩器，基于pthread实现多线程压缩/解压，与bzip2格式完全兼容"
    license = "bzip2-1.0.6"
    homepage = "https://launchpad.net/pbzip2"

    package_type = "application"

    settings = "os", "compiler", "build_type", "arch"

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        self.requires("bzip2/1.0.8")

    def layout(self):
        basic_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def build(self):
        apply_conandata_patches(self)

        bzip2_info = self.dependencies["bzip2"].cpp_info
        include_dir = bzip2_info.aggregated_components().includedirs[0]
        lib_dir = bzip2_info.aggregated_components().libdirs[0]

        compilers = self.conf.get("tools.build:compiler_executables", default={}, check_type=dict)
        cxx = compilers.get("cpp", "clang++") if compilers else "clang++"

        cxxflags = (
            f"-O2 -fPIC -pthread -D_POSIX_PTHREAD_SEMANTICS "
            f"-D_LARGEFILE64_SOURCE -D_FILE_OFFSET_BITS=64 "
            f"-DUSE_STACKSIZE_CUSTOMIZATION -I{include_dir}"
        )
        ldflags = f"-L{lib_dir}"
        ldlibs = "-lbz2 -lpthread"

        self.run(
            f"make CXX={cxx} CXXFLAGS='{cxxflags}' LDFLAGS='{ldflags}' "
            f"LDLIBS='{ldlibs}' -j1",
            cwd=self.source_folder,
        )

    def package(self):
        bindir = os.path.join(self.package_folder, "bin")
        mandir = os.path.join(self.package_folder, "share", "man", "man1")
        os.makedirs(bindir, exist_ok=True)
        os.makedirs(mandir, exist_ok=True)

        copy(self, "pbzip2", self.source_folder, bindir)
        copy(self, "pbzip2.1", self.source_folder, mandir)

        # Create symlinks (R5: rm -f && ln -s)
        for link in ["pbunzip2", "pbzcat"]:
            link_path = os.path.join(bindir, link)
            if os.path.lexists(link_path):
                os.remove(link_path)
            os.symlink("pbzip2", link_path)

    def package_info(self):
        self.cpp_info.bindirs = ["bin"]
        self.cpp_info.resdirs = ["share"]
