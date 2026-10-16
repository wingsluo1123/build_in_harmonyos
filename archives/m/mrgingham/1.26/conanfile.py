#!/usr/bin/env python3
"""Conan recipe — mrgingham 1.26 (chessboard corner finder) on OHOS/aarch64.

mrgingham (Dima Kogan) finds chessboard corners / grids of circles in images for
camera-calibration pipelines.  It ships a C++ shared library (libmrgingham) and
a small set of command-line tools, built by its own hand-written Makefile which
is driven by the upstream "mrbuild" Makefile framework.

Platform notes (OHOS, aarch64, clang 15, libc++, native build = host):

* Build system is a plain Makefile.  `choose_mrbuild.mk` requires the `mrbuild`
  Makefile framework (https://github.com/dkogan/mrbuild), which mrgingham does
  not vendor and which is not published as a Conan package.  source() downloads
  the exact release that choose_mrbuild.mk pins (V := 1.13) into
  <source>/mrbuild/; choose_mrbuild.mk prefers that local checkout.  No network
  is needed at build time.

* The OHOS SDK links with LLVM lld, which does not implement GNU ld's
  `-Wl,--default-symver` that mrbuild's `Makefile.common.footer` appends to the
  full shared-object link (`ld.lld: error: unknown argument '--default-symver'`).
  patches/0001 removes that flag at its source, in the vendored footer.  See
  notes.md for why the flag is dropped unconditionally rather than behind a
  "is the linker lld?" probe: such a probe re-execs the linker at Makefile-parse
  time and silently stops matching on CI workers (observed on the platform CI),
  which would let `--default-symver` through again.

* On CI workers the SDK lld itself needs `libxml2.so.16` from the SDK's
  `llvm/lib` (its RUNPATH is `$ORIGIN/../lib`).  An ambient/Conan
  `LD_LIBRARY_PATH` entry pointing at a different `libxml2.so.16` shadows it and
  lld aborts with "Error loading shared library libxml2.so.16 ... symbol not
  found" (reproduced on-device).  `_sdk_llvm_libdir()` + the `LD_LIBRARY_PATH`
  prefix keep the SDK's own libxml2 first for every lld invocation.

* The default goal `all` also builds two optional artefacts that are NOT
  available on OHOS, so the recipe builds the explicit library + tool targets
  instead (see notes.md):
    - the CPython extension `mrgingham$(PY_EXT_SUFFIX)` needs NumPy headers
      (numpy/arrayobject.h); there is no NumPy port for OHOS.
    - README.org needs `mawk`, which is not installed on OHOS (only awk/gawk).

* `VERSION=1.26` is injected.  mrgingham's Makefile leaves VERSION to mrbuild's
  default ($(ABI_VERSION).$(TAIL_VERSION) = "2.1"); the ABI/TAIL numbers name
  the shared object (libmrgingham.so.2.1) and are untouched, while VERSION is
  only what the tools/manpages report.  It must match the upstream tag v1.26.

* R33: CC/CXX/CPPFLAGS come from Conan conf / dependency package folders, never
  from the ambient shell.

* `-lpthread` (hard-coded by the upstream Makefile) resolves to the OHOS SDK
  sysroot's libpthread.a.
"""

import glob
import os
import shutil

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.files import (apply_conandata_patches, copy,
                               export_conandata_patches, get)
from conan.tools.gnu import PkgConfigDeps
from conan.tools.layout import basic_layout

# Library + tool targets that are actually buildable on OHOS (see module
# docstring for why `all` is not used).
BUILD_TARGETS = [
    "libmrgingham.so.2.1",
    "mrgingham",
    "mrgingham-from-image",
    "test-dump-chessboard-corners",
    "test-dump-blobs",
    "test-find-grid-from-points",
]

# mrbuild's DIST_BIN (upstream install set).
DIST_BIN = [
    "mrgingham",
    "mrgingham-observe-pixel-uncertainty",
    "mrgingham-rotate-corners",
]

# mrbuild's DIST_INCLUDE.
DIST_INCLUDE = ["mrgingham.hh", "point.hh"]


