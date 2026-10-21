#!/usr/bin/env python3
"""Conan recipe — liblscp 1.0.1 (LinuxSampler Control Protocol client library).

Upstream is a plain CMake C library.  Everything OHOS-specific is handled
through CMake cache variables and package metadata; no source patch is needed
(see notes.md for the line-by-line reading of the upstream build system).
"""
import os

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.cmake import CMake, CMakeToolchain, cmake_layout
from conan.tools.files import apply_conandata_patches, copy, export_conandata_patches, get

required_conan_version = ">=2.0"


class LiblscpConan(ConanFile):
    name = "liblscp"
    version = "1.0.1"
    description = (
        "LinuxSampler Control Protocol (LSCP) client library: blocking socket "
        "client, command wrappers and event subscription for talking to a "
        "LinuxSampler backend."
    )
    license = "LGPL-2.1-or-later"
    homepage = "https://linuxsampler.org/"
    url = "https://download.linuxsampler.org/packages/liblscp-1.0.1.tar.gz"
    topics = ("lscp", "linuxsampler", "audio", "network", "protocol")

    package_type = "library"
    settings = "os", "arch", "compiler", "build_type"
    options = {"shared": [True, False]}
    default_options = {"shared": True}

    def export_sources(self):
        export_conandata_patches(self)

    def validate(self):
        # src/CMakeLists.txt:45 hardcodes `add_library (${PROJECT_NAME} SHARED ...)`,
        # so a static build cannot be requested without patching upstream.
        if not self.options.shared:
            raise ConanInvalidConfiguration(
                "liblscp 1.0.1 only builds a shared library: upstream "
                "src/CMakeLists.txt hardcodes add_library(${PROJECT_NAME} SHARED ...) "
                "and BUILD_SHARED_LIBS has no effect."
            )

    def layout(self):
        cmake_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def generate(self):
        tc = CMakeToolchain(self)
        # Upstream computes CONFIG_LIBDIR/CONFIG_INCLUDEDIR as
        # "${CMAKE_INSTALL_PREFIX}/<GNUInstallDirs result>" (top CMakeLists.txt:36-41
        # and 75-81) and uses them as install destinations.  Pinning the two
        # GNUInstallDirs outputs makes the package layout deterministic on aarch64
        # instead of inheriting the generator's lib/lib64 guess.
        tc.variables["CMAKE_INSTALL_LIBDIR"] = "lib"
        tc.variables["CMAKE_INSTALL_INCLUDEDIR"] = "include"

        # OHOS: CMake 4.4.3 ships no Platform/HarmonyOS module, so
        # CMAKE_SHARED_LIBRARY_SONAME_C_FLAG stays empty and the link rule
        # template <SONAME_FLAG><TARGET_SONAME> never passes -Wl,-soname --
        # even though upstream src/CMakeLists.txt:58-63 already declares
        # VERSION 6.0.6 / SOVERSION 6.  The result was a liblscp.so with no
        # DT_SONAME (W3 gate L5a fail).  Supply the missing flag and keep one
        # flat liblscp.so whose DT_SONAME equals its own file name, so the
        # packaged layout and the linker stem `lscp` stay unchanged.
        # Same mechanism as archives/a/accessibility/26.04.3/conanfile.py:117-131
        # and knowledge/DRAFT-libharu-2.3.0-missing-dt-soname.
        tc.variables["CMAKE_SHARED_LIBRARY_SONAME_C_FLAG"] = "-Wl,-soname,"
        tc.variables["CMAKE_PLATFORM_NO_VERSIONED_SONAME"] = "ON"
        tc.generate()

    def build(self):
        apply_conandata_patches(self)
        cmake = CMake(self)
        cmake.configure()
        # Upstream registers no test target (no enable_testing/add_test anywhere in
        # the tarball), so cmake.test() is deliberately not called; the behavioural
        # evidence is the consumer test in test_package/.  See notes.md.
        cmake.build()

    def package(self):
        cmake = CMake(self)
        cmake.install()
        copy(self, "LICENSE",
             src=self.source_folder,
             dst=os.path.join(self.package_folder, "licenses"))
        copy(self, "README",
             src=self.source_folder,
             dst=os.path.join(self.package_folder, "licenses"))

    def package_info(self):
        # OUTPUT_NAME is "lscp" with PREFIX "lib" (src/CMakeLists.txt:58-63),
        # so the artifact is liblscp.so and the linker stem is `lscp`.
        self.cpp_info.libs = ["lscp"]
        self.cpp_info.includedirs = ["include"]
        self.cpp_info.libdirs = ["lib"]
        # target_link_libraries(liblscp PUBLIC pthread) (src/CMakeLists.txt:50)
        self.cpp_info.system_libs = ["pthread"]
        self.cpp_info.set_property("cmake_file_name", "liblscp")
        self.cpp_info.set_property("cmake_target_name", "liblscp::liblscp")
        self.cpp_info.set_property("pkg_config_name", "lscp")
