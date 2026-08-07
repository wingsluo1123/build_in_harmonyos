#!/usr/bin/env python3
"""Conan recipe for pcsc-lite 2.4.0.

pcsc-lite is a middleware to access smart cards using SCard API (PC/SC).
Build system: Meson.
"""
import os

from conan import ConanFile
from conan.tools.files import get, apply_conandata_patches, export_conandata_patches, rm, replace_in_file
from conan.tools.meson import Meson, MesonToolchain
from conan.tools.gnu import PkgConfigDeps
from conan.tools.layout import basic_layout


class PcscliteConan(ConanFile):
    name = "pcsc-lite"
    version = "2.4.0"
    description = "Middleware to access a smart card using SCard API (PC/SC)"
    license = "GPL-3.0"
    homepage = "https://github.com/LudovicRousseau/PCSC"
    url = "https://github.com/LudovicRousseau/PCSC"

    package_type = "library"

    settings = "os", "arch", "compiler", "build_type"
    options = {
        "shared": [True, False],
        "fPIC": [True, False],
    }
    default_options = {
        "shared": True,
        "fPIC": True,
    }

    def export_sources(self):
        export_conandata_patches(self)

    def config_options(self):
        if self.settings.os == "Windows":
            self.options.rm_safe("fPIC")

    def requirements(self):
        self.requires("libusb/1.0.27")

    def layout(self):
        basic_layout(self, src_folder=".")

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def generate(self):
        tc = MesonToolchain(self)
        tc.project_options["libsystemd"] = "false"
        tc.project_options["libudev"] = "false"
        tc.project_options["libusb"] = "true"
        tc.project_options["polkit"] = "false"
        tc.project_options["usb"] = "true"
        tc.project_options["serial"] = "true"
        tc.generate()
        # MesonToolchain only writes c/cpp to [binaries], not ar.
        # Add ar and ranlib so meson can find the archiver.
        native_file = os.path.join(self.generators_folder, "conan_meson_native.ini")
        replace_in_file(self, native_file, "[binaries]\n",
                         "[binaries]\nar = '/data/service/hnp/bin/llvm-ar'\nranlib = '/data/service/hnp/bin/llvm-ranlib'\n")
        # Generate pkg-config files for dependencies (libusb)
        pkg = PkgConfigDeps(self)
        pkg.generate()

    def build(self):
        apply_conandata_patches(self)
        # meson.options and meson_options.txt both exist in the source tree;
        # meson requires only one. Remove the legacy meson_options.txt.
        rm(self, "meson_options.txt", self.source_folder)
        meson = Meson(self)
        meson.configure()
        meson.build()

    def package(self):
        meson = Meson(self)
        meson.install()

    def package_info(self):
        self.cpp_info.libs = ["pcsclite"]
        self.cpp_info.includedirs = ["include/PCSC"]
        if self.settings.os in ("Linux", "OHOS"):
            self.cpp_info.system_libs = ["pthread"]
