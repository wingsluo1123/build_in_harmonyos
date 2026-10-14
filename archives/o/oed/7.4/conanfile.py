#!/usr/bin/env python3
"""Conan recipe for oed 7.4 — portable version of the OpenBSD ed(1) line editor.

oed is a small, self-contained C89 line editor whose only dependency is libc.
Upstream ships a hand-written POSIX sh `configure` script that probes the
compiler and writes a plain Makefile — there is no autoconf/automake involved,
so this recipe drives configure/make directly instead of AutotoolsToolchain.

HarmonyOS (OHOS) adaptations
----------------------------
* patches/0001-buf.c.patch — upstream compiled the scratch-file template in as
  "/tmp/ed.XXXXXXXXXX".  HarmonyOS PC mounts /tmp read-only (erofs), so every
  `ed` invocation died with "cannot open temp file" before reading a single
  command.  open_sbuf() now tries $TMPDIR, then the compiled-in directory, then
  $HOME, which keeps the tool usable on read-only-/tmp systems without changing
  behaviour where /tmp is writable.
* --program-name=ed — upstream configure silently installs the executable as
  "oed" whenever an `ed` binary is already reachable through PATH, which would
  make the produced artefact depend on the builder's machine.  Pin the name.
* patches/0002-configure.patch — upstream builds its include path as
  "-I$(pwd)".  In environments where getcwd() fails (containers, sandboxes, a
  removed working directory) $(pwd) expands to nothing, the "-I" flag alone is
  rejected by the C compiler probe and is therefore dropped; the tree-local
  regex.h is then no longer found via <regex.h>, so the `extern reallocarray`
  declaration it pulls in from config.h never reaches glbl.c and clang 16+
  fails the build on an implicit declaration.  "-I." is what upstream means —
  make always runs in the source directory — and survives a failed getcwd().
"""
from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.files import apply_conandata_patches, export_conandata_patches, get
from conan.tools.layout import basic_layout


class OedConan(ConanFile):
    name = "oed"
    version = "7.4"
    description = "Portable version of the OpenBSD ed(1) line editor"
    license = "BSD-2-Clause"  # portability files (strlcpy/strlcat/reallocarray) are ISC
    homepage = "https://github.com/ibara/oed"
    url = "https://gitcode.com/OpenHarmonyPCDeveloper/build_in_harmonyos"

    package_type = "application"  # CLI executable -> software-level commands.json (R38)

    settings = "os", "compiler", "build_type", "arch"

    def export_sources(self):
        export_conandata_patches(self)

    def validate(self):
        # R32: never compare against "Linux" alone
        if self.settings.os not in ("Linux", "OHOS"):
            raise ConanInvalidConfiguration(
                f"{self.ref} only supports Linux and OHOS, not {self.settings.os}"
            )

    def layout(self):
        basic_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def build(self):
        apply_conandata_patches(self)

        # R33: take the compiler from the Conan configuration, never from a bare
        # ${CC} in the shell environment.
        compilers = self.conf.get(
            "tools.build:compiler_executables", default={}, check_type=dict
        ) or {}
        cc = compilers.get("c", "clang")

        # R1: only the switches this hand-written configure actually understands
        # (--prefix/--mandir/--cc/--cflags/--ldflags/--program-name/--enable-lto/
        # --enable-static).  oed needs nothing beyond libc, so no flags beyond
        # the compiler and the pinned program name are passed.
        self.run(
            f"./configure --prefix={self.package_folder} "
            f"--cc={cc} --program-name=ed",
            cwd=self.source_folder,
        )
        # R9: -j1
        self.run("make -j1", cwd=self.source_folder)

        # R51: upstream has NO test suite — `make test` is a stub that prints
        # "No tests" and upstream ships no tests/ directory.  The functional
        # verification therefore lives in test_package/test.sh; see
        # test_package/MANIFEST.yml for the upstream test inventory evidence.

    def package(self):
        # Upstream `make install` honours PREFIX and DESTDIR.  PREFIX already
        # points at the package folder, so DESTDIR must not be passed (it would
        # install into <package_folder>/<package_folder>/bin).
        self.run("make install", cwd=self.source_folder)

    def package_info(self):
        # R38: CLI tool -> executables only
        self.cpp_info.bindirs = ["bin"]
