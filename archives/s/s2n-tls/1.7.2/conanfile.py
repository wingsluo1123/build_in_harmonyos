#!/usr/bin/env python3
"""Conan recipe for s2n-tls v1.7.2 — AWS TLS/SSL implementation.

s2n-tls uses CMake and requires libcrypto (OpenSSL).
The Findcrypto.cmake module in s2n-tls expects find_package(crypto) with
target AWS::crypto, so we map the openssl dependency accordingly.
"""
from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.files import get, apply_conandata_patches, export_conandata_patches
from conan.tools.cmake import CMake, CMakeDeps, CMakeToolchain, cmake_layout


class S2nTlsConan(ConanFile):
    name = "s2n-tls"
    version = "1.7.2"
    description = "AWS implementation of the TLS/SSL protocol, designed for simplicity and security"
    license = "Apache-2.0"
    homepage = "https://github.com/aws/s2n-tls"
    url = "https://github.com/aws/s2n-tls"

    package_type = "library"

    settings = "os", "compiler", "build_type", "arch"
    options = {"shared": [True, False]}
    default_options = {"shared": False}

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        self.requires("openssl/1.1.1w")

    def validate(self):
        # R32: settings.os must check in ("Linux", "OHOS")
        if str(self.settings.os) not in ("Linux", "OHOS"):
            raise ConanInvalidConfiguration("s2n-tls is only supported on Linux and OHOS")

    def layout(self):
        cmake_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def generate(self):
        tc = CMakeToolchain(self)
        tc.variables["BUILD_SHARED_LIBS"] = "ON" if self.options.shared else "OFF"
        tc.variables["BUILD_TESTING"] = "OFF"
        tc.variables["S2N_STACKTRACE"] = "OFF"
        tc.variables["UNSAFE_TREAT_WARNINGS_AS_ERRORS"] = "OFF"
        tc.generate()
        # s2n-tls calls find_package(crypto) and expects target AWS::crypto
        deps = CMakeDeps(self)
        deps.set_property("openssl", "cmake_file_name", "crypto")
        deps.set_property("openssl", "cmake_target_name", "AWS::crypto")
        deps.generate()

    def build(self):
        apply_conandata_patches(self)
        cmake = CMake(self)
        cmake.configure()
        cmake.build()

    def package(self):
        cmake = CMake(self)
        cmake.install()

    def package_info(self):
        self.cpp_info.set_property("cmake_file_name", "s2n")
        self.cpp_info.set_property("cmake_target_name", "AWS::s2n")
        self.cpp_info.libs = ["s2n"]
        if self.settings.os in ("Linux", "OHOS"):
            self.cpp_info.system_libs = ["dl", "rt", "m", "pthread"]
