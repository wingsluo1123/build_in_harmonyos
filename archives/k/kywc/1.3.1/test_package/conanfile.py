#!/usr/bin/env python3
"""test_package for kywc 1.3.1 — real libkywc consumer on a real socket.

Compiles test_kywc.c against the installed package (include/libkywc.h,
lib/libkywc.so) and runs it: a minimal Wayland server (wl_compositor v4
global) on an AF_UNIX socket inside the OHOS sandbox, then real public API
calls (kywc_context_create / create_by_display / process / destroy plus the
error paths). The binary prints CHECK PASS / CHECK FAIL per case and exits
non-zero on failure — the test() self.run is a real execution, not a stub.

The installed kywc.pc is inspected as well: Name/Version/Libs/Cflags and the
relocatable prefix=${pcfiledir}/../.. written by package().
"""
import os
import shutil

from conan import ConanFile
from conan.errors import ConanException
from conan.tools.build import cross_building


class KywcTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"
    test_type = "explicit"
    generators = "VirtualRunEnv"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def layout(self):
        # keep generators/build outputs out of the archive source dir
        self.folders.build = "build"
        self.folders.generators = "build/conan"

    def _package_folder(self):
        return self.dependencies[self.tested_reference_str].package_folder

    def _check_package_layout(self):
        pkg = self._package_folder()
        checks = [
            ("libkywc shared library", os.path.join(pkg, "lib", "libkywc.so")),
            ("public header", os.path.join(pkg, "include", "libkywc.h")),
            ("pkg-config metadata",
             os.path.join(pkg, "lib", "pkgconfig", "kywc.pc")),
        ]
        missing = [name for name, path in checks if not os.path.isfile(path)]
        if missing:
            raise ConanException("kywc: missing artifacts: " + ", ".join(missing))
        with open(os.path.join(pkg, "lib", "pkgconfig", "kywc.pc"),
                  "r", encoding="utf-8") as f:
            pc = f.read()
        for needle in ("Name: kywc",
                       "Version: 1.3.1",
                       "Libs: -L${libdir} -lkywc",
                       "Cflags: -I${includedir}",
                       "prefix=${pcfiledir}/../.."):
            if needle not in pc:
                raise ConanException(f"kywc: kywc.pc is missing {needle!r}")

    def build(self):
        # clang needs a writable tmpdir (host /tmp may be read-only on OHOS)
        tmpdir = os.path.join(self.build_folder, "tmp")
        os.makedirs(tmpdir, exist_ok=True)
        os.environ["TMPDIR"] = tmpdir
        cc = shutil.which(os.environ.get("CC", "clang")) or "clang"
        pkg = self._package_folder()
        wayland = self.dependencies["wayland"].package_folder
        src = os.path.join(self.source_folder, "test_kywc.c")
        exe = os.path.join(self.build_folder, "test_kywc")
        flags = " ".join([
            f"-I{pkg}/include",
            f"-I{wayland}/include",
            f"-L{pkg}/lib",
            f"-L{wayland}/lib",
            "-lkywc -lwayland-client -lwayland-server -lpthread -lm",
        ])
        self.run(f"{cc} -o {exe} {src} {flags}")

    def test(self):
        self._check_package_layout()
        exe = os.path.join(self.build_folder, "test_kywc")
        if not os.path.isfile(exe):
            raise ConanException(f"kywc: consumer binary missing: {exe}")
        if cross_building(self):
            self.output.info("cross-building: link-only verification")
            return
        self.output.info("run libkywc consumer test (in-process compositor)")
        self.run(f'"{exe}"', env="conanrun")
        self.output.info("kywc 1.3.1 consumer test PASS")
