#!/usr/bin/env python3
"""Conan recipe for zinnia 0.06 — Yet Another Hand Written Character Recognizer.

Autotools (configure + make) based pure C++ library with CLI tools
(zinnia / zinnia_learn / zinnia_convert). No third-party dependencies.
Adapted for HarmonyOS PC (aarch64-linux-ohos).
"""
from conan import ConanFile
from conan.tools.files import get, apply_conandata_patches, export_conandata_patches
from conan.tools.gnu import Autotools, AutotoolsToolchain
from conan.tools.layout import basic_layout


class ZinniaConan(ConanFile):
    name = "zinnia"
    version = "0.06"
    description = "zinnia: Yet Another Hand Written Character Recognizer (C++ library + CLI tools)"
    license = "BSD-3-Clause"
    homepage = "https://zinnia.sourceforge.net/"
    url = "https://gitcode.com/OpenHarmonyPCDeveloper/build_in_harmonyos"

    package_type = "library"

    settings = "os", "compiler", "build_type", "arch"
    options = {"shared": [True, False], "fPIC": [True, False]}
    default_options = {"shared": False, "fPIC": True}

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
        # R26/R32: pure C++ lib, no system-name conflict; static default.
        # Keep configure args minimal (R1): only --prefix is required by default.
        if not self.options.shared:
            tc.configure_args.append("--enable-static")
            tc.configure_args.append("--disable-shared")
        tc.generate()

    def build(self):
        apply_conandata_patches(self)
        autotools = Autotools(self)
        autotools.configure()
        autotools.make(args=["-j1"])

    def package(self):
        autotools = Autotools(self)
        autotools.install()

    def package_info(self):
        self.cpp_info.libs = ["zinnia"]
        # CLI tools installed to bin/ (R38: declared in commands.json)
        self.cpp_info.bindirs = ["bin"]
