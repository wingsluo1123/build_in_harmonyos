#!/usr/bin/env python3
"""Conan recipe — tm-align 20190822 (TMalign / TMscore, C++ implementation).

TM-align / TM-score (Zhang Lab, University of Michigan) compare protein
structures from PDB files. The Debian orig tarball ships each tool twice: a
Fortran 77 version (*.f) and a C++ version (*.cpp). This recipe builds the
C++ version only, so the package needs nothing but the C++ standard library
and libm (no gfortran runtime).

Adaptation notes (see notes.md):
  * The upstream source has no build system; the official build line is
      g++ -static -O3 -ffast-math -lm -o TMalign TMalign.cpp
    -> the compiler is taken from the Conan toolchain conf (R33) and the
    tools are compiled directly. No source patch is needed.
  * The tarball has no top-level directory, so source() must not strip_root.
"""
import os

from conan import ConanFile
from conan.errors import ConanException
from conan.tools.files import apply_conandata_patches, copy, export_conandata_patches, get
from conan.tools.layout import basic_layout


class TmAlignConan(ConanFile):
    name = "tm-align"
    version = "20190822"
    description = "TM-align and TM-score: protein structure alignment and scoring (C++ implementation)"
    license = "LicenseRef-TM-align-permissive"
    homepage = "https://zhanggroup.org/TM-align/"
    url = "https://gitcode.com/OpenHarmonyPCDeveloper/build_in_harmonyos/tree/main/archives/t/tm-align/20190822"

    package_type = "application"
    languages = "C++"
    settings = "os", "arch", "compiler", "build_type"

    _tools = ("TMalign", "TMscore")

    def export_sources(self):
        export_conandata_patches(self)

    def layout(self):
        basic_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"][self.version])

    def build(self):
        apply_conandata_patches(self)
        cxx = self.conf.get("tools.build:compiler_executables", default={}, check_type=dict).get("cpp", "clang++")
        opt = "-O0 -g" if self.settings.build_type == "Debug" else "-O3 -ffast-math"
        for tool in self._tools:
            self.run(f'{cxx} {opt} -o "{tool}" "{os.path.join(self.source_folder, tool + ".cpp")}" -lm',
                     cwd=self.build_folder)
            if not os.path.isfile(os.path.join(self.build_folder, tool)):
                raise ConanException(f"{tool} was not produced by the build")

    def package(self):
        for tool in self._tools:
            copy(self, tool, self.build_folder, os.path.join(self.package_folder, "bin"))

    def package_info(self):
        self.cpp_info.libdirs = []
        self.cpp_info.includedirs = []
        self.cpp_info.bindirs = ["bin"]
