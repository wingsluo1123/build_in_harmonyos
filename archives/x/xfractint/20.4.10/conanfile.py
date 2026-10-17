#!/usr/bin/env python3
"""Conan recipe — xfractint 20.4.10 (X11 fractal generator, handwritten Makefile).

Upstream is the classic Fractint X11 port (xfractint 20.04p10): a recursive
set of handwritten GNU Makefiles with no configure/cmake. The build:

  1. compiles and runs the help compiler ./hc (hc /c) to generate
     fractint.hlp natively on the device;
  2. recurses into common/ and unix/ with CFLAGS passed down;
  3. links everything with the flags from $(CFLAGS) and $(LIBS).

Every upstream default that does not fit HarmonyOS PC (CC=/usr/bin/gcc,
no -fcommon, /usr/X11R6 lib paths) is overridden on the make command line;
only two minimal portability patches touch the sources (see conandata.yml).
"""

import os
import shutil

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.files import (
    apply_conandata_patches,
    copy,
    export_conandata_patches,
    get,
)
from conan.tools.layout import basic_layout


class XfractintConan(ConanFile):
    name = "xfractint"
    version = "20.4.10"
    description = "X11 fractal generator and zoomer (Fractint UNIX port)"
    license = "LicenseRef-Fractint"
    homepage = "http://www.fractint.org/"
    url = "https://gitcode.com/OpenHarmonyPCDeveloper/build_in_harmonyos"
    package_type = "application"
    settings = "os", "arch", "compiler", "build_type"

    def validate(self):
        if str(self.settings.os) not in ("Linux", "OHOS"):
            raise ConanInvalidConfiguration(
                f"xfractint supports Linux/OHOS, not {self.settings.os}"
            )

    def requirements(self):
        # Sole library dependency plus its headers-only protocol package.
        # xorgproto (X11/X.h, Xatom.h, keysymdefs...) is required explicitly:
        # as a transitive dep it is not surfaced to this recipe's dependency
        # iteration (same lesson as xworld's manifest).
        self.requires("libx11/1.8.13.1")
        self.requires("xorgproto/2025.1")

    def layout(self):
        basic_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def export_sources(self):
        export_conandata_patches(self)

    def _dependency_dirs(self):
        """Explicit include/lib closure of all host dependencies."""
        include_dirs, lib_dirs = [], []
        for dep in self.dependencies.host.values():
            package_folder = dep.package_folder
            if not package_folder:
                continue
            include_dir = os.path.join(package_folder, "include")
            lib_dir = os.path.join(package_folder, "lib")
            if os.path.isdir(include_dir) and include_dir not in include_dirs:
                include_dirs.append(include_dir)
            if os.path.isdir(lib_dir) and lib_dir not in lib_dirs:
                lib_dirs.append(lib_dir)
        return include_dirs, lib_dirs

    def build(self):
        apply_conandata_patches(self)

        compilers = self.conf.get(
            "tools.build:compiler_executables", check_type=dict, default={}
        )
        cc = compilers.get("c", "clang") if compilers else "clang"
        jobs = self.conf.get("tools.build:jobs", default=4)

        include_dirs, lib_dirs = self._dependency_dirs()

        # Full upstream CFLAGS (top Makefile's assignment is fully overridden):
        # header dir, XFRACT defines, -fcommon for the cross-file tentative
        # definitions (clang defaults to -fno-common), plus the X11 headers.
        cflags = " ".join(
            [
                "-I./headers",
                "-DXFRACT",
                "-DNOBSTRING",
                "-DBIG_ANSI_C",
                "-DLINUX",
                "-fno-builtin",
                "-fcommon",
                "-O2",
            ]
            + [f"-I{d}" for d in include_dirs]
        )

        # The final link rule is "$(CC) -o xfractint $(CFLAGS) $(OPT) ... $(LIBS)"
        # — there is no $(LDFLAGS) — so the library search path and the link
        # closure must be declared inside LIBS (implement policy item 5).
        libs_parts = [f"-L{d}" for d in lib_dirs]
        if lib_dirs:
            libs_parts.append(f"-Wl,-rpath-link,{':'.join(lib_dirs)}")
        libs_parts.extend(["-lX11", "-lm"])
        libs = " ".join(libs_parts)

        # PREFIX feeds the SRCDIR baked into unix.c/fractint.c/help.c
        # (where fractint.hlp and the data files live at runtime).
        prefix = self.package_folder

        make_cmd = (
            f"make -j{jobs} "
            f"CC='{cc}' "
            f"CFLAGS='{cflags}' "
            f"LIBS='{libs}' "
            f"PREFIX='{prefix}'"
        )
        self.run(make_cmd, cwd=self.source_folder, env="conanbuild")

    def package(self):
        source = self.source_folder
        package = self.package_folder

        bin_dir = os.path.join(package, "bin")
        share_dir = os.path.join(package, "share", "xfractint")
        os.makedirs(bin_dir, exist_ok=True)
        os.makedirs(share_dir, exist_ok=True)

        executable = os.path.join(source, "xfractint")
        if not os.path.isfile(executable):
            raise ConanInvalidConfiguration(
                "xfractint executable missing after build: %s" % executable
            )
        shutil.copy2(executable, os.path.join(bin_dir, "xfractint"))

        # Mirror the upstream `make install` file set (without its
        # /usr/bin/install + strip steps) into <package>/share/xfractint.
        copy(self, "fractint.hlp", source, share_dir, keep_path=False)
        copy(self, "sstools.ini", source, share_dir, keep_path=False)
        copy(self, "*.txt", source, share_dir, keep_path=False)
        copy(self, "read.me", source, share_dir, keep_path=False)
        for data_dir, pattern in (
            ("pars", "*.par"),
            ("formulas", "*.frm"),
            ("ifs", "*.ifs"),
            ("lsystem", "*.l"),
            ("maps", "*.map"),
        ):
            copy(
                self,
                pattern,
                os.path.join(source, data_dir),
                os.path.join(share_dir, data_dir),
                keep_path=False,
            )

        # The upstream license statement lives in read.me ("Copyrighted
        # freeware", custom Fractint license => LicenseRef-Fractint).
        license_dir = os.path.join(package, "licenses")
        os.makedirs(license_dir, exist_ok=True)
        copy(self, "read.me", source, license_dir, keep_path=False)
        shutil.move(
            os.path.join(license_dir, "read.me"),
            os.path.join(license_dir, "LICENSE.readme"),
        )

    def package_info(self):
        self.cpp_info.bindirs = ["bin"]
        self.runenv_info.prepend_path("PATH", os.path.join(self.package_folder, "bin"))
        # xfractint resolves help/data files through findpath(): $FRACTDIR
        # first, then the compile-time SRCDIR, then ./. Exporting FRACTDIR
        # keeps the data lookup correct even after Conan relocates the
        # package folder (SRCDIR is only a build-time best effort).
        self.runenv_info.define(
            "FRACTDIR", os.path.join(self.package_folder, "share", "xfractint")
        )
