#!/usr/bin/env python3
"""Conan recipe — brogue 1.14.1-r2 (Makefile).

Brogue is a roguelike game.
"""
from conan import ConanFile
from conan.tools.files import get, apply_conandata_patches, export_conandata_patches
from conan.tools.layout import basic_layout


class BrogueConan(ConanFile):
    name = "brogue"
    version = "1.14.1-r2"
    description = "Roguelike game"
    license = "AGPL-3.0-or-later"
    homepage = "https://sites.google.com/site/broguegame/"
    url = ""  # CI fills this

    package_type = "application"

    settings = "os", "compiler", "build_type", "arch"

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
        # Use terminal mode instead of SDL graphics (no SDL2 available on OHOS)
        self.run(f"cd {self.source_folder}/src && sed -i 's/TERMINAL := NO/TERMINAL := YES/' config.mk")
        self.run(f"cd {self.source_folder}/src && sed -i 's/GRAPHICS := YES/GRAPHICS := NO/' config.mk")
        self.run(f"cd {self.source_folder}/src && make CFLAGS='-fPIC -O2'")

    def package(self):
        self.run(f"mkdir -p {self.package_folder}/bin")
        self.run(f"cp {self.source_folder}/bin/brogue {self.package_folder}/bin/")

    def package_info(self):
        self.cpp_info.libs = []
        self.cpp_info.bindirs = ["bin"]
