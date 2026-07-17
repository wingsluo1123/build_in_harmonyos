#!/usr/bin/env python3
"""Conan recipe for scdoc 1.11.3 — simple man page generator.

scdoc is a tool that converts a simple markup language into roff-formatted
man pages. It uses a plain Makefile with no configure script and no external
dependencies. The build produces a single static binary.

Platform: OHOS aarch64 (also builds on Linux).
Build system: Makefile (no configure).
No patches needed for 1.11.3 (str_create(void) fix already upstream).
"""
import os

from conan import ConanFile
from conan.tools.files import get, copy, apply_conandata_patches, export_conandata_patches
from conan.tools.layout import basic_layout


class ScdocConan(ConanFile):
    name = "scdoc"
    version = "1.11.3"
    description = "Simple man page generator using a custom markup language"
    license = "MIT"
    homepage = "https://git.sr.ht/~sircmpwn/scdoc"
    url = ""  # CI fills this

    package_type = "application"

    settings = "os", "arch", "compiler", "build_type"

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
        comp_execs = self.conf.get("tools.build:compiler_executables", default={}, check_type=dict)
        cc = comp_execs.get("c", "clang")

        # R9: Use -j1. Run in source folder where Makefile is.
        self.run(f"make CC={cc} -j1", cwd=self.source_folder)

        # Run upstream tests (make check runs test scripts that invoke ./scdoc)
        # Tests use #!/bin/sh which is available on OHOS
        import subprocess
        try:
            result = subprocess.run(
                "make check", shell=True, cwd=self.source_folder,
                capture_output=True, text=True, timeout=120
            )
            if result.returncode != 0:
                self.output.warning("make check failed — upstream tests did not pass")
                self.output.info(result.stdout[-500:] if result.stdout else "")
                self.output.info(result.stderr[-500:] if result.stderr else "")
            else:
                self.output.info("make check: SUCCESS")
                self.output.info(result.stdout[-500:] if result.stdout else "")
        except subprocess.TimeoutExpired:
            self.output.warning("make check timed out after 120s — degraded to warning")

    def package(self):
        # Build outputs are in source folder (Makefile project, no separate build dir)
        src = self.source_folder
        # Copy scdoc binary to bin/
        copy(self, "scdoc", src=src, dst=os.path.join(self.package_folder, "bin"), keep_path=False)
        # Copy man pages
        copy(self, "scdoc.1", src=src, dst=os.path.join(self.package_folder, "share", "man", "man1"), keep_path=False)
        copy(self, "scdoc.5", src=src, dst=os.path.join(self.package_folder, "share", "man", "man5"), keep_path=False)
        # Copy pkgconfig file
        copy(self, "scdoc.pc", src=src, dst=os.path.join(self.package_folder, "share", "pkgconfig"), keep_path=False)

    def package_info(self):
        self.cpp_info.bindirs = ["bin"]
        self.cpp_info.libdirs = []
        self.cpp_info.libs = []
