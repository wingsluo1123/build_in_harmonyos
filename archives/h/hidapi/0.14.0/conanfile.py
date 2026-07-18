#!/usr/bin/env python3
"""Conan recipe — hidapi 0.14.0 (CMake).

HIDAPI is a multi-platform library for communicating with USB and Bluetooth HID devices.
Uses hidraw backend with stub libudev (libudev not available on HarmonyOS).
"""
import os

from conan import ConanFile
from conan.tools.files import get, apply_conandata_patches, export_conandata_patches, replace_in_file
from conan.tools.cmake import CMake, CMakeToolchain, cmake_layout


class HidapiConan(ConanFile):
    name = "hidapi"
    version = "0.14.0"
    description = "Multi-platform library for communicating with USB and Bluetooth HID devices"
    license = "BSD-3-Clause"
    homepage = "https://github.com/libusb/hidapi"
    url = ""

    settings = "os", "compiler", "build_type", "arch"

    def export_sources(self):
        export_conandata_patches(self)

    def layout(self):
        cmake_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def generate(self):
        tc = CMakeToolchain(self)
        tc.variables["HIDAPI_NO_ICONV"] = "ON"
        tc.variables["HIDAPI_WITH_LIBUSB"] = "OFF"
        tc.variables["BUILD_SHARED_LIBS"] = "OFF"
        tc.generate()

    def build(self):
        apply_conandata_patches(self)

        # Create stub libudev (not available on HarmonyOS)
        stub_dir = os.path.join(self.source_folder, "stub-udev")
        os.makedirs(stub_dir, exist_ok=True)

        libudev_h = """#ifndef LIBUDEV_H
#define LIBUDEV_H
#include <sys/types.h>
struct udev;
struct udev_device;
struct udev_enumerate;
struct udev_list_entry;
struct udev *udev_new(void);
struct udev *udev_unref(struct udev *udev);
struct udev_device *udev_device_new_from_devnum(struct udev *udev, char type, dev_t devnum);
struct udev_device *udev_device_new_from_subsystem_sysname(struct udev *udev, const char *subsystem, const char *sysname);
struct udev_device *udev_device_new_from_syspath(struct udev *udev, const char *syspath);
struct udev_device *udev_device_unref(struct udev_device *udev_device);
const char *udev_device_get_devnode(struct udev_device *udev_device);
struct udev_device *udev_device_get_parent(struct udev_device *udev_device);
const char *udev_device_get_sysattr_value(struct udev_device *udev_device, const char *sysattr);
struct udev_list_entry *udev_device_get_devlinks_list_entry(struct udev_device *udev_device);
struct udev_enumerate *udev_enumerate_new(struct udev *udev);
int udev_enumerate_add_match_subsystem(struct udev_enumerate *udev_enumerate, const char *subsystem);
int udev_enumerate_scan_devices(struct udev_enumerate *udev_enumerate);
struct udev_list_entry *udev_enumerate_get_list_entry(struct udev_enumerate *udev_enumerate);
struct udev_enumerate *udev_enumerate_unref(struct udev_enumerate *udev_enumerate);
struct udev_list_entry *udev_list_entry_get_next(struct udev_list_entry *list_entry);
const char *udev_list_entry_get_name(struct udev_list_entry *list_entry);
#define udev_list_entry_foreach(iterator, first) \\
    for (iterator = (first); iterator != NULL; iterator = udev_list_entry_get_next(iterator))
#endif
"""
        with open(os.path.join(stub_dir, "libudev.h"), "w") as f:
            f.write(libudev_h)

        stub_c = """#include <stddef.h>
#include "libudev.h"
struct udev *udev_new(void) { return NULL; }
struct udev *udev_unref(struct udev *udev) { (void)udev; return NULL; }
struct udev_device *udev_device_new_from_devnum(struct udev *udev, char t, dev_t d) { (void)udev; (void)t; (void)d; return NULL; }
struct udev_device *udev_device_new_from_subsystem_sysname(struct udev *udev, const char *s, const char *n) { (void)udev; (void)s; (void)n; return NULL; }
struct udev_device *udev_device_new_from_syspath(struct udev *udev, const char *p) { (void)udev; (void)p; return NULL; }
struct udev_device *udev_device_unref(struct udev_device *d) { (void)d; return NULL; }
const char *udev_device_get_devnode(struct udev_device *d) { (void)d; return NULL; }
struct udev_device *udev_device_get_parent(struct udev_device *d) { (void)d; return NULL; }
const char *udev_device_get_sysattr_value(struct udev_device *d, const char *a) { (void)d; (void)a; return NULL; }
struct udev_list_entry *udev_device_get_devlinks_list_entry(struct udev_device *d) { (void)d; return NULL; }
struct udev_enumerate *udev_enumerate_new(struct udev *udev) { (void)udev; return NULL; }
int udev_enumerate_add_match_subsystem(struct udev_enumerate *e, const char *s) { (void)e; (void)s; return 0; }
int udev_enumerate_scan_devices(struct udev_enumerate *e) { (void)e; return 0; }
struct udev_list_entry *udev_enumerate_get_list_entry(struct udev_enumerate *e) { (void)e; return NULL; }
struct udev_enumerate *udev_enumerate_unref(struct udev_enumerate *e) { (void)e; return NULL; }
struct udev_list_entry *udev_list_entry_get_next(struct udev_list_entry *e) { (void)e; return NULL; }
const char *udev_list_entry_get_name(struct udev_list_entry *e) { (void)e; return NULL; }
"""
        with open(os.path.join(stub_dir, "stub-udev.c"), "w") as f:
            f.write(stub_c)

        # Create stub libudev.pc for pkg-config
        pc_dir = os.path.join(stub_dir, "pkgconfig")
        os.makedirs(pc_dir, exist_ok=True)
        libudev_pc = f"""prefix={stub_dir}
libdir=${{prefix}}
includedir=${{prefix}}

Name: libudev
Description: stub libudev for HarmonyOS
Version: 1.0
Libs: -L${{libdir}} -ludev_stub
Cflags: -I${{includedir}}
"""
        with open(os.path.join(pc_dir, "libudev.pc"), "w") as f:
            f.write(libudev_pc)

        # Compile stub-udev.c into libudev_stub.a
        cc = os.environ.get("CC", "clang")
        ar = os.environ.get("AR", "llvm-ar")
        self.run(f"{cc} -c -fPIC -I{stub_dir} -o {stub_dir}/stub-udev.o {stub_dir}/stub-udev.c")
        self.run(f"{ar} rcs {stub_dir}/libudev_stub.a {stub_dir}/stub-udev.o")

        # Set PKG_CONFIG_PATH to find stub libudev
        old_pc = os.environ.get("PKG_CONFIG_PATH", "")
        os.environ["PKG_CONFIG_PATH"] = pc_dir + (":" + old_pc if old_pc else "")

        # Modify src/CMakeLists.txt: add HarmonyOS to Linux check
        src_cmake = os.path.join(self.source_folder, "src", "CMakeLists.txt")
        if os.path.isfile(src_cmake):
            replace_in_file(self, src_cmake,
                'if(CMAKE_SYSTEM_NAME MATCHES "Linux")',
                'if(CMAKE_SYSTEM_NAME MATCHES "Linux" OR CMAKE_SYSTEM_NAME STREQUAL "HarmonyOS")')
            # Don't force HIDAPI_WITH_LIBUSB=ON for non-Linux
            replace_in_file(self, src_cmake,
                'set(HIDAPI_WITH_LIBUSB ON)',
                'set(HIDAPI_WITH_LIBUSB OFF)')

        # Add compile options to bypass stub libudev implicit declaration errors
        top_cmake = os.path.join(self.source_folder, "CMakeLists.txt")
        if os.path.isfile(top_cmake):
            replace_in_file(self, top_cmake,
                "project(hidapi LANGUAGES C)",
                'project(hidapi LANGUAGES C)\nadd_compile_options(-Wno-error=implicit-function-declaration -Wno-error=int-conversion)')

        # Add stub-udev.c to the hidraw target so it's compiled into the library
        src_cmake = os.path.join(self.source_folder, "src", "CMakeLists.txt")
        if os.path.isfile(src_cmake):
            replace_in_file(self, src_cmake,
                'add_subdirectory("${PROJECT_ROOT}/linux" linux)',
                'add_subdirectory("${PROJECT_ROOT}/linux" linux)\nif(TARGET hidapi_hidraw)\n    target_sources(hidapi_hidraw PRIVATE ${PROJECT_ROOT}/stub-udev/stub-udev.c)\n    target_include_directories(hidapi_hidraw PRIVATE ${PROJECT_ROOT}/stub-udev)\nendif()')

        cmake = CMake(self)
        cmake.configure(cli_args=["-DCMAKE_POLICY_VERSION_MINIMUM=3.5"])
        cmake.build()

    def package(self):
        cmake = CMake(self)
        cmake.install()

    def package_info(self):
        self.cpp_info.libs = ["hidapi-hidraw"]
