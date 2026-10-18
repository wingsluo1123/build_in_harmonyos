#!/usr/bin/env python3
"""Conan recipe - ifmail 2.14tx8.10 (FidoNet transport + gateway suite).

Build system: a hand-written top-level Makefile that does `include CONFIG`
(a plain make-variable file, no configure/cmake/meson anywhere). Every
platform choice is therefore a make command-line override in _make_args();
CONFIG's own Linux OPTS block is kept untouched because musl is close enough
that only DO_NEED_TIME is missing from it (parsedate.y and gettime.c include
<time.h> solely under that knob, so `struct tm` is incomplete without it).

Artifacts - 14 executables; iflib/utlib.a is an internal convenience archive
and is deliberately not installed:
  ifcico/: ifcico ifindex ifinfo ifreq ifroute nlpatch nlookup
  ifgate/: ifmail ifnews (hard link to ifmail) iftoss ifpack ifunpack ifstat
  iflib/ : make_new_ref

Upstream tests (R51): iflib/Makefile carries four -DTESTING targets. Three of
them (testconf, testscan, testrfcaddr) are built and executed at the end of
build() by uptests/run_upstream_tests.sh, which asserts 30 independent check
items against fixtures committed next to the recipe. They are skipped when
this recipe runs as a cross build, because the host cannot execute OHOS
binaries (the ohos-local profile sets tools.build.cross_building:can_run to
False); the CI worker builds natively and does execute them. testtrap is never
executed - its -DTESTING handler returns instead of abort()ing, so it has no
deterministic terminal state (see the script header for the measurement).
"""
import os
import shutil

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.build import can_run
from conan.tools.env import VirtualBuildEnv
from conan.tools.files import (
    apply_conandata_patches,
    copy,
    export_conandata_patches,
    get,
)
from conan.tools.layout import basic_layout


