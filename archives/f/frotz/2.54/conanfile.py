#!/usr/bin/env python3
"""Conan recipe — frotz 2.54 (Z-machine interpreter, plain Makefile).
Lessons: self.run with cwd=source_folder, -j1, apply_conandata_patches.
Existing patch 0001 adds stdbool.h + KEY_MOUSE for ncursesw."""
import os
from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.files import get, apply_conandata_patches, export_conandata_patches
from conan.tools.gnu import AutotoolsToolchain
from conan.tools.layout import basic_layout

class FrotzConan(ConanFile):
    name = "frotz"
    version = "2.54"
    description = "Frotz — Z-machine interpreter for playing interactive fiction"
    license = "GPL-2.0-or-later"
    homepage = "https://frotz.sourceforge.net/"
    url = ""
    package_type = "application"
    settings = "os", "compiler", "build_type", "arch"

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        pass

    def layout(self):
        basic_layout(self)

    def validate(self):
        if self.settings.os not in ("Linux", "OHOS"):
            raise ConanInvalidConfiguration(f"frotz supports Linux/OHOS")

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def generate(self):
        tc = AutotoolsToolchain(self)
        tc.extra_defines.append("__OHOS__")
        tc.generate()

    def build(self):
        apply_conandata_patches(self)
        # Plain Makefile in source dir. -j1 avoids mkfifo on OHOS.
        self.run("make -j1 SOUND_TYPE=none", cwd=self.source_folder, env="conanbuild")

    def package(self):
        self.run(f"make install PREFIX={self.package_folder} SOUND_TYPE=none",
                 cwd=self.source_folder, env="conanbuild")

    def package_info(self):
        self.cpp_info.bindirs = ["bin"]
