#!/usr/bin/env python3
"""Conan recipe — ecdsautils 0.4.2 (CMake, BSD-2-Clause).

Upstream: https://github.com/freifunk-gluon/ecdsautils tag v0.4.2
Build system: CMake (top-level CMakeLists.txt, cmake_minimum_required 2.8.3).
Hard dependency: libuecc (upstream does `find_package(libuecc REQUIRED)`).

Upstream has no automated test suite (N_static = 0): the tarball contains no
test sources and no enable_testing()/add_test()/ctest reference at any level.
Verification is therefore provided by the consumer test in test_package/.
"""
import os

from conan import ConanFile
from conan.tools.cmake import CMake, CMakeToolchain, cmake_layout
from conan.tools.files import apply_conandata_patches, export_conandata_patches, get


class EcdsautilsConan(ConanFile):
    name = "ecdsautils"
    version = "0.4.2"
    description = "Tiny command line tools and library for ECDSA signature creation and verification"
    license = "BSD-2-Clause"
    homepage = "https://github.com/freifunk-gluon/ecdsautils"
    url = "https://github.com/freifunk-gluon/ecdsautils"

    package_type = "library"

    settings = "os", "compiler", "build_type", "arch"
    options = {"shared": [True, False]}
    default_options = {"shared": False}

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        # Our PUBLIC header include/ecdsautil/ecdsautil/ecdsa.h does
        # `#include <libuecc/ecc.h>`, so consumers need libuecc's headers too.
        # Conan 2's check_downstream() sets headers=False for the transitive
        # require whenever the *middle* package type is STATIC (a static archive
        # is fully resolved at its own link time), which would strip
        # libuecc's include dir from every consumer. Declare the traits.
        self.requires("libuecc/7.0", transitive_headers=True, transitive_libs=True)

    def layout(self):
        cmake_layout(self)

    def source(self):
        # The official codeload URL ends in ".../refs/tags/v0.4.2" — no file
        # extension — so get() deduces the name "v0.4.2" and unzip() then falls
        # back to the zip extractor: "BadZipFile: File is not a zip file".
        # Give the download an explicit .tar.gz name (手册/07 §12.3).
        get(self, **self.conan_data["sources"], filename="ecdsautils-0.4.2.tar.gz",
            strip_root=True)

    def generate(self):
        tc = CMakeToolchain(self)

        # Upstream declares cmake_minimum_required(VERSION 2.8.3); CMake >= 4.0
        # refuses policy versions older than 3.5 (platform ships CMake 4.1.2).
        tc.cache_variables["CMAKE_POLICY_VERSION_MINIMUM"] = "3.5"
        # Upstream defaults to shared; map our option onto its cache variable.
        tc.cache_variables["BUILD_SHARED_LIBS"] = bool(self.options.shared)
        # `cmake --install` rewrites RPATH bytes on musl -> skip install RPATH.
        tc.cache_variables["CMAKE_SKIP_INSTALL_RPATH"] = "ON"

        # The top-level CMakeLists does `set(CMAKE_MODULE_PATH ${ECDSAUTIL_SOURCE_DIR})`,
        # so upstream's Findlibuecc.cmake always wins module mode. That module
        # resolves libuecc through find_path()/find_library(). The .pc file shipped
        # inside the conan package carries the *builder's* absolute prefix, so
        # pkg-config hints are stale on any other host -> pre-seed the two cache
        # entries straight from the Conan dependency package folder.
        uecc = self.dependencies["libuecc"]
        inc_dir = os.path.join(uecc.package_folder, "include", "libuecc-7")
        if not os.path.isdir(inc_dir):
            inc_dir = os.path.join(uecc.package_folder, "include")
        # Pick the libuecc artifact that actually exists on disk — never infer a
        # file name from *our own* shared option (that has no causal relation to
        # what libuecc shipped). Prefer the flavour that matches how we link:
        # a shared libecdsautil.so should link libuecc.so, a static one libuecc.a.
        # If neither candidate exists, leave LIBUECC_LIBRARIES unset so that
        # upstream find_library() runs its normal search instead of pointing at
        # a non-existent path.
        lib_dir = os.path.join(uecc.package_folder, "lib")
        preferred = ["libuecc.so", "libuecc.a"] if bool(self.options.shared) \
            else ["libuecc.a", "libuecc.so"]
        found = next((os.path.join(lib_dir, n) for n in preferred
                      if os.path.isfile(os.path.join(lib_dir, n))), None)
        tc.cache_variables["LIBUECC_INCLUDE_DIR"] = inc_dir
        if found:
            tc.cache_variables["LIBUECC_LIBRARIES"] = found

        tc.generate()

    def build(self):
        apply_conandata_patches(self)
        cmake = CMake(self)
        cmake.configure()
        cmake.build()
        # Upstream ships no test suite (N_static = 0), so there is no test to run.

    def package(self):
        cmake = CMake(self)
        cmake.install()

    def package_info(self):
        # Upstream installs the archive as lib<output-name>.a with
        # `set_target_properties(libecdsautil ... OUTPUT_NAME ecdsautil)`.
        self.cpp_info.libs = ["ecdsautil"]
        # Headers land in <prefix>/include/ecdsautil-0.4.2/ecdsautil/*.h, so the
        # documented `#include <ecdsautil/ecdsa.h>` needs that parent directory.
        self.cpp_info.includedirs = ["include/ecdsautil-0.4.2"]
        self.cpp_info.bindirs = ["bin"]
        self.cpp_info.libdirs = ["lib"]
