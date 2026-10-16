#!/usr/bin/env python3
"""Conan recipe for indi-nexdome 1.5+20221222183051 — INDI driver for NexDome domes.

indi-nexdome is the driver that lets any INDI client (KStars, …) control a
NexDome 2.4 m personal-observatory dome over its USB/serial controller. It is
shipped as a single subproject of the INDI 3rdparty monorepo and builds the
``indi_nexdome`` executable (an INDI driver that is spawned by ``indiserver``)
plus its ``indi_nexdome.xml`` device descriptor.

HarmonyOS PC (aarch64) adaptation:
  * the bundled ``cmake_modules/FindINDI.cmake`` / ``FindNova.cmake`` are
    old-style find modules (cache variables, not imported targets), so the
    Conan packages are wired in through those cache variables instead of
    CMakeDeps config files;
  * the driver executable resolves ``main()`` from ``libindidriver`` (INDI's
    documented entry-point trick — ``indidevapi.h``: "does not contain the C
    main() function"), which works with both the static and the shared form;
  * the device descriptor is installed into the package's own ``share/indi``
    (the upstream ``INDI_DATA_DIR`` autodetection only searches system paths).

License: LGPL-2.0-or-later (upstream indi-3rdparty / Jasem Mutlaq).
"""
import os

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.cmake import CMake, CMakeToolchain, cmake_layout
from conan.tools.files import (
    apply_conandata_patches,
    export_conandata_patches,
    get,
)


class IndiNexdomeConan(ConanFile):
    name = "indi-nexdome"
    version = "1.5+20221222183051"
    description = ("INDI driver for NexDome personal-observatory domes "
                   "(device control over USB/serial)")
    license = "LGPL-2.0-or-later"
    homepage = "https://indilib.org"
    url = "https://github.com/indilib/indi-3rdparty"
    topics = ("astronomy", "indi", "driver", "dome", "nexdome")

    package_type = "application"
    settings = "os", "compiler", "build_type", "arch"
    exports_sources = "patches/*"

    # R32: OHOS platform compatibility — only the Linux family is supported.
    def validate(self):
        if self.settings.os not in ("Linux", "OHOS", "HarmonyOS"):
            raise ConanInvalidConfiguration(
                f"indi-nexdome supports Linux/OHOS, not {self.settings.os}")

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        # libindi provides the INDI::Dome base class, indidriver (main()) and
        # the driver headers; libnova and zlib are the framework's declared
        # link dependencies (required by the upstream CMakeLists).
        self.requires("libindi/2.2.2.1")
        self.requires("libnova/0.16")
        self.requires("zlib/1.3.1.1")

    def layout(self):
        cmake_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    @staticmethod
    def _pick_lib(libdir, names):
        for name in names:
            candidate = os.path.join(libdir, name)
            if os.path.exists(candidate):
                return candidate
        return os.path.join(libdir, names[0])

    def _dependency_archives(self):
        """Absolute link paths for the whole host dependency closure.

        The driver is linked statically against the INDI framework (its shared
        objects cannot be loaded at runtime on this OHOS target), so the static
        archives of every transitive dependency must be on the link line inside
        a linker group."""
        libs = []
        for dep in self.dependencies.host.values():
            info = dep.cpp_info
            for libdir in info.libdirs:
                for name in info.libs:
                    for suffix in (".a", ".so"):
                        candidate = os.path.join(libdir, f"lib{name}{suffix}")
                        if os.path.exists(candidate):
                            libs.append(candidate)
                            break
        return libs

    def generate(self):
        tc = CMakeToolchain(self)
        # E092: CMake does not recognise the HarmonyOS platform name here, so
        # build for the Linux ABI of the OHOS clang toolchain (libindi same).
        tc.variables["CMAKE_SYSTEM_NAME"] = "Linux"
        tc.variables["CMAKE_SYSTEM_PROCESSOR"] = "aarch64"

        # The bundled FindINDI.cmake/FindNova.cmake are old-style modules: they
        # read cache variables and search for paths rather than imported targets.
        # Seed them with the exact Conan package locations.
        indi = self.dependencies["libindi"]
        tc.variables["INDI_ROOT"] = indi.package_folder

        nova = self.dependencies["libnova"]
        nova_folder = nova.package_folder
        tc.variables["NOVA_INCLUDE_DIR"] = os.path.join(nova_folder, "include")
        tc.variables["NOVA_LIBRARIES"] = self._pick_lib(
            os.path.join(nova_folder, "lib"), ["libnova.a", "libnova.so"])

        tc.variables["ZLIB_ROOT"] = self.dependencies["zlib"].package_folder

        # Static-link helper: the transitive archives of the INDI framework.
        tc.variables["INDI_NEXDOME_DEPS"] = ";".join(self._dependency_archives())

        # Install the device descriptor under the package's own share/indi.
        tc.variables["INDI_DATA_DIR"] = "share/indi"

        # OHOS signs every ELF with a content hash (.codesign) that the kernel
        # enforces on exec. CMake's install step rewrites the RPATH after lld
        # wrote that signature, invalidating it: exec then fails with a
        # misleading "Operation not permitted". Skipping both RPATHs keeps the
        # installed file byte-identical to the build tree (libapogee3 pattern);
        # consumers resolve dependencies through LD_LIBRARY_PATH (conanrun).
        tc.variables["CMAKE_SKIP_BUILD_RPATH"] = True
        tc.variables["CMAKE_SKIP_INSTALL_RPATH"] = True
        tc.generate()

    def build(self):
        apply_conandata_patches(self)
        cmake = CMake(self)
        cmake.configure()
        # R9: serial build on the OHOS host (parallel make's jobserver triggers
        # a silent clang failure, see libfishcamp/1.2).
        cmake.build(cli_args=["-j1"])

    def package(self):
        cmake = CMake(self)
        cmake.install()

    def package_info(self):
        # Pure executable package: the driver is spawned by indiserver.
        self.cpp_info.bindirs = ["bin"]
        self.cpp_info.includedirs = []
        self.cpp_info.libdirs = []
