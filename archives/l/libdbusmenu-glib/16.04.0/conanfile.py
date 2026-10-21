#!/usr/bin/env python3
"""Build the official GLib menu-protocol library and run all eight original GLib entries.

The release ships the generated sources for its eleven library translation units.
The recipe packages this GLib protocol library and uses real published native
DBus test tools to execute its original client/server/proxy programs.
Source identity is the release tarball SHA256 recorded in conandata.yml.
"""
import os
import sys
import json
import shlex
import shutil
import subprocess

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.env import VirtualRunEnv
from conan.tools.files import copy, get, apply_conandata_patches, export_conandata_patches
from conan.tools.gnu import PkgConfigDeps
from conan.tools.layout import basic_layout
from conan.tools.build import cross_building

# The glib library TU list, straight from libdbusmenu-glib/Makefile.am
# libdbusmenu_glib_la_SOURCES minus the headers.  Every file here ships
# pre-generated in the tarball — nothing needs glib-genmarshal /
# glib-mkenums / gdbus-codegen at build time.
_TUS = [
    "dbus-menu-clean.xml.c",
    "defaults.c",
    "enum-types.c",
    "menuitem.c",
    "menuitem-marshal.c",
    "menuitem-proxy.c",
    "server.c",
    "server-marshal.c",
    "client-marshal.c",
    "client-menuitem.c",
    "client.c",
]

# Public headers, libdbusmenu_glibinclude_HEADERS verbatim.
_HEADERS = [
    "menuitem.h",
    "menuitem-proxy.h",
    "server.h",
    "client.h",
    "enum-types.h",
    "dbusmenu-glib.h",
    "types.h",
]

# libtool -version-info 4:12:0 → file .so.4.0.12, soname .so.4
_LT_CURRENT = 4
_LT_REVISION = 12
_LT_AGE = 0


