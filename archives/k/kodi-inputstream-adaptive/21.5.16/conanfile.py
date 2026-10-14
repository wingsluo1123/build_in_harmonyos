#!/usr/bin/env python3
"""Conan recipe for kodi-inputstream-adaptive 21.5.16 — Kodi adaptive
streaming input stream add-on (DASH / HLS / Smooth Streaming).

Upstream: https://github.com/xbmc/inputstream.adaptive (tag 21.5.16-Omega,
commit 0b4dbaeffd175c4cddd32f7fd61cf81f12bda27d).

inputstream.adaptive is a Kodi binary add-on implementing adaptive streaming
input streams. The product is a single dlopen() shared module (upstream name
inputstream.adaptive.so, packaged with the standard lib prefix as
libinputstream.adaptive.so) built from the upstream src/ tree plus the
in-tree static libs (lib/mpegts, lib/webm_parser, lib/cdm) and the vendored
xbmc Bento4 fork. The Kodi host ABI travels exclusively through the C
function tables exported by ADDONCREATOR (kodi/AddonBase.h); the module has
no link-time dependency on a Kodi host.

The upstream CMakeLists.txt requires the Kodi build system:
find_package(Kodi REQUIRED) provides build_addon()/add_dir_sources() and
KODI_INCLUDE_DIR. The ohpcd registry has no Kodi build system, so this
recipe (kodi-inputstream-rtmp/21.1.2 precedent, kodi-platform
recipe-cmake precedent):

- ships its own CMake entry point under recipe-cmake/ (build_script_folder)
  that reuses the tarball Helpers.cmake macros, consumes the upstream
  subdirectory CMakeLists file declarations (GlobalSourceList /
  GlobalDepsFoldersList) verbatim, and links its own SHARED module target
  against Conan CMakeDeps targets;
- vendors the kodi-dev-kit headers under kodi-dev-kit/kodi (verbatim
  kodi/ subtree of xbmc 21.3-Omega, sha256
  a60afcb556e4a00cb19fc35b7e77758107c9a8096c6ce9b66af5f92396be31aa,
  xbmc/addons/kodi-dev-kit/include/kodi with the include/ path segment
  normalized away — the repo .gitignore excludes archives/**/include/).
  ADDON_INSTANCE_VERSION_INPUTSTREAM is 3.3.0 in those headers, which is
  the instance API the 21.5.16-Omega add-on is written against (Omega
  branch); BUILD_KODI_ADDON is intentionally NOT defined so versions.h
  keeps every version branch compiled in (test_package exercises them).

Bento4: upstream pins the xbmc FORK 1.6.0-641-3-Omega
(depends/common/bento4/bento4.txt) and builds it internally
(ENABLE_INTERNAL_BENTO4) with an explicit -fPIC because the static
libap4.a is linked into the dlopen module (non-PIC archives fail on
aarch64 with R_AARCH64 relocation errors; build-chain-pitfalls / R26
zlib precedent). The registry bento4/1.6.0-641 is the axiomatic-systems
official upstream — a different version family from the fork the ISA code
targets — so this recipe fetches the pinned fork tarball (pinned in
conandata.yml, E277 vendored-dependency pattern) and builds it in-tree as
a static PIC archive (recipe-cmake/CMakeLists.txt).

Tests: the upstream gtest suite (src/test, 58 cases over local manifests
fixtures, no network) is built and executed for real by build() via ctest
(target inputstream.adaptive_test, add_test(manifest_tests ...)), exactly
like the upstream CI ("make CTEST_OUTPUT_ON_FAILURE=1 test").
"""
import os

from conan import ConanFile
from conan.tools.cmake import CMake, CMakeToolchain, cmake_layout
from conan.tools.files import copy, get


