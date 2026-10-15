#!/usr/bin/env python3
"""Conan recipe — fbset 2.1 (bare upstream Makefile, no configure).

fbset (frame buffer settings) queries and changes the video mode of a Linux
frame buffer device through the FB ioctl family (FBIOGET_VSCREENINFO,
FBIOPUT_VSCREENINFO, ...).  Upstream, by Geert Uytterhoeven, ships a two-file
C program plus a hand-written Makefile: no configure, no install usable inside
a package, and no test target.

Adaptation points (see notes.md for the evidence):
  * `fb.h` is shipped in-tree, so the kernel headers are *not* required and
    there is no compile wall; only `fbset.h` guarded <asm/types.h> behind
    __GLIBC__, which musl/OHOS does not define (patch 0001).
  * The Makefile hardcodes `CC = gcc -Wall -O2 -I.` while this platform ships
    clang only, and `flex`/`bison` are needed to generate lex.yy.c/modes.tab.c
    from the un-generated modes.l/modes.y — hence tool_requires() for both and
    a command-line CC/CFLAGS override (R33: values come from the Conan conf,
    never from shell environment variables).
  * `make install` hardcodes /sbin, /usr/man and mknod()s /dev/fb* — none of
    which may run inside a package, so package() installs the binary by hand.
  * patch 0002 makes the informational `--help` request exit 0 (upstream
    routed it through Die()/exit(1)), which is what the L2 smoke gate and
    every consumer expectation require; every error path keeps status 1.
"""
import glob
import os

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.env import Environment, VirtualBuildEnv
from conan.tools.files import (
    apply_conandata_patches,
    copy,
    export_conandata_patches,
    get,
)
from conan.tools.layout import basic_layout


class FbsetConan(ConanFile):
    name = "fbset"
    version = "2.1"
    description = "Linux frame buffer video mode query/change utility (FB ioctl family)"
    license = "GPL-2.0-only"
    homepage = "http://g33rt.be/migrated/Linux/fbdev/"
    # Upstream distributes tarballs only (no public VCS), so the recipe points
    # at the author's page instead of leaving an empty placeholder.
    url = "http://g33rt.be/migrated/Linux/fbdev/"
    topics = ("framebuffer", "fbdev", "video-mode", "linux")
    package_type = "application"

    settings = "os", "compiler", "build_type", "arch"

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        # fbset links against libc only (musl on OHOS); no third-party
        # runtime dependency.
        pass

    def validate(self):
        # R32: OHOS must be matched alongside Linux, never `== "Linux"`.
        if self.settings.os not in ("Linux", "OHOS"):
            raise ConanInvalidConfiguration(
                f"fbset supports Linux/OHOS only, got {self.settings.os}"
            )

    def build_requirements(self):
        # modes.l / modes.y are shipped un-generated; the upstream Makefile
        # runs flex + bison while building, and neither is guaranteed on a
        # clean CI worker.
        self.tool_requires("flex/2.6.4")
        self.tool_requires("bison/3.8.2")

    def layout(self):
        basic_layout(self, src_folder="src")

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def _compiler_c(self):
        # R33: take the compiler from the Conan profile, never from ${CC}.
        executables = self.conf.get(
            "tools.build:compiler_executables", default={}, check_type=dict
        )
        return executables.get("c") or "clang"

    def generate(self):
        VirtualBuildEnv(self).generate()
        # Expose the resolved compiler inside the build environment so the
        # override is visible in logs and in any generated script.
        env = Environment()
        env.define("CC", self._compiler_c())
        env.vars(self).save_script("conanbuild_cc")

    def build(self):
        apply_conandata_patches(self)

        cc = self._compiler_c()
        # -I. keeps the upstream include of the in-tree fb.h/fbset.h working.
        # -fPIE + pie/relro/now are the hardening baseline checked by L4.
        cflags = "-O2 -Wall -fPIE -I."
        ldflags = "-pie -Wl,-z,relro,-z,now"
        # The Makefile bakes `CC = gcc ...` into a normal assignment, so the
        # command line wins; LDLIBS stays empty because musl provides
        # everything fbset uses (ioctl/open/printf family).
        self.run(
            f'make CC="{cc}" CFLAGS="{cflags}" LDFLAGS="{ldflags}" LDLIBS="" -j1',
            cwd=self.source_folder,
            env="conanbuild",
        )

    def package(self):
        # Upstream `make install` writes to /sbin, /usr/man and mknod()s
        # /dev/fb0..fb7 — install the artifacts by hand instead.
        copy(
            self,
            "fbset",
            self.source_folder,
            os.path.join(self.package_folder, "bin"),
        )
        os.chmod(os.path.join(self.package_folder, "bin", "fbset"), 0o755)
        # The video mode database fbset reads (upstream: /etc/fb.modes*).
        copy(
            self,
            "*.modes.*",
            os.path.join(self.source_folder, "etc"),
            os.path.join(self.package_folder, "share", "fbset"),
        )
        self._sign_binaries()

    def _is_elf(self, path):
        try:
            with open(path, "rb") as f:
                return f.read(4) == b"\x7fELF"
        except OSError:
            return False

    def _sign_binaries(self):
        """HarmonyOS XPM requires signed executables; sign them in place.

        `env -u LD_LIBRARY_PATH` is required: the profile buildenv prepends
        the SDK llvm lib dir, and a conflicting libc++.so makes
        binary-sign-tool fail with "Error relocating ... symbol not found".
        """
        if self.settings.os != "OHOS":
            return
        targets = glob.glob(os.path.join(self.package_folder, "bin", "*"))
        objcopy = "/data/service/hnp/bin/llvm-objcopy"
        signer = "/data/service/hnp/bin/binary-sign-tool"
        for f in targets:
            if not os.path.isfile(f) or os.path.islink(f) or not self._is_elf(f):
                continue
            # .codesign is only present on a previously signed file; a missing
            # section (first signing) is expected, so that step is best-effort.
            # The sign step below is the one that must succeed — it is not
            # guarded and any failure there aborts package().
            self.run(
                'env -u LD_LIBRARY_PATH {oc} --remove-section .codesign '
                '"{f}" 2>/dev/null || true'.format(oc=objcopy, f=f)
            )
            self.run(
                'env -u LD_LIBRARY_PATH {sg} sign -inFile "{f}" -outFile '
                '"{f}" -selfSign 1'.format(sg=signer, f=f)
            )

    def package_info(self):
        # fbset is a command line tool: no library, no headers.
        self.cpp_info.libs = []
        self.cpp_info.includedirs = []
        self.cpp_info.libdirs = []
        self.cpp_info.bindirs = ["bin"]
