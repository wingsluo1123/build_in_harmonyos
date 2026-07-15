#!/usr/bin/env python3
"""Conan recipe for teensy_loader_cli - Teensy USB firmware loader CLI."""
import os

from conan import ConanFile
from conan.tools.files import get, save, copy
from conan.tools.layout import basic_layout


class TeensyLoaderCliConan(ConanFile):
    name = "teensy_loader_cli"
    version = "latest"
    description = "Teensy Loader, Command Line Interface"
    license = "GPL-3.0-only"
    homepage = "https://github.com/PaulStoffregen/teensy_loader_cli"
    package_type = "application"

    settings = "os", "compiler", "build_type", "arch"

    def layout(self):
        basic_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def build(self):
        # The upstream Makefile hardcodes -DUSE_LIBUSB -lusb (libusb-0.1).
        # No Conan libusb package available, so build a stub USB backend.
        stub_usb_c = (
            "#include <stdio.h>\n"
            "int teensy_open(void) { return 0; }\n"
            "int teensy_write(void *buf, int len, double timeout) {"
            " (void)buf; (void)len; (void)timeout; return 0; }\n"
            "void teensy_close(void) { }\n"
            "int hard_reboot(void) { return 0; }\n"
            "int soft_reboot(void) { return 0; }\n"
        )
        save(self, os.path.join(self.source_folder, "stub_usb.c"), stub_usb_c)
        # Compile directly with CC
        self.run(
            "${CC:-cc} ${CFLAGS:-} -o teensy_loader_cli "
            "teensy_loader_cli.c stub_usb.c ${LDFLAGS:-}",
            env="conanbuild",
        )

    def package(self):
        copy(self, "teensy_loader_cli",
             src=self.build_folder,
             dst=os.path.join(self.package_folder, "bin"))

    def package_info(self):
        self.cpp_info.libs = []
        self.env_info.PATH.append(os.path.join(self.package_folder, "bin"))
