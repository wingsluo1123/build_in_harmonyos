#!/usr/bin/env python3
"""Conan recipe — rolo 021 (Autotools, in-source).

rolo (https://github.com/libvc/rolo) is a text-based (vCard) contact
management program with an ncurses front end.  Upstream ships only
configure.ac/Makefile.am (no generated configure).  build() does NOT run
autoreconf (ninth strategy, 2026-10-14): this runner has no perl and no
autoconf package, and the ohpcd automake/1.18 recipe declares no
requirements (audited: requirements() is pass), so no Conan node provides
autoreconf at all — the eighth-cycle "drop the bash prefix" fix only
changed the calling convention while the binary stayed absent
(/bin/sh: autoreconf: inaccessible or not found).  Adding a Conan
autoconf edge would drag CCI m4/1.4.19 back into the graph (repo
autoconf/2.72 requires + tool_requires m4; CCI-first runners resolve it
to the recipe that dies at configure[139]), and vendoring autoconf
sources is equally blocked (all of autoconf/automake/aclocal are perl
scripts; the merged-bin listing shows no perl).  So every configure
generation step is eliminated: libvc is compiled directly (Conan
bison/2.7 or native yacc + vendored flex + cc + ar, see _build_libvc),
unac is compiled directly too (eleventh strategy: the Debian orig
tarball ships no configure and the runner has no autoreconf, so $CC
-c unac.c + ar rcs with a build-time probed config.h, see
_build_unac_direct), and rolo itself is compiled directly (hand-written
config.h limited to the PACKAGE_* macros its sources actually use — only
main.c reads config.h, only PACKAGE_STRING — plus cc + link against the
two private prefixes and ncursesw6-config flags; upstream suite runs via
sh test/run-tests straight into make_check.log).  One tool edge:
bison/2.7 for YACC (ohpcd-only, zero-dep, OHOS-proven); the graph holds exactly one requires (ncurses/6.6, leaf).

Build layout is deliberately in-source (folders.build = "."): the upstream
test driver test/run-tests resolves its fixtures relative to its own
location (../configure.ac, contacts.vcf, ../src/rolo), which only exists
when configure/make run inside the source tree.

Upstream hard requirements (configure.ac):
  libvc (AC_CHECK_LIB, fatal) / ncursesw + menuw (fatal) /
  glib-2.0 + unac (PKG_CHECK_MODULES, fatal).
shunit2 only gates the unit tests (WARNING when absent, suite skipped).

Dependency note: libvc has no recipe in this repository yet, so it is
vendored inside this recipe — the official libvc v013 tag tarball is
fetched (hash-pinned below) and built static into a private build-folder
prefix before rolo configures.  No conan requires on libvc, so dependency
resolution never blocks; rolo links the private static lib.  See notes.md.

glib-2.0 (PKG_CHECK_MODULES, fatal) is NOT consumed as a Conan package:
rolo uses exactly one trivial glib API — g_utf8_strlen() for menu column
width compensation in src/entry.c (3 calls) — so build() rewrites the
sources in place (exact-match, count-verified, fail closed): configure.ac
drops the GLIB PKG_CHECK_MODULES block and the $GLIB_LIBS/$GLIB_CFLAGS
wiring, entry.c drops #include <glib.h> for a local rolo_utf8_strlen()
with identical NUL-terminated code-point counting semantics.  Rationale in
notes.md problem #11: every glib revision in this repo has manifest status
built (no ohpcd binary), so any requires forces a from-source meson build
plus its libffi chain, and every autotools node in that chain dies at
configure[139] on runners without HNP bash (this round: libffi/3.4.4
package e80f2bcb, same signature as the m4 deaths).

unac (PKG_CHECK_MODULES, fatal) exists in this repository (unac/1.8.0)
but is vendored too: it never published a binary (manifest status built),
so every consumer triggers its source build, whose
tool_requires("automake/1.18") + tool_requires("libtool/2.5.4") resolve
off-repo (libtool/2.5.4 does not even exist in archives/) and — via the
CCI automake requires/tool_requires autoconf, which requires/tool_requires
m4 — drag CCI m4/1.4.19 into the graph, whose source build dies at
configure[139] (CONFIG_SHELL=/data/service/hnp/bin/bash inaccessible,
Error 127, package 579a4b17, two preflight rounds).  Vendoring the same
official Debian orig tarball (same URL/sha256 as the unac recipe) into a
private static prefix removes that whole subtree; rolo consumes it via
CPPFLAGS/LDFLAGS plus PKG_CONFIG_PATH for its unac.pc.  The unac recipe's
two aarch64 int->size_t patches (real stack corruption) are applied
equivalently by exact-match, count-verified replacement.  Eleventh
strategy (2026-10-14): the orig tarball ships NO configure
(tenth-cycle preflight file-list evidence) and the runner has no
autoreconf, so no configure is generated at all — unac is built
directly ($CC -c unac.c + ar rcs; the 13000-line unac.c already
embeds the Unicode tables, only the unaccent CLI needs autotools),
with a build-time probed config.h and a consumer-symbol link gate
(see _build_unac_direct).
"""
import hashlib
import glob
import json
import os
import re
import shutil
import time
import urllib.error
import urllib.request

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.env import Environment
from conan.tools.files import apply_conandata_patches, copy, export_conandata_patches, get
from conan.tools.gnu import AutotoolsDeps, AutotoolsToolchain, PkgConfigDeps
from conan.tools.layout import basic_layout


# Upstream test inventory (audited from the v021 tag tarball, see
# test_package/MANIFEST.yml): test/run-tests defines 4 shunit2 test
# functions.  This constant is the audit total, NOT a result.
UPSTREAM_TEST_TOTAL = 4

# shunit2 single-file runner used to execute the upstream suite when the
# build machine does not provide one.  Official source, hash pinned
# (downloaded and hashed 2026-10-13).
# Ordered mirror list (official last as fallback, same sha256): the
# raw.githubusercontent.com fetch below retries each entry in order, so a
# single-domain timeout no longer fails the build.
SHUNIT2_URLS = [
    "https://gh-proxy.com/https://raw.githubusercontent.com/kward/shunit2/v2.1.8/shunit2",
    "https://raw.githubusercontent.com/kward/shunit2/v2.1.8/shunit2",
]
SHUNIT2_URL = SHUNIT2_URLS[-1]
SHUNIT2_SHA256 = "d8f8fb2caff6e3ff77cea8837d1ae5e4fed857fe2948f9859f24f72c43814c28"

# libvc (vCard parsing library, https://github.com/libvc/libvc) — hard
# rolo dependency (AC_CHECK_LIB(vc, vc_new), fatal).  No recipe exists in
# this repository, so the official v013 tag tarball is vendored: fetched
# and built static into a private build-folder prefix in build().
# Official GitHub tag archive, downloaded and hashed 2026-10-13
# (22258 bytes).
# Ordered mirror list (ci/conan/build_and_test.sh GitHub mapping:
# gh-proxy first, official last as fallback, same sha256).  Conan get()
# tries each entry in order, so a single-domain timeout (this round:
# github.com connect timeout x3) no longer fails the build.
LIBVC_URLS = [
    "https://gh-proxy.com/https://github.com/libvc/libvc/archive/refs/tags/v013.tar.gz",
    "https://github.com/libvc/libvc/archive/refs/tags/v013.tar.gz",
]
LIBVC_URL = LIBVC_URLS[-1]
LIBVC_SHA256 = "a43bf49ff2b9e17cf7e332f3aa9f218c46782400aa848e6af4589e6b244821c2"

# unac (accent-stripping library, https://www.nongnu.org/libunac/) — hard
# rolo dependency (PKG_CHECK_MODULES([UNAC],[unac]), fatal).  Vendored for
# the reason in the module docstring: same URL/sha256 as
# archives/u/unac/1.8.0/conandata.yml (Debian orig tarball).
UNAC_URL = "https://deb.debian.org/debian/pool/main/u/unac/unac_1.8.0.orig.tar.gz"
UNAC_SHA256 = "29d316e5b74615d49237556929e95e0d68c4b77a0a0cfc346dc61cf0684b90bf"

# Vendored yacc/lex toolchain for libvc (eighth strategy, 2026-10-14):
# libvc's configure fatally requires LEX + YACC, but the preflight runner
# provides neither natively (YACC=MISSING LEX=MISSING, HNP mount
# Permission denied) and no Conan bison/flex edge survives CCI-first
# runners (every available version resolves to a CCI recipe that pulls
# m4, or pulls m4 itself; flex/bison also need m4 at RUNTIME).  The
# seventh strategy (GNU m4+bison+flex vendoring) unblocked m4 but died
# twice in bison 3.8.2's own lib/ build (make -C lib Error 2): bison's
# lib/ bundles a gnulib generation that has neither freadahead.c nor
# freadptr.c/freadseek.c, so the musl patcher is a no-op there and the
# real failure is an unidentified third file.  So YACC is now provided
# by Berkeley byacc 2.0 instead of GNU bison: libvc's vc_parse.y is pure
# POSIX yacc (only %token/%start/actions, YYACCEPT/yyerrok, no bison
# extensions, audited from the v013 tarball), byacc is 14 plain C files
# with no gnulib, no C++ and negligible memory use, and it installs a
# program literally named `yacc`, which satisfies AC_PROG_YACC plus the
# AC_CHECK_PROG(have_yacc) gate.  m4 is still vendored first (flex
# invokes it at generation time) and flex stays (vc_scan.l needs flex
# %option/%x, bootstrap via its shipped scan.c).  Release tarballs ship
# configure, so no autoreconf and no new Conan graph nodes.  Only used
# when native yacc/lex are absent; native binaries are preferred.
M4_URLS = [
    "https://mirrors.tuna.tsinghua.edu.cn/gnu/m4/m4-1.4.19.tar.gz",
    "https://mirrors.ustc.edu.cn/gnu/m4/m4-1.4.19.tar.gz",
    "https://mirrors.aliyun.com/gnu/m4/m4-1.4.19.tar.gz",
    "https://ftp.gnu.org/gnu/m4/m4-1.4.19.tar.gz",
]
M4_URL = M4_URLS[-1]
M4_SHA256 = "3be4a26d825ffdfda52a56fc43246456989a3630093cced3fbddf4771ee58a70"
BYACC_URL = "https://invisible-island.net/archives/byacc/byacc-2.0.tgz"
BYACC_SHA256 = "fb23cfdcc4bb7ac8b52ebbf89c5e150e6e26e3c01e13ca9aca148173ab9bffdd"
# NOTE (2026-10-14, 12th round): the former first entry
# (mirrors.tuna.tsinghua.edu.cn/gnu/flex/...) is REMOVED, not reordered.
# flex is not a GNU project, so that path 404s on EVERY build (preflight
# evidence this round: WARN Not found + retry before the gh-proxy fetch);
# each miss costs a full fetch cycle ahead of the memory-critical flex
# configure below.  gh-proxy first, official last as fallback, same sha256.
FLEX_URLS = [
    "https://gh-proxy.com/https://github.com/westes/flex/releases/download/v2.6.4/flex-2.6.4.tar.gz",
    "https://github.com/westes/flex/releases/download/v2.6.4/flex-2.6.4.tar.gz",
]
FLEX_URL = FLEX_URLS[-1]
FLEX_SHA256 = "e87aae032bf07c26f85ac0ed3250998c37621d95f8bd748b31f15b33c45ee995"


