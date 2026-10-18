#!/usr/bin/env python3
"""Conan recipe — infnoise 0.3.3 (manual Makefile build).

infnoise is a hardware TRNG (true random number generator) driver: it reads
entropy from an Infinite Noise USB TRNG (FTDI FT240X) and exposes:
  - libinfnoise (static + shared library with version-script exports)
  - infnoise CLI binary
  - tools/ utility set (passgen/entcheck/hex2bin/bin2hex/flipbits/dice/...)

Build adaptations (patch 0001):
  - git probes replaced with fixed version strings (no .git in release tarball)
  - FTDI_INCLUDE/LDFLAGS injection for the libftdi/libusb Conan dependency
"""
import os

from conan import ConanFile
from conan.tools.files import get, copy, apply_conandata_patches, export_conandata_patches
from conan.tools.layout import basic_layout


class InfnoiseConan(ConanFile):
    name = "infnoise"
    version = "0.3.3"
    description = "Hardware TRNG driver for the Infinite Noise Multiplier (FTDI FT240X USB)"
    license = "CC-BY-3.0"
    homepage = "https://github.com/leetronics/infnoise"
    url = "https://github.com/leetronics/infnoise"

    package_type = "library"

    settings = "os", "compiler", "build_type", "arch"
    options = {"shared": [True, False]}
    default_options = {"shared": False}

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        # FTDI USB driver for the FT240X chip; pulls in libusb/1.0.27 transitively
        self.requires("libftdi/1.5", transitive_headers=True, transitive_libs=True)

    def layout(self):
        basic_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def build(self):
        apply_conandata_patches(self)

        # R33: get compiler from Conan conf, never from shell env vars
        compilers = self.conf.get("tools.build:compiler_executables", default={}, check_type=dict)
        cc = compilers.get("c", "clang")
        ar = compilers.get("ar", "llvm-ar")
        ranlib = compilers.get("ranlib", "llvm-ranlib")

        ftdi = self.dependencies["libftdi"].package_folder
        usb = self.dependencies["libusb"].package_folder
        ftdi_inc = os.path.join(ftdi, "include", "libftdi1")
        usb_inc = os.path.join(usb, "include", "libusb-1.0")
        ftdi_lib = os.path.join(ftdi, "lib")
        usb_lib = os.path.join(usb, "lib")

        ftdi_include = f"-I {ftdi_inc} -I {usb_inc}"
        ldflags = (f"-L{ftdi_lib} -L{usb_lib} "
                   f"-Wl,-rpath-link,{ftdi_lib} -Wl,-rpath-link,{usb_lib}")

        src = self.source_folder
        self.run(
            f"make -C {src}/software -f Makefile.linux "
            f"CC={cc} AR={ar} RANLIB={ranlib} "
            f"FTDI_INCLUDE='{ftdi_include}' LDFLAGS='{ldflags}' -j1",
            cwd=self.source_folder,
        )
        # tools/ set (pure C utilities, no libftdi include required at link)
        self.run(
            f"make -C {src}/software/tools "
            f"CC={cc} CFLAGS='-Wall -Wextra -Werror -std=c99 -O2 -I {ftdi_inc}' -j1",
            cwd=self.source_folder,
        )

    def package(self):
        sof = os.path.join(self.source_folder, "software")
        copy(self, "libinfnoise.h", sof, os.path.join(self.package_folder, "include"))
        copy(self, "libinfnoise.a", sof, os.path.join(self.package_folder, "lib"))
        copy(self, "libinfnoise.so", sof, os.path.join(self.package_folder, "lib"))
        copy(self, "infnoise", sof, os.path.join(self.package_folder, "bin"))
        for tool in ("passgen", "healthcheck", "findlongest", "entcheck",
                     "hex2bin", "bin2hex", "flipbits", "dice"):
            copy(self, tool, os.path.join(sof, "tools"),
                 os.path.join(self.package_folder, "bin"))

    def package_info(self):
        self.cpp_info.libs = ["infnoise"]
        self.cpp_info.requires = ["libftdi::libftdi"]
        self.cpp_info.set_property("cmake_file_name", "libinfnoise")
        self.cpp_info.set_property("cmake_target_name", "libinfnoise::libinfnoise")
        self.cpp_info.set_property("pkg_config_name", "libinfnoise")
        self.cpp_info.bindirs = ["bin"]