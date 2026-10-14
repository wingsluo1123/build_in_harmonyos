#!/usr/bin/env python3
"""Conan recipe for loudgain 0.6.8.

loudgain is a ReplayGain 2.0 command-line utility: it decodes audio files
through FFmpeg, measures EBU R128 loudness with libebur128, and writes the
resulting ReplayGain tags through TagLib.  It installs a single executable
(plus an auxiliary shell script rgbpm), so the package type is
"application" and there is no public library API.

OHOS notes:
- The upstream CMakeLists resolves libavcodec/libavformat/libswresample/
  libavutil/taglib via pkg-config and libebur128 via a custom find module.
  pkg-config is not usable on this host, so patch 0001 rewrites the
  dependency block as plain find_path/find_library calls which honor the
  CMAKE_INCLUDE_PATH / CMAKE_LIBRARY_PATH cache variables that this recipe
  injects from the conan dependency graph.
- FFmpeg 5+ removed av_register_all() (still used, guarded by a version
  check in scan.c), so the recipe pins ffmpeg/4.4.x, the newest series the
  upstream code compiles against unpatched.
- taglib/1.13.1 is chosen over 2.x because the upstream build hard-codes
  -std=gnu++11 while taglib 2.x headers require C++17.
- libmp3lame is NOT a direct dependency: MP3 encoding is not done by
  loudgain (decode via FFmpeg, which pulls lame itself; tagging via TagLib).
- CMake >= 4 rejects the upstream cmake_minimum_required(VERSION 2.8); the
  recipe raises CMAKE_POLICY_VERSION_MINIMUM=3.5 as a cache variable (same
  approach as the taglib 1.13.1 recipe).
"""

import os

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.cmake import CMake, CMakeToolchain
from conan.tools.files import (
    apply_conandata_patches,
    copy,
    export_conandata_patches,
    get,
)
from conan.tools.layout import basic_layout


class LoudgainConan(ConanFile):
    name = "loudgain"
    version = "0.6.8"
    description = (
        "ReplayGain 2.0 command-line tool: measures EBU R128 loudness of "
        "MP3/FLAC/Ogg/Opus/MP4/WAV files (decode via FFmpeg, analysis via "
        "libebur128) and writes ReplayGain tags via TagLib"
    )
    license = "BSD-2-Clause"
    homepage = "https://github.com/Moonbase59/loudgain"
    url = "https://atomgit.com/OpenHarmonyPCDeveloper/build_in_harmonyos"
    package_type = "application"

    settings = "os", "arch", "compiler", "build_type"

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        self.requires("libebur128/1.2.6")
        self.requires("taglib/1.13.1")
        self.requires("ffmpeg/4.4.8")
        # taglib/1.13.1 pins zlib/1.3.1 while ffmpeg/4.4.8 pins the
        # adaptation-fixed zlib/1.3.1.1 (R37 suffix); align the graph on the
        # fixed version (same upstream 1.3.1, published later for bugfixes).
        self.requires("zlib/1.3.1.1", override=True)

    def validate(self):
        if str(self.settings.os) not in ("Linux", "OHOS"):
            raise ConanInvalidConfiguration(
                f"loudgain requires a POSIX-like target (Linux or OHOS), "
                f"not {self.settings.os}"
            )

    def layout(self):
        basic_layout(self, src_folder=".")

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def generate(self):
        tc = CMakeToolchain(self)
        # Patched CMakeLists resolves every dependency with plain
        # find_path/find_library, which search CMAKE_INCLUDE_PATH and
        # CMAKE_LIBRARY_PATH by default.  Feed them the absolute include/lib
        # dirs of the whole conan host graph (components aggregated, since
        # ffmpeg/4.4.8 declares per-library components).
        inc, lib = [], []
        for dep in self.dependencies.host.values():
            # ffmpeg/4.4.8 declares per-library components; plain packages
            # have none, so fall back to the top-level cpp_info.
            infos = (
                list(dep.cpp_info.components.values())
                if dep.cpp_info.components else [dep.cpp_info]
            )
            for comp in infos:
                for d in (comp.includedirs or []):
                    inc.append(
                        d if os.path.isabs(d)
                        else os.path.join(dep.package_folder, d)
                    )
                for d in (comp.libdirs or []):
                    lib.append(
                        d if os.path.isabs(d)
                        else os.path.join(dep.package_folder, d)
                    )
        tc.variables["CMAKE_INCLUDE_PATH"] = ";".join(inc)
        tc.variables["CMAKE_LIBRARY_PATH"] = ";".join(lib)
        tc.generate()

    def build(self):
        apply_conandata_patches(self)
        cmake = CMake(self)
        cmake.configure(
            # Upstream declares cmake_minimum_required(VERSION 2.8); CMake 4.x
            # refuses to configure unless the policy floor is raised.  Must be
            # a command-line -D: a toolchain-file set() is not read before
            # CMakeLists.txt is parsed (same approach as taglib/1.13.1).
            variables={"CMAKE_POLICY_VERSION_MINIMUM": "3.5"},
        )
        cmake.build()

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
        self.cpp_info.bindirs = ["bin"]
        self.cpp_info.libdirs = []
        self.cpp_info.includedirs = []
