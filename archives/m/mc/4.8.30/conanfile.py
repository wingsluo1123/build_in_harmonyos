#!/usr/bin/env python3
"""Conan recipe for Midnight Commander (mc) 4.8.30.

Midnight Commander is a visual file manager for Unix-like systems.
Built with S-Lang terminal library and GLib on HarmonyOS.
"""
import os
import shutil

from conan import ConanFile
from conan.tools.files import get, apply_conandata_patches, export_conandata_patches
from conan.tools.gnu import Autotools, AutotoolsToolchain, PkgConfigDeps
from conan.tools.layout import basic_layout


class McConan(ConanFile):
    name = "mc"
    version = "4.8.30"
    description = "Midnight Commander - visual file manager, Norton Commander style"
    license = "GPL-3.0"
    homepage = "https://www.midnight-commander.org"
    url = ""  # CI fills this

    package_type = "application"

    settings = "os", "compiler", "build_type", "arch"

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        self.requires("glib2/2.88.0")
        self.requires("slang/2.3.3")

    def build_requirements(self):
        # Build tools are installed system-wide via Harmonybrew
        pass

    def layout(self):
        basic_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def generate(self):
        tc = AutotoolsToolchain(self)
        # Platform-specific configure args
        tc.configure_args.append("--with-slang")
        tc.configure_args.append("--without-x")
        tc.generate()
        # Generate pkg-config files for dependencies
        pc = PkgConfigDeps(self)
        pc.generate()

    def build(self):
        apply_conandata_patches(self)

        # Ensure build tools are in PATH (Harmonybrew install)
        hb_bin = os.path.expanduser("~/.harmonybrew/bin")
        if os.path.isdir(hb_bin):
            env_path = os.environ.get("PATH", "")
            os.environ["PATH"] = hb_bin + ":" + env_path

        # Ensure CC/CXX are set (HarmonyOS doesn't have cc/c++ symlinks by default)
        os.environ.setdefault("CC", "clang")
        os.environ.setdefault("CXX", "clang++")

        # Add m4_pattern_allow to configure.ac (workaround for autoconf 2.73+
        # treating dnl/AC_MSG_WARN/AC_MSG_ERROR as undefined macros)
        configure_ac = os.path.join(self.source_folder, "configure.ac")
        with open(configure_ac, "r") as f:
            content = f.read()
        allow = (
            "m4_pattern_allow([dnl])\n"
            "m4_pattern_allow([AC_MSG_WARN])\n"
            "m4_pattern_allow([AC_MSG_ERROR])\n"
        )
        if "m4_pattern_allow([dnl])" not in content:
            content = allow + content
            with open(configure_ac, "w") as f:
                f.write(content)

        # Run autoreconf to generate configure script
        # (GitHub archive doesn't include pre-generated configure)
        # Include pkg.m4 and libtool m4 paths for aclocal
        aclocal_paths = [
            "m4",
            "m4.include",
            os.path.expanduser("~/.harmonybrew/share/aclocal"),
            "/data/service/hnp/pkg-config.org/pkg-config_0.29.2/share/aclocal",
        ]
        aclocal_args = " ".join(f"-I {p}" for p in aclocal_paths if os.path.isdir(p))
        self.run(f"autoreconf --install --force {aclocal_args}",
                 env="conanbuild", cwd=self.source_folder)

        # Patch config.guess for HarmonyOS
        self._patch_config_guess()

        # Patch configure: replace umask 077 with umask 022
        # (HarmonyOS file system doesn't support 700-permission temp dirs)
        configure_path = os.path.join(self.source_folder, "configure")
        with open(configure_path, "r") as f:
            content = f.read()
        content = content.replace("umask 077", "umask 022")
        with open(configure_path, "w") as f:
            f.write(content)

        # Create po/Makefile from po/Makefile.in (gettext version mismatch workaround)
        po_makefile_in = os.path.join(self.source_folder, "po", "Makefile.in")
        po_makefile = os.path.join(self.source_folder, "po", "Makefile")
        if os.path.exists(po_makefile_in) and not os.path.exists(po_makefile):
            with open(po_makefile_in, "r") as f:
                content = f.read()
            if "top_builddir" not in content:
                content = content.replace(
                    "top_srcdir = ..", "top_srcdir = ..\ntop_builddir = .."
                )
            content = content.replace("@POMAKEFILEDEPS@", "")
            content = content.replace("$(top_builddir)/config.status", "../config.status")
            with open(po_makefile, "w") as f:
                f.write(content)

        autotools = Autotools(self)
        autotools.configure()

        # Fix po/Makefile in the BUILD directory after configure
        build_po_makefile = os.path.join(self.build_folder, "po", "Makefile")
        if os.path.exists(build_po_makefile):
            with open(build_po_makefile, "r") as f:
                content = f.read()
            if "top_builddir" not in content:
                content = content.replace(
                    "top_srcdir = ..", "top_srcdir = ..\ntop_builddir = .."
                )
            content = content.replace("@POMAKEFILEDEPS@", "")
            content = content.replace("$(top_builddir)/config.status", "../config.status")
            with open(build_po_makefile, "w") as f:
                f.write(content)
        else:
            # Create a minimal po/Makefile with 'all' target
            build_po_dir = os.path.join(self.build_folder, "po")
            if not os.path.isdir(build_po_dir):
                os.makedirs(build_po_dir, exist_ok=True)
            with open(build_po_makefile, "w") as f:
                f.write("all:\n\t@echo 'Skipping po (NLS not configured)'\n"
                        "install:\n\t@echo 'Skipping po install'\n"
                        "clean:\n\tdistclean:\n\tcheck:\n")

        autotools.make(args=["-j1"])

    def _patch_config_guess(self):
        """Patch config.guess and config.sub for HarmonyOS support."""
        config_dir = os.path.join(self.source_folder, "config")

        # Patch config.guess
        guess_path = os.path.join(config_dir, "config.guess")
        if os.path.exists(guess_path):
            with open(guess_path, "r") as f:
                content = f.read()
            content = content.replace(
                "Linux|GNU|GNU/*)", "Linux|GNU|GNU/*|HarmonyOS)"
            )
            content = content.replace(
                "    aarch64:Linux:*:*)",
                '    aarch64:HarmonyOS:*:*)\n\tGUESS="$UNAME_MACHINE-unknown-linux-gnu"\n\t;;\n    aarch64:Linux:*:*)',
            )
            with open(guess_path, "w") as f:
                f.write(content)

        # Patch config.sub
        sub_path = os.path.join(config_dir, "config.sub")
        if os.path.exists(sub_path):
            with open(sub_path, "r") as f:
                content = f.read()
            content = content.replace(
                "\t\t\t| linux-* \\",
                "\t\t\t| ohos-* \\\n\t\t\t| linux-* \\",
            )
            with open(sub_path, "w") as f:
                f.write(content)

    def package(self):
        autotools = Autotools(self)
        autotools.install()

    def package_info(self):
        self.cpp_info.libs = []
        # mc is an application, not a library
        self.cpp_info.bindirs = ["bin"]
