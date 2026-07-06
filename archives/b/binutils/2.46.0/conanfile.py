#!/usr/bin/env python3
"""Conan recipe for binutils 2.46.0 — Autotools project."""
import os

from conan import ConanFile
from conan.tools.files import get, copy, apply_conandata_patches, export_conandata_patches
from conan.tools.gnu import Autotools, AutotoolsToolchain
from conan.tools.layout import basic_layout
from conan.tools.env import Environment


class BinutilsConan(ConanFile):
    name = "binutils"
    version = "2.46.0"
    description = "binutils 2.46.0"
    license = "MIT"
    homepage = ""
    url = ""

    settings = "os", "compiler", "build_type", "arch"

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        pass

    def layout(self):
        basic_layout(self)
        self.folders.build = "."

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def generate(self):
        tc = AutotoolsToolchain(self)
        tc.extra_ldflags.append("-static")
        tc.extra_cflags.append("-Wno-error=unused-function")
        tc.configure_args.append("--disable-gprofng")
        tc.configure_args.append("--disable-gprof")
        tc.configure_args.append("--disable-gdb")
        tc.configure_args.append("--disable-gdbserver")
        tc.configure_args.append("--disable-werror")
        tc.configure_args.append("--disable-sim")
        tc.configure_args.append("--enable-targets=aarch64-linux-ohos")
        tc.generate()
        # E001: Set CC/CXX for autotools on OHOS
        env = Environment()
        env.define("CC", "clang")
        env.define("CXX", "clang++")
        env.vars(self, scope="build").save_script("conanbuild_env")

    def build(self):
        apply_conandata_patches(self)
        skill_root = os.environ.get("SKILL_ROOT", "/storage/Users/currentUser/.opendesk/apps/skills/resources/build_in_harmonyos")
        # E007: Fix config.guess/config.sub for OHOS
        for subdir in ["", "config", "build-aux"]:
            cg = os.path.join(self.source_folder, subdir, "config.guess") if subdir else os.path.join(self.source_folder, "config.guess")
            cs = os.path.join(self.source_folder, subdir, "config.sub") if subdir else os.path.join(self.source_folder, "config.sub")
            if os.path.exists(cg) and os.path.exists(cs):
                self.run(f'perl {skill_root}/scripts/patch-autotools-ohos.pl {cg} {cs}', cwd=self.source_folder)
        # Fix config.status permission issue
        configure_path = os.path.join(self.source_folder, "configure")
        if os.path.exists(configure_path):
            self.run(f"sed -i 's/umask 077/umask 022/g' {configure_path}", cwd=self.source_folder)
        autotools = Autotools(self)
        autotools.configure()
        autotools.make(args=["-j1"])

    def package(self):
        autotools = Autotools(self)
        autotools.install()

    def package_info(self):
        self.cpp_info.libs = ["bfd", "opcodes", "iberty", "ctf", "sframe"]
        self.cpp_info.bindirs = ["bin"]
