#!/usr/bin/env python3
"""Conan recipe — tcl 8.6.14 (HarmonyOS PC)
"""
from conan import ConanFile
from conan.tools.files import get, apply_conandata_patches, export_conandata_patches
from conan.tools.gnu import Autotools, AutotoolsToolchain
from conan.tools.layout import basic_layout
import os


class TclConan(ConanFile):
    name = "tcl"
    version = "8.6.14"
    description = "Tcl — the Tool Command Language"
    license = "Tcl/Tk"
    homepage = "https://www.tcl.tk/"

    package_type = "library"

    settings = "os", "compiler", "build_type", "arch"
    options = {"shared": [True, False]}
    default_options = {"shared": False}

    def export_sources(self):
        export_conandata_patches(self)

    def layout(self):
        basic_layout(self, src_folder="unix")

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)
        # Apply Conan standard patch mechanism for HMDFS umask fix (E011)
        apply_conandata_patches(self)

    def generate(self):
        tc = AutotoolsToolchain(self)
        # E001: ensure CC=clang is set for HarmonyOS (no system cc)
        tc.extra_vars = {"CC": os.environ.get("CC", "clang"),
                         "CXX": os.environ.get("CXX", "clang++")}
        if self.options.shared:
            tc.configure_args.append("--enable-shared")
            tc.configure_args.append("--disable-static")
        else:
            tc.configure_args.append("--disable-shared")
            tc.configure_args.append("--enable-static")
        tc.generate()

    def build(self):
        autotools = Autotools(self)
        autotools.configure(build_script_folder=os.path.join(self.source_folder, "unix"))
        autotools.make()

    def package(self):
        autotools = Autotools(self)
        autotools.install()

    def package_info(self):
        self.cpp_info.libs = ["tcl8.6"]
        if self.options.shared:
            self.cpp_info.defines.append("TCL_SHARED_BUILD=1")
        else:
            self.cpp_info.defines.append("TCL_SHARED_BUILD=0")