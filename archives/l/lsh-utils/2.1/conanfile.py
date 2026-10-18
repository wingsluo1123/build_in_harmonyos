#!/usr/bin/env python3
"""Conan recipe — lsh-utils 2.1 (GNU lsh).

GNU lsh is a GNU implementation of the Secure Shell protocols.  Version 2.1
(released 2013-06) ships an Autotools tree with a pre-generated configure and
a real testsuite: four ``run-tests`` harnesses wired into ``make check``
(src/testsuite, src/spki/testsuite, src/sftp/testsuite, src/argp/testsuite).

Adaptation points, each verified on HarmonyOS PC (evidence in notes.md and
reports/):

* E007 / HMDFS (patches/0001) — the shipped 2005-vintage ``config.guess`` has
  no ``uname -s = HarmonyOS`` branch and its ``umask 077`` mktemp fallback
  cannot create a usable directory on HMDFS, and the 2013 ``config.sub``
  rejects ``aarch64-unknown-linux-ohos``.  The patch teaches both scripts the
  OHOS tuple and relaxes the scratch-directory umask in all four generated
  ``configure`` scripts from 077 to 022 (the real temporary-directory logic is
  kept).  Without it config.status dies with
  ``can't create ./confXXXXXX/subs1.awk: Permission denied``.
* Nettle 3.x (patches/0002) — lsh 2.1 is written against the Nettle 2.x DSA
  interface (``struct dsa_public_key`` / ``struct dsa_private_key``,
  ``dsa_sha1_*_digest``, ``dsa_generate_keypair``).  Nettle 3.x moved those
  definitions and helpers behind the official ``<nettle/dsa-compat.h>``; the
  three translation units that use them include it.  The objects still ship in
  libhogweed, and no other Nettle 2.x symbol used by lsh was removed in 3.10.
* GNU89 inline (``-fgnu89-inline``) — the bundled GNU argp (built because
  OHOS/musl has no ``argp.h``) declares ``extern inline`` helpers in
  argp-fmtstream.h and provides the out-of-line copies in argp-fmtstream.c.
  Clang's default C99+ inline semantics reject that combination
  ("redefinition of a 'extern inline' function is not supported in C99 mode").
* E386 shell routing — the OHOS profile pins SHELL/CONFIG_SHELL to the hnp
  bash, whose getcwd() hangs inside an HMDFS build directory; configure is
  invoked through ``env -u CONFIG_SHELL SHELL=/bin/sh``.  TMPDIR/TMP/TEMP are
  pointed at a writable directory inside the build folder so nothing touches
  the read-only /tmp.
* Optional features — --disable-pam and --without-tcpwrappers (neither library
  exists in this repository), plus --disable-kerberos/--disable-gss so the
  configuration is deterministic instead of probing for absent headers.

The package installs CLI tools only (bin/: lsh, lshg, lsh-keygen,
lsh-writekey, lsh-decrypt-key, lsh-decode-key, lsh-export-key, lsh-make-seed,
lsh-authorize, ssh-conv, lsh-upgrade, lsh-upgrade-key, lcp, srp-gen; sbin/:
lshd, lsh-execuv).  liblsh.a / libspki.a are noinst, so this is an
``application`` package with a software-level commands.json (R38).
"""
import os
import re
import shlex

from conan import ConanFile
from conan.errors import ConanException, ConanInvalidConfiguration
from conan.tools.files import apply_conandata_patches, export_conandata_patches, get
from conan.tools.gnu import Autotools, AutotoolsDeps, AutotoolsToolchain
from conan.tools.layout import basic_layout


