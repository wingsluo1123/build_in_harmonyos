#!/usr/bin/env python3
"""Conan recipe for kywc 1.3.1 — Meson (C11).

kywc is the Kylin Wayland compositor (kylin-wayland-compositor). Only the
libkywc/ subtree is packaged: it is the client library that ukui-quick's
window-thumbnail module consumes (`pkg_check_modules(... kywc REQUIRED)`,
`#include <libkywc.h>`, `kywc_context_create()`). The compositor half needs
wlroots 0.17 and the full desktop stack (xkbcommon, libdrm, libinput, pixman,
json-c, libsystemd, cairo, pango, librsvg, libjpeg, libudev, libunwind, xcb),
none of which exists in the OHOS registry, and no OHOS consumer needs it.

Local patches (patches/):
  0001 meson: add the libkywc_only / wayland_scanner_path /
       kywc_install_rpath options. With libkywc_only=true the top-level
       meson.build enters only libkywc/ and skips the wlroots/compositor
       dependency block. The release tag 1.3.1 left the Meson project version
       at 1.3.0; the patch aligns it so that kywc.pc reports 1.3.1.
  0002 libkywc: generate the four kywc client protocol files locally (the
       compositor build generates them in protocols/, which the libkywc-only
       build never enters) and drop the versioned shared library name (HMDFS
       rejects the soname symlinks the version: argument creates).

wayland-scanner: the scanner installed by the wayland package cannot be
executed on the device — its DT_NEEDED bakes the build machine's Conan cache
path for libexpat, so execve fails with EPERM. A statically linked scanner
(libc only) is compiled from the wayland 1.22.0 sources, following the
chayang precedent.

install_rpath: OHOS verifies the ELF .codesign section that the toolchain
attaches at link time, and a post-link byte edit invalidates it — dlopen then
fails with EACCES. meson's installer (depfixer) strips the build rpath added
for the absolute libwayland-client.so path, rewriting .dynstr in place. The
kywc_install_rpath option is therefore set to the wayland package's lib
directory, exactly the string depfixer would remove; old and new rpath match,
depfixer writes identical bytes, and the installed library stays identical to
the signed build artifact.

Upstream ships no test suite: a recursive search of the tree finds no
test()/benchmark() declaration in any meson.build (0 hits). `meson test -C
<build folder>` is still run in build() so the log records the authoritative
count ("No tests defined."); a non-zero exit fails the build.
"""
import os
import re
import shutil

from conan import ConanFile
from conan.errors import ConanException
from conan.tools.files import apply_conandata_patches, export_conandata_patches, get
from conan.tools.layout import basic_layout
from conan.tools.meson import Meson, MesonToolchain

# wayland release whose sources build the embedded static scanner. Kept in
# sync with the wayland requirement below.
SCANNER_WAYLAND_VERSION = "1.22.0"


