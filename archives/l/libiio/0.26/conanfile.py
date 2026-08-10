#!/usr/bin/env python3
"""Conan recipe — libiio 0.26 (CMake)"""
from conan import ConanFile
from conan.tools.files import get, apply_conandata_patches, export_conandata_patches
from conan.tools.cmake import CMake, CMakeToolchain, cmake_layout


class LibiioConan(ConanFile):
    name = "libiio"
    version = "0.26"
    description = "Library for interfacing with Linux IIO (Industrial I/O) devices"
    license = "LGPL-2.1-or-later"
    homepage = "https://github.com/analogdevicesinc/libiio"

    package_type = "library"

    settings = "os", "compiler", "build_type", "arch"
    options = {"shared": [True, False]}
    default_options = {"shared": True}

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        self.requires("libusb/1.0.27")
        self.requires("libxml2/2.15.3")

    def layout(self):
        cmake_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def generate(self):
        tc = CMakeToolchain(self)
        tc.variables["BUILD_SHARED_LIBS"] = "ON" if self.options.shared else "OFF"
        # Enable all default-ON backends (no trimming)
        tc.variables["WITH_USB_BACKEND"] = "ON"
        tc.variables["WITH_XML_BACKEND"] = "ON"
        tc.variables["WITH_NETWORK_BACKEND"] = "ON"
        tc.variables["WITH_LOCAL_BACKEND"] = "ON"
        tc.variables["WITH_IIOD"] = "ON"
        tc.variables["WITH_TESTS"] = "ON"
        # Platform-incompatible sub-features (not trimming — these require
        # kernel-level or system-service infrastructure not available on OHOS)
        tc.variables["HAVE_DNS_SD"] = "OFF"  # avahi not available on OHOS
        tc.variables["WITH_AIO"] = "OFF"     # libaio not available on OHOS
        tc.variables["WITH_IIOD_USBD"] = "OFF"  # functionfs.h not available
        tc.variables["WITH_SERIAL_BACKEND"] = "OFF"  # OFF by default, libserialport not in conan
        tc.variables["WITH_MAN"] = "OFF"
        tc.variables["WITH_DOC"] = "OFF"
        tc.variables["INSTALL_UDEV_RULE"] = "OFF"  # no udev on OHOS
        tc.generate()

    def build(self):
        apply_conandata_patches(self)
        cmake = CMake(self)
        cmake.configure()
        cmake.build()

    def package(self):
        cmake = CMake(self)
        cmake.install()

    def package_info(self):
        self.cpp_info.libs = ["iio"]
        self.cpp_info.set_property("cmake_file_name", "libiio")
        self.cpp_info.set_property("pkg_config_name", "libiio")
