#!/usr/bin/env python3
"""Conan recipe for libusb 1.0.27 — cross-platform USB device access library.

libusb is a C library that provides generic access to USB devices on many
platforms (Linux, macOS, Windows, ...). HarmonyOS PC (OHOS) uses the Linux
usbfs/netlink backends with OHOS-specific patches.

Build system: autotools (bootstrap + configure + make)
Product: libusb-1.0 static library (dependency for dfu-util, teensy_loader_cli, ...)
"""
import os

from conan import ConanFile
from conan.tools.files import (
    apply_conandata_patches,
    export_conandata_patches,
    get,
)
from conan.tools.gnu import Autotools, AutotoolsToolchain
from conan.tools.layout import basic_layout


class LibusbConan(ConanFile):
    name = "libusb"
    version = "1.0.27"
    description = "A cross-platform library to access USB devices"
    license = "LGPL-2.1-or-later"
    homepage = "https://libusb.info/"
    url = ""  # CI fills this

    package_type = "library"

    settings = "os", "compiler", "build_type", "arch"
    options = {"shared": [True, False], "fPIC": [True, False]}
    default_options = {"shared": False, "fPIC": True}

    def config_options(self):
        # OHOS 平台: 静态库即可, 移除 shared 选项 (鸿蒙上动态库链接链不完整)
        if self.settings.os == "OHOS":
            self.options.rm_safe("shared")
        if self.settings.os == "Windows":
            self.options.rm_safe("fPIC")
            self.options.rm_safe("shared")

    def configure(self):
        if self.options.get_safe("shared"):
            self.options.rm_safe("fPIC")

    def export_sources(self):
        export_conandata_patches(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)
        # git 源码无 release configure, 先 bootstrap 生成 (autoreconf -fi)
        self.run("sh bootstrap.sh", cwd=self.source_folder)
        # bootstrap 后应用补丁 (configure 补丁针对生成的 configure 文件)
        apply_conandata_patches(self)

    def generate(self):
        tc = AutotoolsToolchain(self)
        # OHOS 平台需显式指定 build 类型, 避免 config.guess 识别失败
        if self.settings.os == "OHOS":
            tc.configure_args.append("--build=aarch64-unknown-linux-gnu")
            # HarmonyOS 无 udev, 禁用其支持
            tc.configure_args.append("--disable-udev")
        tc.generate()

    def build(self):
        autotools = Autotools(self)
        autotools.configure()
        autotools.make()

    def package(self):
        autotools = Autotools(self)
        autotools.install()

    def package_info(self):
        # libusb 安装产物: libusb-1.0.{a,so} + 头文件 libusb.h
        self.cpp_info.libs = ["usb-1.0"]
        self.cpp_info.includedirs = ["include/libusb-1.0"]
        self.cpp_info.set_property("cmake_file_name", "libusb-1.0")
        self.cpp_info.set_property("cmake_target_name", "libusb-1.0::libusb-1.0")
