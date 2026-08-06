#!/usr/bin/env python3
"""Conan recipe for htop 3.4.1 — Interactive process viewer.

htop is a command-line application (not a library).
Build system: Autotools (configure + make).

ncurses is installed from cmd-pkgs pre-compiled package (not conancenter)
because conancenter's ncurses recipe cannot build on HarmonyOS.
"""
import os
import shutil
import subprocess

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.files import get, apply_conandata_patches, export_conandata_patches
from conan.tools.gnu import Autotools, AutotoolsToolchain
from conan.tools.layout import basic_layout
from conan.tools.env import Environment


class HtopConan(ConanFile):
    name = "htop"
    version = "3.4.1"
    description = "Interactive process viewer for Unix systems"
    license = "GPL-2.0"
    homepage = "https://htop.dev/"
    url = ""  # CI fills this

    package_type = "application"
    settings = "os", "compiler", "build_type", "arch"

    def export_sources(self):
        export_conandata_patches(self)

    def configure(self):
        if self.settings.os not in ("Linux", "OHOS"):
            raise ConanInvalidConfiguration(f"htop only supports Linux/OHOS, got {self.settings.os}")

    def layout(self):
        basic_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def _ensure_ncurses(self):
        """Install ncurses from cmd-pkgs if not already available."""
        home = os.path.expanduser("~")
        ncurses_h = os.path.join(home, "usr/local/include/curses.h")
        if os.path.exists(ncurses_h):
            return  # Already installed

        # Download ncurses pre-compiled package directly (skip install.sh to avoid security popup hang)
        tmpdir = os.path.join(home, "tmp/ncurses-install")
        os.makedirs(tmpdir, exist_ok=True)
        tarball = os.path.join(tmpdir, "ncurses.tar.gz")
        url = "https://gitcode.com/OpenHarmonyPCDeveloper/cmd-pkgs/releases/download/pkgs/ncurses-6.4-ohos-aarch64.tar.gz"

        # Download
        self.run(f'curl -fSL -o "{tarball}" "{url}"', env="conanbuild")

        # Extract
        self.run(f'tar xzf "{tarball}" -C "{tmpdir}"', env="conanbuild")

        # Copy files to $HOME/usr/local (manual, no security popup)
        for subdir in ["lib", "share", "bin"]:
            src = os.path.join(tmpdir, subdir)
            dst = os.path.join(home, "usr/local", subdir)
            if os.path.isdir(src):
                os.makedirs(dst, exist_ok=True)
                for item in os.listdir(src):
                    s = os.path.join(src, item)
                    d = os.path.join(dst, item)
                    if os.path.isdir(s):
                        os.makedirs(d, exist_ok=True)
                        for root, dirs, files in os.walk(s):
                            for f in files:
                                sf = os.path.join(root, f)
                                df = os.path.join(d, os.path.relpath(sf, s))
                                os.makedirs(os.path.dirname(df), exist_ok=True)
                                shutil.copy2(sf, df)
                    else:
                        shutil.copy2(s, d)

        # Install ncurses headers from source (cmd-pkgs package lacks headers)
        # Download ncurses source for headers
        ncurses_src = os.path.join(home, "tmp/ncurses-6.4-src")
        if not os.path.exists(ncurses_src):
            src_tarball = os.path.join(home, "tmp/ncurses-6.4.tar.gz")
            src_url = "https://github.com/mirror/ncurses/archive/refs/tags/v6.4.tar.gz"
            self.run(f'curl -fSL -o "{src_tarball}" "{src_url}"', env="conanbuild")
            self.run(f'mkdir -p "{ncurses_src}" && tar xzf "{src_tarball}" -C "{home}/tmp/"', env="conanbuild")

        # Generate headers using autoconf (patch config.guess for HarmonyOS)
        ncurses_dir = os.path.join(home, "tmp/ncurses-6.4")
        if os.path.isdir(ncurses_dir):
            # Patch config.guess/config.sub for HarmonyOS
            self._patch_config_guess(ncurses_dir)
            os.makedirs(os.path.join(home, "usr/local/include"), exist_ok=True)
            # Run configure to generate headers
            self.run(
                f'cd "{ncurses_dir}" && '
                f'TMPDIR={home}/tmp '
                f'./configure --prefix={home}/usr/local --with-shared=no --without-debug --enable-widec 2>&1 || true',
                env="conanbuild"
            )
            # Fix umask issue in config.status
            cfg_status = os.path.join(ncurses_dir, "config.status")
            if os.path.isfile(cfg_status):
                with open(cfg_status, 'r') as f:
                    content = f.read()
                content = content.replace('umask 077', 'umask 000')
                with open(cfg_status, 'w') as f:
                    f.write(content)
                self.run(f'cd "{ncurses_dir}" && /data/service/hnp/bin/bash ./config.status 2>&1 || true', env="conanbuild")
            # Generate headers
            self.run(f'cd "{ncurses_dir}/include" && make curses.h term.h 2>&1 || true', env="conanbuild")
            # Copy headers
            for hdr in ["curses.h", "term.h", "termcap.h", "unctrl.h", "ncurses_cfg.h",
                        "hashsize.h", "ncurses_def.h", "parametrized.h", "config.h", "ncurses_dll.h"]:
                src_h = os.path.join(ncurses_dir, "include", hdr)
                dst_h = os.path.join(home, "usr/local/include", hdr)
                if os.path.isfile(src_h):
                    shutil.copy2(src_h, dst_h)
            # Create ncurses.h symlink
            ncurses_h = os.path.join(home, "usr/local/include/ncurses.h")
            curses_h = os.path.join(home, "usr/local/include/curses.h")
            if not os.path.exists(ncurses_h) and os.path.exists(curses_h):
                if os.path.islink(ncurses_h) or os.path.exists(ncurses_h):
                    os.remove(ncurses_h)
                os.symlink("curses.h", ncurses_h)

    def _patch_config_guess(self, src_dir):
        """Patch config.guess and config.sub for HarmonyOS support."""
        for cfg_file in ["config.guess", "config.sub"]:
            path = os.path.join(src_dir, cfg_file)
            if not os.path.isfile(path):
                continue
            with open(path, 'r') as f:
                content = f.read()
            if "HarmonyOS" not in content and cfg_file == "config.guess":
                insert = (
                    '    *:HarmonyOS:*:*)\n'
                    '\tcase "$UNAME_MACHINE" in\n'
                    '\t    aarch64|arm64) MACHINE=aarch64 ;;\n'
                    '\t    *) MACHINE="$UNAME_MACHINE" ;;\n'
                    '\tesac\n'
                    '\tGUESS=${MACHINE}-unknown-linux-ohos\n'
                    '\t;;\n\n'
                )
                content = content.replace(
                    'case $UNAME_MACHINE:$UNAME_SYSTEM:$UNAME_RELEASE:$UNAME_VERSION in\n    *:NetBSD:*:*)',
                    'case $UNAME_MACHINE:$UNAME_SYSTEM:$UNAME_RELEASE:$UNAME_VERSION in\n' + insert + '    *:NetBSD:*:*)'
                )
                with open(path, 'w') as f:
                    f.write(content)
            elif cfg_file == "config.sub" and "ohos" not in content:
                content = content.replace('gnu* | android* | bsd*', 'gnu* | android* | ohos* | bsd*')
                content = content.replace(
                    'linux-gnu* | linux-dietlibc* | linux-android* | linux-newlib* \\\n\t\t   | linux-musl*',
                    'linux-gnu* | linux-dietlibc* | linux-android* | linux-newlib* | linux-ohos* \\\n\t\t   | linux-musl*'
                )
                with open(path, 'w') as f:
                    f.write(content)

    def generate(self):
        env = Environment()
        env.define("CC", "clang")
        env.define("CXX", "clang++")
        env.vars(self).save_script("conanautotools_cc")

        tc = AutotoolsToolchain(self)
        home = os.path.expanduser("~")
        tc.configure_args.append(f"NCURSES_CFLAGS=-I{home}/usr/local/include")
        tc.configure_args.append(f"NCURSES_LIBS=-L{home}/usr/local/lib -lncursesw")
        tc.configure_args.append(f"LDFLAGS=-L{home}/usr/local/lib")
        tc.generate()

    def build(self):
        self._ensure_ncurses()
        apply_conandata_patches(self)
        autotools = Autotools(self)
        autotools.configure()
        autotools.make(args=["-j1"])

    def package(self):
        autotools = Autotools(self)
        autotools.install()

    def package_info(self):
        self.cpp_info.bindirs = ["bin"]
