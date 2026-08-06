#!/usr/bin/env python3
"""Conan recipe for nmap 7.95 — Network security scanner and discovery tool.
nmap is a command-line tool (executable), not a library.
Build system: autotools (configure + make).
"""
import os
import shutil

from conan import ConanFile
from conan.tools.files import get, apply_conandata_patches, export_conandata_patches
from conan.tools.gnu import AutotoolsToolchain
from conan.tools.layout import basic_layout


class NmapConan(ConanFile):
    name = "nmap"
    version = "7.95"
    description = "Network security scanner and discovery tool"
    license = "GPL-2.0"
    homepage = "https://nmap.org/"
    url = ""

    package_type = "application"
    settings = "os", "compiler", "build_type", "arch"

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        pass

    def layout(self):
        basic_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def generate(self):
        tc = AutotoolsToolchain(self)
        tc.generate()

    def build(self):
        apply_conandata_patches(self)
        self._fix_umask_all()
        self._fix_config_sub_all()
        self._fix_sockaddr_storage()
        self._touch_source_files()
        os.chdir(self.source_folder)
        self.run("./configure --build=aarch64-unknown-linux-ohos "
                 "--host=aarch64-unknown-linux-ohos "
                 "--without-zenmap --without-ndiff --without-nmap-update --prefix=",
                 env="conanbuild")
        self.run("make nmap -j1", env="conanbuild")
        self.run("make -C ncat", env="conanbuild")
        self.run("make -C nping", env="conanbuild")

    def _fix_umask_all(self):
        for root, _, files in os.walk(self.source_folder):
            for fname in files:
                if fname == "configure":
                    fpath = os.path.join(root, fname)
                    with open(fpath, "r") as f:
                        content = f.read()
                    if "umask 077" in content:
                        content = content.replace("umask 077", "umask 022")
                        with open(fpath, "w") as f:
                            f.write(content)

    def _fix_config_sub_all(self):
        for root, _, files in os.walk(self.source_folder):
            for fname in files:
                if fname == "config.sub":
                    self._fix_config_sub(os.path.join(root, fname))

    def _fix_config_sub(self, path):
        with open(path, "r") as f:
            content = f.read()
        if "| ohos*" in content or "| linux-ohos*" in content:
            return
        if "linux-uclibc*" in content:
            content = content.replace("linux-uclibc*", "linux-uclibc* | linux-ohos*")
        elif "linux-android*" in content:
            content = content.replace("linux-android*", "linux-android* | linux-ohos*")
        elif "linux-musl*" in content:
            content = content.replace("linux-musl*", "linux-musl* | linux-ohos*")
        if " | ohos*" not in content and "android*" in content:
            content = content.replace("android*", "android* | ohos*")
        with open(path, "w") as f:
            f.write(content)

    def _fix_sockaddr_storage(self):
        """Fix sockaddr_storage redefinition between sys/socket.h and linux/socket.h."""
        # Fix libpcap/pcap-linux.c
        pcap_file = os.path.join(self.source_folder, "libpcap", "pcap-linux.c")
        if os.path.isfile(pcap_file):
            self._add_sockaddr_guard(pcap_file, "linux/if.h")
        # Fix libdnet-stripped/src/tun-linux.c
        dnet_file = os.path.join(self.source_folder, "libdnet-stripped", "src", "tun-linux.c")
        if os.path.isfile(dnet_file):
            self._add_sockaddr_guard(dnet_file, "linux/if.h")

    def _add_sockaddr_guard(self, filepath, header):
        """Add #define guard around #include <header> to avoid sockaddr_storage redefinition."""
        with open(filepath, "r") as f:
            content = f.read()
        include_line = f"#include <{header}>"
        if include_line not in content or "__OHOS__" in content:
            return  # Already fixed or not found
        guard = (
            f"#ifdef __OHOS__\n"
            f"/* OHOS: Avoid sockaddr_storage redefinition between sys/socket.h and linux/socket.h */\n"
            f"#define sockaddr_storage __linux_sockaddr_storage\n"
            f"#endif\n"
            f"{include_line}\n"
            f"#ifdef __OHOS__\n"
            f"#undef sockaddr_storage\n"
            f"#endif\n"
        )
        content = content.replace(include_line, guard, 1)
        with open(filepath, "w") as f:
            f.write(content)

    def _touch_source_files(self):
        """Set source file timestamps old so generated files appear newer."""
        old_ts = 946684800  # 2000-01-01
        source_exts = (".am", ".ac", ".m4")
        source_files = ("Makefile.am", "configure.ac", "acinclude.m4", "aclocal.m4")
        for root, _, files in os.walk(self.source_folder):
            for fname in files:
                fpath = os.path.join(root, fname)
                if fname in source_files or fname.endswith(source_exts):
                    if os.path.isfile(fpath):
                        os.utime(fpath, (old_ts, old_ts))

    def package(self):
        bin_dir = os.path.join(self.package_folder, "bin")
        os.makedirs(bin_dir, exist_ok=True)
        for binary in ["nmap", "ncat/ncat", "nping/nping"]:
            src = os.path.join(self.source_folder, binary)
            dst = os.path.join(bin_dir, os.path.basename(binary))
            if os.path.isfile(src):
                shutil.copy2(src, dst)
        data_dir = os.path.join(self.package_folder, "share", "nmap")
        os.makedirs(data_dir, exist_ok=True)
        for f in os.listdir(self.source_folder):
            if f.startswith("nmap-") and os.path.isfile(os.path.join(self.source_folder, f)):
                shutil.copy2(os.path.join(self.source_folder, f), os.path.join(data_dir, f))

    def package_info(self):
        self.cpp_info.bindirs = ["bin"]
