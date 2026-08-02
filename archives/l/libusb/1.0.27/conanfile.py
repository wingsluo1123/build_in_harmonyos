#!/usr/bin/env python3
"""Conan recipe for libusb 1.0.27 — USB device access library.

Build system: autotools (upstream release tarball already ships `configure`,
so no autoreconf is required).

HarmonyOS/OHOS notes
--------------------
* ``--disable-udev``: HarmonyOS has no libudev. Device enumeration therefore
  falls back to sysfs, which is not reachable inside the sandbox
  (SELinux, errno=13). Consumers should initialise with
  ``libusb_init_context()`` + ``LIBUSB_OPTION_NO_DEVICE_DISCOVERY``.
* ``0004-configure-umask.patch``: HMDFS creates ``umask 077`` temp dirs with
  a setgid bit, which makes ``config.status`` fail with "Permission denied"
  (knowledge id E112). Relaxed to ``umask 022``.
  This is a re-generated variant of the legacy ``0001-configure.patch``,
  which was produced against an ``autoreconf``-regenerated ``configure`` and
  therefore does not apply to the upstream release tarball.
* ``0002-libusb-os-linux_netlink.c.patch``: works around the
  ``sockaddr_storage`` redefinition clash between ``linux/socket.h`` and
  ``sys/socket.h`` (knowledge id E091).
* ``0003-libusb-os-linux_usbfs.c.patch``: ``get_kernel_version()`` cannot
  parse the ``"HongMeng Kernel X.Y.Z"`` uname release string; report a modern
  Linux version instead so the minimum-kernel check passes.
"""
import os

from conan import ConanFile
from conan.tools.files import (
    get,
    rm,
    apply_conandata_patches,
    export_conandata_patches,
)
from conan.tools.gnu import Autotools, AutotoolsToolchain
from conan.tools.layout import basic_layout


class LibusbConan(ConanFile):
    name = "libusb"
    version = "1.0.27"
    description = "USB device access library"
    license = "LGPL-2.1-or-later"
    homepage = "https://libusb.info/"
    url = "https://gitcode.com/OpenHarmonyPCDeveloper/build_in_harmonyos"
    topics = ("usb", "hardware", "driver")

    package_type = "library"

    settings = "os", "compiler", "build_type", "arch"
    options = {"shared": [True, False], "fPIC": [True, False]}
    default_options = {"shared": False, "fPIC": True}

    def export_sources(self):
        export_conandata_patches(self)

    def config_options(self):
        if str(self.settings.os) == "Windows":
            self.options.rm_safe("fPIC")

    def configure(self):
        if self.options.shared:
            self.options.rm_safe("fPIC")
        # Pure C library — no C++ runtime needed in the package id.
        self.settings.rm_safe("compiler.libcxx")
        self.settings.rm_safe("compiler.cppstd")

    def requirements(self):
        pass

    def layout(self):
        basic_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def generate(self):
        tc = AutotoolsToolchain(self)
        # HarmonyOS ships no libudev; without this configure aborts.
        tc.configure_args.append("--disable-udev")
        # Upstream defaults already keep these off, but be explicit so the
        # build stays minimal and reproducible.
        tc.configure_args.append("--disable-examples-build")
        tc.configure_args.append("--disable-tests-build")
        tc.generate()

    def build(self):
        apply_conandata_patches(self)
        autotools = Autotools(self)
        autotools.configure()
        autotools.make()

    def package(self):
        autotools = Autotools(self)
        autotools.install()
        # Libtool archives embed absolute build paths and are not relocatable.
        rm(self, "*.la", self.package_folder, recursive=True)

    def package_info(self):
        self.cpp_info.libs = ["usb-1.0"]
        # Upstream installs headers into <prefix>/include/libusb-1.0/libusb.h;
        # expose both so consumers can use <libusb.h> or <libusb-1.0/libusb.h>.
        self.cpp_info.includedirs = ["include", os.path.join("include", "libusb-1.0")]
        self.cpp_info.set_property("pkg_config_name", "libusb-1.0")
        self.cpp_info.set_property("cmake_file_name", "libusb")
        self.cpp_info.set_property("cmake_target_name", "libusb::libusb")
        # OHOS/musl folds pthread into libc, so only glibc-style targets need
        # an explicit -lpthread.
        if str(self.settings.os) in ("Linux", "FreeBSD"):
            self.cpp_info.system_libs = ["pthread"]
