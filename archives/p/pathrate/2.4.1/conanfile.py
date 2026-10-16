#!/usr/bin/env python3
"""HarmonyOS package for the Pathrate sender and receiver."""

import os

from conan import ConanFile
from conan.tools.files import apply_conandata_patches, copy, get
from conan.tools.layout import basic_layout


class PathrateConan(ConanFile):
    name = "pathrate"
    version = "2.4.1"
    description = "End-to-end network path capacity measurement"
    license = "GPL-2.0-or-later"
    homepage = "http://www.cc.gatech.edu/~dovrolis/bw-est/pathrate.html"
    url = "https://gitcode.com/OpenHarmonyPCDeveloper/build_in_harmonyos"
    package_type = "application"
    settings = "os", "arch", "compiler", "build_type"

    def export_sources(self):
        copy(self, "*.patch", src=os.path.join(self.recipe_folder, "patches"),
             dst=os.path.join(self.export_sources_folder, "patches"))

    def layout(self):
        basic_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"],
            filename="pathrate-2.4.1.tar.gz", strip_root=True)

    def build(self):
        apply_conandata_patches(self)
        compilers = self.conf.get(
            "tools.build:compiler_executables", default={}, check_type=dict
        )
        cc = compilers.get("c", "clang") if compilers else "clang"
        for target in ("pathrate_snd", "pathrate_rcv"):
            sources = f"{target}.c {target}_func.c"
            self.run(
                f"{cc} -std=gnu89 -O2 -pthread {sources} -o {target} -lm",
                cwd=self.source_folder,
            )

    def package(self):
        for name in ("pathrate_snd", "pathrate_rcv"):
            copy(self, name, src=self.source_folder,
                 dst=os.path.join(self.package_folder, "bin"))
        copy(self, "COPYING", src=self.source_folder,
             dst=os.path.join(self.package_folder, "licenses"))
        for name in ("README", "CHANGES"):
            copy(self, name, src=self.source_folder,
                 dst=os.path.join(self.package_folder, "res"))

    def package_info(self):
        self.cpp_info.bindirs = ["bin"]
