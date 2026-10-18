#!/usr/bin/env python3
"""Conan recipe — sndio 1.10.0 on HarmonyOS PC (OHOS / arm64).

sndio is the OpenBSD-derived audio & MIDI framework: libsndio (client library),
sndiod (server daemon) plus the aucat / sndioctl / midicat tools.

Build system: a hand written `configure` (pure POSIX sh, no compiler probes) that
sed-generates every Makefile from Makefile.in.  `configure` switches on `uname`,
so OHOS needs its own `HarmonyOS)` case -- patches/0003 adds it (alsa off,
ldadd=-lm, libsndio.so.{MAJ} symlink set, -Wl,-soname=libsndio.so.{MAJ}).
patches/0001 and 0002 make bsd-compat/ build against musl (OHOS): SOCK_CLOEXEC
already exists and struct ucred is incomplete, so getpeereid() uses a local
sndio_ucred.

Rules honoured:
  * R5  -- configure and the generated Makefiles run through CONFIG_SHELL (OHOS
          has no /bin/sh); default /data/service/hnp/bin/bash.
  * R9  -- make -j1.
  * R33 -- CC / AR / RANLIB come from tools.build:compiler_executables and are
          passed explicitly; ${CC} from the shell environment is never trusted.

Upstream ships no regression suite (there is no regress/ directory in the
tarball), so test_package/ carries the HarmonyOS-specific consumer test.
"""
import os
import shutil

from conan import ConanFile
from conan.errors import ConanException
from conan.tools.files import (apply_conandata_patches, copy, export_conandata_patches,
                               get, replace_in_file)
from conan.tools.layout import basic_layout


