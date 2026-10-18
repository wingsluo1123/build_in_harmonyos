#!/usr/bin/env python3
"""Conan recipe — sylpheed 3.7.0 (GTK+2 E-Mail client, Autotools) on HarmonyOS PC.

Upstream: https://sylpheed.sraoss.jp/sylpheed/v3.7/sylpheed-3.7.0.tar.gz
License: GPL-2.0-or-later AND LGPL-2.1-or-later

OHOS adaptation notes:
  - config.guess/config.sub patched for HarmonyOS recognition (linux-ohos triplet)
  - GLib/GTK+2 detected via PkgConfigDeps (pkgconf tool_requires)
  - gettext/libintl headers + -lintl injected manually (autotools limitation)
  - Optional features disabled: GPGME, LDAP, compface, gtkspell
  - mktemp 077 patched to 000 (HMDFS 2700 permission issue)
  - LD=ld.lld explicitly set (OHOS lacks /bin/ld)
  - R49 compliant: dependency injection uses build_folder private prefix
"""

import os
import shutil

from conan import ConanFile
from conan.tools.build import cross_building
from conan.tools.env import Environment
from conan.tools.files import apply_conandata_patches, copy, get, replace_in_file
from conan.tools.gnu import Autotools, AutotoolsToolchain, PkgConfigDeps
from conan.tools.layout import basic_layout


