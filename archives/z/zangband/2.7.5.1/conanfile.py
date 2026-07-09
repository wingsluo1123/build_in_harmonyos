#!/usr/bin/env python3
"""Conan recipe — Zangband 2.7.5.1 (Autotools)."""
import os
import tarfile
import shutil

from conan import ConanFile
from conan.tools.files import get, copy, apply_conandata_patches, export_conandata_patches
from conan.tools.gnu import Autotools, AutotoolsToolchain
from conan.tools.layout import basic_layout


class ZangbandConan(ConanFile):
    name = "zangband"
    version = "2.7.5.1"
    description = "Roguelike computer role playing game based on Angband"
    license = "MIT"
    homepage = "https://sourceforge.net/projects/zangband/"
    url = ""

    settings = "os", "compiler", "build_type", "arch"
    exports = "zangband-2.7.5.1.tar.gz"

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        pass

    def layout(self):
        basic_layout(self, src_folder=".")

    def source(self):
        local_tarball = os.path.join(self.recipe_folder, "zangband-2.7.5.1.tar.gz")
        if os.path.exists(local_tarball):
            with tarfile.open(local_tarball, "r:gz") as t:
                members = t.getnames()
                top_dir = members[0].split("/")[0] if members else None
                t.extractall(self.source_folder)
                if top_dir:
                    extracted = os.path.join(self.source_folder, top_dir)
                    if os.path.isdir(extracted):
                        for item in os.listdir(extracted):
                            src = os.path.join(extracted, item)
                            dst = os.path.join(self.source_folder, item)
                            shutil.move(src, dst)
                        os.rmdir(extracted)
        else:
            get(self, **self.conan_data["sources"], strip_root=True)

    def generate(self):
        tc = AutotoolsToolchain(self)
        tc.extra_cflags.append("-fPIC -O2")
        tc.generate()

    def build(self):
        apply_conandata_patches(self)
        autotools = Autotools(self)
        autotools.configure()

        # Create stub files
        for path in [".version", "src/defines.h"]:
            full_path = os.path.join(self.source_folder, path)
            os.makedirs(os.path.dirname(full_path), exist_ok=True)
            if not os.path.exists(full_path):
                with open(full_path, "w") as f:
                    f.write("2.7.5pre1\n" if path == ".version" else "/* stub */\n")

        # Verify autoconf.h was created; fallback to autoconf.h.in
        autoconf_h = os.path.join(self.source_folder, "src", "autoconf.h")
        if not os.path.exists(autoconf_h) or os.path.getsize(autoconf_h) == 0:
            autoconf_h_in = os.path.join(self.source_folder, "src", "autoconf.h.in")
            if os.path.exists(autoconf_h_in):
                shutil.copy(autoconf_h_in, autoconf_h)

        # Touch generated files
        for f in ["makefile", "config.status", "src/autoconf.h", ".version"]:
            fpath = os.path.join(self.source_folder, f)
            if os.path.exists(fpath):
                os.utime(fpath, None)

        # Use absolute path for -I flag and override CFLAGS/LIBS
        src_dir = os.path.join(self.source_folder, "src")
        prefix = os.path.expanduser("~/usr/local")
        gen = self.generators_folder
        cflags = f"-fPIC -O2 -I{prefix}/include -DHAVE_CONFIG_H"
        libs = "-lz -lncurses -lX11"
        ldflags = f"-L{prefix}/lib"
        make_args = f'CC=clang CC_AUX=clang TK_PORT= CFLAGS="{cflags}" CPPFLAGS="-I{src_dir}" LDFLAGS="{ldflags}" LIBS="{libs}" -j1 -o .version -o configure -o makefile -o config.status -o src/autoconf.h'
        env_script = os.path.join(gen, "conanbuild.sh")
        if os.path.exists(env_script):
            cmd = f"source {env_script} && make {make_args}"
        else:
            cmd = f"make {make_args}"
        self.run(cmd, cwd=self.source_folder)

    def package(self):
        src_dir = os.path.join(self.source_folder, "src")
        gen = self.generators_folder
        env_script = os.path.join(gen, "conanbuild.sh")
        # Create package directory structure
        pkg_data = os.path.join(self.package_folder, "share", "games", "zangband", "lib")
        os.makedirs(pkg_data, exist_ok=True)
        os.makedirs(os.path.join(self.package_folder, "bin"), exist_ok=True)
        pkg_prefix = self.package_folder
        if os.path.exists(env_script):
            cmd = f"source {env_script} && make CC=clang CC_AUX=clang TK_PORT= prefix={pkg_prefix} -o .version -o configure -o makefile -o config.status -o src/autoconf.h install"
        else:
            cmd = f"make CC=clang CC_AUX=clang TK_PORT= prefix={pkg_prefix} install"
        self.run(cmd, cwd=self.source_folder)

    def package_info(self):
        self.cpp_info.libs = []
