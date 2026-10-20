#!/usr/bin/env python3
"""Conan recipe for kywc 1.3.2 — Meson.

Kylin Wayland compositor client library (libkywc).  The upstream project is
kylin-wayland-compositor; 1.3.2 is a Debian packaging revision (the gitee
repository only publishes the upstream/1.3.0 and upstream/1.3.1 tags), so the
source is the Debian pool orig tarball (R39; units-filter/userinfo/uucpsend
precedent).  The tarball's meson.build still declares project version 1.3.0 —
that is upstream's own inconsistency, the source itself is the 1.3.2 release.

Only libkywc is built.  The compositor it normally ships with needs wlroots
0.20, xkbcommon, libdrm, libinput, libdisplay-info, pixman, cairo/pango,
librsvg, libsystemd, json-c, udev and gbm, none of which are packaged for
OHOS, while ukui-quick 4.22.0.1 only consumes the client library
(`pkg_check_modules(... REQUIRED kywc)`, `#include <libkywc.h>`, Debian
Build-Depends libkywc1-dev).  Three local patches add a `compositor` option
(default true, upstream behaviour preserved) that gates every compositor-side
target; `subdir('protocols')` and the libkywc subdirectory stay
unconditional.  With `-Dcompositor=false` the remaining requirements are
wayland-client, wayland-protocols and libm.

Why a static wayland-scanner: protocols/meson.build runs
`find_program('wayland-scanner')`.  HMDFS refuses to execute cache binaries
that link shared libraries, so the scanner shipped by the wayland package
cannot run on the device.  A scanner linked statically against libc is built
from wayland 1.24.0 source in generate() (wayland-protocols/1.48 precedent).
"""
import os
import shutil

from conan import ConanFile
from conan.errors import ConanException, ConanInvalidConfiguration
from conan.tools.files import get, apply_conandata_patches, export_conandata_patches
from conan.tools.layout import basic_layout
from conan.tools.meson import Meson, MesonToolchain

# wayland source version used to build the embedded static scanner
SCANNER_WAYLAND_VERSION = "1.24.0"
SCANNER_EXPAT_STATIC = "/data/service/hnp/expat.org/expat_2.7.3/lib/libexpat.a"
SCANNER_EXPAT_INCLUDE = "/data/service/hnp/expat.org/expat_2.7.3/include"