class RoloConan(ConanFile):
    name = "rolo"
    version = "021"
    description = "rolo: text-based (vCard) contact management software with an ncurses interface"
    license = "GPL-2.0-or-later"
    homepage = "https://github.com/libvc/rolo"
    url = "https://gitcode.com/OpenHarmonyPCDeveloper/build_in_harmonyos"

    package_type = "application"

    settings = "os", "compiler", "build_type", "arch"

    def export_sources(self):
        export_conandata_patches(self)

    def validate(self):
        # R32: platform check must cover OHOS, never == "Linux" alone.
        if str(self.settings.os) not in ("Linux", "OHOS"):
            raise ConanInvalidConfiguration(
                "rolo upstream targets POSIX/curses systems, built here for "
                "Linux/OHOS only, got os=%s" % self.settings.os
            )

    def requirements(self):
        # ncursesw (wide-char UI) + menuw (index menu); ncurses/6.6 builds
        # with --enable-widec and ships menuw (see its notes.md).  Leaf
        # node (no requires/tool_requires of its own), binary-hit.
        self.requires("ncurses/6.6")
        # PKG_CHECK_MODULES([GLIB],[glib-2.0]) in configure.ac is satisfied
        # WITHOUT a conan requires (see module docstring + notes.md #11):
        # build() rewrites configure.ac/src/entry.c in place to drop the
        # glib edge (single trivial API reimplemented locally).  No glib
        # node means no meson source build and no libffi chain on runners
        # without HNP bash/clang.  pcre2/zlib only mattered through glib.
        # PKG_CHECK_MODULES([UNAC],[unac]) in configure.ac — vendored, see
        # module docstring: repo unac/1.8.0 never published a binary and its
        # tool_requires("libtool/2.5.4") names a version absent from this
        # repo, so requiring it drags the CCI automake -> autoconf -> m4
        # chain into the graph, which dies at configure[139] on runners
        # without HNP bash.  No conan requires; build() compiles the
        # official tarball into a private prefix and points PKG_CONFIG_PATH
        # at its unac.pc.
        # Fifth-strategy-cycle note (2026-10-14): the previous
        # libffi/3.5.2 override is REMOVED.  Re-reading the preflight log
        # shows the failure domain moved: the m4 chain is gone (unac
        # vendoring worked — no m4/libtool-2.5.4 nodes), and glib/2.84.0.2
        # now source-builds and dies in meson compiler detection
        # (/data/service/hnp/bin/clang missing, HNP mount Permission
        # denied).  The override changed glib's package ID away from its
        # canonical libffi/3.4.4 leg (status published, has ohpcd binary)
        # to libffi/3.5.2 (status built, no binary), forcing TWO source
        # builds (libffi + glib) instead of letting both hit binaries.
        # Subtraction route: declare no libffi edge at all and let glib
        # resolve its canonical leg.
        # libvc (AC_CHECK_LIB(vc, vc_new), fatal) is vendored from the
        # official v013 tarball into a private prefix in build() — no
        # conan requires (no libvc recipe exists in this repository).

    def build_requirements(self):
        # Tenth-strategy-cycle note (2026-10-14): ONE tool_requires —
        # bison/2.7 for YACC.  The ninth cycle's private byacc 2.0 built
        # and passed its `-V` smoke but dies at libvc generation time
        # with `yacc: f - cannot open "action_file"` (byacc temp-file
        # creation inside libvc-src/src, opaque on this runner).  bison
        # 2.7 is a DIFFERENT route, not a retry of byacc: it is an
        # ohpcd-only version (CCI has no 2.7, so no CCI m4 chain — unlike
        # bison/3.8.2 which sc/7.16 proved drags conancenter m4 and dies
        # at configure[139] without HNP bash), declares zero
        # requirements (audited: no requires/tool_requires at all, so no
        # m4 edge), and is OHOS-proven (manifest status passed, 293/293
        # upstream tests on a real device with 9 OHOS patches).  LEX
        # stays privately vendored (flex 2.6.4 built and installed clean
        # this round: libfl.a installed, ldconfig warning harmless).
        # Autoreconf stays eliminated (ninth-cycle rationale unchanged).
        self.tool_requires("bison/2.7")
        self._log_tool_landscape()
        self.output.info("rolo: tool edge bison/2.7 (YACC); "
                         "lex still vendored privately when native missing")
        # Historical note (cycles 2-4, kept for audit): m4/1.4.19 was chased
        # through RREV pins, flex downgrades and unac vendoring; the constant
        # puller chain (unac -> CCI automake -> CCI autoconf -> CCI m4, plus
        # bison/flex requires on m4) is documented in notes.md #7-#9.  All
        # of those edges are gone now (no unac/bison/flex/m4/automake/libtool
        # nodes at all).

    @staticmethod
    def _tool_search_dirs():
        """Extra directories probed for native build tools (beyond PATH).

        The preflight runner's HNP toolchain may live in per-package
        directories rather than a merged bin/, and the merged bin/ itself
        is inaccessible on some runners, so glob both layouts.  Never
        raises.
        """
        found = []
        try:
            for directory in ("/data/service/hnp/bin",
                              "/storage/Users/currentUser/usr/local/bin",
                              "/usr/local/bin"):
                try:
                    if os.path.isdir(directory) and directory not in found:
                        found.append(directory)
                except Exception:
                    pass
            for pattern in ("/data/service/hnp/*/bin",
                            "/data/service/hnp/*/*/bin"):
                try:
                    for directory in sorted(glob.glob(pattern)):
                        try:
                            if os.path.isdir(directory) \
                                    and directory not in found:
                                found.append(directory)
                        except Exception:
                            pass
                except Exception:
                    pass
        except Exception:
            pass
        return found

    @staticmethod
    def _native_probe(candidates, extra_dirs=()):
        """Return an absolute executable path for the first candidate found.

        Searches PATH plus the HNP/Harmonybrew tool directories (merged
        bin/ and per-package */bin layouts).  Never raises (probe failures
        just mean 'not found').
        """
        search_dirs = list(extra_dirs) + RoloConan._tool_search_dirs()
        try:
            for cand in candidates:
                if os.path.isabs(cand):
                    if os.path.isfile(cand) and os.access(cand, os.X_OK):
                        return cand
                    continue
                found = shutil.which(cand)
                if found:
                    return found
                for directory in search_dirs:
                    candidate = os.path.join(directory, cand)
                    if os.path.isfile(candidate) \
                            and os.access(candidate, os.X_OK):
                        return candidate
        except Exception:
            return None
        return None

    def _log_tool_landscape(self):
        """Log ground truth about device tool availability (evidence).

        Bounded directory listings plus per-tool resolution, so the next
        preflight log shows exactly what the runner provides instead of
        forcing another round of guessing.  Never raises.
        """
        try:
            for root in ("/data/service/hnp",
                         "/storage/Users/currentUser/usr/local/bin",
                         "/usr/local/bin"):
                try:
                    if os.path.isdir(root):
                        entries = sorted(os.listdir(root))[:40]
                        self.output.info("rolo: ls %s (%d shown): %s"
                                         % (root, len(entries),
                                            " ".join(entries)))
                    else:
                        self.output.info("rolo: %s: not a directory" % root)
                except Exception as exc:
                    self.output.info("rolo: ls %s failed: %r" % (root, exc))
            try:
                extra = RoloConan._tool_search_dirs()
                self.output.info("rolo: tool search dirs (%d): %s"
                                 % (len(extra), ":".join(extra[:20])))
            except Exception as exc:
                self.output.info("rolo: search-dir probe failed: %r" % exc)
            for label, names in (
                    ("yacc", ("bison", "yacc", "byacc")),
                    ("lex", ("flex", "lex")),
                    ("automake", ("aclocal", "automake")),
                    ("libtool", ("libtoolize", "libtool", "glibtoolize")),
                    ("autoconf", ("autoconf", "autoreconf", "autoheader",
                                  "autom4te")),
                    ("perl", ("perl",)),
                    ("m4", ("m4",)),
                    ("archive", ("ar", "llvm-ar", "ranlib")),
                    ("pkgconfig", ("pkg-config", "pkgconf")),
                    ("help2man", ("help2man",))):
                try:
                    hit = self._native_probe(names)
                    self.output.info("rolo: native %s: %s"
                                     % (label, hit or "MISSING"))
                except Exception as exc:
                    self.output.info("rolo: native %s probe error: %r"
                                     % (label, exc))
        except Exception as exc:
            self.output.warning("rolo: tool landscape log failed: %r" % exc)

    def layout(self):
        # In-source build: test/run-tests locates ../configure.ac,
        # contacts.vcf and ../src/rolo relative to itself.
        basic_layout(self)
        self.folders.build = "."
        self.folders.generators = os.path.join(".", "conan")

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def generate(self):
        # Provides CC/CFLAGS/CONFIG_SHELL for the manual configure/make
        # invocations in build() (R33: no bare ${CC} from the shell).
        tc = AutotoolsToolchain(self)
        tc.configure_args.append("--prefix=/")
        # config.guess predates HarmonyOS recognition; pin the triplet
        # explicitly (same approach as the merged alpine recipe).
        triplet = "%s-unknown-linux-gnu" % self._machine(str(self.settings.arch))
        tc.configure_args.append("--build=%s" % triplet)
        tc.configure_args.append("--host=%s" % triplet)
        env = tc.environment()
        # True-machine fix (mdk/1.3.1 precedent): the repo profile pins CC
        # to /data/service/hnp/bin/clang, which is inaccessible on runners
        # where the HNP mount reports Permission denied (this round:
        # vendored m4 configure picks that CC and dies with "C compiler
        # cannot create executables", Error 77).  Probe the configured
        # compiler and reuse it only when runnable; otherwise fall back to
        # a PATH-discovered compiler.  Only CC/CXX are overridden; all
        # flags (CFLAGS/LDFLAGS/etc.) are preserved untouched (R33).
        _cc = self._resolve_compiler("c")
        _cxx = self._resolve_compiler("cpp")
        if _cc:
            env.define("CC", _cc)
        if _cxx:
            env.define("CXX", _cxx)
        self.output.info("rolo compilers: CC=%s CXX=%s" % (_cc, _cxx))
        # E266 (c-ares/babeltrace/mdk precedent): OHOS SDK lld links
        # libxml2 from SDK llvm/lib; the worker default search path misses
        # it so configure reports "C compiler cannot create executables".
        # Prepend SDK llvm/lib when present; never touches flags/test scope.
        _llvm_lib = "/data/service/hnp/ohos-sdk.org/ohos-sdk_26.0.0.18/ohos/native/llvm/lib"
        if not os.path.isdir(_llvm_lib):
            try:
                _cands = sorted(glob.glob("/data/service/hnp/ohos-sdk.org/*/ohos/native/llvm/lib"))
                _llvm_lib = _cands[0] if _cands else ""
            except Exception:
                _llvm_lib = ""
        if _llvm_lib:
            try:
                env.prepend_path("LD_LIBRARY_PATH", _llvm_lib)
                self.output.info("rolo LD_LIBRARY_PATH prepend: %s" % _llvm_lib)
            except Exception as exc:
                self.output.warning("rolo LD_LIBRARY_PATH prepend failed: %r" % exc)
        else:
            self.output.info("rolo LD_LIBRARY_PATH: no SDK llvm/lib found, skipping")
        tc.generate(env=env)
        # No PKG_CHECK_MODULES packages remain as Conan deps (glib dropped
        # in build(), unac.pc comes from the vendored private prefix via an
        # inline PKG_CONFIG_PATH on the configure command below, not from
        # Conan deps).  PkgConfigDeps is kept as a no-op for forward
        # compatibility.
        PkgConfigDeps(self).generate()
        # -L/-l flags for AC_CHECK_LIB(ncursesw/menuw) probes.
        AutotoolsDeps(self).generate()
        # NOTE (2026-10-14, #33): no rolo_pkgconfig save_script anymore.
        # The Environment save_script emitted conan/rolo_pkgconfig.sh whose
        # line 13 calls `printenv`, absent on the true-machine runner
        # (preflight: `rolo_pkgconfig.sh[13]: printenv: inaccessible or
        # not found`).  Its only content (PKG_CONFIG_PATH -> empty
        # generators_folder) is unused: PkgConfigDeps is a no-op and the
        # vendored unac.pc is consumed via explicit -I/-L, so dropping the
        # script changes no flags and removes the printenv gate.

    def build(self):
        apply_conandata_patches(self)
        # HMFS: getcwd(3) is unavailable on some mounts, configure aborts
        # with "working directory cannot be determined"; seed PWD so the
        # shell need not call getcwd() (rancid/adms precedent).
        os.environ["PWD"] = self.source_folder
        # OOM hardening (2026-10-14): route every rm fork to the real
        # system binary, never the Harmonybrew shim that dies with
        # "Out of memory" under pressure.  See _prefer_system_rm.
        self._prefer_system_rm()
        src = self.source_folder
        # NOTE (2026-10-14, #33): conanbuild only.  The former
        # ["conanbuild", "rolo_pkgconfig"] sourced rolo_pkgconfig.sh (see
        # generate()) whose printenv gate fails before any inline PATH
        # hardening runs; all prior vendored steps already use ["conanbuild"].
        env = ["conanbuild"]
        sh = self._good_shell()

        # Drop the glib edge (rewrites src/entry.c in place to use a local
        # rolo_utf8_strlen instead of g_utf8_strlen; the configure.ac edit
        # is kept for audit consistency although no configure is generated
        # anymore).  See notes.md problem #11.
        self._drop_glib_dependency(src)

        # TMPDIR-aware mkstemp templates (see notes.md problem #35):
        # src/add.c + src/edit.c hardcode "/tmp/rolo-XXXXXX", but HMBS
        # runners inject a per-task TMPDIR (/tmp may be read-only), so the
        # edit path (move_and_edit test) can die there.  In-place rewrite,
        # same exact-match discipline as the glib drop.
        self._fix_tmpdir_templates(src)
        # Round-2 correction: round-1 mktemp rewrite was a misdiagnosis
        # (identical failure with it applied); restore driver pristine.
        self._restore_run_tests_tmpdir(src)
        self._ensure_suite_tmpdir()

        shunit2_ok = self._ensure_shunit2(src)

        # Vendored libvc (official v013): no recipe exists in this repo,
        # so build it static into a private build-folder prefix first
        # (direct cc/ar build, no autotools — see _build_libvc).  Returns
        # the prefix; rolo picks it up via the explicit -I/-L flags in
        # _build_rolo_direct (replacing AC_CHECK_LIB(vc) + #include <vc.h>).
        libvc_prefix = self._build_libvc()
        libvc_inc = os.path.join(libvc_prefix, "include")
        libvc_lib = os.path.join(libvc_prefix, "lib")
        for var, flag in (("CPPFLAGS", "-I%s" % libvc_inc),
                          ("CFLAGS", "-I%s" % libvc_inc),
                          ("LDFLAGS", "-L%s" % libvc_lib)):
            prev = os.environ.get(var, "")
            if flag not in prev:
                os.environ[var] = (flag + " " + prev).strip()
        self.output.info("vendored libvc prefix: %s (CPPFLAGS=%s LDFLAGS=%s)"
                         % (libvc_prefix, os.environ.get("CPPFLAGS", ""),
                            os.environ.get("LDFLAGS", "")))

        # Vendored unac (module docstring): same private-prefix pattern
        # (shipped configure when the tarball provides it, else direct
        # cc/ar per the eleventh strategy).  unac.pc lands in
        # <prefix>/lib/pkgconfig; extra link libs (e.g. -liconv, only
        # when probed necessary) thread into the rolo link below.
        unac_prefix, unac_extra_libs = self._build_unac()
        unac_inc = os.path.join(unac_prefix, "include")
        unac_lib = os.path.join(unac_prefix, "lib")
        unac_pc = os.path.join(unac_lib, "pkgconfig")
        for var, flag in (("CPPFLAGS", "-I%s" % unac_inc),
                          ("CFLAGS", "-I%s" % unac_inc),
                          ("LDFLAGS", "-L%s" % unac_lib)):
            prev = os.environ.get(var, "")
            if flag not in prev:
                os.environ[var] = (flag + " " + prev).strip()
        self.output.info("vendored unac prefix: %s (CPPFLAGS=%s LDFLAGS=%s pc=%s)"
                         % (unac_prefix, os.environ.get("CPPFLAGS", ""),
                            os.environ.get("LDFLAGS", ""), unac_pc))

        # rolo itself: direct cc/link build (no autoreconf/configure/make;
        # ninth strategy).  Places src/rolo for the upstream suite, then
        # runs the suite straight into make_check.log.
        self._build_rolo_direct(src, libvc_prefix, unac_prefix,
                                unac_extra_libs)

        # Layer 1: upstream official suite (test/run-tests via sh;
        # 4 shunit2 cases, see test_package/MANIFEST.yml).  ROLO defaults
        # inside run-tests to $CURDIR/../src/rolo (our direct-build
        # binary); shunit2 resolves via the PATH provisioned above.
        # NOTE (2026-10-14, #34): export the ncurses terminfo database
        # inline.  run-tests drives rolo headless as
        # `TERM=dumb rolo -f contacts.vcf`, which needs initscr() to
        # resolve even the dumb entry; ncurses/6.6 ships share/terminfo
        # (2899 entries) and exposes it only via runenv TERMINFO[_DIRS],
        # but this step runs with env=["conanbuild"] so runenv is absent
        # (preflight: `cannot initialize terminal type ($TERM="dumb")`,
        # 1 of 4 failed).  Explicit exports keep upstream TERM untouched.
        # Redirect to a log file so the shunit2 summary can be parsed from
        # a deterministic file source, then replay the log for the record.
        # Forensics for #35 (read-only probes, always exit 0, never gate):
        # records TMPDIR and /tmp writability so the next round can tell a
        # tmpdir failure apart from a curses/libvc failure.
        self.run(
            self._with_util_path(
                "echo \"rolo tmp probe: TMPDIR=${TMPDIR:-<unset>}\"; "
                "ls -ld \"/tmp\" \"${TMPDIR:-/tmp}\" 2>&1; "
                "touch \"/tmp/rolo-wr-probe-$$\" 2>&1 && "
                "{ echo \"rolo tmp probe: /tmp writable\"; "
                "rm -f \"/tmp/rolo-wr-probe-$$\"; } || "
                "echo \"rolo tmp probe: /tmp NOT writable\"; exit 0"),
            cwd=src, env=env)
        terminfo_prefix = self._ncurses_terminfo_exports()
        tmpdir_export = self._suite_tmpdir_export()
        # Deterministic plain shunit2 output on every runner: the pinned
        # 2.1.8 honors SHUNIT_COLOR (none disables ANSI even when tput
        # claims colors); the parser additionally strips ANSI, so either
        # mechanism alone suffices and both together are stable.
        shunit_color = 'export SHUNIT_COLOR="none"; '
        self.run(
            self._with_util_path(
                "%s%s%s\"%s\" test/run-tests > make_check.log 2>&1; "
                "rc=$?; cat make_check.log; exit $rc"
                % (tmpdir_export, shunit_color, terminfo_prefix, sh)),
            cwd=src, env=env)

        # Single deterministic parse of the saved log: shunit2 prints
        # "Ran N tests." plus an "OK" / "FAILED (...)" summary line.
        result = self._parse_shunit2_log(os.path.join(src, "make_check.log"),
                                         shunit2_ok)
        self.output.info("rolo upstream check parsed: %s" % json.dumps(result))
        # Stage machine-readable evidence for test_package/test.sh, which
        # re-emits it as HMBS_UPSTREAM_TEST_RESULT (single source, no
        # guessing, no arithmetic patch-ups).
        evidence_dir = os.path.join(self.package_folder, "share", "doc", "rolo")
        os.makedirs(evidence_dir, exist_ok=True)
        # NOTE: compact single-line JSON — test.sh re-emits this file content
        # as the trailing HMBS_UPSTREAM_TEST_RESULT marker line, which must
        # stay on one physical line for the machine-evidence parser.
        with open(os.path.join(evidence_dir, "upstream-check.json"),
                  "w", encoding="utf-8") as handle:
            json.dump(result, handle, ensure_ascii=False, sort_keys=True)
            handle.write("\n")
        # Stage the ncurses terminfo dir for test_package (build context
        # sees the direct ncurses dep; test_package's transitive lookup
        # resolves None, see preflight WARN pkg=None x2).  Same-machine
        # cache paths are stable between create's build and test phases,
        # so the absolute dir stays valid; test_package verifies isdir
        # before use and fails honestly when absent.
        try:
            _tip = ""
            try:
                _ncp = self.dependencies["ncurses"].package_folder
            except Exception:
                _ncp = ""
            if _ncp:
                _tic = os.path.join(_ncp, "share", "terminfo")
                if os.path.isdir(_tic):
                    _tip = _tic
            with open(os.path.join(evidence_dir, "terminfo-path.txt"),
                      "w", encoding="utf-8") as handle:
                handle.write((_tip + "\n") if _tip else "\n")
            self.output.info("rolo staged terminfo path: %s" % (_tip or "<empty>"))
        except Exception as exc:
            self.output.warning("rolo stage terminfo path failed: %r" % (exc,))
        if result["status"] not in ("passed", "skipped"):
            raise RuntimeError(
                "rolo upstream suite not green: %s (see make_check.log)" % result)

    # src/Makefile.am rolo_SOURCES, audited from the v021 tag tarball.
    _ROLO_SOURCES = (
        "main.c", "index.c", "view.c", "edit.c", "help.c",
        "delete.c", "add.c", "entry.c", "search.c",
    )

    def _write_rolo_config_h(self, cfgdir):
        """Write the minimal config.h that rolo's sources actually consume.

        Audited (temp probe 2026-10-14, full v021 source grep): the ONLY
        config.h consumer is src/main.c (``#if HAVE_CONFIG_H`` /
        ``#include "config.h"`` / ``PACKAGE_STRING``); add.c's VERSION is
        the vCard literal "VERSION:3.0", not a macro; no TU references any
        HAVE_* macro.  Values replicate AC_INIT([rolo],[021],
        [rafael@laboissiere.net]) from configure.ac, i.e. exactly what a
        real configure would emit for PACKAGE_STRING ("rolo 021", asserted
        by upstream test_rolo_version AND consumer case B).  Written into
        the build folder (never the source tree) and wired via
        -DHAVE_CONFIG_H=1 plus -I.  Fails closed on content drift.
        """
        os.makedirs(cfgdir, exist_ok=True)
        path = os.path.join(cfgdir, "config.h")
        content = (
            "/* Generated by rolo/021 conanfile (direct build, no configure).\n"
            "   Values replicate configure.ac AC_INIT([rolo],[021],\n"
            "   [rafael@laboissiere.net]); only main.c consumes config.h\n"
            "   (PACKAGE_STRING), audited 2026-10-14. */\n"
            "#ifndef ROLO_CONFIG_H\n"
            "#define ROLO_CONFIG_H\n"
            '#define PACKAGE_NAME "rolo"\n'
            '#define PACKAGE_TARNAME "rolo"\n'
            '#define PACKAGE_VERSION "021"\n'
            '#define PACKAGE_STRING "rolo 021"\n'
            '#define PACKAGE_BUGREPORT "rafael@laboissiere.net"\n'
            '#define PACKAGE_URL ""\n'
            "#endif\n"
        )
        with open(path, "w", encoding="utf-8") as handle:
            handle.write(content)
        self.output.info("rolo config.h written: %s" % path)
        return cfgdir

    def _ncurses_direct_flags(self):
        """Return (cflags, libs) for direct cc/link against ncurses/6.6.

        Uses the package's own relocated bin/ncursesw6-config script (a
        plain /bin/sh script; the ncurses recipe guarantees its presence
        and HMBS guarantees /bin/sh), so --cflags/--libs encode exactly
        what this static widec build needs (including -ltinfo when the
        build requires it).  -lmenuw is appended by the caller (menu is a
        separate library the config script does not cover).  Verifies
        menu.h resolvability under the returned -I set and the presence of
        a menuw archive; fails closed with listings otherwise.
        """
        import subprocess
        try:
            pkg = self.dependencies["ncurses"].package_folder
        except Exception as exc:
            raise RuntimeError(
                "rolo direct build needs ncurses/6.6 dependency: %r" % exc)
        cfg = os.path.join(pkg, "bin", "ncursesw6-config")
        if not os.path.isfile(cfg):
            try:
                entries = sorted(os.listdir(os.path.join(pkg, "bin")))
            except OSError:
                entries = []
            raise RuntimeError(
                "ncursesw6-config missing (bin holds %s); cannot derive "
                "direct-build flags" % entries)

        def _pick_shell():
            # HMBS guarantees /bin/sh; never exec the config script
            # directly (its shebang interpreter and exec bit are not
            # guaranteed on chmod:0 runners: direct exec dies with
            # FileNotFoundError(2) even when isfile passes).
            for cand in ("/bin/sh", os.environ.get("SHELL", "")):
                if cand and os.path.isfile(cand):
                    return cand
            which_sh = shutil.which("sh")
            if which_sh:
                return which_sh
            return "/bin/sh"
        shell = _pick_shell()
        self.output.info("rolo ncurses config shell: %s" % shell)
        def _run_config(arg):
            try:
                proc = subprocess.run(
                    [shell, cfg, arg], stdout=subprocess.PIPE,
                    stderr=subprocess.STDOUT, timeout=60)
            except Exception as exc:
                raise RuntimeError(
                    "ncursesw6-config %s failed to execute: %r" % (arg, exc))
            out = proc.stdout.decode("utf-8", errors="replace").strip()
            if proc.returncode != 0:
                raise RuntimeError(
                    "ncursesw6-config %s rc=%d: %s"
                    % (arg, proc.returncode, out[:500]))
            return out

        cflags = _run_config("--cflags")
        libs = _run_config("--libs")
        self.output.info("rolo ncurses cflags: %s" % cflags)
        self.output.info("rolo ncurses libs: %s" % libs)
        # menu.h must resolve: check the package include dirs directly
        # (config --cflags normally covers include/, but verify).
        menu_hit = ""
        for inc in (os.path.join(pkg, "include"),
                    os.path.join(pkg, "include", "ncursesw")):
            if os.path.isfile(os.path.join(inc, "menu.h")):
                menu_hit = inc
                break
        if not menu_hit:
            raise RuntimeError(
                "menu.h not found under %s/include (rolo main.c needs "
                "<menu.h>)" % pkg)
        if menu_hit not in cflags:
            cflags = (cflags + " -I%s" % menu_hit).strip()
            self.output.info("rolo ncurses cflags appended menu dir: %s"
                             % menu_hit)
        # menuw archive must exist (we link -lmenuw explicitly).
        libdir = os.path.join(pkg, "lib")
        try:
            entries = sorted(os.listdir(libdir))
        except OSError as exc:
            raise RuntimeError(
                "ncurses lib dir unreadable (%s): %r" % (libdir, exc))
        if not any(n.startswith("libmenuw.") for n in entries):
            raise RuntimeError(
                "no libmenuw.* in ncurses lib dir %s (holds %s)"
                % (libdir, entries))
        if "-lncursesw" not in libs:
            raise RuntimeError(
                "ncursesw6-config --libs lacks -lncursesw: %r" % libs)
        return cflags, libs

    def _ncurses_terminfo_exports(self):
        """Return inline `export TERMINFO[_DIRS]=...; ` for the test shell.

        ncurses/6.6 ships its terminfo database at <pkg>/share/terminfo
        (notes: 2899 entries via tic) and exposes it only through runenv
        (runenv_info TERMINFO/TERMINFO_DIRS).  The upstream suite runs in
        build() with env=["conanbuild"], so runenv is absent and even
        `TERM=dumb` fails at initscr() (`cannot initialize terminal
        type`).  This exports both variables inline to the exact package
        directory (verified isdir, entry count logged); upstream's inline
        `TERM=dumb` is left untouched.  Returns "" with a warning when
        the database is absent (suite then fails honestly, never skipped).
        """
        try:
            pkg = self.dependencies["ncurses"].package_folder
        except Exception as exc:
            self.output.warning(
                "rolo terminfo: no ncurses dependency: %r" % (exc,))
            return ""
        terminfo = os.path.join(pkg, "share", "terminfo")
        try:
            if not os.path.isdir(terminfo):
                self.output.warning(
                    "rolo terminfo: %s not a directory (pkg=%s)"
                    % (terminfo, pkg))
                return ""
            try:
                entries = sum(
                    len(files)
                    for _root, _dirs, files in os.walk(terminfo))
            except Exception:
                entries = -1
            self.output.info(
                "rolo terminfo: %s (%s entries)" % (terminfo, entries))
            return ("export TERMINFO=\"%s\"; "
                    "export TERMINFO_DIRS=\"%s\"; " % (terminfo, terminfo))
        except Exception as exc:
            self.output.warning("rolo terminfo probe failed: %r" % (exc,))
            return ""

    def _build_rolo_direct(self, src, libvc_prefix, unac_prefix,
                             unac_extra_libs=""):
        """Compile + link rolo directly (no autoreconf/configure/make).

        Ninth strategy (2026-10-14): mirrors src/Makefile.am
        (bin_PROGRAMS = rolo, the 9 sources in _ROLO_SOURCES) with profile
        $CC/$CFLAGS plus explicit -I/-L for the two private prefixes and
        the ncurses flags from _ncurses_direct_flags (replacing
        AC_CHECK_LIB(ncursesw/menuw) and PKG_CHECK_MODULES(UNAC); the GLIB
        wiring is already dropped by _drop_glib_dependency).  Links the
        binary to src/rolo inside the source tree because test/run-tests
        resolves ROLO=${ROLO:-$CURDIR/../src/rolo}.  A strict -v gate
        (output must be exactly "rolo 021") fails the build closed on any
        config.h/link skew before the suite runs; test counts still come
        solely from the run-tests log parsed afterwards.
        """
        import subprocess
        libvc_inc = os.path.join(libvc_prefix, "include")
        libvc_lib = os.path.join(libvc_prefix, "lib")
        unac_inc = os.path.join(unac_prefix, "include")
        unac_lib = os.path.join(unac_prefix, "lib")
        for artifact in (os.path.join(libvc_inc, "vc.h"),
                         os.path.join(libvc_lib, "libvc.a"),
                         os.path.join(unac_inc, "unac.h"),
                         os.path.join(unac_lib, "libunac.a")):
            if not os.path.isfile(artifact):
                raise RuntimeError(
                    "rolo direct build prereq missing: %s" % artifact)
        srcs = os.path.join(src, "src")
        for name in self._ROLO_SOURCES:
            if not os.path.isfile(os.path.join(srcs, name)):
                raise RuntimeError(
                    "rolo source drift: missing src/%s (audited v021 set: "
                    "%s)" % (name, self._ROLO_SOURCES))
        cfgdir = self._write_rolo_config_h(
            os.path.join(self.build_folder, "rolo-cfg"))
        objdir = os.path.join(self.build_folder, "rolo-obj")
        os.makedirs(objdir, exist_ok=True)
        nc_cflags, nc_libs = self._ncurses_direct_flags()
        benv = ["conanbuild"]
        for name in self._ROLO_SOURCES:
            obj = os.path.join(objdir, os.path.splitext(name)[0] + ".o")
            self._run_retry(
                "$CC $CFLAGS $CPPFLAGS -DHAVE_CONFIG_H=1 "
                "-I\"%s\" -I\"%s\" -I\"%s\" %s "
                "-c \"src/%s\" -o \"%s\""
                % (cfgdir, libvc_inc, unac_inc, nc_cflags, name, obj),
                cwd=src, env=benv)
        objs = " ".join(
            "\"%s\"" % os.path.join(objdir, os.path.splitext(n)[0] + ".o")
            for n in self._ROLO_SOURCES)
        binary = os.path.join(srcs, "rolo")
        self._run_retry(
            "$CC $LDFLAGS %s -o \"%s\" "
            "-L\"%s\" -L\"%s\" -lvc -lunac -lmenuw %s %s"
            % (objs, binary, libvc_lib, unac_lib, nc_libs,
               unac_extra_libs),
            cwd=src, env=benv)
        if not os.path.isfile(binary):
            raise RuntimeError(
                "rolo direct link produced no binary at %s" % binary)
        self.output.info("rolo direct build ok: %s" % binary)
        # Strict version gate: -v exits before curses init (safe
        # headless); any config.h or link skew fails closed HERE, never
        # as a miscounted test later.
        try:
            proc = subprocess.run(
                [binary, "-v"], stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT, timeout=60)
        except Exception as exc:
            raise RuntimeError(
                "rolo -v smoke failed to execute %s: %r" % (binary, exc))
        out = proc.stdout.decode("utf-8", errors="replace").strip()
        if proc.returncode != 0 or out != "rolo 021":
            raise RuntimeError(
                "rolo -v gate failed (rc=%d out=%r, want 'rolo 021'); "
                "config.h or link skew" % (proc.returncode, out[:200]))
        self.output.info("rolo -v gate ok: 'rolo 021'")

    def package(self):
        # Direct install (no make install): the binary was linked to
        # <source>/src/rolo by _build_rolo_direct because the upstream
        # suite requires it there; copy it plus the man page into the
        # package.  copy() preserves the linker's +x mode.
        binary = os.path.join(self.source_folder, "src", "rolo")
        if not os.path.isfile(binary):
            raise RuntimeError(
                "package needs built binary, missing: %s" % binary)
        try:
            mode = oct(os.stat(binary).st_mode & 0o777)
        except OSError:
            mode = "unknown"
        self.output.info("rolo package binary: %s (mode %s)"
                         % (binary, mode))
        copy(self, "rolo", src=os.path.join(self.source_folder, "src"),
             dst=os.path.join(self.package_folder, "bin"), keep_path=False)
        man = os.path.join(self.source_folder, "doc", "rolo.1")
        if os.path.isfile(man):
            copy(self, "rolo.1", src=os.path.join(self.source_folder, "doc"),
                 dst=os.path.join(self.package_folder, "share", "man", "man1"),
                 keep_path=False)
        else:
            self.output.warning("rolo man page missing (doc/rolo.1); "
                                "packaging binary only")
        copy_license = os.path.join(self.source_folder, "COPYING")
        if os.path.isfile(copy_license):
            copy(self, "COPYING", src=self.source_folder,
                 dst=os.path.join(self.package_folder, "licenses"), keep_path=False)

    def package_info(self):
        # Single executable bin/rolo; no linkable library or headers.
        self.cpp_info.bindirs = ["bin"]
        self.cpp_info.includedirs = []
        self.cpp_info.libdirs = []

    def _machine(self, arch):
        return {"armv8": "aarch64"}.get(arch, arch)

    @staticmethod
    def _good_shell():
        """Shell that never reuses a poisoned profile CONFIG_SHELL.

        zurl/1.12.0 notes #30/#31: the profile may export
        CONFIG_SHELL=/data/service/hnp/bin/bash, which is inaccessible on
        some preflight runners; autoconf configure re-executes itself
        through $CONFIG_SHELL and dies with Error 127 at configure[139]
        (this round's libffi log shows the identical signature).  HMBS
        guarantees shell=/bin/sh, so prefer it (existence check only, no
        subprocess probing); the inherited CONFIG_SHELL value is never
        trusted.
        """
        for cand in ("/bin/sh", os.environ.get("SHELL")):
            if cand == "sh":
                return "sh"
            if cand and os.path.isfile(cand) \
                    and os.access(cand, os.X_OK):
                return cand
        return "sh"

    def _triplet(self):
        return "%s-unknown-linux-gnu" % self._machine(str(self.settings.arch))

    def _cand_works(self, prog):
        """True if prog runs --version cleanly (mdk/1.3.1 precedent).

        Only a subprocess probe; no os.access X_OK (R49: HMDFS ignores
        chmod, X_OK is unreliable).  Never trusts the poisoned HNP bash
        path.  Never raises.
        """
        import subprocess
        if not prog:
            return False
        prog = prog.strip().split()[0].strip("\"'")
        if "/" not in prog:
            prog = shutil.which(prog) or ""
            if not prog:
                return False
        if "hnp/bin/bash" in prog:
            return False
        try:
            result = subprocess.run(
                [prog, "--version"],
                stdout=subprocess.PIPE, stderr=subprocess.STDOUT, timeout=20)
            return result.returncode == 0
        except Exception:
            return False

    def _resolve_compiler(self, kind):
        """Return a runnable CC/CXX (mdk/1.3.1 precedent, adapted).

        Priority: profile tools.build:compiler_executables value when it
        actually runs (healthy host zero-change); else PATH-discovered
        clang/clang++ (HMBS prepends tool dirs to buildenv PATH) plus
        cc/gcc fallbacks and the Harmonybrew merged-bin fallback.  Only
        covers compiler variables, never flags.  kind: 'c'/'cpp'.
        """
        bare = "clang" if kind == "c" else "clang++"
        try:
            exes = self.conf.get("tools.build:compiler_executables", default=None)
        except Exception:
            exes = None
        conf_val = None
        if isinstance(exes, dict):
            conf_val = (exes.get("c") if kind == "c"
                        else exes.get("cpp") or exes.get("cxx"))
        if conf_val and self._cand_works(conf_val):
            return conf_val.strip().split()[0].strip("\"'")
        if conf_val:
            self.output.warning(
                "rolo pinned compiler not runnable: %r; falling back" % (conf_val,))
            try:
                same_dir = os.path.dirname(conf_val.strip().split()[0])
                if same_dir:
                    sibling = os.path.join(same_dir, bare)
                    if self._cand_works(sibling):
                        self.output.info(
                            "rolo compiler fallback (sibling): %s" % sibling)
                        return sibling
            except Exception:
                pass
        for cand in (bare, "cc" if kind == "c" else "c++", "gcc" if kind == "c" else "g++",
                     os.path.join(os.path.expanduser("~"), "usr", "local", "bin", bare),
                     "/storage/Users/currentUser/usr/local/bin/" + bare):
            if self._cand_works(cand):
                resolved = (cand.strip().split()[0] if "/" in cand
                            else shutil.which(cand))
                self.output.info(
                    "rolo compiler fallback: %s (conf was %r)" % (resolved, conf_val))
                return resolved
        return conf_val or bare

    def _dump_config_log(self, src_dir, label):
        """Retain config.log forensics on configure failure (mdk precedent).

        Logs the CC probe line, the candidate list, LD_LIBRARY_PATH and
        the tail of config.log so the next preflight round shows why the
        compiler check failed.  Never raises.
        """
        try:
            self.output.info("rolo %s forensics: CC=%r CXX=%r LD_LIBRARY_PATH=%r"
                             % (label, os.environ.get("CC"), os.environ.get("CXX"),
                                os.environ.get("LD_LIBRARY_PATH")))
        except Exception:
            pass
        for name in ("config.log",):
            path = os.path.join(src_dir, name)
            try:
                if not os.path.isfile(path):
                    self.output.info("rolo %s forensics: %s not found (searched %s)"
                                     % (label, name, path))
                    continue
                with open(path, encoding="utf-8", errors="replace") as handle:
                    lines = handle.read().splitlines()
                self.output.info("rolo %s forensics: %s (%d lines, tail 40):"
                                 % (label, path, len(lines)))
                for line in lines[-40:]:
                    self.output.info("rolo %s config.log | %s" % (label, line[:400]))
            except Exception as exc:
                self.output.info("rolo %s forensics: cannot read %s: %r"
                                 % (label, path, exc))

    def _drop_glib_dependency(self, src):
        """Remove rolo's glib edge via in-place source rewrites.

        rolo uses exactly one glib API: g_utf8_strlen(s, -1) in
        src/entry.c:set_menu_print_format (3 calls, NUL-terminated UTF-8
        char count for menu column width compensation).  Every glib
        revision in this repo has manifest status built (no ohpcd binary),
        so any requires forces a from-source meson build plus its libffi
        chain, and every autotools node in that chain dies at
        configure[139] on runners without HNP bash (this round:
        libffi/3.4.4 package e80f2bcb, same signature as the earlier m4
        deaths; previous round: glib meson clang missing).  ncurses/6.6,
        the only remaining requires, is a leaf node (no transitive deps).

        Rewrites (exact-match, count-verified, fail closed — same pattern
        as _apply_unac_type_fixes, so no .patch files and no hunk-header
        parser risk):
          configure.ac: drop the GLIB PKG_CHECK_MODULES block and the
            $GLIB_LIBS/$GLIB_CFLAGS wiring (UNAC block untouched).
          src/entry.c: drop #include <glib.h>, add a static
            rolo_utf8_strlen() with identical semantics (count bytes that
            are not UTF-8 continuation bytes), retarget the 3 calls.
        Idempotent: skips when the stamp exists (rewrites already applied).
        """
        stamp = os.path.join(src, ".rolo-no-glib-stamp")
        if os.path.isfile(stamp):
            self.output.info("rolo glib edge already dropped (stamp present)")
            return

        def _replace_once(path, old, new, want, label):
            with open(path, encoding="utf-8") as handle:
                text = handle.read()
            found = text.count(old)
            if found != want:
                raise RuntimeError(
                    "rolo glib-drop anchor drift (%s): want %d "
                    "occurrence(s), found %d in %s; refusing to guess"
                    % (label, want, found, path))
            with open(path, "w", encoding="utf-8") as handle:
                handle.write(text.replace(old, new))
            self.output.info("rolo glib-drop applied: %s" % label)

        conf_ac = os.path.join(src, "configure.ac")
        _replace_once(
            conf_ac,
            "# Glib settings\nPKG_CHECK_MODULES([GLIB],[glib-2.0])\n\n",
            "",
            1, "configure.ac glib PKG_CHECK_MODULES block")
        _replace_once(
            conf_ac,
            'LIBS="$LIBS $GLIB_LIBS $UNAC_LIBS"',
            'LIBS="$LIBS $UNAC_LIBS"',
            1, "configure.ac LIBS glib wiring")
        _replace_once(
            conf_ac,
            'CFLAGS="$CFLAGS $GLIB_CFLAGS $UNAC_CFLAGS"',
            'CFLAGS="$CFLAGS $UNAC_CFLAGS"',
            1, "configure.ac CFLAGS glib wiring")

        entry_c = os.path.join(src, "src", "entry.c")
        # NOTE: retarget the call sites FIRST, before inserting the local
        # counter whose comment must not itself contain the old symbol
        # (otherwise a naive occurrence count would see its own insert;
        # this ordering keeps the count anchored to upstream's 3 calls).
        _replace_once(
            entry_c,
            "g_utf8_strlen",
            "rolo_utf8_strlen",
            3, "entry.c call sites")
        _replace_once(
            entry_c,
            "#include <vc.h>\n#include <glib.h>\n#include <unac.h>",
            "#include <vc.h>\n#include <unac.h>\n"
            "\n"
            "/* Local UTF-8 code-point counter replacing the single glib\n"
            "   string helper used below: counts bytes that are not UTF-8\n"
            "   continuation bytes (0x80..0xBF); identical result for\n"
            "   valid UTF-8, same single-char fallback as the original for\n"
            "   invalid bytes.  Only used for menu column width\n"
            "   compensation below. */\n"
            "/* Same contract as the replaced helper (p, max_len): */\n"
            "/* max_len < 0 means NUL-terminated; otherwise at most */\n"
            "/* max_len bytes. */\n"
            "static long\n"
            "rolo_utf8_strlen (const char *s, long max_len)\n"
            "{\n"
            "  long n = 0;\n"
            "  long i = 0;\n"
            "  unsigned char c;\n"
            "  if (NULL == s)\n"
            "    return 0;\n"
            "  if (max_len < 0)\n"
            "    while ('\\0' != (c = (unsigned char) *s++))\n"
            "      if (0x80 != (c & 0xC0))\n"
            "        n++;\n"
            "  else\n"
            "    while (i < max_len && '\\0' != (c = (unsigned char) *s++))\n"
            "      {\n"
            "        i++;\n"
            "        if (0x80 != (c & 0xC0))\n"
            "          n++;\n"
            "      }\n"
            "  return n;\n"
            "}",
            1, "entry.c glib include -> local counter")

        with open(stamp, "w", encoding="utf-8") as handle:
            handle.write("rolo glib edge dropped: configure.ac + entry.c\n")
        self.output.info("rolo glib edge dropped (configure.ac + entry.c)")

    def _fix_tmpdir_templates(self, src):
        """Honor TMPDIR for rolo's editor temp files (notes.md #35).

        Upstream src/add.c (add_entry) and src/edit.c (edit_entry) both
        declare ``char filename[PATH_MAX] = "/tmp/rolo-XXXXXX"`` for
        mkstemp, with no fallback.  HMBS runners inject per-task
        TMPDIR/TMP/TEMP and /tmp may be read-only (test.sh already avoids /tmp
        for this reason), so the move_and_edit upstream test
        (``ROLO_EDITOR=cat`` edit path) can die inside mkstemp/fdopen
        while quit-only flows stay green — matching the preflight
        signature (2 of 4 failed, empty edit output, core dumped).

        Rewrites (exact-match, count-verified, fail closed — same
        discipline as _drop_glib_dependency, so no .patch files):
          add.c/edit.c: build the template from $TMPDIR (falling back to
            /tmp when unset/empty) via getenv/strcpy/strcat only
            (both TUs already include stdlib.h + string.h; no new
            includes, no control-flow change — a still-failing mkstemp
            stays loud, never silently skipped).
        Idempotent: skips when the stamp exists.
        """
        stamp = os.path.join(src, ".rolo-tmpdir-stamp")
        # Upgrade path (#38): stamp v1 fixed TMPDIR-only; v2 honors
        # TMPDIR/TMP/TEMP.  A reused tree with v1 content must be
        # re-patched, not skipped.
        if os.path.isfile(stamp):
            try:
                with open(stamp, encoding="utf-8") as _sh:
                    _sv = _sh.read()
            except OSError:
                _sv = ""
            if "v2 TMPDIR/TMP/TEMP" in _sv:
                self.output.info("rolo tmpdir templates already fixed (stamp v2 present)")
                return
            self.output.info("rolo tmpdir stamp v1 found, upgrading to v2")

        def _replace_once(path, old, new, want, label):
            with open(path, encoding="utf-8") as handle:
                text = handle.read()
            found = text.count(old)
            if found != want:
                raise RuntimeError(
                    "rolo tmpdir anchor drift (%s): want %d "
                    "occurrence(s), found %d in %s; refusing to guess"
                    % (label, want, found, path))
            with open(path, "w", encoding="utf-8") as handle:
                handle.write(text.replace(old, new))
            self.output.info("rolo tmpdir fix applied: %s" % label)

        new_decl = (
            "  char filename[PATH_MAX];\n"
            "  /* HMBS/HarmonyOS (#35/#38): /tmp may be read-only; build the\n"
            "     mkstemp template from $TMPDIR/$TMP/$TEMP with /tmp fallback. */\n"
            "  {\n"
            "    const char *td = getenv (\"TMPDIR\");\n"
            "    if (NULL == td || '\\0' == *td)\n"
            "      td = getenv (\"TMP\");\n"
            "    if (NULL == td || '\\0' == *td)\n"
            "      td = getenv (\"TEMP\");\n"
            "    if (NULL == td || '\\0' == *td)\n"
            "      td = \"/tmp\";\n"
            "    strcpy (filename, td);\n"
            "    strcat (filename, \"/rolo-XXXXXX\");\n"
            "  }"
        )
        v1_marker = "HMBS/HarmonyOS (#35): /tmp may be read-only"
        for base, label in (("add.c", "add_entry"), ("edit.c", "edit_entry")):
            path = os.path.join(src, "src", base)
            try:
                with open(path, encoding="utf-8") as _fh:
                    _txt = _fh.read()
            except OSError as exc:
                raise RuntimeError("rolo tmpdir fix cannot read %s: %r" % (path, exc))
            if new_decl in _txt:
                self.output.info("rolo tmpdir fix already v2: %s" % label)
                continue
            if v1_marker in _txt:
                with open(path, "w", encoding="utf-8") as _fh:
                    _fh.write(_txt.replace(v1_marker, "HMBS/HarmonyOS (#35/#38): /tmp may be read-only"))
                with open(path, encoding="utf-8") as _fh:
                    _txt2 = _fh.read()
                # insert TMP/TEMP lookups if upgrading from v1 text
                v1_lookup = "    const char *td = getenv (\"TMPDIR\");\n    if (NULL == td || '\\0' == *td)\n      td = \"/tmp\";"
                v2_lookup = "    const char *td = getenv (\"TMPDIR\");\n    if (NULL == td || '\\0' == *td)\n      td = getenv (\"TMP\");\n    if (NULL == td || '\\0' == *td)\n      td = getenv (\"TEMP\");\n    if (NULL == td || '\\0' == *td)\n      td = \"/tmp\";"
                if v1_lookup in _txt2:
                    with open(path, "w", encoding="utf-8") as _fh:
                        _fh.write(_txt2.replace(v1_lookup, v2_lookup))
                    self.output.info("rolo tmpdir fix upgraded v1->v2: %s" % label)
                    continue
            _replace_once(
                path,
                "  char filename[PATH_MAX] = \"/tmp/rolo-XXXXXX\";",
                new_decl,
                1, "%s mkstemp template (%s)" % (base, label))

        with open(stamp, "w", encoding="utf-8") as handle:
            handle.write("rolo tmpdir templates fixed v2 TMPDIR/TMP/TEMP: add.c + edit.c\n")
        self.output.info("rolo tmpdir templates fixed v2 (add.c + edit.c)")

    def _restore_run_tests_tmpdir(self, src):
        # Round-2 correction: the round-1 rewrite of the two bare
        # vcf=$(mktemp) lines was a misdiagnosis (the next preflight hit
        # the identical no-summary fingerprint with it applied; its
        # traceback line matches this tree, so the code did run).  The
        # proven root cause is colorized shunit2 output (see the parser):
        # bare mktemp honors TMPDIR on GNU/toybox/busybox, and the suite
        # step always exports a writable TMPDIR inline, so no driver
        # mutation is needed.  Restore the two lines pristine when the
        # round-1 marker is present (e.g. a reused source tree); skip
        # silently when already pristine.  Fail closed on count drift.
        path = os.path.join(src, "test", "run-tests")
        try:
            with open(path, encoding="utf-8") as handle:
                text = handle.read()
        except OSError as exc:
            raise RuntimeError("rolo run-tests restore cannot read: %r" % (exc,))
        new = 'vcf=$(mktemp "${TMPDIR:-/tmp}/rolo-test.XXXXXX")'
        old = "vcf=$(mktemp)"
        if new not in text:
            if text.count(old) != 2:
                raise RuntimeError("rolo run-tests pristine drift want 2 found %d" % text.count(old))
            self.output.info("rolo run-tests already pristine, no restore needed")
            return
        if text.count(new) != 2:
            raise RuntimeError("rolo run-tests marker drift want 2 found %d" % text.count(new))
        with open(path, "w", encoding="utf-8") as handle:
            handle.write(text.replace(new, old))
        self.output.info("rolo run-tests restored pristine (2 mktemp lines)")

    def _ensure_suite_tmpdir(self):
        # Prefer HMBS-injected TMPDIR/TMP/TEMP when writable, else
        # fall back to build_folder/rolo-tmp. Exports all three so
        # mktemp and shunit2 inside run-tests honor it. Never raises.
        try:
            cand = os.environ.get("TMPDIR") or os.environ.get("TMP") or os.environ.get("TEMP") or ""
            use = ""
            if cand and os.path.isdir(cand):
                try:
                    probe = os.path.join(cand, ".rolo-tmp-wr-probe")
                    with open(probe, "w", encoding="utf-8") as handle:
                        handle.write("ok\n")
                    try:
                        os.remove(probe)
                    except OSError:
                        pass
                    use = cand
                except OSError:
                    use = ""
            if not use:
                try:
                    use = os.path.join(self.build_folder, "rolo-tmp")
                    os.makedirs(use, exist_ok=True)
                except Exception as exc:
                    self.output.warning("rolo suite tmpdir fallback failed: %r" % (exc,))
                    return ""
            for var in ("TMPDIR", "TMP", "TEMP"):
                try:
                    os.environ[var] = use
                except Exception:
                    pass
            self.output.info("rolo suite tmpdir: %s" % use)
            return use
        except Exception as exc:
            self.output.warning("rolo suite tmpdir probe failed: %r" % (exc,))
            return ""

    def _suite_tmpdir_export(self):
        # Inline export so conanbuild aggregation cannot drop it.
        try:
            use = os.environ.get("TMPDIR") or os.environ.get("TMP") or os.environ.get("TEMP") or ""
            if not use:
                return ""
            return 'export TMPDIR="%s"; export TMP="%s"; export TEMP="%s"; ' % (use, use, use)
        except Exception:
            return ""

    def _build_libvc(self):
        """Fetch and statically build official libvc v013 privately.

        libvc has no recipe in this repository; rolo links it (upstream
        AC_CHECK_LIB(vc, vc_new) is fatal).  This builds the official v013
        tag tarball (hash-pinned LIBVC_URLS/SHA256) into
        ``<build_folder>/libvc-prefix`` (R49: private prefix, never
        /usr/local) as a static-only archive.  Only the header + the
        static archive are consumed at rolo link time; nothing is packaged
        or exported.

        Ninth strategy (2026-10-14): NO autotools.  The v013 tag ships no
        configure and autoreconf cannot run on this runner (no
        perl/autoconf package; ohpcd automake/1.18 provides no autoreconf
        binary — eighth-cycle root-cause re-audit).  libvc's configure
        surface is trivially small (audited configure.ac: AC_PROG_CC,
        AC_PROG_LEX/YACC gates, LT_INIT, AC_CHECK_INCLUDES_DEFAULT,
        AC_C_CONST, AC_FUNC_MALLOC, two AC_CHECK_FUNCS, one visibility
        m4_include; NO AC_CONFIG_HEADERS), so the build is done directly,
        faithfully mirroring src/Makefile.am
        (BUILT_SOURCES = vc_parse.h, AM_YFLAGS = -d, AM_LFLAGS = -i,
        SOURCES = vc.c vc_parse.y vc_scan.l):
          1. ``$YACC -d vc_parse.y`` (vendored byacc or native), rename the
             generated pair to vc_parse.c/vc_parse.h (candidate search
             covers byacc y.tab.* and bison *.tab.* layouts);
          2. ``$LEX -i -o vc_scan.c vc_scan.l`` for flex (plain lex gets no
             flags, lex.yy.c renamed instead);
          3. ``$CC -c`` the three C files (HAVE_VISIBILITY stays undefined,
             so ``#if HAVE_VISIBILITY`` in vc_parse.y/vc_scan.l evaluates to
             0 exactly as with an unconfigured tree — no config.h needed);
          4. ``ar rcs lib/libvc.a`` + copy src/vc.h to include/vc.h.
        The flex scanner needs no -lfl (the .l file carries
        ``%option noyywrap``, audited).  Idempotent via stamp; network/hash
        failures raise (fail closed, never skip).
        """
        prefix = os.path.join(self.build_folder, "libvc-prefix")
        src_dir = os.path.join(self.build_folder, "libvc-src")
        stamp = os.path.join(prefix, ".libvc-013-direct-built")
        header = os.path.join(prefix, "include", "vc.h")
        static_lib = os.path.join(prefix, "lib", "libvc.a")
        if os.path.isfile(stamp) and os.path.isfile(header) \
                and os.path.isfile(static_lib):
            self.output.info("vendored libvc v013 already built at %s" % prefix)
            return prefix
        # Fresh (or incomplete) build: fetch sources via Conan (hash
        # verified) and (re)install to the private prefix.
        if os.path.isdir(src_dir):
            shutil.rmtree(src_dir, ignore_errors=True)
        os.makedirs(src_dir, exist_ok=True)
        get(self, url=LIBVC_URLS, sha256=LIBVC_SHA256,
            destination=src_dir, strip_root=True)
        self._downgrade_opt_in_tree(src_dir, "libvc")
        # yacc/lex for vc_parse.y / vc_scan.l: native preferred, else the
        # private m4+byacc+flex prefix (no Conan graph nodes).  Sets
        # YACC/LEX/M4 in os.environ (see _ensure_vendored_lex_yacc).
        self._ensure_vendored_lex_yacc()
        yacc = os.environ.get("YACC") or ""
        lex = os.environ.get("LEX") or ""
        if not yacc or not lex:
            raise RuntimeError(
                "vendored libvc needs yacc+lex and neither native nor "
                "vendored pair resolved (YACC=%r LEX=%r); searched PATH plus "
                "tool dirs %s" % (yacc, lex, self._tool_search_dirs()))
        sdir = os.path.join(src_dir, "src")
        for want in ("vc.c", "vc.h", "vc_parse.y", "vc_scan.l"):
            if not os.path.isfile(os.path.join(sdir, want)):
                raise RuntimeError(
                    "vendored libvc tarball layout drift: missing %s "
                    "(audited v013 files: vc.c vc.h vc_parse.y vc_scan.l)"
                    % want)
        benv = ["conanbuild"]
        # 1) parser: $YACC -d (AM_YFLAGS).  Output names differ per tool
        # (byacc: y.tab.c/y.tab.h; bison: vc_parse.tab.c/vc_parse.tab.h),
        # so rename whichever candidate pair exists.
        # m4-first hardening (2026-10-14): bison spawns `m4` at
        # generation time and locates skeletons via BISON_PKGDATADIR.
        # Both are in os.environ after _ensure, but self.run with
        # env=["conanbuild"] may not preserve them through
        # conanbuild.sh sourcing, so export them inline (same values,
        # no new semantics; byacc ignores both).
        # CI build #91874 amendment (2026-10-14): the bison/2.7 tool
        # edge exports BISON_PKGDATADIR via runenv into EVERY
        # self.run(env=["conanbuild"]) invocation (conanbuild.sh
        # aggregation), even when _ensure chose the NATIVE bison 3.8.2
        # pair.  Native 3.8.2 honors that variable and then looks for
        # 3.8.2-style skeletons (bison.m4/c-skel.m4) inside the 2.7
        # data dir -> `m4: cannot open .../bison3d52.../skeletons/...`
        # with zero output, while the subprocess smoke (clean env,
        # no conanbuild.sh) stays green and hides the skew.  When the
        # chosen yacc is native (no outer BISON_PKGDATADIR), unset the
        # variable inline AFTER conanbuild.sh sourcing so native bison
        # falls back to its own compiled-in datadir; the Conan-bison
        # branch keeps the explicit export (same value, no change).
        _gen_prefix = ""
        try:
            _parts = []
            _m4 = os.environ.get("M4", "")
            if _m4:
                _parts.append('export M4="%s"; ' % _m4)
                _mdb = os.path.dirname(_m4)
                if _mdb:
                    _parts.append('export PATH="%s:$PATH"; ' % _mdb)
            _bpd = os.environ.get("BISON_PKGDATADIR", "")
            if _bpd:
                _parts.append('export BISON_PKGDATADIR="%s"; ' % _bpd)
            else:
                _parts.append('unset BISON_PKGDATADIR; ')
            _gen_prefix = "".join(_parts)
            if _gen_prefix:
                self.output.info("rolo libvc gen env: %s" % _gen_prefix)
        except Exception as _exc:
            self.output.info("rolo libvc gen env build failed: %r" % _exc)
            _gen_prefix = ""
        self._run_retry(_gen_prefix + '"%s" -d vc_parse.y' % yacc,
                        cwd=sdir, env=benv, label="libvc yacc")
        self._rename_generated_pair(
            sdir, ("vc_parse.c", "y.tab.c", "vc_parse.tab.c"),
            ("vc_parse.h", "y.tab.h", "vc_parse.tab.h"), "libvc yacc")
        # CI #92890: bison -d emits vc_parse.tab.c containing
        # #include "vc_parse.tab.h" (line 126); after the rename above the
        # header lives at vc_parse.h (which vc_scan.l expects), so the
        # stale include must be rewritten before cc, else
        # "fatal error: 'vc_parse.tab.h' file not found".
        self._fix_libvc_parser_include(sdir)
        # 2) scanner: flex -i -o (AM_LFLAGS = -i).  Non-flex lex gets no
        # flags; its default lex.yy.c output is renamed instead.
        if "flex" in os.path.basename(lex):
            self._run_retry(_gen_prefix + '"%s" -i -o vc_scan.c vc_scan.l' % lex,
                              cwd=sdir, env=benv, label="libvc flex")
        else:
            self.output.info("vendored libvc: non-flex lex %s, no -i flag "
                             "(upstream -i semantics only guaranteed with "
                             "flex)" % lex)
            self._run_retry(_gen_prefix + '"%s" vc_scan.l' % lex, cwd=sdir, env=benv,
                              label="libvc lex")
            self._rename_generated_pair(
                sdir, ("vc_scan.c", "lex.yy.c"), (), "libvc lex")
        if not os.path.isfile(os.path.join(sdir, "vc_scan.c")):
            raise RuntimeError(
                "vendored libvc scanner generation produced no vc_scan.c "
                "(sdir=%s)" % sdir)
        # 3) compile the three translation units with profile flags
        # plus a lowmem tail (vendored scope; last -O/-g wins).
        self._run_retry("$CC $CFLAGS $CPPFLAGS -O1 -g0 -I. -c vc.c vc_parse.c vc_scan.c",
                        cwd=sdir, env=benv, label="libvc cc")
        # 4) archive + install header (ar rcs writes the symbol index, no
        # separate ranlib needed; libtool proved ar works on this runner).
        ar = self._resolve_ar()
        libdir = os.path.join(prefix, "lib")
        incdir = os.path.join(prefix, "include")
        os.makedirs(libdir, exist_ok=True)
        os.makedirs(incdir, exist_ok=True)
        self._run_retry('"%s" rcs "%s" vc.o vc_parse.o vc_scan.o'
                          % (ar, os.path.join(libdir, "libvc.a")), cwd=sdir, env=benv,
                          label="libvc ar")
        shutil.copyfile(os.path.join(sdir, "vc.h"),
                        os.path.join(incdir, "vc.h"))
        if not (os.path.isfile(header) and os.path.isfile(static_lib)):
            raise RuntimeError(
                "vendored libvc install incomplete: want %s and %s "
                "(prefix=%s)" % (header, static_lib, prefix))
        with open(stamp, "w", encoding="utf-8") as handle:
            handle.write("libvc v013 vendored direct static build ok\n")
        self.output.info("vendored libvc v013 built at %s" % prefix)
        return prefix

    def _fix_libvc_parser_include(self, sdir):
        """Rewrite stale bison header refs to the renamed vc_parse.h.

        bison ``-d vc_parse.y`` writes ``vc_parse.tab.c`` whose body
        contains ``#include "vc_parse.tab.h"``; the recipe renames the
        pair to ``vc_parse.c``/``vc_parse.h`` (``vc_scan.l`` already
        expects ``vc_parse.h``), so the stale ``.tab.h``/``y.tab.h``
        spelling must be retargeted before ``cc``.  byacc trees contain
        no such include, making this a no-op there.  Fail closed when
        neither target file exists; stale refs absent is fine.
        """
        targets = [os.path.join(sdir, n)
                   for n in ("vc_parse.c", "vc_scan.c")]
        if not any(os.path.isfile(p) for p in targets):
            raise RuntimeError(
                "libvc include fixup: neither vc_parse.c nor vc_scan.c "
                "present in %s" % sdir)
        for path in targets:
            if not os.path.isfile(path):
                continue
            with open(path, "r", encoding="utf-8", errors="replace") as handle:
                text = handle.read()
            fixed = (text.replace('"vc_parse.tab.h"', '"vc_parse.h"')
                         .replace('"y.tab.h"', '"vc_parse.h"'))
            if fixed != text:
                with open(path, "w", encoding="utf-8", newline="") as handle:
                    handle.write(fixed)
                self.output.info(
                    "libvc include fixup: retargeted stale header ref in %s"
                    % os.path.basename(path))
            else:
                self.output.info(
                    "libvc include fixup: no stale ref in %s"
                    % os.path.basename(path))

    @staticmethod
    def _rename_generated_pair(sdir, c_names, h_names, label):
        """Rename the first existing candidate pair to the wanted names.

        c_names[0]/h_names[0] are the wanted names; the rest are tool
        outputs (byacc y.tab.*, bison *.tab.*).  Already-correct names are
        left in place.  Raises with a directory listing when nothing
        matches (fail closed, never guess).
        """
        want_c = c_names[0]
        have_c = next((n for n in c_names
                       if os.path.isfile(os.path.join(sdir, n))), None)
        if have_c is None:
            try:
                entries = sorted(os.listdir(sdir))
            except OSError:
                entries = []
            raise RuntimeError(
                "%s: no parser/scanner C output (wanted one of %s; "
                "sdir=%s holds %s)" % (label, c_names, sdir, entries))
        if have_c != want_c:
            os.replace(os.path.join(sdir, have_c),
                       os.path.join(sdir, want_c))
        if h_names:
            want_h = h_names[0]
            have_h = next((n for n in h_names
                           if os.path.isfile(os.path.join(sdir, n))), None)
            if have_h is None:
                try:
                    entries = sorted(os.listdir(sdir))
                except OSError:
                    entries = []
                raise RuntimeError(
                    "%s: no parser header output (wanted one of %s; "
                    "sdir=%s holds %s)" % (label, h_names, sdir, entries))
            if have_h != want_h:
                os.replace(os.path.join(sdir, have_h),
                           os.path.join(sdir, want_h))

    def _resolve_ar(self):
        """Return an absolute archiver path (ar preferred, llvm-ar fallback).

        libtool's ranlib step succeeded on this runner during the vendored
        flex install, so a working archiver exists; fail closed with the
        searched locations when none resolves.  Never raises for probe
        noise — only a hard miss raises.
        """
        for cand in ("ar", "llvm-ar"):
            found = shutil.which(cand)
            if found:
                self.output.info("rolo archiver: %s" % found)
                return found
        raise RuntimeError(
            "no archiver on PATH (tried ar, llvm-ar); searched PATH=%s plus "
            "tool dirs %s" % (os.environ.get("PATH", ""),
                              self._tool_search_dirs()))

    def _build_unac(self):
        """Fetch and statically build official unac 1.8.0 privately.

        unac/1.8.0 exists in this repo but never published a binary, so it
        always source-builds, activating its tool_requires (automake/1.18
        + libtool/2.5.4, the latter absent from this repo) and — via CCI
        automake -> autoconf -> m4 — the CCI m4/1.4.19 node that dies at
        configure[139] on runners without HNP bash.  Building the same
        official Debian orig tarball (same URL/sha256 as the unac recipe)
        into ``<build_folder>/unac-prefix`` as static-only removes that
        whole subtree from the graph; only headers + static archive +
        unac.pc are consumed at rolo direct cc/link time.

        Two routes (chosen at build time, both idempotent via stamp):
        shipped configure (official CI runners) keeps the legacy flow
        mirroring archives/u/unac/1.8.0/conanfile.py (config.rpath,
        ACLOCAL_PATH, autoreconf, umask fix, TMPDIR redirect, srcdir
        quirk, make -j1, HELP2MAN bypass, triplet, SHELL pinning);
        otherwise (this preflight runner: orig tarball holds no
        configure and no autoreconf exists) _build_unac_direct
        compiles unac.c straight to a static archive with a probed
        config.h.  Returns (prefix, extra_libs) — extra link libs
        ("" or "-liconv") proven necessary by probes, threaded into
        the rolo link.
        """
        prefix = os.path.join(self.build_folder, "unac-prefix")
        src_dir = os.path.join(self.build_folder, "unac-src")
        stamp = os.path.join(prefix, ".unac-180-built")
        header = os.path.join(prefix, "include", "unac.h")
        static_lib = os.path.join(prefix, "lib", "libunac.a")
        pc_file = os.path.join(prefix, "lib", "pkgconfig", "unac.pc")
        if os.path.isfile(stamp) and os.path.isfile(header) \
                and os.path.isfile(static_lib) and os.path.isfile(pc_file):
            extra = self._read_unac_stamp_extra(stamp)
            self.output.info("vendored unac 1.8.0 already built at %s (extra=%r)" % (prefix, extra))
            return prefix, extra
        if os.path.isdir(src_dir):
            shutil.rmtree(src_dir, ignore_errors=True)
        os.makedirs(src_dir, exist_ok=True)
        get(self, url=UNAC_URL, sha256=UNAC_SHA256,
            destination=src_dir, strip_root=True)
        # NOTE: no _downgrade_opt_in_tree here (it lives in the legacy
        # configure route only): the direct route compiles unac.c with
        # explicit -O1 -g0 and must not text-mutate the 13k-line table
        # file.  Type fixes below are exact-anchor and table-safe.
        # Same hunks as the unac recipe's two patches (aarch64 stack
        # corruption); exact-match, count-verified, fail closed.
        self._apply_unac_type_fixes(src_dir)
        # Route dispatch (eleventh strategy): shipped configure keeps
        # the legacy flow; otherwise build directly (no autotools).
        if os.path.isfile(os.path.join(src_dir, "configure")):
            self.output.info("vendored unac: shipped configure present, legacy configure+make flow")
            extra_libs = self._build_unac_with_configure(src_dir, prefix)
            route = "configure"
        else:
            self.output.info("vendored unac: no shipped configure and no autoreconf on this runner; direct cc/ar build")
            extra_libs = self._build_unac_direct(src_dir, prefix)
            route = "direct"
        for artifact in (header, static_lib, pc_file):
            if not os.path.isfile(artifact):
                raise RuntimeError(
                    "vendored unac install incomplete: missing %s (prefix=%s)"
                    % (artifact, prefix))
        with open(stamp, "w", encoding="utf-8") as handle:
            handle.write("unac 1.8.0 vendored static build ok route=%s extra=%s\n" % (route, extra_libs))
        self.output.info("vendored unac 1.8.0 built at %s (route=%s extra=%r)" % (prefix, route, extra_libs))
        return prefix, extra_libs

    def _build_unac_with_configure(self, src_dir, prefix):
        """Legacy configure+make flow for trees shipping configure.

        Untouched ninth-strategy body (serves official CI runners whose
        trees provide configure); configure resolves iconv itself, so
        this returns "" (no extra libs to thread).  The opt-downgrade
        moved here with it: only this route consumes generated build
        scripts, and only here is mutating them safe.
        """
        self._downgrade_opt_in_tree(src_dir, "unac")
        old_pwd = os.environ.get("PWD")
        os.environ["PWD"] = src_dir
        self._push_lowmem_flags()
        # HMDFS: conftest dummy.c hits Permission denied on some mounts;
        # point temp files at a stable writable dir (unac precedent).
        old_tmpdir = os.environ.get("TMPDIR")
        try:
            _btmp = os.path.join(os.path.expanduser("~"), ".conan_build_tmp")
            os.makedirs(_btmp, exist_ok=True)
            os.environ["TMPDIR"] = _btmp
        except OSError:
            pass
        try:
            sh = self._good_shell()
            benv = ["conanbuild"]
            # config.rpath is only needed when autoreconf actually runs (it
            # is a no-op when the tarball ships configure — _run handles
            # the ordering internally).  The umask fix applies to the
            # shipped configure as well (HMDFS, E011).
            self._run_unac_autoreconf(src_dir, benv)
            self._fix_umask_077(src_dir)
            self._freeze_autotools_generated(src_dir, "unac")
            triplet = self._triplet()
            self._run_retry(
                "CFLAGS=\"$CFLAGS -O1 -g0\" CXXFLAGS=\"$CXXFLAGS -O1 -g0\" CONFIG_SHELL=\"%s\" SHELL=\"%s\" \"%s\" configure --prefix=\"%s\" "
                "--disable-shared --enable-static --disable-dependency-tracking --build=%s --host=%s"
                % (sh, sh, sh, prefix, triplet, triplet),
                cwd=src_dir, env=benv)
            # builder Perl script uses $ENV{'srcdir'} to locate
            # unaccent-local-map.perl (unac precedent).
            os.environ["srcdir"] = src_dir
            self._run_retry("CFLAGS=\"$CFLAGS -O1 -g0\" CXXFLAGS=\"$CXXFLAGS -O1 -g0\" CONFIG_SHELL=\"%s\" SHELL=\"%s\" make SHELL=%s RM=\"${RM:-rm -f}\" CFLAGS=\"$CFLAGS -O1 -g0\" CXXFLAGS=\"$CXXFLAGS -O1 -g0\" -j1 MAKEINFO=true AUTOHEADER=true AUTOCONF=true AUTOMAKE=true ACLOCAL=true"
                     % (sh, sh, sh), cwd=src_dir, env=benv)
            self._run_retry("CFLAGS=\"$CFLAGS -O1 -g0\" CXXFLAGS=\"$CXXFLAGS -O1 -g0\" CONFIG_SHELL=\"%s\" SHELL=\"%s\" make SHELL=%s RM=\"${RM:-rm -f}\" CFLAGS=\"$CFLAGS -O1 -g0\" CXXFLAGS=\"$CXXFLAGS -O1 -g0\" -j1 install HELP2MAN=/bin/true MAKEINFO=true AUTOHEADER=true AUTOCONF=true AUTOMAKE=true ACLOCAL=true"
                     % (sh, sh, sh), cwd=src_dir, env=benv)
        finally:
            try:
                self._pop_lowmem_flags()
            except Exception:
                pass
            if old_pwd is None:
                os.environ.pop("PWD", None)
            else:
                os.environ["PWD"] = old_pwd
            if old_tmpdir is None:
                os.environ.pop("TMPDIR", None)
            else:
                os.environ["TMPDIR"] = old_tmpdir
        return ""

    def _read_unac_stamp_extra(self, stamp):
        """Return persisted extra link libs from a previous unac build.

        Never raises: unknown stamp content means no extra libs.
        """
        try:
            with open(stamp, encoding="utf-8") as handle:
                text = handle.read()
            match = re.search(r"extra=(\S*)", text)
            if match:
                return match.group(1)
        except OSError as exc:
            self.output.info("unac stamp re-read failed: %r" % (exc,))
        return ""

    @staticmethod
    def _header_for_have(name):
        """Map HAVE_FOO_H to its header path (HAVE_SYS_TYPES_H -> sys/types.h).

        Mechanical autoconf naming inversion; the probe decides truth.
        """
        core = name[5:].lower() if name.startswith("HAVE_") else name.lower()
        if core.endswith("_h"):
            core = core[:-2]
        return core.replace("_", "/") + ".h"

    def _probe_cc(self, probedir, name, src_text, benv, link_libs="",
                  extra_cflags=""):
        """Compile+link one probe TU with the conanbuild $CC.

        Writes probe_<name>.c under probedir; returns True iff the link
        produced a binary.  Never raises: FAIL is a legitimate configure
        answer, logged as such (the command echo already sits in the log
        above on failure).
        """
        safe = re.sub(r"[^A-Za-z0-9_]", "_", name)
        c_path = os.path.join(probedir, "probe_%s.c" % safe)
        bin_path = os.path.join(probedir, "probe_%s" % safe)
        try:
            with open(c_path, "w", encoding="utf-8") as handle:
                handle.write(src_text)
        except OSError as exc:
            self.output.info("unac probe %s: cannot write TU: %r" % (safe, exc))
            return False
        try:
            if os.path.isfile(bin_path):
                os.unlink(bin_path)
        except OSError:
            pass
        cmd = ("$CC $CFLAGS $CPPFLAGS %s -o \"%s\" \"%s\" %s"
               % (extra_cflags, bin_path, c_path, link_libs))
        try:
            self.run(self._with_util_path(cmd), cwd=probedir, env=benv)
            ok = os.path.isfile(bin_path)
        except Exception as exc:
            ok = False
            self.output.info("unac probe %s -> FAIL (%s)"
                             % (safe, str(exc)[:200]))
        if ok:
            self.output.info("unac probe %s -> OK" % safe)
        return ok

    def _link_check_unac(self, probedir, incdir, libdir, symbols, benv,
                         libs):
        """Link a TU taking the address of each consumer symbol.

        Proves the archive provides exactly what rolo links, with
        transitive closure (a missing iconv/getopt surfaces here, not at
        the rolo link).  Returns True/False, never raises.
        """
        body = "".join("  (void)&%s;\n" % s for s in symbols)
        # unac.h uses size_t without including <stddef.h> itself (it
        # relies on the consumer providing it, as rolo's own sources do
        # via stdio/stdlib); the probe TU must do the same or every
        # gate attempt dies with "unknown type name 'size_t'".
        src = ("#include <stddef.h>\n#include <unac.h>\n"
               "int main(void)\n{\n%s  return 0;\n}\n" % body)
        return self._probe_cc(
            probedir, "gate_link", src, benv,
            link_libs="-L\"%s\" -lunac %s" % (libdir, libs),
            extra_cflags="-Wno-error -I\"%s\"" % incdir)

    def _discover_unac_consumer_symbols(self, unac_h):
        """Grep rolo sources for unac* symbols referenced by the consumer.

        Only tokens declared as functions in unac.h count (a bare-word
        match admits the `#include <unac.h>` line's own `unac` token and
        comment words, which then die as `(void)&unac` undeclared).  A
        token counts only when unac.h contains it followed by `(`,
        i.e. a function declaration/definition site.  Comment mentions
        such as the tool name in --help text are dropped with a log
        line.  Fails closed when nothing remains: the whole vendoring
        exists for that reference, so an empty set means assumption
        drift.
        """
        roots = [os.path.join(self.source_folder, "src")]
        found = set()
        for root in roots:
            try:
                names = sorted(os.listdir(root))
            except OSError:
                continue
            for name in names:
                if not name.endswith((".c", ".h")):
                    continue
                try:
                    with open(os.path.join(root, name), encoding="utf-8",
                              errors="replace") as handle:
                        text = handle.read()
                except OSError:
                    continue
                # Strip block/line comments so doc references such as
                # "see unac(3)" never become candidate symbols, then drop
                # preprocessor directives so "#include <unac.h>" never
                # contributes its bare "unac" basename token.
                no_block = re.sub(r"/\*.*?\*/", " ", text, flags=re.S)
                lines = []
                for line in no_block.splitlines():
                    code = line.split("//", 1)[0]
                    if code.lstrip().startswith("#"):
                        continue
                    lines.append(code)
                code_text = "\n".join(lines)
                for tok in re.findall(r"\bunac[A-Za-z0-9_]*\b", code_text):
                    if tok != "unac.h":
                        found.add(tok)
        self.output.info("unac direct audit: raw rolo unac* tokens %s"
                         % sorted(found))
        # Declaration check runs on comment-stripped unac.h: the shipped
        # header documents "See the unac(3) manual page", whose bare
        # "unac(" text falsely satisfied the old check and kept the
        # header-basename token "unac" (which then died as
        # "(void)&unac" undeclared). Stripping comments leaves only
        # real declaration sites.
        clean_h = re.sub(r"/\*.*?\*/", " ", unac_h, flags=re.S)
        clean_h = re.sub(r"//[^\n]*", " ", clean_h)
        symbols = [s for s in sorted(found)
                   if re.search(r"\b%s\s*\(" % re.escape(s), clean_h)]
        dropped = sorted(found - set(symbols))
        if dropped:
            self.output.info("unac direct audit: tokens not declared in "
                             "unac.h, dropped from link gate: %s" % dropped)
        self.output.info("unac direct audit: rolo consumer symbols %s"
                         % symbols)
        if not symbols:
            raise RuntimeError(
                "unac direct build: no unac* symbol referenced under %s "
                "that unac.h declares; assumption drift" % roots)
        return symbols

    def _write_unac_config_h(self, cfgdir, undefs, decisions, pkg):
        """Write the probed config.h for the unac direct build.

        Every name parsed from config.h.in is emitted exactly once:
        PACKAGE_*/VERSION from configure.ac AC_INIT, STDC_HEADERS as 1,
        WORDS_BIGENDIAN only when big-endian (autoconf convention),
        ICONV_CONST as "" (blank) or const per the iconv.m4 probe,
        UNAC_VERSION as the quoted verified version, probed HAVE_* as
        1 / undef-comment.  UNAC_VERSION is additionally ensured with a
        guarded fallback even when config.h.in predates it (stale
        shipped config.h.in vs configure.ac AC_DEFINE): unac.c returns
        it unconditionally, so a missing entry must not mean a missing
        macro.  Fails closed when the
        emitted set drifts from the parsed set (logic bug, never paper
        over it).
        """
        os.makedirs(cfgdir, exist_ok=True)
        seen = []
        lines = [
            "/* Generated by rolo/021 _build_unac_direct (no configure). */",
            "/* PACKAGE_* from configure.ac AC_INIT (verified); HAVE_* by */",
            "/* $CC probe on this runner (define = linked, undef = absent). */",
            "#ifndef UNAC_CONFIG_H",
            "#define UNAC_CONFIG_H",
        ]
        emitted_unac_version = False
        for name in undefs:
            if name in seen:
                continue
            seen.append(name)
            if name in pkg:
                lines.append("#define %s \"%s\"" % (name, pkg[name]))
            elif name == "STDC_HEADERS":
                lines.append("#define STDC_HEADERS 1")
            elif name == "WORDS_BIGENDIAN":
                if decisions.get(name):
                    lines.append("#define WORDS_BIGENDIAN 1")
                else:
                    lines.append("/* #undef WORDS_BIGENDIAN */")
            elif name == "ICONV_CONST":
                # AM_ICONV semantics (gettext iconv.m4): value is "" or
                # "const", never 1/undef. decisions holds the probed
                # string; empty emits a blank macro so
                # "(ICONV_CONST char **)" stays valid C.
                val = decisions.get(name, "")
                if val == "const":
                    lines.append("#define ICONV_CONST const")
                else:
                    lines.append("#define ICONV_CONST /**/")
            elif name == "UNAC_VERSION":
                # unac.c returns UNAC_VERSION as a string literal; value
                # is the AC_INIT-verified version from pkg VERSION.
                ver = pkg.get("VERSION", "1.8.0")
                lines.append("#define UNAC_VERSION \"%s\"" % ver)
                emitted_unac_version = True
            elif name in decisions:
                if decisions[name]:
                    lines.append("#define %s 1" % name)
                else:
                    lines.append("/* #undef %s */" % name)
            else:
                lines.append("/* #undef %s */" % name)
                self.output.info("unac config.h: no probe for %s, left "
                                 "undefined" % name)
        if not emitted_unac_version:
            # config.h.in predates the AC_DEFINE (stale shipped file):
            # unac.c returns UNAC_VERSION unconditionally, so ensure it
            # here with an include guard instead of failing the compile.
            # Value mirrors the AC_INIT-verified version (tegrarcm/1.8
            # precedent: extend the generated header with package-identity
            # definitions). Not added to `seen`: the drift check below
            # still compares exactly the parsed undef set.
            ver = pkg.get("VERSION", "1.8.0")
            lines.append("#ifndef UNAC_VERSION")
            lines.append("#define UNAC_VERSION \"%s\"" % ver)
            lines.append("#endif")
            self.output.info("unac config.h: UNAC_VERSION absent from "
                             "config.h.in, ensured guarded fallback \"%s\""
                             % ver)
        lines.append("#endif")
        if sorted(seen) != sorted(set(undefs)):
            raise RuntimeError(
                "unac config.h emission drift: parsed %d name(s), emitted "
                "%d" % (len(set(undefs)), len(seen)))
        path = os.path.join(cfgdir, "config.h")
        with open(path, "w", encoding="utf-8") as handle:
            handle.write("\n".join(lines) + "\n")
        defined = sum(1 for line in lines if line.startswith("#define "))
        self.output.info("unac config.h written: %s (%d defined, %d total)"
                         % (path, defined, len(seen)))
        return cfgdir

    def _write_unac_pc(self, pc_path, prefix, version, extra_libs):
        """Write the unac.pc this private prefix exposes.

        Values mirror what configure would emit for --disable-shared
        --enable-static into this prefix; Libs carries the probed extra
        libs so downstream links stay closed.
        """
        content = (
            "prefix=%s\n" % prefix
            + "exec_prefix=${prefix}\n"
            + "libdir=${exec_prefix}/lib\n"
            + "includedir=${prefix}/include\n"
            + "\n"
            + "Name: unac\n"
            + "Description: Unicode accent stripping library\n"
            + "Version: %s\n" % version
            + "Libs: -L${libdir} -lunac%s\n"
            % ((" " + extra_libs) if extra_libs else "")
            + "Cflags: -I${includedir}\n"
        )
        os.makedirs(os.path.dirname(pc_path), exist_ok=True)
        with open(pc_path, "w", encoding="utf-8") as handle:
            handle.write(content)
        self.output.info("unac pc written: %s (extra=%r)" % (pc_path, extra_libs))

    def _build_unac_direct(self, src_dir, prefix):
        """Compile unac 1.8.0 directly: $CC -c unac.c + ar (no autotools).

        Eleventh strategy (2026-10-14) — a different route from the
        ninth, which assumed the Debian orig tarball ships a configure
        (June unac notes Step 2 ran plain ./configure) and failed closed
        when absent.  The tenth-cycle preflight proves that assumption
        wrong: the tarball holds only configure.ac/Makefile.am/autogen.sh
        (sdir list in the failure log) while this runner provides no
        autoreconf (native autoconf/automake/libtool ALL MISSING; ohpcd
        automake/1.18 requirements() is pass so no Conan edge can supply
        it; harmonybrew perl alone cannot run autogen.sh without the
        autoconf macro tree; vendoring the full autoconf+automake+libtool
        source stack would reintroduce the just-eliminated m4/perl
        chain).  So autotools is eliminated for unac exactly as the ninth
        strategy did for libvc/rolo:
          * the library is ONE translation unit: unac.c already embeds
            the ~13000 lines of Unicode tables (patch 0002 anchors at
            line 13875); only the unaccent CLI needs getopt/autotools,
            which rolo never consumes.
          * config.h is a build-time mini-configure: every HAVE_* macro
            the sources reference is decided by an actual $CC
            compile/link probe — never guessed, every decision logged;
            PACKAGE_* comes from configure.ac AC_INIT (version verified);
            ICONV_CONST follows gettext iconv.m4 ("" vs "const" via a
            POSIX-signature compile probe, never 1) and UNAC_VERSION is
            the verified version as a quoted string.
          * gates (fail closed): the exact unac* symbols rolo references
            are discovered by grep (filtered against unac.h declarations)
            and link-probed as an address-of TU against the archive with
            transitive closure, so a missing iconv/getopt surfaces here
            rather than at the rolo link; -liconv is adopted only when a
            probe proves it necessary and is returned for the rolo link.
        Returns the extra link libs ("" or "-liconv").  Idempotent via
        the outer stamp; network/hash failures raise.
        """
        benv = ["conanbuild"]
        # 1) source audit (evidence; every later decision cites this log).
        try:
            entries = sorted(os.listdir(src_dir))
        except OSError:
            entries = []
        self.output.info("unac direct audit: sdir holds %s" % entries)
        for want in ("unac.c", "unac.h"):
            path = os.path.join(src_dir, want)
            if not os.path.isfile(path):
                raise RuntimeError(
                    "unac direct build needs %s (sdir holds %s); tarball "
                    "layout drift" % (want, entries))
            try:
                size = os.path.getsize(path)
            except OSError:
                size = -1
            self.output.info("unac direct audit: %s (%d bytes)" % (want, size))
        try:
            with open(os.path.join(src_dir, "unac.c"), encoding="utf-8",
                      errors="replace") as handle:
                unac_c = handle.read()
        except OSError as exc:
            raise RuntimeError("unac direct build cannot read unac.c: %r"
                               % (exc,))
        try:
            with open(os.path.join(src_dir, "unac.h"), encoding="utf-8",
                      errors="replace") as handle:
                unac_h = handle.read()
        except OSError as exc:
            raise RuntimeError("unac direct build cannot read unac.h: %r"
                               % (exc,))
        have_refs = sorted(set(re.findall(r"HAVE_[A-Z0-9_]+", unac_c))
                           | set(re.findall(r"HAVE_[A-Z0-9_]+", unac_h)))
        self.output.info("unac direct audit: HAVE_* referenced %s" % have_refs)
        uses_config_h = ("HAVE_CONFIG_H" in unac_c) or ("HAVE_CONFIG_H" in unac_h)
        self.output.info("unac direct audit: uses HAVE_CONFIG_H=%s"
                         % uses_config_h)
        includes = sorted(set(re.findall(r"#\s*include\s*[<\"]([^>\"]+)[>\"]",
                                          unac_c)))
        self.output.info("unac direct audit: unac.c includes %s" % includes)
        getopt_refs = sorted(set(re.findall(
            r"\b(getopt\w*|optarg|optind|opterr|optopt)\b", unac_c)))
        self.output.info("unac direct audit: getopt refs in unac.c %s"
                         % getopt_refs)
        try:
            with open(os.path.join(src_dir, "configure.ac"), encoding="utf-8",
                      errors="replace") as handle:
                configure_ac = handle.read()
        except OSError as exc:
            raise RuntimeError("unac direct build cannot read configure.ac: %r"
                               % (exc,))
        self.output.info("unac direct audit: configure.ac head: %r"
                         % configure_ac[:1200])
        # Version discovery: AC_INIT first, then AM_INIT_AUTOMAKE,
        # brackets optional.  The first attempt assumed the modern
        # [bracket] form and the preflight run proved it wrong
        # (drift error with zero candidates); this 2002-era tree may
        # use bare AC_INIT(unac, 1.8.0) or carry the version only in
        # AM_INIT_AUTOMAKE.  Every candidate is logged; zero matches
        # or inconsistent versions still fail closed.
        found_versions = []
        for pattern in (r"AC_INIT\(\s*\[?([^\],\)]+)\]?\s*,\s*\[?([^\],\)]+)\]?"
                        r"(?:\s*,\s*\[?([^\]\)]*)\]?)?",
                        r"AM_INIT_AUTOMAKE\(\s*\[?([^\],\)]+)\]?\s*,\s*\[?([^\],\)]+)\]?"):
            for match in re.finditer(pattern, configure_ac):
                found_versions.append(
                    (match.group(1).strip().strip("[]"),
                     match.group(2).strip().strip("[]"),
                     match.group(3).strip().strip("[]")
                     if match.lastindex >= 3 and match.group(3) else ""))
        self.output.info("unac direct audit: version candidates %s"
                         % (found_versions,))
        unac_hits = [(n, v, b) for (n, v, b) in found_versions
                     if n == "unac"]
        if not unac_hits:
            raise RuntimeError(
                "unac direct build: no AC_INIT/AM_INIT_AUTOMAKE names "
                "unac (candidates %s); refusing to guess version"
                % (found_versions,))
        versions = set(v for (_, v, _) in unac_hits)
        if len(versions) != 1:
            raise RuntimeError(
                "unac direct build: inconsistent unac versions %s; "
                "refusing to guess" % sorted(versions))
        unac_version = unac_hits[0][1]
        unac_bugreport = next((b for (_, _, b) in unac_hits if b), "")
        if unac_version.startswith("$"):
            # The version lives outside configure.ac: this tree ships
            # a .version file (seen in the sdir listing) and calls
            # AC_INIT(unac, $VERSION).  Resolve it from tree files —
            # preflight proved the token is literally $VERSION — and
            # never invent it: .version content first, VERSION=
            # assignment in configure.ac second, anything else fails
            # closed.  Every source is logged.
            var = unac_version.strip().lstrip("$").strip("{}() ")
            resolved = ""
            try:
                with open(os.path.join(src_dir, ".version"),
                          encoding="utf-8", errors="replace") as handle:
                    resolved = handle.read().strip().split()[0]
            except (OSError, IndexError) as exc:
                self.output.info("unac direct audit: .version "
                                 "unreadable: %r" % (exc,))
            assign = re.search(r"^VERSION\s*=\s*(\S+)", configure_ac,
                               flags=re.M)
            self.output.info("unac direct audit: version var=%s "
                             ".version=%r assign=%s"
                             % (var, resolved,
                                assign.group(1) if assign else None))
            if var == "VERSION" and resolved:
                unac_version = resolved
            elif var == "VERSION" and assign:
                unac_version = assign.group(1).strip().strip("\"'")
            else:
                raise RuntimeError(
                    "unac direct build: version is a variable %r with "
                    "no tree source (.version/assign); refusing to "
                    "guess" % unac_hits[0][1])
            self.output.info("unac direct audit: resolved version=%s"
                             % unac_version)
        self.output.info("unac direct audit: name=unac version=%s "
                         "bugreport=%s" % (unac_version, unac_bugreport))
        if unac_version != "1.8.0":
            raise RuntimeError("unac direct build: version drift %r (want "
                               "1.8.0)" % unac_version)
        # 2) config.h.in: the full decision surface.
        config_in = os.path.join(src_dir, "config.h.in")
        if not os.path.isfile(config_in):
            raise RuntimeError("unac direct build: config.h.in missing (sdir "
                               "holds %s)" % entries)
        try:
            with open(config_in, encoding="utf-8", errors="replace") as handle:
                config_in_text = handle.read()
        except OSError as exc:
            raise RuntimeError("unac direct build cannot read config.h.in: %r"
                               % (exc,))
        undefs = re.findall(r"^#undef\s+([A-Za-z0-9_]+)", config_in_text,
                            flags=re.M)
        self.output.info("unac direct audit: config.h.in %d undef(s): %s"
                         % (len(undefs), sorted(set(undefs))))
        # 3) probes (mini-configure).  Headers first: function probes
        # include exactly the headers proven present below.
        probedir = os.path.join(self.build_folder, "unac-probe")
        os.makedirs(probedir, exist_ok=True)
        decisions = {}
        for name in sorted(set(undefs)):
            if name in ("PACKAGE_NAME", "PACKAGE_TARNAME", "PACKAGE_VERSION",
                        "PACKAGE_STRING", "PACKAGE_BUGREPORT", "PACKAGE_URL",
                        "VERSION", "STDC_HEADERS", "WORDS_BIGENDIAN",
                        "HAVE_CONFIG_H", "HAVE_ICONV"):
                continue
            if not name.endswith("_H"):
                continue
            header = self._header_for_have(name)
            src = "#include <%s>\nint main(void){return 0;}\n" % header
            decisions[name] = self._probe_cc(probedir, "h_%s" % name.lower(),
                                             src, benv)
        std_headers = ["stdio.h", "stdlib.h", "string.h", "errno.h",
                       "unistd.h", "stdarg.h"]
        std_ok = {}
        for header in std_headers:
            key = "std_%s" % header.replace(".", "_").replace("/", "_")
            src = "#include <%s>\nint main(void){return 0;}\n" % header
            std_ok[header] = self._probe_cc(probedir, key, src, benv)
        inc_block = "".join("#include <%s>\n" % h
                            for h in std_headers if std_ok[h])
        for name in sorted(decisions):
            if decisions[name]:
                header = self._header_for_have(name)
                if header not in std_headers:
                    inc_block += "#include <%s>\n" % header
        # iconv special-case: HAVE_ICONV has no linkable symbol of its
        # own; decide it by linking a real iconv_open call, trying libc
        # first and -liconv second (musl needs no extra lib; log which).
        iconv_libs = None
        if "HAVE_ICONV" in set(undefs):
            if decisions.get("HAVE_ICONV_H"):
                iconv_src = (inc_block + "#include <iconv.h>\n"
                             + "int main(void){\n"
                             + "  iconv_t cd = iconv_open((const char*)0, "
                             + "(const char*)0);\n"
                             + "  (void)cd;\n  return 0;\n}\n")
                if self._probe_cc(probedir, "f_iconv_open", iconv_src, benv):
                    iconv_libs = ""
                elif self._probe_cc(probedir, "f_iconv_open_liconv",
                                    iconv_src, benv, link_libs="-liconv"):
                    iconv_libs = "-liconv"
                decisions["HAVE_ICONV"] = iconv_libs is not None
                self.output.info("unac probe HAVE_ICONV -> %s (libs=%r)"
                                 % (decisions["HAVE_ICONV"], iconv_libs))
            else:
                decisions["HAVE_ICONV"] = False
                self.output.info("unac probe HAVE_ICONV -> False "
                                 "(no iconv.h, no call probe attempted)")
        # ICONV_CONST special-case (AM_ICONV semantics from gettext
        # iconv.m4): the value is "" or "const", never 1/undef. Probe by
        # declaring the POSIX non-const iconv signature; when it
        # compiles the system uses "char **" (empty), otherwise
        # "const char **". Compile+link with an empty main is
        # equivalent to autoconf AC_COMPILE_IFELSE here (no iconv call,
        # so link adds no noise). Fail-closed default is "const"-side
        # only when the POSIX declaration is actually rejected; a
        # missing iconv.h falls back to "" like iconv.m4 does when no
        # iconv exists yet.
        if "ICONV_CONST" in set(undefs):
            posix_src = ("#include <stdlib.h>\n#include <iconv.h>\n"
                         "extern size_t iconv(iconv_t cd, char **inbuf, "
                         "size_t *inbytesleft, char **outbuf, "
                         "size_t *outbytesleft);\n"
                         "int main(void){return 0;}\n")
            if not decisions.get("HAVE_ICONV_H"):
                decisions["ICONV_CONST"] = ""
                self.output.info("unac probe ICONV_CONST -> '' "
                                 "(no iconv.h, POSIX default)")
            elif self._probe_cc(probedir, "iconv_const_nonconst",
                                posix_src, benv,
                                extra_cflags="-Wno-error"):
                decisions["ICONV_CONST"] = ""
                self.output.info("unac probe ICONV_CONST -> '' "
                                 "(POSIX non-const signature compiles)")
            else:
                decisions["ICONV_CONST"] = "const"
                self.output.info("unac probe ICONV_CONST -> 'const' "
                                 "(POSIX signature rejected)")
        # UNAC_VERSION special-case: unac.c returns it as a string
        # literal (const char *unac_version(void){ return UNAC_VERSION; }).
        # Value is the AC_INIT-verified version; the emitter quotes it.
        if "UNAC_VERSION" in set(undefs):
            decisions["UNAC_VERSION"] = True
            self.output.info("unac probe UNAC_VERSION -> \"%s\" "
                             "(from AC_INIT version)" % unac_version)
        # 4) function probes: address-of avoids calling-convention risk
        # from guessed prototypes; -Wno-error keeps legacy-header
        # warnings from flipping a present symbol to absent.
        for name in sorted(set(undefs)):
            if name in decisions:
                continue
            if name in ("PACKAGE_NAME", "PACKAGE_TARNAME", "PACKAGE_VERSION",
                        "PACKAGE_STRING", "PACKAGE_BUGREPORT", "PACKAGE_URL",
                        "VERSION", "HAVE_CONFIG_H"):
                continue
            if name == "STDC_HEADERS":
                decisions[name] = True
                continue
            if name == "WORDS_BIGENDIAN":
                import sys as _sys
                decisions[name] = (_sys.byteorder == "big")
                self.output.info("unac probe WORDS_BIGENDIAN: byteorder=%s "
                                 "-> %s" % (_sys.byteorder, decisions[name]))
                continue
            if name in ("ICONV_CONST", "UNAC_VERSION"):
                # Handled by the dedicated probes above (string-valued,
                # never 1/undef); the generic extern-int probe must not
                # run for them (it produced "#define ICONV_CONST 1").
                continue
            if not name.startswith("HAVE_"):
                # Non-feature macros must never get a bogus "#define FOO
                # 1" from an extern-int probe; leave undefined (the
                # emitter logs it) so a real use surfaces as a compiler
                # error instead of silent miscompilation.
                self.output.info("unac probe %s: non-HAVE macro, left "
                                 "undefined" % name)
                continue
            suffix = (name[5:].lower() if name.startswith("HAVE_")
                      else name.lower())
            if not re.match(r"^[a-z][a-z0-9_]*$", suffix):
                decisions[name] = False
                self.output.info("unac probe %s: non-identifier suffix, -> "
                                 "False" % name)
                continue
            src = (inc_block + "extern int %s();\nint main(void)"
                   "{ (void)&%s; return 0; }\n" % (suffix, suffix))
            decisions[name] = self._probe_cc(probedir, "f_%s" % suffix, src,
                                             benv,
                                             extra_cflags="-Wno-error")
        # 5) config.h from decisions.
        pkg = {"PACKAGE_NAME": "unac",
               "PACKAGE_TARNAME": "unac",
               "PACKAGE_VERSION": unac_version,
               "PACKAGE_STRING": "unac %s" % unac_version,
               "PACKAGE_BUGREPORT": unac_bugreport,
               "PACKAGE_URL": "",
               "VERSION": unac_version}
        cfgdir = self._write_unac_config_h(
            os.path.join(self.build_folder, "unac-cfg"), undefs, decisions,
            pkg)
        # 6) compile the library TU (+ getopt TU only when referenced).
        objdir = os.path.join(self.build_folder, "unac-obj")
        os.makedirs(objdir, exist_ok=True)
        self._run_retry(
            "$CC $CFLAGS $CPPFLAGS -Wno-error -O1 -g0 -DHAVE_CONFIG_H=1 "
            "-I\"%s\" -I\"%s\" -c \"%s\" -o \"%s\""
            % (cfgdir, src_dir, os.path.join(src_dir, "unac.c"),
               os.path.join(objdir, "unac.o")),
            cwd=src_dir, env=benv, label="unac cc")
        if getopt_refs and not os.path.isfile(os.path.join(src_dir,
                                                            "getopt.c")):
            self.output.info("unac direct: unac.c refs getopt %s but no "
                             "getopt.c ships; single-object variant only"
                             % getopt_refs)
        if getopt_refs and os.path.isfile(os.path.join(src_dir, "getopt.c")):
            self._run_retry(
                "$CC $CFLAGS $CPPFLAGS -Wno-error -O1 -g0 -DHAVE_CONFIG_H=1 "
                "-I\"%s\" -I\"%s\" -c \"%s\" -o \"%s\""
                % (cfgdir, src_dir, os.path.join(src_dir, "getopt.c"),
                   os.path.join(objdir, "getopt.o")),
                cwd=src_dir, env=benv, label="unac getopt cc")
        # 7) install header, then pick the archive variant that passes
        # the consumer link gate (getopt variant only when it exists).
        ar = self._resolve_ar()
        libdir = os.path.join(prefix, "lib")
        incdir = os.path.join(prefix, "include")
        for directory in (libdir, incdir, objdir):
            os.makedirs(directory, exist_ok=True)
        shutil.copyfile(os.path.join(src_dir, "unac.h"),
                        os.path.join(incdir, "unac.h"))
        libpath = os.path.join(libdir, "libunac.a")
        variants = [[os.path.join(objdir, "unac.o")]]
        if os.path.isfile(os.path.join(objdir, "getopt.o")):
            variants.append([os.path.join(objdir, "unac.o"),
                             os.path.join(objdir, "getopt.o")])
            self.output.info("unac direct: getopt fallback variant armed "
                             "(unac.c refs %s)" % getopt_refs)
        symbols = self._discover_unac_consumer_symbols(unac_h)
        if iconv_libs is not None:
            lib_order = [iconv_libs] + [x for x in ("", "-liconv")
                                        if x != iconv_libs]
        else:
            lib_order = ["", "-liconv"]
        chosen_extra = None
        tried = []
        for objs in variants:
            self._run_retry(
                "\"%s\" rcs \"%s\" %s"
                % (ar, libpath, " ".join("\"%s\"" % o for o in objs)),
                cwd=src_dir, env=benv, label="unac ar")
            for libs in lib_order:
                tried.append((len(objs), libs))
                if self._link_check_unac(probedir, incdir, libdir, symbols,
                                         benv, libs):
                    chosen_extra = libs
                    self.output.info("unac direct: link gate passed "
                                     "(objs=%d extra=%r)" % (len(objs), libs))
                    break
            if chosen_extra is not None:
                break
        if chosen_extra is None:
            raise RuntimeError(
                "unac direct build: consumer link gate failed for symbols "
                "%s (tried %s); full probe output sits in the log above"
                % (symbols, tried))
        # 8) pkg-config file for audit continuity.
        self._write_unac_pc(os.path.join(libdir, "pkgconfig", "unac.pc"),
                            prefix, unac_version, chosen_extra)
        # 9) supplementary: upstream's own unactest when it builds
        # standalone (unknown CLI contract, so run-failure is logged
        # evidence, not a gate; the hard gates above still hold).
        for candidate in ("unactest.c", "unactest1.c"):
            cpath = os.path.join(src_dir, candidate)
            if not os.path.isfile(cpath):
                continue
            try:
                with open(cpath, encoding="utf-8", errors="replace") as handle:
                    ttext = handle.read()
            except OSError:
                continue
            if "main" not in ttext or "unac.h" not in ttext:
                self.output.info("unac direct: %s has no standalone harness "
                                 "(needs build-system fixtures); skipped "
                                 "with reason logged" % candidate)
                continue
            binpath = os.path.join(probedir, "unactest_run")
            try:
                self.run(self._with_util_path(
                    "$CC $CFLAGS $CPPFLAGS -Wno-error -O1 -g0 "
                    "-DHAVE_CONFIG_H=1 -I\"%s\" -I\"%s\" \"%s\" -o \"%s\" "
                    "-L\"%s\" -lunac %s"
                    % (cfgdir, incdir, cpath, binpath, libdir,
                       chosen_extra)),
                    cwd=src_dir, env=benv)
            except Exception as exc:
                self.output.info("unac direct: %s does not build standalone "
                                 "(%s); skipped, archive gate above holds"
                                 % (candidate, str(exc)[:300]))
                continue
            try:
                self.run(self._with_util_path("\"%s\"" % binpath),
                         cwd=src_dir, env=benv)
                self.output.info("unac direct: %s ran green" % candidate)
            except Exception as exc:
                self.output.info("unac direct: %s built but exited nonzero "
                                 "(%s); logged as evidence, not a gate "
                                 "(unknown CLI contract)"
                                 % (candidate, str(exc)[:500]))
        self.output.info("vendored unac 1.8.0 direct-built at %s (extra=%r)"
                         % (prefix, chosen_extra))
        return chosen_extra

    def _apply_unac_type_fixes(self, src_dir):
        """Apply the unac recipe's two aarch64 int->size_t fixes.

        Same hunks as archives/u/unac/1.8.0/patches/0001 + 0002 (upstream
        passes int where size_t is expected; stack corruption on aarch64,
        see that recipe's notes).  Implemented as exact-match replacement
        with occurrence counts verified — no external `patch` binary needed
        on the device; any anchor drift fails closed.
        """
        fixes = [
            ("unaccent.c",
             "    int unaccented_length = 0;\n",
             "    size_t unaccented_length = 0;\n", 1),
            ("unac.c",
             "    int utf16_length = 0;\n",
             "    size_t utf16_length = 0;\n", 1),
            ("unac.c",
             "    int utf16_unaccented_length = 0;\n",
             "    size_t utf16_unaccented_length = 0;\n", 1),
        ]
        for filename, old, new, want in fixes:
            path = os.path.join(src_dir, filename)
            with open(path, encoding="utf-8") as handle:
                text = handle.read()
            found = text.count(old)
            if found != want:
                raise RuntimeError(
                    "unac type-fix anchor drift in %s: want %d occurrence(s), "
                    "found %d; refusing to guess" % (filename, want, found))
            with open(path, "w", encoding="utf-8") as handle:
                handle.write(text.replace(old, new))
            self.output.info("unac type fix applied: %s" % filename)

    def _ensure_unac_config_rpath(self, src_dir):
        """Provide config.rpath for unac's autoreconf (unac precedent).

        The Debian orig tarball ships no config.rpath; autoreconf needs it
        from gettext.  Uses the same candidate locations as the unac
        recipe.  Fails closed with the searched paths when nothing is
        found, instead of dying inside autoreconf.
        """
        dest = os.path.join(src_dir, "config.rpath")
        if os.path.isfile(dest):
            self.output.info("unac config.rpath already shipped, no copy needed")
            return
        candidates = [
            "/data/service/hnp/gettext.org/gettext_0.26/share/gettext/config.rpath",
            "/usr/local/share/gettext/config.rpath",
            "/usr/share/gettext/config.rpath",
        ]
        for candidate in candidates:
            if os.path.isfile(candidate):
                shutil.copy(candidate, dest)
                self.output.info("unac config.rpath copied from %s" % candidate)
                return
        raise RuntimeError(
            "unac autoreconf needs config.rpath (gettext auxiliary file): "
            "tarball does not ship it and none of %s exists on this runner"
            % candidates)

    def _run_unac_autoreconf(self, src_dir, benv):
        """Run unac's autoreconf sequence when possible, else fail closed.

        Ninth strategy (2026-10-14): the Debian orig tarball is expected to
        ship configure (the June adaptation built it via plain ./configure
        with no autoreconf step, see unac notes Step 2), in which case this
        returns early having done nothing.  When configure is absent AND
        no autoreconf binary resolves (this runner: no perl, no autoconf
        package, ohpcd automake/1.18 ships no autoreconf), raise with the
        searched locations instead of dying inside a perl-less autoreconf
        with Error 127 — never fake a configure.  Kept the legacy
        autoreconf sequence for runners that do provide it (official CI
        may), unchanged from archives/u/unac/1.8.0/conanfile.py.
        """
        if os.path.isfile(os.path.join(src_dir, "configure")):
            self.output.info("unac configure already present, skipping autoreconf")
            return
        if not self._native_probe(("autoreconf",)):
            try:
                entries = sorted(os.listdir(src_dir))
            except OSError:
                entries = []
            raise RuntimeError(
                "vendored unac tarball ships no configure (sdir holds %s) "
                "and this runner provides no autoreconf (perl/autoconf "
                "absent, ohpcd automake/1.18 has no such binary); refusing "
                "to guess a configure (fail closed, never fake it)" % entries)
        # autoreconf will run: it needs config.rpath from gettext first.
        self._ensure_unac_config_rpath(src_dir)
        self.run(
            'LT_BIN=$(which libtoolize 2>/dev/null) && '
            'LT_ROOT=$(dirname $(dirname "$LT_BIN")) && '
            'LT_M4_DIR=$(find "$LT_ROOT" -name "libtool.m4" 2>/dev/null | head -1 | xargs dirname 2>/dev/null) && '
            'GT_M4="/data/service/hnp/gettext.org/gettext_0.26/share/gettext/m4" && '
            'if [ -n "$LT_M4_DIR" ]; then export ACLOCAL_PATH="$LT_M4_DIR:$GT_M4:${ACLOCAL_PATH}"; '
            'elif [ -d "$GT_M4" ]; then export ACLOCAL_PATH="$GT_M4:${ACLOCAL_PATH}"; fi && '
            'autoreconf --install --force && '
            'aclocal --force && autoconf --force && autoheader --force',
            cwd=src_dir, env=benv)

    def _fix_umask_077(self, src_dir):
        """Rewrite umask 077 -> 022 in generated configure files.

        config.status creates its temp dir with umask 077, which is
        unwritable on the HMDFS /storage mount (unac/automake precedent);
        must run AFTER autoreconf (which regenerates configure).
        """
        for cfg in glob.glob(os.path.join(src_dir, "**", "configure"),
                             recursive=True):
            try:
                with open(cfg, encoding="utf-8", errors="ignore") as handle:
                    text = handle.read()
            except OSError:
                continue
            if "umask 077" in text:
                with open(cfg, "w", encoding="utf-8") as handle:
                    handle.write(text.replace("umask 077", "umask 022"))
                self.output.info("unac umask fix: %s" % cfg)

    def _conan_bison(self):
        """Return (bison_bin, pkgdatadir) from the bison/2.7 tool edge.

        Never raises: returns (None, None) when the tool package is
        absent so the caller can fall back to vendored byacc.  bison 2.7
        installs under usr/bin + usr/share/bison (see its conanfile:
        --prefix=/usr with DESTDIR); the consumer must export
        BISON_PKGDATADIR so bison finds m4sugar at generation time.
        """
        try:
            pkg = self.dependencies.build["bison"].package_folder
        except Exception as exc:
            self.output.info("rolo conan bison absent: %r" % (exc,))
            return None, None
        for cand in (os.path.join(pkg, "usr", "bin", "bison"),
                     os.path.join(pkg, "bin", "bison")):
            if os.path.isfile(cand):
                data = os.path.join(pkg, "usr", "share", "bison")
                if not os.path.isdir(data):
                    data = None
                self.output.info("rolo conan bison: %s (pkgdata=%s)"
                                 % (cand, data))
                return cand, data
        self.output.info("rolo conan bison package holds no binary (pkg=%s)"
                         % pkg)
        return None, None

    def _smoke_yacc_ok(self, yacc_bin):
        """True if yacc_bin really generates C output (never raises).

        CI gate (2026-10-14, PR #15792 build #91603): the CI runner
        exposes a native bison, so the probe took the "native pair"
        branch — but that binary is a stale install whose skeleton dir
        is gone.  It starts, then dies with ``m4: cannot open
        '.../bison3d52.../p/usr/share/bison/skeletons/bison.m4'`` and
        produces no output, so _build_libvc later fails with "no
        parser/scanner C output".  Existence/X_OK probing cannot catch
        a missing data dir; only a real ``-d`` generation can.  Runs
        the candidate on a minimal grammar in a build-folder scratch
        dir (writable by construction, no TMPDIR dependence) and
        accepts only when a C file appears.  False (with a log line)
        means "fall through to the next yacc source".

        CI build #92704 amendment (2026-10-15): a TRANSIENT fork failure
        (native flex ``fork failed``, vendored m4 ``can't fork`` on the
        shared CI worker) must not discard a healthy native binary on a
        single attempt.  When the smoke output matches a memory/fork
        signature (_is_mem_retryable), retry up to 3 times with a short
        cooldown; a persistent failure (missing skeletons, bad install)
        still falls through immediately with no retry.  Test scope and
        flags untouched.
        """
        import subprocess
        for attempt in range(1, 4):
            try:
                scratch = os.path.join(self.build_folder, "rolo-yacc-smoke")
                shutil.rmtree(scratch, ignore_errors=True)
                os.makedirs(scratch, exist_ok=True)
                with open(os.path.join(scratch, "smoke.y"), "w",
                          encoding="utf-8") as handle:
                    handle.write("%token NUM\n%%\nstart: NUM ;\n%%\n"
                                 "int yylex(void){return 0;}\n"
                                 "int yyerror(const char *s){(void)s;return 0;}\n")
                proc = subprocess.run(
                    [yacc_bin, "-d", "smoke.y"],
                    cwd=scratch, stdout=subprocess.PIPE,
                    stderr=subprocess.STDOUT, timeout=60)
                out = proc.stdout.decode("utf-8", errors="replace")
                produced = sorted(
                    n for n in ("smoke.tab.c", "y.tab.c",
                                "smoke.c", "y_tab.c")
                    if os.path.isfile(os.path.join(scratch, n)))
                ok = proc.returncode == 0 and bool(produced)
                tail = out.strip()[-300:] if out.strip() else ""
                if ok:
                    self.output.info("rolo yacc smoke: %s rc=0 produced=%s"
                                     % (yacc_bin, produced))
                    return True
                retryable = self._is_mem_retryable(out)
                self.output.info("rolo yacc smoke: %s rc=%d produced=%s%s%s"
                                 % (yacc_bin, proc.returncode, produced,
                                    (" tail=%r" % tail)
                                    if tail else "",
                                    (" (transient %d/3, retrying)" % attempt)
                                    if retryable and attempt < 3 else ""))
                if not retryable or attempt >= 3:
                    return False
                try:
                    time.sleep(5)
                except Exception:
                    pass
            except Exception as exc:
                self.output.info("rolo yacc smoke error: %s: %r"
                                 % (yacc_bin, exc))
                return False
        return False

    def _smoke_lex_ok(self, lex_bin):
        """True if lex_bin really generates a scanner (never raises).

        Same CI gate as _smoke_yacc_ok: a probed flex/lex path may exist
        yet fail at generation time on a runner with a stale install.
        Minimal grammar (no %option, portable to flex and plain lex);
        flex takes ``-o``, plain lex gets no flags and defaults to
        lex.yy.c.  Only generation is checked (no link).

        CI build #92704 amendment (2026-10-15): same transient rule as
        _smoke_yacc_ok — ``flex: fork failed`` on the shared CI worker
        is retried up to 3 times before the native flex is discarded
        (which would otherwise force the heavy vendored m4+flex chain
        that itself dies with ``can't fork`` under the same pressure).
        Persistent failures fall through immediately.
        """
        import subprocess
        for attempt in range(1, 4):
            try:
                scratch = os.path.join(self.build_folder, "rolo-lex-smoke")
                shutil.rmtree(scratch, ignore_errors=True)
                os.makedirs(scratch, exist_ok=True)
                with open(os.path.join(scratch, "smoke.l"), "w",
                          encoding="utf-8") as handle:
                    handle.write("%%\n. ;\n%%\nint main(void){return 0;}\n")
                if "flex" in os.path.basename(lex_bin or ""):
                    argv = [lex_bin, "-o", "smoke.c", "smoke.l"]
                    want = ("smoke.c",)
                else:
                    argv = [lex_bin, "smoke.l"]
                    want = ("lex.yy.c",)
                proc = subprocess.run(
                    argv, cwd=scratch, stdout=subprocess.PIPE,
                    stderr=subprocess.STDOUT, timeout=60)
                out = proc.stdout.decode("utf-8", errors="replace")
                produced = [n for n in want
                            if os.path.isfile(os.path.join(scratch, n))]
                ok = proc.returncode == 0 and bool(produced)
                tail = out.strip()[-300:] if out.strip() else ""
                if ok:
                    self.output.info("rolo lex smoke: %s rc=0 produced=%s"
                                     % (lex_bin, produced))
                    return True
                retryable = self._is_mem_retryable(out)
                self.output.info("rolo lex smoke: %s rc=%d produced=%s%s%s"
                                 % (lex_bin, proc.returncode, produced,
                                    (" tail=%r" % tail)
                                    if tail else "",
                                    (" (transient %d/3, retrying)" % attempt)
                                    if retryable and attempt < 3 else ""))
                if not retryable or attempt >= 3:
                    return False
                try:
                    time.sleep(5)
                except Exception:
                    pass
            except Exception as exc:
                self.output.info("rolo lex smoke error: %s: %r"
                                 % (lex_bin, exc))
                return False
        return False

    def _ensure_vendored_lex_yacc(self):
        """Expose yacc/lex for libvc direct build (bison -d / flex -i).

        Tenth strategy (2026-10-14): YACC prefers, in order, native
        binaries, then the Conan bison/2.7 tool edge (ohpcd-only,
        zero-dep, OHOS-proven), and only then the private byacc build
        (which dies on this runner with `cannot open "action_file"`).
        LEX prefers native, else the private m4+flex prefix (proven
        working: flex installed clean this round).  m4 is still built
        first whenever flex is vendored (flex invokes it at generation
        time).  The private bin/ is prepended to PATH with absolute
        M4/YACC/LEX plus BISON_PKGDATADIR exports for deterministic
        generation.

        Smoke-gate amendment (2026-10-14, CI build #91603): every
        candidate — native, Conan bison, vendored byacc — must pass a
        real generation smoke (_smoke_yacc_ok/_smoke_lex_ok) before use.
        A probed path may belong to a stale install whose data dir is
        gone (native bison runs, then `m4: cannot open
        '.../skeletons/bison.m4'`, no output); existence probing cannot
        catch that.  Smoke failures fall through to the next source,
        never fail closed while another source remains.
        """
        for dirname in RoloConan._tool_search_dirs():
            try:
                old_path = os.environ.get("PATH", "")
                if dirname not in old_path.split(os.pathsep):
                    os.environ["PATH"] = dirname + os.pathsep + old_path
            except Exception:
                pass
        yacc = self._native_probe(("bison", "yacc", "byacc"))
        lex = self._native_probe(("flex", "lex"))
        self.output.info("rolo libvc yacc/lex native: YACC=%s LEX=%s"
                         % (yacc or "MISSING", lex or "MISSING"))
        if yacc and not self._smoke_yacc_ok(yacc):
            self.output.info("rolo libvc yacc: native %s fails generation "
                             "smoke, ignoring (see rolo yacc smoke line)"
                             % yacc)
            yacc = None
        if lex and not self._smoke_lex_ok(lex):
            self.output.info("rolo libvc lex: native %s fails generation "
                             "smoke, ignoring (see rolo lex smoke line)"
                             % lex)
            lex = None
        if yacc and lex:
            os.environ["YACC"] = yacc
            os.environ["LEX"] = lex
            self.output.info("rolo libvc yacc/lex: using native pair")
            return
        tools_prefix = os.path.join(self.build_folder, "yl-tools-prefix")
        os.makedirs(tools_prefix, exist_ok=True)
        # Eleventh strategy (2026-10-14, preflight 11:33Z): m4 FIRST.
        # Root cause of this round: Conan bison/2.7 smoked BEFORE the
        # private m4 existed ("m4 subprocess failed: No such file or
        # directory", native m4 MISSING), so a healthy bison was rejected
        # and the build fell through to vendored byacc, which dies on
        # this runner with `cannot open "action_file"`.  bison invokes
        # m4 at generation time, so M4 + PATH must exist before ANY
        # bison smoke (native retry or Conan edge).  Build m4 now and
        # export it immediately; the later bison smoke then inherits it.
        # m4 is required at flex generation time too, so building it
        # first changes no other semantics.
        m4_bin = self._build_vendored_m4(tools_prefix)
        bindir_early = os.path.join(tools_prefix, "bin")
        try:
            old_path = os.environ.get("PATH", "")
            if bindir_early not in old_path.split(os.pathsep):
                os.environ["PATH"] = bindir_early + os.pathsep + old_path
            os.environ["M4"] = m4_bin
            self.output.info("rolo libvc m4-first: M4=%s PATH prepend %s"
                             % (m4_bin, bindir_early))
        except Exception as exc:
            self.output.info("rolo libvc m4-first export failed: %r" % exc)
        # A native yacc probed above was smoked WITHOUT m4 on PATH; if
        # it was rejected only for that reason, retry now that the
        # private m4 is exported (same smoke gate, no semantics change).
        if not yacc:
            yacc_retry = self._native_probe(("bison", "yacc", "byacc"))
            if yacc_retry and self._smoke_yacc_ok(yacc_retry):
                yacc = yacc_retry
                os.environ["YACC"] = yacc
                self.output.info("rolo libvc yacc: native retry ok with "
                                 "vendored m4 (%s)" % yacc)
            elif yacc_retry:
                self.output.info("rolo libvc yacc: native retry still fails "
                                 "with vendored m4, continuing to Conan bison")
        # YACC order: native > Conan bison/2.7 > vendored byacc.
        # (byacc is last resort: it builds but dies at generation time
        # on this runner with `cannot open "action_file"`.)
        if not yacc:
            bison_bin, bison_data = self._conan_bison()
            if bison_bin:
                if bison_data:
                    os.environ["BISON_PKGDATADIR"] = bison_data
                if self._smoke_yacc_ok(bison_bin):
                    yacc = bison_bin
                    os.environ["YACC"] = yacc
                    self.output.info("rolo libvc yacc: using Conan bison/2.7 "
                                     "(with vendored m4)")
                else:
                    self.output.info("rolo libvc yacc: Conan bison %s fails "
                                     "generation smoke even with vendored m4, "
                                     "falling back to vendored byacc"
                                     % bison_bin)
                    os.environ.pop("BISON_PKGDATADIR", None)
        if not yacc:
            yacc = self._build_vendored_byacc(tools_prefix)
            if not self._smoke_yacc_ok(yacc):
                raise RuntimeError(
                    "vendored byacc %s fails generation smoke and no other "
                    "yacc is usable (native and Conan bison were rejected "
                    "above; see rolo yacc smoke lines)" % yacc)
        else:
            if "YACC" not in os.environ:
                os.environ["YACC"] = yacc
        if not lex:
            lex = self._build_vendored_flex(tools_prefix, m4_bin)
        else:
            os.environ["LEX"] = lex
        bindir = os.path.join(tools_prefix, "bin")
        old_path = os.environ.get("PATH", "")
        if bindir not in old_path.split(os.pathsep):
            os.environ["PATH"] = bindir + os.pathsep + old_path
        os.environ["M4"] = m4_bin
        if "YACC" not in os.environ:
            os.environ["YACC"] = yacc
        if "LEX" not in os.environ:
            os.environ["LEX"] = lex
        self.output.info("rolo libvc yacc/lex: YACC=%s LEX=%s M4=%s"
                         % (os.environ.get("YACC"), os.environ.get("LEX"),
                            os.environ.get("M4")))
        try:
            self.output.info("rolo util-path: %s"
                             % (self._util_path_prefix() or "(empty)"))
        except Exception:
            pass

    def _push_lowmem_flags(self):
        """Append -O1 -g0 tails for vendored builds (OOM hardening).

        Appended so the last -O/-g wins on clang/gcc: -O1 cuts peak
        optimizer memory on huge generated parsers (flex scan tables), -g0
        drops debug emission.  Scoped to private tool/lib builds only;
        rolo itself keeps profile flags untouched.  Saved values are
        stashed in _ROLO_SAVE_* vars and restored by _pop_lowmem_flags.
        Never raises.
        """
        try:
            for var in ("CFLAGS", "CXXFLAGS"):
                save = "_ROLO_SAVE_" + var
                if save not in os.environ:
                    os.environ[save] = os.environ.get(var, "")
                os.environ[var] = self._lowmem_flag_tail(var)
            self.output.info("rolo lowmem flags: CFLAGS=%r CXXFLAGS=%r"
                             % (os.environ.get("CFLAGS", ""),
                                os.environ.get("CXXFLAGS", "")))
        except Exception as exc:
            self.output.info("rolo lowmem push failed: %r" % exc)

    def _pop_lowmem_flags(self):
        """Restore flags saved by _push_lowmem_flags.  Never raises."""
        try:
            for var in ("CFLAGS", "CXXFLAGS"):
                save = "_ROLO_SAVE_" + var
                if save in os.environ:
                    old = os.environ.pop(save)
                    if old:
                        os.environ[var] = old
                    else:
                        os.environ.pop(var, None)
        except Exception:
            pass

    def _vendored_tool_env(self, src_dir):
        """Seed PWD/TMPDIR/umask hardening shared by vendored tool builds."""
        self._push_lowmem_flags()
        old_pwd = os.environ.get("PWD")
        os.environ["PWD"] = src_dir
        old_tmpdir = os.environ.get("TMPDIR")
        try:
            _btmp = os.path.join(os.path.expanduser("~"), ".conan_build_tmp")
            os.makedirs(_btmp, exist_ok=True)
            os.environ["TMPDIR"] = _btmp
        except OSError:
            pass
        try:
            old_umask = os.umask(0o022)
        except OSError:
            old_umask = None
        return old_pwd, old_tmpdir, old_umask

    def _restore_vendored_tool_env(self, old_pwd, old_tmpdir, old_umask):
        try:
            self._pop_lowmem_flags()
        except Exception:
            pass
        if old_pwd is None:
            os.environ.pop("PWD", None)
        else:
            os.environ["PWD"] = old_pwd
        if old_tmpdir is None:
            os.environ.pop("TMPDIR", None)
        else:
            os.environ["TMPDIR"] = old_tmpdir
        if old_umask is not None:
            try:
                os.umask(old_umask)
            except OSError:
                pass

    def _relax_configure_umask(self, src_dir, label):
        """Rewrite umask 077 -> 022 in a shipped configure (HMDFS, E011)."""
        cfg = os.path.join(src_dir, "configure")
        try:
            with open(cfg, encoding="utf-8", errors="ignore") as handle:
                text = handle.read()
        except OSError:
            return
        if "umask 077" in text:
            with open(cfg, "w", encoding="utf-8") as handle:
                handle.write(text.replace("umask 077", "umask 022"))
            self.output.info("vendored %s umask fix: %s" % (label, cfg))

    def _freeze_autotools_generated(self, src_dir, label):
        """Touch shipped generated files newer than patched inputs.

        True-machine failure (2026-10-14, compile stage): vendored flex
        2.6.4 died at ``make SUBDIRS=src`` with
        ``aclocal-1.15: inaccessible or not found`` / ``Error 127`` at
        ``Makefile:493: aclocal.m4``.  Root cause is mtime skew, not a
        missing tool: _downgrade_opt_in_tree rewrites configure.ac /
        Makefile.am / m4/*.m4 literals (-O2->-O1 etc.) AFTER unpack, so
        those inputs become NEWER than the shipped aclocal.m4/configure/
        Makefile.in.  The top-level Makefile's maintainer rule then tries
        to re-run ``aclocal-1.15`` (exact versioned name baked into the
        2.6.4 Makefile), which no runner provides.  m4/byacc survived only
        because they build with ``-C lib``/``-C src`` (never evaluating
        the top-level remake rule).  Fix: after every on-disk rewrite and
        before configure, utime the shipped generated files (aclocal.m4,
        configure, config.h.in, every Makefile.in) so make considers them
        up to date.  Pure os.utime (no external touch binary, no shim
        risk); never raises on missing files (logs only).
        """
        try:
            import glob as _glob
            targets = []
            for _name in ("aclocal.m4", "configure", "config.h.in",
                         "config.hin"):
                _p = os.path.join(src_dir, _name)
                if os.path.isfile(_p):
                    targets.append(_p)
            try:
                targets.extend(sorted(_glob.glob(
                    os.path.join(src_dir, "**", "Makefile.in"),
                    recursive=True)))
                targets.extend(sorted(_glob.glob(
                    os.path.join(src_dir, "**", "config.h.in"),
                    recursive=True)))
                targets.extend(sorted(_glob.glob(
                    os.path.join(src_dir, "**", "config.hin"),
                    recursive=True)))
                targets.extend(sorted(_glob.glob(
                    os.path.join(src_dir, "**", "stamp-h.in"),
                    recursive=True)))
            except Exception:
                pass
            for _p in targets:
                try:
                    os.utime(_p, None)
                except OSError as _exc:
                    self.output.info(
                        "vendored %s freeze: cannot touch %s: %r"
                        % (label, _p, _exc))
            self.output.info(
                "vendored %s autotools freeze: %d file(s) touched under %s"
                % (label, len(targets), src_dir))
        except Exception as _exc:
            self.output.info(
                "vendored %s autotools freeze failed: %r" % (label, _exc))

    def _prefer_system_rm(self):
        """Bypass the Harmonybrew rm shim for all subsequent shell-outs.

        True-machine failure (2026-10-14, compile stage): every rm fork
        dies with ``sh: /storage/.../.harmonybrew/bin/rm: Out of memory``.
        That path is a Harmonybrew shim resolved via PATH; under memory
        pressure the extra fork/exec layer fails while the real /bin/rm
        still runs.  Mitigation (no behaviour change, same GNU rm
        semantics): create ``<build_folder>/rolo-bin/rm`` as a symlink to
        the real system rm (/bin/rm preferred, /usr/bin/rm fallback),
        prepend that dir to PATH, and export RM to "<abs path> -f" so
        make's $(RM) never resolves the shim either.  The trailing -f is
        required: libtool issues `rm symlinks` that must succeed when the
        target is absent (plain rm without -f dies with Error 1, seen in
        flex 2.6.4 libfl.la link).  All make invocations use
        RM="${RM:-rm -f}" (quoted, single argv) so the embedded space
        survives as one make variable.  Never raises (logs only); when no
        system rm exists the PATH is left untouched.
        """
        try:
            sys_rm = None
            for cand in ("/bin/rm", "/usr/bin/rm"):
                try:
                    if os.path.isfile(cand) and os.access(cand, os.X_OK):
                        sys_rm = cand
                        break
                except Exception:
                    continue
            if not sys_rm:
                self.output.info("rolo rm bypass: no system rm found, skip")
                return
            bindir = os.path.join(self.build_folder, "rolo-bin")
            try:
                os.makedirs(bindir, exist_ok=True)
            except OSError:
                pass
            link = os.path.join(bindir, "rm")
            try:
                if os.path.islink(link) or os.path.isfile(link):
                    try:
                        os.unlink(link)
                    except OSError:
                        pass
                try:
                    os.symlink(sys_rm, link)
                except (OSError, NotImplementedError):
                    try:
                        shutil.copyfile(sys_rm, link)
                    except OSError:
                        pass
            except Exception as exc:
                self.output.info("rolo rm bypass: shim setup failed: %r" % exc)
                return
            old_path = os.environ.get("PATH", "")
            if bindir not in old_path.split(os.pathsep):
                os.environ["PATH"] = bindir + os.pathsep + old_path
            os.environ["RM"] = sys_rm + " -f"
            self.output.info("rolo rm bypass: rm -> %s (PATH prepend %s)"
                             % (sys_rm, bindir))
        except Exception as exc:
            self.output.info("rolo rm bypass failed: %r" % exc)

    @staticmethod
    def _lowmem_flag_tail(var):
        """Tail flags that lower cc1 memory for vendored tool builds.

        Appended (never prepended) so the last -O/-g wins on clang/gcc:
        -O1 cuts the optimizer's peak on huge generated parsers
        (byacc/flex scan tables), -g0 drops debug emission.  Scoped to
        the private m4/byacc/flex/libvc/unac builds only; rolo itself
        keeps the profile flags untouched.
        """
        prev = os.environ.get(var, "")
        tail = " -O1 -g0"
        if tail.strip() not in prev:
            return (prev + tail).strip()
        return prev

    # Memory-signature retry + on-disk opt downgrade (2026-10-14 drop fix).
    # True-machine evidence this round: m4 configure aborts mid compiler
    # probe with "Connection to 47.122.125.180 closed by remote host"
    # (outer SSH drop under memory pressure on the shared runner, right
    # after "checking whether clang understands -c and -o together").
    # Inner configure/make retries cannot resurrect a dead outer SSH
    # session, but they do absorb the inner memory signatures that precede
    # such drops ("can\'t fork", "Out of memory", "Killed", cc1 OOM) and
    # the on-disk -O/-g downgrade lowers cc1 peak so the OOM killer never
    # targets the session.  Retry is strictly gated on signature text:
    # any other failure re-raises immediately (never masks real errors,
    # never touches test scope).
    _MEM_RETRY_SIGNS = (
        "out of memory",
        "can't fork",
        "fork failed",
        "try again",
        "cannot allocate memory",
        "killed",
        "internal compiler error",
        "closed by remote host",
        "connection reset",
        "connection timed out",
    )

    @staticmethod
    def _is_mem_retryable(text):
        try:
            low = str(text).lower()
        except Exception:
            return False
        return any(s in low for s in RoloConan._MEM_RETRY_SIGNS)

    def _util_path_prefix(self):
        """Compute a PATH-hardening prefix for shell-out commands.

        True-machine evidence (2026-10-14, bison-edge round): vendored
        m4 configure dies at line 478 with `printf/sed/expr:
        inaccessible or not found` immediately after a
        tool_requires(bison/2.7) edge is added — the sourced conanbuild
        env no longer carries the shell-utility directories (same runner
        fingerprint as the green-configure round: identical 40-entry
        merged-bin listing, all native MISSING).  Mechanism-agnostic
        hardening: resolve the directories holding sh/sed/expr/printf/
        grep/awk/rm/mkdir from the OUTER process PATH (rich: harmonybrew
        + system) plus well-known system dirs, and force them to the
        front of PATH inline (emitted as `export PATH=\"<dirs>:$PATH\"`
        by _with_util_path, evaluated AFTER conanbuild.sh sourcing, so
        it survives any aggregator replace-semantics).  Test scope untouched; only
        command env.  Never raises; returns \"\" when nothing resolves.
        """
        try:
            dirs = []
            for prog in ("sh", "sed", "expr", "printf", "grep",
                         "awk", "rm", "mkdir", "cat", "mktemp", "cmp",
                         "mv", "cp", "chmod", "printenv", "env"):
                try:
                    hit = shutil.which(prog)
                except Exception:
                    hit = None
                if hit:
                    parent = os.path.dirname(hit)
                    if parent and parent not in dirs:
                        dirs.append(parent)
            # shunit2 provision dir (see _ensure_shunit2): the outer
            # os.environ PATH mutation is invisible inside the conanbuild
            # aggregation (same replace-semantics as #25), so the inline
            # export must carry it or test/run-tests dies with
            # `.: shunit2: No such file or directory` even when the file
            # was fetched fine.  Harmless for vendored builds.
            try:
                _shunit2_dir = os.path.join(self.build_folder, "rolo-tools")
                if os.path.isdir(_shunit2_dir) \
                        and _shunit2_dir not in dirs:
                    dirs.append(_shunit2_dir)
            except Exception:
                pass
            # System shunit2 (when _ensure_shunit2 took the which() branch
            # and never created rolo-tools) is equally invisible inside the
            # conanbuild aggregation; carry its directory too.
            try:
                _sys_shunit2 = shutil.which("shunit2")
                if _sys_shunit2:
                    _sys_dir = os.path.dirname(_sys_shunit2)
                    if _sys_dir and _sys_dir not in dirs:
                        dirs.append(_sys_dir)
            except Exception:
                pass
            for cand in ("/bin", "/usr/bin",
                         os.path.join(os.path.expanduser("~"),
                                      ".harmonybrew", "bin"),
                         "/storage/Users/currentUser/usr/local/bin"):
                try:
                    if cand and cand not in dirs and os.path.isdir(cand):
                        dirs.append(cand)
                except Exception:
                    pass
            if not dirs:
                return ""
            return "PATH=\"%s:$PATH\" " % ":".join(dirs)
        except Exception as exc:
            self.output.info("rolo util-path probe failed: %r" % (exc,))
            return ""

    def _with_util_path(self, cmd):
        """Export the util-PATH for the whole shell invocation.

        Uses `export PATH=\"...:$PATH\";` (not a single-command
        assignment prefix) so `;`-chained followers (`cat`, `exit`)
        share the hardened PATH too.
        """
        try:
            if not cmd or not isinstance(cmd, str):
                return cmd
            if "export PATH=" in cmd:
                return cmd
            prefix = self._util_path_prefix()
            if not prefix:
                return cmd
            # _util_path_prefix returns `PATH=\"...:$PATH\" `; convert
            # the single-command prefix into a shell-wide export.
            core = prefix.strip()
            if core.startswith("PATH="):
                core = "export " + core
            return core + "; " + cmd
        except Exception:
            return cmd

    def _run_retry(self, cmd, cwd=None, env=None, label="", tries=3,
                   cooldown=8):
        """Run self.run, retrying ONLY memory-signature failures.

        CI build #92578 evidence: native flex dies with `flex: fork
        failed` (Error 1) at libvc scanner generation.  Conan's
        exception text for self.run is the generic `Error 1 while
        executing ...` and does NOT carry the tool's stderr, so
        checking str(exc) alone never matches any memory signature and
        no retry happens.  This wrapper redirects the command output
        to a per-label log file, replays it (cat) so the CI log still
        shows it, then matches signatures against exception + log
        tail.  POSIX sh only (no pipefail/PIPESTATUS); rolo flags and
        test scope untouched.
        """
        try:
            cmd = self._with_util_path(cmd)
        except Exception:
            pass
        try:
            _safe = re.sub(r"[^A-Za-z0-9_.-]+", "_", (label or "cmd"))[:40] or "cmd"
            _log = os.path.join(self.build_folder, "rolo-retry-%s.log" % _safe)
        except Exception:
            _log = None
        last_exc = None
        for attempt in range(1, tries + 1):
            try:
                if _log:
                    _wrapped = ("%s > \"%s\" 2>&1; rc=$?; cat \"%s\"; exit $rc"
                                % (cmd, _log, _log))
                else:
                    _wrapped = cmd
                self.run(_wrapped, cwd=cwd, env=env)
                if attempt > 1:
                    self.output.info(
                        "rolo retry ok: %s (attempt %d/%d)"
                        % (label or cmd[:80], attempt, tries))
                return
            except Exception as exc:
                last_exc = exc
                msg = str(exc)
                # Include the replayed tool output: Conan's exception is
                # generic (no stderr), so the real signature (e.g. `flex:
                # fork failed`) only exists in the log file.
                try:
                    if _log and os.path.isfile(_log):
                        with open(_log, encoding="utf-8",
                                  errors="replace") as _h:
                            msg = msg + "\n" + _h.read()[-4000:]
                except Exception:
                    pass
                if not self._is_mem_retryable(msg):
                    raise
                if attempt >= tries:
                    self.output.warning(
                        "rolo retry exhausted: %s (%d/%d): %r"
                        % (label or cmd[:80], attempt, tries, exc))
                    raise
                self.output.warning(
                    "rolo retry %d/%d (memory signature): %s: %r; "
                    "cooldown %ds"
                    % (attempt, tries, label or cmd[:80], exc, cooldown))
                try:
                    time.sleep(cooldown)
                except Exception:
                    pass
        if last_exc is not None:
            raise last_exc

    def _downgrade_opt_in_tree(self, src_dir, label):
        """Replace high-opt/debug flags in vendored build scripts on disk.

        Appended -O1 -g0 tails already win for $CFLAGS, but generated
        configure/Makefile files embed literal -O2/-O3/-g/-g3 and
        -march=native/-mcpu=native defaults that still raise cc1 peak
        before the tail is evaluated.  Rewrite those literals to -O1/-g0
        (text-only, idempotent, scoped to the private vendored tree;
        rolo sources and test scope untouched).  Never raises on missing
        files; fails closed only via logs.

        Maintainer-mode guard (2026-10-14, second fix for the
        aclocal/autoheader class): autotools INPUT files (configure.ac,
        Makefile.am, m4 macros, *.in templates, aclocal.m4, configure
        itself) are NEVER rewritten here.  Rewriting them makes the
        shipped generated files (aclocal.m4/configure/config.h.in/
        Makefile.in) stale, so make fires maintainer remake rules that
        need versioned aclocal/autoheader/autoconf — absent on every
        runner (flex died at aclocal.m4 Error 127, then m4 at
        config.h.in/autoheader Error 127).  The embedded -O2 in those
        inputs only sets defaults when CFLAGS is unset, but every build
        below always exports CFLAGS, so skipping them changes no compile
        flags.  Only compiled sources and plain build scripts are
        rewritten; shipped generated files are refreshed afterwards by
        _freeze_autotools_generated.
        """
        changed = 0
        skipped_inputs = 0
        try:
            for root, _dirs, files in os.walk(src_dir):
                for name in files:
                    if name in ("config.guess", "config.sub"):
                        continue
                    # Maintainer inputs: rewriting them invalidates the
                    # shipped generated files and triggers remake rules.
                    if name in ("configure", "configure.ac", "aclocal.m4",
                                "config.h.in", "config.hin", "config.status",
                                "stamp-h1", "stamp-h.in"):
                        skipped_inputs += 1
                        continue
                    if name.endswith((".ac", ".am", ".m4", ".in")):
                        skipped_inputs += 1
                        continue
                    path = os.path.join(root, name)
                    try:
                        with open(path, encoding="utf-8",
                                  errors="ignore") as handle:
                            text = handle.read()
                    except OSError:
                        continue
                    new = text
                    for hi in ("-O3", "-O2"):
                        if hi in new:
                            new = new.replace(hi, "-O1")
                    if "-march=native" in new:
                        new = new.replace("-march=native", "-march=generic")
                    if "-mcpu=native" in new:
                        new = new.replace("-mcpu=native", "-mcpu=generic")
                    # -g3/-g2 standalone debug flags -> -g0; keep -g0.
                    new = re.sub(r"-g3\b", "-g0", new)
                    new = re.sub(r"(?<!-g)-g2\b", "-g0", new)
                    if new != text:
                        try:
                            with open(path, "w",
                                      encoding="utf-8") as handle:
                                handle.write(new)
                            changed += 1
                        except OSError:
                            pass
        except Exception as exc:
            self.output.info(
                "vendored %s opt-downgrade walk failed: %r" % (label, exc))
            return
        self.output.info(
            "vendored %s opt-downgrade: %d file(s) rewritten, %d maintainer input(s) skipped under %s"
            % (label, changed, skipped_inputs, src_dir))


    def _patch_vendored_gnulib_for_musl(self, src_dir, label):
        """Apply musl opaque-FILE fallback to bundled gnulib stdio helpers.

        True-machine failure (2026-10-14): vendored m4 1.4.19 dies in
        lib/freadahead.c with '#error "Please port gnulib freadahead.c to
        your platform!"' because its gnulib predates musl opaque-FILE
        support (HarmonyOS uses musl libc, FILE is opaque, no
        __freadahead).  Same signature as the merged coreutils/9.10 recipe,
        which carries patches/0002-lib-freadahead.c.patch (plus 0003/0004
        for freadptr/freadseek).  This helper applies the equivalent
        0002/0003/0004 hunks in place (exact-anchor, fail closed,
        idempotent): insert an '#elif defined __linux__ &&
        !defined __GLIBC__' branch before the SLOW_BUT_NO_HACKS/#else
        fallback in freadahead.c (return 0 via <stdio_ext.h> __fwriting)
        and freadptr.c (return NULL), plus the freadptrinc abort() branch
        in freadseek.c.  Applied to every matching file found under
        src_dir (vendored m4/flex bundle gnulib; byacc has none and is
        skipped).  Never raises on
        missing files (logs only); raises only on anchor drift.
        """
        import glob as _glob
        found = []
        for _name in ("freadahead.c", "freadptr.c", "freadseek.c"):
            try:
                found.extend(sorted(_glob.glob(
                    os.path.join(src_dir, "**", _name), recursive=True)))
            except Exception:
                pass
        if not found:
            self.output.info("vendored %s gnulib-musl: no freadahead/freadptr/freadseek under %s"
                             % (label, src_dir))
            return
        for _path in found:
            try:
                with open(_path, encoding="utf-8", errors="replace") as _h:
                    _text = _h.read()
            except OSError as _exc:
                self.output.warning("vendored %s gnulib-musl: cannot read %s: %r"
                                    % (label, _path, _exc))
                continue
            _base = os.path.basename(_path)
            if "defined __linux__ && !defined __GLIBC__" in _text:
                self.output.info("vendored %s gnulib-musl already patched: %s"
                                 % (label, _path))
                continue
            _new = None
            if _base == "freadseek.c":
                # coreutils 0004 precedent: freadptrinc() opens with
                # "#if HAVE___FREADPTRINC"; prepend the musl abort branch.
                if "#if HAVE___FREADPTRINC" in _text:
                    _musl_seek = ("#if defined __linux__ && !defined __GLIBC__\n"
                                  "  /* HarmonyOS/musl: opaque FILE (coreutils 9.10 0004 precedent).\n"
                                  "     Cannot increment the in-memory pointer directly.\n"
                                  "     Only reached when freadptr returns non-NULL,\n"
                                  "     which never happens for musl (see freadptr.c).  */\n"
                                  "  abort ();\n"
                                  "#elif HAVE___FREADPTRINC")
                    _new = _text.replace("#if HAVE___FREADPTRINC",
                                         _musl_seek, 1)
                elif "Please port gnulib freadseek" in _text:
                    _musl_seek = ("#elif defined __linux__ && !defined __GLIBC__\n"
                                  "  /* HarmonyOS/musl: opaque FILE (coreutils 9.10 0004 precedent).  */\n"
                                  "  abort ();\n")
                    if "#elif defined SLOW_BUT_NO_HACKS" in _text:
                        _new = _text.replace("#elif defined SLOW_BUT_NO_HACKS",
                                             _musl_seek + "#elif defined SLOW_BUT_NO_HACKS", 1)
                    else:
                        self.output.info("vendored %s gnulib-musl: no SLOW anchor in %s, skip"
                                         % (label, _path))
                        continue
                else:
                    self.output.info("vendored %s gnulib-musl: no freadseek anchor in %s, skip"
                                     % (label, _path))
                    continue
            elif _base == "freadptr.c":
                # coreutils 0003 precedent: return NULL (caller falls back
                # to fgetc/fread) via <stdio_ext.h> __fwriting guard.
                if "Please port gnulib freadptr" not in _text:
                    self.output.info("vendored %s gnulib-musl: no port-error anchor in %s, skip"
                                     % (label, _path))
                    continue
                _musl = ("#elif defined __linux__ && !defined __GLIBC__\n"
                         "  /* HarmonyOS/musl: opaque FILE (coreutils 9.10 0003 precedent).\n"
                         "     Cannot expose the internal buffer; return NULL so the\n"
                         "     caller uses fgetc/fread instead (safe fallback).  */\n"
                         "# include <stdio_ext.h>\n"
                         "  if (__fwriting (fp))\n"
                         "    return NULL;\n"
                         "  return NULL;\n")
                if "#elif defined SLOW_BUT_NO_HACKS" in _text:
                    _new = _text.replace("#elif defined SLOW_BUT_NO_HACKS",
                                         _musl + "#elif defined SLOW_BUT_NO_HACKS", 1)
                else:
                    _lines = _text.splitlines(keepends=True)
                    _err = next((_i for _i, _l in enumerate(_lines)
                                 if "Please port gnulib freadptr" in _l), None)
                    if _err is None:
                        raise RuntimeError(
                            "vendored %s gnulib-musl anchor drift in %s: "
                            "port-error vanished; refusing to guess" % (label, _path))
                    _els = next((_i for _i in range(_err - 1, -1, -1)
                                 if _lines[_i].strip() == "#else"), None)
                    if _els is None:
                        raise RuntimeError(
                            "vendored %s gnulib-musl anchor drift in %s: "
                            "no #else before port-error; refusing to guess"
                            % (label, _path))
                    _lines.insert(_els, _musl)
                    _new = "".join(_lines)
            else:
                if "Please port gnulib freadahead" not in _text:
                    self.output.info("vendored %s gnulib-musl: no port-error anchor in %s, skip"
                                     % (label, _path))
                    continue
                _musl = ("#elif defined __linux__ && !defined __GLIBC__\n"
                         "  /* HarmonyOS/musl: opaque FILE (coreutils 9.10 0002 precedent).\n"
                         "     musl provides __fwriting in <stdio_ext.h>; without\n"
                         "     __freadahead report 0 pending bytes (safe fallback).  */\n"
                         "# include <stdio_ext.h>\n"
                         "  if (__fwriting (fp))\n"
                         "    return 0;\n"
                         "  return 0;\n")
                if "#elif defined SLOW_BUT_NO_HACKS" in _text:
                    _new = _text.replace("#elif defined SLOW_BUT_NO_HACKS",
                                         _musl + "#elif defined SLOW_BUT_NO_HACKS", 1)
                else:
                    _lines = _text.splitlines(keepends=True)
                    _err = next((_i for _i, _l in enumerate(_lines)
                                 if "Please port gnulib freadahead" in _l), None)
                    if _err is None:
                        raise RuntimeError(
                            "vendored %s gnulib-musl anchor drift in %s: "
                            "port-error vanished; refusing to guess" % (label, _path))
                    _els = next((_i for _i in range(_err - 1, -1, -1)
                                 if _lines[_i].strip() == "#else"), None)
                    if _els is None:
                        raise RuntimeError(
                            "vendored %s gnulib-musl anchor drift in %s: "
                            "no #else before port-error; refusing to guess"
                            % (label, _path))
                    _lines.insert(_els, _musl)
                    _new = "".join(_lines)
            if _new is None or _new == _text:
                raise RuntimeError(
                    "vendored %s gnulib-musl anchor drift in %s: "
                    "replacement made no change; refusing to guess" % (label, _path))
            with open(_path, "w", encoding="utf-8") as _h:
                _h.write(_new)
            self.output.info("vendored %s gnulib-musl patched: %s" % (label, _path))

    def _build_vendored_m4(self, tools_prefix):
        """Build GNU m4 1.4.19 into the private toolchain prefix."""
        stamp = os.path.join(tools_prefix, ".m4-1419-built")
        m4_bin = os.path.join(tools_prefix, "bin", "m4")
        if os.path.isfile(stamp) and os.path.isfile(m4_bin):
            self.output.info("vendored m4 1.4.19 already built at %s"
                             % tools_prefix)
            return m4_bin
        src_dir = os.path.join(self.build_folder, "m4-src")
        if os.path.isdir(src_dir):
            shutil.rmtree(src_dir, ignore_errors=True)
        os.makedirs(src_dir, exist_ok=True)
        get(self, url=M4_URLS, sha256=M4_SHA256,
            destination=src_dir, strip_root=True)
        self._downgrade_opt_in_tree(src_dir, "m4")
        self._relax_configure_umask(src_dir, "m4")
        self._patch_vendored_gnulib_for_musl(src_dir, "m4")
        self._freeze_autotools_generated(src_dir, "m4")
        old_pwd, old_tmpdir, old_umask = self._vendored_tool_env(src_dir)
        try:
            sh = self._good_shell()
            benv = ["conanbuild"]
            triplet = self._triplet()
            try:
                self._run_retry(
                    "CFLAGS=\"$CFLAGS -O1 -g0\" CXXFLAGS=\"$CXXFLAGS -O1 -g0\" CONFIG_SHELL=\"%s\" SHELL=\"%s\" \"%s\" configure --prefix=\"%s\" "
                    "--disable-nls --disable-dependency-tracking --build=%s --host=%s"
                    % (sh, sh, sh, tools_prefix, triplet, triplet),
                    cwd=src_dir, env=benv)
            except Exception:
                self._dump_config_log(src_dir, "m4-configure")
                raise
            self._run_retry("CFLAGS=\"$CFLAGS -O1 -g0\" CXXFLAGS=\"$CXXFLAGS -O1 -g0\" CONFIG_SHELL=\"%s\" SHELL=\"%s\" make SHELL=%s RM=\"${RM:-rm -f}\" CFLAGS=\"$CFLAGS -O1 -g0\" CXXFLAGS=\"$CXXFLAGS -O1 -g0\" -j1 -C lib MAKEINFO=true AUTOHEADER=true AUTOCONF=true AUTOMAKE=true ACLOCAL=true"
                     % (sh, sh, sh), cwd=src_dir, env=benv)
            # Only bin/m4 is needed downstream (flex generation-time
            # M4): skip the bundled gnulib self-test tree (tests/), whose
            # build died at tests/vma-iter.o with '/bin/sh: can't fork -
            # try again' on the shared runner.  Not an upstream-suite skip:
            # rolo's own `make check` still runs in full later.
            self._run_retry("CFLAGS=\"$CFLAGS -O1 -g0\" CXXFLAGS=\"$CXXFLAGS -O1 -g0\" CONFIG_SHELL=\"%s\" SHELL=\"%s\" make SHELL=%s RM=\"${RM:-rm -f}\" CFLAGS=\"$CFLAGS -O1 -g0\" CXXFLAGS=\"$CXXFLAGS -O1 -g0\" -j1 -C src MAKEINFO=true AUTOHEADER=true AUTOCONF=true AUTOMAKE=true ACLOCAL=true"
                     % (sh, sh, sh), cwd=src_dir, env=benv)
            # install-info-am copies 3 .info files via the install shim
            # (multi-source install -> Error 64 on this runner); only
            # bin/m4 is needed, so install just src/ with empty
            # INFO_DEPS/info_TEXINFOS to no-op that target (flex uses
            # SUBDIRS=src, same reason).
            self._run_retry("CFLAGS=\"$CFLAGS -O1 -g0\" CXXFLAGS=\"$CXXFLAGS -O1 -g0\" CONFIG_SHELL=\"%s\" SHELL=\"%s\" make SHELL=%s RM=\"${RM:-rm -f}\" CFLAGS=\"$CFLAGS -O1 -g0\" CXXFLAGS=\"$CXXFLAGS -O1 -g0\" -j1 -C src install MAKEINFO=true INFO_DEPS= info_TEXINFOS= AUTOHEADER=true AUTOCONF=true AUTOMAKE=true ACLOCAL=true"
                     % (sh, sh, sh), cwd=src_dir, env=benv)
        finally:
            self._restore_vendored_tool_env(old_pwd, old_tmpdir, old_umask)
        if not os.path.isfile(m4_bin):
            raise RuntimeError(
                "vendored m4 install incomplete: missing %s" % m4_bin)
        self._run_retry("\"%s\" --version" % m4_bin, env=["conanbuild"], label="m4 smoke")
        with open(stamp, "w", encoding="utf-8") as handle:
            handle.write("m4 1.4.19 vendored build ok\n")
        # Reclaim the m4 source tree (full gnulib lib/ objects) BEFORE the
        # flex download+configure below.  Preflight evidence (2026-10-14):
        # flex configure finishes its checks and dies with "Connection ...
        # closed by remote host" right after "creating ./config.status" --
        # the outer SSH session drops under memory pressure on the shared
        # runner, which no inner retry can resurrect.  Nothing below reads
        # m4-src (rebuilds stay stamp-gated at the top of this method).
        try:
            shutil.rmtree(src_dir, ignore_errors=True)
            self.output.info("vendored m4 src tree reclaimed: %s" % src_dir)
        except Exception as exc:
            self.output.info("vendored m4 src reclaim skipped: %r" % (exc,))
        self.output.info("vendored m4 1.4.19 built at %s" % m4_bin)
        return m4_bin

    def _build_vendored_byacc(self, tools_prefix):
        """Build Berkeley byacc 2.0 into the private toolchain prefix (YACC)."""
        stamp = os.path.join(tools_prefix, ".byacc-20-built")
        yacc_bin = os.path.join(tools_prefix, "bin", "yacc")
        if os.path.isfile(stamp) and os.path.isfile(yacc_bin):
            self.output.info("vendored byacc 2.0 already built at %s"
                             % tools_prefix)
            return yacc_bin
        src_dir = os.path.join(self.build_folder, "byacc-src")
        if os.path.isdir(src_dir):
            shutil.rmtree(src_dir, ignore_errors=True)
        os.makedirs(src_dir, exist_ok=True)
        get(self, url=BYACC_URL, sha256=BYACC_SHA256,
            destination=src_dir, strip_root=True)
        self._downgrade_opt_in_tree(src_dir, "byacc")
        self._relax_configure_umask(src_dir, "byacc")
        self._freeze_autotools_generated(src_dir, "byacc")
        # The release tarball ships yaccpar.c pre-generated from
        # yaccpar.skel via awk at dist time; touch the generated files
        # so make never tries to regenerate them (the flex recipe uses
        # the same stage1scan.c bootstrap precedent; the runner may not
        # provide awk at all).
        for _gen in ("yaccpar.c", "btyaccpar.c"):
            try:
                _p = os.path.join(src_dir, _gen)
                if os.path.isfile(_p):
                    os.utime(_p, None)
            except OSError:
                pass
        old_pwd, old_tmpdir, old_umask = self._vendored_tool_env(src_dir)
        try:
            sh = self._good_shell()
            benv = ["conanbuild"]
            triplet = self._triplet()
            try:
                self._run_retry(
                    "CFLAGS=\"$CFLAGS -O1 -g0\" CXXFLAGS=\"$CXXFLAGS -O1 -g0\" CONFIG_SHELL=\"%s\" SHELL=\"%s\" \"%s\" configure --prefix=\"%s\" "
                    "--disable-dependency-tracking --build=%s --host=%s"
                    % (sh, sh, sh, tools_prefix, triplet, triplet),
                    cwd=src_dir, env=benv)
            except Exception:
                self._dump_config_log(src_dir, "byacc-configure")
                raise
            self._run_retry("CFLAGS=\"$CFLAGS -O1 -g0\" CXXFLAGS=\"$CXXFLAGS -O1 -g0\" CONFIG_SHELL=\"%s\" SHELL=\"%s\" make SHELL=%s RM=\"${RM:-rm -f}\" CFLAGS=\"$CFLAGS -O1 -g0\" CXXFLAGS=\"$CXXFLAGS -O1 -g0\" -j1 MAKEINFO=true AUTOHEADER=true AUTOCONF=true AUTOMAKE=true ACLOCAL=true"
                     % (sh, sh, sh), cwd=src_dir, env=benv)
            self._run_retry("CFLAGS=\"$CFLAGS -O1 -g0\" CXXFLAGS=\"$CXXFLAGS -O1 -g0\" CONFIG_SHELL=\"%s\" SHELL=\"%s\" make SHELL=%s RM=\"${RM:-rm -f}\" CFLAGS=\"$CFLAGS -O1 -g0\" CXXFLAGS=\"$CXXFLAGS -O1 -g0\" -j1 install MAKEINFO=true AUTOHEADER=true AUTOCONF=true AUTOMAKE=true ACLOCAL=true"
                     % (sh, sh, sh), cwd=src_dir, env=benv)
        finally:
            self._restore_vendored_tool_env(old_pwd, old_tmpdir, old_umask)
        if not os.path.isfile(yacc_bin):
            raise RuntimeError(
                "vendored byacc install incomplete: missing %s" % yacc_bin)
        self._run_retry("\"%s\" -V" % yacc_bin, env=["conanbuild"], label="byacc smoke")
        with open(stamp, "w", encoding="utf-8") as handle:
            handle.write("byacc 2.0 vendored build ok\n")
        self.output.info("vendored byacc 2.0 built at %s" % yacc_bin)
        return yacc_bin

    @staticmethod
    def _patch_flex_configure_for_hmdfs(src_dir):
        """Chmod the configure tmp-dir awk files (HMDFS mode-000 fix).

        Adapted from archives/f/flex/2.6.4 conanfile._patch_configure_for_hmdfs
        (same tarball/sha256, so the anchors are identical): on HMDFS,
        heredoc-created $ac_tmp/*.awk files get mode 000, and the generated
        config.status then dies on the first `sed < subs1.awk` with
        Permission denied.  Inject `chmod 644` after every creation point in
        `configure` once, so the chmods flow into config.status as well.
        Idempotent (guarded); raises only on anchor drift.
        """
        cfg = os.path.join(src_dir, "configure")
        try:
            with open(cfg, encoding="utf-8") as handle:
                text = handle.read()
        except OSError:
            return
        if 'chmod 644 "$ac_tmp/subs1.awk"' in text:
            return
        replacements = [
            ('echo \'BEGIN {\' >"$ac_tmp/subs1.awk" &&',
             'echo \'BEGIN {\' >"$ac_tmp/subs1.awk" &&\nchmod 644 "$ac_tmp/subs1.awk" &&'),
            ('fi < "$ac_tmp/subs1.awk" > "$ac_tmp/subs.awk" \\\n'
             '  || as_fn_error $? "could not setup config files machinery" "$LINENO" 5',
             'chmod 644 "$ac_tmp/subs1.awk"\n'
             'fi < "$ac_tmp/subs1.awk" > "$ac_tmp/subs.awk" \\\n'
             '  || as_fn_error $? "could not setup config files machinery" "$LINENO" 5\n'
             'chmod 644 "$ac_tmp/subs.awk"'),
        ]
        names = ["subs1.awk", "subs.awk"]
        missed = []
        for i, (old, new) in enumerate(replacements):
            if old in text:
                text = text.replace(old, new, 1)
            else:
                missed.append(names[i])
        if missed:
            raise RuntimeError(
                "vendored flex HMDFS awk patch missed anchors for: "
                + ", ".join(missed))
        with open(cfg, "w", encoding="utf-8") as handle:
            handle.write(text)

    def _build_vendored_flex(self, tools_prefix, m4_bin):
        """Build flex 2.6.4 into the private toolchain prefix (LEX)."""
        stamp = os.path.join(tools_prefix, ".flex-264-built")
        flex_bin = os.path.join(tools_prefix, "bin", "flex")
        if os.path.isfile(stamp) and os.path.isfile(flex_bin):
            self.output.info("vendored flex 2.6.4 already built at %s"
                             % tools_prefix)
            return flex_bin
        src_dir = os.path.join(self.build_folder, "flex-src")
        if os.path.isdir(src_dir):
            shutil.rmtree(src_dir, ignore_errors=True)
        os.makedirs(src_dir, exist_ok=True)
        get(self, url=FLEX_URLS, sha256=FLEX_SHA256,
            destination=src_dir, strip_root=True)
        self._downgrade_opt_in_tree(src_dir, "flex")
        # Bootstrap: the release tarball ships the generated scanner; reuse
        # it so flex's own build needs no yacc/lex (flex recipe precedent).
        stage1 = os.path.join(src_dir, "src", "stage1scan.c")
        shipped = os.path.join(src_dir, "src", "scan.c")
        if not os.path.isfile(stage1) and os.path.isfile(shipped):
            shutil.copyfile(shipped, stage1)
            self.output.info("vendored flex bootstrap: scan.c -> stage1scan.c")
        self._relax_configure_umask(src_dir, "flex")
        self._patch_vendored_gnulib_for_musl(src_dir, "flex")
        self._freeze_autotools_generated(src_dir, "flex")
        # HMDFS awk-tmp fix (archives/f/flex/2.6.4 precedent, same tarball).
        self._patch_flex_configure_for_hmdfs(src_dir)
        old_pwd, old_tmpdir, old_umask = self._vendored_tool_env(src_dir)
        old_m4 = os.environ.get("M4")
        old_path = os.environ.get("PATH", "")
        try:
            os.environ["M4"] = m4_bin
            bindir = os.path.join(tools_prefix, "bin")
            if bindir not in old_path.split(os.pathsep):
                os.environ["PATH"] = bindir + os.pathsep + old_path
            # HMDFS workaround (archives/f/flex/2.6.4 precedent): configure
            # and config.status stage awk/heredoc tmp files under $TMPDIR,
            # which _vendored_tool_env points at ~/.conan_build_tmp on the
            # HMDFS /storage mount (mode-000 files).  Prefer the non-HMDFS
            # /data partition when present; scoped here, restored by
            # _restore_vendored_tool_env in `finally` below.  The
            # HMBS-injected task TMPDIR is untouched outside this vendored
            # flex build.
            try:
                _cache = "/data/storage/el2/base/cache"
                if os.path.isdir(_cache):
                    os.environ["TMPDIR"] = _cache
                    self.output.info(
                        "vendored flex TMPDIR override: %s" % _cache)
            except Exception as exc:
                self.output.info(
                    "vendored flex TMPDIR override skipped: %r" % (exc,))
            sh = self._good_shell()
            benv = ["conanbuild"]
            triplet = self._triplet()
            try:
                self._run_retry(
                    "CFLAGS=\"$CFLAGS -O1 -g0\" CXXFLAGS=\"$CXXFLAGS -O1 -g0\" CONFIG_SHELL=\"%s\" SHELL=\"%s\" \"%s\" configure --prefix=\"%s\" "
                    "--disable-nls --disable-dependency-tracking ac_cv_func_reallocarray=no --build=%s --host=%s"
                    % (sh, sh, sh, tools_prefix, triplet, triplet),
                    cwd=src_dir, env=benv)
            except Exception:
                self._dump_config_log(src_dir, "flex-configure")
                raise
            # Skip doc/po (need makeinfo/gettext); the scanner lives in src/.
            # NOTE (2026-10-14 aclocal fix): build with -C src, never with
            # top-level SUBDIRS=src.  The top-level Makefile carries the
            # maintainer remake rule for aclocal.m4 (versioned
            # aclocal-1.15, absent on every runner); after the on-disk
            # -O downgrade any skew retriggers it (Error 127).  -C src
            # evaluates only src/Makefile, which has no aclocal rule.
            self._run_retry("CFLAGS=\"$CFLAGS -O1 -g0\" CXXFLAGS=\"$CXXFLAGS -O1 -g0\" CONFIG_SHELL=\"%s\" SHELL=\"%s\" make SHELL=%s RM=\"${RM:-rm -f}\" CFLAGS=\"$CFLAGS -O1 -g0\" CXXFLAGS=\"$CXXFLAGS -O1 -g0\" -j1 -C src MAKEINFO=true AUTOHEADER=true AUTOCONF=true AUTOMAKE=true ACLOCAL=true"
                     % (sh, sh, sh), cwd=src_dir, env=benv)
            self._run_retry("CFLAGS=\"$CFLAGS -O1 -g0\" CXXFLAGS=\"$CXXFLAGS -O1 -g0\" CONFIG_SHELL=\"%s\" SHELL=\"%s\" make SHELL=%s RM=\"${RM:-rm -f}\" CFLAGS=\"$CFLAGS -O1 -g0\" CXXFLAGS=\"$CXXFLAGS -O1 -g0\" -j1 -C src install MAKEINFO=true AUTOHEADER=true AUTOCONF=true AUTOMAKE=true ACLOCAL=true"
                     % (sh, sh, sh), cwd=src_dir, env=benv)
        finally:
            if old_m4 is None:
                os.environ.pop("M4", None)
            else:
                os.environ["M4"] = old_m4
            os.environ["PATH"] = old_path
            self._restore_vendored_tool_env(old_pwd, old_tmpdir, old_umask)
        if not os.path.isfile(flex_bin):
            raise RuntimeError(
                "vendored flex install incomplete: missing %s" % flex_bin)
        self._run_retry("\"%s\" --version" % flex_bin, env=["conanbuild"], label="flex smoke")
        with open(stamp, "w", encoding="utf-8") as handle:
            handle.write("flex 2.6.4 vendored build ok\n")
        self.output.info("vendored flex 2.6.4 built at %s" % flex_bin)
        return flex_bin

    def _ensure_shunit2(self, src):
        """Make a ``shunit2`` executable visible to configure's probe.

        Returns True when usable (system one or provisioned), False when the
        suite will print "Unit tests skipped".  Only a network-level failure
        falls through to False; a hash mismatch raises (supply-chain).
        """
        if shutil.which("shunit2"):
            self.output.info("shunit2 found on PATH, using system copy")
            return True
        tools_dir = os.path.join(self.build_folder, "rolo-tools")
        os.makedirs(tools_dir, exist_ok=True)
        dest = os.path.join(tools_dir, "shunit2")
        if not os.path.isfile(dest):
            self.output.info("shunit2 not on PATH, fetching %s" % SHUNIT2_URLS[0])
            data = None
            last_exc = None
            for _url in SHUNIT2_URLS:
                try:
                    request = urllib.request.Request(
                        _url, headers={"User-Agent": "conan-rolo-build"})
                    with urllib.request.urlopen(request, timeout=120) as response:
                        data = response.read()
                    self.output.info("shunit2 fetched from %s (%d bytes)"
                                     % (_url, len(data)))
                    break
                except (urllib.error.URLError, OSError, TimeoutError) as exc:
                    last_exc = exc
                    self.output.warning(
                        "shunit2 download failed from %s (%r); trying next mirror"
                        % (_url, exc))
                    continue
            if data is None:
                self.output.warning(
                    "shunit2 download failed (%r); upstream suite will report "
                    "skipped with reason" % last_exc)
                return False
            digest = hashlib.sha256(data).hexdigest()
            if digest != SHUNIT2_SHA256:
                raise RuntimeError(
                    "shunit2 hash mismatch: got %s, want %s" % (digest, SHUNIT2_SHA256))
            with open(dest, "wb") as handle:
                handle.write(data)
            try:
                os.chmod(dest, 0o755)
            except OSError:
                pass
        os.environ["PATH"] = tools_dir + os.pathsep + os.environ.get("PATH", "")
        self.output.info("provisioned shunit2 %s" % dest)
        return True

    def _parse_shunit2_log(self, log_path, shunit2_ok):
        """Parse the saved ``make check`` log into an evidence dict.

        The ONLY number source is the log file: the shunit2 "Ran N tests."
        line and its OK/FAILED summary line.  Missing/unparseable output is
        reported truthfully (never patched up to look green).
        """
        base = {
            "framework": "shunit2",
            "command": "make check",
            "discovered": UPSTREAM_TEST_TOTAL,
        }
        try:
            with open(log_path, encoding="utf-8", errors="replace") as handle:
                log = handle.read()
            # shunit2 2.1.8 colorizes its summary whenever tput claims colors
            # (preflight showed a lone green OK: runner variance across the
            # shared fleet).  Strip ANSI CSI so the single-source regexes
            # below match plain or colored output identically; numbers still
            # come only from this log file, never guessed.
            log = re.sub(chr(27) + '\[[0-9;]*[A-Za-z]', '', log)
        except OSError as exc:
            base.update(status="error", executed=0, passed=0, failed=0,
                        skipped=0,
                        reason="make_check.log unreadable: %r" % exc)
            return base
        if "Unit tests skipped" in log and not re.search(r"^Ran \d+ tests\.", log,
                                                          flags=re.MULTILINE):
            base.update(status="skipped", executed=0, passed=0, failed=0,
                        skipped=UPSTREAM_TEST_TOTAL,
                        reason=("configure found no shunit2 on PATH "
                                "(provisioned=%s); test/Makefile check target "
                                "printed 'Unit tests skipped', 0 of %d cases ran")
                        % (shunit2_ok, UPSTREAM_TEST_TOTAL))
            return base
        ran = re.search(r"^Ran (\d+) tests\.", log, flags=re.MULTILINE)
        if not ran:
            base.update(status="error", executed=0, passed=0, failed=0,
                        skipped=0,
                        reason=("no shunit2 'Ran N tests.' summary in "
                                "make_check.log; refusing to guess counts"))
            return base
        total = int(ran.group(1))
        failed_match = re.search(r"^FAILED", log, flags=re.MULTILINE)
        ok_match = re.search(r"^OK", log, flags=re.MULTILINE)
        if ok_match and not failed_match:
            base.update(status="passed", executed=total, passed=total,
                        failed=0, skipped=0)
            return base
        if failed_match:
            failures = re.search(r"failures=(\d+)", log)
            errors = re.search(r"errors=(\d+)", log)
            skipped = re.search(r"skipped=(\d+)", log)
            failed = int(failures.group(1)) if failures else total
            failed += int(errors.group(1)) if errors else 0
            n_skipped = int(skipped.group(1)) if skipped else 0
            passed = total - failed - n_skipped
            if passed < 0 or failed < 0 or n_skipped < 0:
                base.update(status="error", executed=total, passed=0,
                            failed=total, skipped=0,
                            reason=("shunit2 summary counts inconsistent "
                                    "(see make_check.log); failing closed"))
                return base
            base.update(status="failed" if passed == 0 else "partial",
                        executed=total, passed=passed, failed=failed,
                        skipped=n_skipped,
                        reason=("shunit2 suite reported FAILED "
                                "(see make_check.log)"))
            return base
        base.update(status="error", executed=total, passed=0, failed=0,
                    skipped=0,
                    reason=("shunit2 'Ran N tests.' present but no OK/FAILED "
                            "verdict; refusing to guess counts"))
        return base
