#!/usr/bin/env python3
"""Conan recipe for ncurses 6.5.

This package is intentionally static-only on OHOS. Installing ncurses shared
libraries can shadow the system ncurses runtime used by the shell.
"""

import os
import shlex
import shutil

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.files import (
    apply_conandata_patches,
    copy,
    export_conandata_patches,
    get,
)
from conan.tools.gnu import AutotoolsToolchain
from conan.tools.layout import basic_layout


class NcursesConan(ConanFile):
    name = "ncurses"
    version = "6.5"
    description = "Terminal handling library and terminfo tools"
    license = "X11"
    homepage = "https://invisible-island.net/ncurses/"
    url = ""
    package_type = "static-library"

    settings = "os", "arch", "compiler", "build_type"

    def export_sources(self):
        export_conandata_patches(self)

    def validate(self):
        if self.settings.os not in ("Linux", "OHOS"):
            raise ConanInvalidConfiguration("ncurses recipe supports Linux and OHOS")

    def layout(self):
        basic_layout(self, src_folder=".")
        self.folders.build = "."

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def _home_prefix_bin(self):
        home = os.environ.get("HOME")
        if not home:
            return None
        return os.path.join(home, "usr", "local", "bin")

    def _path(self):
        parts = []
        home_bin = self._home_prefix_bin()
        if home_bin and os.path.isdir(home_bin):
            parts.append(home_bin)
        current = os.environ.get("PATH")
        if current:
            parts.append(current)
        return os.pathsep.join(parts)

    def _shell(self):
        home_bin = self._home_prefix_bin()
        candidates = []
        if home_bin:
            candidates.append(os.path.join(home_bin, "bash"))
        candidates.extend(
            [
                os.environ.get("CONFIG_SHELL"),
                os.environ.get("SHELL"),
                shutil.which("bash"),
                "/bin/sh",
                "/data/service/hnp/bin/bash",
            ]
        )
        for candidate in candidates:
            if self._is_usable_executable(candidate):
                return candidate
        return shutil.which("sh") or "/bin/sh"

    def _tmpdir(self):
        tmpdir = os.environ.get("TMPDIR")
        if not tmpdir:
            tmpdir = os.path.join(os.path.expanduser("~"), "tmp", "ncurses-conan")
        os.makedirs(tmpdir, exist_ok=True)
        return tmpdir

    def _tool(self, key, fallback):
        executables = self.conf.get(
            "tools.build:compiler_executables", default={}, check_type=dict
        )
        candidate = executables.get(key)
        if self._is_usable_executable(candidate):
            return candidate
        home_bin = self._home_prefix_bin()
        if home_bin:
            candidate = os.path.join(home_bin, fallback)
            if self._is_usable_executable(candidate):
                return candidate
        candidate = shutil.which(fallback)
        if self._is_usable_executable(candidate):
            return candidate
        return fallback

    def _compiler(self, key, fallback):
        executables = self.conf.get(
            "tools.build:compiler_executables", default={}, check_type=dict
        )
        candidate = executables.get(key)
        if self._is_usable_executable(candidate):
            return candidate
        ohos_candidate = self._ohos_toolchain_compiler(key)
        if self._is_usable_executable(ohos_candidate):
            return ohos_candidate
        return self._tool(key, fallback)

    def _ohos_toolchain_compiler(self, key):
        home = os.environ.get("HOME")
        if self.settings.os != "OHOS" or not home:
            return None
        name = "ohos-clang" if key == "c" else "ohos-clangxx"
        return os.path.join(home, "validation", "toolchain-bin", name)

    def _is_usable_executable(self, path):
        if not path:
            return False
        return not os.path.isabs(path) or os.access(path, os.X_OK)

    def _env_prefix(self):
        env = {
            "CC": self._compiler("c", "clang"),
            "CXX": self._compiler("cpp", "clang++"),
            "AR": self._tool("ar", "llvm-ar"),
            "RANLIB": self._tool("ranlib", "llvm-ranlib"),
            "TMPDIR": self._tmpdir(),
            "CONFIG_SHELL": self._shell(),
            "SHELL": self._shell(),
            "PATH": self._path(),
        }
        return " ".join(f"{key}={shlex.quote(str(value))}" for key, value in env.items())

    def _configure_args(self):
        args = [
            "--prefix=/",
            "--without-shared",
            "--without-debug",
            "--without-profile",
            "--without-ada",
            "--without-cxx",
            "--without-cxx-binding",
            "--without-manpages",
            "--disable-stripping",
            "--enable-widec",
            "--enable-overwrite",
            "--enable-pc-files",
            "--with-pkg-config-libdir=/lib/pkgconfig",
        ]
        if self.settings.os == "OHOS":
            args.append("--build=aarch64-unknown-linux-gnu")
        return args

    def generate(self):
        AutotoolsToolchain(self).generate()

    def build(self):
        if self.settings.os == "OHOS":
            apply_conandata_patches(self)
        env = self._env_prefix()
        shell = shlex.quote(self._shell())
        args = " ".join(shlex.quote(arg) for arg in self._configure_args())
        self.run(f"{env} {shell} ./configure {args}", cwd=self.source_folder, env="conanbuild")
        self.run(f"{env} make -j1", cwd=self.source_folder, env="conanbuild")
        self.run(f"{env} make -C test -j1", cwd=self.source_folder, env="conanbuild")
        self.run(f"{env} make -C test check", cwd=self.source_folder, env="conanbuild")

    def package(self):
        env = self._env_prefix()
        self.run(
            f'{env} make install DESTDIR="{self.package_folder}"',
            cwd=self.source_folder,
            env="conanbuild",
        )
        copy(
            self,
            "COPYING",
            src=self.source_folder,
            dst=os.path.join(self.package_folder, "licenses"),
        )

    def package_info(self):
        bin_dir = os.path.join(self.package_folder, "bin")
        terminfo_dir = os.path.join(self.package_folder, "share", "terminfo")
        self.cpp_info.libs = ["formw", "menuw", "panelw", "ncursesw"]
        self.cpp_info.set_property("pkg_config_name", "ncursesw")
        self.cpp_info.set_property("cmake_file_name", "Curses")
        self.cpp_info.set_property("cmake_target_name", "Curses::Curses")
        self.runenv_info.prepend_path("PATH", bin_dir)
        self.runenv_info.define_path("TERMINFO", terminfo_dir)
        self.runenv_info.define("TERMINFO_DIRS", terminfo_dir)
        self.buildenv_info.prepend_path("PATH", bin_dir)
        self.buildenv_info.define_path("TERMINFO", terminfo_dir)
        self.buildenv_info.define("TERMINFO_DIRS", terminfo_dir)
