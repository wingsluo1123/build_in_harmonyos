#!/usr/bin/env python3
"""Conan recipe for Berkeley DB 5.3.28.

Berkeley DB uses autotools but requires running configure from the
build_unix/ subdirectory: cd build_unix && ../dist/configure --prefix=...
The source tarball contains a src/ directory with the actual source code.

R26: Not a system-name library, so shared builds are fine.
"""
from conan import ConanFile
from conan.tools.files import get, apply_conandata_patches, export_conandata_patches
from conan.tools.gnu import Autotools, AutotoolsToolchain
from conan.tools.layout import basic_layout
import os


class Berkeleydb5Conan(ConanFile):
    name = "berkeley-db5"
    version = "5.3.28"
    description = "Berkeley DB 5.3.28 — embedded key/value database library"
    license = "Sleepycat"  # Berkeley DB Sleepycat Public License
    homepage = "https://www.oracle.com/database/technologies/related/berkeleydb.html"
    url = ""  # CI fills this

    package_type = "library"

    settings = "os", "compiler", "build_type", "arch"
    options = {"shared": [True, False]}
    default_options = {"shared": False}

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
        # Berkeley DB needs to be configured from build_unix/ directory
        # using ../dist/configure
        tc.configure_args.append("--enable-static")
        tc.configure_args.append("--enable-shared")
        tc.configure_args.append("--with-repmgr-ssl=no")
        # HMDFS compatibility: avoid umask 077 temp dir issue
        tc.extra_defines.append("TMPDIR=${TMPDIR:-/tmp}")
        tc.generate()

    def build(self):
        apply_conandata_patches(self)
        autotools = Autotools(self)
        # Berkeley DB requires configure to be run from build_unix/
        src_dir = self.source_folder
        build_dir = os.path.join(src_dir, "build_unix")
        os.makedirs(build_dir, exist_ok=True)
        self.run(f"cd {build_dir} && ../dist/configure --prefix={self.prefix} "
                 f"--enable-static --enable-shared --with-repmgr-ssl=no",
                 env="conanbuild")
        self.run(f"cd {build_dir} && make -j1", env="conanbuild")
        self.run(f"cd {build_dir} && make install DESTDIR={self.package_folder}",
                 env="conanbuild")

    def package(self):
        # build() already handles install via DESTDIR
        pass

    def package_info(self):
        self.cpp_info.libs = ["db-5.3"]
        self.cpp_info.includedirs = ["include"]
        self.cpp_info.libdirs = ["lib"]
