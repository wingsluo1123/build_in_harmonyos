#!/usr/bin/env python3
"""Conan recipe — libzmf 0.0.2 (Autotools).

libzmf is a library for reading and converting Zoner Draw and Zebra file
formats. It is part of the Document Liberation Project.

Dependencies (R27: @ohpcd/stable):
  - librevenge/0.0.5      (core dependency, provides librevenge-0.0)
  - boost/1.84.0          (header-only: cstdint, math/constants, optional, variant)
  - zlib/1.3.1            (PNG chunk compression in Zoner format)
  - libpng/1.6.43         (embedded PNG preview decoding)
  - icu/73.2              (Unicode normalization for text records)

Platform adaptations:
  - R26: Static linking for DevBox compatibility (--disable-shared --enable-static)
  - E007/E072: config.guess/config.sub replaced with OHOS-aware versions
  - umask 077 -> 022 in generated configure (HarmonyOS FS limitation)

Build system: Autotools (configure + make). The upstream release tarball
ships a pre-generated `configure` script, so `autoreconf` is NOT required
under normal circumstances. The recipe calls `autoreconf -fi` only when
patches touch configure.ac/Makefile.am; here patches only replace
config.guess/config.sub, so we skip autoreconf and run configure directly.
"""
import os
import shutil

from conan import ConanFile
from conan.tools.files import get, apply_conandata_patches, export_conandata_patches
from conan.tools.gnu import Autotools, AutotoolsToolchain
from conan.tools.layout import basic_layout


class LibzmfConan(ConanFile):
    name = "libzmf"
    version = "0.0.2"
    description = "Library for importing and converting Zoner Draw drawings"
    license = "MPL-2.0"
    homepage = "https://sourceforge.net/projects/libzmf/"
    url = ""  # CI fills this

    settings = "os", "compiler", "build_type", "arch"

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        # R27: Dependencies must reference @ohpcd/stable
        self.requires("librevenge/0.0.5", transitive_headers=True)
        self.requires("boost/1.84.0", transitive_headers=True)
        self.requires("zlib/1.3.1")
        self.requires("libpng/1.6.43")
        self.requires("icu/73.2")

    def layout(self):
        basic_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def generate(self):
        tc = AutotoolsToolchain(self)
        # R26: Build static libraries (DevBox only copies bin/, no lib/)
        tc.configure_args.append("--enable-static")
        tc.configure_args.append("--disable-shared")
        # boost spirit classic has -Wshadow warnings; suppress as non-error
        tc.extra_cxxflags.append("-Wno-error=shadow")
        tc.generate()

    def build(self):
        apply_conandata_patches(self)
        src = self.source_folder

        # E007/E072: Replace config.guess/config.sub with OHOS-aware versions.
        # The upstream release tarball already ships config.guess/config.sub,
        # but they predate OHOS aarch64 recognition. The patch files replace
        # them wholesale; if the patched copy is still missing the OHOS triplet,
        # fall back to the system automake copy.
        am_dir = "/storage/Users/currentUser/usr/local/share/automake-1.17"
        for script in ("config.guess", "config.sub"):
            sys_script = os.path.join(am_dir, script)
            if os.path.exists(sys_script):
                shutil.copy2(sys_script, os.path.join(src, script))

        # Fix: umask 077 -> 022 in generated configure (HarmonyOS FS limitation)
        configure = os.path.join(src, "configure")
        if os.path.exists(configure):
            with open(configure, "r") as f:
                content = f.read()
            content = content.replace("umask 077", "umask 022")
            with open(configure, "w") as f:
                f.write(content)

        autotools = Autotools(self)
        autotools.configure()
        autotools.make()

    def package(self):
        autotools = Autotools(self)
        autotools.install()

    def package_info(self):
        # Headers are in include/libzmf-0.0/libzmf/
        self.cpp_info.includedirs.append("include/libzmf-0.0")
        # Library file is libzmf-0.0.a; strip "lib" prefix for -l flag
        self.cpp_info.libs = ["zmf-0.0"]
        self.cpp_info.set_property("cmake_file_name", "libzmf")
        self.cpp_info.set_property("cmake_target_name", "libzmf::libzmf")
        # libzmf.pc requires librevenge-0.0; propagate via requires
        self.cpp_info.requires = ["librevenge::librevenge"]
