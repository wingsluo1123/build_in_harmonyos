#!/usr/bin/env python3
"""Conan recipe for htop 3.4.1 — Interactive process viewer.

Autotools project (configure + make + make install).
System prebuilt ncurses via DEFAULT_PREFIX env var.
htop is a command-line application (not a library).
"""
import os
import shutil
import subprocess

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.files import get, apply_conandata_patches, export_conandata_patches
from conan.tools.gnu import Autotools, AutotoolsToolchain
from conan.tools.env import Environment
from conan.tools.layout import basic_layout


class HtopConan(ConanFile):
    name = "htop"
    version = "3.4.1"
    description = "Interactive process viewer for Unix systems"
    license = "GPL-2.0"
    homepage = "https://htop.dev/"
    url = "https://github.com/htop-dev/htop"

    package_type = "application"

    settings = "os", "compiler", "build_type", "arch"

    def export_sources(self):
        export_conandata_patches(self)

    def validate(self):
        # R32: Use `in ("Linux", "OHOS")` for settings.os check
        if self.settings.os not in ("Linux", "OHOS"):
            raise ConanInvalidConfiguration(
                f"htop supports Linux/OHOS only, got {self.settings.os}"
            )

    def layout(self):
        basic_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def _ensure_ncurses(self):
        """Ensure ncursesw is available (install via cmd-pkgs if missing)."""
        prefix = os.environ.get("DEFAULT_PREFIX") or os.path.expanduser("~/usr/local")
        lib = os.path.join(prefix, "lib", "libncursesw.a")
        if os.path.exists(lib):
            return prefix
        # Install ncurses via cmd-pkgs
        try:
            subprocess.run(
                ["curl", "-fsSL",
                 "https://gitcode.com/OpenHarmonyPCDeveloper/cmd-pkgs/releases/download/pkgs/install.sh"],
                capture_output=True, text=True, timeout=120,
            ).stdout
            subprocess.run(
                ["sh", "-s", "--", "ncurses", "6.4"],
                input=subprocess.run(
                    ["curl", "-fsSL",
                     "https://gitcode.com/OpenHarmonyPCDeveloper/cmd-pkgs/releases/download/pkgs/install.sh"],
                    capture_output=True, text=True, timeout=120,
                ).stdout,
                shell=True, timeout=180,
            )
        except Exception:
            pass
        return prefix

    def _ensure_mktemp_wrapper(self):
        """Create a mktemp wrapper to work around HMDFS permission issue.

        toybox mktemp -d creates directories with SGID bit that are unwritable
        on HMDFS. This wrapper uses mkdir instead.
        """
        prefix = os.environ.get("DEFAULT_PREFIX") or os.path.expanduser("~/usr/local")
        wrapper_path = os.path.join(prefix, "bin", "mktemp")
        if os.path.exists(wrapper_path) and os.access(wrapper_path, os.X_OK):
            # Check if it's already our wrapper (not toybox)
            try:
                with open(wrapper_path, "r") as f:
                    content = f.read(100)
                if "HMDFS" in content or "mkdir" in content:
                    return wrapper_path
            except Exception:
                pass

        wrapper_content = '''#!/bin/sh
# mktemp wrapper for HMDFS - use mkdir instead of mktemp -d
create_dir=false
template=""
for arg in "$@"; do
    [ "$arg" = "-d" ] && create_dir=true
    [ "$arg" = "-p" ] && continue
    template="$arg"
done
if $create_dir; then
    [ -z "$template" ] && template="${TMPDIR:-/tmp}/confXXXXXX"
    random=$(cat /dev/urandom 2>/dev/null | tr -dc 'a-zA-Z0-9' | head -c 6 || echo $$)
    dirname=$(echo "$template" | sed "s/XXXXXX/$random/")
    umask 077 && mkdir -p "$dirname" 2>/dev/null && echo "$dirname"
else
    exec /bin/mktemp "$@"
fi
'''
        try:
            os.makedirs(os.path.dirname(wrapper_path), exist_ok=True)
            with open(wrapper_path, "w") as f:
                f.write(wrapper_content)
            os.chmod(wrapper_path, 0o755)
        except Exception:
            pass
        return wrapper_path

    def generate(self):
        # Ensure mktemp wrapper is in place for HMDFS
        self._ensure_mktemp_wrapper()

        tc = AutotoolsToolchain(self)
        # R33: Compiler/flags from Conan Toolchain.
        # ncurses is a system prebuilt package (cmd-pkgs).
        sysroot = os.environ.get("DEFAULT_PREFIX") or os.path.expanduser("~/usr/local")
        sys_inc = os.path.join(sysroot, "include")
        sys_lib = os.path.join(sysroot, "lib")

        tc.extra_cflags.append(f"-I{sys_inc}")
        tc.extra_cflags.append(f"-I{os.path.join(sys_inc, 'ncursesw')}")
        tc.extra_cflags.append("-DNCURSES_WIDECHAR")
        tc.extra_ldflags.append(f"-L{sys_lib}")
        # R26: ncurses is a system-name library, must be statically linked
        tc.extra_ldflags.append("-static")

        tc.configure_args.append("--prefix=/")
        tc.generate()

        # Set TMPDIR and ensure mktemp wrapper is in PATH
        env = Environment()
        tmpdir = os.path.expanduser("~/tmp")
        os.makedirs(tmpdir, exist_ok=True)
        env.define("TMPDIR", tmpdir)
        # Prepend sysroot/bin to PATH for mktemp wrapper
        env.prepend_path("PATH", os.path.join(sysroot, "bin"))
        env.vars(self).save_script("env_htop")

    def build(self):
        # Ensure ncurses is available
        self._ensure_ncurses()

        apply_conandata_patches(self)
        autotools = Autotools(self)
        autotools.configure()
        # Use -j1 to avoid HMDFS FIFO issues with make jobserver
        autotools.make(args=["-j1"])

    def package(self):
        autotools = Autotools(self)
        autotools.install()

    def package_info(self):
        self.cpp_info.bindirs = ["bin"]
