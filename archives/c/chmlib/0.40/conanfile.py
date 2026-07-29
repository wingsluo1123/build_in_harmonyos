#!/usr/bin/env python3
"""
Conan recipe for chmlib v0.40 — OHOS (OpenHarmony) aarch64 adaptation.

Build system: autotools (autoreconf + configure + make).
GitHub source lacks pre-generated configure; autoreconf generates it.
OHOS platform fixes (config.guess / config.sub / umask) applied via sed.
"""
from conan import ConanFile
from conan.tools.files import get, apply_conandata_patches, export_conandata_patches
from conan.tools.gnu import Autotools, AutotoolsToolchain
from conan.tools.layout import basic_layout


class ChmlibConan(ConanFile):
    name = "chmlib"
    version = "0.40"
    description = "Library for reading Microsoft ITSS/CHM format files"
    license = "LGPL-2.1-or-later"
    homepage = "https://github.com/jedwing/CHMLib"
    url = "https://github.com/jedwing/CHMLib"

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
        if not self.options.shared:
            tc.configure_args.append("--enable-static")
            tc.configure_args.append("--disable-shared")
        tc.configure_args.append("--enable-examples=no")
        tc.generate()

    def build(self):
        src = self.source_folder

        # GitHub auto-tarball lacks configure; generate it
        autotools = Autotools(self)
        autotools.autoreconf(args=["-fi"])

        # E007: Fix config.guess to recognise HarmonyOS
        self.run(
            "sed -i '/^case \"\\${UNAME_MACHINE}:\\${UNAME_SYSTEM}:\\${UNAME_RELEASE}:\\${UNAME_VERSION}\" in$/i\\\n"
            "    *:HarmonyOS:*:*) echo ${UNAME_MACHINE}-unknown-linux-ohos; exit 0;;' "
            "config.guess",
            cwd=src
        )

        # E007: Fix config.sub — add linux-ohos in three places
        self.run(
            "sed -i 's/| linux-gnu\\* | linux-dietlibc/| linux-gnu* | linux-ohos* | linux-dietlibc/' "
            "config.sub",
            cwd=src
        )
        self.run(
            "sed -i 's/| -linux-gnu\\* | -linux-newlib/| -linux-gnu* | -linux-ohos* | -linux-newlib/' "
            "config.sub",
            cwd=src
        )
        self.run(
            "sed -i '/^-linux\\*)$/i\\\n"
            "\t-linux-ohos)\\n"
            "\t\tos=-linux-ohos\\n"
            "\t\t;;' "
            "config.sub",
            cwd=src
        )

        # E097: HMDFS setgid — fix umask 077 → 022 for configure temp files
        self.run(
            "sed -i 's/umask 077/umask 022/g' configure",
            cwd=src
        )

        # Apply source-level patch (aarch64 types in chm_lib.c)
        apply_conandata_patches(self)

        autotools.configure()
        autotools.make(args=["-j1"])

    def package(self):
        autotools = Autotools(self)
        autotools.install()

    def package_info(self):
        self.cpp_info.libs = ["chm"]
