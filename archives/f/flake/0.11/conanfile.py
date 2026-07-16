#!/usr/bin/env python3
"""Conan recipe — flake 0.11 (custom ffmpeg-style configure)"""

import os

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.files import get, apply_conandata_patches, export_conandata_patches, replace_in_file
from conan.tools.env import VirtualBuildEnv
from conan.tools.layout import basic_layout


class FlakeConan(ConanFile):
    name = "flake"
    version = "0.11"
    description = "FLAC audio encoder — lossless WAV to FLAC encoding"
    license = "LGPL-2.1"
    homepage = "https://sourceforge.net/projects/flake-enc/"
    url = "https://gitcode.com/OpenHarmonyPCDeveloper/build_in_harmonyos"

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
        env = VirtualBuildEnv(self)
        env.generate()

    def validate(self):
        if self.settings.os not in ("Linux", "OHOS"):
            raise ConanInvalidConfiguration("flake only supports Linux/OHOS")

    def build(self):
        apply_conandata_patches(self)
        src = self.source_folder
        # Fix shebang for OHOS (E165: /bin/sh -> /system/bin/sh)
        configure_path = os.path.join(src, "configure")
        replace_in_file(self, configure_path, "#!/bin/sh", "#!/system/bin/sh")
        # flake uses custom ffmpeg-style configure, not standard autotools
        # R33: compiler from Conan settings, not raw shell env vars
        cc = str(self.settings.compiler)
        ar = "llvm-ar" if self.settings.os == "OHOS" else "ar"
        ranlib = "llvm-ranlib" if self.settings.os == "OHOS" else "ranlib"
        self.run(
            f'cd "{src}" && ./configure --prefix="" --cc={cc} --ar={ar} '
            f'--ranlib={ranlib} --extra-cflags="-fPIC -O2"'
        )
        # Sequential build: parallel make has race condition
        # (progs target depends on libflake.a, but all target runs them in parallel)
        self.run(f'cd "{src}" && make lib')
        self.run(f'cd "{src}" && make progs')
        self.run(f'cd "{src}" && make utils')

    def package(self):
        src = self.source_folder
        self.run(f'cd "{src}" && make install DESTDIR="{self.package_folder}"')

    def package_info(self):
        self.cpp_info.libs = ["flake"]
        self.cpp_info.system_libs = ["m"]
        self.cpp_info.bindirs = ["bin"]
