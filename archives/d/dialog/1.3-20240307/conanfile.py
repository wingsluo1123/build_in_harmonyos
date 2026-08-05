#!/usr/bin/env python3
"""Conan recipe — dialog 1.3-20240307 (autotools: configure + make).

dialog is a TUI dialog box library and command-line tool. On HarmonyOS PC it
is adapted as follows (see notes.md for the full rationale):

  * ncurses is not published to the Conan artifact repository, so it is treated
    as a system dependency installed via cmd-pkgs (static library + headers).
    No external Conan dependency is required.
  * config.sub is patched to recognize 'ohos' as a valid OS suffix.
  * The configure script and its generated config.status use 'umask 077' which
    fails on HMDFS (E007). The umask is removed from configure BEFORE running
    it, so config.status is generated without the problematic umask.
  * The build triplet is passed explicitly as 'aarch64-linux-ohos' to avoid
    invoking config.guess (which cannot detect HarmonyOS via uname).

R26: dialog is both a library (libdialog.a) and an application (dialog binary).
     Static linking is used for the ncurses dependency.
R32: settings.os must check in ("Linux", "OHOS").
R34: test_package executes the dialog binary (--version) to verify functionality.
"""
import os
import subprocess
import tarfile

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.files import (
    get, save, load, replace_in_file, apply_conandata_patches,
    export_conandata_patches, copy,
)
from conan.tools.gnu import Autotools, AutotoolsToolchain
from conan.tools.layout import basic_layout


def _get_prefix():
    """Get the prefix for installing/finding system dependencies."""
    prefix = os.environ.get("DEFAULT_PREFIX")
    if prefix:
        return prefix
    return os.path.join(os.path.expanduser("~"), "usr", "local")


def _is_ncurses_installed(prefix):
    """Check if ncurses library is installed at prefix."""
    for libname in ["libncursesw.a", "libncurses.a"]:
        if os.path.exists(os.path.join(prefix, "lib", libname)):
            return True
    return False


def _is_ncurses_headers_installed(prefix):
    """Check if ncurses headers are installed at prefix."""
    return os.path.exists(os.path.join(prefix, "include", "curses.h"))


def _install_cmd_pkg(name, version, prefix):
    """Download and install a cmd-pkgs prebuilt package."""
    url = "https://gitcode.com/OpenHarmonyPCDeveloper/cmd-pkgs/releases/download/pkgs/install.sh"
    cmd = f'curl -fsSL {url} | sh -s -- {name} {version} {prefix}'
    subprocess.run(cmd, shell=True, timeout=300, capture_output=True, text=True)


def _install_ncurses_headers(prefix, header_tarball):
    """Install ncurses headers from bundled tarball (cmd-pkgs only ships libs)."""
    inc_dst = os.path.join(prefix, "include")
    os.makedirs(inc_dst, exist_ok=True)
    if header_tarball and os.path.exists(header_tarball):
        with tarfile.open(header_tarball, "r:gz") as tar:
            tar.extractall(inc_dst)


class DialogConan(ConanFile):
    name = "dialog"
    version = "1.3-20240307"
    description = "display dialog boxes from shell scripts"
    license = "LGPL-2.1"
    homepage = "https://invisible-island.net/dialog/dialog.html"
    url = ""  # CI fills this

    package_type = "application"

    settings = "os", "compiler", "build_type", "arch"

    def export_sources(self):
        export_conandata_patches(self)
        copy(self, "ncurses-headers.tar.gz", self.recipe_folder, self.export_sources_folder)

    def validate(self):
        # R32: settings.os must check in ("Linux", "OHOS")
        if self.settings.os not in ("Linux", "OHOS"):
            raise ConanInvalidConfiguration(
                "dialog is only supported on Linux/OHOS, not " + str(self.settings.os)
            )

    def layout(self):
        basic_layout(self)

    def requirements(self):
        # ncurses is system-installed via cmd-pkgs, not a conan dep.
        pass

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)
        apply_conandata_patches(self)

    def generate(self):
        prefix = _get_prefix()
        hdr_tarball = os.path.join(self.source_folder, "ncurses-headers.tar.gz")

        # Ensure system dependencies (ncurses) are installed via cmd-pkgs
        if not _is_ncurses_installed(prefix):
            _install_cmd_pkg("ncurses", "6.4", prefix)
        # cmd-pkgs ncurses only ships library, not headers - install from bundled tarball
        if not _is_ncurses_headers_installed(prefix):
            _install_ncurses_headers(prefix, hdr_tarball)

        # Create libncurses.a symlink to libncursesw.a (dialog looks for -lncurses)
        libdir = os.path.join(prefix, "lib")
        ncursew = os.path.join(libdir, "libncursesw.a")
        ncurse = os.path.join(libdir, "libncurses.a")
        if os.path.exists(ncursew) and not os.path.exists(ncurse):
            os.symlink("libncursesw.a", ncurse)

        tc = AutotoolsToolchain(self)
        # Pass build/host triplet explicitly to avoid config.guess (E007)
        tc.configure_args.append("--build=aarch64-linux-ohos")
        tc.configure_args.append("--host=aarch64-linux-ohos")
        # Use ncurses (not curses)
        tc.configure_args.append("--with-ncurses")
        # System-installed ncurses
        inc = os.path.join(prefix, "include")
        lib = os.path.join(prefix, "lib")
        if os.path.isdir(inc):
            tc.extra_cflags.append("-I" + inc)
        if os.path.isdir(lib):
            tc.extra_ldflags.append("-L" + lib)
        tc.generate()

    def build(self):
        # Fix umask 077 in configure script BEFORE running it (E007 HMDFS fix).
        # configure generates config.status with the same umask code, so fixing
        # configure first ensures config.status is generated without the issue.
        configure = os.path.join(self.source_folder, "configure")
        replace_in_file(self, configure, "umask 077 && mktemp", "mktemp", strict=False)
        replace_in_file(self, configure, "umask 077 && mkdir", "mkdir", strict=False)

        autotools = Autotools(self)
        autotools.configure()

        # Also fix config.status in case it was generated with umask 077
        # (shouldn't happen after the configure fix, but just in case)
        cs_path = os.path.join(self.build_folder, "config.status")
        mk_path = os.path.join(self.build_folder, "makefile")
        if os.path.exists(cs_path):
            content = load(self, cs_path)
            if "umask 077" in content:
                content = content.replace("umask 077 && mktemp", "mktemp")
                content = content.replace("umask 077 && mkdir", "mkdir")
                save(self, cs_path, content)
                # Re-run config.status to regenerate Makefiles
                if not os.path.exists(mk_path):
                    self.run("cd " + self.build_folder + " && bash config.status")

        # Build with -j1 to avoid HMDFS FIFO issues (make jobserver)
        autotools.make(args=["-j1"])

    def package(self):
        autotools = Autotools(self)
        # Use -j1 for install to avoid HMDFS mkfifo issues
        autotools.install(args=["-j1"])

    def package_info(self):
        # dialog produces both a binary and a static library
        self.cpp_info.libs = ["dialog"]
        self.cpp_info.bindirs = ["bin"]
        # Ensure dialog binary is on PATH for VirtualRunEnv (test_package)
        self.runenv_info.prepend_path("PATH", os.path.join(self.package_folder, "bin"))
