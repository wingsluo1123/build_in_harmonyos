#!/usr/bin/env python3
"""Conan recipe for libgphoto2 2.5.31 — Autotools build for HarmonyOS PC (arm64).

libgphoto2 is a library for accessing digital cameras. This recipe cross-compiles
it for OpenHarmony with USB IOLib disabled (--without-libusb1) and NLS disabled
(--disable-nls).

The source is a git archive tag that does NOT include a configure script, so
autoreconf -fi is run in build(). Gettext m4 macros and config.rpath are included
as patches since autopoint is not available on the CI worker.
"""
import os
import shutil

from conan import ConanFile
from conan.tools.files import get, apply_conandata_patches, export_conandata_patches
from conan.tools.gnu import Autotools, AutotoolsToolchain
from conan.tools.layout import basic_layout


class Libgphoto2Conan(ConanFile):
    name = "libgphoto2"
    version = "2.5.31"
    description = "A library for accessing digital cameras (gPhoto2)"
    license = "LGPL-2.1-or-later"
    homepage = "https://github.com/gphoto/libgphoto2"
    url = "https://gitcode.com/OpenHarmonyPCDeveloper/build_in_harmonyos"

    package_type = "library"

    settings = "os", "compiler", "build_type", "arch"
    options = {"shared": [True, False]}
    default_options = {"shared": True}

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        self.requires("libtool/2.5.4")
        self.requires("libexif/0.6.26")
        self.requires("popt/1.16")
        self.requires("zlib/1.3.1")

    def layout(self):
        basic_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def generate(self):
        tc = AutotoolsToolchain(self)
        tc.configure_args.append("--disable-nls")
        tc.configure_args.append("--without-libusb1")
        # libltdl (from libtool dependency) - pass as make variables to configure
        libtool = self.dependencies["libtool"]
        cpp = libtool.cpp_info
        ltdl_inc = cpp.includedirs[0] if cpp.includedirs else ""
        ltdl_lib = cpp.libdirs[0] if cpp.libdirs else ""
        tc.configure_args.append(f"LTDLINCL=-I{ltdl_inc}")
        tc.configure_args.append(f"LIBLTDL=-L{ltdl_lib} -lltdl")
        # Set PKG_CONFIG_PATH so configure can find libexif, popt, etc.
        pkg_paths = []
        for dep in self.dependencies.values():
            for bd in dep.cpp_info.builddirs:
                pkg_paths.append(bd)
        if pkg_paths:
            tc.environment["PKG_CONFIG_PATH"] = ":".join(pkg_paths)
        tc.generate()

    def build(self):
        src = self.source_folder

        # Create directories needed by patches (source from git archive doesn't have them)
        os.makedirs(os.path.join(src, "auto-aux"), exist_ok=True)
        os.makedirs(os.path.join(src, "auto-m4"), exist_ok=True)
        os.makedirs(os.path.join(src, "po"), exist_ok=True)
        os.makedirs(os.path.join(src, "libgphoto2_port", "po"), exist_ok=True)

        apply_conandata_patches(self)

        # Set up libgphoto2_port subdirectory
        port_dir = os.path.join(src, "libgphoto2_port")
        port_m4 = os.path.join(port_dir, "auto-m4")
        port_aux = os.path.join(port_dir, "auto-aux")
        os.makedirs(port_m4, exist_ok=True)
        os.makedirs(port_aux, exist_ok=True)

        # Create ABOUT-NLS (normally done by autopoint, which is not available)
        open(os.path.join(src, "ABOUT-NLS"), "w").close()
        open(os.path.join(port_dir, "ABOUT-NLS"), "w").close()

        # Copy m4 files from top-level auto-m4 to subdirectory
        top_m4 = os.path.join(src, "auto-m4")
        if os.path.isdir(top_m4):
            for f in os.listdir(top_m4):
                src_f = os.path.join(top_m4, f)
                if os.path.isfile(src_f):
                    shutil.copy2(src_f, os.path.join(port_m4, f))

        # Copy config.rpath to subdirectory auto-aux
        rpath = os.path.join(src, "auto-aux", "config.rpath")
        if os.path.isfile(rpath):
            shutil.copy2(rpath, os.path.join(port_aux, "config.rpath"))

        # Save ohos-patched config.guess/config.sub before autoreconf overwrites them
        saved_guess = None
        saved_sub = None
        guess_path = os.path.join(src, "auto-aux", "config.guess")
        sub_path = os.path.join(src, "auto-aux", "config.sub")
        if os.path.isfile(guess_path):
            with open(guess_path) as f:
                saved_guess = f.read()
        if os.path.isfile(sub_path):
            with open(sub_path) as f:
                saved_sub = f.read()

        # Run autoreconf on top-level
        self.run("autoreconf -fi --no-recursive -I auto-m4 -I libgphoto2_port/gphoto-m4",
                 cwd=src)

        # Run autoreconf on subdirectory
        self.run("autoreconf -fi --no-recursive -I auto-m4 -I gphoto-m4",
                 cwd=port_dir)

        # Restore ohos-patched config.guess/config.sub
        if saved_guess:
            for d in [os.path.join(src, "auto-aux"), port_aux]:
                with open(os.path.join(d, "config.guess"), "w") as f:
                    f.write(saved_guess)
                os.chmod(os.path.join(d, "config.guess"), 0o755)
        if saved_sub:
            for d in [os.path.join(src, "auto-aux"), port_aux]:
                with open(os.path.join(d, "config.sub"), "w") as f:
                    f.write(saved_sub)
                os.chmod(os.path.join(d, "config.sub"), 0o755)

        # Fix configure umask 077→022 and temp dir (same as libexif)
        for cfg in [os.path.join(src, "configure"), os.path.join(port_dir, "configure")]:
            if os.path.isfile(cfg):
                with open(cfg, "r") as f:
                    content = f.read()
                content = content.replace("umask 077", "umask 022")
                content = content.replace('"./confXXXXXX"', '"${HOME}/tmp/confXXXXXX"')
                with open(cfg, "w") as f:
                    f.write(content)

        autotools = Autotools(self)
        autotools.configure()
        autotools.make(args=["-j1"])

    def package(self):
        autotools = Autotools(self)
        autotools.install()

    def package_info(self):
        self.cpp_info.libs = ["gphoto2", "gphoto2_port"]
