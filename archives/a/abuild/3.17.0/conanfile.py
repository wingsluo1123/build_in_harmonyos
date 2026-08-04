#!/usr/bin/env python3
"""Conan recipe for abuild 3.17.0 — Alpine build tools.

abuild is a set of shell scripts and C helper tools for building Alpine Linux
packages (.apk). This recipe builds the C helper tools (abuild-tar, abuild-gzsplit,
abuild-sudo, abuild-fetch, abuild-rm, abuild-rmtemp) and installs the shell scripts
(abuild, abuild-keygen, abuild-sign, newapkbuild, abump, apkgrel, checkapk, etc.)
with appropriate version/prefix substitution.

Key adaptation points:
- C tools compiled with standard clang (no special OHOS platform changes needed)
- openssl required for abuild-tar (APK signing/verification)
- zlib required for abuild-gzsplit (gzip stream splitting)
- Shell scripts are .in templates with @VERSION@ and @prefix@ substitution
- man pages: scdoc-based, requires scdoc build-time tool
"""

import os

from conan import ConanFile
from conan.tools.files import get, apply_conandata_patches, export_conandata_patches
from conan.tools.layout import basic_layout


class AbuildConan(ConanFile):
    name = "abuild"
    version = "3.17.0"
    description = "Script to build Alpine Packages"
    license = "GPL-2.0-only"
    homepage = "https://gitlab.alpinelinux.org/alpine/abuild/"
    url = "https://gitlab.alpinelinux.org/alpine/abuild/"
    package_type = "application"

    settings = "os", "compiler", "build_type", "arch"

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        # abuild-tar uses openssl for APK signing/verification
        self.requires("openssl/3.5.6")
        # abuild-gzsplit uses zlib for gzip stream splitting
        self.requires("zlib/1.3.1.1")

    def layout(self):
        basic_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def _get_cc(self):
        # R33: Get compiler from Conan conf, not undefined shell variables
        comp_execs = self.conf.get("tools.build:compiler_executables", default={}, check_type=dict)
        return comp_execs.get("c") or "clang"

    def _get_cxx(self):
        comp_execs = self.conf.get("tools.build:compiler_executables", default={}, check_type=dict)
        return comp_execs.get("cpp") or "clang++"

    def _dep_cflags(self, dep_name):
        """Get include flags from a conan dependency."""
        try:
            dep = self.dependencies[dep_name]
            incdirs = dep.cpp_info.includedirs
            if incdirs:
                return " ".join(f"-I{d}" for d in incdirs)
        except Exception:
            pass
        return ""

    def _dep_ldflags(self, dep_name):
        """Get lib directory flags from a conan dependency."""
        try:
            dep = self.dependencies[dep_name]
            libdirs = dep.cpp_info.libdirs
            if libdirs:
                return " ".join(f"-L{d}" for d in libdirs)
        except Exception:
            pass
        return ""

    def _dep_libs(self, dep_name):
        """Get link flags from a conan dependency."""
        try:
            dep = self.dependencies[dep_name]
            libs = dep.cpp_info.libs
            if libs:
                return " ".join(f"-l{l}" for l in libs)
        except Exception:
            pass
        return ""

    def build(self):
        apply_conandata_patches(self)

        src = self.source_folder
        cc = self._get_cc()
        cxx = self._get_cxx()

        # Get dependency flags directly from conan (bypass pkg-config)
        ssl_cflags = self._dep_cflags("openssl")
        ssl_ldflags = self._dep_ldflags("openssl")
        ssl_libs = self._dep_libs("openssl")
        if not ssl_libs:
            ssl_libs = "-lssl -lcrypto"
        zlib_libs = self._dep_libs("zlib")
        if not zlib_libs:
            zlib_libs = "-lz"

        # Makefile uses ?= so these env vars override the pkg-config invocation
        make_prefix = (f"CC={cc} CXX={cxx} "
                       f"SSL_CFLAGS=\"{ssl_cflags}\" "
                       f"SSL_LDFLAGS=\"{ssl_ldflags}\" "
                       f"SSL_LIBS=\"{ssl_libs}\" "
                       f"ZLIB_LIBS=\"{zlib_libs}\"")

        # Build C helper tools using the Makefile
        targets = ["abuild-tar", "abuild-gzsplit", "abuild-sudo",
                    "abuild-fetch", "abuild-rm", "abuild-rmtemp"]
        for target in targets:
            self.run(f"cd {src} && {make_prefix} make {target}")

        # Generate scripts from .in templates
        scripts = ["abuild", "abuild-keygen", "abuild-sign", "newapkbuild",
                    "abump", "apkgrel", "checkapk"]
        for script in scripts:
            self.run(f"cd {src} && make {script}")

        # Fix shebang: abuild.in uses #!/bin/ash which doesn't exist on OHOS
        for script in scripts:
            script_path = os.path.join(src, script)
            if os.path.isfile(script_path):
                with open(script_path, "r") as f:
                    content = f.read()
                if content.startswith("#!/bin/ash"):
                    content = content.replace("#!/bin/ash", "#!/bin/sh", 1)
                    with open(script_path, "w") as f:
                        f.write(content)
                    os.chmod(script_path, 0o755)

        # Generate functions.sh and abuild.conf
        self.run(f"cd {src} && make functions.sh")
        self.run(f"cd {src} && make abuild.conf")

    def package(self):
        src = self.source_folder
        pkg = self.package_folder

        bindir = os.path.join(pkg, "bin")
        sharedir = os.path.join(pkg, "share", "abuild")
        sysconfdir = os.path.join(pkg, "etc")

        os.makedirs(bindir, exist_ok=True)
        os.makedirs(sharedir, exist_ok=True)
        os.makedirs(sysconfdir, exist_ok=True)

        # Install binaries
        usr_bin_files = [
            "abuild", "abuild-keygen", "abuild-sign", "newapkbuild",
            "abump", "apkgrel", "checkapk",
            "abuild-tar", "abuild-gzsplit", "abuild-sudo",
            "abuild-fetch", "abuild-rm", "abuild-rmtemp",
        ]
        for f in usr_bin_files:
            fpath = os.path.join(src, f)
            if os.path.exists(fpath):
                dest = os.path.join(bindir, f)
                os.rename(fpath, dest)
                os.chmod(dest, 0o755)

        # Install shared files
        for f in ["functions.sh", "default.conf", "sample.APKBUILD",
                   "sample.initd", "sample.confd", "sample.pre-install",
                   "sample.post-install"]:
            fpath = os.path.join(src, f)
            if os.path.exists(fpath):
                os.rename(fpath, os.path.join(sharedir, f))

        # Install autotools helper files
        for f in ["config.sub", "config.guess"]:
            fpath = os.path.join(src, f)
            if os.path.exists(fpath):
                os.rename(fpath, os.path.join(sharedir, f))

        # Install config
        for f in ["abuild.conf"]:
            fpath = os.path.join(src, f)
            if os.path.exists(fpath):
                os.rename(fpath, os.path.join(sysconfdir, f))

    def package_info(self):
        self.cpp_info.bindirs = ["bin"]
        self.cpp_info.libs = []