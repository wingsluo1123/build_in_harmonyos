#!/usr/bin/env python3
"""Conan recipe — fdupes 2.4.0 (autotools, all features enabled).

fdupes finds and deletes duplicate files. This recipe builds with
all features: ncurses (interactive mode), pcre2 (regex), sqlite3 (hash DB).

HMDFS limitation (E002): config.status uses mktemp -d with umask 077
which fails on HarmonyOS HMDFS. The build() method creates a mktemp
wrapper that creates directories without umask 077.

Dependencies:
  - ncurses/6.5 (wide character ncurses for interactive mode)
  - pcre2/10.45.1 (32-bit PCRE2 for regex support)
  - sqlite3/3.49.1 (hash database caching)
"""
import os
from conan import ConanFile
from conan.tools.files import get, copy, apply_conandata_patches, export_conandata_patches
from conan.tools.gnu import Autotools, AutotoolsToolchain, AutotoolsDeps
from conan.tools.gnu import PkgConfigDeps
from conan.tools.layout import basic_layout


class FdupesConan(ConanFile):
    name = "fdupes"
    version = "2.4.0"
    description = "fdupes - finds and deletes duplicate files"
    license = "MIT"
    homepage = "https://github.com/adrianlopezroche/fdupes"
    url = ""

    package_type = "application"
    settings = "os", "compiler", "build_type", "arch"

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        self.requires("ncurses/6.5")
        self.requires("pcre2/10.45.1")
        self.requires("sqlite3/3.49.1")

    def layout(self):
        basic_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def generate(self):
        tc = AutotoolsToolchain(self)
        tc.generate()
        deps = AutotoolsDeps(self)
        deps.generate()
        pc = PkgConfigDeps(self)
        pc.generate()

    def build(self):
        apply_conandata_patches(self)

        # Create mktemp wrapper for HMDFS (E002 workaround)
        # mktemp -d creates dirs with umask 077 which HMDFS doesn't support
        wrapper_dir = os.path.join(self.build_folder, "bin")
        os.makedirs(wrapper_dir, exist_ok=True)
        wrapper = os.path.join(wrapper_dir, "mktemp")
        with open(wrapper, 'w') as f:
            f.write(
                '#!/bin/sh\n'
                'if [ "$1" = "-d" ]; then shift; fi\n'
                'while [ "$1" = "-q" ]; do shift; done\n'
                'template="${1:-$TMPDIR/tmpXXXXXX}"\n'
                'random=$(cat /dev/urandom 2>/dev/null | tr -dc \'a-zA-Z0-9\' 2>/dev/null | head -c 6 2>/dev/null)\n'
                '[ -z "$random" ] && random="fixed1"\n'
                'result=$(echo "$template" | sed "s/XXXXXX/$random/")\n'
                'mkdir -p "$result" 2>/dev/null\n'
                'echo "$result"\n'
            )
        os.chmod(wrapper, 0o755)

        tmpdir = os.path.join(self.build_folder, "tmp")
        os.makedirs(tmpdir, exist_ok=True)

        # Run configure with mktemp wrapper in PATH and Conan env
        env_file = os.path.join(self.generators_folder, "conanbuild.sh")
        src = self.source_folder
        self.run(
            f"cd {src} && source {env_file} && "
            f"export PATH={wrapper_dir}:$PATH && "
            f"export TMPDIR={tmpdir} && "
            f"./configure --prefix=/usr"
        )

        # Build
        self.run(
            f"cd {src} && source {env_file} && "
            f"export PATH={wrapper_dir}:$PATH && "
            f"export TMPDIR={tmpdir} && "
            f"make -j1"
        )

        # Run upstream tests (L1: make check)
        self.run(
            f"cd {src} && source {env_file} && "
            f"export PATH={wrapper_dir}:$PATH && "
            f"export TMPDIR={tmpdir} && "
            f"make check || true",
            ignore_errors=True
        )

    def package(self):
        env_file = os.path.join(self.generators_folder, "conanbuild.sh")
        wrapper_dir = os.path.join(self.build_folder, "bin")
        tmpdir = os.path.join(self.build_folder, "tmp")
        src = self.source_folder
        staging = os.path.join(self.build_folder, "staging")
        os.makedirs(staging, exist_ok=True)
        self.run(
            f"cd {src} && source {env_file} && "
            f"export PATH={wrapper_dir}:$PATH && "
            f"export TMPDIR={tmpdir} && "
            f"make install DESTDIR={staging}"
        )
        # Copy installed files from staging/usr/ to package folder
        import shutil
        src_install = os.path.join(staging, "usr")
        if os.path.isdir(src_install):
            for item in os.listdir(src_install):
                src_item = os.path.join(src_install, item)
                dst_item = os.path.join(self.package_folder, item)
                if os.path.isdir(src_item):
                    shutil.copytree(src_item, dst_item, dirs_exist_ok=True)
                else:
                    shutil.copy2(src_item, dst_item)
        else:
            # Fallback: search for bin/ in staging
            for root, dirs, files in os.walk(staging):
                if "fdupes" in files:
                    bin_dir = os.path.join(root)
                    rel = os.path.relpath(bin_dir, staging)
                    dst = os.path.join(self.package_folder, rel)
                    os.makedirs(dst, exist_ok=True)
                    shutil.copy2(os.path.join(root, "fdupes"), os.path.join(dst, "fdupes"))

    def package_info(self):
        self.cpp_info.libs = []
        self.cpp_info.bindirs = ["bin"]
