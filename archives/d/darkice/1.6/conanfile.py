#!/usr/bin/env python3
"""Conan recipe for darkice 1.6 — live audio streamer.

darkice is a CLI application (not a library). It uses autotools but the
upstream source (SVN-imported GitHub repo) ships only configure.in, so
autoreconf -fi must be run before configure.

Key adaptation notes:
- Source is in darkice/trunk/ subdirectory (SVN-imported repo structure)
- autoreconf needs ACLOCAL_PATH with pkg.m4 for PKG_CHECK_MODULES
- autoconf's config.status uses umask 077 which triggers SELinux denial
  on HarmonyOS; patch configure to use umask 022 instead
- lame and faac detection uses LA_SEARCH_LIB (not pkg-config), needs
  --with-lame-prefix pointing to the dependency's package folder
"""

import os
import shutil

from conan import ConanFile
from conan.tools.files import get, export_conandata_patches, replace_in_file
from conan.tools.gnu import Autotools, AutotoolsToolchain
from conan.tools.layout import basic_layout


class DarkiceConan(ConanFile):
    name = "darkice"
    version = "1.6"
    description = "DarkIce is a live audio streamer that records audio from an audio interface and streams it to an Icecast or ShoutCast server"
    license = "GPL-3.0"
    homepage = "https://github.com/rafael2k/darkice"

    package_type = "application"

    settings = "os", "compiler", "build_type", "arch"

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        # Override libogg version: flac/1.4.3 needs 1.3.5, libvorbis/1.3.7
        # needs 1.3.6 — force 1.3.6 for all to resolve the conflict.
        self.requires("libogg/1.3.6", override=True)
        self.requires("libvorbis/1.3.7")
        self.requires("opus/1.5.2.1")
        self.requires("flac/1.4.3")
        self.requires("lame/4.0")
        # alsa-lib: available as cmd-pkg (system library), not as conan package.
        # configure auto-detects via pkg-config.

    def layout(self):
        basic_layout(self)

    def source(self):
        # The tarball is from a SVN-imported GitHub repo; it extracts to
        # rafael2k-darkice-<hash>/ containing darkice/trunk/ (the actual
        # source), darkice-gui/trunk/, website/, etc.
        get(self, **self.conan_data["sources"], strip_root=False)
        src_folder = self.source_folder
        for entry in os.listdir(src_folder):
            if entry.startswith("rafael2k-darkice"):
                trunk = os.path.join(src_folder, entry, "darkice", "trunk")
                if os.path.isdir(trunk):
                    for item in os.listdir(trunk):
                        shutil.move(os.path.join(trunk, item),
                                    os.path.join(src_folder, item))
                    # Remove the now-empty wrapper directory tree
                    shutil.rmtree(os.path.join(src_folder, entry))
                    break

    def generate(self):
        tc = AutotoolsToolchain(self)
        # Enable conan-managed features (required — will fail if not found)
        tc.configure_args.append("--with-vorbis")
        tc.configure_args.append("--with-opus")
        tc.configure_args.append("--with-flac")
        # lame uses LA_SEARCH_LIB (not pkg-config), needs prefix
        lame_dep = self.dependencies["lame"]
        tc.configure_args.append("--with-lame")
        tc.configure_args.append("--with-lame-prefix={}".format(lame_dep.package_folder))
        # Auto-detect for non-conan system deps (alsa, faac, fdk-aac, jack,
        # samplerate): configure will enable if found, silently disable if not.
        # Explicitly disable truly unavailable deps (no conan recipe, no cmd-pkg)
        tc.configure_args.append("--without-twolame")
        tc.configure_args.append("--without-pulseaudio")
        tc.generate()

    def build(self):
        # Find pkg.m4 location for ACLOCAL_PATH (PKG_CHECK_MODULES macro)
        aclocal_paths = []
        for p in [
            "/data/service/hnp/pkg-config.org/pkg-config_0.29.2/share/aclocal",
            os.path.expanduser("~/usr/local/share/aclocal"),
            "/usr/local/share/aclocal",
            "/usr/share/aclocal",
        ]:
            if os.path.isdir(p) and p not in aclocal_paths:
                aclocal_paths.append(p)
        aclocal_arg = ":".join(aclocal_paths) if aclocal_paths else ""

        # System pkg-config path for cmd-pkg installs (alsa, faac, etc.)
        sys_pkg = os.path.expanduser("~/usr/local/lib/pkgconfig")
        if os.path.isdir(sys_pkg):
            cur = os.environ.get("PKG_CONFIG_PATH", "")
            if sys_pkg not in cur:
                os.environ["PKG_CONFIG_PATH"] = sys_pkg + (":" + cur if cur else "")

        src = self.source_folder

        # Create a wrapper script that sets ACLOCAL_PATH then runs autoreconf.
        # Conan's env="conanbuild" sources conanbuild.sh (PATH, CC, etc.) but
        # doesn't preserve os.environ changes. The wrapper bridges this gap:
        # conanbuild.sh provides PATH (find automake/aclocal), wrapper provides
        # ACLOCAL_PATH (find pkg.m4 for PKG_CHECK_MODULES expansion).
        wrapper = os.path.join(self.build_folder, "_run_autoreconf.sh")
        with open(wrapper, "w") as f:
            f.write("#!/bin/sh\n")
            f.write('cd "{}"\n'.format(src))
            if aclocal_arg:
                f.write('export ACLOCAL_PATH="{}"\n'.format(aclocal_arg))
            f.write("exec autoreconf -fi\n")
        os.chmod(wrapper, 0o755)

        self.run("./_run_autoreconf.sh", env="conanbuild")

        # Fix: autoconf's config.status uses umask 077 when creating temp
        # directories, which triggers SELinux denial on HarmonyOS (E046).
        # Patch the generated configure script to use umask 022 instead.
        replace_in_file(self, os.path.join(src, "configure"),
                        "umask 077", "umask 022")

        autotools = Autotools(self)
        try:
            autotools.configure()
        except Exception as e:
            # Print config.log tail for CI debugging
            log_file = os.path.join(src, "config.log")
            if os.path.exists(log_file):
                with open(log_file) as f:
                    lines = f.readlines()
                print("=== config.log (last 30 lines) ===")
                for line in lines[-30:]:
                    print(line.rstrip())
            raise
        autotools.make(args=["-j1"])

    def package(self):
        autotools = Autotools(self)
        autotools.install()

    def package_info(self):
        self.cpp_info.bindirs = ["bin"]