class SndioConan(ConanFile):
    name = "sndio"
    version = "1.10.0"
    description = "Small audio and MIDI framework: libsndio + sndiod/aucat/sndioctl"
    license = "ISC"
    homepage = "https://sndio.org/"
    package_type = "library"
    settings = "os", "arch", "compiler", "build_type"
    options = {"shared": [True, False], "fPIC": [True, False]}
    default_options = {"shared": True, "fPIC": True}

    def export_sources(self):
        export_conandata_patches(self)

    def layout(self):
        basic_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"][self.version], strip_root=True)

    # ------------------------------------------------------------------ helpers
    @staticmethod
    def _shell():
        """R5: OHOS has no /bin/sh, configure and each Makefile need a shell."""
        for candidate in (os.environ.get("CONFIG_SHELL"),
                          shutil.which("bash"),
                          "/data/service/hnp/bin/bash"):
            if candidate and os.path.exists(candidate):
                return candidate
        raise ConanException(
            "no usable shell found; set CONFIG_SHELL (OHOS has no /bin/sh)")

    def _build_tool(self, key, fallback):
        """R33: never rely on ${CC} from the environment (empty on CI workers)."""
        compilers = self.conf.get("tools.build:compiler_executables",
                                  default={}, check_type=dict) or {}
        value = compilers.get(key) or fallback
        if os.path.sep in value and not os.path.exists(value):
            raise ConanException(
                f"tools.build:compiler_executables:{key} points to a missing file: {value}")
        return value

    def _flags(self):
        """Optimisation for the requested build type plus any profile cflags."""
        opt = {"Debug": "-O0 -g", "Release": "-O2",
               "RelWithDebInfo": "-O2 -g", "MinSizeRel": "-Os"}.get(
                   str(self.settings.build_type), "-O2")
        cflags = [opt]
        if self.options.get_safe("fPIC", True):
            cflags.append("-fPIC")
        cflags.extend(self.conf.get("tools.build:cflags", default=[], check_type=list) or [])
        ldflags = []
        for key in ("tools.build:sharedlinkflags", "tools.build:exelinkflags"):
            ldflags.extend(self.conf.get(key, default=[], check_type=list) or [])
        return " ".join(cflags), " ".join(ldflags)

    def _assert_patches_applied(self):
        """`patch` on this host is toybox: it exits 0 without touching the file.

        A silent no-op would happily compile the unpatched sources and produce a
        library without the HarmonyOS/configure case, so verify the hunks really
        landed before building.
        """
        checks = (("configure", "HarmonyOS)"),
                  ("bsd-compat/getpeereid.c", "sndio_ucred"),
                  ("bsd-compat/bsd-compat.h", "ifndef SOCK_CLOEXEC"))
        missing = []
        for rel, needle in checks:
            path = os.path.join(self.source_folder, rel)
            if not os.path.isfile(path):
                missing.append(f"{rel}: file missing")
                continue
            with open(path, encoding="utf-8", errors="replace") as handle:
                if needle not in handle.read():
                    missing.append(f"{rel}: no {needle!r}")
        if missing:
            raise ConanException(
                "conandata patches were NOT applied (" + ", ".join(missing) + "). "
                "A silent no-op `patch` (toybox) is the usual cause: run conan "
                "with a real patch implementation on PATH.")

    # -------------------------------------------------------------------- build
    def build(self):
        apply_conandata_patches(self)
        self._assert_patches_applied()

        shell = self._shell()
        cc = self._build_tool("c", "clang")
        ar = self._build_tool("ar", "llvm-ar")
        ranlib = self._build_tool("ranlib", "llvm-ranlib")
        cflags, ldflags = self._flags()

        configure = [f"--prefix={self.package_folder}",
                     # Man pages go to the build folder: they are not part of the
                     # Conan package, and installing then deleting them only makes
                     # the layout look like something it is not.
                     f"--mandir={os.path.join(self.build_folder, 'man')}",
                     "--disable-alsa",   # no ALSA on OHOS
                     "--disable-oss", "--disable-sun",
                     "--disable-rmidi", "--disable-umidi",
                     "--enable-dynamic" if self.options.shared else "--enable-static"]
        self.run(" ".join([f"{shell} ./configure"] + configure),
                 cwd=self.source_folder, env="conanbuild")

        make_vars = [f"SHELL={shell}", f"CC={cc}", f"AR={ar}", f"RANLIB={ranlib}",
                     f'CFLAGS="{cflags}"',
                     # Always assigned, even when empty: an inherited host
                     # LDFLAGS would otherwise inject foreign -L paths ahead of
                     # our own (observed: -L$HOME/usr/local/lib before ../libsndio).
                     f'LDFLAGS="{ldflags}"']
        self.run(" ".join(["make", "-j1"] + make_vars), cwd=self.source_folder, env="conanbuild")
        self.run(" ".join(["make", "install"] + make_vars), cwd=self.source_folder, env="conanbuild")

    # ------------------------------------------------------------------ package
    def package(self):
        # Repo convention: every recipe ships the upstream licence.
        copy(self, "LICENSE", src=self.source_folder,
             dst=os.path.join(self.package_folder, "licenses"))

        # sndio.pc is generated with an absolute prefix (the package folder).
        # Make it relocatable the way Conan consumers expect (lib/pkgconfig -> ../..).
        pc_file = os.path.join(self.package_folder, "lib", "pkgconfig", "sndio.pc")
        if os.path.isfile(pc_file):
            replace_in_file(self, pc_file,
                            f"prefix={self.package_folder}",
                            "prefix=${pcfiledir}/../..")

        libdir = os.path.join(self.package_folder, "lib")
        if self.options.shared and not os.path.exists(os.path.join(libdir, "libsndio.so")):
            raise ConanException("shared build produced no lib/libsndio.so")
        if not self.options.shared and not os.path.exists(os.path.join(libdir, "libsndio.a")):
            raise ConanException("static build produced no lib/libsndio.a")

    def package_info(self):
        self.cpp_info.set_property("cmake_file_name", "sndio")
        self.cpp_info.set_property("cmake_target_name", "sndio::sndio")
        self.cpp_info.set_property("pkg_config_name", "sndio")
        self.cpp_info.libs = ["sndio"]
        self.cpp_info.bindirs = ["bin"]
        self.cpp_info.includedirs = ["include"]
        self.cpp_info.libdirs = ["lib"]
