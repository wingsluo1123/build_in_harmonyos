#!/usr/bin/env python3
"""Conan recipe — libsndfile 1.2.2 (CMake).

Build system: CMake
Dependencies: libogg/1.3.6.1, libvorbis/1.3.7, flac/1.4.3, opus/1.5.2.1

libsndfile ships its own Find*.cmake modules (FindOgg, FindVorbis,
FindFLAC, FindOpus) that use find_path/find_library with pkg-config
hints.  These modules create targets like FLAC::FLAC and Opus::opus
which differ in case from what Conan CMakeDeps would generate
(flac::flac, opus::opus).  To avoid target-name mismatches we force
module mode via CMAKE_FIND_PACKAGE_PREFER_CONFIG=OFF and point
CMAKE_INCLUDE_PATH / CMAKE_LIBRARY_PATH at each dependency's package
folder so the Find modules locate headers and libraries directly.
"""
import glob
import os

from conan import ConanFile
from conan.tools.cmake import CMake, CMakeDeps, CMakeToolchain, cmake_layout
from conan.tools.files import get, replace_in_file


class LibsndfileConan(ConanFile):
    name = "libsndfile"
    version = "1.2.2"
    description = "Library for reading and writing sound files (WAV, AIFF, AU, FLAC, OGG/Vorbis, Opus)"
    license = "LGPL-2.1-or-later"
    homepage = "https://libsndfile.github.io/libsndfile/"
    url = "https://gitcode.com/OpenHarmonyPCDeveloper/build_in_harmonyos"
    package_type = "library"

    settings = "os", "arch", "compiler", "build_type"
    options = {"shared": [True, False], "fPIC": [True, False]}
    default_options = {"shared": True, "fPIC": True}

    def config_options(self):
        if self.settings.os == "Windows":
            self.options.rm_safe("fPIC")

    def configure(self):
        if self.options.shared:
            self.options.rm_safe("fPIC")

    def requirements(self):
        self.requires("libogg/1.3.6.1")
        self.requires("libvorbis/1.3.7")
        self.requires("flac/1.4.3")
        self.requires("opus/1.5.2.1")

    def layout(self):
        cmake_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)
        # Patch cmake_minimum_required for CMake >= 4.0 compatibility
        replace_in_file(
            self, "CMakeLists.txt",
            "cmake_minimum_required (VERSION 3.1..3.18)",
            "cmake_minimum_required (VERSION 3.5..3.18)",
        )
        # Add alias targets for CMakeDeps target-name mismatches:
        # libsndfile links against FLAC::FLAC and Opus::opus (mixed case),
        # but Conan CMakeDeps generates flac::flac and opus::opus (lowercase).
        replace_in_file(
            self, "CMakeLists.txt",
            "include(SndFileChecks)",
            "include(SndFileChecks)\n"
            "# Conan CMakeDeps target name compatibility\n"
            "if(TARGET flac::flac AND NOT TARGET FLAC::FLAC)\n"
            "  add_library(FLAC::FLAC INTERFACE IMPORTED)\n"
            "  set_target_properties(FLAC::FLAC PROPERTIES INTERFACE_LINK_LIBRARIES flac::flac)\n"
            "endif()\n"
            "if(TARGET opus::opus AND NOT TARGET Opus::opus)\n"
            "  add_library(Opus::opus INTERFACE IMPORTED)\n"
            "  set_target_properties(Opus::opus PROPERTIES INTERFACE_LINK_LIBRARIES opus::opus)\n"
            "endif()",
        )

    def generate(self):
        CMakeDeps(self).generate()
        tc = CMakeToolchain(self)

        # --- Build configuration (toolchain-level regular variables) ---
        tc.variables["BUILD_SHARED_LIBS"] = bool(self.options.shared)
        tc.variables["ENABLE_EXTERNAL_LIBS"] = True
        tc.variables["BUILD_TESTING"] = False
        tc.variables["BUILD_EXAMPLES"] = False
        tc.variables["BUILD_PROGRAMS"] = False
        tc.generate()

    def build(self):
        # Cache variables survive cmake re-configures (triggered by make),
        # unlike toolchain-file regular variables which are lost.
        cmake = CMake(self)
        cmake.configure(variables={"CMAKE_POLICY_VERSION_MINIMUM": "3.5"})
        cmake.build()

    def package(self):
        CMake(self).install()
        self._sign_ohos_shared_libs()

    # ------------------------------------------------------------------
    # OHOS code-signing (XPM requirement)
    # ------------------------------------------------------------------
    def _is_elf(self, path):
        try:
            with open(path, "rb") as f:
                return f.read(4) == b"\x7fELF"
        except OSError:
            return False

    def _sign_ohos_shared_libs(self):
        if str(self.settings.os) != "OHOS":
            return
        if not self.options.shared:
            return

        targets = []
        for pattern in ("*.so", "*.so.*"):
            targets += glob.glob(
                os.path.join(self.package_folder, "lib", "**", pattern),
                recursive=True,
            )

        objcopy = os.environ.get("LLVM_OBJCOPY", "/data/service/hnp/bin/llvm-objcopy")
        signer = os.environ.get("BINARY_SIGN_TOOL", "/data/service/hnp/bin/binary-sign-tool")
        if not os.path.isfile(signer):
            self.output.warning(
                "binary-sign-tool not found ({}): skipping code signing. "
                "On device, unsigned .so files will fail to dlopen due to XPM.".format(signer))
            return

        for f in targets:
            if os.path.islink(f):
                continue
            if not self._is_elf(f):
                continue
            self.run('{oc} --remove-section .codesign "{f}" 2>/dev/null || true'.format(
                oc=objcopy, f=f))
            self.run('{sg} sign -inFile "{f}" -outFile "{f}" -selfSign 1'.format(
                sg=signer, f=f))

    def package_info(self):
        self.cpp_info.set_property("cmake_file_name", "SndFile")
        self.cpp_info.set_property("cmake_target_name", "SndFile::sndfile")
        self.cpp_info.set_property("pkg_config_name", "sndfile")
        self.cpp_info.libs = ["sndfile"]
        self.cpp_info.requires = [
            "libogg::libogg",
            "libvorbis::vorbis",
            "libvorbis::vorbisenc",
            "flac::flac",
            "opus::opus",
        ]
        if str(self.settings.os) in ("Linux", "OHOS"):
            self.cpp_info.system_libs = ["m"]
