#!/usr/bin/env python3
"""Conan recipe — aircrack-ng 1.7 (Autotools: autoreconf + configure + make).

Aircrack-ng is a complete suite of tools for WiFi security auditing:
WEP/WPA-PSK cracking, packet capture/injection, and network analysis.

Build system: autotools (configure.ac + Makefile.am), but the release
tarball does NOT include a pre-generated configure script, so autoreconf
must be run first.

Key adaptations for HarmonyOS:
  - sockaddr_storage redefinition: bionic libc's sys/socket.h and
    linux/socket.h both define struct sockaddr_storage, causing a
    compile error. Patches add #define _UAPI_LINUX_SOCKET_H guard.
  - HMDFS umask 077: config.status uses umask 077 to create temp dirs,
    which fails on HMDFS (setgid + no exec = Permission denied).
    Fixed by patching config.status after configure generates it.
  - Autotools: automake/libtool installed via cmd-pkgs; pkg.m4 from
    pkg-config copied into build/m4/ so PKG_CHECK_MODULES expands.

R32: settings.os must check in ("Linux", "OHOS").
R34: test_package runs aircrack-ng --help to verify binary works.
R38: command-line tool — commands.json declared at software level.
"""
import os
import shutil
import subprocess

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.files import (
    get, save, load, apply_conandata_patches,
    export_conandata_patches,
)
from conan.tools.gnu import Autotools, AutotoolsToolchain
from conan.tools.layout import basic_layout


def _get_prefix():
    """Return user-writable prefix for system deps (never /usr/local).

    DEFAULT_PREFIX is set by the Conan profile buildenv (ci/conan/profiles/ohos-aarch64),
    not a bare shell env var. This is the standard pattern for cmd-pkgs integration.
    """
    prefix = os.environ.get("DEFAULT_PREFIX")
    if prefix:
        return prefix
    return os.path.join(os.path.expanduser("~"), "usr", "local")


def _ensure_cmd_pkg(name, version, prefix):
    """Install a prebuilt package from cmd-pkgs if not already present.

    Raises RuntimeError on failure to avoid silent build issues.
    """
    url = "https://gitcode.com/OpenHarmonyPCDeveloper/cmd-pkgs/releases/download/pkgs/install.sh"
    cmd = f'curl -fsSL {url} | sh -s -- {name} {version} {prefix}'
    result = subprocess.run(cmd, shell=True, timeout=300, capture_output=True, text=True)
    if result.returncode != 0:
        raise RuntimeError(
            f"Failed to install {name} {version} from cmd-pkgs: {result.stderr}"
        )


def _is_tool_available(name):
    """Check if a command-line tool is on PATH."""
    return shutil.which(name) is not None


def _ensure_autotools(prefix):
    """Ensure automake and libtool are installed (from cmd-pkgs)."""
    if not _is_tool_available("automake") or not _is_tool_available("aclocal"):
        _ensure_cmd_pkg("automake", "1.17", prefix)
    if not _is_tool_available("libtoolize") or not _is_tool_available("libtool"):
        _ensure_cmd_pkg("libtool", "2.4.7", prefix)

    # Fix symlinks: cmd-pkgs installs scripts with shebangs pointing to
    # $prefix/bin/{perl,bash,sed} which may not exist.
    hnp_bin = "/data/service/hnp/bin"
    for tool in ["perl", "bash", "sed", "autoconf", "autoheader",
                 "autom4te", "ifnames", "grep", "find", "m4"]:
        real = shutil.which(tool) or os.path.join(hnp_bin, tool)
        if os.path.exists(real):
            link = os.path.join(prefix, "bin", tool)
            if not os.path.exists(link):
                try:
                    os.symlink(real, link)
                except OSError:
                    pass  # symlink may already exist or prefix/bin may be read-only


