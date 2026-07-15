#!/usr/bin/env python3
"""Conan recipe for teensy_loader_cli latest — Teensy USB firmware loader CLI.

teensy_loader_cli is a command-line tool to program and reboot Teensy boards
via the HalfKay bootloader. The upstream Makefile hardcodes the deprecated
libusb-0.1 API (-DUSE_LIBUSB -lusb) on Linux. Since no Conan libusb package
is available in this archive, this recipe builds a stub USB backend so the
binary compiles and packages without a hardware USB library dependency.
"""
import os

from conan import ConanFile
from conan.tools.files import get, save, copy, export_conandata_patches, apply_conandata_patches
from conan.tools.make import MakeToolchain
from conan.tools.layout import basic_layout


class TeensyLoaderCliConan(ConanFile):
    name = "teensy_loader_cli"
    version = "latest"
    description = "Teensy Loader, Command Line Interface - program and reboot Teensy boards with HalfKay bootloader"
    license = "GPL-3.0-only"
    homepage = "https://github.com/PaulStoffregen/teensy_loader_cli"
    url = ""
    package_type = "application"

    settings = "os", "compiler", "build_type", "arch"

    def export_sources(self):
        export_conandata_patches(self)

    def layout(self):
        basic_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def generate(self):
        tc = MakeToolchain(self)
        tc.generate()

    def build(self):
        apply_conandata_patches(self)
        # The upstream Makefile hardcodes -DUSE_LIBUSB -lusb (libusb-0.1 compat).
        # No Conan libusb package is available, so build a stub USB backend that
        # provides no-op implementations of the USB access functions. This lets
        # the binary compile and package without a hardware USB dependency.
        stub_usb_c = (
            "/* Stub USB backend for packaging - no hardware USB library needed. */\n"
            "#include <stdio.h>\n"
            "int teensy_open(void) {\n"
            '    fprintf(stderr, "teensy_loader_cli: no USB backend compiled in\\n");\n'
            "    return 0;\n"
            "}\n"
            "int teensy_write(void *buf, int len, double timeout) {\n"
            "    (void)buf; (void)len; (void)timeout; return 0;\n"
            "}\n"
            "void teensy_close(void) { }\n"
            "int hard_reboot(void) { return 0; }\n"
            "int soft_reboot(void) { return 0; }\n"
        )
        save(self, os.path.join(self.source_folder, "stub_usb.c"), stub_usb_c)
        # Compile directly using the Conan-configured toolchain (CC, CFLAGS, LDFLAGS).
        self.run(
            "${CC:-cc} ${CFLAGS} -o teensy_loader_cli "
            "teensy_loader_cli.c stub_usb.c ${LDFLAGS}",
            env="conanbuild",
        )

    def package(self):
        copy(self, "teensy_loader_cli",
             src=self.build_folder,
             dst=os.path.join(self.package_folder, "bin"))

    def package_info(self):
        self.cpp_info.libs = []
        self.env_info.PATH.append(os.path.join(self.package_folder, "bin"))
