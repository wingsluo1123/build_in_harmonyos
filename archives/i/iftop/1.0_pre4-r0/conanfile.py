#!/usr/bin/env python3
"""Conan recipe — iftop 1.0_pre4-r0 (autotools application).

iftop is a real-time bandwidth monitoring tool that displays network
usage by host. On HarmonyOS PC it is adapted as follows (see notes.md):

  * ncurses is unavailable as a Conan package, so it is installed via
    cmd-pkgs (prebuilt static library + bundled headers tarball).
  * libpcap/1.10.6 is a Conan dependency from the ohpcd artifact repo.
  * config.guess/config.sub are patched for HarmonyOS platform detection.
  * pthread_cancel is unavailable on musl/OHOS, replaced with flag+join.
  * Global variables in ui_common.h are changed to extern declarations.

R26: Static linking for terminal tools (system-name libs).
R32: settings.os must check in ("Linux", "OHOS").
R38: Command-line tool, commands.json declared at software level.
"""
import os
import subprocess

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.files import (
    get, save, load, apply_conandata_patches,
    export_conandata_patches, copy,
)
from conan.tools.gnu import Autotools, AutotoolsToolchain
from conan.tools.layout import basic_layout


def _get_prefix():
    """Get the prefix for installing/finding system dependencies.

    Always returns a user-writable path (never /usr/local).
    Uses DEFAULT_PREFIX env var (set by CI/HNP environment) or ~/usr/local.
    """
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
    import tarfile
    inc_dst = os.path.join(prefix, "include")
    os.makedirs(inc_dst, exist_ok=True)
    if header_tarball and os.path.exists(header_tarball):
        with tarfile.open(header_tarball, "r:gz") as tar:
            tar.extractall(inc_dst)
    # Create ncursesw.h wrapper for configure test
    ncursesw_h = os.path.join(inc_dst, "ncursesw.h")
    if not os.path.exists(ncursesw_h):
        with open(ncursesw_h, "w") as f:
            f.write('#include <curses.h>\n')


class IftopConan(ConanFile):
    name = "iftop"
    version = "1.0_pre4-r0"
    description = "Real-time bandwidth monitoring tool (display bandwidth usage on an interface by host)"
    license = "GPL-2.0-or-later"
    homepage = "https://pdw.ex-parrot.com/iftop/"
    url = ""  # CI fills this

    package_type = "application"

    settings = "os", "compiler", "build_type", "arch"

    def export_sources(self):
        export_conandata_patches(self)
        copy(self, "ncurses-headers.tar.gz", self.recipe_folder, self.export_sources_folder)

    def requirements(self):
        # libpcap is a Conan dependency from the ohpcd artifact repo.
        self.requires("libpcap/1.10.6")
        # ncurses is system-installed via cmd-pkgs, not a Conan dep.

    def validate(self):
        # R32: settings.os must check in ("Linux", "OHOS")
        if self.settings.os not in ("Linux", "OHOS"):
            raise ConanInvalidConfiguration(
                "iftop is only supported on Linux/OHOS, not " + str(self.settings.os)
            )

    def layout(self):
        basic_layout(self)
        # In-source build: configure references config/pthread.c by relative
        # path, so build must happen in the source root, not a subfolder.
        self.folders.build = "."
        self.folders.generators = "."

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)
        apply_conandata_patches(self)

    def generate(self):
        prefix = _get_prefix()
        hdr_tarball = os.path.join(self.source_folder, "ncurses-headers.tar.gz")

        # Ensure ncurses is installed via cmd-pkgs
        if not _is_ncurses_installed(prefix):
            _install_cmd_pkg("ncurses", "6.4", prefix)
        # cmd-pkgs ncurses only ships library, not headers - install from bundled tarball
        if not _is_ncurses_headers_installed(prefix):
            _install_ncurses_headers(prefix, hdr_tarball)

        tc = AutotoolsToolchain(self)

        # Include paths for ncurses (system-installed)
        inc = os.path.join(prefix, "include")
        lib = os.path.join(prefix, "lib")
        if os.path.isdir(inc):
            tc.extra_cflags.append("-I" + inc)
        if os.path.isdir(lib):
            tc.extra_ldflags.append("-L" + lib)

        # libpcap: tell configure where to find it (Conan dependency)
        # The configure script has a custom pcap.h check that saves/restores
        # CPPFLAGS, so we need both --with-libpcap and explicit flags.
        libpcap = self.dependencies.get("libpcap")
        if libpcap:
            pcap_prefix = libpcap.package_folder
            pcap_inc = os.path.join(pcap_prefix, "include")
            pcap_lib = os.path.join(pcap_prefix, "lib")
            tc.configure_args.append("--with-libpcap=" + pcap_prefix)
            if os.path.isdir(pcap_inc):
                tc.extra_cflags.append("-I" + pcap_inc)
            if os.path.isdir(pcap_lib):
                tc.extra_ldflags.append("-L" + pcap_lib)

        # R26: Terminal tools - system same-name libs must be static
        tc.extra_ldflags.append("-static")

        # Tell configure where to find ncurses
        tc.configure_args.append("--with-curses=" + prefix)

        # Install sbin binaries to bin/ for CI compatibility (L2/L5 checks)
        tc.configure_args.append("--sbindir=${prefix}/bin")

        tc.generate()

    def _fix_config_status(self, build):
        """Fix config.status: remove umask 077 for temp dir (HMDFS permission).

        config.status is a generated file (not in source tarball), so it
        cannot be patched via conandata.yml. This fix must be applied inline
        after configure generates it.
        """
        path = os.path.join(build, "config.status")
        if not os.path.exists(path):
            return
        content = load(self, path)
        content = content.replace("umask 077 && mktemp", "mktemp")
        content = content.replace("umask 077 && mkdir", "mkdir")
        content = content.replace(
            "ac_tmp=$tmp",
            'ac_tmp=$tmp\nchmod 755 "$tmp" 2>/dev/null'
        )
        save(self, path, content)

    def build(self):
        # Pre-fix configure: remove umask 077 for HMDFS compatibility
        # (configure is a generated file, cannot be patched via conandata)
        configure_path = os.path.join(self.source_folder, "configure")
        if os.path.exists(configure_path):
            content = load(self, configure_path)
            content = content.replace("umask 077", "umask 022")
            save(self, configure_path, content)

        autotools = Autotools(self)
        autotools.configure()

        # Fix config.status if it still has umask 077 (generated file)
        self._fix_config_status(self.build_folder)

        # If config.status failed during configure, re-run it manually
        cs_path = os.path.join(self.build_folder, "config.status")
        mk_path = os.path.join(self.build_folder, "Makefile")
        if os.path.exists(cs_path) and not os.path.exists(mk_path):
            self._fix_config_status(self.build_folder)
            self.run("cd " + self.build_folder + " && bash config.status")

        # Build
        autotools.make(args=["-j1"])

    def package(self):
        autotools = Autotools(self)
        autotools.install()

    def package_info(self):
        # iftop is a standalone terminal binary, not a library
        self.cpp_info.libs = []
        self.cpp_info.bindirs = ["bin"]
        # Ensure iftop binary is on PATH for VirtualRunEnv (test_package)
        self.runenv_info.prepend_path("PATH", os.path.join(self.package_folder, "bin"))
