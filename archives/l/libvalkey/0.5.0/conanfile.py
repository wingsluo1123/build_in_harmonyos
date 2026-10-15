#!/usr/bin/env python3
"""Conan recipe — libvalkey 0.5.0 (raw GNU Make, no configure).

Builds the upstream release via its plain Makefile. Uses package-relative
pkg-config metadata and keeps libvalkey.so.0 ABI unchanged. TLS/RDMA are
optional and off by default (no extra system deps required).
"""
import os

from conan import ConanFile
from conan.tools.files import get, copy, rm, apply_conandata_patches, export_conandata_patches
from conan.tools.layout import basic_layout


class LibvalkeyConan(ConanFile):
    name = "libvalkey"
    version = "0.5.0"
    description = "libvalkey is the C client library used by Valkey (RESP2/RESP3)."
    license = "BSD-3-Clause"
    homepage = "https://github.com/valkey-io/libvalkey"
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

        compilers = self.conf.get("tools.build:compiler_executables", default={}, check_type=dict)
        cc = compilers.get("c", "clang") if compilers else "clang"
        ar = compilers.get("ar", "llvm-ar") if compilers else "llvm-ar"
        ranlib = compilers.get("ranlib", "llvm-ranlib") if compilers else "llvm-ranlib"

        # Raw make project (no configure). TLS/RDMA stay off (no extra deps).
        # Makefile lives at source root; build there (basic_layout build-release
        # 子目录不含 Makefile)。
        self.run(f"make CC={cc} AR={ar} RANLIB={ranlib} USE_TLS=0 USE_RDMA=0 -j1",
                 cwd=self.source_folder)

    def package(self):
        # `make install` installs headers, static+shared libs and valkey.pc
        # under $(DESTDIR)$(PREFIX). Use DESTDIR = package_folder, PREFIX = /
        # so files land at <package>/include, <package>/lib, <package>/lib/pkgconfig.
        self.run(f"make install USE_TLS=0 USE_RDMA=0 PREFIX=/ DESTDIR={self.package_folder}",
                 cwd=self.source_folder)
        if not self.options.shared:
            # 静态模式（默认）：移除共享库与符号链接，仅保留 libvalkey.a。
            # 避免消费者运行时把同名 .so 当作动态依赖而解析到错误符号。
            rm(self, "libvalkey.so*", os.path.join(self.package_folder, "lib"))

    def package_info(self):
        self.cpp_info.libs = ["valkey"]
        self.cpp_info.set_property("pkg_config_name", "valkey")