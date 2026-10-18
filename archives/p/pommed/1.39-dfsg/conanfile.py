#!/usr/bin/env python3
"""Conan recipe — pommed 1.39-dfsg

pommed is the Apple laptops hotkeys handler daemon: it drives the LCD
backlight, the keyboard backlight, the ambient light sensor, CD/DVD ejection,
the beeper and the video output through evdev, sysfs, ACPI and D-Bus.

Build system: plain recursive Makefile.  Only the `pommed` daemon is built;
the `gpomme` (GTK+ 2) and `wmpomme` (X11/WindowMaker) GUI clients that live in
the same tarball are shipped by Debian as separate binary packages and are
deliberately out of scope here (see notes.md).

License: GPL-2.0-or-later
"""
import os
import shutil

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.env import VirtualBuildEnv
from conan.tools.files import (
    apply_conandata_patches,
    copy,
    export_conandata_patches,
    get,
)
from conan.tools.gnu import PkgConfigDeps
from conan.tools.layout import basic_layout


class PommedConan(ConanFile):
    name = "pommed"
    version = "1.39-dfsg"
    description = ("Apple laptops hotkeys handler daemon — LCD/keyboard backlight, "
                   "ambient light, CD eject, beeper and video output")
    license = "GPL-2.0-or-later"
    homepage = "https://sources.debian.org/src/pommed/"
    url = ""  # CI fills this

    package_type = "application"

    settings = "os", "compiler", "build_type", "arch"

    def export_sources(self):
        export_conandata_patches(self)

    def layout(self):
        basic_layout(self)

    def validate(self):
        # R32: OHOS platform compatibility
        if self.settings.os not in ("Linux", "OHOS"):
            raise ConanInvalidConfiguration(f"Unsupported OS: {self.settings.os}")

    def requirements(self):
        self.requires("dbus/1.14.10")
        self.requires("alsa-lib/1.2.16.1")
        self.requires("audiofile/0.3.6")
        self.requires("libconfuse/3.3")
        self.requires("pciutils/3.13.0")

    def generate(self):
        VirtualBuildEnv(self).generate()
        PkgConfigDeps(self).generate()
        self._pkgconfig_aliases()

    def _pkgconfig_aliases(self):
        """The upstream Makefile asks pkg-config for `dbus-1` and `libpci`,
        but PkgConfigDeps names its files after the Conan package ref
        (`dbus.pc`, `pciutils.pc`).  Publish the names the Makefile expects.
        """
        gen = self.generators_folder
        for alias, source in (("dbus-1.pc", "dbus.pc"),
                              ("libpci.pc", "pciutils.pc")):
            src = os.path.join(gen, source)
            dst = os.path.join(gen, alias)
            if os.path.exists(src) and not os.path.exists(dst):
                shutil.copyfile(src, dst)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def build(self):
        apply_conandata_patches(self)

        # R33: the compiler comes from the Conan profile, never a bare shell env
        comp_execs = self.conf.get("tools.build:compiler_executables",
                                   default={}, check_type=dict) or {}
        cc = comp_execs.get("c", "clang")

        # The sysroot ships <sys/inotify.h> and <sys/timerfd.h>, but the
        # Makefile probes the *build host* /usr/include for them; that path
        # does not exist here, so the Makefile would fall back to the bundled
        # syscall-number shims, which `#error` out on aarch64.  Blanking these
        # make variables keeps the real sysroot headers in use.
        #
        # LDFLAGS=-lc++ : libaudiofile.a carries C++ objects, so the final link
        #                 needs libc++ (the Makefile links with the C driver).
        # CPPFLAGS=-fcommon : 2011-era C relying on GCC<10 tentative
        #                 definitions (e.g. `lcd_bck_info` is defined in three
        #                 translation units and would otherwise be a duplicate
        #                 symbol with clang's default -fno-common).
        gen = self.generators_folder
        self.run(
            f'PKG_CONFIG_PATH="{gen}" make -j1 -C pommed CC="{cc}"'
            f' CPPFLAGS="-fcommon" LDFLAGS="-lc++"'
            f' INOTIFY_CFLAGS= TIMERFD_CFLAGS=',
            cwd=self.source_folder,
        )

    def package(self):
        copy(self, "pommed", src=os.path.join(self.source_folder, "pommed"),
             dst=os.path.join(self.package_folder, "bin"))
        copy(self, "COPYING", src=self.source_folder,
             dst=os.path.join(self.package_folder, "licenses"))
        copy(self, "pommed.1", src=self.source_folder,
             dst=os.path.join(self.package_folder, "share", "man", "man1"))
        # Beep samples (BEEP_DEFAULT_FILE is compiled in as
        # /usr/share/pommed/goutte.wav) and the shipped sample configurations.
        copy(self, "*.wav", src=os.path.join(self.source_folder, "pommed", "data"),
             dst=os.path.join(self.package_folder, "share", "pommed"))
        copy(self, "pommed.conf.*", src=self.source_folder,
             dst=os.path.join(self.package_folder, "share", "pommed"))

    def package_info(self):
        # A daemon, not a library.
        self.cpp_info.libs = []
        self.cpp_info.includedirs = []
        self.cpp_info.libdirs = []
        self.cpp_info.bindirs = ["bin"]
