#!/usr/bin/env python3
"""Conan recipe for armci-mpi 0.4 — ARMCI MPI implementation.

armci-mpi provides the ARMCI (Aggregate Remote Memory Copy Interface) API
using MPI one-sided communication (RMA). It depends on an MPI implementation
(mpich) and is built as a static library (libarmci.a).
"""
import os
from shlex import quote

from conan import ConanFile
from conan.tools.files import get, apply_conandata_patches, export_conandata_patches, copy
from conan.tools.gnu import Autotools, AutotoolsToolchain
from conan.tools.layout import basic_layout


class ArmcimpiConan(ConanFile):
    name = "armci-mpi"
    version = "0.4"
    description = "ARMCI (Aggregate Remote Memory Copy Interface) MPI implementation using MPI one-sided communication (RMA)"
    license = "MIT"
    homepage = "https://github.com/pmodels/armci-mpi"

    package_type = "library"

    settings = "os", "compiler", "build_type", "arch"
    options = {"shared": [True, False]}
    default_options = {"shared": False}

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        self.requires("mpich/5.0.1")

    def build_requirements(self):
        self.tool_requires("autoconf/2.72")
        self.tool_requires("automake/1.18")
        self.tool_requires("libtool/2.5.4")

    def layout(self):
        basic_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def generate(self):
        tc = AutotoolsToolchain(self)
        if not self.options.shared:
            tc.configure_args.append("--enable-static")
            tc.configure_args.append("--disable-shared")
        mpich = self.dependencies.get("mpich")
        if mpich:
            mpich_inc = os.path.join(mpich.package_folder, "include")
            mpich_lib = os.path.join(mpich.package_folder, "lib")
            tc.extra_cflags.append(f"-I{mpich_inc}")
            tc.extra_ldflags.append(f"-L{mpich_lib}")
            tc.extra_ldflags.append("-lmpi")
        tc.generate()

    def build(self):
        apply_conandata_patches(self)
        autotools = Autotools(self)
        if not os.path.isfile(os.path.join(self.source_folder, "configure")):
            autotools.autoreconf()
        self._fix_umask()
        autotools.configure()
        autotools.make(args=["-j1"])

    def package(self):
        autotools = Autotools(self)
        autotools.install()
        copy(self, "COPYRIGHT", src=self.source_folder, dst=os.path.join(self.package_folder, "licenses"), keep_path=False)

    def _fix_umask(self):
        """Fix umask 077 in configure scripts (HarmonyOS setgid issue)."""
        import glob
        for cfg in glob.glob(os.path.join(self.source_folder, "**", "configure"), recursive=True):
            try:
                with open(cfg, encoding="utf-8", errors="ignore") as f:
                    text = f.read()
            except OSError:
                continue
            if "umask 077" in text:
                with open(cfg, "w", encoding="utf-8") as f:
                    f.write(text.replace("umask 077", "umask 022"))

    def package_info(self):
        self.cpp_info.libs = ["armci"]
        self.cpp_info.set_property("cmake_file_name", "armci-mpi")
        self.cpp_info.set_property("cmake_target_name", "armci-mpi::armci-mpi")
        self.cpp_info.set_property("pkg_config_name", "armci-mpi")
