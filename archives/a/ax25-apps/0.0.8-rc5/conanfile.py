#!/usr/bin/env python3
"""Conan recipe — ax25-apps 0.0.8-rc5 (Autotools).

AX.25 amateur radio protocol user programs: call, listen, ax25ipd, ax25rtd, ax25rtctl, ax25mond.
"""
from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.files import get, apply_conandata_patches, export_conandata_patches, replace_in_file
from conan.tools.gnu import Autotools, AutotoolsToolchain
from conan.tools.layout import basic_layout
import os


class Ax25AppsConan(ConanFile):
    name = "ax25-apps"
    version = "0.0.8-rc5"
    description = "AX.25 amateur radio protocol user programs (call, listen, ax25ipd, ax25rtd)"
    license = "GPL-2.0-or-later"
    homepage = "https://linux-ax25.in-berlin.de/wiki/Ax25apps"
    url = "https://linux-ax25.in-berlin.de/wiki/Ax25apps"

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
        # R33: All compiler flags from Conan toolchain, not shell env vars
        # Manually add libax25 dependency paths (AutotoolsToolchain doesn't auto-include them)
        libax25 = self.dependencies["libax25"]
        pkg_folder = libax25.package_folder
        if pkg_folder:
            tc.extra_cflags.append(f"-I{os.path.join(pkg_folder, 'include')}")
            tc.extra_ldflags.append(f"-L{os.path.join(pkg_folder, 'lib')}")
        # System libraries (ncurses, libiconv) at standard OHOS user prefix
        sys_prefix = "/storage/Users/currentUser/usr/local"
        tc.extra_cflags.append(f"-I{sys_prefix}/include")
        tc.extra_ldflags.append(f"-L{sys_prefix}/lib")
        tc.generate()

    def build(self):
        # Apply patches from conandata.yml (io.c, call.h, yapp.c)
        apply_conandata_patches(self)

        # Add -liconv to call link (call binary uses iconv functions)
        # This is not a patch because it modifies Makefile.am which needs autoreconf
        replace_in_file(self, "call/Makefile.am",
                        "call_LDADD = $(NCURSES_LIB) $(AX25_LIB)",
                        "call_LDADD = $(NCURSES_LIB) $(AX25_LIB) -liconv")

        # Run autoreconf to generate configure and Makefile.in
        self.run("autoreconf -fi", env="conanbuild")

        # E129: Fix umask 077 -> umask 022 in generated configure (HMDFS setgid issue)
        # Must be applied AFTER autoreconf generates configure
        replace_in_file(self, "configure", "umask 077", "umask 022")

        # E165: Fix shebang in generated configure
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
