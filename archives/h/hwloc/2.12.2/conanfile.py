#!/usr/bin/env python3
"""Conan recipe for hwloc/2.12.2 (Autotools project: configure + make).

hwloc is the Hardware Locality library from OpenMPI — discovers and binds
the hardware topology of the running system. This recipe builds the static
library and the 13 command-line tools (hwloc-info/lstopo/hwloc-bind ...).
"""
from conan import ConanFile
from conan.tools.files import get, apply_conandata_patches, export_conandata_patches
from conan.tools.gnu import Autotools, AutotoolsToolchain
from conan.tools.layout import basic_layout


class HwlocConan(ConanFile):
    name = "hwloc"
    version = "2.12.2"
    description = "hwloc 2.12.2"
    license = "BSD-3-Clause"
    homepage = "https://www.open-mpi.org/projects/hwloc/"
    url = "https://download.open-mpi.org/release/hwloc/v2.12/hwloc-2.12.2.tar.gz"

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

    def generate(self):
        tc = AutotoolsToolchain(self)
        # R26: System-name libraries default to static
        if not self.options.shared:
            tc.configure_args.append("--enable-static")
            tc.configure_args.append("--disable-shared")
        # Add project-specific configure args here:
        # tc.configure_args.append("--without-bash-malloc")
        tc.generate()

    def build(self):
        apply_conandata_patches(self)
        autotools = Autotools(self)
        autotools.configure()
        autotools.make(args=[
            "-j1",
            "ACLOCAL=/bin/true",
            "AUTOMAKE=/bin/true",
            "AUTOHEADER=/bin/true",
        ])

    def package(self):
        autotools = Autotools(self)
        autotools.install(args=[
            "-j1",
            "ACLOCAL=/bin/true",
            "AUTOMAKE=/bin/true",
            "AUTOHEADER=/bin/true",
        ])

    def package_info(self):
        self.cpp_info.libs = ["hwloc"]
