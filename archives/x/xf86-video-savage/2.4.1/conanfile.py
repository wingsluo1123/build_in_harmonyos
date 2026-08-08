#!/usr/bin/env python3
"""Conan recipe for xf86-video-savage 2.4.1 — X.Org video driver for S3 Savage chips.

This driver is a loadable X.Org server module (.so). It links against
xorg-server and libpciaccess at runtime (loaded by the X server).
xorgproto and pixman are Conan-managed dependencies.
xorg-server and libpciaccess are system-installed (via cmd-pkgs).
"""
import os
import shutil

from conan import ConanFile
from conan.tools.files import get, apply_conandata_patches, export_conandata_patches
from conan.tools.gnu import Autotools, AutotoolsToolchain
from conan.tools.layout import basic_layout


class Xf86VideoSavageConan(ConanFile):
    name = "xf86-video-savage"
    version = "2.4.1"
    description = "X.Org video driver for S3 Savage graphics chips"
    license = "MIT"
    homepage = "https://gitlab.freedesktop.org/xorg/driver/xf86-video-savage"
    url = ""

    package_type = "library"

    settings = "os", "compiler", "build_type", "arch"
    options = {"shared": [True, False]}
    default_options = {"shared": True}

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        self.requires("xorgproto/2025.1")
        self.requires("pixman/0.46.4.2")

    def layout(self):
        basic_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def generate(self):
        tc = AutotoolsToolchain(self)
        # OHOS platform: disable XAA and DRI (not supported on OHOS)
        tc.configure_args.append("--disable-xaa")
        tc.configure_args.append("--disable-dri")
        # Set SED to GNU sed (required by libtool generation)
        sed_path = shutil.which("sed") or "/bin/sed"
        tc.configure_args.append("SED=" + sed_path)
        # Disable documentation tools
        tc.configure_args.append("HELP2MAN=/bin/true")
        tc.configure_args.append("MAKEINFO=/bin/true")
        tc.generate()

    def build_env(self):
        """Set PKG_CONFIG_PATH to find system-installed xorg-server and libpciaccess."""
        prefix = os.path.expanduser("~") + "/usr/local"
        pc_paths = [
            f"{prefix}/lib/pkgconfig",
            f"{prefix}/share/pkgconfig",
        ]
        existing = os.environ.get("PKG_CONFIG_PATH", "")
        all_paths = ":".join(pc_paths + ([existing] if existing else []))
        os.environ["PKG_CONFIG_PATH"] = all_paths
        os.environ["LD_LIBRARY_PATH"] = f"{prefix}/lib:" + os.environ.get("LD_LIBRARY_PATH", "")
        os.environ["PATH"] = f"{prefix}/bin:" + os.environ.get("PATH", "")

    def build(self):
        self.build_env()
        apply_conandata_patches(self)
        autotools = Autotools(self)
        autotools.configure()
        autotools.make(args=["-j1"])

    def package(self):
        autotools = Autotools(self)
        autotools.install()

    def package_info(self):
        # The driver module is savage_drv.so, installed to lib/xorg/modules/drivers/
        self.cpp_info.libs = ["savage_drv"]
        self.cpp_info.libdirs = ["lib/xorg/modules/drivers"]
