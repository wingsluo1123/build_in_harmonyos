#!/usr/bin/env python3
"""Conan recipe — gmime 3.2.7

GMime is a C/C++ library for parsing and creating MIME messages.
Autotools project, depends on glib.
License: LGPL-2.1
Homepage: https://github.com/jstedfast/gmime
"""
import os
import re
import shutil
import stat
from pathlib import Path

from conan import ConanFile
from conan.tools.files import get, apply_conandata_patches, export_conandata_patches
from conan.tools.gnu import Autotools, AutotoolsToolchain
from conan.tools.layout import basic_layout
from conan.tools.env import Environment


class GmimeConan(ConanFile):
    name = "gmime"
    version = "3.2.7"
    description = "GMime is a C/C++ library for parsing and creating MIME messages"
    license = "LGPL-2.1"
    homepage = "https://github.com/jstedfast/gmime"
    url = ""  # CI fills this

    package_type = "library"

    settings = "os", "compiler", "build_type", "arch"
    options = {"shared": [True, False]}
    default_options = {"shared": True}

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        self.requires("glib/2.84.0")

    def layout(self):
        basic_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def generate(self):
        tc = AutotoolsToolchain(self)
        tc.configure_args.append("--build=aarch64-unknown-linux-gnu")
        tc.configure_args.append("--disable-gtk-doc")
        tc.configure_args.append("--disable-introspection")
        tc.generate()

        # Fix dependency .pc files: conan packages often have prefix=/ which
        # produces broken include/lib paths. Rewrite prefix to actual package root.
        env = Environment()
        fixed_pc_dir = os.path.join(self.build_folder, "fixed_pkgconfig")
        os.makedirs(fixed_pc_dir, exist_ok=True)

        pkg_config_paths = []
        for dep_name, dep in self.dependencies.items():
            cpp_info = dep.cpp_info
            dep_root = cpp_info.rootpath if hasattr(cpp_info, "rootpath") else None
            # Find the package root from libdirs
            if not dep_root:
                for libdir in cpp_info.libdirs:
                    if os.path.isdir(libdir):
                        dep_root = os.path.dirname(libdir)
                        break
            if not dep_root:
                for incdir in cpp_info.includedirs:
                    if os.path.isdir(incdir):
                        dep_root = os.path.dirname(incdir)
                        break

            # Find and fix .pc files
            for libdir in cpp_info.libdirs:
                pc_dir = os.path.join(libdir, "pkgconfig")
                if os.path.isdir(pc_dir):
                    for pc_file in os.listdir(pc_dir):
                        if pc_file.endswith(".pc"):
                            src = os.path.join(pc_dir, pc_file)
                            dst = os.path.join(fixed_pc_dir, pc_file)
                            with open(src, "r") as f:
                                content = f.read()
                            if dep_root:
                                content = re.sub(
                                    r"^prefix=/\s*$",
                                    f"prefix={dep_root}",
                                    content,
                                    flags=re.MULTILINE,
                                )
                                content = re.sub(
                                    r"^prefix=\s*$",
                                    f"prefix={dep_root}",
                                    content,
                                    flags=re.MULTILINE,
                                )
                            with open(dst, "w") as f:
                                f.write(content)
            pkg_config_paths.append(fixed_pc_dir)

        if pkg_config_paths:
            existing = os.environ.get("PKG_CONFIG_PATH", "")
            all_paths = pkg_config_paths + ([existing] if existing else [])
            env.define_path("PKG_CONFIG_PATH", os.pathsep.join(all_paths))
        env.define("PKG_CONFIG", os.environ.get("PKG_CONFIG", "pkg-config"))
        # OHOS: musl dynamic linker is in /lib, add to linker search path
        env.append("LDFLAGS", "-L/lib")
        # OHOS: mktemp -d creates dirs with broken group perms (hmmac MAC),
        # causing config.status to fail writing subs*.awk. Create a mktemp
        # wrapper that returns failure to force autoconf AS_TMPDIR to use
        # mkdir fallback.
        wrapper_dir = Path(self.build_folder) / ".hmos_fix"
        wrapper_dir.mkdir(exist_ok=True)
        wrapper = wrapper_dir / "mktemp"
        wrapper.write_text(
            '#!/bin/sh\n'
            '# HarmonyOS: mktemp -d creates dirs with broken perms (hmmac MAC).\n'
            '# Return failure to force autoconf AS_TMPDIR to use mkdir fallback.\n'
            'exit 1\n'
        )
        wrapper.chmod(wrapper.stat().st_mode | stat.S_IEXEC)
        env.prepend_path("PATH", str(wrapper_dir))
        env.vars(self).save_script("gmime_env")

    def build(self):
        apply_conandata_patches(self)
        autotools = Autotools(self)
        autotools.configure()
        autotools.make(args=["-j1"])

    def package(self):
        autotools = Autotools(self)
        autotools.install()

    def package_info(self):
        self.cpp_info.includedirs = ["include/gmime-3.0"]
        self.cpp_info.libs = ["gmime-3.0"]
        self.cpp_info.set_property("pkg_config_name", "gmime-3.0")