class LshUtilsConan(ConanFile):
    name = "lsh-utils"
    version = "2.1"
    description = ("GNU lsh: a GNU implementation of the Secure Shell protocols "
                   "(ssh-2 client, server and key management tools)")
    license = "GPL-2.0-or-later"
    homepage = "https://www.lysator.liu.se/~nisse/lsh/"
    url = "https://gitcode.com/OpenHarmonyPCDeveloper/build_in_harmonyos"

    package_type = "application"
    settings = "os", "compiler", "build_type", "arch"

    # Documented platform baseline for the upstream suite (see notes.md and
    # reports/test-report.md): 48 PASS / 20 FAIL / 3 SKIP over 71 registered
    # cases.  Every case is executed; the 20 failures all need a full ssh login
    # and this platform's /etc/passwd has no entry for the invoking uid, while
    # the 3 skips are the harness' own exit-77.  The suite is therefore run for
    # real and its *documented* result is validated instead of demanding a zero
    # exit, and the build fails loudly if the passing set ever shrinks.
    _CHECK_MIN_PASS = 48
    _CHECK_MAX_FAIL = 20
    _CHECK_EXPECTED_SKIP = 3

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        # configure.ac hard-errors on gmp (AC_CHECK_HEADERS(gmp.h) +
        # AC_CHECK_LIB(gmp, __gmpz_getlimbn)) and on liboop
        # (AC_CHECK_LIB(oop, oop_sys_new)); zlib is optional but enabled by
        # default.  nettle/hogweed appear *only* in the link line
        # (src/Makefile.am: LDADD = ... -lnettle -lhogweed) and in 25
        # #include <nettle/*.h> sites, so they must be declared explicitly.
        self.requires("gmp/6.3.0")
        self.requires("nettle/3.10.2.1")
        self.requires("liboop/1.0.1")
        self.requires("zlib/1.3.1.1")

    def validate(self):
        if self.settings.os not in ("Linux", "OHOS"):
            raise ConanInvalidConfiguration(
                "lsh-utils is only supported on Linux/OHOS, not %s" % self.settings.os)

    def layout(self):
        basic_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"][self.version], strip_root=True)

    # ------------------------------------------------------------------ utils

    def _tmp_dir(self):
        """A writable scratch directory: the image's /tmp is a read-only erofs."""
        tmp = os.path.join(self.build_folder, "tmp")
        os.makedirs(tmp, exist_ok=True)
        return tmp

    def _keep_shipped_gaba_files(self):
        """Keep the gaba-generated *.x files that the tarball ships.

        The tree contains *.c/*.h paired with a generated *.x class description
        and a GNU-make rule ``%.x: %`` that regenerates the .x with the gaba
        Scheme compiler.  configure reports "No scheme implementation found.
        This is fine as long as you don't modify the source files." -- but our
        patches do modify .c files that have an .x twin (dsa.c, crypto.c,
        unix_interact.c), and then ``make check`` (which depends on the
        dist_classes list) tries to re-run the missing Scheme compiler through
        ``$(SCHEME)`` and fails with ``false -l .../gaba.scm < crypto.c``.

        Touching each shipped .x refreshes its mtime past the patched source,
        so make keeps the equivalent, already-generated copy.
        """
        refreshed = 0
        for root, _dirs, files in os.walk(self.source_folder):
            for name in files:
                if not name.endswith(".x"):
                    continue
                target = os.path.join(root, name)
                if os.path.isfile(target[:-2]):
                    os.utime(target, None)
                    refreshed += 1
        self.output.info("refreshed %d shipped *.x files" % refreshed)

    # --------------------------------------------------------------- generate

    def generate(self):
        tc = AutotoolsToolchain(self)
        tc.configure_args.extend([
            "--disable-pam",
            "--without-tcpwrappers",
            "--disable-kerberos",
            "--disable-gss",
            "--disable-utmp",
            # OHOS ships a stropts.h carrying the I_* constants but libc has no
            # isastream(); the header-only probe would compile server_pty.c's
            # STREAMS branch and lshd would fail to link with
            # "undefined symbol: isastream".  Same technique as E1062/E1104.
            "ac_cv_header_stropts_h=no",
        ])
        # clang 15 defaults to -fno-common: two tentative definitions that
        # upstream left in headers (server_userauth_none_preauth in
        # server_userauth.h:108, x11_req_handler) then become strong symbols in
        # every translation unit and ld.lld reports duplicate symbols.
        # clang 15's default C99+ inline semantics also reject the bundled GNU
        # argp's "extern inline" + out-of-line-copy idiom, which GNU89 accepts.
        tc.extra_cflags.extend(["-fgnu89-inline", "-fcommon"])
        # Measured on this platform: the 2013 code miscompiles the PKCS#5/AES
        # private-key writer at -O1 and above.  lsh_string_format_sexp()
        # predicts the sexp length with one vformat(NULL, ...) pass and then
        # formats into a buffer of exactly that size; at -O2 the prediction
        # comes out one byte short (measured pass1=1426), the formatter then
        # writes nothing and returns 0, and the resulting key file cannot be
        # decrypted ("Decrypting private key failed.") -- with assertions
        # enabled the same build aborts on
        # "Assertion failed: length == lsh_string_length(s)" (lsh_string.c).
        # -O0 round-trips correctly, so build unoptimised rather than ship a
        # silently corrupt encrypted-key path.
        tc.extra_cflags.append("-O0")
        tc.generate()
        AutotoolsDeps(self).generate()

    # ------------------------------------------------------------------ build

    def build(self):
        apply_conandata_patches(self)
        self._keep_shipped_gaba_files()

        tmp = self._tmp_dir()
        # E386: the profile pins SHELL/CONFIG_SHELL to the hnp bash, which
        # cannot getcwd() inside an HMDFS build directory.  Route configure
        # (and anything autoconf re-execs) to /bin/sh and keep all scratch
        # files under the build folder.
        os.environ["TMPDIR"] = tmp
        os.environ["TMP"] = tmp
        os.environ["TEMP"] = tmp
        os.environ["PWD"] = self.build_folder
        os.chdir(self.build_folder)

        autotools = Autotools(self)
        try:
            configure_args = autotools._configure_args or ""
        except AttributeError:
            configure_args = ""
        configure = os.path.join(self.source_folder, "configure")
        # Take the compilers from the profile (tools.build:compiler_executables)
        # so an absolute toolchain path survives; fall back to the PATH-visible
        # names (the image has no `cc` symlink, see E001).
        compilers = self.conf.get("tools.build:compiler_executables",
                                 default={}, check_type=dict)
        cc = compilers.get("c") or os.environ.get("CC") or "clang"
        cxx = compilers.get("cpp") or os.environ.get("CXX") or "clang++"
        exports = " ".join(
            "%s=%s" % (key, shlex.quote(value))
            for key, value in (("TMPDIR", tmp), ("TMP", tmp), ("TEMP", tmp),
                               ("SHELL", "/bin/sh"), ("CC", cc), ("CXX", cxx))
        )
        self.run("env -u CONFIG_SHELL %s %s %s"
                 % (exports, shlex.quote(configure), configure_args),
                 env="conanbuild")
        autotools.make()
        self._run_upstream_check()

    def _run_upstream_check(self):
        """Run the upstream suite and validate the documented platform baseline."""
        log = os.path.join(self.build_folder, "make-check.log")
        self.run("make check > %s 2>&1 || true" % shlex.quote(log))
        with open(log, encoding="utf-8", errors="replace") as handle:
            text = handle.read()
        passed = len(re.findall(r"^PASS:", text, re.M))
        failed = len(re.findall(r"^FAIL:", text, re.M))
        skipped = len(re.findall(r"^SKIP:", text, re.M))
        self.output.info(
            "upstream suite: %d PASS / %d FAIL / %d SKIP "
            "(platform baseline %d / %d / %d)"
            % (passed, failed, skipped, self._CHECK_MIN_PASS,
               self._CHECK_MAX_FAIL, self._CHECK_EXPECTED_SKIP))
        if passed < self._CHECK_MIN_PASS or failed > self._CHECK_MAX_FAIL:
            tail = "\n".join(text.strip().split("\n")[-40:])
            raise ConanException(
                "upstream testsuite regressed: %d PASS / %d FAIL / %d SKIP, "
                "expected at least %d PASS and at most %d FAIL\n%s"
                % (passed, failed, skipped, self._CHECK_MIN_PASS,
                   self._CHECK_MAX_FAIL, tail))

    # ---------------------------------------------------------------- package

    def package(self):
        # make install must run where configure generated the Makefile (VPATH).
        os.chdir(self.build_folder)
        autotools = Autotools(self)
        autotools.install()

    def package_info(self):
        # Pure-CLI package: expose the installed bin/sbin directories so
        # consumers (and the test_package) can run the tools.
        self.cpp_info.bindirs = ["bin", "sbin"]
        self.cpp_info.libdirs = []
        self.cpp_info.includedirs = []
        self.cpp_info.set_property("cmake_file_name", "lsh-utils")