class KywcConan(ConanFile):
    name = "kywc"
    version = "1.3.2"
    description = "Kylin Wayland compositor client library (libkywc)"
    license = "Expat"
    homepage = "https://gitee.com/openkylin/kylin-wayland-compositor"
    url = "https://gitcode.com/OpenHarmonyPCDeveloper/build_in_harmonyos"

    package_type = "shared-library"
    settings = "os", "arch", "compiler", "build_type"

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        # libkywc/meson.build: dependency('wayland-client')
        # protocols/meson.build: dependency('wayland-protocols', version: '>=1.36')
        self.requires("wayland/" + SCANNER_WAYLAND_VERSION)
        self.requires("wayland-protocols/1.48")

    def validate(self):
        if self.settings.os not in ("Linux", "OHOS"):
            raise ConanInvalidConfiguration(
                f"{self.ref} only supports Linux/OHOS (got {self.settings.os})")

    def layout(self):
        basic_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)
        get(self, **self.conan_data["scanner_sources"], strip_root=True,
            destination="wayland-scanner-src")

    def generate(self):
        tc = MesonToolchain(self)
        # Only the client library is wanted; the compositor, tools, examples
        # and the portal all depend on the unpackaged wlroots stack.
        tc.project_options["compositor"] = "false"
        tc.project_options["libkywc"] = "true"
        tc.project_options["examples"] = "false"
        tc.project_options["tools"] = "false"
        tc.project_options["portal"] = "false"
        tc.project_options["nls"] = "disabled"
        tc.project_options["libunwind"] = "disabled"
        tc.project_options["tracy"] = "false"

        # protocols/meson.build does
        #   wl_protocol_dir = wayland_protos.get_variable('pkgdatadir')
        # and the PkgConfigDeps-generated wayland-protocols.pc has no
        # pkgdatadir variable, so dependency() would abort on get_variable().
        # Hand-write a .pc that exposes the real pkgdatadir and put it first on
        # PKG_CONFIG_PATH (wayland-protocols/1.48 fixes the same gap from the
        # producer side).
        fixed_pc_dir = os.path.join(self.generators_folder, "fixed_pkgconfig")
        os.makedirs(fixed_pc_dir, exist_ok=True)
        wp_base = self.dependencies["wayland-protocols"].package_folder
        with open(os.path.join(fixed_pc_dir, "wayland-protocols.pc"), "w",
                  encoding="utf-8", newline="\n") as f:
            f.write(f"prefix={wp_base}\n"
                    "datadir=${prefix}/share\n"
                    "pkgdatadir=${prefix}/share/wayland-protocols\n\n"
                    "Name: Wayland Protocols\n"
                    "Description: Wayland protocol files\n"
                    "Version: 1.48\n")
        # wayland-client.pc from the wayland package carries
        # "Requires.private: libffi", but libffi is not packaged for this
        # build (the wayland recipe only needs it for the scanner/server) and
        # pkg-config refuses to emit cflags when a private requirement is
        # missing.  libkywc only needs the client API, so expose a minimal
        # wayland-client.pc without the private dependency.
        wl_base = self.dependencies["wayland"].package_folder
        with open(os.path.join(fixed_pc_dir, "wayland-client.pc"), "w",
                  encoding="utf-8", newline="\n") as f:
            f.write(f"prefix={wl_base}\n"
                    "libdir=${prefix}/lib\n"
                    "includedir=${prefix}/include\n\n"
                    "Name: Wayland Client\n"
                    "Description: Wayland client library\n"
                    "Version: 1.24.0\n"
                    "Libs: -L${libdir} -lwayland-client\n"
                    "Cflags: -I${includedir}\n")
        # Meson resolves libkywc's dependency('wayland-client') through
        # pkg-config, but MesonToolchain alone does not expose dependency .pc
        # files.  Append every host dependency's lib/pkgconfig after the
        # hand-written .pc files (wayland/1.24.0 precedent).
        dep_pc_paths = []
        for dep in self.dependencies.values():
            # A greedy transitive requirement whose binary is not needed for
            # this package (libffi for wayland-client) has package_folder None.
            if not dep.package_folder:
                continue
            pc_dir = os.path.join(dep.package_folder, "lib", "pkgconfig")
            if os.path.isdir(pc_dir):
                dep_pc_paths.append(pc_dir)
        tc.pkg_config_path = os.pathsep.join(
            [fixed_pc_dir] + dep_pc_paths + [tc.pkg_config_path or ""])
        tc.generate()

        # OHOS sandbox: meson cannot resolve llvm-ar (HMDFS symlink, zix/serd
        # precedent).  Inject it into the generated native file, and also put
        # it on the environment for any tool spawned outside meson.
        compiler_executables = (
            self.conf.get("tools.build:compiler_executables", default={},
                          check_type=dict) or {})
        ar_path = (compiler_executables.get("ar") or shutil.which("ar")
                   or "/data/service/hnp/bin/ar")
        native_file = os.path.join(self.generators_folder,
                                   "conan_meson_native.ini")
        with open(native_file, "r", encoding="utf-8") as f:
            content = f.read()
        if "\nar =" not in content:
            content = content.replace(
                "[binaries]\n", f"[binaries]\nar = '{ar_path}'\n", 1)
            with open(native_file, "w", encoding="utf-8", newline="\n") as f:
                f.write(content)
        os.environ["AR"] = ar_path
        ranlib = compiler_executables.get("ranlib") or shutil.which("ranlib")
        if ranlib:
            os.environ["RANLIB"] = ranlib

        # protocols/meson.build: find_program('wayland-scanner') searches the
        # host PATH; the static scanner is produced there by
        # _build_static_scanner() before meson configure runs.  Conan 2 does
        # not source saved env scripts for tool subprocesses, so PATH and
        # PKG_CONFIG_PATH are exported on os.environ as well (qtwayland
        # precedent).
        os.environ["PATH"] = (self.generators_folder + os.pathsep
                              + os.environ.get("PATH", ""))
        pkg_config_path = tc.pkg_config_path
        if os.environ.get("PKG_CONFIG_PATH"):
            pkg_config_path += os.pathsep + os.environ["PKG_CONFIG_PATH"]
        os.environ["PKG_CONFIG_PATH"] = pkg_config_path

    # ── static wayland-scanner ────────────────────────────────────────────

    def _find_expat_static(self):
        candidates = [SCANNER_EXPAT_STATIC]
        for dep in self.dependencies.values():
            # Same guard as generate(): a transitive dependency whose binary
            # is not needed (libffi) reports package_folder None.
            if dep.ref.name == "expat" and dep.package_folder:
                candidates.append(os.path.join(dep.package_folder,
                                               "lib", "libexpat.a"))
        for candidate in candidates:
            if os.path.isfile(candidate):
                self.output.info(f"kywc: static expat -> {candidate}")
                return candidate
        raise ConanException(
            "no static libexpat.a found for the static wayland-scanner link; "
            f"tried: {candidates}")

    def _find_expat_include(self):
        candidates = [SCANNER_EXPAT_INCLUDE]
        for dep in self.dependencies.values():
            # Same guard as _find_expat_static() and generate().
            if dep.ref.name == "expat" and dep.package_folder:
                candidates.append(os.path.join(dep.package_folder, "include"))
        for candidate in candidates:
            if os.path.isdir(candidate):
                return candidate
        return None

    def _build_static_scanner(self):
        """Build a statically linked wayland-scanner from wayland source."""
        scanner_src = os.path.join(self.source_folder, "wayland-scanner-src")

        config_h = os.path.join(scanner_src, "config.h")
        with open(config_h, "w", encoding="utf-8", newline="\n") as f:
            f.write("#define HAVE_EXPAT 1\n"
                    '#define PACKAGE "wayland"\n'
                    f'#define VERSION "{SCANNER_WAYLAND_VERSION}"\n')

        version_in = os.path.join(scanner_src, "src", "wayland-version.h.in")
        version_h = os.path.join(scanner_src, "src", "wayland-version.h")
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

        dtd_h = os.path.join(scanner_src, "src", "wayland.dtd.h")
        self.run(
            f"python3 {scanner_src}/src/embed.py "
            f"{scanner_src}/protocol/wayland.dtd wayland_dtd > {dtd_h}",
            env="conanbuild",
        )

        scanner_bin = os.path.join(self.generators_folder, "wayland-scanner")
        cc = shutil.which("clang") or "/data/service/hnp/bin/clang"
        expat_include = self._find_expat_include()
        inc_flag = f"-I{expat_include} " if expat_include else ""
        self.run(
            f"{cc} -o {scanner_bin} "
            f"-include {config_h} "
            f"-I{scanner_src} -I{scanner_src}/src -I{scanner_src}/protocol "
            f"{scanner_src}/src/scanner.c {scanner_src}/src/wayland-util.c "
            f"{inc_flag}{self._find_expat_static()} "
            f"-lm -lpthread -static",
            env="conanbuild",
        )
        self.output.info("kywc: built static wayland-scanner")

    # ── build / package ───────────────────────────────────────────────────

    def build(self):
        # The scanner must exist before meson configure resolves
        # find_program('wayland-scanner').
        self._build_static_scanner()
        apply_conandata_patches(self)
        meson = Meson(self)
        meson.configure()
        meson.build()

    def package(self):
        Meson(self).install()
        if self.settings.os == "OHOS":
            self._resign_installed_elfs()
        self._create_shared_lib_aliases()

    def package_info(self):
        self.cpp_info.libs = ["kywc"]
        self.cpp_info.includedirs = ["include"]
        self.cpp_info.set_property("pkg_config_name", "kywc")
        self.cpp_info.set_property("cmake_file_name", "kywc")
        self.cpp_info.set_property("cmake_target_name", "kywc::kywc")

    # ── helpers ───────────────────────────────────────────────────────────

    def _create_shared_lib_aliases(self):
        """Restore libkywc.so -> libkywc.so.N links if the install lost them.

        Meson installs the versioned library plus its SONAME symlink; on some
        filesystems the symlink step is dropped (libinput precedent), which
        breaks ``-lkywc``.  Fall back to byte copies when symlink() is
        refused.
        """
        libdir = os.path.join(self.package_folder, "lib")
        if not os.path.isdir(libdir):
            return
        real = None
        for name in sorted(os.listdir(libdir)):
            if name.startswith("libkywc.so.") and name != "libkywc.so":
                real = name
                break
        if not real:
            return
        soname = "libkywc.so." + real.split("libkywc.so.")[1].split(".")[0]
        for src, dst in ((real, soname), (soname, "libkywc.so")):
            src_path = os.path.join(libdir, src)
            dst_path = os.path.join(libdir, dst)
            if os.path.exists(src_path) and not os.path.lexists(dst_path):
                try:
                    os.symlink(src, dst_path)
                except OSError:
                    shutil.copy2(src_path, dst_path)

    @staticmethod
    def _is_elf(path):
        try:
            with open(path, "rb") as handle:
                return handle.read(4) == b"\x7fELF"
        except OSError:
            return False

    def _resign_installed_elfs(self):
        """Re-sign every installed ELF for OHOS.

        ``meson install`` rewrites each ELF it installs (it blanks the build
        tree RUNPATH in place), which invalidates the link-time ``.codesign``
        section; the loader then refuses to map the library.  Strip the stale
        section and re-sign the installed file (libinput/kpkpass precedent).
        """
        objcopy = "/data/service/hnp/bin/llvm-objcopy"
        signer = "/data/service/hnp/bin/binary-sign-tool"
        if not os.path.isfile(objcopy):
            objcopy = shutil.which("llvm-objcopy") or objcopy
        if not os.path.isfile(signer):
            signer = shutil.which("binary-sign-tool") or signer
        for tool in (objcopy, signer):
            if not os.path.isfile(tool):
                raise ConanException(
                    f"Required OHOS signing tool not found: {tool}")
        for root, _dirs, files in os.walk(self.package_folder):
            for name in sorted(files):
                path = os.path.join(root, name)
                if os.path.islink(path) or not os.path.isfile(path):
                    continue
                if not self._is_elf(path):
                    continue
                self.run(f'"{objcopy}" --remove-section .codesign "{path}"')
                self.run(f'"{signer}" sign -inFile "{path}" -outFile "{path}" '
                         f"-selfSign 1")
