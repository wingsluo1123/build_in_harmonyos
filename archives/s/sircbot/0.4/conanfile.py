#!/usr/bin/env python3
"""Conan recipe for sircbot 0.4 — small IRC bot for git hooks, cronjobs and scripts.

Plain C (4 sources, hand-written Makefile, no configure).  The build produces
two executables:

  * ``sircbot``      — the daemon: connects to an IRC server, joins the given
                       channels and owns one AF_UNIX socket per channel.
  * ``sircbot-send`` — CLI that pipes stdin into a channel socket, which makes
                       the daemon relay it as a PRIVMSG.

Upstream ships **no test suite**: the Makefile has no ``check``/``test``
target (``make -n check`` -> "No rule to make target 'check'") and the sources
contain no assertions, so this recipe runs no upstream tests.  All verification
lives in ``test_package/`` as consumer end-to-end tests (see MANIFEST.yml and
notes.md).

Adapted for HarmonyOS PC (OHOS/aarch64).  See patches/conandata for the two
portability patches; both keep the historical behaviour and only add
run-time overrides plus fallbacks.
"""
import os

from conan import ConanFile
from conan.tools.files import apply_conandata_patches, copy, export_conandata_patches, get
from conan.tools.layout import basic_layout


class SircbotConan(ConanFile):
    name = "sircbot"
    version = "0.4"

    description = "sircbot — small IRC bot for use with git hooks, cronjobs and scripts"
    license = "GPL-2.0-only"
    homepage = "https://git.alpinelinux.org/cgit/sircbot/"
    url = "https://gitcode.com/OpenHarmonyPCDeveloper/build_in_harmonyos"

    package_type = "application"

    settings = "os", "compiler", "build_type", "arch"

    def export_sources(self):
        export_conandata_patches(self)

    def layout(self):
        basic_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def build(self):
        apply_conandata_patches(self)

        # R33: take the compiler from the Conan configuration, never from bare
        # shell variables (${CC} is empty on the release workers).
        compilers = self.conf.get("tools.build:compiler_executables",
                                  default={}, check_type=dict)
        cc = compilers.get("c", "clang") if compilers else "clang"

        # Only the daemon and its CLI are built.  The Makefile's optional Lua
        # binding is guarded by `ifneq (NOLUA,)`, which compares the literal
        # word NOLUA against the empty string and is therefore always true —
        # that target cannot be switched off from the command line, so the two
        # shipped targets are requested explicitly instead.  See notes.md for
        # why the binding is not part of this adaptation.
        # R9: build serially.
        self.run(f"make CC={cc} sircbot sircbot-send -j1", cwd=self.source_folder)

    def package(self):
        # `make install` cannot be used: it depends on $(TARGETS), which always
        # contains the Lua module the Makefile refuses to drop.
        copy(self, "sircbot", self.source_folder,
             os.path.join(self.package_folder, "bin"))
        copy(self, "sircbot-send", self.source_folder,
             os.path.join(self.package_folder, "bin"))

    def package_info(self):
        self.cpp_info.bindirs = ["bin"]
