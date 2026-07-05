#!/usr/bin/env python3
"""Conan recipe — berkeley-db4 4.8.30 (Autotools)."""
import os

from conan import ConanFile
from conan.tools.files import get, copy, apply_conandata_patches, export_conandata_patches
from conan.tools.gnu import Autotools, AutotoolsToolchain
from conan.tools.layout import basic_layout


class Berkeleydb4Conan(ConanFile):
    name = "berkeley-db4"
    version = "4.8.30"
    description = "Berkeley DB 4.8 - embedded database library"
    license = "MIT"
    homepage = ""
    url = ""  # CI fills this

    settings = "os", "compiler", "build_type", "arch"

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        pass

    def layout(self):
        basic_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def generate(self):
        tc = AutotoolsToolchain(self)
        # R26: Berkeley DB is a system same-name library, disable shared to avoid polluting /lib
        tc.configure_args.append("--disable-shared")
        tc.generate()

    def build(self):
        apply_conandata_patches(self)
        # HMDFS: umask 077 + setgid parent creates 2700 dirs that block file creation.
        # Replace umask 077 with umask 022 in dist/configure (affects both configure
        # and the generated config.status template) so temp dirs get 0755/2755 perms.
        dist_configure = os.path.join(self.source_folder, "dist", "configure")
        if os.path.exists(dist_configure):
            with open(dist_configure, "r") as f:
                content = f.read()
            content = content.replace("umask 077", "umask 022")
            with open(dist_configure, "w") as f:
                f.write(content)
            self.output.info("Patched umask 077 -> umask 022 in dist/configure")

        # Use build folder tmp to avoid external setgid issues
        build_tmp = os.path.join(self.build_folder, "tmp")
        os.makedirs(build_tmp, exist_ok=True)
        os.environ["TMPDIR"] = build_tmp

        autotools = Autotools(self)
        autotools.configure()
        # Berkeley DB builds from build_unix/ directory (created by configure wrapper)
        build_unix = os.path.join(self.source_folder, "build_unix")
        autotools.make(args=["-j1", "-C", build_unix])

    def package(self):
        autotools = Autotools(self)
        # Install from build_unix/ directory
        build_unix = os.path.join(self.source_folder, "build_unix")
        autotools.install(args=["-C", build_unix])

    def package_info(self):
        self.cpp_info.libs = ["db-4.8"]