class IfmailConan(ConanFile):
    name = "ifmail"
    version = "2.14tx8.10"
    description = (
        "ifmail: FidoNet transport and gateway suite for Unix - ifcico "
        "mailer (FTSC/EMSI/Wazoo/Hydra/Zmodem/binkp over serial and TCP), "
        "ifgate mail/news gateways (ifmail, ifnews, iftoss, ifpack, "
        "ifunpack) and the nodelist index tools"
    )
    # Debian's .dsc declares GPL; upstream's own notice (LSM "Copying-policy:
    # Free" plus the header in CONFIG) is freeware-with-attribution for the
    # original Crosser code, while the ifcico-3.0.cm modules it incorporates
    # are GPL. GPL-2.0-or-later is the combined-work SPDX id Debian uses.
    license = "GPL-2.0-or-later"
    homepage = "http://ifmail.sourceforge.net/"
    url = "https://gitcode.com/OpenHarmonyPCDeveloper/build_in_harmonyos"
    topics = ("fidonet", "ftn", "mailer", "gateway", "echomail", "cli")

    package_type = "application"
    settings = "os", "compiler", "build_type", "arch"

    # Executables per source directory (see the module docstring).
    _BINDIR_OBJS = {
        "ifcico": ("ifcico", "ifindex", "ifinfo", "ifreq", "ifroute",
                   "nlpatch", "nlookup"),
        "ifgate": ("ifmail", "ifnews", "iftoss", "ifpack", "ifunpack",
                   "ifstat"),
        "iflib": ("make_new_ref",),
    }

    def export_sources(self):
        export_conandata_patches(self)
        # Upstream -DTESTING fixtures + runner (R51 step 2).
        copy(self, "uptests/*", self.recipe_folder, self.export_sources_folder)

    def requirements(self):
        # OHOS has no system ndbm. gdbm's compat layer provides <ndbm.h> plus
        # libgdbm_compat, which is exactly the API ifmail uses (dbm_open /
        # dbm_store / dbm_fetch / dbm_firstkey / dbm_nextkey / dbm_delete in
        # iflib/ref.c, ifgate/{msgidbm,ifdbm,nlindex,nodecheck}.c and
        # ifcico/nlindex.c).
        # gdbm/1.23 is the registry build configured --enable-libgdbm-compat
        # (static, verified by inspecting the downloaded package tree:
        # include/{ndbm.h,dbm.h} + lib/libgdbm_compat.a). gdbm/1.24 is built
        # --disable-libgdbm-compat and ships no ndbm.h at all, so it cannot
        # back this package.
        self.requires("gdbm/1.23")

    def build_requirements(self):
        # iflib/parsedate.y, ifcico/flagexp.y + flaglex.l and
        # ifcico/ftscprod.c (awk) are generated at build time; the OHOS CI
        # worker has no system yacc/lex/awk, so pull them through the build
        # profile. A macOS dev box simulating the worker with an OHOS-settings
        # profile uses its host tools instead (user.build:flex_bison_native
        # conf - same pattern as libidl2/0.8.14, seexpr/3.0.1, scws/1.2.3).
        if self.settings_build.os == "OHOS" and not self.conf.get(
                "user.build:flex_bison_native", default=False):
            self.tool_requires("bison/3.8.2")
            self.tool_requires("flex/2.6.4.2")
            self.tool_requires("awk/20251225")

    def validate(self):
        # R32: OHOS must be matched alongside Linux, never `== "Linux"`.
        if self.settings.os not in ("Linux", "OHOS"):
            raise ConanInvalidConfiguration(
                f"ifmail is not validated for {self.settings.os}"
            )

    def layout(self):
        basic_layout(self)

    def source(self):
        # The tarball's single root directory is ifmail-2.14tx8.10.orig.
        get(self, **self.conan_data["sources"], strip_root=True)

    def generate(self):
        # Puts the tool_requires (bison/flex/awk) on PATH for build().
        VirtualBuildEnv(self).generate()

    @staticmethod
    def _resolve_shell():
        """Pick a shell that exists on the machine running the build.

        OHOS has no /bin/sh, and CONFIG sets SHELL=/bin/sh, so make must be
        overridden (R5). CONFIG_SHELL is the repo-wide convention, but the
        value has to exist here: the CI worker has the hnp bash, while a dev
        box simulating the worker with an OHOS-settings profile does not
        (make dies with "SHELL: No such file or directory" before compiling
        anything).
        """
        for cand in (os.environ.get("CONFIG_SHELL"),
                     "/data/service/hnp/bin/bash",
                     shutil.which("bash"),
                     "/bin/bash", "/bin/sh"):
            if cand and os.path.exists(cand):
                return cand
        return "sh"

    def _make_args(self):
        """Make command-line overrides replacing CONFIG's 1999 Linux defaults.

        R33: every toolchain value comes from Conan conf, never from shell
        environment variables, because $CC/$CFLAGS are empty on CI workers.
        """
        # tools.build:compiler_executables is one dict-valued conf; the ":c"
        # sub-key form raises "does not exist in configuration list" on conan
        # 2.29.1, so read the dict and pick the entries out of it (same shape
        # as run-parts/5.23.2, rvvm/0.6, ren/1.0 in this repo).
        compilers = self.conf.get("tools.build:compiler_executables",
                                  default={}, check_type=dict)
        cc = compilers.get("c", "clang")
        ar = compilers.get("ar", "llvm-ar")
        ranlib = compilers.get("ranlib", "llvm-ranlib")
        gdbm_root = self.dependencies["gdbm"].package_folder
        pkg = self.package_folder
        shell = self._resolve_shell()

        cflags = " ".join((
            "-O2",
            # parsedate.y / gettime.c only include <time.h> under this knob.
            "-DDO_NEED_TIME",
            "-I" + os.path.join(gdbm_root, "include"),
        ))
        # CONFIG's Linux LIBS is "-lgdbm -lresolv": OHOS musl folds the
        # resolver into libc and ships no libresolv, and the ndbm compat
        # layer lives in libgdbm_compat (link order matters: compat first).
        libs = " ".join((
            "-L" + os.path.join(gdbm_root, "lib"),
            "-lgdbm_compat", "-lgdbm",
        ))
        # Compile-time path defaults. CONFIG bakes each of them into the
        # binaries as a -D string, so they are pointed at the package folder
        # to keep a fresh install self-consistent (rgb/1.1.1 pattern). A site
        # config passed with -I overrides logfile/debugfile/inbound/outbound/
        # public/nodelist/database at runtime; MAPTABDIR (charset tables) and
        # CONFIGFILE have no runtime override other than -I, which is why the
        # data is packaged exactly where MAPTABDIR points.
        dirs = {
            "BINDIR": os.path.join(pkg, "bin"),
            "CONFIGFILE": os.path.join(pkg, "etc", "ifmail", "config"),
            "MAPTABDIR": os.path.join(pkg, "share", "ifmail", "maptabs"),
            "DEBUGFILE": os.path.join(pkg, "var", "log", "ifmail", "ifdebug"),
            "LOGFILE": os.path.join(pkg, "var", "log", "ifmail", "iflog"),
            "LOCKDIR": os.path.join(pkg, "var", "lock"),
            "PUBDIR": os.path.join(pkg, "var", "spool", "uucppublic"),
            "NEWSSPOOL": os.path.join(pkg, "var", "spool", "news"),
            # CONFIG documents that FAKEDIR needs the trailing slash.
            "FAKEDIR": os.path.join(pkg, "var", "spool", "ifmail", "fake") + "/",
        }
        args = [
            'CC="%s"' % cc,
            'AR="%s"' % ar,
            'RANLIB="%s"' % ranlib,
            'CFLAGS="%s"' % cflags,
            'LIBS="%s"' % libs,
            'YACC="bison -y"',
            'LEX="flex"',
            'AWK="awk"',
            'SHELL="%s"' % shell,
            # po/ would need msgfmt-generated catalogs plus libintl; NLS only
            # localises interactive messages, so it stays off (documented as a
            # non-core optional feature in notes.md, still path A).
            "USE_NLS=no",
            # Keeps the MSGID <-> Message-ID reference db (iflib/ref.c) and the
            # make_new_ref tool, both of which need the ndbm layer above.
            "REFERENCES_MSC96=yes",
        ]
        args.extend('%s="%s"' % (k, v) for k, v in sorted(dirs.items()))
        # R9 / E525: -j1. GNU make >= 4.4 drives its jobserver through a FIFO,
        # which HMDFS does not support, and parallel sub-makes add fork
        # pressure on the constrained worker.
        args.append("-j1")
        return " ".join(args)

    def _upstream_tests(self, args, src):
        """R51 step 2: build and run the upstream -DTESTING self-tests."""
        self.run("make -C iflib testconf testscan testrfcaddr %s" % args,
                 cwd=src)
        if not can_run(self):
            # can_run() honours tools.build.cross_building:can_run, which the
            # ohos-local dev profile sets to False: conan-verify passes that
            # profile for BOTH -pr:h and -pr:b, so cross_building() alone is
            # False on a macOS dev box while the binaries are still OHOS ELF
            # and cannot execute here. The native OHOS CI worker reports
            # can_run=True and does execute them.
            self.output.warning(
                "upstream self-tests built but NOT executed: can_run() is "
                "False in this configuration (OHOS binaries cannot run on this "
                "host). The native OHOS CI worker executes them."
            )
            return
        shell = self._resolve_shell()
        script = os.path.join(src, "uptests", "run_upstream_tests.sh")
        work = os.path.join(self.build_folder, "uptests-work")
        self.run('"%s" "%s" "%s"' % (shell, script, work), cwd=src)


    def build(self):
        apply_conandata_patches(self)
        src = self.source_folder
        args = self._make_args()
        # The top-level Makefile loops over DIRS = iflib ifgate ifcico (po/ is
        # dropped by USE_NLS=no); command-line overrides reach the sub-makes
        # through MAKEFLAGS.
        self.run("make all %s" % args, cwd=src)
        self._upstream_tests(args, src)

    def package(self):
        src = self.source_folder
        pkg = self.package_folder
        for subdir, names in self._BINDIR_OBJS.items():
            for name in names:
                copy(self, name, os.path.join(src, subdir),
                     os.path.join(pkg, "bin"), keep_path=False)

        # Charset translation tables - MAPTABDIR is baked into the binaries,
        # so they must land exactly there.
        copy(self, "*", os.path.join(src, "misc", "maptabs"),
             os.path.join(pkg, "share", "ifmail", "maptabs"))

        # Sample site config and area list. They are installed as *.sample on
        # purpose: upstream's misc/config includes /etc/ifmail/passwds and
        # points every spool at /var/spool/ifmail, none of which exists on a
        # fresh OHOS system, so making it the live CONFIGFILE would turn every
        # invocation without -I into a confusing rc=65.
        etc = os.path.join(pkg, "etc", "ifmail")
        os.makedirs(etc, exist_ok=True)
        for sample in ("config", "Areas"):
            copy(self, sample, os.path.join(src, "misc"), etc)
            os.rename(os.path.join(etc, sample),
                      os.path.join(etc, sample + ".sample"))

        # Man pages (upstream `make man` installs them with -o man -g man,
        # which needs root; copy them instead).
        for subdir in ("ifcico", "ifgate", "iflib"):
            copy(self, "*.8", os.path.join(src, subdir),
                 os.path.join(pkg, "share", "man", "man8"), keep_path=False)
            copy(self, "*.3", os.path.join(src, subdir),
                 os.path.join(pkg, "share", "man", "man3"), keep_path=False)
        copy(self, "ifcico.8.fr", os.path.join(src, "ifcico"),
             os.path.join(pkg, "share", "man", "fr", "man8"), keep_path=False)

        # Docs. The tarball ships no COPYING file: the licence notice lives in
        # the CONFIG header and in Credits.TX/LSM, so those travel with the
        # package instead.
        doc = os.path.join(pkg, "share", "doc", "ifmail")
        for name in ("README", "README.first", "README.charset",
                     "Changelog.TX", "Credits.TX", "LSM", "LSM.TX"):
            copy(self, name, src, doc, keep_path=False)
        copy(self, "CONFIG", src, doc, keep_path=False)

        # Runtime directories the baked defaults point at. Without them the
        # freopen(debugfile) in readconfig() and any lock/spool write fail on a
        # fresh install; a packaged file keeps the directories in the tarball.
        for rel in (os.path.join("var", "log", "ifmail"),
                    os.path.join("var", "lock"),
                    os.path.join("var", "spool", "uucppublic"),
                    os.path.join("var", "spool", "news"),
                    os.path.join("var", "spool", "ifmail", "fake")):
            keep = os.path.join(pkg, rel)
            os.makedirs(keep, exist_ok=True)
            with open(os.path.join(keep, ".keep"), "w", encoding="utf-8") as fh:
                fh.write("")

    def package_info(self):
        # Application package: no headers, no libraries to propagate
        # (iflib/utlib.a is an internal convenience archive and is not
        # installed). gdbm is linked statically from the registry build, so
        # nothing extra is needed at runtime.
        self.cpp_info.bindirs = ["bin"]
        self.cpp_info.libdirs = []
        self.cpp_info.includedirs = []
