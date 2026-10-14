#!/usr/bin/env python3
"""Conan recipe — libcuckoo 0.3.1.1 (header-only cuckoo hashing library).

Notes:
- Header-only: package() installs headers only (package_type=header-library).
- CMakeLists.txt uses cmake_minimum_required(VERSION 3.1.0), removed in
  CMake 4.x -> patches/0001-cmake-min-version.patch bumps it to 3.5.0...3.31.
- Upstream unit tests (Catch v1.5.9, 80 TEST_CASEs) and stress tests are
  built and run in build() so that conan create verifies them on OHOS:
  * 0002-catch-urng-result-type.patch: OHOS libc++ rejects Catch v1.5.9's
    RandomNumberGenerator (signed result_type) per __libcpp_random_is_valid_urng.
  * 0003-c-interface-tmpfile-ohos.patch: /tmp is read-only on OHOS and musl
    tmpfile() hardcodes /tmp; test now uses mkstemp in TMPDIR.
"""
from conan import ConanFile
from conan.tools.build import can_run
from conan.tools.cmake import CMake, CMakeToolchain, cmake_layout
from conan.tools.files import apply_conandata_patches, export_conandata_patches, get


class LibcuckooConan(ConanFile):
    name = "libcuckoo"
    version = "0.3.1.1"
    description = "High-performance concurrent hash table based on cuckoo hashing"
    license = "Apache-2.0"
    homepage = "https://github.com/efficient/libcuckoo"
    url = ""  # CI fills this

    package_type = "header-library"
    settings = "os", "compiler", "build_type", "arch"
    no_copy_source = True

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        pass

    def layout(self):
        cmake_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def generate(self):
        tc = CMakeToolchain(self)
        # NOTE: cmake_minimum_required(3.1.0) is fixed by patches/0001-cmake-min-version.patch.
        # A CMAKE_POLICY_VERSION_MINIMUM CACHE var set here does NOT work: the toolchain
        # file is loaded at project(), i.e. AFTER cmake_minimum_required is parsed.
        # Enable upstream tests (unit + stress) so they are built and run in
        # build(). Universal benchmark is a benchmark, not a test — keep off.
        tc.variables["BUILD_UNIT_TESTS"] = "ON"
        tc.variables["BUILD_STRESS_TESTS"] = "ON"
        tc.variables["BUILD_UNIVERSAL_BENCHMARK"] = "OFF"
        tc.variables["BUILD_EXAMPLES"] = "OFF"
        tc.generate()

    def build(self):
        apply_conandata_patches(self)
        cmake = CMake(self)
        cmake.configure()
        cmake.build()
        # Run upstream tests (unit_tests: Catch framework; stress_checked /
        # stress_unchecked with upstream default parameters). Gate the build:
        # a real regression must fail conan create.
        if can_run(self):
            cmake.test()

    def package(self):
        cmake = CMake(self)
        cmake.install()

    def package_info(self):
        # Header-only library: no libs to link
        self.cpp_info.bindirs = []
        self.cpp_info.libdirs = []
