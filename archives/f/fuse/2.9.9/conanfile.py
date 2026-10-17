#!/usr/bin/env python3
"""Conan recipe for fuse 2.9.9 — FUSE 2.x (Libfuse2 legacy ABI).

Build system: autotools (configure + make).
Outputs: libfuse.a + libulockmgr.a (static, R26), headers, pkg-config,
         bin/fusermount + bin/ulockmgr_server (CLI, R38 → commands.json).

Adaptation points (evidence in notes.md):
  - E011: HMDFS umask 077 breaks config.status temp dirs → patches/0001-configure.patch
  - E007/E072: the bundled config.sub is 2016 vintage; the recipe passes the
    aarch64-unknown-linux-gnu triplet, which that config.sub accepts, so no
    config.guess/config.sub patching is needed.
  - E085: example/ links libfuse.so and hits unimplemented pthread_cancel /
    pthread_setcancelstate on OHOS bionic → --disable-example.
  - R26: libfuse is a system-name library → static only, to avoid /lib pollution.
  - Runtime capability wall: open("/dev/fuse") returns EACCES on OHOS, and the
    upstream install hook's chmod u+s / mknod never take effect (E046), so
    fusermount cannot mount here. test_package asserts the wall (and its
    negative controls) instead of pretending the mount path works.
"""
import os

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.files import (
    apply_conandata_patches,
    rmdir,
    export_conandata_patches,
    get,
)
from conan.tools.gnu import Autotools, AutotoolsToolchain
from conan.tools.layout import basic_layout


class FuseConan(ConanFile):
    name = "fuse"
    version = "2.9.9"
    description = ("FUSE 2.x (Libfuse2 legacy ABI) — Filesystem in Userspace "
                   "library and utilities")
    license = "LGPL-2.1 AND GPL-2.0"
    homepage = "https://github.com/libfuse/libfuse"
    url = ""  # CI fills this

    package_type = "library"

    settings = "os", "arch", "compiler", "build_type"
    options = {
        "shared": [True, False],
        "fPIC": [True, False],
    }
    default_options = {
        "shared": False,
        "fPIC": True,
    }

    def export_sources(self):
        export_conandata_patches(self)

    def config_options(self):
        if self.settings.os == "Windows":
            del self.options.fPIC

    def validate(self):
        # R32: settings.os judgement must use `in ("Linux", "OHOS")`
        if self.settings.os not in ("Linux", "OHOS"):
            raise ConanInvalidConfiguration("fuse is supported only on Linux/OHOS")
        if self.settings.os == "OHOS" and self.settings.arch != "armv8":
            raise ConanInvalidConfiguration("OHOS builds require armv8/aarch64")
        # R26: system-name library — a shared libfuse would pollute /lib
        if self.options.shared:
            raise ConanInvalidConfiguration(
                "fuse is a system-name library; shared option disabled (R26)"
            )

    def requirements(self):
        pass  # no external conan dependencies

    def layout(self):
        basic_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def generate(self):
        tc = AutotoolsToolchain(self)
        # R26: system-name library — static only
        tc.configure_args.extend([
            "--enable-static",
            "--disable-shared",
            "--disable-example",
            "--enable-util",
        ])
        if str(self.settings.os) == "OHOS":
            # The bundled config.sub (timestamp 2016-11-04) accepts
            # aarch64-unknown-linux-gnu; the -ohos triplet is handled
            # unstably by the bundled libtool/ltmain.sh (E007/E072).
            tc.configure_args.extend([
                "--build=aarch64-unknown-linux-gnu",
                "--host=aarch64-unknown-linux-gnu",
            ])
        tc.generate()

    def build(self):
        apply_conandata_patches(self)
        autotools = Autotools(self)
        autotools.configure()
        autotools.make(args=["-j1"])

    def package(self):
        autotools = Autotools(self)
        autotools.install()
        # drop libtool .la wrappers; pkg-config goes away because conan
        # manages the dependency chain itself
        import glob as _glob
        for _la in _glob.glob(os.path.join(self.package_folder, "lib", "*.la")):
            os.remove(_la)
        rmdir(self, os.path.join(self.package_folder, "lib", "pkgconfig"))
        # util/Makefile.am also installs rootfs-only helpers: mount.fuse
        # (/sbin), the sysv init script (/etc/init.d) and a udev rule
        # (/etc/udev/rules.d). Those targets do not exist on OHOS (/etc is a
        # symlink to /system/etc) and their install hooks (chmod u+s, mknod)
        # are no-ops here, so they are stripped from the package. The real
        # CLIs are bin/fusermount and bin/ulockmgr_server. See notes.md.
        for _junk in ("sbin", "etc", "dev"):
            rmdir(self, os.path.join(self.package_folder, _junk))

    def package_info(self):
        self.cpp_info.libs = ["fuse", "ulockmgr"]
        self.cpp_info.system_libs = ["pthread"]
        self.cpp_info.includedirs = ["include", "include/fuse"]
        # R38: this package ships CLI tools under bin/ — declare the bindir
        # explicitly so PF8 does not read it as "pure library carrying
        # commands.json".
        self.cpp_info.bindirs = ["bin"]
        # fuse_common.h enforces _FILE_OFFSET_BITS=64 via #error
        self.cpp_info.defines = ["_FILE_OFFSET_BITS=64"]
