#!/usr/bin/env python3
"""Conan recipe for lsm 1.0.21 — OHOS (HarmonyOS PC) adaptation.

lsm (Link Status Monitor, binary name foolsm) is a pure-Makefile C tool:
no configure, no CMake, no test suite. Upstream tarball
foolsm-1.0.21.tar.gz builds a single sbin binary `foolsm` plus helper
scripts and a sample config.

Upstream project was renamed foolsm -> lsm transitional packaging in
Debian because of a conflicting path with libstoragemgmt; the binary
kept the name `foolsm`. This recipe keeps the task name `lsm` while
packaging the `foolsm` binary (see notes.md).

Build: make -j1 CC=<conan conf compiler> (R33, R9).
Install: manual staging with conan copy() (no `make install`: OHOS worker
has only toybox `install`, which fails on HMDFS with Error 64, and HMDFS
has no chmod, so `install -m` is unusable); layout mirrors
`make install DESTDIR=<pf> PREFIX=/ BINDIR=/bin` so the binary lands in
package bin/foolsm (conan bindirs).
Upstream tests: none (Makefile has no check/test target, no tests/
directory) — audited in build() log and declared no_tests in
test_package/MANIFEST.yml.
"""

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.files import apply_conandata_patches, copy, export_conandata_patches, get
from conan.tools.layout import basic_layout


class LsmConan(ConanFile):
    name = "lsm"
    version = "1.0.21"
    description = "Foobar Link Status Monitor — ping multiple targets and run a script on up/down events"
    license = "GPL-2.0-only"
    homepage = "https://lsm.foobar.fi/"
    url = "https://lsm.foobar.fi/"
    topics = ("lsm", "foolsm", "network", "monitor", "icmp", "arping")

    package_type = "application"

    settings = "os", "compiler", "build_type", "arch"

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        # Pure C, libc only — no external dependencies.
        pass

    def layout(self):
        basic_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def validate(self):
        if self.settings.os not in ("Linux", "OHOS"):
            raise ConanInvalidConfiguration(
                "lsm supports Linux and OHOS targets only, got %s" % self.settings.os
            )

    def generate(self):
        # Makefile project: no toolchain file to inject. R33 compliance is
        # achieved in build() by reading the compiler from Conan conf and
        # passing it explicitly on the make command line (not via shell env).
        pass

    def build(self):
        import os

        apply_conandata_patches(self)
        # R33: compiler comes from Conan conf, never from bare shell env.
        compilers = self.conf.get("tools.build:compiler_executables", default={}, check_type=dict)
        cc = compilers.get("c", "clang") if compilers else "clang"
        # Upstream test audit (machine evidence in conan create log):
        # foolsm-1.0.21 ships 56 tarball entries, no tests/ or test/
        # directory, and the Makefile defines only all/clean/distclean/
        # tar/rpm/install targets — no check/test target. `make -n check`
        # therefore has nothing to run; the no_tests declaration in
        # test_package/MANIFEST.yml is grounded here.
        self.output.info("lsm upstream audit: scanning source tree for tests")
        self.run("ls -la \"%s\"" % self.source_folder)
        self.run(
            "if test -d \"%s/tests\" -o -d \"%s/test\"; then echo \"UPSTREAM_TEST_DIRS_FOUND\"; else echo \"UPSTREAM_TEST_DIRS_ABSENT\"; fi"
            % (self.source_folder, self.source_folder)
        )
        self.run(
            "grep -cE \"^ *(check|test) *:\" \"%s/Makefile\" || echo \"UPSTREAM_MAKE_CHECK_ABSENT rc=$?\""
            % self.source_folder
        )
        # R9: -j1 on OHOS.
        self.run("make -j1 CC=\"%s\"" % cc, cwd=self.source_folder)

    def package(self):
        import os

        # Upstream `make install` shells out to GNU coreutils `install`
        # (install -d / install -D -m...). The OHOS worker only has toybox
        # `install`, which fails on HMDFS with `Error 64` even for the very
        # first `install -d <pf>/share/doc/foolsm/examples` line, and any
        # `-m` mode setting would walk into the HMDFS no-chmod restriction
        # (HMBS_CAP_CHMOD=0). Bypass the upstream install target entirely and
        # stage the same file set with conan copy() + os.makedirs, which need
        # no external `install` binary and perform no chmod (precedent:
        # cassbeam/dbeacon manual staging for `install -D`).
        # Layout mirrors `make install DESTDIR=<pf> PREFIX=/ BINDIR=/bin`:
        #   bin/foolsm, etc/foolsm/foolsm.conf, libexec/foolsm/*_script,
        #   share/doc/foolsm/examples/*, var/lib/foolsm (empty runtime dir).
        bindir = os.path.join(self.package_folder, "bin")
        os.makedirs(bindir, exist_ok=True)
        copy(self, "foolsm", src=self.source_folder, dst=bindir,
             keep_path=False)
        etcdir = os.path.join(self.package_folder, "etc", "foolsm")
        os.makedirs(etcdir, exist_ok=True)
        copy(self, "foolsm.conf", src=self.source_folder, dst=etcdir,
             keep_path=False)
        scriptdir = os.path.join(self.package_folder, "libexec", "foolsm")
        os.makedirs(scriptdir, exist_ok=True)
        for script in ("shorewall_script", "shorewall6_script",
                       "default_script", "group_script"):
            copy(self, script, src=self.source_folder, dst=scriptdir,
                 keep_path=False)
        exdir = os.path.join(
            self.package_folder, "share", "doc", "foolsm", "examples")
        os.makedirs(exdir, exist_ok=True)
        for doc in ("README", "foolsm.conf.sample", "default_script.sample",
                    "rsyslog-foolsm.conf.sample"):
            copy(self, doc, src=self.source_folder, dst=exdir,
                 keep_path=False)
        os.makedirs(os.path.join(self.package_folder, "var", "lib", "foolsm"),
                     exist_ok=True)
        copy(self, "LICENSE", src=self.source_folder,
             dst=os.path.join(self.package_folder, "licenses"), keep_path=False)

    def package_info(self):
        # Command-line tool, not a linkable library.
        self.cpp_info.libs = []
        self.cpp_info.includedirs = []
        self.cpp_info.libdirs = []
        self.cpp_info.bindirs = ["bin"]
