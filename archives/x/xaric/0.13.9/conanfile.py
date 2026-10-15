#!/usr/bin/env python3
"""Conan recipe — xaric 0.13.9 (Autotools) on HarmonyOS PC.

xaric is a terminal IRC client in the ircII family.  configure has two hard
requirements:

  - OpenSSL, probed by AX_CHECK_OPENSSL (configure.ac:360-366) — the macro
    hard-fails with "failed to find OpenSSL" when the probe link fails;
  - tgetent(), probed across termcap/termlib/curses/xtermcap
    (configure.ac:269-285) — configure hard-fails with "i can not find
    tgetent" when none of the four libraries is found.

OHOS adaptations:
  - ``--with-openssl=<prefix>`` bypasses the pkg-config driver and points
    AX_CHECK_OPENSSL at the Conan openssl package (include/openssl/ssl.h +
    lib/libssl.a lib/libcrypto.a).  openssl is packaged statically
    (no-shared), so the resulting xaric binary is fully static apart from
    libc.
  - OHOS ships no libtermcap/libcurses, and the Conan ncurses package
    provides only libncursesw.a.  xaric's tgetent chain never tries
    -lncursesw, so patches/0001-tgetent-ncursesw.patch inserts an
    -lncursesw probe between -lcurses and -lxtermcap (the shipped configure
    script is patched; configure.ac is kept in sync for maintainability).
  - ncurses headers (termcap.h, curses.h) and the static library are
    injected via extra_cflags/extra_ldflags; HAVE_TERMCAP_H then enables the
    termcap code paths in ircterm.c/irc.h and the tgetent probe links
    against libncursesw.a.
  - ``-fcommon``: ircterm.h declares the term_* function pointers as
    tentative definitions (and ircterm.c defines two of them again), which
    clang >= 10 rejects at link time under its default ``-fno-common``.
  - patches/0002-sockopt-cross-fallback.patch gives the SA_CHECK_SOCKOPT
    probes a cross-compiling branch; upstream left action-if-cross empty, so
    a cross build aborts with "cannot run test program while cross
    compiling".  Native builds (the CI worker) never take that branch.
  - patches/0003-trace-symbol-collision-ncursesw.patch renames xaric's own
    ``trace()`` logger to ``xaric_trace()``: ncurses exports ``trace`` from
    lib_trace.c and the static libncursesw.a pulls that member into the link
    ("duplicate symbol: trace").  Semantics differ (varargs logger vs
    ``char *trace(unsigned)``), so ``-Wl,--allow-multiple-definition`` would
    be unsafe here; the rename is the fix recommended for that case by
    knowledge/drafts/DRAFT-14410-static-ncurses-beep-duplicate-symbol.
  - explicit ``--host``/``--build`` triplets: this configure is autoconf 2.69
    without AC_CANONICAL_HOST and the tarball ships no config.sub, so
    AutotoolsToolchain injects nothing and configure would try to *run* the
    freshly linked a.out.  On the CI worker build == host (native, runtime
    probes execute); on a dev box the differing build triplet puts configure
    into cross mode, where ac_cv_ipv4/ac_cv_ipv6 are pinned to what the
    native probe detects so the same source paths get compiled.
  - patching sa.ac/configure.ac makes them newer than aclocal.m4, which
    would make `make` re-run aclocal/autoconf (absent on the build host);
    build() re-stamps the generated files in dependency order instead.

Runtime note: xaric's main() refuses to start without a TTY on stdin
(irc.c:798 ``isatty(0)``), so the test_package drives the binary through a
PTY (python3 pty module) and asserts the printed version.
"""
import os
import glob
import json
import time

from conan import ConanFile
from conan.tools.files import apply_conandata_patches, export_conandata_patches, get
from conan.tools.gnu import Autotools, AutotoolsToolchain
from conan.tools.layout import basic_layout


