#!/usr/bin/env python3
"""Conan recipe — xsettings 0.10 (libxsettings-client, Xsettings protocol client C library)

Build system: CMake (rewritten from upstream autotools; configure.ac uses
AC_PATH_X/AC_PATH_XTRA to detect X11, Makefile.am builds libXsettings-client.la
with @X_LIBS@).  The CMake rewrite preserves the same library name, SONAME,
and public headers.

License: MIT (X11-style, see src/COPYING)
Homepage: https://matchbox-project.org/sources/optional-dependencies/
Source: https://downloads.yoctoproject.org/releases/matchbox/optional-dependencies/

Dependencies (verified from configure.ac + Makefile.am):
  - configure.ac:13-14  AC_PATH_X + AC_PATH_XTRA  → detects X11 via pkg-config/X11
  - Makefile.am:11       libXsettings_client_la_LIBADD = @X_LIBS@  → links -lX11 only
  - No other dependencies (no glib, no libxml, no additional X libs)
  ⇒ Exact dependency: libx11 only.

Upstream source audit:
  - 4 source files: xsettings-client.c, xsettings-common.c + 2 headers
  - XsettingsBuffer/XSettingsColor/XSettingsList/XSettingsSetting structs
  - Core API: xsettings_client_new/destroy/get_setting/process_event
  - Serializes XSETTINGS protocol property data from X11 manager window

Upstream test audit:
  - Makefile.am: no check/TESTS/check_PROGRAMS target
  - No test/ directory, no *_test.cc files
  - INSTALL document does not mention tests
  ⇒ upstream_tests_exist: false; test_package validates consumer-side API usage.
"""

import os

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.cmake import CMake, CMakeDeps, CMakeToolchain, cmake_layout
from conan.tools.files import apply_conandata_patches, copy, export_conandata_patches, get


class XsettingsConan(ConanFile):
    name = "xsettings"
    version = "0.10"
    description = "Xsettings protocol client C library (libxsettings-client)"
    license = "MIT"
    homepage = "https://matchbox-project.org/sources/optional-dependencies/"
    url = "https://downloads.yoctoproject.org/releases/matchbox/optional-dependencies/"
    package_type = "library"
    settings = "os", "arch", "compiler", "build_type"
    options = {
        "shared": [True, False],
        "fPIC": [True, False],
    }
    default_options = {
        "shared": True,
        "fPIC": True,
    }

    def export_sources(self):
        # House pattern (catcodec/pen precedent): export upstream patches
        # declared in conandata.yml (none for xsettings 0.10 — no-op guard).
        export_conandata_patches(self)

    def configure(self):
        if self.options.shared:
            self.options.rm_safe("fPIC")

    def validate(self):
        if str(self.settings.os) not in ("Linux", "OHOS"):
            raise ConanInvalidConfiguration(
                f"xsettings supports Linux and OHOS, not {self.settings.os}"
            )

    def requirements(self):
        self.requires("libx11/1.8.13.1", transitive_headers=True, transitive_libs=True)
        # Explicitly require xorgproto for X11/X.h header (libx11 uses autotools
        # → CMakeDeps doesn't propagate xorgproto include dir)
        self.requires("xorgproto/2025.1")

    def layout(self):
        # cmake_layout separates source and build folders in conan create
        cmake_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"][str(self.version)], strip_root=True)
        # Write CMakeLists.txt to source_folder (CMake needs it at source root)
        # libx11 uses autotools → doesn't propagate xorgproto headers
        xorg_inc = self.dependencies["xorgproto"].package_folder + "/include"
        cmake_content = (
            'cmake_minimum_required(VERSION 3.16)\n'
            'project(xsettings-client VERSION 0.10 LANGUAGES C)\n'
            'find_package(libx11 CONFIG REQUIRED)\n'
            'add_library(Xsettings-client xsettings-client.c xsettings-common.c)\n'
            'target_include_directories(Xsettings-client PUBLIC\n'
            '    $<BUILD_INTERFACE:${CMAKE_CURRENT_SOURCE_DIR}>\n'
            f'    {xorg_inc}\n'
            '    $<INSTALL_INTERFACE:include>)\n'
            'target_link_libraries(Xsettings-client PUBLIC libx11::libx11)\n'
            # CMake does not know the HarmonyOS platform module, so VERSION/SOVERSION
            # target properties are silently ignored (no -Wl,-soname) -> packaged .so
            # lacks DT_SONAME (CI L5a gate). Set it explicitly (W3 run4 evidence).
            'target_link_options(Xsettings-client PRIVATE "LINKER:-soname,libXsettings-client.so.0")\n'
            'set_target_properties(Xsettings-client PROPERTIES\n'
            '    C_STANDARD 99 C_STANDARD_REQUIRED ON\n'
            '    VERSION 0.10 SOVERSION 0 OUTPUT_NAME Xsettings-client)\n'
            'install(TARGETS Xsettings-client LIBRARY DESTINATION lib ARCHIVE DESTINATION lib RUNTIME DESTINATION bin)\n'
            'install(FILES xsettings-client.h xsettings-common.h DESTINATION include)\n'
        )
        cmake_path = os.path.join(self.source_folder, "CMakeLists.txt")
        with open(cmake_path, "w", encoding="utf-8") as f:
            f.write(cmake_content)
        self.output.info(f"CMakeLists.txt written to {cmake_path}")

    def generate(self):
        tc = CMakeToolchain(self)
        deps = CMakeDeps(self)
        deps.generate()
        tc.generate()

    def build(self):
        # Apply patches from conandata.yml (no-op for 0.10: patchless release).
        apply_conandata_patches(self)
        cmake = CMake(self)
        cmake.configure()
        # HMFS (HarmonyOS FUSE): concurrent clang jobs cause EACCES.
        # cmake.build() appends -j1 AFTER its own -j20 → still parallel.
        # Directly run cmake --build with explicit -j1.
        self.run(
            f"cmake --build {self.build_folder} -- -j1",
            stdout=open(os.path.join(self.build_folder, "build_stdout.log"), "w"),
            stderr=open(os.path.join(self.build_folder, "build_stderr.log"), "w"),
        )

    def package(self):
        cmake = CMake(self)
        cmake.install()
        copy(
            self,
            "COPYING",
            src=self.source_folder,
            dst=os.path.join(self.package_folder, "licenses"),
            keep_path=False,
        )

    def package_info(self):
        self.cpp_info.libs = ["Xsettings-client"]
        self.cpp_info.set_property("cmake_file_name", "xsettings")
        self.cpp_info.set_property("cmake_target_name", "xsettings::xsettings")
        self.cpp_info.set_property("pkg_config_name", "xsettings-client")
