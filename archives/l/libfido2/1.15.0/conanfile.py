#!/usr/bin/env python3
"""Conan recipe — libfido2 1.15.0 (CMake).

libfido2 provides library functionality and command-line tools to
communicate with a FIDO device over USB or NFC, and to verify attestation
and assertion signatures.
"""
import os

from conan import ConanFile
from conan.tools.files import get, apply_conandata_patches, export_conandata_patches
from conan.tools.cmake import CMake, CMakeToolchain, cmake_layout


class Libfido2Conan(ConanFile):
    name = "libfido2"
    version = "1.15.0"
    description = "Library for FIDO2, WebAuthn and FIDO Client to Authenticator Protocol"
    license = "BSD-2-Clause"
    homepage = "https://github.com/Yubico/libfido2"
    url = ""

    settings = "os", "compiler", "build_type", "arch"

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        self.requires("libcbor/0.11.0")
        self.requires("openssl/3.5.6")
        self.requires("zlib/1.3.1")

    def layout(self):
        cmake_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def generate(self):
        tc = CMakeToolchain(self)
        tc.variables["BUILD_TESTS"] = "OFF"
        tc.variables["BUILD_EXAMPLES"] = "OFF"
        tc.variables["BUILD_TOOLS"] = "ON"
        tc.variables["BUILD_MANPAGES"] = "OFF"
        tc.generate()

    def build(self):
        apply_conandata_patches(self)

        # Create stub libudev for HarmonyOS (libudev not available)
        stub_dir = os.path.join(self.source_folder, "src", "stub-udev")
        os.makedirs(stub_dir, exist_ok=True)

        libudev_h = """#ifndef LIBUDEV_H
#define LIBUDEV_H

struct udev;
struct udev_device;
struct udev_enumerate;
struct udev_list_entry;

struct udev *udev_new(void);
struct udev *udev_unref(struct udev *udev);
struct udev_enumerate *udev_enumerate_new(struct udev *udev);
int udev_enumerate_add_match_subsystem(struct udev_enumerate *e, const char *s);
int udev_enumerate_scan_devices(struct udev_enumerate *e);
struct udev_list_entry *udev_enumerate_get_list_entry(struct udev_enumerate *e);
struct udev_enumerate *udev_enumerate_unref(struct udev_enumerate *e);
struct udev_list_entry *udev_list_entry_get_next(struct udev_list_entry *e);
const char *udev_list_entry_get_name(struct udev_list_entry *e);
#define udev_list_entry_foreach(iterator, first) \\
\tfor (iterator = (first); iterator != NULL; iterator = udev_list_entry_get_next(iterator))
struct udev_device *udev_device_new_from_syspath(struct udev *udev, const char *syspath);
const char *udev_device_get_devnode(struct udev_device *dev);
struct udev_device *udev_device_get_parent_with_subsystem_devtype(struct udev_device *dev, const char *subsystem, const char *devtype);
const char *udev_device_get_sysattr_value(struct udev_device *dev, const char *attr);
struct udev_device *udev_device_unref(struct udev_device *dev);

#endif /* LIBUDEV_H */
"""
        with open(os.path.join(stub_dir, "libudev.h"), "w") as f:
            f.write(libudev_h)

        stub_c = """#include <stddef.h>
#include "libudev.h"

struct udev *udev_new(void) { return NULL; }
struct udev *udev_unref(struct udev *udev) { (void)udev; return NULL; }
struct udev_enumerate *udev_enumerate_new(struct udev *udev) { (void)udev; return NULL; }
int udev_enumerate_add_match_subsystem(struct udev_enumerate *e, const char *s) { (void)e; (void)s; return -1; }
int udev_enumerate_scan_devices(struct udev_enumerate *e) { (void)e; return -1; }
struct udev_list_entry *udev_enumerate_get_list_entry(struct udev_enumerate *e) { (void)e; return NULL; }
struct udev_enumerate *udev_enumerate_unref(struct udev_enumerate *e) { (void)e; return NULL; }
struct udev_list_entry *udev_list_entry_get_next(struct udev_list_entry *e) { (void)e; return NULL; }
const char *udev_list_entry_get_name(struct udev_list_entry *e) { (void)e; return NULL; }
struct udev_device *udev_device_new_from_syspath(struct udev *udev, const char *syspath) { (void)udev; (void)syspath; return NULL; }
const char *udev_device_get_devnode(struct udev_device *dev) { (void)dev; return NULL; }
struct udev_device *udev_device_get_parent_with_subsystem_devtype(struct udev_device *dev, const char *subsystem, const char *devtype) { (void)dev; (void)subsystem; (void)devtype; return NULL; }
const char *udev_device_get_sysattr_value(struct udev_device *dev, const char *attr) { (void)dev; (void)attr; return NULL; }
struct udev_device *udev_device_unref(struct udev_device *dev) { (void)dev; return NULL; }
"""
        with open(os.path.join(stub_dir, "stub-udev.c"), "w") as f:
            f.write(stub_c)

        # Add stub-udev.c to CMake build
        src_cmake = os.path.join(self.source_folder, "src", "CMakeLists.txt")
        if os.path.isfile(src_cmake):
            with open(src_cmake, "r") as f:
                content = f.read()
            if "stub-udev.c" not in content:
                content = content.replace(
                    'hid_linux.c hid_unix.c)',
                    'hid_linux.c hid_unix.c ${PROJECT_SOURCE_DIR}/src/stub-udev/stub-udev.c)'
                )
                with open(src_cmake, "w") as f:
                    f.write(content)

        # Set PKG_CONFIG_PATH for pkg-config based dependency detection
        pkg_paths = []
        for dep_name in ["libcbor", "openssl", "zlib"]:
            try:
                dep = self.dependencies[dep_name]
            except Exception:
                continue
            pkg_root = str(getattr(dep, "package_folder", "") or "")
            for libdir in dep.cpp_info.libdirs:
                pkg_dir = os.path.join(pkg_root, str(libdir), "pkgconfig")
                if os.path.isdir(pkg_dir):
                    pkg_paths.append(pkg_dir)
                    # Fix broken .pc files (prefix may be / or point to build dir)
                    for pc_file in os.listdir(pkg_dir):
                        pc_path = os.path.join(pkg_dir, pc_file)
                        if os.path.isfile(pc_path):
                            with open(pc_path, "r") as f:
                                lines = f.readlines()
                            changed = False
                            for i, line in enumerate(lines):
                                stripped = line.strip()
                                # Fix prefix=/ (root, broken zlib)
                                if stripped == "prefix=/":
                                    lines[i] = f"prefix={pkg_root}\n"
                                    changed = True
                                # Fix prefix pointing to build dir (p/b/) instead of package dir
                                elif stripped.startswith("prefix=") and "/p/b/" in stripped:
                                    lines[i] = f"prefix={pkg_root}\n"
                                    changed = True
                            if changed:
                                with open(pc_path, "w") as f:
                                    f.writelines(lines)
        if pkg_paths:
            os.environ["PKG_CONFIG_PATH"] = ":".join(pkg_paths) + ":" + os.environ.get("PKG_CONFIG_PATH", "")

        cmake = CMake(self)
        cmake.configure(cli_args=["-DCMAKE_POLICY_VERSION_MINIMUM=3.5"])
        cmake.build()

    def package(self):
        cmake = CMake(self)
        cmake.install()

    def package_info(self):
        self.cpp_info.libs = ["fido2"]
        self.cpp_info.bindirs = ["bin"]