class XaricConan(ConanFile):
    name = "xaric"
    version = "0.13.9"
    description = "Terminal IRC client in the ircII family"
    license = "GPL-2.0-or-later"
    homepage = "https://xaric.org/"
    url = "https://gitcode.com/OpenHarmonyPCDeveloper/build_in_harmonyos"
    package_type = "application"

    settings = "os", "compiler", "build_type", "arch"

    def export_sources(self):
        export_conandata_patches(self)

    def layout(self):
        basic_layout(self)

    def requirements(self):
        # OpenSSL is a hard configure requirement (AX_CHECK_OPENSSL).
        self.requires("openssl/3.5.6.1")
        # ncurses provides tgetent via libncursesw.a (OHOS has no libtermcap).
        self.requires("ncurses/6.6")

    def source(self):
        get(self, **self.conan_data["sources"][self.version], strip_root=True)

    def generate(self):
        openssl = self.dependencies["openssl"]
        ncurses = self.dependencies["ncurses"]
        tc = AutotoolsToolchain(self)
        # Bypass pkg-config: point AX_CHECK_OPENSSL at the Conan package.
        tc.configure_args.append("--with-openssl=%s" % openssl.package_folder)
        # termcap.h/curses.h come from the ncurses package; HAVE_TERMCAP_H
        # enables the termcap code paths in ircterm.c/irc.h.
        tc.extra_cflags.append(
            "-I%s" % os.path.join(ncurses.package_folder, "include")
        )
        # ircterm.h declares the term_* function pointers as tentative
        # definitions (1990s style) and ircterm.c defines two of them a second
        # time.  clang >= 10 defaults to -fno-common, so every translation
        # unit that includes the header emits a strong symbol and the link
        # aborts with "duplicate symbol: term_scroll".  -fcommon restores the
        # merging semantics the upstream code was written for (same fix as
        # rotter/0.9, wily/0.13.42 and wise/2.4.1 in this repository).
        tc.extra_cflags.append("-fcommon")
        # configure's tgetent probe and the final link need -lncursesw.
        tc.extra_ldflags.append(
            "-L%s" % os.path.join(ncurses.package_folder, "lib")
        )
        if self.settings.os == "OHOS":
            # xaric's configure (autoconf 2.69) has no AC_CANONICAL_HOST and
            # the tarball ships no config.sub/config.guess, so
            # AutotoolsToolchain injects no triplets and configure stays in
            # native mode: it then tries to *run* the freshly linked a.out and
            # aborts with "cannot run C compiled programs" on a cross build.
            # Pass the triplets explicitly (house pattern: slrn, scws).  On
            # the HarmonyOS CI worker build == host, so the native probes still
            # run; only the local macOS simulation enters cross mode.
            tc.configure_args.append("--host=aarch64-unknown-linux-ohos")
            if self._is_native_ohos():
                tc.configure_args.append("--build=aarch64-unknown-linux-ohos")
            else:
                tc.configure_args.append("--build=x86_64-apple-darwin")
                # AC_RUN_IFELSE probes cannot execute while cross compiling,
                # and their cross branches default to "no" — that would
                # silently drop IPV4/IPV6 (iflist.c, ga_nsearch.c) and compile
                # a different source set than the native CI build.  Pin them to
                # what the probe detects on an OHOS device so the local
                # simulation covers the same code.
                tc.configure_args.extend([
                    "ac_cv_ipv4=yes",
                    "ac_cv_ipv6=yes",
                ])
        tc.generate()

    def _is_native_ohos(self):
        # True only for a real native HarmonyOS PC build.  The local
        # ohos-local profile declares OHOS settings on a macOS host and flags
        # that simulation via user.build:flex_bison_native.
        if str(self.settings.os) != "OHOS":
            return False
        if str(self.settings_build.os) != "OHOS":
            return False
        return not self.conf.get("user.build:flex_bison_native",
                                 default=False, check_type=bool)

    def build(self):
        apply_conandata_patches(self)
        self._restamp_autotools_generated()
        autotools = Autotools(self)
        autotools.configure()
        autotools.make(args=["-j1"])
        # Upstream registers zero Automake TESTS (no test/ or tests/ dir; the
        # Makefile.am declares only bin_PROGRAMS/man_MANS/subdir variables and
        # no TESTS/check_PROGRAMS); `make check` is the automake default empty
        # target.  Run it for real so the no_tests marker below is machine
        # evidence from an executed command, not a claim.  See notes.md for the
        # R51 three-step audit.
        autotools.make(target="check", args=["-j1"])
        self._emit_no_tests_marker()

    def _restamp_autotools_generated(self):
        """Keep generated Autotools files newer than the patched inputs.

        Both patches touch sa.ac / configure.ac, so those inputs end up newer
        than aclocal.m4, configure and Makefile.in.  Makefile.in's maintainer
        rules (am__aclocal_m4_deps = sa.ac configure.ac) then re-run
        aclocal/autoconf/automake during `make`, and the build host has no
        Autotools: "aclocal-1.16: command not found" -> Error 127.  The
        patches keep the shipped configure in sync with configure.ac, so
        re-stamping in dependency order is enough - no regeneration needed.
        """
        stamp = time.time()
        for offset, name in enumerate(
                ("aclocal.m4", "configure", "config.h.in", "Makefile.in")):
            path = os.path.join(self.source_folder, name)
            if os.path.exists(path):
                os.utime(path, (stamp + offset, stamp + offset))

    def _emit_no_tests_marker(self):
        upstream = {
            "status": "no_tests",
            "framework": "autotools",
            "command": "make check",
            "discovered": 0,
            "executed": 0,
            "passed": 0,
            "failed": 0,
            "skipped": 0,
            "reason": "xaric-0.13.9 audited: no test/ or tests/ directory in the "
                      "release tarball; the single Makefile.am declares no TESTS "
                      "or check_PROGRAMS, and the generated Makefile.in only "
                      "provides the automake default check/check-am target with "
                      "no registered cases; `make check` therefore executes zero "
                      "test cases (R51 three-step audit, see notes.md).",
        }
        print("HMBS_UPSTREAM_TEST_RESULT=" + json.dumps(upstream, ensure_ascii=False), flush=True)

    def package(self):
        autotools = Autotools(self)
        autotools.install()
        # Pure application package: drop any libtool archives if present.
        for la in glob.glob(
            os.path.join(self.package_folder, "**", "*.la"), recursive=True
        ):
            os.remove(la)
        self._sign_ohos_executables()

    def _sign_ohos_executables(self):
        """OHOS executables must carry a .codesign section to be loadable."""
        import shutil
        import subprocess

        if str(self.settings.os) != "OHOS":
            return
        bindir = os.path.join(self.package_folder, "bin")
        if not os.path.isdir(bindir):
            return
        signer = shutil.which("binary-sign-tool") or "/data/service/hnp/bin/binary-sign-tool"
        readelf = shutil.which("llvm-readelf") or "/data/service/hnp/bin/llvm-readelf"
        if not os.path.isfile(signer) or not os.path.isfile(readelf):
            self.output.info("OHOS signing tools unavailable; leaving binaries untouched")
            return
        for name in sorted(os.listdir(bindir)):
            path = os.path.join(bindir, name)
            if not os.path.isfile(path) or os.path.islink(path):
                continue
            with open(path, "rb") as handle:
                if handle.read(4) != b"\x7fELF":
                    continue
            sections = subprocess.run(
                [readelf, "-SW", path], capture_output=True, text=True, timeout=30
            ).stdout
            if sections.count(".codesign") == 1:
                continue
            temporary = path + ".xaric-signed"
            subprocess.run(
                [signer, "sign", "-inFile", path, "-outFile", temporary, "-selfSign", "1"],
                check=True, timeout=60,
            )
            os.chmod(temporary, (os.stat(path).st_mode & 0o777) | 0o055)
            os.replace(temporary, path)

    def package_info(self):
        self.cpp_info.bindirs = ["bin"]
        self.cpp_info.libs = []