class KodiInputstreamAdaptiveConan(ConanFile):
    name = "kodi-inputstream-adaptive"
    version = "21.5.16"
    description = ("Kodi input stream add-on for adaptive streaming "
                   "(DASH/HLS/SmoothStreaming; inputstream.adaptive)")
    license = "GPL-2.0-or-later"
    homepage = "https://github.com/xbmc/inputstream.adaptive"
    url = "https://github.com/xbmc/inputstream.adaptive"
    package_type = "shared-library"

    settings = "os", "compiler", "build_type", "arch"
    options = {"shared": [True, False], "fPIC": [True, False]}
    # The add-on is a dlopen() module for the Kodi host; a static archive has
    # no consumer, so shared is the default.
    default_options = {"shared": True, "fPIC": True}

    generators = "CMakeDeps"
    exports_sources = "recipe-cmake/*", "kodi-dev-kit/*"

    def requirements(self):
        # Published on the ohpcd registry (probed 2026-10-02, same probe as
        # CI L0i). gtest is the upstream test framework only (upstream
        # depends/common pins googletest 1.14.0; upstream FindGtest.cmake floor is
        # gtest>=1.10.0 — the registry gtest/1.17.0 satisfies it (gtest is also what
        # the registry rapidjson/1.1.0.1 recipe requires transitively, keeping a
        # single gtest package in the graph).
        self.requires("pugixml/1.16")
        self.requires("rapidjson/1.1.0.1")
        self.requires("gtest/1.17.0")

    def config_options(self):
        if self.settings.os == "Windows":
            self.options.rm_safe("fPIC")

    def configure(self):
        if self.options.shared:
            self.options.rm_safe("fPIC")

    def layout(self):
        cmake_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)
        # Vendored xbmc Bento4 fork (see module docstring); extracted next to
        # the add-on sources, consumed by recipe-cmake/CMakeLists.txt.
        get(self, **self.conan_data["bento4"], strip_root=True,
            destination="bento4")
        # exports_sources are merged into the source folder BEFORE source()
        # runs, so the tarball extraction would clobber same-named files.
        # recipe-cmake/ and kodi-dev-kit/ are subfolders the tarball does not
        # contain; re-copy them from the recipe folder after extraction
        # (kodi-inputstream-rtmp/21.1.2 precedent).
        copy(self, "*", src=os.path.join(self.recipe_folder, "recipe-cmake"),
             dst=os.path.join(self.source_folder, "recipe-cmake"))
        copy(self, "*", src=os.path.join(self.recipe_folder, "kodi-dev-kit"),
             dst=os.path.join(self.source_folder, "kodi-dev-kit"))

    def generate(self):
        tc = CMakeToolchain(self)
        tc.variables["BUILD_SHARED_LIBS"] = bool(self.options.shared)
        tc.generate()

    def build(self):
        cmake = CMake(self)
        cmake.configure(build_script_folder="recipe-cmake")
        cmake.build()
        # Upstream gtest suite, executed for real (native run on the OHOS
        # device): add_test(manifest_tests inputstream.adaptive_test
        # <src>/src/test/manifests), 58 gtest cases over local fixtures.
        # ctest -V keeps the command line and the full gtest summary in the
        # conan create log (CI L1c evidence); non-zero exit fails the build.
        self.run(f'ctest -V --test-dir "{self.build_folder}"')

    def package(self):
        cmake = CMake(self)
        cmake.install()
        copy(self, "LICENSE.md", src=self.source_folder,
             dst=os.path.join(self.package_folder, "licenses"))
        copy(self, "LICENSES/*", src=self.source_folder,
             dst=os.path.join(self.package_folder, "licenses", "LICENSES"),
             keep_path=False)

    def package_info(self):
        self.cpp_info.libs = ["inputstream.adaptive"]
        # No public headers are installed (the add-on module exposes only its
        # ADDONCREATOR C entry points; Kodi add-on headers are vendored by the
        # consumer recipe when needed).
        self.cpp_info.includedirs = []
        # Self-contained module: Bento4/mpegts/webm_parser/cdm static PIC
        # archives are baked in at build time, pugixml is a static PIC
        # archive baked in too, rapidjson is header-only. The remaining
        # undefined symbols (libc/libdl on OHOS musl) resolve at load in the
        # host process. Consumers need no extra link requirements.
        self.cpp_info.requires = []
