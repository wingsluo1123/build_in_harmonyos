#!/usr/bin/env python3
"""Conan recipe — ax25-apps 0.0.8-rc5 (Autotools).

AX.25 amateur radio protocol user programs: call, listen, ax25ipd, ax25rtd,
ax25rtctl, ax25mond.
"""
import os

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.files import get, apply_conandata_patches, export_conandata_patches, replace_in_file
from conan.tools.gnu import Autotools, AutotoolsToolchain, AutotoolsDeps
from conan.tools.layout import basic_layout


class Ax25AppsConan(ConanFile):
    name = "ax25-apps"
    version = "0.0.8-rc5"
    description = "AX.25 amateur radio protocol user programs (call, listen, ax25ipd, ax25rtd, ax25rtctl, ax25mond)"
    license = "GPL-2.0-or-later"
    homepage = "https://linux-ax25.in-berlin.de/wiki/Ax25apps"
    url = ""  # CI fills this

    package_type = "application"

    settings = "os", "compiler", "build_type", "arch"

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        self.requires("libax25/0.0.12-rc5")

    def layout(self):
        # In-source build required because autoreconf needs configure.ac
        basic_layout(self, src_folder=".")
        self.folders.build = "."

    def validate(self):
        # R32: settings.os must be in ("Linux", "OHOS")
        if self.settings.os not in ("Linux", "OHOS"):
            raise ConanInvalidConfiguration(f"Only Linux/OHOS supported, got {self.settings.os}")

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def generate(self):
        tc = AutotoolsToolchain(self)
        # R33: All compiler flags from Conan toolchain, not shell env vars.
        # libax25 dependency paths are handled automatically by AutotoolsDeps.
        # For system libraries (ncurses, libiconv) that are not in the OHOS
        # SDK sysroot, detect the user-installed prefix dynamically.
        # The OHOS SDK sysroot does not include ncurses or libiconv, so these
        # are installed in the user's local prefix ($HOME/usr/local).
        home = os.path.expanduser("~")
        sys_prefix = os.path.join(home, "usr", "local")
        if os.path.isdir(os.path.join(sys_prefix, "lib")):
            tc.extra_cflags.append(f"-I{os.path.join(sys_prefix, 'include')}")
            tc.extra_ldflags.append(f"-L{os.path.join(sys_prefix, 'lib')}")
        tc.generate()

        # AutotoolsDeps generates flags for conan dependencies (libax25)
        deps = AutotoolsDeps(self)
        deps.generate()

    def build(self):
        # Apply patches from conandata.yml (io.c, call.h, yapp.c, Makefile.am)
        apply_conandata_patches(self)

        # Run autoreconf to generate configure and Makefile.in from patched Makefile.am
        self.run("autoreconf -fi", env="conanbuild")

        # E129: Fix umask 077 -> umask 022 in generated configure (HMDFS setgid issue)
        replace_in_file(self, "configure", "umask 077", "umask 022")

        # E165: Fix shebang in generated configure for OHOS
        replace_in_file(self, "configure", "#! /bin/sh", "#!/system/bin/sh")

        autotools = Autotools(self)
        autotools.configure()
        autotools.make(args=["-j1"])

    def package(self):
        autotools = Autotools(self)
        autotools.install()

    def package_info(self):
        # Application package: binaries in bin/ and sbin/
        self.cpp_info.bindirs = ["bin", "sbin"]
        # System libraries needed at runtime
        self.cpp_info.system_libs = ["ncursesw", "iconv"]
