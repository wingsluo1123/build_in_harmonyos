#!/usr/bin/env python3
"""Conan recipe for man-db 2.13.1 on HarmonyOS PC (aarch64).

man-db is a manual page reader — a command-line tool, not a library.
Depends on gdbm (database backend) and libpipeline (subprocess pipeline).
"""
import os
import shutil
from conan import ConanFile
from conan.tools.files import get, apply_conandata_patches, export_conandata_patches, replace_in_file
from conan.tools.gnu import Autotools, AutotoolsToolchain, PkgConfigDeps
from conan.tools.env import VirtualBuildEnv
from conan.tools.layout import basic_layout


class MandbConan(ConanFile):
    name = "man-db"
    version = "2.13.1"
    description = "Manual page tools — man, mandb, apropos, whatis, etc."
    license = "GPL-2.0-or-later"
    homepage = "https://www.nongnu.org/man-db/"
    url = ""

    package_type = "application"

    settings = "os", "compiler", "build_type", "arch"
    # No shared/static option — man-db is an application, not a library

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        self.requires("gdbm/1.23")
        self.requires("libpipeline/1.5.8")

    def layout(self):
        basic_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def generate(self):
        # VirtualBuildEnv sets CPPFLAGS/LDFLAGS from dependencies' cpp_info
        VirtualBuildEnv(self).generate()
        tc = AutotoolsToolchain(self)
        # man-db-specific configure options
        tc.configure_args.append("--disable-setuid")
        tc.configure_args.append("--with-systemdtmpfilesdir=no")
        tc.configure_args.append("--with-systemdsystemunitdir=no")
        # R32: platform check for OHOS
        tc.generate()
        # Generate .pc files for dependencies (gdbm, libpipeline)
        PkgConfigDeps(self).generate()

    def build(self):
        apply_conandata_patches(self)
        # Fix umask 077 → 022 for HMDFS compatibility (E011)
        replace_in_file(self, os.path.join(self.source_folder, "configure"),
                        "umask 077", "umask 022")
        # Create nroff wrapper if nroff not available (needed for documentation)
        if not shutil.which("nroff"):
            nroff_path = os.path.join(self.build_folder, "nroff")
            content = '#!/bin/sh\nexec groff -Tascii -mandoc "$@"\n'
            with open(nroff_path, "w") as f:
                f.write(content)
            os.chmod(nroff_path, 0o755)
            # Ensure the wrapper is in PATH
            current_path = os.environ.get("PATH", "")
            os.environ["PATH"] = os.path.dirname(nroff_path) + ":" + current_path
        autotools = Autotools(self)
        autotools.configure()
        autotools.make(args=["-j1"])

    def package(self):
        autotools = Autotools(self)
        autotools.install()

    def package_info(self):
        # man-db is a command-line tool — expose bindirs, not libs
        self.cpp_info.bindirs = ["bin", "sbin"]
        # lib/man-db contains the shared library needed by binaries at runtime
        self.cpp_info.libdirs = ["lib", "lib/man-db"]
        self.cpp_info.libs = []
