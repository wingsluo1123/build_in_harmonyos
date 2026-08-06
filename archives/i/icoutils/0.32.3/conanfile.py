#!/usr/bin/env python3
"""Conan recipe for icoutils — Extract and convert Windows icon/cursor resources.

Autotools build (configure + make). Produces command-line tools: icotool, wrestool,
extresso, genresscript.
"""
import os
import tarfile

from conan import ConanFile
from conan.tools.files import get, apply_conandata_patches, export_conandata_patches, copy
from conan.tools.gnu import Autotools, AutotoolsToolchain, PkgConfigDeps
from conan.tools.layout import basic_layout
from conan.tools.env import VirtualBuildEnv


class IcoutilsConan(ConanFile):
    name = "icoutils"
    version = "0.32.3"
    description = "Extract and convert Windows icon and cursor resources (ICO/CUR/ANI)"
    license = "GPL-3.0"
    homepage = "https://www.nongnu.org/icoutil/"

    package_type = "application"

    settings = "os", "compiler", "build_type", "arch"

    def export_sources(self):
        export_conandata_patches(self)
        # Include source tarball to avoid network download on CI workers
        copy(self, "icoutils-0.32.3.tar.bz2",
             src=os.path.join(self.recipe_folder, "sources"),
             dst=self.export_sources_folder)

    def requirements(self):
        self.requires("libpng/1.6.58")

    def layout(self):
        basic_layout(self)

    def source(self):
        # Try local copy first (from export_sources), fall back to download
        tarball = os.path.join(self.export_sources_folder, "icoutils-0.32.3.tar.bz2")
        if os.path.exists(tarball):
            # Use Python tarfile to avoid toybox tar compatibility issues
            with tarfile.open(tarball, "r:bz2") as tf:
                members = tf.getmembers()
                # strip_root=True: remove first path component
                for m in members:
                    parts = m.name.split("/", 1)
                    if len(parts) > 1:
                        m.name = parts[1]
                    else:
                        m.name = ""
                    if m.name:
                        tf.extract(m, self.source_folder)
        else:
            get(self, **self.conan_data["sources"], strip_root=True)

    def generate(self):
        env = VirtualBuildEnv(self)
        env.generate()
        pkg = PkgConfigDeps(self)
        pkg.generate()
        tc = AutotoolsToolchain(self)
        # Explicitly add libpng lib/include dirs since configure uses AC_CHECK_LIB not pkg-config
        libpng_folder = self.dependencies["libpng"].package_folder
        libpng_libdir = os.path.join(libpng_folder, "lib")
        libpng_incdir = os.path.join(libpng_folder, "include", "libpng16")
        if not os.path.isdir(libpng_incdir):
            libpng_incdir = os.path.join(libpng_folder, "include")
        tc.ldflags.append(f"-L{libpng_libdir}")
        tc.cflags.append(f"-I{libpng_incdir}")
        tc.generate()

    def build(self):
        apply_conandata_patches(self)
        # Create libpng.so symlink: conan installs libpng16.so but configure checks -lpng
        libpng_folder = self.dependencies["libpng"].package_folder
        libpng_libdir = os.path.join(libpng_folder, "lib")
        libpng16_so = os.path.join(libpng_libdir, "libpng16.so")
        libpng_so = os.path.join(libpng_libdir, "libpng.so")
        if os.path.exists(libpng16_so) and not os.path.exists(libpng_so):
            try:
                os.symlink("libpng16.so", libpng_so)
            except OSError:
                pass
        autotools = Autotools(self)
        autotools.configure()
        autotools.make(args=["-j2"])

    def package(self):
        autotools = Autotools(self)
        autotools.install()

    def package_info(self):
        self.cpp_info.bindirs = ["bin"]
        self.cpp_info.libdirs = []
