#!/usr/bin/env python3
"""Conan recipe for usbredir 0.15.0, the SPICE/QEMU USB redirection libraries."""

import os

from conan import ConanFile
from conan.tools.files import copy, get
from conan.tools.gnu import PkgConfigDeps
from conan.tools.meson import Meson, MesonToolchain, meson_layout


class UsbredirConan(ConanFile):
    name = "usbredir"
    version = "0.15.0"
    description = "USB redirection protocol parser and host libraries"
    license = "LGPL-2.1-or-later"
    homepage = "https://www.spice-space.org"
    url = "https://gitlab.freedesktop.org/spice/usbredir"
    package_type = "library"

    settings = "os", "compiler", "build_type", "arch"
    options = {"shared": [True, False], "fPIC": [True, False]}
    default_options = {"shared": True, "fPIC": True}

    def config_options(self):
        if self.settings.os == "Windows":
            self.options.rm_safe("fPIC")

    def configure(self):
        if self.options.shared:
            self.options.rm_safe("fPIC")

    def requirements(self):
        self.requires("libusb/1.0.27")

    def layout(self):
        meson_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"][self.version], strip_root=True)

    def generate(self):
        PkgConfigDeps(self).generate()
        tc = MesonToolchain(self)
        tc.project_options["default_library"] = "shared" if self.options.shared else "static"
        tc.project_options["git_werror"] = "disabled"
        tc.project_options["tools"] = "disabled"
        tc.project_options["tests"] = "disabled"
        tc.project_options["fuzzing"] = "disabled"
        tc.generate()

        compiler_executables = self.conf.get(
            "tools.build:compiler_executables", default={}, check_type=dict
        ) or {}
        ar = compiler_executables.get("ar")
        ranlib = compiler_executables.get("ranlib")
        if not ar:
            cc = compiler_executables.get("c") or ""
            bindir = os.path.dirname(cc) if os.path.sep in cc else ""
            if bindir:
                ar_candidate = os.path.join(bindir, "llvm-ar")
                if os.path.isfile(ar_candidate):
                    ar = ar_candidate
                ranlib_candidate = os.path.join(bindir, "llvm-ranlib")
                if os.path.isfile(ranlib_candidate):
                    ranlib = ranlib_candidate
        native_file = os.path.join(self.generators_folder, "conan_meson_native.ini")
        if ar and os.path.isfile(native_file):
            with open(native_file, encoding="utf-8") as handle:
                content = handle.read()
            if "\nar =" not in content and "[binaries]" in content:
                insert = f"[binaries]\nar = '{ar}'\n"
                if ranlib:
                    insert += f"ranlib = '{ranlib}'\n"
                content = content.replace("[binaries]\n", insert, 1)
                with open(native_file, "w", encoding="utf-8") as handle:
                    handle.write(content)

    def build(self):
        meson = Meson(self)
        meson.configure()
        meson.build()

    def package(self):
        meson = Meson(self)
        meson.install()
        copy(self, "COPYING*", self.source_folder, os.path.join(self.package_folder, "licenses"))

    def package_info(self):
        self.cpp_info.libs = ["usbredirhost", "usbredirparser"]
        self.cpp_info.set_property("cmake_file_name", "usbredir")
        self.cpp_info.set_property("cmake_target_name", "usbredir::usbredir")
        self.cpp_info.set_property("pkg_config_name", "libusbredirhost")
