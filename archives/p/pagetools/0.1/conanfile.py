#!/usr/bin/env python3
"""Conan recipe for pagetools 0.1 — Page Layout Detection Tools on HarmonyOS PC."""

import os
import shlex

from conan import ConanFile
from conan.tools.env import Environment
from conan.tools.files import apply_conandata_patches, copy, export_conandata_patches, get
from conan.tools.layout import basic_layout


class PagetoolsConan(ConanFile):
    name = "pagetools"
    version = "0.1"
    description = "Automatic deskew and bounding box determination for scanned page images"
    license = "GPL-2.0-or-later"
    homepage = "https://sourceforge.net/projects/pagetools/"
    url = "https://gitcode.com/OpenHarmonyPCDeveloper/build_in_harmonyos"
    package_type = "application"

    settings = "os", "compiler", "build_type", "arch"

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        self.requires("netpbm/10.73.42")
        self.requires("libtiff/4.7.2")

    def layout(self):
        basic_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"])

    def generate(self):
        netpbm = self.dependencies["netpbm"].cpp_info
        libtiff = self.dependencies["libtiff"].cpp_info
        comp_execs = self.conf.get("tools.build:compiler_executables", default={}, check_type=dict)
        cxx = comp_execs.get("cpp") or comp_execs.get("c++") or "clang++"
        ar = comp_execs.get("ar") or "/opt/lpk-fixed/llvm-ar"
        include_flags = " ".join(
            f"-I{p}" for p in list(netpbm.includedirs) + list(libtiff.includedirs)
        )
        lib_flags = " ".join(
            f"-L{p}" for p in list(netpbm.libdirs) + list(libtiff.libdirs)
        )
        env = Environment()
        env.define("CXX", cxx)
        env.define("AR", ar)
        env.define("LDFLAGS", lib_flags)
        env.vars(self).save_script("pagetools-build-env")

    def build(self):
        apply_conandata_patches(self)
        comp_execs = self.conf.get("tools.build:compiler_executables", default={}, check_type=dict)
        cxx = comp_execs.get("cpp") or comp_execs.get("c++") or "clang++"
        ar = comp_execs.get("ar") or "/opt/lpk-fixed/llvm-ar"
        netpbm = self.dependencies["netpbm"].cpp_info
        libtiff = self.dependencies["libtiff"].cpp_info
        include_flags = " ".join(
            f"-I{p}" for p in list(netpbm.includedirs) + list(libtiff.includedirs)
        )
        lib_flags = " ".join(
            f"-L{p}" for p in list(netpbm.libdirs) + list(libtiff.libdirs)
        )
        cxxflags = f"-fPIC -O2 {include_flags}"
        self.run(
            f"make all -j1 "
            f"CXX={shlex.quote(cxx)} AR={shlex.quote(ar)} "
            f"C++_FLAGS={shlex.quote(cxxflags)} LDFLAGS={shlex.quote(lib_flags)} "
            f"LIBPBM=netpbm",
            cwd=self.source_folder,
        )

    def package(self):
        copy(self, "pbm_findskew", os.path.join(self.source_folder, "pbm_findskew"),
             os.path.join(self.package_folder, "bin"))
        copy(self, "tiff_findskew", os.path.join(self.source_folder, "tiff_findskew"),
             os.path.join(self.package_folder, "bin"))
        copy(self, "libptutil.a", self.source_folder,
             os.path.join(self.package_folder, "lib"))
        copy(self, "libptraster.a", self.source_folder,
             os.path.join(self.package_folder, "lib"))
        copy(self, "libptformats.a", self.source_folder,
             os.path.join(self.package_folder, "lib"))
        copy(self, "COPYING", self.source_folder,
             os.path.join(self.package_folder, "share", "licenses", "pagetools"))
        copy(self, "README.txt", self.source_folder,
             os.path.join(self.package_folder, "share", "doc", "pagetools"))

    def package_info(self):
        self.cpp_info.bindirs = ["bin"]
        self.cpp_info.libs = ["ptformats", "ptraster", "ptutil"]
