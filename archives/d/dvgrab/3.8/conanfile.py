#!/usr/bin/env python3
"""Conan recipe for dvgrab 3.8 — Digital video capture tool for IEEE 1394 (FireWire) devices.

dvgrab is a command-line tool for capturing DV/HDV video from FireWire camcorders.
It depends on libraw1394, libavc1394, libiec61883, and libdv.

Platform adaptations for HarmonyOS:
  - musl libc lacks pthread_testcancel/pthread_cancel (macro stubs)
  - musl uses __func__ instead of glibc's __ASSERT_FUNCTION
  - HMDFS rejects file creation in umask 077 directories (sed fix in build())
  - autoreconf needed (source from git, no pre-generated configure)
"""
import os

from conan import ConanFile
from conan.tools.files import get, apply_conandata_patches, export_conandata_patches, replace_in_file
from conan.tools.gnu import Autotools, AutotoolsToolchain
from conan.tools.layout import basic_layout


class DvgrabConan(ConanFile):
    name = "dvgrab"
    version = "3.8"
    description = "Digital video capture tool for IEEE 1394 (FireWire) devices"
    license = "GPL-2.0-or-later"
    homepage = "https://github.com/ddennedy/dvgrab"
    url = ""  # CI fills this

    # dvgrab is a command-line application, not a library
    package_type = "application"

    settings = "os", "compiler", "build_type", "arch"

    # Build requirements: autotools needed since source is from git (no pre-generated configure)
    tool_requires = (
        "autoconf/2.72",
        "automake/1.17",
        "libtool/2.4.7",
    )

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        self.requires("libraw1394/2.1.2")
        self.requires("libavc1394/0.5.4")
        self.requires("libiec61883/1.2.0")
        self.requires("libdv/1.0.0")

    def layout(self):
        basic_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def generate(self):
        tc = AutotoolsToolchain(self)
        tc.configure_args.append("--prefix=")
        # Pass dependency paths via pkg-config
        tc.generate()

    def build(self):
        apply_conandata_patches(self)

        # Run autoreconf to generate configure script (source from git repo)
        self.run("autoreconf -fi", env="conanbuild")

        # Fix HMDFS umask 077 issue: HMDFS doesn't allow file creation in
        # directories created with umask 077 (drwx--S--- permissions).
        # autoconf's AS_TMPDIR uses umask 077, so we patch it to umask 022.
        # This affects both configure and config.status scripts.
        for script in ["configure", "config.status"]:
            if os.path.exists(script):
                replace_in_file(self, script, "umask 077", "umask 022")

        autotools = Autotools(self)
        autotools.configure()
        autotools.make(args=["-j2"])

    def package(self):
        autotools = Autotools(self)
        autotools.install()

    def package_info(self):
        # dvgrab is a command-line tool — declare bindirs for the executable
        self.cpp_info.bindirs = ["bin"]
        # No libraries to link against
        self.cpp_info.libs = []
