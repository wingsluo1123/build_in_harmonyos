#!/usr/bin/env python3
"""Conan recipe for libxfce4util 4.20.0 (Autotools).

Pure autotools release tarball (no glib host tools needed: no gdbus-codegen,
no glib-mkenums, no glib-genmarshal).  Ships libxfce4util.so.7 (verinfo
7:0:0), the libxfce4util-1.0 pkg-config module, headers under
include/xfce4/libxfce4util and the xfce4-kiosk-query CLI (upstream installs
it via sbin_PROGRAMS; Conan's AutotoolsToolchain flattens sbindir to
${prefix}/bin, so inside the conan package it lives in bin/).
"""

import os
import shutil
import subprocess

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.files import (
    apply_conandata_patches,
    copy,
    export_conandata_patches,
    get,
    replace_in_file,
    rm,
)
from conan.tools.gnu import Autotools, AutotoolsToolchain, PkgConfigDeps
from conan.tools.layout import basic_layout


class Libxfce4utilConan(ConanFile):
    name = "libxfce4util"
    version = "4.20.0"
    description = "Xfce base utility library (kiosk mode, INI-style config, resource pools)"
    license = "LGPL-2.0-or-later"
    homepage = "https://docs.xfce.org/xfce/libxfce4util/start"
    url = "https://gitcode.com/OpenHarmonyPCDeveloper/build_in_harmonyos"

    package_type = "library"

    settings = "os", "arch", "compiler", "build_type"
    options = {"shared": [True, False], "fPIC": [True, False]}
    default_options = {"shared": True, "fPIC": True}

    def export_sources(self):
        export_conandata_patches(self)

    def validate(self):
        if self.settings.os not in ("Linux", "OHOS"):
            raise ConanInvalidConfiguration(
                "os={} not supported; this recipe targets OHOS/Linux".format(
                    self.settings.os
                )
            )

    def config_options(self):
        if self.settings.os == "Windows":
            self.options.rm_safe("fPIC")

    def configure(self):
        if self.options.shared:
            self.options.rm_safe("fPIC")

    def requirements(self):
        # configure.ac: glib_min_version >= 2.72.0, consumed as XDT_CHECK_PACKAGE
        # on glib-2.0 / gobject-2.0 / gio-2.0.  Pinned to glib/2.84.0.1, the most
        # widely deployed published baseline in this repository (sibling-recipe
        # convention; requires and test_package must stay in sync).
        self.requires(
            "glib/2.84.0.1",
            transitive_headers=True,
            transitive_libs=True,
        )

    def layout(self):
        basic_layout(self, src_folder=".")

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def generate(self):
        # XDT_CHECK_PACKAGE discovers glib-2.0/gobject-2.0/gio-2.0 through
        # pkg-config: materialize the dependency .pc files, then point
        # PKG_CONFIG_PATH at them on the configure invocation.
        PkgConfigDeps(self).generate()

        tc = AutotoolsToolchain(self)
        if self.settings.os == "OHOS":
            source_map = "{}=.".format(self.source_folder)
            tc.extra_cflags.extend(
                [
                    "-ffile-prefix-map={}".format(source_map),
                    "-fdebug-prefix-map={}".format(source_map),
                    "-fmacro-prefix-map={}".format(source_map),
                ]
            )
            # Explicit link closure (build-chain-pitfalls "共享库链接闭包"):
            # libxfce4util itself gets GLIB_LIBS from pkg-config, but the
            # xfce4-kiosk-query tool only links the libtool .la, so make the
            # dependency libdirs explicit on every link line instead of
            # relying on lld's implicit DT_NEEDED closure search.
            # (The g_libintl_* closure is handled by source patch 0004, which
            # no-ops the i18n calls under --disable-nls — injecting the glib
            # proxy libintl DSO onto the link line here would break every
            # configure runtime conftest with "cannot run C compiled
            # programs" and leave consumers with an unresolvable NEEDED.)
            for libdir in self._glib_libdirs():
                tc.extra_ldflags.append("-L{}".format(libdir))

        tc.configure_args.extend(
            [
                # NLS off (E015/E027): AM_GNU_GETTEXT([external]) would drag in
                # a host libintl; OHOS has no published gettext runtime.
                "--disable-nls",
                "--disable-gtk-doc",
                "--enable-introspection=no",
                "--enable-vala=no",
                "--disable-silent-rules",
            ]
        )
        if self.options.shared:
            tc.configure_args.extend(["--enable-shared", "--disable-static"])
        else:
            tc.configure_args.extend(["--enable-static", "--disable-shared"])
        # PKG_CONFIG_PATH must be carried as a configure argument: the conan
        # build env does not export it automatically for AutotoolsToolchain.
        tc.configure_args.append(
            "PKG_CONFIG_PATH={}".format(self.generators_folder)
        )
        tc.generate()

    def _glib_libdirs(self):
        """Absolute libdirs of the published glib package (top level plus all
        components, deduplicated, existing directories only)."""
        dep = self.dependencies["glib"]
        package_folder = getattr(dep, "package_folder", None) or ""

        def _abs(path):
            return path if os.path.isabs(path) or not package_folder else os.path.join(package_folder, path)

        dirs = []
        for libdir in list(dep.cpp_info.libdirs):
            candidate = _abs(libdir)
            if os.path.isdir(candidate) and candidate not in dirs:
                dirs.append(candidate)
        for component in getattr(dep.cpp_info, "components", {}).values():
            for libdir in list(component.libdirs):
                candidate = _abs(libdir)
                if os.path.isdir(candidate) and candidate not in dirs:
                    dirs.append(candidate)
        return dirs

    def _make_args(self):
        if self.settings.os == "OHOS":
            # Same precedent as libgcrypt 1.12.2 on this device class: make
            # ignores SHELL from the environment, pass it as an override.
            return ["SHELL=/system/bin/sh"]
        return []

    def build(self):
        apply_conandata_patches(self)
        autotools = Autotools(self)
        autotools.configure()
        if self.settings.os == "OHOS":
            # Same libtool fix as libgcrypt 1.12.2: stop libtool from
            # hardcoding -rpath into installed artifacts (breaks OHOS
            # codesign; consumers resolve via LD_LIBRARY_PATH).  The libtool
            # 2.4.7 script stores the spec backslash-escaped; accept both
            # forms and degrade to a warning — the package-level
            # patchelf --remove-rpath pass is the real guarantee.
            libtool = os.path.join(self.build_folder, "libtool")
            if os.path.isfile(libtool):
                for pattern in (
                    'hardcode_libdir_flag_spec="\\$wl-rpath \\$wl\\$libdir"',
                    'hardcode_libdir_flag_spec="$wl-rpath $wl$libdir"',
                ):
                    with open(libtool, "r", encoding="utf-8", errors="replace") as handle:
                        text = handle.read()
                    if pattern in text:
                        replace_in_file(self, libtool, pattern, 'hardcode_libdir_flag_spec=""')
                        break
                else:
                    self.output.warning(
                        "libtool hardcode_libdir_flag_spec pattern not found; "
                        "relying on post-package patchelf --remove-rpath"
                    )
        autotools.make(args=self._make_args())
        # Upstream ships no test suite (see test_package/MANIFEST.yml and
        # notes.md: no tests/ directory, no TESTS in any Makefile.in, no
        # meson test()).  "make check" is kept in the build so the CI log
        # carries the verifiable no-op evidence (check-recursive with no
        # TESTS -> "Nothing to be done").
        autotools.make(args=["check"] + self._make_args())

    def package(self):
        autotools = Autotools(self)
        autotools.install(args=self._make_args())
        copy(
            self,
            "COPYING*",
            src=self.source_folder,
            dst=os.path.join(self.package_folder, "licenses"),
        )
        rm(self, "*.la", os.path.join(self.package_folder, "lib"))
        if self.settings.os == "OHOS":
            self._postprocess_ohos_elfs()

    def _locate_tool(self, name):
        found = shutil.which(name)
        if found:
            return found
        # Device HNP toolchain directory (same location as the published
        # libgcrypt 1.12.2 recipe uses on the CI workers).
        fallback = os.path.join("/data/service/hnp/bin", name)
        if os.path.isfile(fallback):
            return fallback
        raise RuntimeError("Required OHOS {} tool is missing".format(name))

    def _postprocess_ohos_elfs(self):
        tools = {
            "patchelf": self._locate_tool("patchelf"),
            "objcopy": self._locate_tool("llvm-objcopy"),
            "signer": self._locate_tool("binary-sign-tool"),
        }
        for root, _, files in os.walk(self.package_folder):
            for filename in files:
                path = os.path.join(root, filename)
                with open(path, "rb") as stream:
                    if stream.read(4) != b"\x7fELF":
                        continue
                subprocess.run(
                    [tools["patchelf"], "--remove-rpath", path], check=True
                )
                subprocess.run(
                    [tools["objcopy"], "--remove-section", ".codesign", path],
                    check=False,
                    stdout=subprocess.DEVNULL,
                    stderr=subprocess.DEVNULL,
                )
                subprocess.run(
                    [
                        tools["signer"],
                        "sign",
                        "-inFile",
                        path,
                        "-outFile",
                        path,
                        "-selfSign",
                        "1",
                    ],
                    check=True,
                )

    def package_info(self):
        self.cpp_info.set_property("cmake_file_name", "libxfce4util")
        self.cpp_info.set_property("cmake_target_name", "libxfce4util::libxfce4util")
        # Canonical upstream pkg-config module name (XDT_CHECK_PACKAGE on
        # libxfce4util-1.0 by downstream xfconf et al).
        self.cpp_info.set_property("pkg_config_name", "libxfce4util-1.0")
        # Upstream installs headers under include/xfce4/libxfce4util and the
        # .pc carries Cflags: -I${includedir}/xfce4.
        self.cpp_info.includedirs = ["include/xfce4"]
        self.cpp_info.libdirs = ["lib"]
        self.cpp_info.libs = ["xfce4util"]
        # xfce4-kiosk-query ships inside the package.  Upstream declares it
        # sbin_PROGRAMS, but Conan's AutotoolsToolchain passes
        # --sbindir=${prefix}/bin (see knowledge E2167/E545: the toolchain
        # injects all GNU dir flags with bin-flattened defaults), so the
        # installed location inside this conan package is bin/.
        self.cpp_info.bindirs = ["bin"]
        self.cpp_info.requires = [
            "glib::glib-2.0",
            "glib::gobject-2.0",
            "glib::gio-2.0",
        ]
