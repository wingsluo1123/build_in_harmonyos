#!/usr/bin/env python3
"""Conan recipe for avahi 0.8 — Service Discovery for Linux using mDNS/DNS-SD.

Autotools (configure + make)。按 OHOS 平台裁剪非必要组件,
仅构建客户端/核心/公共库(guile-avahi 等下游只需要 client 库)。
"""
import os

from conan import ConanFile
from conan.tools.files import get, apply_conandata_patches, export_conandata_patches
from conan.tools.gnu import Autotools, AutotoolsDeps, AutotoolsToolchain, PkgConfigDeps
from conan.tools.layout import basic_layout


class AvahiConan(ConanFile):
    name = "avahi"
    version = "0.8"
    description = "Service Discovery for Linux using mDNS/DNS-SD (Bonjour compatible)"
    license = "LGPL-2.1"
    homepage = "https://github.com/avahi/avahi"
    url = "https://github.com/avahi/avahi"

    package_type = "library"

    settings = "os", "compiler", "build_type", "arch"
    options = {"shared": [True, False]}
    default_options = {"shared": False}

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        self.requires("dbus/1.14.10")
        self.requires("libdaemon/0.14")
        self.requires("expat/2.8.2")
        self.requires("libcap/2.69")

    def layout(self):
        basic_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def generate(self):
        tc = AutotoolsToolchain(self)
        # R26: 静态编译,避免污染系统库路径
        if not self.options.shared:
            tc.configure_args.append("--enable-static")
            tc.configure_args.append("--disable-shared")
        # OHOS 平台裁剪:仅构建 client/core/common 库,禁用 GUI/绑定/守护进程相关
        tc.configure_args.append("--with-distro=none")
        tc.configure_args.append("--disable-glib")
        tc.configure_args.append("--disable-gobject")
        tc.configure_args.append("--disable-libevent")
        tc.configure_args.append("--disable-qt3")
        tc.configure_args.append("--disable-qt4")
        tc.configure_args.append("--disable-qt5")
        tc.configure_args.append("--disable-gtk")
        tc.configure_args.append("--disable-gtk3")
        tc.configure_args.append("--disable-python")
        tc.configure_args.append("--disable-pygobject")
        tc.configure_args.append("--disable-python-dbus")
        tc.configure_args.append("--disable-mono")
        tc.configure_args.append("--disable-monodoc")
        tc.configure_args.append("--disable-autoipd")
        tc.configure_args.append("--disable-doxygen-doc")
        tc.configure_args.append("--disable-manpages")
        tc.configure_args.append("--disable-xmltoman")
        tc.configure_args.append("--disable-nls")
        tc.configure_args.append("--disable-gdbm")
        tc.configure_args.append("--disable-dbm")
        tc.configure_args.append("--disable-stack-protector")
        tc.generate()
        AutotoolsDeps(self).generate()
        # avahi configure 通过 pkg-config 检测 dbus-1 >= 0.34，
        # 但 dbus 配方的 pkg_config_name 未声明，PkgConfigDeps 默认生成 dbus.pc。
        # 此处覆盖为 dbus-1，使 PkgConfigDeps 生成 dbus-1.pc 供 configure 找到。
        self.dependencies["dbus"].cpp_info.set_property("pkg_config_name", "dbus-1")
        PkgConfigDeps(self).generate()

    def build(self):
        apply_conandata_patches(self)
        autotools = Autotools(self)
        # G2: conftest 动态链接依赖库（libexpat.so 等），configure 运行检测程序
        # 时若 LD_LIBRARY_PATH 不含依赖库目录会报 "cannot run C compiled programs"。
        old_loader_path = self._configure_loader_path()
        try:
            autotools.configure()
            autotools.make(args=["-j1"])
        finally:
            self._restore_loader_path(old_loader_path)

    def _configure_loader_path(self):
        """把依赖库目录注入 LD_LIBRARY_PATH，供 configure 的 conftest 运行检测使用。"""
        libdirs = []
        for dependency in self.dependencies.values():
            libdirs.extend(dependency.cpp_info.libdirs)
        if not libdirs:
            return None
        current = os.environ.get("LD_LIBRARY_PATH")
        if current:
            libdirs.append(current)
        os.environ["LD_LIBRARY_PATH"] = ":".join(libdirs)
        return current

    @staticmethod
    def _restore_loader_path(value):
        if value is None:
            os.environ.pop("LD_LIBRARY_PATH", None)
        else:
            os.environ["LD_LIBRARY_PATH"] = value

    def package(self):
        autotools = Autotools(self)
        autotools.install()

    def package_info(self):
        self.cpp_info.libs = ["avahi-client", "avahi-common", "avahi-core"]
        self.cpp_info.requires = ["dbus::dbus", "libdaemon::libdaemon", "expat::expat", "libcap::libcap"]
        self.cpp_info.set_property("cmake_file_name", "avahi")
        self.cpp_info.set_property("cmake_target_name", "avahi::avahi")
