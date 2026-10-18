#!/usr/bin/env python3
"""Conan recipe for xcb-util 0.4.1.

The X.Org convenience library merged from the former atom, aux and event
helpers (single libxcb-util since 0.3.8): xcb_aux_* window/GC parameter
packers, the predefined-atom name builders (xcb_atom_*) and the event
label lookup tables (xcb_event_*). Pure autotools; the x.org release
tarball ships pre-generated configure + Makefile.in, so no automake or
libtool step is needed (the OHOS device has neither installed).

Upstream dependency surface is deliberately minimal: the only external
header is <xcb/xcb.h> and the only linked library is libxcb. Unlike
xcb-util-wm, xorgproto is NOT required — no X11/ header is referenced
anywhere in src/. XCB_UTIL_COMMON does run
`pkg-config --variable=xcbproto_version xcb`, which Conan's minimal
generated xcb.pc does not carry; the value is patched in from the real
xcb.pc shipped by the libxcb package (same fix as xcb-util-wm/0.4.2).
"""

import os
import re

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.files import copy, get, load, replace_in_file, save
from conan.tools.gnu import Autotools, AutotoolsToolchain
from conan.tools.layout import basic_layout


class XcbUtilConan(ConanFile):
    name = "xcb-util"
    version = "0.4.1"
    description = "XCB convenience library: aux helpers, atom cache and event labels"
    license = "MIT"
    homepage = "https://gitlab.freedesktop.org/xorg/lib/libxcb-util"
    url = "https://gitlab.freedesktop.org/xorg/lib/libxcb-util"
    package_type = "library"
    settings = "os", "arch", "compiler", "build_type"
    generators = "PkgConfigDeps"
    options = {
        "shared": [True, False],
        "fPIC": [True, False],
    }
    default_options = {
        "shared": True,
        "fPIC": True,
    }

    def configure(self):
        if self.options.shared:
            self.options.rm_safe("fPIC")

    def validate(self):
        if str(self.settings.os) not in ("Linux", "OHOS"):
            raise ConanInvalidConfiguration(
                f"xcb-util supports Linux and OHOS, not {self.settings.os}"
            )

    def requirements(self):
        self.requires("libxcb/1.17.0")

    def layout(self):
        basic_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"][str(self.version)], strip_root=True)

    def generate(self):
        tc = AutotoolsToolchain(self)
        tc.configure_args.append("--build=aarch64-unknown-linux-gnu")
        tc.configure_args.append("--host=aarch64-unknown-linux-gnu")
        if self.options.shared:
            tc.configure_args.append("--enable-shared")
            tc.configure_args.append("--disable-static")
        else:
            tc.configure_args.append("--disable-shared")
            tc.configure_args.append("--enable-static")
        # Explicit cross-library link closure: libxcb-util.so resolves libxcb
        # symbols, so give the linker the dependency lib directory directly
        # instead of relying on implicit DT_NEEDED closure search (lld on
        # OHOS does not fall back to it the way GNU ld does). Injected here,
        # before tc.generate() snapshots the toolchain environment.
        dep_lib = os.path.join(self.dependencies["libxcb"].package_folder, "lib")
        if os.path.isfile(os.path.join(dep_lib, "libxcb.so")):
            tc.extra_ldflags.append(f"-L{dep_lib}")
            tc.extra_ldflags.append(f"-Wl,-rpath-link,{dep_lib}")
        tc.generate()

        # XCB_UTIL_COMMON queries `pkg-config --variable=xcbproto_version xcb`,
        # which Conan's minimal generated xcb.pc does not carry. Patch it in
        # from the real xcb.pc shipped by the libxcb package.
        conan_pc_dir = os.path.join(self.build_folder, "conan")
        xcb_pc = os.path.join(conan_pc_dir, "xcb.pc")
        if os.path.isfile(xcb_pc):
            existing = load(self, xcb_pc)
            if "xcbproto_version" not in existing:
                xcb_pkg = self.dependencies["libxcb"].package_folder
                orig_xcb_pc = os.path.join(xcb_pkg, "lib", "pkgconfig", "xcb.pc")
                if os.path.isfile(orig_xcb_pc):
                    for line in load(self, orig_xcb_pc).splitlines():
                        if line.startswith("xcbproto_version="):
                            lines = existing.splitlines()
                            insert_idx = 0
                            for i, ln in enumerate(lines):
                                if ln.startswith("prefix=") or ln.startswith("exec_prefix="):
                                    insert_idx = i + 1
                            lines.insert(insert_idx, line)
                            save(self, xcb_pc, "\n".join(lines) + "\n")
                            break

    def _fix_dependency_la_files(self):
        """Fix stale build-time paths in dependency .la files."""
        dep = self.dependencies["libxcb"]
        dep_lib = os.path.join(dep.package_folder, "lib")
        if not os.path.isdir(dep_lib):
            return
        for entry in os.listdir(dep_lib):
            if not entry.endswith(".la"):
                continue
            la_path = os.path.join(dep_lib, entry)
            with open(la_path, "r", encoding="utf-8") as handle:
                content = handle.read()
            content = re.sub(
                r"^libdir='.*'$", f"libdir='{dep_lib}'", content, flags=re.MULTILINE
            )

            def _replace_la(match):
                lib_name = os.path.basename(match.group(1))[3:-3]
                return f" -l{lib_name}"

            content = re.sub(r"(\s+/[^ ]+\.la\b)", _replace_la, content)
            with open(la_path, "w", encoding="utf-8") as handle:
                handle.write(content)

    def build(self):
        self._fix_dependency_la_files()
        configure_path = os.path.join(self.source_folder, "configure")
        if str(self.settings.os) == "OHOS" and os.path.exists(configure_path):
            # HMDFS: config.status' `umask 077` creates directories even the
            # owner cannot write; /system/bin/sh cannot run these scripts.
            replace_in_file(self, configure_path, "umask 077", "umask 022", strict=False)
            for pattern in ("#! /bin/sh", "#!/bin/sh", "#! /bin/bash", "#!/bin/bash"):
                replace_in_file(
                    self,
                    configure_path,
                    pattern,
                    "#!/data/service/hnp/bin/bash",
                    strict=False,
                )
        autotools = Autotools(self)
        autotools.configure()
        autotools.make()
        # The release ships no test programs (no tests/ dir, no TESTS in
        # src/Makefile.am), so this is a no-op target; it is kept so the
        # build log carries a trace of the upstream check entry point.
        autotools.make(target="check")

    def package(self):
        autotools = Autotools(self)
        autotools.install()
        self._patch_libtool_libdir()
        copy(
            self,
            "COPYING",
            src=self.source_folder,
            dst=os.path.join(self.package_folder, "licenses"),
            keep_path=False,
        )

    def _patch_libtool_libdir(self):
        lib_dir = os.path.join(self.package_folder, "lib")
        if not os.path.isdir(lib_dir):
            return
        for entry in os.listdir(lib_dir):
            if not entry.endswith(".la"):
                continue
            la_path = os.path.join(lib_dir, entry)
            with open(la_path, "r", encoding="utf-8") as handle:
                content = handle.read()
            new_content = re.sub(
                r"^libdir='.*'$", f"libdir='{lib_dir}'", content, flags=re.MULTILINE
            )
            if new_content != content:
                with open(la_path, "w", encoding="utf-8") as handle:
                    handle.write(new_content)

    def package_info(self):
        # Upstream installs ONE library (libxcb-util.so.1, version-info 1:0:0)
        # plus four pkg-config files that all point at it (xcb-util.pc and the
        # historical xcb-aux/xcb-atom/xcb-event.pc aliases), so a single
        # component models the package and the aliases are declared so any of
        # the four pkg-config names resolves.
        self.cpp_info.libs = ["xcb-util"]
        self.cpp_info.set_property("pkg_config_name", "xcb-util")
        self.cpp_info.set_property("pkg_config_aliases", ["xcb-aux", "xcb-atom", "xcb-event"])
        self.cpp_info.set_property("cmake_file_name", "xcb-util")
        self.cpp_info.set_property("cmake_target_name", "xcb-util::xcb-util")
