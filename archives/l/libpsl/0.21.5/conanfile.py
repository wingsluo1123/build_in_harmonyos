#!/usr/bin/env python3
"""Conan recipe for libpsl 0.21.5 on HarmonyOS PC (arm64).

Build system: meson
libpsl is a C library for the Public Suffix List.

IDNA support is disabled (runtime=no) because ICU is not available on OHOS.
The core suffix lookup functionality is preserved.
Static build is used to avoid musl dynamic linker RUNPATH issues.
"""

import os

from conan import ConanFile
from conan.tools.files import get, copy, rmdir, rm
from conan.tools.meson import Meson, MesonToolchain
from conan.tools.gnu import PkgConfigDeps


class LibpslConan(ConanFile):
    name = "libpsl"
    version = "0.21.5"
    description = "C library for the Public Suffix List"
    license = "MIT"
    homepage = "https://github.com/rockdaboot/libpsl"
    url = "https://gitcode.com/OpenHarmonyPCDeveloper/build_in_harmonyos"

    package_type = "library"
    settings = "os", "compiler", "build_type", "arch"
    options = {"shared": [True, False], "fPIC": [True, False]}
    default_options = {"shared": False, "fPIC": True}

    def config_options(self):
        if self.settings.os == "Windows":
            del self.options.fPIC

    def configure(self):
        if self.options.shared:
            self.options.rm_safe("fPIC")
        self.settings.rm_safe("compiler.cppstd")
        self.settings.rm_safe("compiler.libcxx")

    def layout(self):
        self.folders.source = "src"
        self.folders.build = "build"
        self.folders.generators = "build"

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def generate(self):
        tc = MesonToolchain(self)
        # No IDNA runtime (ICU not available on OHOS)
        tc.project_options["runtime"] = "no"
        # Disable tests
        tc.project_options["tests"] = "false"
        tc.generate()
        deps = PkgConfigDeps(self)
        deps.generate()

    def build(self):
        meson = Meson(self)
        meson.configure()
        meson.build()

    def package(self):
        copy(self, "COPYING", src=self.source_folder, dst=os.path.join(self.package_folder, "licenses"))
        copy(self, "LICENSE", src=self.source_folder, dst=os.path.join(self.package_folder, "licenses"))
        meson = Meson(self)
        meson.install()
        rmdir(self, os.path.join(self.package_folder, "lib", "pkgconfig"))
        rmdir(self, os.path.join(self.package_folder, "share"))

    def package_info(self):
        self.cpp_info.set_property("pkg_config_name", "libpsl")
        self.cpp_info.libs = ["psl"]
        if not self.options.shared:
            self.cpp_info.defines = ["PSL_STATIC"]
