#!/usr/bin/env python3
"""Conan recipe for picat 3.9.7 — Makefile-based CLI tool.

Picat is a logic-based multi-paradigm programming language. It uses a custom
Makefile (Makefile.ohos) for OpenHarmony, with the build target in emu/.

Build:
  cd emu && make -f Makefile.ohos -j1

Outputs:
  emu/picat    — ELF binary
  lib/*.pi     — 26 library modules

R9:  Use make -j1 (not -j$(nproc))
R32: settings.os includes both Linux and OHOS
R33: No shell env vars — Makefile.ohos hardcodes clang/clang++
R38: Command-line tool — commands.json declared at software level
"""
import os
import stat

from conan import ConanFile
from conan.tools.files import get, copy, apply_conandata_patches, export_conandata_patches
from conan.tools.layout import basic_layout


class PicatConan(ConanFile):
    name = "picat"
    version = "3.9.7"
    description = "Simple, and yet powerful, logic-based multi-paradigm programming language"
    license = "MPL-2.0"
    homepage = "https://picat-lang.org"
    url = ""  # CI fills this

    package_type = "application"
    settings = "os", "arch"

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

        # Create Makefile.ohos for OpenHarmony (based on Makefile.linux64)
        makefile_ohos = os.path.join(self.source_folder, "emu", "Makefile.ohos")
        content = (
            "EXT =\n"
            "CPP    = clang++ -DGC -DGCC -DPICAT -DSAT -DM64BITS -DFANN_NO_DLL -DFANN -D__OHOS__\n"
            "CC     = clang -DGC -DGCC -DPICAT -DSAT -DM64BITS -DFANN_NO_DLL -DFANN -D__OHOS__\n"
            "CCC=$(CC) -c\n"
            "CPPC=$(CPP) -c\n"
            "\n"
            "CFLAGS = -O3 -fPIC -fno-strict-aliasing -finline-functions -Dunix -DLINUX -DPOSIX -w\n"
            "LFLAGS = -lm -lpthread\n"
            "\n"
            "include common.mak\n"
        )
        with open(makefile_ohos, "w") as f:
            f.write(content)

        # R9: Always use -j1
        self.run("make -f Makefile.ohos -j1", cwd=os.path.join(self.source_folder, "emu"))

    def package(self):
        # Copy the picat binary
        emu_dir = os.path.join(self.source_folder, "emu")
        copy(self, "picat", src=emu_dir,
             dst=os.path.join(self.package_folder, "bin"), keep_path=False)
        # Copy library modules (*.pi files)
        lib_dir = os.path.join(self.source_folder, "lib")
        copy(self, "*.pi", src=lib_dir,
             dst=os.path.join(self.package_folder, "share/picat/lib"), keep_path=False)
        # Ensure binary is executable
        bin_file = os.path.join(self.package_folder, "bin", "picat")
        if os.path.isfile(bin_file):
            os.chmod(bin_file, os.stat(bin_file).st_mode | stat.S_IEXEC | stat.S_IXGRP | stat.S_IXOTH)

    def package_info(self):
        self.cpp_info.bindirs = ["bin"]
        self.cpp_info.libdirs = []
        self.cpp_info.libs = []
