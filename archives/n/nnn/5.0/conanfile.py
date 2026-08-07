#!/usr/bin/env python3
"""Conan recipe — nnn 5.0 (Makefile, CLI tool)"""
import os
import glob

from conan import ConanFile
from conan.tools.files import get, copy, replace_in_file, apply_conandata_patches, export_conandata_patches
from conan.tools.layout import basic_layout
from conan.tools.gnu import PkgConfigDeps
from conan.tools.env import VirtualBuildEnv, VirtualRunEnv


class NnnConan(ConanFile):
    name = "nnn"
    version = "5.0"
    description = "The unorthodox terminal file manager (nnn³)"
    license = "BSD-2-Clause"
    homepage = "https://github.com/jarun/nnn"
    url = "https://gitcode.com/OpenHarmonyPCDeveloper/build_in_harmonyos"

    package_type = "application"

    settings = "os", "arch", "compiler", "build_type"

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        self.requires("ncurses/6.6")
        self.requires("musl-fts/1.2.7")

    def layout(self):
        basic_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def generate(self):
        pkg_config = PkgConfigDeps(self)
        pkg_config.generate()
        env = VirtualBuildEnv(self)
        env.generate()
        VirtualRunEnv(self).generate(scope="build")

    def build(self):
        apply_conandata_patches(self)
        readline_install = self._build_readline()
        self._build_nnn(readline_install)

    def _get_cc(self):
        """Get C compiler from Conan conf (R33: never use bare ${CC})."""
        try:
            compilers = self.conf.get("tools.build:compiler_executables", {}, check_type=dict)
            if compilers and "c" in compilers:
                return compilers["c"]
        except Exception:
            pass
        return "clang"

    def _get_dep_paths(self):
        """Extract include and lib directories from Conan dependencies."""
        ncurses_dep = self.dependencies["ncurses"]
        fts_dep = self.dependencies["musl-fts"]
        ncurses_include = os.path.join(ncurses_dep.package_folder, "include")
        ncurses_lib = os.path.join(ncurses_dep.package_folder, "lib")
        fts_include = os.path.join(fts_dep.package_folder, "include")
        fts_lib = os.path.join(fts_dep.package_folder, "lib")
        return ncurses_include, ncurses_lib, fts_include, fts_lib

    def _build_readline(self):
        """Download, patch, and build readline 8.2 from source.

        readline is not published to the ohpcd Conan repo, so we build it
        from source as part of the nnn build process. This preserves full
        readline functionality (history, tab completion, etc.) as required
        by the no-stripping policy.
        """
        readline_data = self.conan_data.get("readline_source", {})
        readline_url = readline_data.get("url",
            "https://ftp.gnu.org/pub/gnu/readline/readline-8.2.tar.gz")
        readline_sha256 = readline_data.get("sha256",
            "3feb7171f16a84ee82ca18a36d7b9be109a52c04f492a053331d7d1095007c35")

        readline_dir = os.path.join(self.build_folder, "readline-src")
        get(self, readline_url, sha256=readline_sha256,
            destination=readline_dir, strip_root=True)

        # --- Patch config.guess: add HarmonyOS detection ---
        config_guess = os.path.join(readline_dir, "support", "config.guess")
        replace_in_file(self, config_guess,
            "*:Bitrig:*:*)",
            "*:HarmonyOS:*:*)\n\t\tcase \"$UNAME_MACHINE\" in\n\t\t\taarch64|arm64)\n\t\t\t\tMACHINE=aarch64\n\t\t\t\t;;\n\t\t\tarmv7*|armv8*)\n\t\t\t\tMACHINE=arm\n\t\t\t\t;;\n\t\t\tx86_64|amd64)\n\t\t\t\tMACHINE=x86_64\n\t\t\t\t;;\n\t\t\ti?86)\n\t\t\t\tMACHINE=i686\n\t\t\t\t;;\n\t\t\t*)\n\t\t\t\tMACHINE=\"$UNAME_MACHINE\"\n\t\t\t\t;;\n\t\tesac\n\t\tGUESS=${MACHINE}-unknown-linux-ohos\n\t\t;;\n    *:Bitrig:*:*)")
        os.chmod(config_guess, 0o755)

        # --- Patch config.sub: accept linux-ohos* (3 changes needed) ---
        config_sub = os.path.join(readline_dir, "support", "config.sub")
        # Change 1: Add linux-ohos* to maybe_os case
        replace_in_file(self, config_sub,
            "| linux-* |",
            "| linux-* | linux-ohos* |")
        # Change 2: Add ohos* to OS validation list
        replace_in_file(self, config_sub,
            "gnu* | android* | bsd*",
            "gnu* | android* | ohos* | bsd*")
        # Change 3: Add linux-ohos* to kernel-OS validation
        replace_in_file(self, config_sub,
            "| linux-musl* | linux-relibc* | linux-uclibc* )",
            "| linux-musl* | linux-relibc* | linux-uclibc* | linux-ohos* )")
        os.chmod(config_sub, 0o755)

        # --- Fix TERMCAP_LIB in shlib/Makefile.in (for shared build correctness) ---
        shlib_makefile = os.path.join(readline_dir, "shlib", "Makefile.in")
        replace_in_file(self, shlib_makefile,
            "-o $@ $(SHARED_OBJ) $(SHLIB_LIBS)",
            "-o $@ $(SHARED_OBJ) $(SHLIB_LIBS) $(TERMCAP_LIB)")
        replace_in_file(self, shlib_makefile,
            "-o $@ $(SHARED_HISTOBJ) xmalloc.so xfree.so $(SHLIB_LIBS)",
            "-o $@ $(SHARED_HISTOBJ) xmalloc.so xfree.so $(SHLIB_LIBS) $(TERMCAP_LIB)")

        # --- Fix HMDFS umask issue: mktemp -d with umask 077 creates
        #     directories that cannot be written to on HarmonyOS HMDFS ---
        configure_path = os.path.join(readline_dir, "configure")
        replace_in_file(self, configure_path, "umask 077 && mktemp", "mktemp")
        replace_in_file(self, configure_path, "umask 077 && mkdir", "mkdir")

        # Get ncurses paths and compiler
        ncurses_include, ncurses_lib, _, _ = self._get_dep_paths()
        cc = self._get_cc()

        # Configure readline
        readline_install = os.path.join(self.build_folder, "readline-install")
        cflags = f"-fPIC -O2 -I{ncurses_include}"
        ldflags = f"-L{ncurses_lib}"
        config_shell = os.environ.get("CONFIG_SHELL", "/data/service/hnp/bin/bash")

        self.run(
            f"cd {readline_dir} && "
            f"CC={cc} CFLAGS='{cflags}' LDFLAGS='{ldflags}' "
            f"CONFIG_SHELL={config_shell} "
            f"./configure --prefix={readline_install} "
            f"--with-curses --disable-shared --enable-static",
            env="conanbuild",
        )

        # Fix config.status umask issue (generated by configure)
        # May not need fixing if configure was already patched
        config_status_path = os.path.join(readline_dir, "config.status")
        if os.path.exists(config_status_path):
            try:
                replace_in_file(self, config_status_path, "umask 077 && mktemp", "mktemp")
                replace_in_file(self, config_status_path, "umask 077 && mkdir", "mkdir")
            except Exception:
                pass  # Already fixed or pattern not present

        # Prevent Makefile regeneration triggering new configure
        self.run(f"cd {readline_dir} && touch configure config.status Makefile")

        # Build readline (R9: -j1)
        self.run(f"cd {readline_dir} && make -j1", env="conanbuild")
        self.run(f"cd {readline_dir} && make install", env="conanbuild")

        # Verify readline was built
        rl_lib = os.path.join(readline_install, "lib", "libreadline.a")
        if not os.path.exists(rl_lib):
            self.output.info("Readline install incomplete, retrying...")
            # Fix any sub-config.status files
            for cs in glob.glob(os.path.join(readline_dir, "**", "config.status"), recursive=True):
                replace_in_file(self, cs, "umask 077 && mktemp", "mktemp")
                replace_in_file(self, cs, "umask 077 && mkdir", "mkdir")
            self.run(
                f"cd {readline_dir} && touch configure config.status Makefile "
                f"&& make -j1 && make install",
                env="conanbuild",
            )

        self.output.info("readline built and installed successfully")
        return readline_install

    def _build_nnn(self, readline_install):
        """Build nnn against readline, ncurses, and musl-fts."""
        cc = self._get_cc()
        ncurses_include, ncurses_lib, fts_include, fts_lib = self._get_dep_paths()

        # Pass compiler flags as make arguments (R33: never use bare ${CC})
        # The nnn Makefile uses += for CFLAGS, so env vars work but make args
        # are more explicit. Use make args for clarity.
        cflags = (
            f"-fPIC -O2 "
            f"-I{ncurses_include} "
            f"-I{readline_install}/include "
            f"-I{fts_include}"
        )
        ldflags = (
            f"-L{ncurses_lib} "
            f"-L{readline_install}/lib "
            f"-L{fts_lib}"
        )
        ldlibs = "-lreadline -lncursesw -lfts -lpthread"
        pkg_config_path = self.generators_folder

        # R9: Use make -j1 (HMDFS doesn't support mkfifo for jobserver)
        self.run(
            f"cd {self.source_folder} && "
            f"make CC={cc} "
            f"CFLAGS='{cflags}' "
            f"LDFLAGS='{ldflags}' "
            f"LDLIBS='{ldlibs}' "
            f"PKG_CONFIG_PATH={pkg_config_path} "
            f"-j1",
            env="conanbuild",
        )

        nnn_bin = os.path.join(self.source_folder, "nnn")
        if not os.path.exists(nnn_bin):
            raise Exception("nnn binary not found after build")

        self.output.info("nnn built successfully")

    def package(self):
        copy(self, "nnn", self.source_folder, os.path.join(self.package_folder, "bin"))
        copy(self, "nnn.1", self.source_folder,
             os.path.join(self.package_folder, "share", "man", "man1"))

    def package_info(self):
        self.cpp_info.libs = []
        self.cpp_info.bindirs = ["bin"]
        self.cpp_info.exelinkflags = []
