#!/usr/bin/env python3
"""Conan recipe — libtcd 2.2.7 (Tide Constituent Data format library, C/autotools) on HarmonyOS PC."""

import os

from conan import ConanFile
from conan.tools.files import apply_conandata_patches, copy, get, replace_in_file
from conan.tools.gnu import Autotools, AutotoolsToolchain
from conan.tools.layout import basic_layout


class LibtcdConan(ConanFile):
    name = "libtcd"
    version = "2.2.7"
    description = "Library for reading and writing Tide Constituent Data (TCD) format files"
    license = "Public Domain"
    homepage = "https://flaterco.com/files/xtide/"
    url = "https://flaterco.com/files/xtide/"

    package_type = "library"

    settings = "os", "compiler", "build_type", "arch"
    options = {"shared": [True, False]}
    default_options = {"shared": False}

    def export_sources(self):
        copy(self, "patches/*", src=self.recipe_folder, dst=self.export_sources_folder)

    def requirements(self):
        pass

    def layout(self):
        basic_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def generate(self):
        tc = AutotoolsToolchain(self)
        if not self.options.shared:
            tc.configure_args.append("--enable-static")
            tc.configure_args.append("--disable-shared")
        tc.generate()

    def build(self):
        apply_conandata_patches(self)
        sf = self.source_folder

        # E005: Patch config.guess (2014) to recognize HarmonyOS platform
        cg = os.path.join(sf, "config.guess")
        replace_in_file(self, cg, "Linux|GNU|GNU/*)", "Linux|GNU|GNU/*|HarmonyOS)")
        replace_in_file(self, cg,
            "    aarch64:Linux:*:*)\n\techo ${UNAME_MACHINE}-unknown-linux-${LIBC}\n\texit ;;",
            "    aarch64:Linux:*:*)\n\techo ${UNAME_MACHINE}-unknown-linux-${LIBC}\n\texit ;;\n    aarch64:HarmonyOS:*:*)\n\techo aarch64-unknown-linux-ohos\n\texit ;;")

        # E005: Patch config.sub (2014) to accept linux-ohos as valid OS
        cs = os.path.join(sf, "config.sub")
        replace_in_file(self, cs,
            "linux-musl* | linux-uclibc* | uclinux-uclibc* | uclinux-gnu* | kfreebsd*-gnu* | \\",
            "linux-musl* | linux-uclibc* | linux-ohos* | uclinux-uclibc* | uclinux-gnu* | kfreebsd*-gnu* | \\")
        replace_in_file(self, cs,
            "| -mingw32* | -mingw64* | -linux-gnu* | -linux-android* \\",
            "| -mingw32* | -mingw64* | -linux-gnu* | -linux-android* | -linux-ohos* \\")

        # E011: HMDFS umask 077 creates temp dirs that the process can't write to.
        replace_in_file(self, os.path.join(sf, "configure"), "umask 077", "umask 022")

        autotools = Autotools(self)
        autotools.configure()
        autotools.make(args=["-j1"])

    def package(self):
        autotools = Autotools(self)
        autotools.install()

    def package_info(self):
        self.cpp_info.libs = ["tcd"]
