#!/usr/bin/env python3
"""Conan recipe for htpdate 1.3.7 — HTTP Time Protocol synchronization tool.

htpdate synchronizes system time via HTTP headers from web servers.
Build system: raw Makefile (no configure).
"""
import os
import subprocess
import tempfile

from conan import ConanFile
from conan.tools.files import get, copy, apply_conandata_patches, export_conandata_patches
from conan.tools.layout import basic_layout


class HtpdateConan(ConanFile):
    name = "htpdate"
    version = "1.3.7"
    description = "HTTP Time Protocol synchronization tool"
    license = "GPL-2.0-or-later"
    homepage = "https://github.com/twekkel/htpdate"
    url = "https://github.com/twekkel/htpdate"

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

        # R33: Get compiler from Conan conf (dict-like), not shell env vars
        compilers = self.conf.get("tools.build:compiler_executables", default={}, check_type=dict)
        cc = compilers.get("c", "clang")

        # R8: Feature detection instead of platform macro (#ifdef __OHOS__)
        # Check if adjtime() is available; if not, define ADJTIME_MISSING
        cflags = "-Wall -std=c11 -pedantic -O2"
        test_code = '#include <sys/time.h>\nint main(void){struct timeval t={0};return adjtime(&t,0);}\n'
        tmpdir = os.environ.get("TMPDIR", "/tmp")
        with tempfile.NamedTemporaryFile(suffix=".c", mode="w", dir=tmpdir, delete=False) as f:
            f.write(test_code)
            test_path = f.name
        out_path = test_path + ".out"
        result = subprocess.run([cc, test_path, "-o", out_path], capture_output=True, timeout=10)
        if os.path.exists(out_path):
            os.unlink(out_path)
        os.unlink(test_path)
        if result.returncode != 0:
            cflags += " -DADJTIME_MISSING"

        self.run(f'make -C {self.source_folder} CC={cc} CFLAGS="{cflags}" -j1')

    def package(self):
        copy(self, "htpdate", self.source_folder, os.path.join(self.package_folder, "bin"))
        copy(self, "htpdate.8", self.source_folder, os.path.join(self.package_folder, "share/man/man8"))

    def package_info(self):
        self.cpp_info.bindirs = ["bin"]
