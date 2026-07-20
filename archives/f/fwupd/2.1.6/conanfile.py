#!/usr/bin/env python3
"""Conan recipe for fwupd 2.1.6 — CLI tool for OHOS.

fwupd is a firmware update daemon. This recipe builds the standalone
CLI tool (fwupdtool) using system-provided libraries (glib, libusb, etc.).
"""
from conan import ConanFile
from conan.tools.files import get, apply_conandata_patches, export_conandata_patches
from conan.tools.meson import Meson, MesonToolchain
import os
import shutil


class FwupdConan(ConanFile):
    name = "fwupd"
    version = "2.1.6"
    description = "Firmware update CLI tool for OpenHarmony PC"
    license = "LGPL-2.1-or-later"
    homepage = "https://github.com/fwupd/fwupd"
    url = ""  # CI fills this

    package_type = "application"

    settings = "os", "compiler", "build_type", "arch"
    options = {"shared": [True, False]}
    default_options = {"shared": False}

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        pass

    def layout(self):
        self.folders.source = "."
        self.folders.build = "build"

    def source(self):
        # Use local work dir for fast source (avoids GitHub download issues)
        src = "/storage/Users/currentUser/builds/fwupd-2.1.6.work"
        if os.path.isdir(src):
            shutil.copytree(src, self.source_folder, dirs_exist_ok=True,
                           ignore=shutil.ignore_patterns('.git', 'build', 'staging'))
            build_dir = os.path.join(self.source_folder, 'build')
            if os.path.isdir(build_dir):
                shutil.rmtree(build_dir)
            # OHOS: copy libusb.h into source root for force-include
            libusb_src = "/storage/Users/currentUser/usr/local/include/libusb-1.0/libusb.h"
            libusb_dst = os.path.join(self.source_folder, "libusb.h")
            if os.path.isfile(libusb_src):
                try:
                    shutil.copy2(libusb_src, libusb_dst)
                    self.output.info(f"Copied libusb.h to source root")
                except Exception as _e:
                    self.output.warning(f"Could not copy libusb.h: {_e}")
        else:
            get(self, **self.conan_data["sources"], strip_root=True)

    def generate(self):
        tc = MesonToolchain(self)

        # R32: OHOS platform compatibility
        is_ohos = self.settings.os == "OHOS"

        # All dependencies come from OHOS system via pkg-config
        # Add system pkg-config paths for glib, libusb, libcurl etc.
        pc_paths = [
            "/storage/Users/currentUser/usr/local/lib/pkgconfig",
            "/storage/Users/currentUser/usr/local/libusb-package/lib/pkgconfig",
            "/data/service/hnp/xz.org/xz_v5.8.2/lib/pkgconfig",
        ]
        valid_paths = [p for p in pc_paths if os.path.isdir(p)]
        if valid_paths:
            tc.pkg_config_path = ":".join(valid_paths)

        tc.project_options["default_library"] = "shared" if self.options.shared else "static"
        tc.project_options["build"] = "standalone"

        # Disable features not needed
        tc.project_options["polkit"] = "disabled"
        tc.project_options["systemd"] = "disabled"
        tc.project_options["plugin_modem_manager"] = "disabled"
        tc.project_options["plugin_uefi_capsule_splash"] = "false"
        tc.project_options["docs"] = "disabled"
        tc.project_options["man"] = "false"
        tc.project_options["tests"] = "false"
        tc.project_options["introspection"] = "disabled"
        tc.project_options["lvfs"] = "disabled"
        tc.project_options["blkid"] = "disabled"
        tc.project_options["bluez"] = "disabled"
        tc.project_options["gnutls"] = "disabled"
        tc.project_options["openssl"] = "disabled"
        tc.project_options["hsi"] = "disabled"
        tc.project_options["passim"] = "disabled"
        tc.project_options["logind"] = "disabled"
        tc.project_options["readline"] = "disabled"
        tc.project_options["bash_completion"] = "false"
        tc.project_options["fish_completion"] = "false"
        tc.project_options["metainfo"] = "false"
        tc.project_options["firmware-packager"] = "false"
        tc.project_options["udev_hotplug"] = "false"
        tc.project_options["libdrm"] = "disabled"
        tc.project_options["libmnl"] = "disabled"
        tc.project_options["qubes"] = "false"
        tc.project_options["vendor_metadata"] = "false"
        tc.project_options["umockdev_tests"] = "disabled"
        tc.project_options["valgrind"] = "disabled"
        tc.project_options["supported_build"] = "disabled"
        tc.project_options["static_analysis"] = "false"

        if is_ohos:
            tc.project_options["vendor_ids_dir"] = "/storage/Users/currentUser/share/hwdata"

        tc.generate()

    def build(self):
        # R32: OHOS builds need special include handling
        is_ohos = self.settings.os == "OHOS"

        # OHOS: expose AR/RANLIB for meson to find static archiver
        old_ar = os.environ.get("AR")
        old_ranlib = os.environ.get("RANLIB")
        os.environ["AR"] = "/data/service/hnp/bin/llvm-ar"
        os.environ["RANLIB"] = "/data/service/hnp/bin/llvm-ranlib"
        try:
            apply_conandata_patches(self)

            # OHOS: copy libusb.h into source tree for -include
            try:
                libusb_src = "/storage/Users/currentUser/usr/local/include/libusb-1.0/libusb.h"
                libusb_dst = os.path.join(self.source_folder, "libusb.h")
                with open(libusb_src) as _fr:
                    _content = _fr.read()
                with open(libusb_dst, 'w') as _fw:
                    _fw.write(_content)
            except Exception as _e:
                self.output.warning(f"Could not copy libusb.h: {_e}")

            # OHOS: add -include libusb.h to top-level meson.build
            top_build = os.path.join(self.source_folder, "meson.build")
            if os.path.isfile(top_build):
                with open(top_build) as _f:
                    _content = _f.read()
                if "force_include_libusb" not in _content:
                    marker = "add_project_arguments(\n  '-DFWUPD_COMPILATION',"
                    replacement = ("# OHOS force_include_libusb\n"
                                   "add_project_arguments('-include', 'libusb.h', language: 'c')\n\n"
                                   "add_project_arguments(\n  '-DFWUPD_COMPILATION',")
                    _content = _content.replace(marker, replacement)
                    with open(top_build, 'w') as _f:
                        _f.write(_content)

            meson = Meson(self)
            meson.configure()
            meson.build()
        finally:
            if old_ar:
                os.environ["AR"] = old_ar
            else:
                os.environ.pop("AR", None)
            if old_ranlib:
                os.environ["RANLIB"] = old_ranlib
            else:
                os.environ.pop("RANLIB", None)

    def package(self):
        meson = Meson(self)
        meson.install()

    def package_info(self):
        self.cpp_info.bindirs = ["bin"]
        self.cpp_info.includedirs = ["include", "include/fwupd-3"]
        self.cpp_info.libs = ["fwupd", "fwupdplugin", "fwupdengine", "fwupdutil"]
