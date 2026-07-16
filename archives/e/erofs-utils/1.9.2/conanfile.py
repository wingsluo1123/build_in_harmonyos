import os
import time

from conan import ConanFile
from conan.tools.files import copy, get, replace_in_file
from conan.tools.gnu import Autotools, AutotoolsToolchain
from conan.tools.layout import basic_layout


class ErofsUtilsConan(ConanFile):
    name = "erofs-utils"
    version = "1.9.2"
    description = "Userspace tools for the EROFS filesystem"
    license = "GPL-2.0-or-later AND MIT"
    homepage = "https://git.kernel.org/pub/scm/linux/kernel/git/xiang/erofs-utils.git"
    settings = "os", "compiler", "build_type", "arch"

    def export_sources(self):
        copy(
            self,
            "*",
            os.path.join(self.recipe_folder, "files"),
            os.path.join(self.export_sources_folder, "files"),
            keep_path=True,
        )

    def layout(self):
        basic_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"][self.version], strip_root=True)
        generated = os.path.join(
            self.export_sources_folder, "files", "autotools-generated"
        )
        copy(self, "*", generated, self.source_folder, keep_path=True)
        self._refresh_autotools_timestamps()

        if str(self.settings.os) == "OHOS":
            replace_in_file(
                self,
                os.path.join(self.source_folder, "configure"),
                "umask 077",
                "umask 022",
            )

    def _refresh_autotools_timestamps(self):
        base = time.time() - 3600
        groups = (
            (["configure.ac", "Makefile.am"], base),
            (["aclocal.m4"], base + 10),
            (["configure", "config.h.in"], base + 20),
        )
        for names, timestamp in groups:
            for name in names:
                path = os.path.join(self.source_folder, name)
                if os.path.exists(path):
                    os.utime(path, (timestamp, timestamp))

        newest = base + 30
        for root, _, files in os.walk(self.source_folder):
            for filename in files:
                if filename == "Makefile.in" or root.endswith(os.sep + "config"):
                    path = os.path.join(root, filename)
                    os.utime(path, (newest, newest))

    def generate(self):
        tc = AutotoolsToolchain(self)
        tc.configure_args.extend(
            [
                "--disable-shared",
                "--enable-static",
                "--disable-multithreading",
                "--disable-lz4",
                "--disable-lzma",
                "--without-zlib",
                "--without-libdeflate",
                "--without-libzstd",
                "--without-qpl",
                "--without-xxhash",
                "--without-libcurl",
                "--without-openssl",
                "--without-libxml2",
                "--without-json-c",
                "--without-libnl3",
                "--disable-ublk",
                "--disable-s3",
                "--disable-oci",
                "--disable-fanotify",
                "--disable-fuse",
                "--without-uuid",
                "--without-selinux",
            ]
        )
        if str(self.settings.os) == "OHOS":
            tc.configure_args.extend(
                [
                    "--build=aarch64-linux-ohos",
                    "--host=aarch64-linux-ohos",
                    "--target=aarch64-linux-ohos",
                ]
            )
        tc.generate()

    def build(self):
        autotools = Autotools(self)
        autotools.configure()
        autotools.make()

    def package(self):
        autotools = Autotools(self)
        autotools.install()
        copy(
            self,
            "COPYING",
            self.source_folder,
            os.path.join(self.package_folder, "licenses"),
        )

    def package_info(self):
        self.cpp_info.bindirs = ["bin", "sbin"]
        self.cpp_info.libdirs = []
