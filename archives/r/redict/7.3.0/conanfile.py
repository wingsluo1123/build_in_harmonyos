#!/usr/bin/env python3
"""Conan recipe for redict 7.3.0 — HarmonyOS PC (aarch64).

Redict is the LGPL-3.0 fork of Redis OSS 7.2.4. It builds command-line
tools (redict-server, redict-cli, redict-benchmark, etc.) using a
Makefile-based build system (no configure script).

Key adaptation notes for HarmonyOS/musl:
  - MALLOC=libc: musl does not support jemalloc, use libc malloc instead
  - setproctitle.c: program_invocation_name is glibc-only, guard with __GLIBC__
  - pthread_cancel/setcancelstate/setcanceltype: not available in musl,
    provide weak no-op stubs
"""
import os

from conan import ConanFile
from conan.tools.files import get, copy, apply_conandata_patches, export_conandata_patches
from conan.tools.layout import basic_layout


class RedictConan(ConanFile):
    name = "redict"
    version = "7.3.0"
    description = "LGPLv3 fork of Redis, distributed in-memory key-value store"
    license = "LGPL-3.0-only"
    homepage = "https://redict.io"
    url = ""  # CI fills this

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

        # R33: Get compiler from Conan conf, NEVER from shell env vars.
        compilers = self.conf.get("tools.build:compiler_executables", default={}, check_type=dict)
        cc = compilers.get("c", "clang")
        cxx = compilers.get("cpp", "clang++")

        # R9: Always use -j1
        # MALLOC=libc: jemalloc not compatible with musl/HarmonyOS
        src_dir = os.path.join(self.source_folder, "src")
        self.run(f"make CC={cc} CXX={cxx} MALLOC=libc -j1 -C {src_dir}")

        # Ensure binaries have redict-* names (Redict source uses redict-*,
        # but if built from Redis source, rename redis-* to redict-*)
        src_dir = os.path.join(self.source_folder, "src")
        for name in ["server", "cli", "benchmark", "sentinel", "check-rdb", "check-aof"]:
            redis_name = f"redis-{name}"
            redict_name = f"redict-{name}"
            redis_path = os.path.join(src_dir, redis_name)
            redict_path = os.path.join(src_dir, redict_name)
            if os.path.exists(redis_path) and not os.path.exists(redict_path):
                os.rename(redis_path, redict_path)

    def package(self):
        # Copy executables from src/ to bin/
        src_dir = os.path.join(self.source_folder, "src")
        for name in ["redict-server", "redict-cli", "redict-benchmark",
                      "redict-sentinel", "redict-check-rdb", "redict-check-aof"]:
            copy(self, name, src_dir, os.path.join(self.package_folder, "bin"))

    def package_info(self):
        self.cpp_info.bindirs = ["bin"]
