#!/usr/bin/env python3
"""Conan recipe for ncurses 6.5."""
import os

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.env import Environment
from conan.tools.files import get, replace_in_file, rm
from conan.tools.gnu import Autotools, AutotoolsToolchain, AutotoolsDeps
from conan.tools.layout import basic_layout


class NcursesConan(ConanFile):
    name = "ncurses"
    version = "6.5"
    description = "Terminal handling and screen optimization library"
    license = "X11"
    homepage = "https://invisible-island.net/ncurses/"
    package_type = "static-library"
    settings = "os", "arch", "compiler", "build_type"
    options = {"fPIC": [True, False]}
    default_options = {"fPIC": True}

    def validate(self):
        if self.settings.os not in ("Linux", "OHOS"):
            raise ConanInvalidConfiguration("ncurses supports Linux and OHOS")

    def layout(self):
        basic_layout(self, src_folder=".")
        self.folders.build = "."

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)
        self._patch_config_scripts()
        replace_in_file(
            self,
            os.path.join(self.source_folder, "configure"),
            "umask 077",
            "umask 022",
        )

    def _patch_config_scripts(self):
        config_guess = os.path.join(self.source_folder, "config.guess")
        replace_in_file(
            self,
            config_guess,
            "\t#if defined(__ANDROID__)\n\tLIBC=android\n\t#else",
            "\t#if defined(__ANDROID__)\n\tLIBC=android\n"
            "\t#elif defined(__OHOS__)\n\tLIBC=ohos\n\t#else",
        )
        replace_in_file(
            self,
            config_guess,
            "case $UNAME_MACHINE:$UNAME_SYSTEM:$UNAME_RELEASE:$UNAME_VERSION in\n"
            "    *:NetBSD:*:*)",
            "case $UNAME_MACHINE:$UNAME_SYSTEM:$UNAME_RELEASE:$UNAME_VERSION in\n"
            "    *:HarmonyOS:*:*)\n"
            "\tcase \"$UNAME_MACHINE\" in\n"
            "\t    aarch64|arm64) MACHINE=aarch64 ;;\n"
            "\t    armv7*|armv8*) MACHINE=arm ;;\n"
            "\t    x86_64|amd64)  MACHINE=x86_64 ;;\n"
            "\t    i?86)          MACHINE=i686 ;;\n"
            "\t    *)             MACHINE=\"$UNAME_MACHINE\" ;;\n"
            "\tesac\n"
            "\tGUESS=${MACHINE}-unknown-linux-ohos\n"
            "\t;;\n"
            "    *:NetBSD:*:*)",
        )

        config_sub = os.path.join(self.source_folder, "config.sub")
        replace_in_file(
            self,
            config_sub,
            "\t\t\tandroid-linux)\n"
            "\t\t\t\tbasic_machine=$field1-unknown\n"
            "\t\t\t\tbasic_os=linux-android\n"
            "\t\t\t\t;;\n"
            "\t\t\t*)",
            "\t\t\tandroid-linux)\n"
            "\t\t\t\tbasic_machine=$field1-unknown\n"
            "\t\t\t\tbasic_os=linux-android\n"
            "\t\t\t\t;;\n"
            "\t\t\tohos-linux)\n"
            "\t\t\t\tbasic_machine=$field1-unknown\n"
            "\t\t\t\tbasic_os=linux-ohos\n"
            "\t\t\t\t;;\n"
            "\t\t\t*)",
        )
        replace_in_file(
            self,
            config_sub,
            "\tgnu* | android* | bsd* | mach* | minix* | genix* | ultrix* | irix* \\\n",
            "\tgnu* | android* | ohos* | bsd* | mach* | minix* | genix* | ultrix* | irix* \\\n",
        )
        replace_in_file(
            self,
            config_sub,
            "\t\t    | linux-relibc*- | linux-uclibc*- )",
            "\t\t    | linux-relibc*- | linux-uclibc*- | linux-ohos*- )",
        )

    def generate(self):
        AutotoolsDeps(self).generate()
        tc = AutotoolsToolchain(self)
        tc.configure_args.extend(
            [
                "--without-debug",
                "--without-ada",
                "--without-cxx",
                "--without-cxx-binding",
                "--without-manpages",
                "--without-progs",
                "--without-tests",
                "--without-shared",
                "--with-normal",
                "--enable-widec",
                "--enable-overwrite",
                "--enable-pc-files",
                "--disable-db-install",
                "--disable-symlinks",
            ]
        )
        if self.options.fPIC:
            tc.extra_cflags.append("-fPIC")
        tc.generate()

    def build(self):
        tmpdir = os.path.join(self.build_folder, "tmp")
        os.makedirs(tmpdir, exist_ok=True)
        env = Environment()
        env.define("TMPDIR", tmpdir)
        with env.vars(self).apply():
            autotools = Autotools(self)
            autotools.configure()
            autotools.make(args=["-j1"])

    def package(self):
        Autotools(self).install()
        rm(self, "*.la", os.path.join(self.package_folder, "lib"))

    def package_info(self):
        self.cpp_info.libs = ["formw", "menuw", "panelw", "ncursesw"]
        self.cpp_info.set_property("cmake_file_name", "ncurses")
        self.cpp_info.set_property("cmake_target_name", "ncurses::ncurses")
        self.cpp_info.set_property("pkg_config_name", "ncursesw")
