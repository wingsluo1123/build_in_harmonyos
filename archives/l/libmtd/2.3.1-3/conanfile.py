#!/usr/bin/env python3
"""Conan recipe for libmtd 2.3.1-3 (mtd-utils 2.3.1 lib/ artifacts).

Packages the four MTD/UBI helper C libraries produced by the mtd-utils
source tree (all `noinst_LIBRARIES`, so package() installs them manually):

- libmtd.a      : /dev/mtd* MEM* ioctl wrappers (libmtd.h)
- libubi.a      : /dev/ubi_ctrl + /dev/ubiN UBI_IOC* ioctl wrappers (libubi.h)
- libubigen.a   : UBI image generation helpers (libubigen.h)
- libscan.a     : UBIFS/UBI volume table scan helpers (libscan.h)
- libmissing.a  : musl/mini libc compatibility shims (backtrace etc.)

Zero third-party dependencies: link-time libc only + kernel UAPI headers
shipped under include/mtd/.
"""
import os

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.files import get, apply_conandata_patches, copy, export_conandata_patches
from conan.tools.gnu import Autotools, AutotoolsToolchain
from conan.tools.layout import basic_layout


class LibmtdConan(ConanFile):
    name = "libmtd"
    version = "2.3.1-3"
    description = "MTD/UBI flash ioctl wrapper libraries (libmtd/libubi/libubigen/libscan) from mtd-utils"
    license = "GPL-2.0-or-later"
    homepage = "https://git.infradead.org/mtd-utils.git"
    url = "https://gitcode.com/OpenHarmonyPCDeveloper/build_in_harmonyos"

    package_type = "library"
    # Static-only artifact: upstream builds noinst static archives (.a) and
    # provides no libtool shared build for lib/.
    settings = "os", "compiler", "build_type", "arch"
    options = {"shared": [True, False], "fPIC": [True, False]}
    default_options = {"shared": False, "fPIC": True}

    def config_options(self):
        if self.settings.os == "Windows":
            del self.options.fPIC

    def configure(self):
        if self.options.shared:
            # lib/ has no libtool shared build upstream — only static .a.
            raise ConanInvalidConfiguration(
                "libmtd upstream (mtd-utils lib/) provides static archives "
                "only; shared=True is not supported"
            )

    no_copy_source = True

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
        # Disable every CLI tool: this package ships the lib/ artifacts only.
        # Without these the configure step hard-requires optional deps
        # (libuuid/openssl/libselinux/lzo/zstd) that the libraries never use.
        tc.configure_args.append("--without-tests")
        tc.configure_args.append("--without-lsmtd")
        tc.configure_args.append("--without-jffs")
        tc.configure_args.append("--without-ubifs")
        if os.path.isdir("/system/bin"):
            # HarmonyOS device host: autoconf's AC_PROG_MKDIR_P falls back to
            # install-sh when HMDFS refuses symlink creation for /bin/mkdir;
            # CONFIG_SHELL keeps the freshly-extracted configure script inside
            # a trusted shell interpreter.
            tc.configure_args.append("MKDIR_P=/system/bin/mkdir -p")
            tc.configure_args.append("CONFIG_SHELL=/system/bin/sh")
        tc.generate()

    def build(self):
        apply_conandata_patches(self)
        autotools = Autotools(self)
        autotools.configure()
        # Only the library targets — every mtd-utils binary stays unbuilt.
        autotools.make(
            args=["libmtd.a", "libmissing.a", "libubi.a", "libubigen.a", "libscan.a"]
        )

    def package(self):
        copy(self, "COPYING", src=self.source_folder, dst=os.path.join(self.package_folder, "licenses"))
        # Public headers: libmtd.h / libubi.h / libubigen.h / libscan.h plus
        # the kernel UAPI headers under include/mtd/ (libubi.h includes
        # <mtd/ubi-user.h>). Internal headers (common.h etc.) need generated
        # config.h and are intentionally NOT shipped.
        inc = os.path.join(self.package_folder, "include")
        copy(self, "libmtd.h", src=os.path.join(self.source_folder, "include"), dst=inc)
        copy(self, "libubi.h", src=os.path.join(self.source_folder, "include"), dst=inc)
        copy(self, "libubigen.h", src=os.path.join(self.source_folder, "include"), dst=inc)
        copy(self, "libscan.h", src=os.path.join(self.source_folder, "include"), dst=inc)
        copy(self, "*.h", src=os.path.join(self.source_folder, "include", "mtd"), dst=os.path.join(inc, "mtd"))
        copy(self, "*.a", src=self.build_folder,
             dst=os.path.join(self.package_folder, "lib"), keep_path=False)

    def package_info(self):
        self.cpp_info.includedirs = ["include"]
        self.cpp_info.libdirs = ["lib"]
        # Consumer link order matters: libmtd.a references libmissing.a symbols
        # (backtrace shims when the libc lacks them).
        self.cpp_info.libs = ["mtd", "ubi", "ubigen", "scan", "missing"]
