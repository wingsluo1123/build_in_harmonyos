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
        else:
            get(self, **self.conan_data["sources"], strip_root=True)

    def generate(self):
        tc = MesonToolchain(self)

        # R32: OHOS platform compatibility
        is_ohos = self.settings.os == "OHOS"

        # OHOS: system libs from SDK sysroot via pkg-config
        if is_ohos:
            _pc = [
                "/storage/Users/currentUser/usr/local/lib/pkgconfig",
                "/storage/Users/currentUser/usr/local/libusb-package/lib/pkgconfig",
                "/data/service/hnp/xz.org/xz_v5.8.2/lib/pkgconfig",
            ]
            _existing = [p for p in _pc if os.path.isdir(p)]
            if _existing:
                os.environ["PKG_CONFIG_PATH"] = ":".join(_existing)

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

        # cairo/pixman 模式: tc.generate() 后手动编辑 native file 注入 AR/RANLIB
        # MesonToolchain 无 toolchain/pkg_config_path 属性，tc.generate() 不读取它们
        _nf = os.path.join(self.generators_folder, "conan_meson_native.ini")
        if is_ohos and os.path.isfile(_nf):
            _ar = "/data/service/hnp/bin/llvm-ar"
            _rl = "/data/service/hnp/bin/llvm-ranlib"
            if os.path.isfile(_ar) and os.path.isfile(_rl):
                with open(_nf) as _f:
                    _c = _f.read()
                if "[binaries]" in _c and "\nar =" not in _c:
                    _ins = "[binaries]\nar = '%s'\nranlib = '%s'\n" % (_ar, _rl)
                    _c = _c.replace("[binaries]\n", _ins, 1)
                    with open(_nf, "w") as _f:
                        _f.write(_c)

    def build(self):
        apply_conandata_patches(self)
        meson = Meson(self)
        meson.configure()
        meson.build()

    def package(self):
        meson = Meson(self)
        meson.install()

    def package_info(self):
        self.cpp_info.bindirs = ["bin"]
        self.cpp_info.includedirs = ["include", "include/fwupd-3"]
        self.cpp_info.libs = ["fwupd", "fwupdplugin", "fwupdengine", "fwupdutil"]
