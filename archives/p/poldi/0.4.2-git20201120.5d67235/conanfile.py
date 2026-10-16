#!/usr/bin/env python3
"""Conan recipe — poldi 0.4.2-git20201120.5d67235 (autotools, OHOS).

Poldi is the GnuPG project's PAM module: it authenticates a user through an
OpenPGP smartcard, the card itself being driven by GnuPG's scdaemon over the
assuan protocol (a trimmed copy of libassuan is bundled in the source tree).
The version string is Debian's name for upstream commit 5d67235 (2020-11-20);
that snapshot intentionally ships ``configure.ac``/``Makefile.am`` only, so
the recipe bootstraps ``aclocal``/``autoheader``/``automake``/``autoconf``
itself (the equivalent of upstream's ``autogen.sh``).

The project's single artifact is ``lib/security/pam_poldi.so`` — a plugin that
the PAM stack loads with ``dlopen(3)``, not a library one links against.  The
consumer case exercising it lives in ``test_package/`` (the E345
"ABI-matched private host" pattern: a small program linked against the
published linux-pam package drives the packaged module through
``pam_start_confdir()``/``pam_authenticate()``).

OHOS specifics — each of them is a platform fact, not a style choice:

* automake/aclocal are missing from the HNP toolchain (E248) while autoconf/
  autoheader/m4 are present, so only automake comes from Conan.  ``autoconf``
  is deliberately *not* a tool_requires: its Conan package pulls in its own
  perl, whose XS modules shadow the system perl and break the bootstrap.
* The freshly generated ``config.guess`` needs the HarmonyOS branch and the
  ``__OHOS__`` libc probe (E007); automake 1.18's ``config.sub`` already
  validates ``aarch64-...-linux-ohos``, which is asserted after the bootstrap.
  The edit is applied to the generated file instead of shipping a patch file,
  because the snapshot does not carry these scripts at all.  This is the
  documented R8 exception: it only teaches the triplet guesser about the
  platform and stubs no library logic.
* autoconf's ``config.status`` creates its scratch directory with
  ``umask 077``; on HMDFS the result is not writable even by its creator, so
  the umask is dropped (E114).
* ``src/poldi.h`` used gettext's ``dgettext()`` unconditionally, while the
  OHOS SDK's ``<libintl.h>`` is an empty stub without declarations — the NLS
  block is now guarded by ``ENABLE_NLS`` and the build runs ``--disable-nls``
  (patch 0002).
* ``pam_poldi.so`` explicitly links ``-lpam`` (patch 0001): on OHOS a
  ``dlopen(3)``ed module is relocated against its own dependency closure
  rather than against the libraries the host process has already loaded, so
  without that DT_NEEDED entry libpam rejects the module with
  ``PAM_MODULE_UNKNOWN``.
* There is no ``makeinfo`` on the worker, hence ``MAKEINFO=true``; upstream
  installs nothing for the manual when the info file cannot be produced.
* ``id(1)`` does not exist on the device; configure only warns about it.

R26: no system-name library is produced, the artifact is a plugin.
R32: ``settings.os`` is never compared for equality against ``"Linux"``.
R33: compiler and flags come from the Conan toolchain/profile, not from bare
     shell variables.
R38: the package installs no executable, so there is no commands.json.
R51: upstream registers no automake TESTS; its two test programs
     (``tests/parse-test``, ``tests/pam-test``) are executed in ``build()``
     and the counts are reported through the HMBS marker.
"""
import json
import os
import re

from conan import ConanFile
from conan.errors import ConanException
from conan.tools.files import (
    apply_conandata_patches,
    copy,
    export_conandata_patches,
    get,
)
from conan.tools.gnu import Autotools, AutotoolsToolchain
from conan.tools.layout import basic_layout

# Shared libraries the module needs at run time; build-time probe programs and
# the upstream test programs need the same directories on the loader path.
_RUNTIME_DEPS = ("libgpg-error", "libgcrypt", "libksba", "linux-pam")


