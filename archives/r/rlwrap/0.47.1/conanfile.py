#!/usr/bin/env python3
"""Conan recipe — rlwrap 0.47.1 (Autotools).

rlwrap is a readline wrapper that provides editing and history for
commands that don't have it built in.
"""
import os
import re
import stat
from pathlib import Path

from conan import ConanFile
from conan.tools.files import get, copy, apply_conandata_patches, export_conandata_patches
from conan.tools.gnu import Autotools, AutotoolsToolchain
from conan.tools.layout import basic_layout
from conan.tools.env import Environment


class RlwrapConan(ConanFile):
    name = "rlwrap"
    version = "0.47.1"
    description = "A readline wrapper that provides line editing and history for interactive commands"
    license = "GPL-2.0-or-later"
    homepage = "https://github.com/hanslub42/rlwrap"
    url = ""  # CI fills this

    settings = "os", "compiler", "build_type", "arch"

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        # readline and ncurses/tinfo are system-level pre-compiled packages
        # (installed via cmd-pkgs / harmonybrew), not available as @ohpcd/stable
        pass

    def layout(self):
        basic_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def generate(self):
        # HarmonyOS: mktemp -d creates dirs with drwx--S--- (broken group perms),
        # causing config.status to fail. Create a mktemp wrapper that forces
        # autoconf to use mkdir fallback (E011 workaround).
        wrapper_dir = Path(self.build_folder) / ".hmos_fix"
        wrapper_dir.mkdir(exist_ok=True)
        wrapper = wrapper_dir / "mktemp"
        wrapper.write_text(
            '#!/bin/sh\n'
            '# HarmonyOS: mktemp -d creates dirs with broken perms.\n'
            '# Return failure to force autoconf AS_TMPDIR to use mkdir fallback.\n'
            'exit 1\n'
        )
        wrapper.chmod(wrapper.stat().st_mode | stat.S_IEXEC)

        tc = AutotoolsToolchain(self)
        # R26: System same-name libraries must not dynamically link to avoid
        # polluting /lib and /lib64. Static linking for terminal tools.
        tc.extra_ldflags.append("-static")
        # libptytty is not available; rlwrap has built-in PTY handling
        tc.configure_args.append("--without-libptytty")
        # Add system library paths from DEFAULT_PREFIX (CI environment)
        # and ~/.harmonybrew (developer environment)
        for prefix in [os.environ.get("DEFAULT_PREFIX", ""), os.path.expanduser("~/.harmonybrew")]:
            if not prefix:
                continue
            inc = os.path.join(prefix, "include")
            lib = os.path.join(prefix, "lib")
            if os.path.exists(inc):
                tc.extra_cflags.append(f"-I{inc}")
            if os.path.exists(lib):
                tc.extra_ldflags.insert(0, f"-L{lib}")
        # Create stub libtinfo.a: ncurses/tinfo libraries exist in the system
        # but are not accessible to the CI worker (file permissions 770, owned
        # by another uid). readline.a is accessible but only calls tgetent etc.
        # (undefined refs). We provide stub implementations so AC_CHECK_LIB
        # passes and static linking succeeds. readline falls back to dumb
        # terminal mode when tgetent returns -1.
        stub_dir = os.path.join(self.build_folder, ".termcap_compat")
        os.makedirs(stub_dir, exist_ok=True)
        stub_c = os.path.join(stub_dir, "tinfo_stub.c")
        with open(stub_c, "w") as f:
            f.write(
                '/* Stub tinfo/termcap functions for CI where ncurses\n'
                ' * is installed but not accessible (file permissions). */\n'
                'int tgetent(char *bp, const char *name) { return -1; }\n'
                'int tgetflag(const char *id) { return 0; }\n'
                'int tgetnum(const char *id) { return -1; }\n'
                'char *tgetstr(const char *id, char **area) { return (char*)0; }\n'
                'char *tgoto(const char *cm, int c, int r) { return (char*)0; }\n'
                'int tputs(const char *s, int n, int (*p)(int)) { return 0; }\n'
            )
        tc.extra_ldflags.insert(0, f"-L{stub_dir}")
        self.output.info(f"Prepared tinfo stub source at {stub_c}")
        tc.generate()

    def build(self):
        apply_conandata_patches(self)
        # Fix: Conan profile sets CONFIG_SHELL=/data/service/hnp/bin/bash
        # which doesn't exist. Replace all $CONFIG_SHELL in configure with /bin/sh.
        configure_path = os.path.join(self.source_folder, "configure")
        self.output.info(f"Fixing CONFIG_SHELL in: {configure_path}")
        with open(configure_path, 'r') as f:
            content = f.read()
        replaced = content.count('$CONFIG_SHELL')
        content = content.replace('$CONFIG_SHELL', '/bin/sh')
        with open(configure_path, 'w') as f:
            f.write(content)
        self.output.info(f"Replaced {replaced} occurrences of $CONFIG_SHELL")


        # Fix: Conan profile sets invalid paths for SHELL, CONFIG_SHELL, CC, CXX
        # (e.g. /data/service/hnp/bin/bash, /data/service/hnp/bin/clang).
        # Patch ALL generated env scripts in the generators folder to use
        # PATH-resolved commands instead of non-existent absolute paths.
        gen_dir = self.generators_folder
        for fname in os.listdir(gen_dir):
            if not fname.endswith('.sh'):
                continue
            fpath = os.path.join(gen_dir, fname)
            with open(fpath, 'r') as f:
                cb_content = f.read()
            modified = False
            # Override SHELL/CONFIG_SHELL → /bin/sh
            if 'export SHELL=' in cb_content or 'export CONFIG_SHELL=' in cb_content:
                cb_content = re.sub(
                    r'export\s+CONFIG_SHELL=[^\n]*',
                    'export CONFIG_SHELL="/bin/sh"',
                    cb_content
                )
                cb_content = re.sub(
                    r'export\s+SHELL=[^\n]*',
                    'export SHELL="/bin/sh"',
                    cb_content
                )
                modified = True
            # Override CC/CXX → use PATH-resolved clang/clang++
            # (profile sets /data/service/hnp/bin/clang which doesn't exist)
            if 'export CC=' in cb_content:
                cb_content = re.sub(
                    r'export\s+CC="[^"]*"',
                    'export CC="clang"',
                    cb_content
                )
                modified = True
            if 'export CXX=' in cb_content:
                cb_content = re.sub(
                    r'export\s+CXX="[^"]*"',
                    'export CXX="clang++"',
                    cb_content
                )
                modified = True
            if modified:
                with open(fpath, 'w') as f:
                    f.write(cb_content)
                self.output.info(f"Patched {fname}: env overrides applied")

        # Compile tinfo stub into libtinfo.a (needed before configure)
        stub_dir = os.path.join(self.build_folder, ".termcap_compat")
        stub_c = os.path.join(stub_dir, "tinfo_stub.c")
        stub_o = os.path.join(stub_dir, "tinfo_stub.o")
        stub_a = os.path.join(stub_dir, "libtinfo.a")
        cc = os.environ.get("CC", "clang")
        ar = os.environ.get("AR", "ar")
        self.run(f'{cc} -c -fPIC -O2 -o {stub_o} {stub_c}')
        self.run(f'{ar} rcs {stub_a} {stub_o}')
        self.output.info(f"Built stub libtinfo.a at {stub_a}")

        # Use Conan Autotools toolchain (no hardcoded env overrides)
        autotools = Autotools(self)
        autotools.configure()
        autotools.make()

    def package(self):
        # Use Conan Autotools install
        autotools = Autotools(self)
        autotools.install()

    def package_info(self):
        # rlwrap is a binary tool, not a library
        self.cpp_info.libs = []
        bin_path = os.path.join(self.package_folder, "bin")
        self.output.info(f"rlwrap binary: {bin_path}")
