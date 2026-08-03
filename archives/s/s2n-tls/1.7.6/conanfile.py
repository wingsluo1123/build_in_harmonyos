#!/usr/bin/env python3
"""Conan recipe for s2n-tls — CMake build system.

s2n-tls is an AWS TLS implementation that depends on aws-lc for
cryptographic primitives. libcrypto.a from aws-lc is statically
linked into libs2n.so at build time.

s2n-tls is NOT a system-name library, so it defaults to shared linking.
"""
from conan import ConanFile
from conan.tools.files import get, apply_conandata_patches, export_conandata_patches
from conan.tools.cmake import CMake, CMakeToolchain, cmake_layout


class S2nTlsConan(ConanFile):
    name = "s2n-tls"
    version = "1.7.6"
    description = "AWS implementation of the TLS/SSL protocol, designed for simplicity and security"
    license = "Apache-2.0"
    homepage = "https://github.com/aws/s2n-tls"
    url = "https://github.com/aws/s2n-tls"  # CI this

    package_type = "library"

    settings = "os", "compiler", "build_type", "arch"
    options = {"shared": [True, False]}
    default_options = {"shared": True}

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        self.requires("aws-lc/5.4.0")

    def layout(self):
        cmake_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def generate(self):
        tc = CMakeToolchain(self)
        # s2n-tls uses find_package(crypto) to locate aws-lc's libcrypto.
        # The aws-lc binary package ships crypto-config.cmake in its
        # lib/crypto/cmake/ directory. Setting CMAKE_PREFIX_PATH to the
        # aws-lc package folder allows CMake to find it.
        aws_lc = self.dependencies["aws-lc"]
        tc.variables["CMAKE_PREFIX_PATH"] = aws_lc.package_folder
        tc.variables["BUILD_TESTING"] = "ON"
        tc.variables["SEARCH_LIBCRYPTO"] = "ON"
        # Disable warnings-as-errors to avoid build failures from
        # platform-specific compiler warnings in test code.
        tc.variables["UNSAFE_TREAT_WARNINGS_AS_ERRORS"] = "OFF"
        # Integration tests require Python pytest + s2nc/s2nd, not available
        tc.variables["S2N_INTEG_TESTS"] = "OFF"
        tc.generate()

    def build(self):
        apply_conandata_patches(self)
        cmake = CMake(self)
        cmake.configure()
        cmake.build()
        # ── 上游官方测试 (必做) ──
        # s2n_stacktrace_test 因 OHOS 不支持 execinfo/backtrace 而豁免
        self.run(
            "ctest -E s2n_stacktrace_test --output-on-failure",
            env="conanrun",
        )

    def package(self):
        cmake = CMake(self)
        cmake.install()

    def package_info(self):
        self.cpp_info.set_property("cmake_file_name", "s2n-tls")
        self.cpp_info.set_property("cmake_target_name", "s2n-tls::s2n-tls")
        self.cpp_info.libs = ["s2n"]
        if self.settings.os in ("Linux", "OHOS"):
            self.cpp_info.system_libs = ["dl", "rt", "pthread"]