class MrginghamConan(ConanFile):
    name = "mrgingham"
    version = "1.26"
    description = ("mrgingham - find chessboard corners and grids of circles "
                   "in images, for camera calibration")
    license = "LGPL-2.1-or-later"
    homepage = "https://github.com/dkogan/mrgingham"
    url = "https://gitcode.com/OpenHarmonyPCDeveloper/build_in_harmonyos"

    package_type = "library"
    settings = "os", "arch", "compiler", "build_type"
    # mrbuild only builds shared libraries ("We don't build static libraries"),
    # so `shared` is declared for package_type=library and pinned to True.
    options = {"shared": [True, False]}
    default_options = {"shared": True}

    def validate(self):
        if self.settings.os not in ("Linux", "OHOS"):
            raise ConanInvalidConfiguration(
                "mrgingham/1.26 in this recipe is a HarmonyOS PC adaptation")
        if not self.options.shared:
            raise ConanInvalidConfiguration(
                "mrgingham builds a shared library only (mrbuild)")

    def export_sources(self):
        export_conandata_patches(self)

    def layout(self):
        basic_layout(self, src_folder=".")

    def requirements(self):
        # Public header mrgingham.hh includes <opencv2/core/core.hpp>, so OpenCV
        # headers/libs must propagate to consumers (R: transitive deps).
        self.requires("opencv/4.12.0", transitive_headers=True, transitive_libs=True)
        # find_grid.cc uses Boost.Polygon's Voronoi diagram (header-only).  It is
        # a build-time-only, non-propagating requirement: no Boost symbol appears
        # in the public interface or in libmrgingham.so's DT_NEEDED.
        # 1.89.0 (headers-only + Boost.Test static lib) is chosen over 1.85.0
        # because the latter pins zlib/1.3.1, which conflicts with the
        # zlib/1.3.1.1 that the OpenCV package pulls in.
        self.requires("boost/1.89.0", transitive_headers=False, transitive_libs=False)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)
        # Vendor the pinned mrbuild Makefile framework (see module docstring).
        get(self,
            url=self.conan_data["mrbuild"]["url"],
            sha256=self.conan_data["mrbuild"]["sha256"],
            destination="mrbuild",
            strip_root=True)

    def generate(self):
        # Writes opencv4.pc (+ transitive dep .pc files) into generators_folder.
        PkgConfigDeps(self).generate()

    def build(self):
        cc, cxx = self._compilers()
        boost_include = os.path.join(self.dependencies["boost"].package_folder, "include")
        gen = self.generators_folder

        # mrbuild builds in-source; run it in a copy of the source tree inside the
        # Conan build folder so the cached source folder stays pristine (mairix
        # precedent).
        apply_conandata_patches(self)
        shutil.copytree(self.source_folder, self.build_folder,
                        symlinks=True, dirs_exist_ok=True)

        # mrbuild evaluates `pkg-config --cflags/--libs opencv4` at Makefile-parse
        # time, so PKG_CONFIG_PATH must be set for the make process.  PKG_CONFIG_LIBDIR
        # *replaces* the default search path (unlike PKG_CONFIG_PATH), keeping the
        # lookup inside the Conan-generated directory.
        # CXXFLAGS/CPPFLAGS go through the environment: mrbuild rejects command-line
        # *FLAGS variables, and R33 forbids depending on ambient shell variables.
        env = (
            f'PKG_CONFIG_PATH="{gen}" PKG_CONFIG_LIBDIR="{gen}" '
            f'CPPFLAGS="-I{boost_include}" '
            f'CXXFLAGS="-std=c++17" '
        )
        # Keep the SDK's own libxml2.so.16 ahead of any Conan/ambient one so the
        # SDK lld can start (see module docstring / notes.md).
        sdk_ld = self._sdk_llvm_libdir()
        ld_env = f'LD_LIBRARY_PATH="{sdk_ld}:$LD_LIBRARY_PATH" ' if sdk_ld else ""
        self.run(
            f'{ld_env}{env} make -j1 CC="{cc}" CXX="{cxx}" VERSION="{self.version}" '
            + " ".join(BUILD_TARGETS),
            cwd=self.build_folder,
        )

    def package(self):
        src = self.build_folder
        libdir = os.path.join(self.package_folder, "lib")
        # Shared library: real file + the SONAME symlinks mrbuild's install rule
        # would create (libmrgingham.so -> libmrgingham.so.2 -> libmrgingham.so.2.1).
        full = glob.glob(os.path.join(src, "libmrgingham.so.*.*"))
        if len(full) != 1:
            raise Exception(f"expected one versioned libmrgingham.so, found {full}")
        full_name = os.path.basename(full[0])
        copy(self, full_name, src, libdir)
        for link in ("libmrgingham.so", "libmrgingham.so.2"):
            os.symlink(full_name, os.path.join(libdir, link))

        include_dir = os.path.join(self.package_folder, "include", "mrgingham")
        for header in DIST_INCLUDE:
            copy(self, header, src, include_dir)

        bindir = os.path.join(self.package_folder, "bin")
        for tool in DIST_BIN:
            copy(self, tool, src, bindir)

        copy(self, "README.org", src, os.path.join(self.package_folder, "licenses"))

    def package_info(self):
        self.cpp_info.libs = ["mrgingham"]
        # Upstream installs the headers into <prefix>/include/mrgingham, so
        # consumers write <mrgingham/mrgingham.hh>; expose both that and the flat
        # directory (mrgingham.hh includes "point.hh" relative to itself).
        self.cpp_info.includedirs = ["include/mrgingham", "include"]
        self.cpp_info.bindirs = ["bin"]
        self.cpp_info.set_property("pkg_config_name", "mrgingham")
        self.cpp_info.set_property("cmake_file_name", "mrgingham")

    def _compilers(self):
        """(CC, CXX) from the Conan conf, never from the ambient shell (R33)."""
        import json
        executables = self.conf.get("tools.build:compiler_executables", default={})
        if isinstance(executables, str):
            executables = json.loads(executables)
        return executables.get("c", "clang"), executables.get("cpp", "clang++")

    def _sdk_llvm_libdir(self):
        """SDK ``llvm/lib`` that holds ``libxml2.so.16``, or "" if not found.

        The OHOS clang driver spawns the SDK's lld, whose RUNPATH is
        ``$ORIGIN/../lib``.  A Conan or ambient ``libxml2.so.16`` earlier on
        ``LD_LIBRARY_PATH`` shadows it and lld aborts with "Error loading shared
        library libxml2.so.16 ... symbol not found" (reproduced on-device).
        Prepending this dir keeps the SDK's own libxml2 first for lld.
        """
        _, cxx = self._compilers()
        compiler = os.path.realpath(shutil.which(cxx) or cxx)
        llvm_lib = os.path.join(os.path.dirname(os.path.dirname(compiler)), "lib")
        if os.path.isfile(os.path.join(llvm_lib, "libxml2.so.16")):
            return llvm_lib
        return ""
