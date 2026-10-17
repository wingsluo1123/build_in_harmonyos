#!/usr/bin/env python3
"""Conan recipe for mrtgutils 0.8.4.

mrtgutils is a small set of MRTG helper programs written in C.  The
release archive contains only Autotools input files, not a generated
configure script.  We compile the programs directly with the compiler
selected by Conan; this keeps the recipe independent of a host Autotools
installation and lets the upstream source files be fixed with one small
portability patch.

All five upstream programs are packaged.  mrtg-sensors, which upstream
links against libsensors when it is available, uses the lm-sensors/3.6.0
package published in the artifact repository.
"""

import os

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.files import (
    apply_conandata_patches,
    copy,
    export_conandata_patches,
    get,
)
from conan.tools.layout import basic_layout


class MrtgutilsConan(ConanFile):
    name = "mrtgutils"
    version = "0.8.4"
    description = (
        "Small MRTG helper utilities for load, uptime, IP accounting, "
        "Apache status, and sensors"
    )
    license = "GPL-2.0-or-later"
    homepage = "https://salsa.debian.org/debian/mrtgutils"
    url = "https://salsa.debian.org/debian/mrtgutils"

    package_type = "application"
    settings = "os", "compiler", "build_type", "arch"

    _programs = (
        "mrtg-load",
        "mrtg-uptime",
        "mrtg-ip-acct",
        "mrtg-apache",
        "mrtg-sensors",
    )

    def validate(self):
        if self.settings.os not in ("Linux", "OHOS"):
            raise ConanInvalidConfiguration(
                f"mrtgutils supports Linux and OHOS only, got {self.settings.os}"
            )

    def requirements(self):
        # libsensors, used by the upstream mrtg-sensors program, is already
        # published in the artifact repository.
        self.requires("lm-sensors/3.6.0")

    def export_sources(self):
        export_conandata_patches(self)

    def layout(self):
        basic_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def _sensors_flags(self):
        """Compile and link flags taken from the lm-sensors package."""
        dependency = self.dependencies["lm-sensors"]
        components = dependency.cpp_info.aggregated_components()
        flags = [
            f'-I"{os.path.join(dependency.package_folder, folder)}"'
            for folder in components.includedirs
        ]
        flags += [
            f'-L"{os.path.join(dependency.package_folder, folder)}"'
            for folder in components.libdirs
        ]
        flags += [f"-l{library}" for library in (components.libs or ["sensors"])]
        return flags

    def build(self):
        apply_conandata_patches(self)

        # R33: the compiler comes from the Conan profile, never from the
        # release worker's possibly-empty CC shell variable.
        compilers = self.conf.get(
            "tools.build:compiler_executables", default={}, check_type=dict
        )
        cc = compilers.get("c") or "clang"

        build_type = str(self.settings.build_type)
        cflags = ["-Wall", "-fPIE"]
        if build_type == "Debug":
            cflags.extend(["-O0", "-g"])
        elif build_type == "RelWithDebInfo":
            cflags.extend(["-O2", "-g", "-DNDEBUG"])
        elif build_type == "MinSizeRel":
            cflags.extend(["-Os", "-DNDEBUG"])
        else:
            cflags.extend(["-O2", "-DNDEBUG"])

        sensors_flags = " ".join(self._sensors_flags())

        os.makedirs(self.build_folder, exist_ok=True)
        common_sources = ["uptime.c", "util.c"]
        for program in self._programs:
            sources = [f"{program}.c", *common_sources]
            source_args = " ".join(
                f'"{os.path.join(self.source_folder, source)}"'
                for source in sources
            )
            output = os.path.join(self.build_folder, program)
            # libsensors is a static library, so its flags have to follow the
            # translation units that reference its symbols.
            extra = f" {sensors_flags} -lm" if program == "mrtg-sensors" else ""
            self.run(
                f'"{cc}" {" ".join(cflags)} {source_args} '
                f'-o "{output}" -pie -Wl,-z,relro,-z,now{extra}',
                cwd=self.source_folder,
            )

    def package(self):
        for program in self._programs:
            copy(
                self,
                program,
                src=self.build_folder,
                dst=os.path.join(self.package_folder, "bin"),
            )
        copy(
            self,
            "*.pod",
            src=self.source_folder,
            dst=os.path.join(self.package_folder, "share", "doc", "mrtgutils"),
        )

    def package_info(self):
        self.cpp_info.bindirs = ["bin"]
        self.cpp_info.libdirs = []
        self.cpp_info.includedirs = []
        self.cpp_info.libs = []
