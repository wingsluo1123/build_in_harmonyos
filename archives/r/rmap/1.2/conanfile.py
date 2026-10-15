#!/usr/bin/env python3
"""Conan recipe — rmap 1.2 (direct compiler build).

rmap: generate images of the earth from vector map data. Upstream ships an
autotools build oriented at host builds; this recipe drives the cross
compiler directly (recipe asset, no upstream source modifications)."""

from conan import ConanFile
from conan.tools.files import copy, get
import os

required_conan_version = ">=2.0"


class RmapConan(ConanFile):
    name = "rmap"
    version = "1.2"
    description = "rmap: generate images of the earth from vector map data (direct compiler build)"
    license = "GPL-2.0-or-later"
    url = "https://rmap.sourceforge.net/"
    homepage = "https://rmap.sourceforge.net/"
    topics = ("maps", "gis", "earth", "imaging")
    package_type = "application"

    settings = "os", "arch", "compiler", "build_type"
    requires = "gd/2.3.3.2"
    no_copy_source = True

    def export_sources(self):
        # Self-written build driver (recipe asset, not an upstream modification):
        # upstream configure is host-oriented (fcntl.h / mmap assumptions and
        # hardcoded -lgd probing), so build() drives the compiler directly.
        pass

    def apply_conandata_patches(self):
        # No upstream patches for 1.2 (patches: [] in conandata.yml).
        pass

    def source(self):
        get(self, **self.conan_data["sources"][self.version],
            destination=self.source_folder, strip_root=True)

    def build(self):
        src = self.source_folder
        gd = self.dependencies["gd"].cpp_info
        gd_inc = " ".join(f"-I{d}" for d in gd.includedirs)
        gd_libdirs = gd.libdirs[0]
        cc = self.conf.get("tools.build:compiler_executables", {}).get(
            "c") or "cc"
        defines = '-DPACKAGE=\\"rmap\\" -DVERSION=\\"1.2\\" -DGD_GIF'
        objs = []
        for f in ("main.c", "rmap.c"):
            obj = os.path.join(self.build_folder, f + ".o")
            self.run(f"{cc} {defines} -I{src} {gd_inc} -O2 -c "
                     f"{os.path.join(src, f)} -o {obj}")
            objs.append(obj)
        exe = os.path.join(self.build_folder, "rmap")
        self.run(f"{cc} -I{src} {gd_inc} -o {exe} " + " ".join(objs)
                 + f" -L{gd_libdirs} -lgd -lm")

    def package(self):
        copy(self, "COPYING", src=self.source_folder,
             dst=os.path.join(self.package_folder, "licenses"))
        copy(self, "rmap", src=self.build_folder,
             dst=os.path.join(self.package_folder, "bin"))
        copy(self, "*.h", src=self.source_folder,
             dst=os.path.join(self.package_folder, "include", "rmap"),
             excludes=("config.h",))
        # runtime data: vector map + default colormap (needed by the CLI)
        copy(self, "earth.rez", src=self.source_folder,
             dst=os.path.join(self.package_folder, "share", "rmap"))
        copy(self, "rmap.colors", src=self.source_folder,
             dst=os.path.join(self.package_folder, "share", "rmap"))

    def package_id(self):
        del self.info.settings.compiler

    def package_info(self):
        self.cpp_info.includedirs = ["include/rmap"]
        self.cpp_info.libdirs = []
        self.cpp_info.libs = []
        self.cpp_info.bindirs = ["bin"]
        self.cpp_info.resdirs = ["share/rmap"]
