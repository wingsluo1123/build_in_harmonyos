#!/usr/bin/env python3
"""Conan recipe — lp_solve 5.5.2.14 (Makefile)"""
import os

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.files import get, copy, apply_conandata_patches, export_conandata_patches
from conan.tools.layout import basic_layout


class LpSolveConan(ConanFile):
    name = "lp_solve"
    version = "5.5.2.14"
    description = "Mixed Integer Linear Programming (MILP) solver"
    license = "LGPL-2.1-or-later"
    homepage = "https://lpsolve.sourceforge.net/"

    package_type = "library"

    settings = "os", "compiler", "build_type", "arch"
    options = {"shared": [True, False]}
    default_options = {"shared": False}

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

        # R32: Platform check compatible with OHOS
        if self.settings.os not in ("Linux", "OHOS"):
            raise ConanInvalidConfiguration(f"{self.name} only supports Linux/OHOS")

        # R33: Get compiler from Conan profile conf
        compilers = self.conf.get("tools.build:compiler_executables", default={})
        if isinstance(compilers, dict):
            cc = compilers.get("c", "clang")
        else:
            cc = "clang"
        ar = "llvm-ar"
        ranlib = "llvm-ranlib"

        # GNU ld (ld.bfd) required — lld has missing libxml2 dependency on OHOS
        ldflags = "-fuse-ld=/data/service/hnp/bin/ld.bfd"
        cflags = "-fPIC -O2"

        # R9: Use -j1, never -j$(nproc)
        # Use -r to disable built-in implicit rules (prevents yacc from
        # regenerating lp_rlp.c from lp_rlp.y, which would lose the
        # pre-generated token defines needed before #include "lp_rlp.h")
        self.run(
            f'make -r CC={cc} AR={ar} RANLIB={ranlib} LDFLAGS="{ldflags}" CFLAGS="{cflags}" all -j1',
            cwd=self.source_folder
        )

    def package(self):
        plat_dir = os.path.join(self.source_folder, "bin", "ux64")

        # Libraries
        copy(self, "liblpsolve55.a", plat_dir, os.path.join(self.package_folder, "lib"))
        if self.options.shared:
            copy(self, "liblpsolve55.so", plat_dir, os.path.join(self.package_folder, "lib"))

        # Executable
        copy(self, "lp_solve", plat_dir, os.path.join(self.package_folder, "bin"))

        # Headers — all installed to flat include/ (matching Makefile install target)
        copy(self, "*.h", self.source_folder, os.path.join(self.package_folder, "include"))
        copy(self, "*.h", os.path.join(self.source_folder, "bfp"), os.path.join(self.package_folder, "include"))
        copy(self, "*.h", os.path.join(self.source_folder, "bfp", "bfp_LUSOL"), os.path.join(self.package_folder, "include"))
        copy(self, "*.h", os.path.join(self.source_folder, "colamd"), os.path.join(self.package_folder, "include"))
        copy(self, "*.h", os.path.join(self.source_folder, "shared"), os.path.join(self.package_folder, "include"))

    def package_info(self):
        self.cpp_info.libs = ["lpsolve55"]
