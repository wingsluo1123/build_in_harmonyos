#!/usr/bin/env python3
"""Conan recipe for rsyslog 8.2404.0 — Autotools project (configure + make).

rsyslog is a high-performance syslog daemon with modular architecture.
Build produces rsyslogd binary and shared library modules (.so).

OHOS adaptations:
- HMDFS umask 077 fix (E011): configure temp directory permission
- pthread_cancel not available on OHOS/musl: condition compilation guards
- config.guess/config.sub updated for HarmonyOS platform detection (E007)
- CC=clang for systems without cc symlink (E001)
"""
import os

from conan import ConanFile
from conan.tools.files import get, apply_conandata_patches, export_conandata_patches
from conan.tools.gnu import Autotools, AutotoolsToolchain, AutotoolsDeps, PkgConfigDeps
from conan.tools.layout import basic_layout
from conan.tools.env import VirtualRunEnv


class RsyslogConan(ConanFile):
    name = "rsyslog"
    version = "8.2404.0"
    description = "High-performance syslog daemon with modular architecture"
    license = "GPL-3.0-or-later"
    homepage = "https://www.rsyslog.com/"
    url = ""  # CI fills this

    package_type = "application"

    settings = "os", "compiler", "build_type", "arch"

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        self.requires("libestr/0.1.11")
        self.requires("libfastjson/1.2304.0")
        self.requires("libgcrypt/1.11.0")
        self.requires("uuid/2.40.1")

    def layout(self):
        basic_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def generate(self):
        env = VirtualRunEnv(self)
        env.generate()
        tc = AutotoolsToolchain(self)
        tc.generate()
        deps = AutotoolsDeps(self)
        deps.generate()
        pc = PkgConfigDeps(self)
        pc.generate()

    def build(self):
        # E001: Ensure CC/CXX are set for systems without cc symlink
        if self.settings.os in ("Linux", "OHOS"):
            os.environ.setdefault("CC", "clang")
            os.environ.setdefault("CXX", "clang++")
            os.umask(0o022)
            # HarmonyOS: configure test programs need to find shared libs
            # at runtime. Set LD_LIBRARY_PATH to include all dep lib dirs.
            dep_lib_paths = []
            for dep_name in ["libgcrypt", "libgpg-error", "uuid",
                             "libestr", "libfastjson"]:
                try:
                    dep = self.dependencies[dep_name]
                    lib_dir = os.path.join(dep.package_folder, "lib")
                    if os.path.isdir(lib_dir):
                        dep_lib_paths.append(lib_dir)
                except Exception:
                    pass
            if dep_lib_paths:
                cur = os.environ.get("LD_LIBRARY_PATH", "")
                os.environ["LD_LIBRARY_PATH"] = ":".join(dep_lib_paths + ([cur] if cur else []))
            # Add libgcrypt bin to PATH (rsyslog uses libgcrypt-config)
            try:
                dep = self.dependencies["libgcrypt"]
                bin_dir = os.path.join(dep.package_folder, "bin")
                if os.path.isdir(bin_dir):
                    os.environ["PATH"] = bin_dir + ":" + os.environ.get("PATH", "")
            except Exception:
                pass

        apply_conandata_patches(self)

        # R32: OHOS platform adaptations
        if self.settings.os in ("Linux", "OHOS"):
            src = self.source_folder

            # E007: Update config.guess/config.sub for HarmonyOS detection
            # The tarball's config.guess (2018-02-24) doesn't recognize HarmonyOS
            # Copy system's OHOS-aware versions
            cg = os.path.join(src, "config.guess")
            cs = os.path.join(src, "config.sub")
            sys_cg = "/storage/Users/currentUser/usr/local/share/automake-1.16/config.guess"
            sys_cs = "/storage/Users/currentUser/usr/local/share/automake-1.16/config.sub"
            if os.path.exists(sys_cg):
                self.run(f"cp {sys_cg} {cg}")
            if os.path.exists(sys_cs):
                self.run(f"cp {sys_cs} {cs}")

            # E011 HMDFS fix: replace umask 077 with umask 000 in configure
            conf = os.path.join(src, "configure")
            self.run(f"sed -i 's/umask 077 && mktemp/umask 000 && mktemp/g' {conf}")
            self.run("sed -i 's|tmp=\\./conf\\$\\$-\\$RANDOM|tmp=$TMPDIR/build-tmp/rsyslog-conf$$-$RANDOM|g' " + conf)
            self.run("sed -i 's|(umask 077 && mkdir \"$tmp\")|(umask 000 && mkdir -p \"$tmp\")|g' " + conf)
            self.run("sed -i 's|cannot create a temporary directory in \\.|cannot create a temporary directory in $TMPDIR/build-tmp|g' " + conf)

        autotools = Autotools(self)
        autotools.configure()
        autotools.make(args=["-j1"])

    def package(self):
        autotools = Autotools(self)
        autotools.install()
        # HMDFS workaround: ensure installed files are world-readable
        if self.settings.os in ("Linux", "OHOS"):
            self.run(f"chmod -R a+r {self.package_folder}")
            self.run(f"find {self.package_folder} -type d -exec chmod a+rx {{}} \\;")

    def package_info(self):
        self.cpp_info.libs = []
        self.cpp_info.includedirs = []
        self.cpp_info.bindirs = ["bin"]
        self.cpp_info.libdirs = ["lib/rsyslog"]
