#!/usr/bin/env python3
"""Conan recipe for pnc-gawk 0.9.5 on HarmonyOS PC (OHOS aarch64).

pnc-gawk is the GNU AWK extension of the pnc project
(https://git.sr.ht/~anjan/pnc, Alpine Linux subpackage ``pnc-gawk``):
``gawkpn.so``, built from ``gawkext/``.  It exposes libphonenumber number
parsing, formatting, validity checks and offline geocoding to AWK programs.

Upstream registers the functions in the ``phonenumber`` AWK namespace
(``dl_load_func(func_table, "phonenumber", "phonenumber")``), so on GNU Awk
5.x they are called as ``phonenumber::pn_format(...)`` or from
``@namespace "phonenumber"`` blocks.

One upstream CMake configuration builds both the ``pnc`` CLI and the
extension; this recipe packages only the extension (the CLI is a separate
upstream binary package).

Dependencies:
  * libphonenumber/8.13.51 — already ships ``libgeocoding.a`` built from the
    same upstream snapshot (v8.13.51).  libgeocoding/9.0.34 is deliberately
    NOT added: pairing a 9.0.34 geocoder archive with 8.13.51 headers and
    phonenumber archive is an ABI/ODR mismatch.
  * icu4c/78 — ICU, required by both phonenumber and geocoding code.
  * gawk/5.3.0 — ``gawkapi.h`` at build time and the runtime host that loads
    the extension.

OHOS adaptation (see patches/ and notes.md):
  * dependency discovery is driven by the build driver instead of the
    hardcoded /usr/local prefix;
  * the AWK extension install directory is prefix-relative (lib/gawk) instead
    of the build-machine AWKLIBPATH.
"""

import os

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.build import can_run
from conan.tools.cmake import CMake, CMakeToolchain, cmake_layout
from conan.tools.files import (apply_conandata_patches, copy, export_conandata_patches,
                               get, rmdir)


class PncGawkConan(ConanFile):
    name = "pnc-gawk"
    version = "0.9.5"
    description = ("GNU AWK extension (gawkpn.so) exposing libphonenumber parsing, "
                   "formatting, validation and offline geocoding")
    license = "GPL-3.0-or-later"
    homepage = "https://git.sr.ht/~anjan/pnc"
    url = "https://github.com/OpenHarmonyPCDeveloper/build_in_harmonyos"

    package_type = "shared-library"

    settings = "os", "compiler", "build_type", "arch"

    def export_sources(self):
        export_conandata_patches(self)

    def configure(self):
        if self.settings.os not in ("Linux", "OHOS"):
            raise ConanInvalidConfiguration(
                "pnc-gawk is only supported on Linux/OHOS, not %s" % self.settings.os
            )

    def requirements(self):
        self.requires("libphonenumber/8.13.51", transitive_headers=True, transitive_libs=True)
        self.requires("icu4c/78", transitive_headers=True, transitive_libs=True)
        self.requires("gawk/5.3.0")

    def layout(self):
        cmake_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def _dependency_flags(self):
        """Collect absolute include dirs, archives and system libs.

        Upstream links with bare find_library() results, so the whole static
        closure (phonenumber + geocoding + protobuf + abseil + ICU + zlib)
        has to reach the link line explicitly.  The archives are wrapped in a
        linker group by generate(), therefore their order is irrelevant.
        """
        includes, libs, system_libs = [], [], []
        for _require, dep in self.dependencies.host.items():
            info = dep.cpp_info.aggregated_components()
            for inc in info.includedirs:
                path = os.path.normpath(os.path.join(dep.package_folder, inc))
                if os.path.isdir(path) and path not in includes:
                    includes.append(path)
            for libdir in info.libdirs:
                directory = os.path.normpath(os.path.join(dep.package_folder, libdir))
                for lib in info.libs:
                    for candidate in ("lib%s.a" % lib, "%s.a" % lib, "lib%s.so" % lib):
                        full = os.path.join(directory, candidate)
                        if os.path.isfile(full) and full not in libs:
                            libs.append(full)
            for syslib in info.system_libs:
                if syslib not in system_libs:
                    system_libs.append(syslib)
        # protobuf/33.6 does not export utf8_range/utf8_validity through
        # cpp_info, but the generated protobuf code of libphonenumber needs
        # both archives.
        try:
            protobuf = self.dependencies["protobuf"]
        except KeyError:
            protobuf = None
        if protobuf is not None:
            for extra in ("utf8_validity", "utf8_range"):
                full = os.path.join(protobuf.package_folder, "lib", "lib%s.a" % extra)
                if os.path.isfile(full) and full not in libs:
                    libs.append(full)
        return includes, libs, system_libs

    def generate(self):
        tc = CMakeToolchain(self)
        includes, libs, system_libs = self._dependency_flags()
        tc.variables["PNC_CONAN_PACKAGE_MODE"] = "ON"
        tc.variables["PNC_DEP_INCLUDE_DIRS"] = ";".join(includes)
        tc.variables["PNC_EXTRA_LINK_LIBRARIES"] = ";".join(
            ["-Wl,--start-group"] + libs + ["-Wl,--end-group"] + system_libs
        )
        tc.variables["GAWK_INCLUDE_DIR"] = os.path.join(
            self.dependencies["gawk"].package_folder, "include"
        )
        tc.variables["AWKLIBPATH"] = "lib/gawk"
        tc.generate()

    def build(self):
        apply_conandata_patches(self)
        cmake = CMake(self)
        cmake.configure()
        cmake.build()
        # Upstream test suite: CMakeLists registers tests.sh through
        # enable_testing()/add_test().  It drives the pnc CLI that is built
        # from the same gawkpnimpl.cc/geocoding code the extension links, so
        # it is the upstream regression suite of this source tree.
        if can_run(self):
            cmake.test()
        else:
            self.output.warning("upstream ctest not run: target binaries cannot execute here")

    def package(self):
        cmake = CMake(self)
        cmake.install()
        # The shared upstream install rules also install the pnc CLI and its
        # man page; this package is the AWK extension only.
        rmdir(self, os.path.join(self.package_folder, "bin"))
        rmdir(self, os.path.join(self.package_folder, "share"))
        copy(self, "LICENSE", src=self.source_folder,
             dst=os.path.join(self.package_folder, "licenses"))

    def package_info(self):
        # gawk plugin: not a linkable library.  Consumers load it through
        # gawk's AWKLIBPATH pointing at <package_folder>/lib/gawk.
        self.cpp_info.libs = []
        self.cpp_info.bindirs = []
        self.cpp_info.includedirs = []
