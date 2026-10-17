#!/usr/bin/env python3
"""Conan recipe — maildrop 4.0.3 (autotools).

maildrop is Courier's mail filter and delivery agent. Its release tarball ships
a top-level ``configure`` that drives nine ``AC_CONFIG_SUBDIRS`` subpackages
(numlib, liblock, rfc822, rfc2045, gdbmobj, bdbobj, makedat, maildir,
maildrop), so anything patched into a generated ``configure`` has to be patched
in ten of them and not in one.

The portability fixes this package needs are source changes carried in
patches/ — hard-link fallbacks for a filesystem that refuses hard links, a
``TMPDIR``-honouring replacement for ``tmpfile()``, an explicit deduction guide
for one nested class template, and two guards that inspect permissions this
target cannot represent. Each one, with the measurement behind it, is recorded
in notes.md next to this recipe.
"""
import os

from conan import ConanFile
from conan.errors import ConanException
from conan.tools.files import get, apply_conandata_patches, export_conandata_patches
from conan.tools.gnu import Autotools, AutotoolsToolchain
from conan.tools.layout import basic_layout


class MaildropConan(ConanFile):
    name = "maildrop"
    version = "4.0.3"
    description = ("Mail filter and delivery agent for maildir mailboxes, from "
                   "the Courier mail server suite")
    license = "GPL-3.0-or-later"
    homepage = "https://www.courier-mta.org/maildrop/"

    package_type = "application"

    settings = "os", "compiler", "build_type", "arch"
    options = {"shared": [True, False]}
    default_options = {"shared": False}

    # configure finds libidn2 and courier-unicode through pkg-config, so their
    # .pc files have to be generated into the build folder.
    generators = "PkgConfigDeps"

    # Every upstream test entry, taken from each subpackage's check-am recipe and
    # run one at a time. `make check` runs exactly these in this order, but a
    # failing entry aborts its subpackage, which would leave the entries after it
    # unrun — and an unrun entry must never be reported as a passing one.
    # libs/numlib, libs/liblock and libs/makedat have an empty check-am.
    TEST_ENTRIES = {
        "libs/rfc822": [
            ("testsuitecpp", "./testsuitecpp | diff -U 5 '{srcdir}/testsuite.txt' -"),
            ("testsuite2", "./testsuite2"),
            ("reftest", "./reftest | diff -U 3 '{srcdir}/reftest.txt' -"),
        ],
        "libs/rfc2045": [
            ("testsuite", "bash '{srcdir}/testsuite' | diff -U 3 '{srcdir}/testsuite.txt.idn' -"),
            ("testsuitemm", "bash '{srcdir}/testsuitemm' | diff -U 3 '{srcdir}/testsuitemm.txt' -"),
            ("testrfc3676parsersuite",
             "bash '{srcdir}/testrfc3676parsersuite' | "
             "diff -U 3 '{srcdir}/testrfc3676parsersuite.txt' -"),
            ("testrfc6533parser", "./testrfc6533parser"),
            ("testsuitecpp", "./testsuitecpp"),
            ("testsuitecpp2", "./testsuitecpp2"),
        ],
        "libs/gdbmobj": [
            ("testsuite", "bash '{srcdir}/testsuite' | cmp -s - '{srcdir}/testsuite.txt'"),
        ],
        "libs/maildir": [
            ("testsuite", "bash '{srcdir}/testsuite' 2>&1 | diff -U 3 '{srcdir}/testsuite.txt' -"),
            ("testsuite2", "bash '{srcdir}/testsuite2' 2>&1 | diff -U 3 '{srcdir}/testsuite2.txt' -"),
            ("maildirkwtest", "LC_ALL=C ./maildirkwtest"),
            ("maildiraclttest", "LC_ALL=C ./maildiraclttest"),
            # check-am invokes testmaildirsearch five times with different inputs
            # and pass criteria; the first one is a not-found case that must exit 2.
            ("testmaildirsearch-notfound",
             "./testmaildirsearch iso-8859-1 needle haystack; test $? = 2 && exit 0; exit 1"),
            ("testmaildirsearch-fold",
             "./testmaildirsearch iso-8859-1 nEEdle needlE"),
            ("testmaildirsearch-collapse",
             "./testmaildirsearch iso-8859-1 'abra  cadAbra' 'abra   cadabra'"),
            ("testmaildirsearch-collapse-lead",
             "./testmaildirsearch iso-8859-1 '  abra  cadAbra  ' ' abra   cadabra'"),
            ("testmaildirsearch-collapse-trail",
             "./testmaildirsearch iso-8859-1 '  abra  cadAbra  ' ' abra   cadabra  '"),
            ("testmaildirmisc", "./testmaildirmisc"),
            ("testmaildircache",
             "LC_ALL=C ./testmaildircache > testmaildircache.out 2>&1 || exit 1; "
             "diff -U 3 '{srcdir}/testmaildircache.tst' testmaildircache.out"),
        ],
    }

    # Subpackages whose check-am drives further sub-makes rather than programs.
    TEST_MAKE_TARGETS = {
        "libs/maildrop": ["run-testsuite", "run-testsuite2",
                          "run-testsuite-mailbot", "run-testsuite3"],
    }

    # Upstream test entries this target cannot satisfy, keyed by the exact entry
    # so that a failure anywhere else is never tolerated. R51 asks for the
    # specific technical reason of each entry.
    UNAVAILABLE_ENTRIES = {
        "libs/rfc2045/testsuite":
            "testsuite.txt.idn is older than two upstream behaviour changes: "
            "its first hunk expects a body part whose charset parameter is "
            "written with single quotes (charset='iso-8859-15', not a valid "
            "RFC 2045 quoted-string) to be decoded, and its second hunk expects "
            "the pre-3.0.0 rendering of utf-8 DSN addresses (ChangeLog "
            "2018-07-31: 'rfc2045/reformime: parse utf-8 address types in "
            "DSNs'). No platform fact is involved in either.",
        "libs/rfc2045/testsuitecpp2":
            "test5 compares the decoded message against a built-in expectation "
            "that keeps raw ISO-8859-1 bytes (\"nob\\xd2dy\") in place, while "
            "this build reports '[unicode encoding error]' for the "
            "content-description name parameter instead. As with the testsuite "
            "entry below, the difference is a decoding-behaviour expectation "
            "with no platform fact behind it. This entry only becomes visible "
            "once the entries are run one by one: under `make check` the "
            "subpackage aborted at its first entry and this one never ran, which "
            "previously made it look like a passing entry.",
        "libs/maildir/testmaildircache":
            "maildircache resolves the cache owner with getpwnam() and then "
            "setgid()/setuid()s to it. This target has no passwd entry for the "
            "process uid, and an unprivileged setuid() to another uid fails "
            "with EPERM, so neither step can succeed. (The getpwuid() "
            "dereference in this same program is fixed by patch 0003; this is "
            "the remaining, unfixable requirement.)",
    }

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        self.requires("pcre2/10.48")
        self.requires("gdbm/1.24")
        self.requires("libidn2/2.3.8")
        self.requires("courier-unicode/2.6.0")
        # libidn2/2.3.8 asks for libiconv/1.17 while courier-unicode/2.6.0 asks
        # for libiconv/1.17.1. Both name the same upstream 1.17 tarball, and
        # only 1.17 keeps both prebuilt binaries resolvable, so unify on it.
        self.requires("libiconv/1.17", override=True)

    def layout(self):
        basic_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def generate(self):
        tc = AutotoolsToolchain(self)
        tc.configure_args.append("--with-db=gdbm")
        # Courier's authlib is not packaged here; maildrop only consults it for
        # setuid delivery integration.
        tc.configure_args.append("--disable-authlib")
        if not self.options.shared:
            tc.configure_args.append("--enable-static")
            tc.configure_args.append("--disable-shared")
        tc.generate()

    def _build_env(self):
        """Environment the tarball's configure, make and tests all need."""
        env = {}

        # This target ships pcre2-config 10.47 and the profile buildenv puts it
        # first on PATH; configure calls pcre2-config by bare name, so the
        # Conan pcre2 (10.48) has to take precedence.
        pcre2_bin = os.path.join(self.dependencies["pcre2"].package_folder, "bin")
        env["PATH"] = pcre2_bin + os.pathsep + os.environ.get("PATH", "")

        # gdbm and libidn2 are shared binaries: configure's conftests and the
        # upstream test programs need their libdirs at run time.
        libdirs = []
        for dep in self.dependencies.values():
            if not dep.package_folder:
                continue
            for libdir in dep.cpp_info.libdirs:
                libdirs.append(os.path.join(dep.package_folder, libdir))
        if libdirs:
            previous = os.environ.get("LD_LIBRARY_PATH", "")
            env["LD_LIBRARY_PATH"] = os.pathsep.join(
                libdirs + ([previous] if previous else []))

        # The C library's compile-time temporary directory is not writable on
        # this target, and the delivered sources honour TMPDIR for that reason.
        env["TMPDIR"] = os.environ.get("TMPDIR") or os.path.expanduser("~/tmp")

        # This target has no /var tree, so none of the mail spools upstream
        # probes for (/var/mail, /usr/spool/mail, /usr/mail) exist. Upstream
        # guards that probe with AC_CACHE_CHECK and its body runs `whoami`,
        # which cannot name the build user because the uid has no passwd entry
        # ("whoami: bad uid"). Stating the two platform facts through the cache
        # is the autoconf-sanctioned way to skip the probe body.
        env["maildrop_cv_SYS_INSTALL_MBOXDIR"] = "./Maildir"
        env["maildrop_cv_SYS_INSTALL_RESET_GID"] = "0"
        return env

    def _srcdir(self, cwd):
        """The srcdir the subpackage's Makefile was configured with.

        The binaries are built in the build tree while the upstream test scripts
        and their expected output stay in the source tree, and the upstream
        recipes address both through $(srcdir). Resolving srcdir the same way
        keeps each entry equivalent to what `make check` runs — using a bare
        ./-relative path silently compares against a missing file.
        """
        makefile = os.path.join(cwd, "Makefile")
        try:
            with open(makefile, encoding="utf-8", errors="ignore") as stream:
                for line in stream:
                    if line.startswith("srcdir ="):
                        return line.split("=", 1)[1].strip()
        except OSError:
            pass
        self.output.warning(
            f"no srcdir in {makefile}; falling back to the build directory, so "
            "entries that compare against source-tree files may fail")
        return cwd

    def _run_upstream_tests(self):
        """Run every upstream test entry individually and report the tally.

        `make check` would be simpler, but it stops a subpackage at its first
        failing entry: the entries after it are then never run, and an unrun
        entry must never be reported as a passing one. Each entry is therefore
        run on its own, its exit status recorded, and the set of failing entries
        compared against UNAVAILABLE_ENTRIES — a failure anywhere else aborts the
        build, and a documented entry that starts passing is reported instead of
        being quietly tolerated.
        """
        results = {}
        logs = os.path.join(self.build_folder, "upstream-tests")
        os.makedirs(logs, exist_ok=True)

        def record(key, command, cwd):
            """Run one entry with its output captured to its own log file.

            The upstream suites print sample messages containing raw ISO-8859-1
            bytes. Letting that reach this process' stdout makes anything that
            decodes our output as UTF-8 fail, so each entry's output — both
            streams, including a failing first pipeline stage — goes to its own
            file, which doubles as the per-entry evidence.
            """
            log = os.path.join(logs, key.replace("/", "-") + ".log")
            results[key] = self.run(f"( {command} ) > '{log}' 2>&1",
                                    cwd=cwd,
                                    ignore_errors=True)
            return log

        for subpackage, entries in self.TEST_ENTRIES.items():
            cwd = os.path.join(self.build_folder, subpackage)
            srcdir = self._srcdir(cwd)
            for name, command in entries:
                key = f"{subpackage}/{name}"
                self.output.info(f"upstream test entry: {key}")
                record(key, command.format(srcdir=srcdir), cwd)
        for subpackage, targets in self.TEST_MAKE_TARGETS.items():
            cwd = os.path.join(self.build_folder, subpackage)
            for target in targets:
                key = f"{subpackage}/{target}"
                self.output.info(f"upstream test entry: {key}")
                record(key, f"make {target}", cwd)

        failing = {key for key, rc in results.items() if rc}

        unexpected = failing - set(self.UNAVAILABLE_ENTRIES)
        if unexpected:
            raise ConanException(
                "upstream test entries failing outside the documented table: "
                + ", ".join(sorted(unexpected)))

        never_run = set(self.UNAVAILABLE_ENTRIES) - set(results)
        if never_run:
            raise ConanException(
                "entries documented as unavailable but never run: "
                + ", ".join(sorted(never_run)))

        now_passing = set(self.UNAVAILABLE_ENTRIES) - failing
        if now_passing:
            self.output.warning(
                "documented as unavailable but passing here, so the documented "
                "reason is stale: " + ", ".join(sorted(now_passing)))

        for key in sorted(failing):
            self.output.warning(f"upstream test entry not passing ({key}): "
                                + self.UNAVAILABLE_ENTRIES[key])

        self.output.info(
            f"upstream test entries: {len(results) - len(failing)}/{len(results)} "
            "run and passing; not passing: "
            + (", ".join(sorted(failing)) if failing else "none"))

    # The tarball ships ten pre-generated configure scripts: one at the top
    # level plus one per AC_CONFIG_SUBDIRS subpackage. Each creates the
    # temporary directory config.status works in with
    # `umask 077 && mktemp -d "./confXXXXXX"`, and on this filesystem such a
    # directory is mode 0700 and rejects every write into it, so config.status
    # stops with "could not setup config files machinery". Widening the umask
    # does not help — mktemp -d pins 0700 — so the probe is rewritten to build
    # the directory with mkdir, which this filesystem leaves writable.
    CONFIGURE_TMPDIR_OLD = ('tmp=`(umask 077 && mktemp -d "./confXXXXXX") 2>/dev/null` &&\n'
                            '  test -d "$tmp"')
    CONFIGURE_TMPDIR_NEW = ('tmp="./conf$$-$RANDOM"\n'
                            '  (mkdir "$tmp" 2>/dev/null) && test -d "$tmp"')

    def _fix_generated_configures(self):
        patched = 0
        for root, _, files in os.walk(self.source_folder):
            if "configure" not in files:
                continue
            path = os.path.join(root, "configure")
            with open(path, "r", encoding="utf-8", errors="ignore") as stream:
                text = stream.read()
            if self.CONFIGURE_TMPDIR_OLD not in text:
                continue
            with open(path, "w", encoding="utf-8") as stream:
                stream.write(text.replace(self.CONFIGURE_TMPDIR_OLD,
                                          self.CONFIGURE_TMPDIR_NEW))
            patched += 1
        if not patched:
            raise ConanException(
                "no configure script carried the temporary directory probe; "
                "upstream changed it, so the build would fail before configure")
        self.output.info(
            f"rewrote the temporary directory probe in {patched} configure script(s)")

    # Autotools helper scripts are executable programs, and sources that travel
    # through an export or a checkout can arrive without their executable bit
    # (knowledge E490), which makes configure fail before it starts.
    AUTOTOOLS_PROGRAMS = ("configure", "config.guess", "config.sub",
                          "install-sh", "missing", "depcomp", "compile",
                          "ltmain.sh", "mkinstalldirs")

    def _restore_helper_modes(self):
        restored = 0
        for root, _, files in os.walk(self.source_folder):
            for name in files:
                if name not in self.AUTOTOOLS_PROGRAMS:
                    continue
                path = os.path.join(root, name)
                mode = os.stat(path).st_mode
                if not mode & 0o111:
                    os.chmod(path, mode | 0o755)
                    restored += 1
        self.output.info(
            f"restored the executable bit on {restored} autotools helper script(s)")

    # `testsuite` and `testsuite.mailbot` are generated by configure from their
    # .in templates, so a patch applied to the tarball's copy of them is
    # overwritten before the tests run and the adjustments have to be made to
    # the generated files instead. testsuite2 and testsuite.txt.idn are real
    # source files and do carry patches.
    GENERATED_TEST_FIXES = (
        ("testsuite", "unset VERBOSE\n",
         "unset VERBOSE\n\n"
         "# This filesystem cannot represent private permissions: the chmod go-rw\n"
         "# below leaves the group bits set, so maildrop's filter file permission\n"
         "# check can never pass here. Accept that exposure explicitly.\n\n"
         "MAILDROP_TRUST_FILTER_PERMS=1\n"
         "export MAILDROP_TRUST_FILTER_PERMS\n"),
        ("testsuite", "#! /bin/bash", "#! /bin/sh"),
        ("testsuite", "/bin/bash -c", "/bin/sh -c"),
        ("testsuite.mailbot", "touch --date='2025-01-01'",
         "touch -t 202501010000"),
    )

    def _apply_generated_test_fixes(self):
        for name, old, new in self.GENERATED_TEST_FIXES:
            for base in (self.build_folder, self.source_folder):
                path = os.path.join(base, "libs", "maildrop", name)
                if not os.path.exists(path):
                    continue
                with open(path, "r", encoding="utf-8", errors="ignore") as stream:
                    text = stream.read()
                if old not in text:
                    continue
                with open(path, "w", encoding="utf-8") as stream:
                    stream.write(text.replace(old, new))
                self.output.info(f"adjusted the generated {name} for this target")

    def build(self):
        apply_conandata_patches(self)
        self._restore_helper_modes()
        self._fix_generated_configures()

        env = self._build_env()
        os.makedirs(env["TMPDIR"], exist_ok=True)

        # gdbm and libidn2 are shared binaries. configure's conftests link
        # -lgdbm successfully and then fail to *run* the probe unless the
        # dependency libdirs are also visible, which reports "GDBM library not
        # found" and stops configure. Hand the whole environment to the
        # autotools helper, which starts configure and make as child processes.
        os.environ.update(env)

        # The autotools toolchain this Conan version generates carries no -I/-L
        # for the dependencies, so configure's AC_CHECK_LIB probes cannot find
        # them. The toolchain script appends to whatever CPPFLAGS/LDFLAGS it
        # inherits, so putting them in the environment before configure runs is
        # enough; -L alone is not, because the probes also have to *run* the
        # binary they just linked, hence the rpath.
        includes, libdirs, libs = [], [], []
        for dep in self.dependencies.values():
            if not dep.package_folder:
                continue
            for incdir in dep.cpp_info.includedirs:
                includes.append(os.path.join(dep.package_folder, incdir))
            for libdir in dep.cpp_info.libdirs:
                libdirs.append(os.path.join(dep.package_folder, libdir))
            libs.extend(dep.cpp_info.libs)

        if includes:
            os.environ["CPPFLAGS"] = (" ".join(f"-I{d}" for d in includes)
                                      + " " + os.environ.get("CPPFLAGS", ""))
        if libdirs:
            os.environ["LDFLAGS"] = (" ".join(f"-L{d}" for d in libdirs)
                                     + " "
                                     + " ".join(f"-Wl,-rpath,{d}" for d in libdirs)
                                     + " " + os.environ.get("LDFLAGS", ""))
        # -L is not enough for the dependency libraries themselves: the static
        # courier-unicode archive references GNU libiconv's prefixed symbols
        # (libiconv_open/libiconv/libiconv_close), which configure cannot infer
        # from the headers, so the link needs -liconv and its siblings.
        if libs:
            os.environ["LIBS"] = (" ".join(f"-l{lib}" for lib in libs)
                                  + " " + os.environ.get("LIBS", ""))

        autotools = Autotools(self)
        autotools.configure()
        self._apply_generated_test_fixes()
        autotools.make(args=["-j1"])

        self._run_upstream_tests()

    def package(self):
        autotools = Autotools(self)
        autotools.install()

    def package_info(self):
        # The package ships command line tools (maildrop, mailbot, reformail,
        # reformime, makemime, deliverquota, makedat); the libraries it builds
        # are internal to them and are not part of a public API.
        self.cpp_info.bindirs = ["bin"]