class AircrackNgConan(ConanFile):
    name = "aircrack-ng"
    version = "1.7"
    description = "Complete suite of tools for WiFi security auditing (WEP/WPA-PSK cracking)"
    license = "GPL-2.0-or-later"
    homepage = "https://www.aircrack-ng.org/"
    url = "https://gitcode.com/OpenHarmonyPCDeveloper/build_in_harmonyos"

    settings = "os", "compiler", "build_type", "arch"
    package_type = "application"

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        # openssl and zlib are system-installed via cmd-pkgs, not conan deps
        pass

    def validate(self):
        # R32: settings.os must check in ("Linux", "OHOS")
        if self.settings.os not in ("Linux", "OHOS"):
            raise ConanInvalidConfiguration(
                "aircrack-ng is only supported on Linux/OHOS, not " + str(self.settings.os)
            )

    def layout(self):
        basic_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)
        apply_conandata_patches(self)

    def generate(self):
        prefix = _get_prefix()

        # Install system dependencies via cmd-pkgs
        if not os.path.exists(os.path.join(prefix, "lib", "libssl.a")):
            _ensure_cmd_pkg("openssl", "1.1.1w", prefix)
        if not os.path.exists(os.path.join(prefix, "lib", "libz.a")):
            _ensure_cmd_pkg("zlib", "1.3.1", prefix)

        # Ensure autotools are available
        _ensure_autotools(prefix)

        tc = AutotoolsToolchain(self)
        # Configure options for static build
        inc = os.path.join(prefix, "include")
        lib = os.path.join(prefix, "lib")
        if os.path.isdir(inc):
            tc.extra_cflags.append("-I" + inc)
            tc.extra_cxxflags.append("-I" + inc)
        if os.path.isdir(lib):
            tc.extra_ldflags.append("-L" + lib)
        # Suppress OpenSSL deprecated API warnings (OpenSSL 1.1.1)
        tc.extra_cflags.append("-Wno-deprecated-declarations")
        tc.extra_cxxflags.append("-Wno-deprecated-declarations")

        tc.configure_args.extend([
            "--with-static=yes",
            "--with-openssl=" + prefix,
            "--without-x",
            "--disable-shared",
            "--enable-static",
            "--disable-experimental",
            "--without-sqlite3",
            "--without-pcap",
            "--without-libnl",
            "--without-hwloc",
            "--without-libgcrypt",
            "--without-pcre",
        ])
        tc.generate()

    def _fix_config_status(self):
        """Fix config.status: replace umask 077 with umask 022.

        On HMDFS, umask 077 + setgid directory = Permission denied when
        config.status tries to write temp .awk files.  This is a generated
        file so it cannot be patched via conandata.yml.  Same pattern as
        abook/0.6.1 conanfile.py.
        """
        path = os.path.join(self.build_folder, "config.status")
        if not os.path.exists(path):
            return
        content = load(self, path)
        content = content.replace("umask 077 && mktemp", "umask 022 && mktemp")
        content = content.replace("umask 077 && mkdir", "umask 022 && mkdir")
        save(self, path, content)

    def _run_autoreconf(self):
        """Run autoreconf to generate configure script.

        The release tarball only contains configure.ac, not a pre-generated
        configure script.  We need automake, libtool, and pkg-config m4
        macros to be available.
        """
        prefix = _get_prefix()
        # Ensure PATH includes our prefix bin (conan run() env must be a list)
        env = [
            "PATH=" + os.path.join(prefix, "bin") + ":" + os.environ.get("PATH", ""),
            "CONFIG_SHELL=" + (shutil.which("bash") or "/data/service/hnp/bin/bash"),
        ]

        # Copy pkg.m4 into build/m4/ so PKG_CHECK_MODULES macro expands
        pkg_m4_candidates = [
            "/data/service/hnp/pkg-config.org/pkg-config_0.29.2/share/aclocal/pkg.m4",
            os.path.join(prefix, "share", "aclocal", "pkg.m4"),
        ]
        m4_dst = os.path.join(self.source_folder, "build", "m4", "pkg.m4")
        for candidate in pkg_m4_candidates:
            if os.path.exists(candidate) and not os.path.exists(m4_dst):
                shutil.copy2(candidate, m4_dst)
                break

        # Create AC_VERSION file (needed by evalrev in configure.ac)
        ac_ver_src = os.path.join(self.source_folder, "AC_VERSION.in")
        ac_ver_dst = os.path.join(self.source_folder, "AC_VERSION")
        if os.path.exists(ac_ver_src) and not os.path.exists(ac_ver_dst):
            shutil.copy2(ac_ver_src, ac_ver_dst)

        # Fix automake's @am_AUTOM4TE@ variable (cmd-pkgs may not substitute it)
        aclocal_path = os.path.join(prefix, "bin", "aclocal")
        if os.path.exists(aclocal_path):
            content = load(self, aclocal_path)
            if "@am_AUTOM4TE@" in content:
                content = content.replace("@am_AUTOM4TE@", "autom4te")
                save(self, aclocal_path, content)
            automake_path = os.path.join(prefix, "bin", "automake")
            if os.path.exists(automake_path):
                content = load(self, automake_path)
                if "@am_AUTOM4TE@" in content:
                    content = content.replace("@am_AUTOM4TE@", "autom4te")
                    save(self, automake_path, content)

        # Run autoreconf (must run in source folder where configure.ac lives)
        self.run("autoreconf -fi", env=env, cwd=self.source_folder)

        # Patch configure: replace umask 077 with umask 022
        configure_path = os.path.join(self.source_folder, "configure")
        if os.path.exists(configure_path):
            content = load(self, configure_path)
            content = content.replace("umask 077", "umask 022")
            save(self, configure_path, content)

    def build(self):
        # Step 1: Run autoreconf to generate configure
        self._run_autoreconf()

        # Step 2: Run configure
        autotools = Autotools(self)
        autotools.configure()

        # Step 3: Fix config.status umask (generated file, cannot patch via conandata)
        self._fix_config_status()

        # If Makefile wasn't generated (config.status failed), re-run it
        cs_path = os.path.join(self.build_folder, "config.status")
        mk_path = os.path.join(self.build_folder, "Makefile")
        if os.path.exists(cs_path) and not os.path.exists(mk_path):
            self._fix_config_status()
            self.run("bash config.status")

        # Step 4: Build
        autotools.make(args=["-j1"])

    def package(self):
        autotools = Autotools(self)
        autotools.install()

    def package_info(self):
        # aircrack-ng is a set of command-line tools, not a library
        self.cpp_info.libs = []
        self.cpp_info.bindirs = ["bin", "sbin"]