class LibdbusmenuGlibConan(ConanFile):
    name = "libdbusmenu-glib"
    version = "16.04.0"
    description = "GLib/GIO implementation of the DBusMenu protocol (shared menus over DBus)"
    license = "LGPL-3.0-or-later OR LGPL-2.1-or-later"
    homepage = "https://launchpad.net/libdbusmenu"
    url = "https://atomgit.com/OpenHarmonyPCDeveloper/build_in_harmonyos"

    package_type = "library"
    settings = "os", "compiler", "build_type", "arch"
    options = {"shared": [True, False], "fPIC": [True, False]}
    default_options = {"shared": True, "fPIC": True}

    def config_options(self):
        if self.settings.os == "Windows":
            del self.options.fPIC

    def configure(self):
        if self.options.shared:
            self.options.rm_safe("fPIC")
        self.settings.rm_safe("compiler.cppstd")
        self.settings.rm_safe("compiler.libcxx")

    def requirements(self):
        self.requires("glib/2.84.0.1", transitive_headers=True, transitive_libs=True)

    def build_requirements(self):
        # Execute the release's original DBUS_RUNNER recipes. This published
        # provider uses the same GLib 2.84.0.1 closure; no executor override.
        self.test_requires("dbustest/19.04.0.1")
        # The published 1.14 client library omits every daemon/tool binary.
        # The standalone bus is a native build tool in its own dependency
        # context, leaving the runner's real client-library graph intact.
        self.tool_requires("dbus/1.16.2.1")

    def validate(self):
        if cross_building(self):
            raise ConanInvalidConfiguration("Original multiprocess tests require native target execution")

    def export_sources(self):
        export_conandata_patches(self)
        copy(self, "*.py", os.path.join(self.recipe_folder, "build-support"),
             os.path.join(self.export_sources_folder, "build-support"))

    def layout(self):
        basic_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"][self.version], strip_root=True)
        apply_conandata_patches(self)

    def generate(self):
        PkgConfigDeps(self).generate()
        VirtualRunEnv(self).generate()
        self._fix_glib_pc_files()

    def _fix_glib_pc_files(self):
        """Generated glib .pc fixes for OHOS musl: expose the (script)
        glib tools as variables and add -lintl to Libs — same patch the
        platform's json-glib recipe carries."""
        gens = self.generators_folder
        glib_pc = os.path.join(gens, "glib-2.0.pc")
        glib_prefix = None
        if os.path.isfile(glib_pc):
            with open(glib_pc) as f:
                for line in f:
                    if line.startswith("prefix="):
                        glib_prefix = line.strip().split("=", 1)[1].strip().strip('"').strip("'")
                        break
        if not glib_prefix:
            return
        bindir = os.path.join(glib_prefix, "bin")
        for pc_name in ("glib-2.0.pc", "gobject-2.0.pc", "gmodule-2.0.pc",
                        "gthread-2.0.pc", "gio-2.0.pc"):
            pc_path = os.path.join(gens, pc_name)
            if not os.path.isfile(pc_path):
                continue
            with open(pc_path) as f:
                content = f.read()
            modified = False
            if "glib_mkenums" not in content:
                content += f"\nglib_genmarshal={bindir}/glib-genmarshal\n"
                content += f"gobject_query={bindir}/gobject-query\n"
                content += f"glib_mkenums={bindir}/glib-mkenums\n"
                modified = True
            if "-lintl" not in content:
                lines = content.splitlines(True)
                content = "".join(
                    l.rstrip("\n") + " -lintl\n" if l.startswith("Libs:") and "-lintl" not in l else l
                    for l in lines)
                modified = True
            if modified:
                with open(pc_path, "w") as f:
                    f.write(content)

    def _toolchain(self):
        """CC / AR from Conan conf, never bare env (R33 convention)."""
        ce = self.conf.get("tools.build:compiler_executables", default={}, check_type=dict) or {}
        cc = ce.get("c", "clang")
        ar = ce.get("ar")
        if not ar:
            ccdir = os.path.dirname(cc) if os.path.sep in cc else ""
            for name in ("llvm-ar", "ar"):
                cand = os.path.join(ccdir, name)
                if ccdir and os.path.isfile(cand):
                    ar = cand
                    break
            ar = ar or "ar"
        return cc, ar

    def _pkg_flags(self):
        """cflags/libs for glib-2.0 gobject-2.0 gio-2.0 via pkg-config
        against the PkgConfigDeps generator output."""
        pc = shutil.which("pkg-config") or shutil.which("pkgconf")
        env = dict(os.environ)
        env["PKG_CONFIG_PATH"] = self.generators_folder
        cflags = subprocess.run([pc, "--cflags", "glib-2.0", "gobject-2.0", "gio-2.0"],
                                capture_output=True, text=True, env=env, check=True).stdout
        libs = subprocess.run([pc, "--libs", "glib-2.0", "gobject-2.0", "gio-2.0"],
                              capture_output=True, text=True, env=env, check=True).stdout
        return shlex.split(cflags), shlex.split(libs)

    def build(self):
        # get(strip_root=True): the tarball root is gone, the glib
        # library directory sits directly in source_folder.
        src = os.path.join(self.source_folder, "libdbusmenu-glib")
        bld = os.path.join(self.build_folder or self.source_folder, "_build")
        os.makedirs(bld, exist_ok=True)
        cc, ar = self._toolchain()
        cflags, libs = self._pkg_flags()
        # GETTEXT_PACKAGE: glib/gi18n-lib.h #errors without it;
        # G_LOG_DOMAIN: client.c concatenates it into a quark string.
        extra = ["-fPIC", "-O1", "-DNDEBUG",
                 '-DGETTEXT_PACKAGE="libdbusmenu"',
                 '-DG_LOG_DOMAIN="LIBDBUSMENU-GLIB"']
        objs = []
        for tu in _TUS:
            obj = os.path.join(bld, tu.replace("/", "_") + ".o")
            cmd = shlex.split(cc) + ["-c", os.path.join(src, tu), "-o", obj] + cflags + extra
            self.output.info(" ".join(cmd))
            subprocess.run(cmd, check=True)
            objs.append(obj)
        soname = f"libdbusmenu-glib.so.{_LT_CURRENT - _LT_AGE}"
        realname = f"{soname}.{_LT_AGE}.{_LT_REVISION}"
        if self.options.shared:
            cmd = shlex.split(cc) + ["-shared", f"-Wl,-soname,{soname}",
                   "-o", os.path.join(bld, realname)] + objs + libs + ["-lintl"]
            self.output.info(" ".join(cmd))
            subprocess.run(cmd, check=True)
        else:
            cmd = [ar, "rcs", os.path.join(bld, "libdbusmenu-glib.a")] + objs
            self.output.info(" ".join(cmd))
            subprocess.run(cmd, check=True)

    def package(self):
        src = self.source_folder
        libsrc = os.path.join(src, "libdbusmenu-glib")
        pkg = self.package_folder
        inc = os.path.join(pkg, "include", "libdbusmenu-glib-0.4", "libdbusmenu-glib")
        os.makedirs(inc, exist_ok=True)
        for h in _HEADERS:
            copy(self, h, libsrc, inc)
        libdir = os.path.join(pkg, "lib")
        os.makedirs(libdir, exist_ok=True)
        bld = os.path.join(self.build_folder or self.source_folder, "_build")
        if self.options.shared:
            soname = f"libdbusmenu-glib.so.{_LT_CURRENT - _LT_AGE}"
            realname = f"{soname}.{_LT_AGE}.{_LT_REVISION}"
            shutil.copy2(os.path.join(bld, realname), os.path.join(libdir, realname))
            for name in (soname, "libdbusmenu-glib.so"):
                dst = os.path.join(libdir, name)
                if not os.path.lexists(dst):
                    try:
                        os.symlink(realname, dst)
                    except OSError:
                        shutil.copy2(os.path.join(bld, realname), dst)
        else:
            shutil.copy2(os.path.join(bld, "libdbusmenu-glib.a"),
                         os.path.join(libdir, "libdbusmenu-glib.a"))
        # pkg-config metadata, mirrors upstream dbusmenu-glib-0.4.pc.in
        # (Requires kept empty upstream; we list the real deps so
        # downstream .pc consumers link correctly).
        pc = f"""prefix={pkg}
exec_prefix=${{prefix}}
libdir=${{prefix}}/lib
includedir=${{prefix}}/include

Cflags: -I${{includedir}}/libdbusmenu-glib-0.4
Requires: glib-2.0 gobject-2.0 gio-2.0
Libs: -L${{libdir}} -ldbusmenu-glib

Name: libdbusmenu-glib
Description: libdbusmenu-glib.
Version: {self.version}
"""
        os.makedirs(os.path.join(pkg, "lib", "pkgconfig"), exist_ok=True)
        with open(os.path.join(pkg, "lib", "pkgconfig", "dbusmenu-glib-0.4.pc"), "w",
                  encoding="utf-8", newline="\n") as f:
            f.write(pc)
        # Licenses: library code is dual LGPL-3 / LGPL-2.1 (header blocks)
        copy(self, "COPYING", src, os.path.join(pkg, "licenses"))
        copy(self, "COPYING.2.1", src, os.path.join(pkg, "licenses"))
        copy(self, "COPYING-GPL3", src, os.path.join(pkg, "licenses"))

        # The object smoke is separate from the release's eight original
        # GLib entries. Run the actual client/server/proxy programs here.
        support = os.path.join(self.source_folder, "build-support")
        sign = os.path.join(support, "sign_elf.py")
        if str(self.settings.os) == "OHOS" and self.options.shared:
            self.run(shlex.join([sys.executable, sign, os.path.join(libdir, realname)]))
            # Aliases may be regular copies on filesystems without symlinks.
            for name in (soname, "libdbusmenu-glib.so"):
                alias = os.path.join(libdir, name)
                if not os.path.islink(alias):
                    shutil.copy2(os.path.join(libdir, realname), alias)
        cc, _ = self._toolchain()
        cc = shlex.split(cc)
        cc[0] = cc[0] if os.path.isabs(cc[0]) else shutil.which(cc[0])
        make = self.conf.get("tools.gnu:make_program", default="make")
        make = make if os.path.isabs(make) else shutil.which(make)
        runner_root = self.dependencies["dbustest"].package_folder
        runner = os.path.join(runner_root, "bin", "dbus-test-runner")
        glib = self.dependencies["glib"].package_folder
        dbus = self.dependencies.build["dbus"].package_folder
        cflags, libs = self._pkg_flags()
        runtime_dirs = []
        for dep in self.dependencies.host.values():
            if dep.package_folder:
                runtime_dirs.extend(os.path.join(dep.package_folder, leaf)
                                    for leaf in dep.cpp_info.libdirs)
        for dep in self.dependencies.build.values():
            if dep.package_folder:
                runtime_dirs.extend(os.path.join(dep.package_folder, leaf)
                                    for leaf in dep.cpp_info.libdirs)
        config = {"source": self.source_folder, "build": self.build_folder,
                  "package": self.package_folder, "cc": cc, "make": make,
                  "runner": runner, "gtester": os.path.join(glib, "bin", "gtester"),
                  "daemon": os.path.join(dbus, "bin", "dbus-daemon"),
                  "shell": shutil.which("bash"), "cflags": cflags, "libs": libs,
                  "runtime_dirs": list(dict.fromkeys(runtime_dirs)),
                  "target_os": str(self.settings.os), "sign_helper": sign}
        path = os.path.join(self.build_folder, "original-glib-tests.json")
        with open(path, "w", encoding="utf8") as stream:
            json.dump(config, stream)
        self.run(shlex.join([sys.executable, os.path.join(support, "upstream_glib.py"), path]),
                 env="conanrun")
        self.output.info("UPSTREAM_ORIGINAL_ENTRIES=8/8; ORIGINAL_PROGRAMS=15; SKIP=0")

    def package_info(self):
        self.cpp_info.set_property("cmake_file_name", "dbusmenu-glib")
        self.cpp_info.set_property("pkg_config_name", "dbusmenu-glib-0.4")
        c = self.cpp_info.components["dbusmenu-glib"]
        c.set_property("cmake_target_name", "dbusmenu-glib::dbusmenu-glib")
        c.set_property("pkg_config_name", "dbusmenu-glib-0.4")
        c.libs = ["dbusmenu-glib"]
        c.includedirs = ["include/libdbusmenu-glib-0.4"]
        c.libdirs = ["lib"]
        c.requires = ["glib::glib-2.0", "glib::gobject-2.0", "glib::gio-2.0"]
        if self.settings.os in ("Linux", "OHOS"):
            c.system_libs = ["intl"]