class PoldiConan(ConanFile):
    name = "poldi"
    version = "0.4.2-git20201120.5d67235"
    description = ("Poldi — PAM module authenticating users with an OpenPGP "
                   "smartcard (GnuPG)")
    license = "GPL-3.0-or-later"
    homepage = "https://www.gnupg.org/software/poldi/index.html"
    url = "https://github.com/gpg/poldi"

    package_type = "shared-library"
    settings = "os", "compiler", "build_type", "arch"

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        # libgcrypt pins libgpg-error/1.55; require the very same revision so
        # that the graph holds exactly one libgpg-error.
        self.requires("libgpg-error/1.55")
        self.requires("libgcrypt/1.12.2")
        # X.509 authentication method (configure disables it when ksba is
        # missing); keeping it is upstream's default.
        self.requires("libksba/1.8.1")
        self.requires("linux-pam/1.7.2")

    def build_requirements(self):
        # aclocal/automake are not part of the OHOS toolchain (E248).
        self.tool_requires("automake/1.18")

    def layout(self):
        basic_layout(self, src_folder=".")

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def generate(self):
        tc = AutotoolsToolchain(self)

        # The GnuPG m4 macros (m4/gpg-error.m4, m4/libgcrypt.m4, m4/ksba.m4)
        # look for <lib>-config scripts.  The Conan packages ship them, but
        # they were configured with --prefix=/, so the -I/-L flags they print
        # point at the build machine root; libgpg-error even ships gpgrt-config
        # instead of gpg-error-config.  Point configure at the packages and
        # carry the real include/library search paths ourselves.
        for name, option in (("libgpg-error", "--with-libgpg-error-prefix"),
                             ("libgcrypt", "--with-libgcrypt-prefix"),
                             ("libksba", "--with-ksba-prefix")):
            folder = self.dependencies[name].package_folder
            tc.configure_args.append("{}={}".format(option, folder))
            tc.extra_cflags.append("-I{}".format(os.path.join(folder, "include")))
            tc.extra_ldflags.append("-L{}".format(os.path.join(folder, "lib")))
        pam = self.dependencies["linux-pam"].package_folder
        tc.extra_cflags.append("-I{}".format(os.path.join(pam, "include")))
        tc.extra_ldflags.append("-L{}".format(os.path.join(pam, "lib")))

        # NLS: see patch 0002 — the OHOS libintl.h carries no declarations.
        tc.configure_args.append("--disable-nls")
        # No makeinfo on the worker; upstream then installs no info file.
        tc.configure_args.append("MAKEINFO=true")
        tc.generate()

    def build(self):
        apply_conandata_patches(self)
        self._export_dependency_environment()
        self._bootstrap()
        self._apply_ohos_autotools_patch()

        autotools = Autotools(self)
        autotools.configure()
        # -j1: repository policy, and the project is small.
        autotools.make(args=["-j1"])
        self._run_upstream_tests()

    def package(self):
        autotools = Autotools(self)
        autotools.install()
        for license_file in ("COPYING", "AUTHORS"):
            copy(self, license_file, src=self.source_folder,
                 dst=os.path.join(self.package_folder, "licenses"))

    def package_info(self):
        # PAM modules are dlopen()ed by the PAM stack: no library to link
        # against and no header to consume.
        self.cpp_info.libdirs = []
        self.cpp_info.includedirs = []
        self.cpp_info.bindirs = []
        self.cpp_info.set_property("cmake_file_name", "poldi")
        module_dir = os.path.join(self.package_folder, "lib", "security")
        self.runenv_info.define_path("POLDI_PAM_MODULE_DIR", module_dir)
        self.buildenv_info.define_path("POLDI_PAM_MODULE_DIR", module_dir)

    # ── helpers ─────────────────────────────────────────────────────────────

    def _export_dependency_environment(self):
        """Make the -config probes and the loader path work during the build.

        configure.ac drives its dependency detection through the GnuPG
        -config scripts, so those have to be reachable and used explicitly
        (the packages' own prefix is "/").  The same directories must be on
        the loader path: configure runs compiled probe programs and build()
        executes the upstream test programs, and both are linked against the
        dependency shared libraries.
        """
        def bin_file(name, *parts):
            return os.path.join(self.dependencies[name].package_folder,
                                "bin", *parts)

        os.environ["GPG_ERROR_CONFIG"] = bin_file("libgpg-error", "gpgrt-config")
        os.environ["LIBGCRYPT_CONFIG"] = bin_file("libgcrypt", "libgcrypt-config")
        os.environ["KSBA_CONFIG"] = bin_file("libksba", "ksba-config")

        lib_dirs = [os.path.join(self.dependencies[name].package_folder, "lib")
                    for name in _RUNTIME_DEPS]
        existing = os.environ.get("LD_LIBRARY_PATH")
        os.environ["LD_LIBRARY_PATH"] = os.pathsep.join(
            lib_dirs + ([existing] if existing else []))

    def _bootstrap(self):
        """Generate configure/Makefile.in from configure.ac/Makefile.am.

        The snapshot carries no generated Autotools files, so upstream's
        autogen.sh steps are replayed here.  automake runs with --copy: plain
        --add-missing would symlink config.guess/config.sub into the tool
        package, and the OHOS triplet edit below must never be applied to the
        shared automake installation.
        """
        common = dict(cwd=self.source_folder, env="conanbuild")
        self.run("aclocal -I m4 --force", **common)
        self.run("autoheader --force", **common)
        self.run("automake --gnu --add-missing --copy --force-missing", **common)
        self.run("autoconf --force", **common)

    def _apply_ohos_autotools_patch(self):
        """Teach the generated triplet guesser and configure about OHOS.

        Same edits as the framework's patch-autotools-ohos.pl (E007): the
        ``__OHOS__`` libc probe and the HarmonyOS system case in config.guess
        (the latter also covers images whose ``uname -s`` still reports
        "Linux").  config.sub of automake 1.18 already accepts
        ``aarch64-...-linux-ohos``, which is asserted below.  E114 is handled
        at the same place: config.status creates its scratch directory with
        ``umask 077``, which on HMDFS yields a directory the build user cannot
        write into.
        """
        guess = os.path.join(self.source_folder, "config.guess")
        sub = os.path.join(self.source_folder, "config.sub")
        configure = os.path.join(self.source_folder, "configure")

        with open(guess, encoding="utf-8") as handle:
            content = handle.read()
        if "__OHOS__" not in content:
            content = re.sub(r"(^\s*#\s*if\s+defined\(__ANDROID__\)\s*\n"
                             r"\s*LIBC=android)",
                             r"\1\n#elif defined(__OHOS__)\n    LIBC=ohos",
                             content, count=1, flags=re.M)
        if "HarmonyOS" not in content:
            block = ("    *:HarmonyOS:*:*)\n"
                     "\tcase \"$UNAME_MACHINE\" in\n"
                     "\t    aarch64|arm64) MACHINE=aarch64 ;;\n"
                     "\t    armv7*|armv8*) MACHINE=arm ;;\n"
                     "\t    x86_64|amd64)  MACHINE=x86_64 ;;\n"
                     "\t    i?86)         MACHINE=i686 ;;\n"
                     "\t    *)            MACHINE=\"$UNAME_MACHINE\" ;;\n"
                     "\tesac\n"
                     "\tGUESS=${MACHINE}-unknown-linux-ohos\n"
                     "\t;;\n\n")
            marker = "    *:NetBSD:*:*)\n"
            if marker not in content:
                raise ConanException("config.guess: NetBSD case not found")
            content = content.replace(marker, block + marker, 1)
        with open(guess, "w", encoding="utf-8") as handle:
            handle.write(content)

        probe = os.path.join(self.build_folder, "config.sub.probe")
        self.run('"{}" aarch64-linux-ohos > "{}"'.format(sub, probe),
                 cwd=self.source_folder, env="conanbuild")
        with open(probe, encoding="utf-8") as handle:
            triplet = handle.read().strip()
        if triplet != "aarch64-unknown-linux-ohos":
            raise ConanException(
                "config.sub does not accept the OHOS triplet: {!r}".format(triplet))

        with open(configure, encoding="utf-8", errors="surrogateescape") as handle:
            content = handle.read()
        patched = content.replace(
            'tmp=`(umask 077 && mktemp -d "./confXXXXXX") 2>/dev/null`',
            'tmp=`mktemp -d "./confXXXXXX" 2>/dev/null`').replace(
            '(umask 077 && mkdir "$tmp")', 'mkdir "$tmp"')
        if patched == content:
            raise ConanException(
                "autoconf's config.status temporary-directory template changed")
        with open(configure, "w", encoding="utf-8",
                  errors="surrogateescape") as handle:
            handle.write(patched)
        self.output.info("OHOS bootstrap adaptations applied (E007/E114)")

    def _run_upstream_tests(self):
        """Run the upstream test entry points and report honest counts.

        tests/Makefile.am declares ``parse-test`` and ``pam-test`` as
        noinst_PROGRAMS and registers no automake TESTS, so ``make check``
        itself runs nothing; both programs are built by ``make all`` and are
        executed here.  The authentication run of pam-test needs a writable
        PAM configuration and an OpenPGP smartcard, which the worker cannot
        provide — that single case is reported as skipped with its reason
        instead of being silently dropped.  The packaged module's real PAM
        flow is covered by test_package/.
        """
        autotools = Autotools(self)
        autotools.make(target="check")

        cases = [
            ("parse-test option vector",
             '"{}" -f foo.txt -b bar baz rest < /dev/null'.format(
                 self._upstream_test_program("parse-test"))),
            ("parse-test config stream",
             '"{}" < /dev/null'.format(
                 self._upstream_test_program("parse-test"))),
            ("pam-test --version",
             '"{}" --version'.format(
                 self._upstream_test_program("pam-test"))),
            ("pam-test --help",
             '"{}" --help'.format(
                 self._upstream_test_program("pam-test"))),
        ]
        for name, command in cases:
            self.output.info("running upstream case: {}".format(name))
            self.run(command, cwd=self.build_folder, env="conanbuild")

        report = {
            "framework": "hand-run upstream programs (no automake TESTS)",
            "command": "make check (0 registered cases) + tests/parse-test "
                       "+ tests/pam-test",
            "discovered": len(cases) + 1,
            "executed": len(cases),
            "passed": len(cases),
            "failed": 0,
            "skipped": 1,
            "skipped_reason": "pam-test <service>: needs a writable PAM "
                              "configuration and an OpenPGP smartcard; the "
                              "module's PAM flow is exercised by test_package",
        }
        self.output.info("HMBS_UPSTREAM_TEST_RESULT="
                         + json.dumps(report, ensure_ascii=False))

    def _upstream_test_program(self, name):
        """Return the built path of an upstream test program.

        Conan builds this recipe out of tree, so the programs generated by
        `make` live in the build folder; the source folder is checked as well
        for the in-source case.
        """
        for base in (self.build_folder, self.source_folder):
            program = os.path.join(base, "tests", name)
            if os.path.isfile(program):
                return program
        raise ConanException("upstream test program was not built: {}".format(name))
