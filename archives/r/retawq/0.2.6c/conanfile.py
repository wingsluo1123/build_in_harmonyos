#!/usr/bin/env python3
"""Conan recipe for retawq 0.2.6c — a text-based web browser.

retawq uses a custom itchconfig build system (not standard autotools).
The configure script accepts --path-prefix=, --set-tg=, --set-tls=, etc.
"""
import os
import subprocess

from conan import ConanFile
from conan.tools.files import get, apply_conandata_patches, export_conandata_patches
from conan.tools.gnu import PkgConfigDeps
from conan.tools.layout import basic_layout


class RetawqConan(ConanFile):
    name = "retawq"
    version = "0.2.6c"
    description = "retawq is a text-based web browser"
    license = "GPL-2.0-only"
    homepage = "https://retawq.sourceforge.net/"

    package_type = "application"

    settings = "os", "compiler", "build_type", "arch"

    # R26: System-named libraries must be static to avoid polluting /lib
    default_options = {
        "ncurses/*:shared": False,
        "openssl/*:shared": False,
    }

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        self.requires("ncurses/6.6")
        self.requires("openssl/1.1.1w")

    def layout(self):
        basic_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def generate(self):
        pc = PkgConfigDeps(self)
        pc.generate()

    def _build_env(self):
        """Build environment dict with dependency paths."""
        cflags = ["-fPIC", "-O2"]
        ldflags = []
        for dep_name, dep in self.dependencies.items():
            cpp = dep.cpp_info
            for d in cpp.includedirs:
                cflags.append(f"-I{d}")
            for d in cpp.libdirs:
                ldflags.append(f"-L{d}")

        env = dict(os.environ)
        # Get compiler from Conan profile conf, fallback to settings
        compilers = self.conf.get("tools.build:compiler_executables", default={})
        env["CC"] = compilers.get("c", str(self.settings.compiler))
        env["CFLAGS"] = " ".join(cflags)
        env["LDFLAGS"] = " ".join(ldflags)
        env["PKG_CONFIG_PATH"] = self.generators_folder
        env["TMPDIR"] = os.path.join(self.generators_folder, "tmp")
        os.makedirs(env["TMPDIR"], exist_ok=True)
        return env

    def build(self):
        apply_conandata_patches(self)

        env = self._build_env()
        src = self.source_folder

        configure_args = [
            "./configure",
            f"--path-prefix={self.package_folder}",
            "--set-tg=curses:ncurses.h:ncursesw",
            "--set-tls=2",
            "--enable-news",
            "--enable-cookies",
            "--enable-textmodemouse",
            "--enable-ipv6",
            "--enable-local-cgi",
            "--set-threading=1",
        ]
        subprocess.check_call(configure_args, env=env, cwd=src)
        subprocess.check_call(["make", "-j1"], env=env, cwd=src)

    def package(self):
        env = self._build_env()
        subprocess.check_call(["make", "install"], env=env, cwd=self.source_folder)

    def package_info(self):
        # retawq is a command-line application, not a library
        self.cpp_info.bindirs = ["bin"]
