#!/usr/bin/env python3
"""Conan recipe for libsixel — Sixel graphics encoding library.

Build system: Meson
Upstream: https://github.com/libsixel/libsixel
"""
import shutil

from conan import ConanFile
from conan.tools.files import get, apply_conandata_patches, export_conandata_patches
from conan.tools.layout import basic_layout
from conan.tools.meson import Meson, MesonToolchain


class LibsixelConan(ConanFile):
    name = "libsixel"
    version = "1.10.5"
    description = "Sixel graphics encoding library"
    license = "MIT"
    homepage = "https://github.com/libsixel/libsixel"
    url = "https://gitcode.com/OpenHarmonyPCDeveloper/build_in_harmonyos"

    package_type = "library"

    settings = "os", "compiler", "build_type", "arch"
    options = {"shared": [True, False]}
    default_options = {"shared": True}

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        pass

    def layout(self):
        basic_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def generate(self):
        tc = MesonToolchain(self)
        # Disable optional features that require external dependencies
        tc.project_options["gdk-pixbuf2"] = "disabled"
        tc.project_options["gd"] = "disabled"
        tc.project_options["libcurl"] = "disabled"
        tc.project_options["jpeg"] = "disabled"
        tc.project_options["png"] = "disabled"
        tc.project_options["python"] = "disabled"
        tc.project_options["tests"] = "disabled"
        # Build shared/static based on Conan option
        tc.project_options["default_library"] = "shared" if self.options.shared else "static"
        # OHOS: meson's subprocess can't find llvm-ar via shutil.which,
        # so explicitly set archiver path in the meson native file
        if self.settings.os in ("Linux", "OHOS"):
            tc.ar = shutil.which("llvm-ar") or "/data/service/hnp/bin/llvm-ar"
            tc.binaries["ranlib"] = shutil.which("llvm-ranlib") or "/data/service/hnp/bin/llvm-ranlib"
        tc.generate()

    def build(self):
        apply_conandata_patches(self)
        meson = Meson(self)
        meson.configure()
        meson.build()

    def package(self):
        meson = Meson(self)
        meson.install()

    def package_info(self):
        self.cpp_info.libs = ["sixel"]
