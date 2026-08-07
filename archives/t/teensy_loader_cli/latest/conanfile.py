#!/usr/bin/env python3
"""Conan recipe for teensy_loader_cli - Teensy USB firmware loader CLI."""
import os

from conan import ConanFile
from conan.tools.files import (
    apply_conandata_patches,
    copy,
    export_conandata_patches,
    get,
)
from conan.tools.gnu import AutotoolsToolchain
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

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        # The USB backend is a real libusb 1.0 port (see the conandata patch),
        # so the CLI links against the packaged libusb instead of a stub.
        self.requires("libusb/1.0.27")

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)
        apply_conandata_patches(self)

    def generate(self):
        # AutotoolsToolchain exposes the profile compiler / flags through the
        # conanbuild environment (CC, CFLAGS, LDFLAGS, ...).
        AutotoolsToolchain(self).generate()

    def build(self):
        # Build the single-file CLI directly against the packaged libusb 1.0.
        # We read the dependency's real include / lib dirs so the recipe does
        # not depend on any fixed install layout.  libusb ships its header as
        # <libusb-1.0/libusb.h>, so add that sub-directory to the include path.
        libusb = self.dependencies["libusb"].cpp_info.aggregated_components()

        inc_flags = []
        for d in libusb.includedirs:
            inc_flags.append(f'-I"{d}"')
            sub = os.path.join(d, "libusb-1.0")
            if os.path.isdir(sub):
                inc_flags.append(f'-I"{sub}"')

        lib_dir_flags = [f'-L"{d}"' for d in libusb.libdirs]
        lib_flags = [f"-l{name}" for name in (libusb.libs or ["usb-1.0"])]
        # Static libusb pulls in udev / pthread on Linux-like targets.
        sys_lib_flags = [f"-l{name}" for name in libusb.system_libs]

        os.makedirs(self.build_folder, exist_ok=True)
        output = os.path.join(self.build_folder, "teensy_loader_cli")
        cmd = (
            "${CC:-clang} ${CFLAGS:-} -DUSE_LIBUSB "
            + " ".join(inc_flags)
            + f' -o "{output}" teensy_loader_cli.c '
            + " ".join(lib_dir_flags + lib_flags + sys_lib_flags)
            + " ${LDFLAGS:-}"
        )
        self.run(cmd, env="conanbuild", cwd=self.source_folder)

    def package(self):
        copy(self, "teensy_loader_cli",
             src=self.build_folder,
             dst=os.path.join(self.package_folder, "bin"))

    def package_info(self):
        self.cpp_info.libs = []
        self.cpp_info.bindirs = ["bin"]
        self.runenv_info.append_path(
            "PATH", os.path.join(self.package_folder, "bin"))
