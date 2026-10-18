#!/usr/bin/env python3
"""Conan recipe — mrxvt 0.5.4 — Autotools build system.

mrxvt (micro RXVT) is a lightweight, tabbed X11 terminal emulator based on
rxvt.  It supports Xft fonts, XPM/JPEG/PNG background images, and session
management via SM/ICE.

Source: https://sourceforge.net/projects/materm/

OHOS portability notes:
  - XPM/JPEG/PNG background image support is disabled because libxpm/3.5.17
    requires libx11/6.4.0 (force=True), which conflicts with libxft's
    libx11/1.8.13 dependency.  Xft font rendering (the essential feature)
    is preserved via the 1.8.13 X11 track.
  - utmp/wtmp/lastlog/session-mgr are disabled (OHOS lacks these services).
  - AC_PATH_X cannot find X11 in Conan's non-standard layout; --x-includes
    and --x-libraries are passed explicitly.
"""
import os
import shutil

from conan import ConanFile
from conan.tools.env import VirtualBuildEnv
from conan.tools.files import get, apply_conandata_patches, export_conandata_patches, replace_in_file
from conan.tools.gnu import Autotools, AutotoolsToolchain, PkgConfigDeps
from conan.tools.layout import basic_layout


class MrxvtConan(ConanFile):
    name = "mrxvt"
    version = "0.5.4"
    package_type = "application"
    description = "Lightweight tabbed X11 terminal emulator based on rxvt"
    license = "GPL-2.0-or-later"
    homepage = "https://sourceforge.net/projects/materm/"
    url = ""

    settings = "os", "compiler", "build_type", "arch"

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        self.requires("libx11/1.8.13", transitive_headers=True)
        self.requires("libxft/2.3.8", transitive_headers=True)
        self.requires("libxrender/0.9.12", transitive_headers=True)
        self.requires("xorgproto/2025.1", transitive_headers=True)
        self.requires("fontconfig/2.18.3", transitive_headers=True)
        self.requires("freetype/2.14.3", transitive_headers=True)
        self.requires("libsm/1.2.4", transitive_headers=True)
        self.requires("libice/1.1.2", transitive_headers=True)

    def layout(self):
        basic_layout(self)

    def source(self):
        sources = self.conan_data["sources"]
        try:
            get(self, **{k: v for k, v in sources.items() if k != "backup_urls"},
                strip_root=True)
        except Exception:
            backup_urls = sources.get("backup_urls", [])
            if backup_urls:
                self.output.warning(f"Primary URL failed, trying backup: {backup_urls[0]}")
                get(self, url=backup_urls[0], strip_root=True)
            else:
                raise

    def generate(self):
        PkgConfigDeps(self).generate()
        VirtualBuildEnv(self).generate()

        tc = AutotoolsToolchain(self)
        tc.configure_args.extend([
            "--enable-xft",
            "--disable-xpm",
            "--disable-jpeg",
            "--disable-png",
            "--enable-256colors",
            "--disable-utmp",
            "--disable-wtmp",
            "--disable-lastlog",
            "--disable-sessionmgr",
            "--disable-debug",
        ])

        if str(self.settings.os) == "OHOS":
            shell = self._ohos_shell()
            environment = tc.environment()
            environment.define_path("SHELL", shell)
            environment.define_path("CONFIG_SHELL", shell)
            environment.define_path("CC", self._compiler_executable("c", "clang"))
            environment.define_path("CXX", self._compiler_executable("cpp", "clang++"))
            environment.define_path("LD", self._tool_executable("ld.lld", "lld", "ld"))
            environment.define_path("AR", self._tool_executable("llvm-ar", "ar"))
            environment.define_path("RANLIB", self._tool_executable("llvm-ranlib", "ranlib"))
            environment.define_path("STRIP", self._tool_executable("llvm-strip", "strip"))
            environment.define_path("NM", self._tool_executable("llvm-nm", "nm"))
            environment.append("CPPFLAGS", self._dep_cppflags())
            environment.append("LDFLAGS", self._dep_ldflags())
            # Cross-compilation cache: AC_CHECK_SIZEOF tries to run test
            # programs; provide aarch64 sizes so configure skips execution.
            tc.update_configure_args({
                "ac_cv_sizeof_char": "1",
                "ac_cv_sizeof_short": "2",
                "ac_cv_sizeof_int": "4",
                "ac_cv_sizeof_long": "8",
                "ac_cv_sizeof_long_long": "8",
                "ac_cv_sizeof_int_p": "8",
                "ac_cv_func_setpgrp_void": "yes",
                "ac_cv_func_working_fork": "yes",
                "ac_cv_func_working_vfork": "yes",
            })
            host_triplet = self._gnu_triplet()
            build_triplet = self._build_triplet()
            tc.update_configure_args({
                "--build": build_triplet,
                "--host": host_triplet,
            })

        libx11 = self.dependencies["libx11"]
        tc.configure_args.append(f"--x-includes={libx11.package_folder}/include")
        tc.configure_args.append(f"--x-libraries={libx11.package_folder}/lib")

        if str(self.settings.os) == "OHOS":
            tc.generate(env=environment)
        else:
            tc.generate()

    def build(self):
        apply_conandata_patches(self)
        if str(self.settings.os) == "OHOS":
            self._patch_configure()
        autotools = Autotools(self)
        autotools.configure()
        autotools.make()

    def package(self):
        autotools = Autotools(self)
        autotools.install()

    def package_info(self):
        self.cpp_info.bindirs = ["bin"]

    def _gnu_triplet(self):
        arch = str(self.settings.arch)
        machine = {"armv8": "aarch64", "x86_64": "x86_64"}.get(arch, arch)
        return f"{machine}-unknown-linux-gnu"

    def _build_triplet(self):
        return "x86_64-pc-linux-gnu"

    def _ohos_shell(self):
        for candidate in (
            os.environ.get("CONFIG_SHELL"),
            os.environ.get("SHELL"),
            shutil.which("sh"),
            "/system/bin/sh",
            "/bin/sh",
            "/usr/bin/sh",
        ):
            if candidate and os.path.isfile(candidate) and os.access(candidate, os.X_OK):
                return candidate
        return "/system/bin/sh"

    def _compiler_executable(self, key, fallback_name):
        executables = self.conf.get("tools.build:compiler_executables", default={}, check_type=dict) or {}
        configured = executables.get(key)
        if configured and os.path.isfile(configured):
            return configured
        found = shutil.which(fallback_name)
        return found or configured or fallback_name

    def _tool_executable(self, *names):
        for name in names:
            found = shutil.which(name)
            if found:
                return found
        return names[0]

    def _dep_dirs(self, subdir):
        result = []
        for dependency in self.dependencies.host.values():
            path = os.path.join(dependency.package_folder, subdir)
            if os.path.isdir(path) and path not in result:
                result.append(path)
        return result

    def _dep_cppflags(self):
        return [f"-I{path}" for path in self._dep_dirs("include")]

    def _dep_ldflags(self):
        flags = []
        for path in self._dep_dirs("lib"):
            flags.append(f"-L{path}")
            flags.append(f"-Wl,-rpath-link,{path}")
        return flags

    def _patch_configure(self):
        configure_path = os.path.join(self.source_folder, "configure")
        if not os.path.isfile(configure_path):
            return
        shell = self._ohos_shell()
        replace_in_file(self, configure_path, "umask 077", "umask 022", strict=False)
        for pattern in ("#! /bin/sh", "#!/bin/sh", "#! /bin/bash", "#!/bin/bash"):
            replace_in_file(self, configure_path, pattern, f"#!{shell}", strict=False)
