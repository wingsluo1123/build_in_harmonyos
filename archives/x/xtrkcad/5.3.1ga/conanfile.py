#!/usr/bin/env python3
"""XTrackCAD - CAD program for designing model railroad layouts.

OpenHarmony PC (aarch64) adaptation notes
-----------------------------------------

* The project picks its POSIX code paths with the CMake ``UNIX`` variable.
  HarmonyOS is not a system CMake knows about, so ``UNIX`` is false there and
  the non POSIX branches are configured instead.  The platform patch marks the
  system as Unix-like rather than relabelling ``CMAKE_SYSTEM_NAME``, which would
  load the wrong platform modules.

* The build rasterises its SVG bitmaps with Inkscape, which is not available on
  OpenHarmony.  A small rasteriser built on top of librsvg (which is) replaces
  it, so that the generated bitmap headers can still be produced.

* Dependencies supplied by Conan install lower case imported targets, while the
  find modules in ``CMake/`` define upper case variables.  The platform patch
  bridges both so that either kind of package source can be used.

* ``app/bin/bitmaps/CMakeLists.txt`` is stored with CRLF line endings upstream.
  A LF patch cannot be applied to a CRLF file, so the adapted copy of that file
  is carried in ``ohos/bitmaps/`` and copied over the sources before
  configuring.
"""
import os

from conan import ConanFile
from conan.tools.cmake import CMake, CMakeDeps, CMakeToolchain, cmake_layout
from conan.tools.files import copy, get, apply_conandata_patches, export_conandata_patches
from conan.tools.gnu import PkgConfigDeps


class XtrkcadConan(ConanFile):
    name = "xtrkcad"
    version = "5.3.1ga"
    description = "XTrackCAD - CAD program for designing model railroad layouts"
    license = "GPL-2.0-or-later"
    homepage = "https://xtrkcad-fork.sourceforge.net/"
    url = "https://gitcode.com/OpenHarmonyPCDeveloper/build_in_harmonyos"
    package_type = "application"

    settings = "os", "compiler", "build_type", "arch"
    options = {"shared": [True, False]}
    default_options = {"shared": False}

    def export_sources(self):
        export_conandata_patches(self)
        copy(self, "ohos/*", src=self.recipe_folder, dst=self.export_sources_folder)

    def requirements(self):
        self.requires("gtk2/2.24.33")
        self.requires("libzip/1.11.4")
        # Used while building: the rasteriser that replaces Inkscape.  It stays a
        # regular requirement because the generated bitmap headers are produced
        # by a program of the same architecture that is being built.
        self.requires("librsvg/2.62.3.1.1")

    def build_requirements(self):
        self.test_requires("cmocka/2.0.2")

    def layout(self):
        cmake_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def generate(self):
        # The project looks GTK up through pkg-config (pkg_check_modules in
        # CMakeLists.txt), and the find modules in CMake/ look for the imported
        # targets that CMakeDeps creates; both generators are therefore needed.
        deps = CMakeDeps(self)
        deps.generate()
        pkg_config_deps = PkgConfigDeps(self)
        pkg_config_deps.generate()
        tc = CMakeToolchain(self)
        tc.variables["BUILD_SHARED_LIBS"] = "ON" if self.options.shared else "OFF"
        tc.generate()

    def build(self):
        apply_conandata_patches(self)
        # See the file header: this file cannot be delivered as a patch.
        copy(self, "*",
             src=os.path.join(self.export_sources_folder, "ohos", "bitmaps"),
             dst=os.path.join(self.source_folder, "app", "bin", "bitmaps"),
             keep_path=False)
        cmake = CMake(self)
        # PlatformSettings.cmake turns gettext on for every non-Apple UNIX and
        # only checks for libintl.h.  The OHOS sysroot ships the header without
        # a linkable libintl, so the _() macros end up calling an undefined
        # gettext(); build without NLS instead (the project's own plain-string
        # fallback).
        cmake.configure(cli_args=["-DXTRKCAD_USE_GETTEXT=OFF"])
        # The build runs tools it has just produced (svg2png rasterises the
        # toolbar bitmaps in place of Inkscape) and tools that ship with the
        # dependencies (gdk-pixbuf-csource turns those bitmaps into C arrays);
        # neither the library dirs nor the bin dirs of the dependencies are on
        # the loader path / PATH of a clean build environment.
        libdirs, bindirs = [], []
        for dep in self.dependencies.values():
            components = dep.cpp_info.aggregated_components()
            libdirs.extend(components.libdirs)
            bindirs.extend(components.bindirs)
        previous = {var: os.environ.get(var) for var in ("LD_LIBRARY_PATH", "PATH")}
        os.environ["LD_LIBRARY_PATH"] = os.pathsep.join(
            [d for d in libdirs if d] + ([previous["LD_LIBRARY_PATH"]] if previous["LD_LIBRARY_PATH"] else []))
        os.environ["PATH"] = os.pathsep.join(
            [d for d in bindirs if d] + ([previous["PATH"]] if previous["PATH"] else []))
        try:
            cmake.build()
            cmake.test()
        finally:
            for var, value in previous.items():
                if value is None:
                    os.environ.pop(var, None)
                else:
                    os.environ[var] = value

    def package(self):
        copy(self, "COPYING", src=os.path.join(self.source_folder, "app"),
             dst=os.path.join(self.package_folder, "licenses"))
        for exe, sub in (("xtrkcad", "app/bin"),
                         ("cnvdsgn", "app/bin"),
                         ("mkturnout", "app/bin"),
                         ("listxtp", "app/tools"),
                         ("svg2png", "app/bin/bitmaps")):
            copy(self, exe, src=os.path.join(self.build_folder, sub),
                 dst=os.path.join(self.package_folder, "bin"))
        for lib, sub in (("libxtrkcad-lib.a", "app/bin"),
                         ("libxtrkcad-wlib.a", "app/wlib"),
                         ("libxtrkcad-cornu.a", "app/cornu"),
                         ("libdynstring.a", "app/dynstring"),
                         ("libcJSON.a", "app/cJSON")):
            copy(self, lib, src=os.path.join(self.build_folder, sub),
                 dst=os.path.join(self.package_folder, "lib"))
        copy(self, "*.h", src=os.path.join(self.source_folder, "app", "bin"),
             dst=os.path.join(self.package_folder, "include"), keep_path=False)
        copy(self, "*.h", src=os.path.join(self.source_folder, "app", "wlib", "include"),
             dst=os.path.join(self.package_folder, "include"), keep_path=False)
        copy(self, "dynstring.h", src=os.path.join(self.source_folder, "app", "dynstring"),
             dst=os.path.join(self.package_folder, "include"))

    def package_info(self):
        self.cpp_info.bindirs = ["bin"]
        self.cpp_info.libdirs = ["lib"]
        self.cpp_info.includedirs = ["include"]
        # The package is an application; only the self contained helper library
        # is meaningful to link against, which is what the package test does.
        self.cpp_info.libs = ["dynstring"]