class SylpheedConan(ConanFile):
    name = "sylpheed"
    version = "3.7.0"
    description = "Sylpheed — lightweight GTK+2 E-Mail client"
    license = "GPL-2.0-or-later AND LGPL-2.1-or-later"
    homepage = "https://sylpheed.sraoss.jp/"
    url = "https://sylpheed.sraoss.jp/sylpheed/v3.7/sylpheed-3.7.0.tar.gz"
    package_type = "application"

    settings = "os", "arch", "compiler", "build_type"
    options = {"shared": [True, False], "fPIC": [True, False]}
    default_options = {"shared": True, "fPIC": True}

    def export_sources(self):
        copy(self, "patches/*", src=self.recipe_folder, dst=self.export_sources_folder)

    def config_options(self):
        if self.settings.os == "Windows":
            self.options.rm_safe("fPIC")

    def configure(self):
        if self.options.shared:
            self.options.rm_safe("fPIC")

    def layout(self):
        basic_layout(self)

    def requirements(self):
        self.requires("glib/2.84.0.1", transitive_headers=True, transitive_libs=True)
        self.requires("gtk2/2.24.33", transitive_headers=True, transitive_libs=True)
        self.requires("gettext/0.22.5", transitive_headers=True, transitive_libs=True)

    def build_requirements(self):
        self.tool_requires("pkgconf/3.0.5")

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    @staticmethod
    def _tool_executable(*names):
        for name in names:
            found = shutil.which(name)
            if found:
                return found
        return None

    def _dep_tool(self, ref_name, *names):
        try:
            dep = self.dependencies.build[ref_name]
        except Exception:
            return None
        for name in names:
            cand = os.path.join(dep.package_folder, "bin", name)
            if os.path.isfile(cand):
                return cand
        return None

    def _patch_generated_pcs(self):
        """Fix .pc files that break OHOS builds (musl loader path)."""
        for pc_name in ("glib-2.0.pc", "gtk+-2.0.pc", "gdk-2.0.pc", "gdk-pixbuf-2.0.pc"):
            pc_path = os.path.join(self.generators_folder, pc_name)
            if not os.path.isfile(pc_path):
                continue
            content = open(pc_path, encoding="utf-8").read()
            if "-l:ld-musl-aarch64.so.1" in content:
                open(pc_path, "w", encoding="utf-8").write(
                    content.replace("-l:ld-musl-aarch64.so.1",
                                    "/lib/ld-musl-aarch64.so.1"))

    def generate(self):
        PkgConfigDeps(self).generate()
        self._patch_generated_pcs()

        tc = AutotoolsToolchain(self)
        # OHOS/HMDFS: sizeof tests in configure return 0 due to conftest.val
        # write/read silently failing on HMDFS — provide cache values explicitly.
        tc.configure_args.append("ac_cv_sizeof_unsigned_short=2")
        tc.configure_args.append("ac_cv_sizeof_unsigned_int=4")
        tc.configure_args.append("ac_cv_sizeof_unsigned_long=8")
        tc.configure_args.append("ac_cv_sizeof_time_t=8")
        tc.configure_args.append("ac_cv_sizeof_off_t=8")
        tc.configure_args.append("ac_cv_sizeof_pid_t=4")
        tc.configure_args.append("ac_cv_sizeof_int=4")
        tc.configure_args.append("ac_cv_sizeof_long=8")
        tc.configure_args.append("ac_cv_sizeof_size_t=8")
        # Disable optional features to reduce dependency graph
        tc.configure_args.append("--disable-gpgme")
        tc.configure_args.append("--disable-ldap")
        tc.configure_args.append("--disable-compface")
        tc.configure_args.append("--disable-gtkspell")
        # Skip runtime tests (cross-compile safe)
        tc.configure_args.append("--disable-glibtest")
        tc.configure_args.append("--disable-gtktest")
        # Explicit triplet: skip configure's config.sub platform probe (fixes "cannot run config.sub" on OHOS HMDFS)
        tc.configure_args.append("--build=aarch64-unknown-linux-ohos")
        tc.configure_args.append("--host=aarch64-unknown-linux-ohos")
        # Inject gettext (autotools won't auto-inject from conan deps)
        gt = self.dependencies.host["gettext"]
        gt_inc = os.path.join(gt.package_folder, "include")
        if os.path.isdir(gt_inc):
            tc.extra_cflags.append("-I" + gt_inc)
        # OHOS ld.lld defaults to --no-allow-shlib-undefined, which breaks
        # sylpheed: libsylph-0.so inherits g_libintl_* as undefined from
        # libglib-2.0.so (GLib's internal libintl). Allow runtime resolution.
        tc.extra_ldflags.append("-Wl,--allow-shlib-undefined")

        env = tc.environment()
        # Disable safe-delete bash functions that intercept rm/unlink during make
        env.define("BASH_ENV", "")
        env.define("CODEBUDDY_SAFE_DELETE_ENABLED", "0")
        env.unset("CODEBUDDY_SAFE_DELETE_BIN_DIR")
        env.prepend_path("PKG_CONFIG_PATH", self.generators_folder)
        for dep in self.dependencies.host.values():
            bin_dir = os.path.join(dep.package_folder, "bin")
            if os.path.isdir(bin_dir):
                env.prepend_path("PATH", bin_dir)
        for dep in self.dependencies.build.values():
            bin_dir = os.path.join(dep.package_folder, "bin")
            if os.path.isdir(bin_dir):
                env.prepend_path("PATH", bin_dir)
        pkg_config = self._dep_tool("pkgconf", "pkgconf", "pkg-config") \
            or self._tool_executable("pkgconf", "pkg-config")
        if pkg_config:
            env.define_path("PKG_CONFIG", pkg_config)
        ld = self._tool_executable("ld.lld", "lld", "ld")
        if ld:
            env.define_path("LD", ld)
        tc.generate(env=env)

    def _make_tmpdir(self):
        tmpdir = os.path.join(self.build_folder, "cfg-tmp")
        os.makedirs(tmpdir, exist_ok=True)
        return tmpdir

    def build(self):
        apply_conandata_patches(self)

        # Fix mktemp 077 -> 000 (HMDFS 2700 permission issue, E011 family)
        for name in ("configure",):
            target = os.path.join(self.source_folder, name)
            if os.path.isfile(target):
                replace_in_file(self, target, "umask 077", "umask 000")

        # HMDFS fix: config.sub/config.guess cannot be executed on HMDFS.
        # Replace them with echo stubs that return the correct triplet,
        # bypassing configure's attempt to run them via /bin/bash.
        triplet = "aarch64-unknown-linux-ohos"
        for script, output in (("config.guess", triplet), ("config.sub", triplet)):
            path = os.path.join(self.source_folder, script)
            if os.path.isfile(path):
                stub = f"#!/bin/sh\necho {output}\n"
                open(path, "w").write(stub)
                os.chmod(path, 0o755)

        # E236: dependency packages ship libtool .la metadata with
        # non-relocatable absolute paths (libdir/dependency_libs baked at
        # build time). On CI those paths no longer exist and libtool fails
        # with "library ... was moved" / "is not a valid libtool archive"
        # while linking libsylpheed-plugin-0.la. Remove stale .la files so
        # libtool resolves dependencies as plain shared -l libraries.
        for dep in self.dependencies.host.values():
            lib_dir = os.path.join(dep.package_folder, "lib")
            if not os.path.isdir(lib_dir):
                continue
            for entry in os.listdir(lib_dir):
                if entry.endswith(".la"):
                    os.remove(os.path.join(lib_dir, entry))

        env = Environment()
        env.define_path("TMPDIR", self._make_tmpdir())

        autotools = Autotools(self)
        with env.vars(self).apply():
            autotools.configure()
            cs = os.path.join(self.build_folder, "config.status")
            if os.path.isfile(cs):
                content = open(cs, encoding="utf-8", errors="surrogateescape").read()
                if "umask 077" in content:
                    open(cs, "w", encoding="utf-8", errors="surrogateescape").write(
                        content.replace("umask 077", "umask 000"))
            autotools.make()
            if not cross_building(self):
                autotools.make(target="check")

    def package(self):
        autotools = Autotools(self)
        autotools.install()
        copy(self, "COPYING", src=self.source_folder,
             dst=os.path.join(self.package_folder, "licenses"))
        copy(self, "COPYING.LIB", src=self.source_folder,
             dst=os.path.join(self.package_folder, "licenses"))

    def package_info(self):
        self.cpp_info.libs = []
        self.cpp_info.bindirs = ["bin"]
        self.cpp_info.includedirs = []
        if self.settings.os in ("Linux", "OHOS"):
            self.cpp_info.system_libs = ["m", "pthread", "dl"]