class KywcConan(ConanFile):
    name = "kywc"
    version = "1.3.1"
    description = "Kylin Wayland compositor client library (libkywc)"
    license = "GPL-1.0-or-later"
    homepage = "https://gitee.com/openkylin/kylin-wayland-compositor"
    url = "https://gitcode.com/OpenHarmonyPCDeveloper/build_in_harmonyos"

    package_type = "shared-library"
    settings = "os", "compiler", "build_type", "arch"
    exports_sources = "patches/*"

    def requirements(self):
        # libkywc/meson.build: dependency('wayland-client'). Literal ref (not
        # built from SCANNER_WAYLAND_VERSION) so the CI registry check can
        # read it from the AST; keep the two in sync.
        self.requires("wayland/1.22.0")
        # wayland-client.pc declares `Requires.private: libffi`, and pkg-config
        # resolves private requirements for --cflags. libffi is only a
        # transitive dependency of wayland, so Conan would treat it as a
        # "skipped binary" and never install its .pc -> meson fails to resolve
        # wayland-client. Promote it to a direct requirement (hyprpicker /
        # chayang precedent).
        self.requires("libffi/3.4.4")

    def build_requirements(self):
        # the device has no system meson
        self.tool_requires("meson/1.11.0")

    def export_sources(self):
        export_conandata_patches(self)

    def layout(self):
        basic_layout(self)

    def source(self):
        # Gitee's edge answers the default Conan user agent with an HTML page
        # (HTTP 200, text/html) instead of the archive, so the sha256 check
        # fails; a curl-like user agent receives the real tarball.
        get(self, **self.conan_data["sources"], strip_root=True,
            headers={"User-Agent": "curl/8.5.0"})
        # wayland sources, used only to build the static wayland-scanner
        get(self, **self.conan_data["scanner_sources"],
            strip_root=True, destination="wayland-scanner-src")

    # ── generate ─────────────────────────────────────────────────────────

    def _c_compiler(self):
        """The C compiler the profile actually uses (fallback: PATH/SDK)."""
        compilers = self.conf.get("tools.build:compiler_executables",
                                  default={}, check_type=dict) or {}
        cc = compilers.get("c")
        if cc and os.path.isfile(cc):
            return cc
        return shutil.which("clang") or "/data/service/hnp/bin/clang"

    def _llvm_tool(self, name):
        """Locate an LLVM binutil next to the profile compiler, then PATH, then SDK."""
        tool_dir = os.path.dirname(self._c_compiler())
        candidate = os.path.join(tool_dir, name)
        if os.path.isfile(candidate):
            return candidate
        return shutil.which(name) or f"/data/service/hnp/bin/{name}"

    def generate(self):
        tc = MesonToolchain(self)
        # build only libkywc/ (see the recipe docstring)
        tc.project_options["libkywc_only"] = "true"
        # absolute path of the static scanner built in build(); the option is
        # handed to find_program() by the patched libkywc/meson.build
        scanner_bin = os.path.join(self.generators_folder, "wayland-scanner")
        tc.project_options["wayland_scanner_path"] = scanner_bin
        # OHOS signs ELF files at link time and the loader refuses any
        # post-link byte edit (dlopen -> EACCES). meson's installer runs
        # depfixer, which strips the build rpath it added for the absolute
        # libwayland-client.so path; that in-place .dynstr rewrite breaks the
        # .codesign section. Handing install_rpath the very same directory
        # makes depfixer write back identical bytes, so the installed library
        # stays byte-for-byte the signed build artifact.
        wayland_pkg = self.dependencies["wayland"].package_folder
        if not wayland_pkg:
            raise ConanException("kywc: wayland package folder is missing; "
                                 "cannot pin install_rpath")
        tc.project_options["kywc_install_rpath"] = os.path.join(wayland_pkg, "lib")

        # every dependency .pc (wayland-client.pc, …): the packaged prefix= is
        # "/" (meson root prefix), so -I${includedir} resolves to /include.
        # Copy each .pc with prefix/libdir/includedir rewritten to the real
        # package folder and put that copy first on PKG_CONFIG_PATH
        # (chayang / hyprpicker precedent).
        fixed_pc_dir = os.path.join(self.generators_folder, "fixed_pkgconfig")
        os.makedirs(fixed_pc_dir, exist_ok=True)
        pc_paths = []
        for dep in self.dependencies.values():
            if dep.package_folder is None:
                continue
            for pc_dir in ("lib", "share"):
                pc = os.path.join(dep.package_folder, pc_dir, "pkgconfig")
                if not os.path.isdir(pc):
                    continue
                pc_paths.append(pc)
                for pc_name in os.listdir(pc):
                    if not pc_name.endswith(".pc"):
                        continue
                    base = dep.package_folder
                    with open(os.path.join(pc, pc_name), "r",
                              encoding="utf-8", errors="replace") as f:
                        content = f.read()
                    content = re.sub(r"(?m)^prefix=.*$", f"prefix={base}", content)
                    content = re.sub(r"(?m)^exec_prefix=.*$",
                                     f"exec_prefix={base}", content)
                    content = re.sub(r"(?m)^libdir=.*$", f"libdir={base}/lib", content)
                    content = re.sub(r"(?m)^includedir=.*$",
                                     f"includedir={base}/include", content)
                    # a packaged .pc may hardcode the build machine's cache path
                    content = re.sub(r"/[^\"\s]*/p/b/[^/\s]+/p", base, content)
                    with open(os.path.join(fixed_pc_dir, pc_name), "w",
                              encoding="utf-8", newline="\n") as f:
                        f.write(content)
        tc.pkg_config_path = os.pathsep.join([fixed_pc_dir] + pc_paths)
        tc.generate()

        # OHOS sandbox: meson cannot find llvm-ar/ranlib (wayland/chayang
        # precedent), so inject them into the [binaries] section of every
        # machine file MesonToolchain generated: native builds read
        # conan_meson_native.ini, cross builds conan_meson_cross.ini.
        ar_path = self._llvm_tool("llvm-ar")
        ranlib_path = self._llvm_tool("llvm-ranlib")
        machine_files = 0
        for name in ("conan_meson_native.ini", "conan_meson_cross.ini"):
            native_file = os.path.join(self.generators_folder, name)
            if not os.path.isfile(native_file):
                continue
            machine_files += 1
            with open(native_file, "r", encoding="utf-8") as f:
                content = f.read()
            # Inject into [binaries] explicitly: a silent no-op of a string
            # replace would only resurface as "program 'llvm-ar' not found",
            # and appending when the key already exists would produce a
            # duplicate that meson rejects.
            lines = content.splitlines(keepends=True)
            bin_start = None
            bin_keys = set()
            section = None
            for i, line in enumerate(lines):
                stripped = line.strip()
                if stripped.startswith("[") and stripped.endswith("]"):
                    section = stripped
                    if section == "[binaries]":
                        bin_start = i
                    continue
                if section == "[binaries]" and "=" in stripped:
                    bin_keys.add(stripped.split("=", 1)[0].strip())
            if bin_start is None:
                raise ConanException(
                    f"kywc: [binaries] section not found in {native_file}")
            inserts = []
            if "ar" not in bin_keys:
                inserts.append(f"ar = '{ar_path}'\n")
            if "ranlib" not in bin_keys:
                inserts.append(f"ranlib = '{ranlib_path}'\n")
            if inserts:
                lines[bin_start + 1:bin_start + 1] = inserts
                with open(native_file, "w", encoding="utf-8", newline="\n") as f:
                    f.write("".join(lines))
        if not machine_files:
            raise ConanException(
                "kywc: MesonToolchain generated no machine file "
                "(conan_meson_native.ini / conan_meson_cross.ini)")

    # ── static wayland-scanner ───────────────────────────────────────────

    def _find_expat_static(self):
        """Locate a static libexpat.a for the fully static scanner link.

        The scanner is linked with `-static` so that it depends on libc only.
        Preference order: the SDK-bundled copy, then any static libexpat
        shipped by the dependencies. Fail loudly instead of degrading quietly.
        """
        candidates = [
            "/data/service/hnp/expat.org/expat_2.7.3/lib/libexpat.a",
        ]
        for dep in self.dependencies.values():
            if dep.ref.name == "expat" and dep.package_folder:
                candidates.append(os.path.join(dep.package_folder,
                                               "lib", "libexpat.a"))
        for c in candidates:
            if os.path.isfile(c):
                self.output.info(f"kywc: static expat -> {c}")
                return c
        raise ConanException(
            "kywc: no static libexpat.a found for the static wayland-scanner "
            f"link; tried: {candidates}")

    def _find_expat_include(self):
        candidates = ["/data/service/hnp/expat.org/expat_2.7.3/include"]
        for dep in self.dependencies.values():
            if dep.ref.name == "expat" and dep.package_folder:
                candidates.append(os.path.join(dep.package_folder, "include"))
        for c in candidates:
            if os.path.isdir(c):
                return c
        return None

    def _build_static_scanner(self):
        """Build a statically linked wayland-scanner from the wayland sources."""
        src = os.path.join(self.source_folder, "wayland-scanner-src")
        if not os.path.isdir(src):
            raise ConanException(
                f"kywc: wayland scanner sources missing: {src}")

        # config.h + wayland-version.h are normally produced by the wayland
        # build system; generate the minimal forms by hand.
        config_h = os.path.join(src, "config.h")
        with open(config_h, "w", encoding="utf-8", newline="\n") as f:
            f.write('#define HAVE_EXPAT 1\n'
                    '#define PACKAGE "wayland"\n'
                    f'#define VERSION "{SCANNER_WAYLAND_VERSION}"\n')

        version_in = os.path.join(src, "src", "wayland-version.h.in")
        version_h = os.path.join(src, "src", "wayland-version.h")
        major, minor, micro = (SCANNER_WAYLAND_VERSION.split(".") + ["0"])[:3]
        with open(version_in, "r", encoding="utf-8") as f:
            content = f.read()
        for key, val in [("@WAYLAND_VERSION@", SCANNER_WAYLAND_VERSION),
                         ("@WAYLAND_VERSION_MAJOR@", major),
                         ("@WAYLAND_VERSION_MINOR@", minor),
                         ("@WAYLAND_VERSION_MICRO@", micro)]:
            content = content.replace(key, val)
        with open(version_h, "w", encoding="utf-8", newline="\n") as f:
            f.write(content)

        # the DTD is embedded into wayland.dtd.h by the upstream embed.py
        dtd_h = os.path.join(src, "src", "wayland.dtd.h")
        self.run(f'python3 {src}/src/embed.py {src}/protocol/wayland.dtd '
                 f'wayland_dtd > {dtd_h}', env="conanbuild")

        scanner_bin = os.path.join(self.generators_folder, "wayland-scanner")
        cc = self._c_compiler()
        expat_inc = self._find_expat_include()
        expat_lib = self._find_expat_static()
        inc_flag = f"-I{expat_inc} " if expat_inc else ""
        self.run(
            f'{cc} -o {scanner_bin} '
            f'-include {config_h} '
            f'-I{src} -I{src}/src -I{src}/protocol '
            f'{src}/src/scanner.c {src}/src/wayland-util.c '
            f'{inc_flag}{expat_lib} '
            f'-lm -lpthread -static',
            env="conanbuild")
        self.output.info(
            f"kywc: built static wayland-scanner ({scanner_bin})")

    # ── build / package ──────────────────────────────────────────────────

    def build(self):
        # must happen before meson configure(): the wayland_scanner_path
        # option hands its absolute path to find_program()
        self._build_static_scanner()

        apply_conandata_patches(self)
        meson = Meson(self)
        meson.configure()
        meson.build()

        # Upstream has no test target; run the command anyway so the log
        # records the authoritative count ("No tests defined."). The build
        # directory is pinned with -C (repo convention), and the call is not
        # wrapped in try/except: exit code 0 is the only tolerated outcome,
        # so a broken test setup fails the build instead of silently
        # degrading to a warning.
        self.run(f'meson test -C "{self.build_folder}"', env="conanbuild")

    def package(self):
        meson = Meson(self)
        meson.install()
        # meson records prefix="/" in the generated kywc.pc (install runs with
        # --prefix=/ --destdir=<package folder>); rewrite it to a package
        # relative prefix so the .pc stays relocatable.
        pc = os.path.join(self.package_folder, "lib", "pkgconfig", "kywc.pc")
        if not os.path.isfile(pc):
            raise ConanException(f"kywc: kywc.pc was not installed: {pc}")
        with open(pc, "r", encoding="utf-8") as f:
            content = f.read()
        content = re.sub(r"(?m)^prefix=.*$", "prefix=${pcfiledir}/../..", content)
        with open(pc, "w", encoding="utf-8", newline="\n") as f:
            f.write(content)
        for path in (os.path.join(self.package_folder, "lib", "libkywc.so"),
                     os.path.join(self.package_folder, "include", "libkywc.h")):
            if not os.path.isfile(path):
                raise ConanException(f"kywc: missing installed artifact {path}")

    def package_info(self):
        self.cpp_info.libs = ["kywc"]
        self.cpp_info.set_property("pkg_config_name", "kywc")
