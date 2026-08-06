#!/usr/bin/env python3
"""Conan recipe for gdnsd 3.8.2 — autotools-based authoritative DNS server.

gdnsd is an authoritative DNS server with geographic and load-balancing
plugins. It uses autotools (autoconf/automake) as its build system.

Key OHOS adaptation notes:
- GitHub archive tarball does not include pre-generated configure script.
  Run autoreconf -fi in build() to generate it.
- autotools config.status fails on HMDFS filesystem due to setgid + umask 077
  creating inaccessible temp directories. Workaround: patch config.status
  to use umask 022 after configure runs.
- pthread_setcanceltype/pthread_cancel not implemented on OHOS (musl libc).
  Patches guard these calls with #ifdef __OHOS__.
- ragel is a build-time tool needed to generate vscf.c from vscf.rl.
  Pre-installed via cmd-pkgs, not available as a Conan package.
- userspace-rcu and libsodium are not available as Conan packages.
  Pre-installed via cmd-pkgs, found via pkg-config.
"""
import os

from conan import ConanFile
from conan.tools.files import apply_conandata_patches, export_conandata_patches, get, replace_in_file
from conan.tools.gnu import Autotools, AutotoolsToolchain
from conan.tools.layout import basic_layout
from conan.tools.env import Environment


class GdnsdConan(ConanFile):
    name = "gdnsd"
    version = "3.8.2"
    description = "Authoritative DNS server with geo-routing and load-balancing plugins"
    license = "GPL-3.0-only"
    homepage = "https://gdnsd.org"
    url = "https://github.com/gdnsd/gdnsd"

    package_type = "application"

    settings = "os", "compiler", "build_type", "arch"

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        self.requires("libev/4.33")
        self.requires("openssl/1.1.1w")
        self.requires("zlib/1.3.1")

    # ragel is a build-time state machine compiler needed to generate vscf.c
    # from vscf.rl. Pre-installed via cmd-pkgs on OHOS CI workers.
    # Not yet available as a Conan package in the ohpcd remote.
    # The conan profile PATH includes /storage/Users/currentUser/usr/local/bin
    # where ragel is installed, so the build system finds it automatically.

    def layout(self):
        basic_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def generate(self):
        tc = AutotoolsToolchain(self)

        # On OHOS, ragel/userspace-rcu/libsodium are pre-installed via cmd-pkgs
        # to /storage/Users/currentUser/usr/local/. Set include/lib paths so
        # configure can find them.
        if self.settings.os in ("Linux", "OHOS"):
            local_prefix = "/storage/Users/currentUser/usr/local"
            tc.extra_cflags.append(f"-I{local_prefix}/include")
            tc.extra_ldflags.append(f"-L{local_prefix}/lib")
        tc.generate()

        # Set PKG_CONFIG_PATH for system-installed deps (userspace-rcu, libsodium)
        if self.settings.os in ("Linux", "OHOS"):
            env = Environment()
            pkg_config_path = "/storage/Users/currentUser/usr/local/lib/pkgconfig"
            env.define("PKG_CONFIG_PATH", pkg_config_path)
            env.vars(self).save_script("conan_gdnsd_env")

    def build(self):
        apply_conandata_patches(self)
        autotools = Autotools(self)

        # GitHub archive tarball doesn't include pre-generated configure script
        autotools.autoreconf()

        # OHOS HMDFS workaround: autotools configure/config.status uses umask 077
        # when creating temp dirs, but HMDFS setgid directories make them
        # inaccessible to the build user. Patch configure to use umask 022.
        if self.settings.os == "OHOS":
            configure_script = os.path.join(self.source_folder, "configure")
            if os.path.exists(configure_script):
                replace_in_file(self, configure_script, "umask 077", "umask 022")

        autotools.configure()

        autotools.make(args=["-j1"])

    def package(self):
        autotools = Autotools(self)
        autotools.install()

    def package_info(self):
        # gdnsd is an application — no cpp_info.libs needed
        self.cpp_info.bindirs = ["sbin", "bin", "libexec"]
        self.cpp_info.libdirs = ["lib"]
        self.cpp_info.includedirs = ["include"]
