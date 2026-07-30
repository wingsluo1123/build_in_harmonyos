#!/usr/bin/env python3
"""Conan recipe for smpeg2 2.0.0."""

import os

from conan import ConanFile
from conan.tools.env import VirtualBuildEnv
from conan.tools.files import apply_conandata_patches, copy, export_conandata_patches, get
from conan.tools.gnu import Autotools, AutotoolsDeps, AutotoolsToolchain
from conan.tools.layout import basic_layout


class Smpeg2Conan(ConanFile):
    name = "smpeg2"
    version = "2_0_0"
    description = "SDL2 MPEG audio/video decoding library"
    license = "LGPL-2.0-or-later"
    homepage = "https://icculus.org/smpeg/"
    url = "https://gitcode.com/OpenHarmonyPCDeveloper/build_in_harmonyos"
    package_type = "library"

    settings = "os", "compiler", "build_type", "arch"
    options = {"shared": [True, False], "fPIC": [True, False]}
    default_options = {"shared": False, "fPIC": True}

    def config_options(self):
        if self.settings.os == "Windows":
            self.options.rm_safe("fPIC")

    def configure(self):
        if self.options.shared:
            self.options.rm_safe("fPIC")

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        self.requires("sdl2/2.30.10")

    def layout(self):
        basic_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def generate(self):
        AutotoolsDeps(self).generate()
        VirtualBuildEnv(self).generate()
        tc = AutotoolsToolchain(self)
        sdl2_config = os.path.join(
            self.dependencies["sdl2"].package_folder, "bin", "sdl2-config"
        ).replace("\\", "/")
        tc.configure_args.extend(["--disable-rpath", "--disable-mmx", f"SDL_CONFIG={sdl2_config}"])
        if self.options.shared:
            tc.configure_args.extend(["--enable-shared", "--disable-static"])
        else:
            tc.configure_args.extend(["--enable-static", "--disable-shared"])
        tc.generate()

    def build(self):
        apply_conandata_patches(self)
        self.run("sh autogen.sh", cwd=self.source_folder)
        autotools = Autotools(self)
        autotools.configure()
        autotools.make(args=["-j1"])

    def package(self):
        autotools = Autotools(self)
        autotools.install()
        copy(
            self,
            "COPYING",
            src=self.source_folder,
            dst=os.path.join(self.package_folder, "licenses"),
        )

    def package_info(self):
        self.cpp_info.libs = ["smpeg2"]
        self.cpp_info.requires = ["sdl2::sdl2"]
        self.cpp_info.includedirs.append(
            os.path.join(self.dependencies["sdl2"].package_folder, "include", "SDL2")
        )
        self.cpp_info.set_property("cmake_file_name", "smpeg2")
        self.cpp_info.set_property("cmake_target_name", "smpeg2::smpeg2")
        self.cpp_info.set_property("pkg_config_name", "smpeg2")
        if self.settings.os in ("Linux", "OHOS"):
            self.cpp_info.system_libs = ["m", "pthread"]
