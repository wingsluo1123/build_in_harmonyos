#!/usr/bin/env python3
"""Conan recipe for jp2a 1.0.7 — JPEG to ASCII converter.

Build system: Autotools (needs autoreconf)
Dependencies: libjpeg, curl (system precompiled packages from cmd-pkgs)
"""
import os

from conan import ConanFile
from conan.tools.env import Environment, VirtualBuildEnv
from conan.tools.files import get, apply_conandata_patches, export_conandata_patches
from conan.tools.gnu import Autotools, AutotoolsToolchain
from conan.tools.layout import basic_layout


class Jp2AConan(ConanFile):
    name = "jp2a"
    version = "1.0.7"
    description = "Simple JPEG to ASCII converter"
    license = "GPL-2.0"
    homepage = "https://github.com/cslarsen/jp2a"
    url = "https://github.com/cslarsen/jp2a"

    settings = "os", "compiler", "build_type", "arch"

    options = {
        "with_curl": [True, False],
    }
    default_options = {
        "with_curl": True,
    }

    def export_sources(self):
        export_conandata_patches(self)

    def layout(self):
        basic_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def generate(self):
        tc = AutotoolsToolchain(self)
        # Point to system-installed dependencies (from cmd-pkgs)
        system_prefix = "/storage/Users/currentUser/usr/local"
        tc.extra_cflags.append(f"-I{system_prefix}/include")
        # Fix out-of-source build: source include/ dir must be reachable
        tc.extra_cflags.append(f"-I{self.source_folder}/include")
        tc.extra_ldflags.append(f"-L{system_prefix}/lib")

        if self.options.with_curl:
            tc.configure_args.append("--enable-curl")
        else:
            tc.configure_args.append("--disable-curl")

        tc.generate()

        # Set TMPDIR via Environment for config.status workaround
        env = Environment()
        env.define("TMPDIR", os.environ.get("TMPDIR", "/storage/Users/currentUser/tmp"))
        env.vars(self, scope="build").save_script("buildenv_tmpdir")

    def build(self):
        apply_conandata_patches(self)
        autotools = Autotools(self)

        # Run autoreconf to generate configure (in source folder)
        autotools.autoreconf()

        # E165: Fix shebangs for OHOS (/bin/sh -> /system/bin/sh)
        self.run("find . -type f -name '*.sh' -o -name 'configure' -o -name 'config.sub' -o -name 'config.guess' -o -name 'install-sh' -o -name 'missing' -o -name 'depcomp' -o -name 'compile' | xargs -r sed -i '1s|^#!/bin/sh|#!/system/bin/sh|; 1s|^#!/bin/bash|#!/data/service/hnp/bin/bash|'", cwd=self.source_folder)

        # OHOS HMDFS workaround: config.status uses mktemp -d with umask 077
        # which creates dirs without write permission on setgid HMDFS dirs.
        # Strategy: run configure --no-create, patch config.status, then run it.
        src_dir = self.source_folder
        build_dir = self.build_folder

        # Step 1: configure --no-create to only generate config.status
        configure_args = [
            "--prefix=/",
            "--enable-curl" if self.options.with_curl else "--disable-curl",
        ]
        args_str = " ".join(configure_args)
        self.run(f"/data/service/hnp/bin/bash {src_dir}/configure --no-create {args_str}", cwd=build_dir)

        # Step 2: Patch config.status to use TMPDIR for mktemp
        cs_path = os.path.join(build_dir, "config.status")
        if os.path.exists(cs_path):
            with open(cs_path, "r") as f:
                content = f.read()
            content = content.replace(
                'tmp=`(umask 077 && mktemp -d "./confXXXXXX") 2>/dev/null`',
                'tmp=`mktemp -d "$TMPDIR/confXXXXXX" 2>/dev/null`'
            )
            content = content.replace(
                '(umask 077 && mkdir "$tmp")',
                'mkdir "$tmp"'
            )
            with open(cs_path, "w") as f:
                f.write(content)

        # Step 3: Run patched config.status to generate Makefiles
        self.run("/data/service/hnp/bin/bash ./config.status", cwd=build_dir)

        # Step 4: Build
        self.run("make -j1", cwd=build_dir)

    def package(self):
        build_dir = self.build_folder
        # make install with DESTDIR into package_folder
        self.run(
            f"make install DESTDIR={self.package_folder}",
            cwd=build_dir,
            env="conanbuild",
        )

    def package_info(self):
        # jp2a is a CLI tool, not a library
        self.cpp_info.libs = []
        self.cpp_info.bindirs = ["bin"]
        self.cpp_info.libdirs = []
        self.cpp_info.includedirs = []

        # Declare system dependencies
        self.cpp_info.system_libs = ["jpeg"]
        if self.options.with_curl:
            self.cpp_info.system_libs.append("curl")

    def package_id(self):
        # Binary package depends on all settings
        pass
