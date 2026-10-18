#!/usr/bin/env python3
"""Conan recipe — libmems 1.6.0-4725 (Autotools).

libmems is the Mauve project's C++ library for DNA string matching and
comparative genomics (maximal exact matches, seed-and-extend alignment
building blocks used by progressiveMauve). Upstream is maintained in the
Mauve Subversion trunk; the Debian Med team publishes the versioned
snapshot tarball that this recipe consumes (see conandata.yml).

Build system: GNU Autotools. The snapshot ships configure.ac plus an
autogen.sh wrapper but no pre-generated configure script, so build()
runs autoreconf before configuring (same step Debian's own build takes).

Dependencies (from configure.ac PKG_CHECK_MODULES + AX_BOOST_*):
  libGenome-1.3 >= 1.3.1, libMUSCLE-3.7 >= 1.0.0, plus Boost
  (filesystem / program_options / iostreams). Neither libgenome nor
  libmuscle is published in the ohpcd registry (preflight:
  "Unable to find 'libgenome/1.3.1' in remotes"), so per aggregated
  experience #1 the recipe vendors both as private static sub-builds:
  conandata.yml `vendored` holds their official Debian-pool sources
  (sha256 unchanged from the .dsc files); build() downloads them with
  conan get(), builds static into build_folder/private prefix and merges
  the archives/headers/.pc files into this package. Boost IS published,
  so it stays a direct remote requires() (transitive_headers/libs); only
  the unpublished remotes are vendored. Version choice (true-machine
  2026-10-16): boost/1.85.0, NOT the 1.91.x line: the 1.91.x recipe installs
  only a BOOST_INCLUDE_LIBRARIES header closure (filesystem / graph /
  iostreams / multiprecision / program_options / regex / thread) and omits
  headers outside it (arg_router precedent: boost/process/*.hpp absent;
  here boost/multi_array.hpp absent, fatal in GreedyBreakpointElimination.h).
  boost/1.85.0 copies the entire boost/ header tree plus compiled
  filesystem / iostreams / program_options (arg_router + unilog precedent,
  remote OHOS binary present; its transitive zlib/1.3.1 is published too).
  No requires() entry points at an unpublished remote (L0i/R36 hard gate).

Upstream tests: none. The tree has no check/test target (only a
commented-out wx-dependent TestSML sketch) and ships no testsuite
directory. The no_tests audit lives in test_package/MANIFEST.yml and the
HMBS_UPSTREAM_TEST_RESULT marker is emitted from test_package/test()
every round (cache-hit safe).

R26: not a system-name library (no libMems in /lib or /lib64), shared
option kept, default static.
R32: settings.os compared with in ("Linux", "OHOS").
R33: no bare ${CC}/${CFLAGS} in self.run(); everything comes from
AutotoolsToolchain / conanbuild env.
R49: vendored injection target is build_folder private prefix, never the
shared /usr/local SYS_PREFIX.
"""

import os
import shlex
import shutil
from pathlib import Path

from conan import ConanFile
from conan.errors import ConanException, ConanInvalidConfiguration
from conan.tools.env import Environment
from conan.tools.files import apply_conandata_patches, copy, export_conandata_patches, get, rm, rmdir, replace_in_file
from conan.tools.gnu import Autotools, AutotoolsToolchain
from conan.tools.layout import basic_layout


class LibmemsConan(ConanFile):
    name = "libmems"
    version = "1.6.0-4725"
    description = "Mauve library to support DNA string matching and comparative genomics"
    license = "GPL-2.0-or-later"
    homepage = "http://sourceforge.net/p/mauve/code/HEAD/tree/libMems/trunk/"
    url = "https://gitcode.com/OpenHarmonyPCDeveloper/build_in_harmonyos"

    package_type = "library"
    settings = "os", "compiler", "build_type", "arch"
    options = {"shared": [True, False]}
    default_options = {"shared": False}

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        # configure.ac AX_BOOST_BASE hard-checks Boost headers >= 1.34.0 plus
        # filesystem / program_options / iostreams (see docstring). True-machine
        # 2026-10-15: `checking for Boost headers version >= 1.34.0... no` /
        # `configure: error: cannot find Boost headers`. True-machine 2026-10-16:
        # `GreedyBreakpointElimination.h:10: fatal error:
        # 'boost/multi_array.hpp' file not found` even though configure's own
        # header probe passed with the same -I flags, so the header is genuinely
        # absent from the boost/1.91.0.1.1 package: that recipe installs only a
        # BOOST_INCLUDE_LIBRARIES closure (see docstring; arg_router precedent).
        # boost/1.85.0 ships the entire boost/ header tree plus all three
        # compiled components (arg_router/unilog precedent, remote OHOS binary
        # present), so require it instead (NOT vendored: aggregated exp #1 only
        # applies to unpublished remotes; boost exists remotely).
        self.requires("boost/1.85.0", transitive_headers=True, transitive_libs=True)

    def build_requirements(self):
        # Snapshot + both vendored deps need autoreconf (configure.ac only).
        # Versions match the already-published OHOS tool recipes proven by
        # the libgenome 1.3.11 archive in this repo (notes.md evidence).
        # m4/1.4.19 is explicit (ots/yp-tools/zimpl precedent): autom4te
        # forks `m4` by bare name, so the binary must come from a pinned
        # tool_requires rather than whatever the shared worker happens to
        # have on PATH.
        self.tool_requires("autoconf/2.72")
        self.tool_requires("automake/1.18")
        self.tool_requires("libtool/2.5.4.1")
        self.tool_requires("m4/1.4.19")
        self.tool_requires("perl/5.42.2")

    def layout(self):
        basic_layout(self)

    def source(self):
        # Main source only; vendored deps are fetched inside build() so a
        # graph-resolution failure can never block on unpublished remotes.
        main = {k: v for k, v in self.conan_data["sources"].items()
                if k in ("url", "sha256")}
        get(self, **main, strip_root=True)

    def _writable_tmpdir(self):
        """E002: OHOS /tmp is an erofs read-only mount.

        Prefer the task-level temp dir injected by hmbs
        (HMBS_TMPDIR/TMPDIR/TMP/TEMP); fall back to a package-isolated
        dir under $HOME. The directory is created idempotently.
        """
        for var in ("HMBS_TMPDIR", "TMPDIR", "TMP", "TEMP"):
            value = os.environ.get(var)
            if value:
                tmpdir = value
                break
        else:
            tmpdir = os.path.join(os.path.expanduser("~"), "tmp", "libmems-1.6.0-4725")
        try:
            os.makedirs(tmpdir, exist_ok=True)
        except OSError:
            tmpdir = self.build_folder or os.getcwd()
        return tmpdir

    def _ohos_sh(self):
        """cvsgraph DRAFT-cvsgraph-bash-getcwd: hnp bash getcwd broken on HMDFS.

        /data/service/hnp/bin/bash fails getcwd in conan build cache dirs
        (shell-init/job-working-directory noise, varied errno) and old/new
        autoconf aborts with 'working directory cannot be determined', while
        /system/bin/sh (toybox) is clean in the same directory. Probe rule
        (E386): stdout/stderr must be diagnosis-free, not just rc==0.
        """
        for cand in ("/system/bin/sh", "/bin/sh"):
            if os.path.exists(cand):
                return cand
        return "/bin/sh"

    def _fix_configure_umask(self, src_dir):
        """fcrackzip/cvsgraph-proven: umask 077 mktemp dirs are unusable on OHOS.

        No-op when the idiom is absent (fail-open, keep real error visible).
        """
        conf = os.path.join(src_dir, "configure")
        if os.path.isfile(conf):
            try:
                replace_in_file(self, conf, "umask 077", "umask 022")
            except Exception:
                pass

    def _clean_configure_cache(self, src_dir):
        """Remove stale autoconf cache so a reused slot never mixes runs.

        True-machine 2026-10-16: main configure reports
        `checking for the Boost filesystem library... (cached) yes` but
        `checking for boost/program_options.hpp... no` in the SAME run.
        `(cached)` proves config.cache survived from an earlier preflight
        (boost 1.91.x attempt) while program_options was probed fresh with
        the new boost 1.85.0 -I set: a split-brain probe, not a missing
        remote package (the recipe's fail-closed header verify passed, so
        the header IS under the boost package_folder). Prior round changed
        flag aggregation only and kept the cache, so the same fingerprint
        recurred. Different route this round: delete config.cache /
        config.status / config.log / autom4te.cache before EVERY configure
        (vendored + main share this helper), fail-open so cleanup never
        masks the real error.
        """
        for _name in ("config.cache", "config.status", "config.log"):
            try:
                _p = os.path.join(src_dir, _name)
                if os.path.isfile(_p):
                    os.remove(_p)
            except OSError:
                pass
        try:
            _d = os.path.join(src_dir, "autom4te.cache")
            if os.path.isdir(_d) and not os.path.islink(_d):
                shutil.rmtree(_d, ignore_errors=True)
        except OSError:
            pass

    def _dump_config_log(self, src_dir, max_lines=40):
        """Emit config.log evidence for the failed probe (fail-open).

        Round-3 rewrite: prior keyword-only dumps hid the true inner
        compiler error. config.log line 1963 shows the compiler DID open
        boost/program_options/options_description.hpp (so -I is correct)
        and failed at its line 16 -- the keyword filter kept that opener
        but dropped the following error lines (no keyword match). This
        version dumps (a) the tail, (b) an 80-line window before the
        `cannot find boost/program_options` error, and (c) every
        error/fatal line with context, so the next round sees the inner
        cause (missing -D vs missing inner header) directly.
        """
        _log = os.path.join(src_dir, "config.log")
        try:
            if not os.path.isfile(_log):
                self.output.warning("OHOS port: no config.log under %s" % src_dir)
                return
            with open(_log, "r", encoding="utf-8", errors="replace") as _h:
                _lines = _h.read().splitlines()
        except OSError:
            return
        self.output.warning("OHOS port: config.log tail (%d lines) under %s"
                            % (max_lines, src_dir))
        for _l in _lines[-max_lines:]:
            self.output.warning("config.log| %s" % _l[:400])
        _err_at = next((i for i, l in enumerate(_lines)
                        if "cannot find boost/program_options" in l), None)
        if _err_at is not None:
            _lo = max(0, _err_at - 80)
            self.output.warning("OHOS port: config.log window [%d..%d] before program_options error"
                                % (_lo + 1, _err_at + 1))
            for _i in range(_lo, _err_at + 1):
                self.output.warning("config.log@%d| %s" % (_i + 1, _lines[_i][:400]))
        _nerr = 0
        for _i, _l in enumerate(_lines):
            _ll = _l.lower()
            if ("error:" in _ll or "fatal error" in _ll) and _nerr < 25:
                _lo = max(0, _i - 3)
                for _j in range(_lo, min(len(_lines), _i + 4)):
                    self.output.warning("config.log-err@%d| %s" % (_j + 1, _lines[_j][:400]))
                _nerr += 1
        for _i, _l in enumerate(_lines):
            if ("program_options" in _l or "BOOST_CPPFLAGS" in _l
                    or "BOOST_SP_NO_PTHREAD" in _l or "ac_cv_header_boost_program_options" in _l):
                pass
            else:
                continue
            if _i < len(_lines) and _err_at is not None and abs(_i - _err_at) <= 80:
                continue  # already shown in window
            self.output.warning("config.log-hit@%d| %s" % (_i + 1, _l[:400]))

    def _run_configure_safe(self, src_dir, args, tmpdir=None):
        """Run configure via an explicit clean shell with CONFIG_SHELL fixed.

        - Explicit `sh configure` bypasses hmdfs shebang-exec refusal.
        - CONFIG_SHELL fixed so autoconf does not bake hnp bash into
          Makefile SHELL / config.status (make phase would re-hit the bug).
        - TMPDIR kept off /tmp (E002, HMBS-injected writable dir preferred).
        """
        self._fix_configure_umask(src_dir)
        self._clean_configure_cache(src_dir)
        # Round-3: prior file-deletion did not clear the "(cached)" hit
        # (cache file lives elsewhere or configure recreates it), so ALSO
        # disable the autoconf cache for every configure via
        # --cache-file=/dev/null (kept alongside deletion, fail-open).
        if "--cache-file" not in args:
            args = args + " --cache-file=/dev/null"
        sh = self._ohos_sh()
        conf = os.path.join(src_dir, "configure")
        tmp = tmpdir or self._writable_tmpdir()
        try:
            os.makedirs(tmp, exist_ok=True)
        except OSError:
            pass
        cmd = ("TMPDIR=%s CONFIG_SHELL=%s %s %s %s" % (
            shlex.quote(tmp), shlex.quote(sh), shlex.quote(sh),
            shlex.quote(conf), args))
        env = Environment()
        env.define("TMPDIR", tmp)
        env.define("TMP", tmp)
        env.define("TEMP", tmp)
        env.define("CONFIG_SHELL", sh)
        env.define("SHELL", sh)
        # 2026-10-17 preflight focus: `Connection to 47.122.125.180 closed
        # by remote host` right after vendored libmuscle
        # `checking for objdir... .libs` with no compiler error, and CI 97047
        # `autom4te[2]: can't fork` 3/3 at vendored libgenome bootstrap.
        # Both are transient exec-channel pressure on the single-slot
        # device/shared worker, not a deterministic configure.ac error.
        # autoreconf already retries; configure was single-shot, so any
        # transient EAGAIN during its compiler probes failed the whole
        # triple-autotools build. Retry configure the same way (3 attempts,
        # backoff 15s*attempt). A deterministic configure error fails all
        # attempts with the same log; config.log is dumped only on the
        # final failure to avoid log spam. No test scope changed.
        import time as _time2
        _last = None
        for _attempt in (1, 2, 3):
            try:
                with env.vars(self).apply():
                    self.run(cmd, cwd=src_dir, env="conanbuild")
                _last = None
                break
            except ConanException as _exc:
                _last = _exc
                if _attempt >= 3:
                    break
                self.output.warning(
                    "OHOS port: configure attempt %d/3 failed, "
                    "sleeping before retry (transient exec pressure): %s"
                    % (_attempt, str(_exc)[:200]))
                try:
                    _time2.sleep(15 * _attempt)
                except Exception:
                    pass
        if _last is not None:
            self._dump_config_log(src_dir)
            raise _last

    def _private_prefix(self):
        """R49: vendored injection target under build_folder (CI-isolated)."""
        prefix = os.path.join(self.build_folder, "private")
        os.makedirs(prefix, exist_ok=True)
        os.makedirs(os.path.join(prefix, "lib", "pkgconfig"), exist_ok=True)
        return prefix

    def _patch_config_guess(self, src_dir):
        """Map HarmonyOS uname to the OHOS triplet (libgenome evidence).

        Post-autoreconf config.guess has no HarmonyOS case, so cross
        configure would guess unknown. Insert the same stanza the proven
        libgenome recipe uses; no-op when already present or when the
        anchor format is unexpected (fail-open here, configure will show
        the real error instead of a guessed patch failure).
        """
        candidates = [
            os.path.join(src_dir, "config", "config.guess"),
            os.path.join(src_dir, "config.guess"),
        ]
        for path in candidates:
            if not os.path.isfile(path):
                continue
            try:
                with open(path, "r", encoding="utf-8", errors="replace") as handle:
                    contents = handle.read()
            except OSError:
                continue
            if "HarmonyOS" in contents:
                return
            anchor = "    *:NetBSD:*:*)"
            if contents.count(anchor) != 1:
                continue
            harmony = ("    *:HarmonyOS:*:*)\n"
                       "        echo \"$UNAME_MACHINE-unknown-linux-ohos\"\n"
                       "        exit ;;\n")
            try:
                with open(path, "w", encoding="utf-8") as handle:
                    handle.write(contents.replace(anchor, harmony + anchor, 1))
            except OSError:
                continue
            return

    def _fix_boost_filesystem_v3(self, src_dir):
        """Port Boost.Filesystem v2 calls to v3 (modern Boost evidence).

        True-machine 2026-10-16: `../libMems/Files.h:82:20: error: no
        member named 'branch_path' in 'boost::filesystem::path'` and
        `:86:21: error: no member named 'leaf'`. Root cause is API age,
        not a missing package: libmems r4725 targets Filesystem v2
        (`branch_path()`/`leaf()`), removed after Boost 1.48 in favour
        of v3 (`parent_path()`/`filename()`); the published
        boost/1.91.0.1.1 only ships v3. v2 `branch_path()` returned a
        path just like v3 `parent_path()`, and v3 `filename()` returns a
        path so the existing `.string()` suffix stays valid. Walk the
        main tree once and rewrite both spellings idempotently
        (re-runs find nothing and return). Fail-open with a warning when
        nothing matches so the compiler still shows the real error.
        """
        import re
        total = 0
        for _root, _dirs, _files in os.walk(src_dir):
            for _name in _files:
                if not _name.endswith((".h", ".hpp", ".cpp", ".cc", ".cxx")):
                    continue
                _p = os.path.join(_root, _name)
                try:
                    with open(_p, "r", encoding="utf-8", errors="replace") as _h:
                        _text = _h.read()
                except OSError:
                    continue
                _new = _text
                _new = _new.replace(".branch_path()", ".parent_path()")
                _new = _new.replace(".leaf()", ".filename()")
                if _new != _text:
                    try:
                        with open(_p, "w", encoding="utf-8", newline="\n") as _h:
                            _h.write(_new)
                    except OSError:
                        continue
                    total += 1
        if total:
            self.output.info("OHOS port: Boost.Filesystem v2->v3 rewrote %d files" % total)
        else:
            self.output.warning("Boost.Filesystem v2 idiom not found under %s" % src_dir)

    def _fix_register_keyword(self, src_dir):
        """Strip the removed `register` storage class (C++17 evidence).

        True-machine 2026-10-17 (clang 15 + libc++, Aligner.lo):
        `libMems/HomologyHMM/algebras.h:190:5: error: ISO C++17 does not
        allow 'register' storage class specifier [-Wregister]` (5 sites:
        lines 190/209/216/229/236, `register BFloat` / `register double`).
        Root cause is language removal, not a missing package: `register`
        was deprecated in C++11 and removed in C++17; upstream r4725
        (2009-era) still spells it. The keyword was only an optimization
        hint, so deleting the word preserves semantics. Rewrite is a
        word-boundary `register` + whitespace -> "" over C/C++ sources
        tree-wide (covers any other TU with the same idiom), idempotent
        (re-runs match nothing). Fail-open with a warning when nothing
        matches so the compiler still shows the real error.
        """
        import re
        pattern = re.compile(r"\bregister\s+")
        total_files = 0
        total_hits = 0
        for _root, _dirs, _files in os.walk(src_dir):
            for _name in _files:
                if not _name.endswith((".h", ".hpp", ".cpp", ".cc", ".cxx", ".c")):
                    continue
                _p = os.path.join(_root, _name)
                try:
                    with open(_p, "r", encoding="utf-8", errors="replace") as _h:
                        _text = _h.read()
                except OSError:
                    continue
                _new, _n = pattern.subn("", _text)
                if _n:
                    try:
                        with open(_p, "w", encoding="utf-8", newline="\n") as _h:
                            _h.write(_new)
                    except OSError:
                        continue
                    total_files += 1
                    total_hits += _n
        if total_hits:
            self.output.info("OHOS port: `register` storage class stripped: %d occurrence(s) in %d file(s)"
                             % (total_hits, total_files))
        else:
            self.output.warning("`register` storage-class idiom not found under %s" % src_dir)

    def _fix_boost_tuple_pushback(self, src_dir):
        """Build boost::tuple values directly instead of std make_tuple.

        True-machine 2026-10-17 (clang 15 + libc++, ProgressiveAligner.lo):
        `ProgressiveAligner.cpp:1602:12: error: no matching member function
        for call to 'push_back'` with
        `cga_list.push_back(make_tuple(c.Copy(), &bs[mI],
        ancestral_matches[mI]))`. The candidate expects
        `const vector<boost::tuples::tuple<...>>::value_type`
        (boost::tuples::tuple) but the argument is `std::tuple`
        (unqualified make_tuple resolved to std::make_tuple via <tuple>).
        Root cause is a tuple-library mismatch, not a missing package:
        the container holds boost::tuples::tuple while the value is built
        with std::make_tuple; libc++ strictly rejects the conversion.
        The fix rewrites each `<vec>.push_back(make_tuple(` site into
        `<vec>.push_back(decltype(<vec>)::value_type(` so the value is
        constructed as the container's own value_type (works for both
        boost::tuple and std::tuple containers, no namespace guess).
        Idempotent (re-runs find no make_tuple behind push_back).
        Fail-open with a warning when nothing matches.
        """
        import re
        pattern = re.compile(r"(\w+)\.push_back\s*\(\s*make_tuple\s*\(")
        total_files = 0
        total_hits = 0
        for _root, _dirs, _files in os.walk(src_dir):
            for _name in _files:
                if not _name.endswith((".h", ".hpp", ".cpp", ".cc", ".cxx")):
                    continue
                _p = os.path.join(_root, _name)
                try:
                    with open(_p, "r", encoding="utf-8", errors="replace") as _h:
                        _text = _h.read()
                except OSError:
                    continue
                def _repl(_m):
                    return "%s.push_back(decltype(%s)::value_type(" % (_m.group(1), _m.group(1))
                _new, _n = pattern.subn(_repl, _text)
                if _n:
                    try:
                        with open(_p, "w", encoding="utf-8", newline="\n") as _h:
                            _h.write(_new)
                    except OSError:
                        continue
                    total_files += 1
                    total_hits += _n
        if total_hits:
            self.output.info("OHOS port: boost::tuple push_back fixed: %d site(s) in %d file(s)"
                             % (total_hits, total_files))
        else:
            self.output.warning("boost::tuple push_back(make_tuple idiom not found under %s" % src_dir)

    def _fix_libcxx_swap_noexcept(self, src_dir):
        """Add the libc++-mandated noexcept to the std::swap specialization.

        True-machine 2026-10-16 (clang 15 + libc++, FileSML.lo and other
        libMems TUs): `CompactGappedAlignment.h:811:6: error:
        'swap<mems::CompactGappedAlignment<>>' is missing exception
        specification 'noexcept(is_nothrow_move_constructible<...>::value
        && is_nothrow_move_assignable<...>::value)'`. Root cause is toolchain
        strictness, not a missing package: libc++ declares the primary
        std::swap with a conditional noexcept, and Clang rejects an explicit
        specialization whose exception specification does not match. The
        2009-era upstream header predates conditional noexcept and declares
        the specialization bare. The fix appends exactly the spec the
        diagnostic mandates, spelled with `std::` / `mems::` qualifications
        so it resolves from any scope (inside `namespace std` or outside),
        on every matching declaration/definition lacking noexcept
        (idempotent: re-runs match nothing and return). Fail-closed when the
        pattern is absent so the compiler still shows the real error.
        """
        import re
        path = os.path.join(src_dir, "libMems", "CompactGappedAlignment.h")
        if not os.path.isfile(path):
            found = None
            for _root, _dirs, _files in os.walk(src_dir):
                if "CompactGappedAlignment.h" in _files:
                    found = os.path.join(_root, "CompactGappedAlignment.h")
                    break
            if found is None:
                raise ConanException(
                    "CompactGappedAlignment.h not found under %s; refusing "
                    "to fake the libc++ swap fix" % src_dir)
            path = found
        try:
            with open(path, "r", encoding="utf-8", errors="replace") as handle:
                text = handle.read()
        except OSError as exc:
            raise ConanException("cannot read %s: %s" % (path, exc))
        spec = ("noexcept(std::is_nothrow_move_constructible"
                "<mems::CompactGappedAlignment<>>::value && "
                "std::is_nothrow_move_assignable"
                "<mems::CompactGappedAlignment<>>::value)")
        pattern = re.compile(
            r"(void\s+(?:std::)?swap\s*\(\s*mems::CompactGappedAlignment<>\s*&\s*\w*\s*,"
            r"\s*mems::CompactGappedAlignment<>\s*&\s*\w*\s*\))"
            r"(?!\s*noexcept)")
        updated, count = pattern.subn(
            lambda match: match.group(1) + " " + spec, text)
        if count == 0:
            if "swap" in text and "noexcept" in text:
                return
            raise ConanException(
                "std::swap specialization pattern not found in %s; refusing "
                "to write a guessed edit" % path)
        try:
            with open(path, "w", encoding="utf-8", newline="\n") as handle:
                handle.write(updated)
        except OSError as exc:
            raise ConanException("cannot write %s: %s" % (path, exc))
        self.output.info(
            "OHOS port: libc++ swap noexcept added in %s (%d site(s))" % (path, count))

    def _fix_vendored_genome_portability(self, src_dir):
        """Replicate the proven libgenome abs() guard (OHOS libc++ evidence).

        Unconditional global `int64 abs(int64)` in libGenome/gnDefs.cpp
        conflicts with libc++ `abs(long long) noexcept` under clang 15.
        The in-repo libgenome archive proves that scoping it to legacy
        compilers fixes the AArch64 build (patches/0003, context lines
        ` // some compilers...` / `int64 abs( int64 a ){` /
        ` \\treturn a < 0 ? -a : a;` / `}`); apply the same edit to the
        vendored copy (test-only patches 0001/0002 are not needed for a
        private static dep whose check target we never run).

        Previous revision matched the tail with an exact `"\\treturn...\\n }"`
        literal, but the file's return line carries a leading space
        (`" \\treturn..."`) so the `#endif` was never written, leaving an
        unterminated `#if` (true-machine error `gnDefs.cpp:8:2: error:
        unterminated conditional directive`). This version matches the
        function body with a whitespace-tolerant regex, verifies the
        `#endif`, and self-heals a guard-without-endif leftover from a
        reused build-folder copy instead of stacking a second guard.
        Fail-closed: an unrecognised abs() shape raises instead of
        writing a half-guarded file.
        """
        import re
        path = os.path.join(src_dir, "libGenome", "gnDefs.cpp")
        if not os.path.isfile(path):
            return
        try:
            with open(path, "r", encoding="utf-8", errors="replace") as handle:
                text = handle.read()
        except OSError:
            return
        guard = "#if (defined(__GNUG__) && (__GNUC__ <= 2)) || defined(__INTEL_COMPILER) || defined(_MSC_VER)"
        if guard in text:
            tail = text.split(guard, 1)[1]
            if "#endif" in tail:
                return
            # Broken reuse: guard present but never closed. Close it after
            # the abs() body's closing brace.
            close = re.search(r"int64\s+abs\s*\(\s*int64\s+a\s*\)\s*\{.*?^\s*\}",
                              tail, flags=re.DOTALL | re.MULTILINE)
            if close is None:
                raise ConanException(
                    "vendored gnDefs.cpp has unclosed abs() guard and "
                    "unrecognised body shape in %s" % path)
            insert_at = text.index(guard) + len(guard) + close.end()
            text = text[:insert_at] + "\n#endif" + text[insert_at:]
            try:
                with open(path, "w", encoding="utf-8", newline="\n") as handle:
                    handle.write(text)
            except OSError:
                pass
            return
        pattern = re.compile(
            r"(// some compilers don't have abs\(\) for 64 bit ints[^\n]*\n)"
            r"(\s*int64\s+abs\s*\(\s*int64\s+a\s*\)\s*\{\s*\n"
            r"\s*return a < 0 \? -a : a;\s*\n"
            r"\s*\})",
            flags=re.DOTALL)
        match = pattern.search(text)
        if match is None:
            raise ConanException(
                "vendored gnDefs.cpp abs() pattern not found in %s; "
                "refusing to write a half-guarded file" % path)
        text = (text[:match.start()] + match.group(1) + guard + "\n"
                + match.group(2) + "\n#endif" + text[match.end():])
        try:
            with open(path, "w", encoding="utf-8", newline="\n") as handle:
                handle.write(text)
        except OSError:
            pass

    def _automake_entrypoints(self):
        """Isolate Autotools bootstrap on host Perl (libgenome E8212 evidence).

        conanbuild env exposes Conan perl/5.42.2 PERL5LIB including XS
        auto/Cwd/Cwd.so built for its own ABI. The HNP/system autoreconf
        (#!/.../perl shebang, e.g. /data/service/hnp/bin/autoreconf) then
        loads that XS via the polluted PERL5LIB and dies with
        "Perl_my_cxt_init: symbol not found" at Cwd.pm line 82 before any
        configure work. Setting PERL alone is not enough.
        Reuse the proven libgenome 1.3.11 recipe logic: run the Autoconf
        package's bin/autoreconf with host perl, restrict PERL5LIB to the
        pure-Perl automake/autoconf share dirs, and route aclocal/automake
        through host-perl wrappers preserving the package relocations.
        """
        package = Path(self.dependencies.build["automake"].package_folder)
        system_perl = shutil.which("perl")
        if not system_perl:
            raise ConanInvalidConfiguration("host Perl is required for Autotools bootstrap")
        perl = Path(system_perl).resolve()
        conan_perl = Path(self.dependencies.build["perl"].package_folder, "bin", "perl").resolve()
        if perl == conan_perl:
            raise ConanInvalidConfiguration("Autotools bootstrap must not use Conan Perl from the user cache")
        overlay = Path(self.build_folder, ".libmems-automake")
        overlay.mkdir(exist_ok=True)
        scripts = {
            "aclocal": (".aclocal-real", [
                "--automake-acdir=" + str(package / "share" / "aclocal-1.18"),
                "--system-acdir=" + str(package / "share" / "aclocal")]),
            "automake": (".automake-real", [
                "--libdir=" + str(package / "share" / "automake-1.18")]),
        }
        result = {}
        for name, (real_name, arguments) in scripts.items():
            real = package / "bin" / real_name
            if not real.is_file():
                raise ConanInvalidConfiguration("automake tool payload missing: " + str(real))
            wrapper = overlay / name
            argv = " ".join(shlex.quote(part) for part in (str(real), *arguments))
            wrapper.write_text("#!/bin/sh\nexec " + shlex.quote(str(perl)) +
                               " " + argv + ' "$@"\n', encoding="utf-8")
            wrapper.chmod(0o700)
            result[name] = wrapper
        result["perl"] = perl
        autoconf = Path(self.dependencies.build["autoconf"].package_folder)
        # True-machine 2026-10-17: `perl .autoreconf-real` + host-perl
        # direct-exec overlay wrappers for autom4te/autoconf/autoheader/...
        # fail deterministically 3/3 with
        # `.autom4te-real: error: m4sugar/m4sugar.m4: no such file`.
        # Root cause is relocation, not fork pressure: the Conan autoconf
        # package is relocatable and its bin/* shell wrappers carry the
        # pkgdatadir relocation (share/autoconf with m4sugar/autoconf/
        # trailer.m4). Bypassing them with `perl .*-real` loses that
        # setup, so autom4te's `m4 --include` no longer finds the data
        # files. The prior fork-exhaustion (`can't fork - try again`) was
        # transient shared-worker pressure (retry absorbs it); the m4sugar
        # miss is deterministic and worse. Different route this round:
        # invoke the shell wrapper bin/autoreconf via an explicit clean
        # `sh` (same proven shape as libgenome 1.3.11, which built OK on
        # the true machine) and do NOT shadow nested autoconf tools --
        # they resolve via conanbuild PATH through their own wrappers.
        # Only aclocal/automake keep host-perl overlay wrappers above,
        # because they need extra --automake-acdir/--libdir flags.
        autoreconf_wrap = autoconf / "bin" / "autoreconf"
        if not autoreconf_wrap.is_file():
            raise ConanInvalidConfiguration("Autoconf autoreconf payload missing")
        result["autoreconf"] = autoreconf_wrap
        result["overlay_dir"] = str(overlay)
        result["perl5lib"] = ":".join((str(package / "share" / "automake-1.18"),
                                      str(autoconf / "share" / "autoconf")))
        return result

    def _ensure_autoreconf(self, src_dir):
        configure = os.path.join(src_dir, "configure")
        if os.path.isfile(configure):
            self._patch_config_guess(src_dir)
            return
        if not os.path.isfile(os.path.join(src_dir, "configure.ac")):
            raise ConanException("neither configure nor configure.ac found under %s" % src_dir)
        entrypoints = self._automake_entrypoints()
        os.makedirs(os.path.join(src_dir, "config"), exist_ok=True)
        # Host-perl direct exec (no shell-wrapper fork) + writable TMPDIR
        # + clean SHELL, with retry on transient fork exhaustion.
        # `self.run` surfaces only `Error 1 while executing`, so the
        # `can't fork` text stays in the step log; retry unconditionally
        # (max 3) with backoff -- a deterministic configure.ac error simply
        # fails all 3 attempts with the same log, while transient EAGAIN
        # (this round's evidence) gets a second chance without masking.
        sh = self._ohos_sh()
        tmp = self._writable_tmpdir()
        try:
            os.makedirs(tmp, exist_ok=True)
        except OSError:
            pass
        # Nested tools (autom4te/m4/...) resolve via conanbuild PATH through
        # their own Conan shell wrappers, which carry the pkgdatadir
        # relocation. Do NOT override AUTOCONF/AUTOM4TE/etc with direct-perl
        # overlay wrappers (2026-10-17 m4sugar lesson above).
        command = ("TMPDIR=" + shlex.quote(tmp) +
                   " SHELL=" + shlex.quote(sh) +
                   " CONFIG_SHELL=" + shlex.quote(sh) +
                   " ACLOCAL=" + shlex.quote(str(entrypoints["aclocal"])) +
                   " AUTOMAKE=" + shlex.quote(str(entrypoints["automake"])) +
                   " PERL=" + shlex.quote(str(entrypoints["perl"])) +
                   " PERL5LIB=" + shlex.quote(entrypoints["perl5lib"]) +
                   " GREP=grep EGREP='grep -E' FGREP='grep -F'" +
                   " " + shlex.quote(sh) +
                   " " + shlex.quote(str(entrypoints["autoreconf"])) +
                   " --force --install -I config -I m4")
        import time as _time
        env = Environment()
        env.define("TMPDIR", tmp)
        env.define("TMP", tmp)
        env.define("TEMP", tmp)
        env.define("SHELL", sh)
        env.define("CONFIG_SHELL", sh)
        last_exc = None
        for attempt in (1, 2, 3, 4, 5):
            try:
                with env.vars(self).apply():
                    self.run(command, cwd=src_dir, env="conanbuild")
                last_exc = None
                break
            except ConanException as exc:
                last_exc = exc
                if attempt >= 5:
                    break
                self.output.warning(
                    "OHOS port: autoreconf attempt %d/5 failed, "
                    "sleeping before retry (transient fork exhaustion): %s"
                    % (attempt, str(exc)[:200]))
                try:
                    _time.sleep(20 * attempt)
                except Exception:
                    pass
        if last_exc is not None:
            raise last_exc
        if not os.path.isfile(configure):
            raise ConanException("autoreconf finished but produced no configure script in %s" % src_dir)
        self._patch_config_guess(src_dir)

    def _write_install_shim(self):
        """cp/mkdir install shim for OHOS HMDFS batch installs.

        Adapted from the proven cxxtools 3.0.0 recipe in this repo: the
        HMBS-injected install (runtime/.../bin/install, install_shim:true)
        only accepts single-file two-arg calls, so automake batch header
        installs (`install -c -m 644 f1..fN dir/`) exit 64 (EX_USAGE).
        True-machine evidence this round:
        `install-library_includeHEADERS] Error 64` after libGenome-1.3.a
        itself linked fine. The shim supports single + multi source,
        mkdir -p, and chmod || true (HMBS_CAP_CHMOD=0). Only the INSTALL
        variable rewrite is changed, install contents and modes are not.
        """
        shim_dir = os.path.join(self.build_folder, "_ohos_install_shim")
        os.makedirs(shim_dir, exist_ok=True)
        install = os.path.join(shim_dir, "install")
        fd = os.open(install, os.O_WRONLY | os.O_CREAT | os.O_TRUNC, 0o755)
        try:
            with os.fdopen(fd, "w", encoding="utf-8", newline="\n") as f:
                f.write(
                    "#!/bin/sh\n"
                    "set -eu\n"
                    "mode=\n"
                    "while [ $# -gt 0 ]; do\n"
                    "  case \"$1\" in\n"
                    "    -p|-c) shift ;;\n"
                    "    -m) [ $# -ge 2 ] || exit 2; mode=$2; shift 2 ;;\n"
                    "    -d) shift; [ $# -gt 0 ] || exit 2; mkdir -p \"$@\"; exit 0 ;;\n"
                    "    --) shift; break ;;\n"
                    "    -*) shift ;;\n"
                    "    *) break ;;\n"
                    "  esac\n"
                    "done\n"
                    "[ $# -ge 2 ] || exit 2\n"
                    "dest=\n"
                    "for arg in \"$@\"; do dest=$arg; done\n"
                    "count=$(($# - 1))\n"
                    "if [ \"$count\" -gt 1 ]; then\n"
                    "  mkdir -p \"$dest\"\n"
                    "else\n"
                    "  mkdir -p \"$(dirname \"$dest\")\"\n"
                    "fi\n"
                    "i=1\n"
                    "for src in \"$@\"; do\n"
                    "  [ $i -gt $count ] && break\n"
                    "  cp -f \"$src\" \"$dest\"\n"
                    "  if [ -n \"$mode\" ]; then\n"
                    "    if [ -d \"$dest\" ]; then chmod \"$mode\" \"$dest/${src##*/}\" 2>/dev/null || true\n"
                    "    else chmod \"$mode\" \"$dest\" 2>/dev/null || true; fi\n"
                    "  fi\n"
                    "  i=$((i + 1))\n"
                    "done\n"
                )
        except Exception:
            try:
                os.close(fd)
            except Exception:
                pass
            raise
        try:
            os.chmod(install, 0o755)
        except OSError:
            pass  # HMBS_CAP_CHMOD=0: HMFS ignores chmod
        return install

    def _redirect_install_to_shim(self, shim_install, root):
        """Point generated Makefiles' INSTALL at the shim (E596 pattern).

        configure bakes the probed install path into every generated
        Makefile's INSTALL variable; INSTALL_DATA/INSTALL_PROGRAM derive
        from ${INSTALL}, and automake routes libtool --mode=install through
        $(INSTALL) too, so replacing INSTALL covers headers, programs and
        static archives in one pass. Do not pass INSTALL on the make command
        line (space-containing values break the shell quoting, Error 126).
        """
        if not root or not os.path.isdir(root):
            return False
        changed_any = False
        for _root, _, _files in os.walk(root):
            if "Makefile" not in _files:
                continue
            _mp = os.path.join(_root, "Makefile")
            try:
                with open(_mp, "r", encoding="utf-8", errors="ignore") as _f:
                    _content = _f.read()
            except OSError:
                continue
            if "INSTALL =" not in _content:
                continue
            _lines = []
            _changed = False
            for _line in _content.splitlines(True):
                _stripped = _line.lstrip()
                if _stripped.startswith("INSTALL = ") and "/install" in _stripped:
                    _indent = _line[:len(_line) - len(_stripped)]
                    _lines.append("%sINSTALL = %s\n" % (_indent, shim_install))
                    _changed = True
                else:
                    _lines.append(_line)
            if _changed:
                try:
                    with open(_mp, "w", encoding="utf-8", newline="\n") as _f:
                        _f.write("".join(_lines))
                except OSError:
                    continue
                changed_any = True
        return changed_any

    def _prebuild_libmuscle_lib(self, src_dir):
        """Build libMUSCLE-3.7.la before the sibling `muscle` program.

        True-machine (vendored libmuscle, serial make): `make[1]: *** No rule
        to make target '../libMUSCLE/libMUSCLE-3.7.la', needed by 'muscle'`
        inside src/libMUSCLE. From that directory the `../libMUSCLE/` prefix
        is a self-reference, but make matches targets literally, so the
        program cannot trigger the real `libMUSCLE-3.7.la` rule in the same
        Makefile -- it only links when the file already exists. Same family
        as the repo's libnfc-tools precedent (`No rule to make target
        '../gcutter/libgcutter.la'`, fixed by building in dependency order).
        We only need the static lib + headers + .pc for libmems'
        PKG_CHECK_MODULES; pre-building the lib keeps every upstream target
        (including the `muscle` program) intact instead of deleting it.
        Fail-open: without the exact stale reference, do nothing and let
        the normal make surface the real error.
        """
        makefile = os.path.join(src_dir, "libMUSCLE", "Makefile")
        if not os.path.isfile(makefile):
            return
        try:
            with open(makefile, "r", encoding="utf-8", errors="ignore") as handle:
                content = handle.read()
        except OSError:
            return
        if "../libMUSCLE/libMUSCLE-3.7.la" not in content:
            return
        if "libMUSCLE-3.7.la:" not in content and "libMUSCLE-3.7.la :" not in content:
            return
        self.output.info("OHOS port: pre-building libMUSCLE-3.7.la before the muscle program")
        self.run("make -C libMUSCLE libMUSCLE-3.7.la -j1", cwd=src_dir, env="conanbuild")

    def _normalize_mtimes(self, root):
        """Clamp workspace-sync future skew so make sees a consistent tree.

        True-machine preflight prints `tar: ... time stamp ... is in the
        future` (~0.65s) for every synced file: the sync host clock runs
        slightly ahead of the device. Harmless for correctness, but it
        leaves extracted vendored trees with mtimes newer than the files
        autoreconf/configure generate next, which confuses make's
        rebuild detection (`checking that generated files are newer than
        configure`) and can trigger redundant rebuilds in the long serial
        triple-autotools build. Walk the extracted tree once with os.utime
        (portable, no fork) and clamp any future mtime back to now.
        Fail-open: never abort the build on a touch error.
        """
        try:
            now = None
            for _root, _dirs, _files in os.walk(root):
                for _name in _dirs + _files:
                    _p = os.path.join(_root, _name)
                    try:
                        _st = os.lstat(_p)
                    except OSError:
                        continue
                    import time as _time
                    if now is None:
                        now = _time.time()
                    if _st.st_mtime > now:
                        try:
                            os.utime(_p, (now, now), follow_symlinks=False)
                        except OSError:
                            try:
                                os.utime(_p, (now, now))
                            except OSError:
                                pass
            try:
                import time as _time2
                os.utime(root, None)
            except OSError:
                pass
        except Exception:
            pass

    def _build_vendored(self, name, prefix):
        """Download + static-install one vendored dep into the private prefix."""
        vendored = self.conan_data.get("vendored", {}).get(name)
        if not vendored:
            raise ConanException("vendored source missing for %s" % name)
        work = os.path.join(self.build_folder, "vendor", name)
        src_dir = os.path.join(work, "src")
        if not os.path.isfile(os.path.join(src_dir, "configure")) and \
           not os.path.isfile(os.path.join(src_dir, "configure.ac")):
            if os.path.isdir(work):
                shutil.rmtree(work, ignore_errors=True)
            os.makedirs(src_dir, exist_ok=True)
            get(self, url=vendored["url"], sha256=vendored["sha256"],
                destination=src_dir, strip_root=True)
        self._normalize_mtimes(src_dir)
        if name == "libgenome":
            self._fix_vendored_genome_portability(src_dir)
        self._ensure_autoreconf(src_dir)
        self._fix_configure_umask(src_dir)
        # Static-only private install; shared objects from vendored deps
        # must never leak as separate .so (merged as .a below).
        if str(self.settings.os) == "OHOS":
            args = "--prefix=%s --disable-shared --enable-static --disable-dependency-tracking" % shlex.quote(prefix)
            args += " --build=x86_64-unknown-linux-gnu --host=aarch64-unknown-linux-ohos"
            self._run_configure_safe(src_dir, args)
        else:
            cmd = "./configure --prefix=\"%s\" --disable-shared --enable-static --disable-dependency-tracking" % prefix
            self.run(cmd, cwd=src_dir, env="conanbuild")
        if name == "libmuscle":
            self._prebuild_libmuscle_lib(src_dir)
        if name == "libmuscle":
            # Private static dep: only the lib + headers + .pc are merged
            # into this package; the `muscle` demo program is never consumed
            # (PKG_CHECK_MODULES only needs libMUSCLE-3.7) and its link is
            # the heaviest single fork in the serial triple-autotools build.
            # The 2026-10-15 preflight dropped the SSH transport right after
            # libmuscle `configure: creating ./config.status` with no
            # compiler error, after the prior single-job throttling
            # (MAKEFLAGS=-j1/XZ_OPT=-T1) was already in place -- so the next
            # route is work reduction, not more throttling. Overriding
            # bin_PROGRAMS on the make command line skips just the program
            # (harmless when the Makefile has no such variable); the static
            # lib is still prebuilt above and installed below. Test scope
            # unchanged: no check target is skipped.
            self.output.info("OHOS port: vendored libmuscle lib-only build (skip muscle program link)")
            self.run("make -j1 bin_PROGRAMS=", cwd=src_dir, env="conanbuild")
        else:
            self.run("make -j1", cwd=src_dir, env="conanbuild")
        try:
            _shim = self._write_install_shim()
            self._redirect_install_to_shim(_shim, src_dir)
        except Exception as _e:
            self.output.warning("install shim setup failed, using system install: %s" % _e)
        if name == "libmuscle":
            self.run("make install -j1 bin_PROGRAMS=", cwd=src_dir, env="conanbuild")
        else:
            self.run("make install -j1", cwd=src_dir, env="conanbuild")
        pc_dir = os.path.join(prefix, "lib", "pkgconfig")
        if not os.path.isdir(pc_dir) or not os.listdir(pc_dir):
            # Fail-closed: a missing .pc means the later PKG_CHECK_MODULES
            # would fail cryptically; surface the real cause now.
            self.output.warning("vendored %s installed no pkg-config file under %s" % (name, pc_dir))

    def _ensure_boost_system_stub(self):
        """Provide an empty libboost_system.a for AX_BOOST_SYSTEM probes.

        True-machine 2026-10-15 round 2: Boost headers now resolve
        (`boost/system/error_code.hpp... yes`) but
        `checking for the Boost system library... no` /
        `configure: error: cannot find the flags to link with Boost system`.
        Root cause is version skew, not a missing package: Boost.System has
        been header-only since 1.69, so the published boost/1.91.0.1.1 package
        ships no libboost_system binary by design (header-only component in
        its package_info), while libmems' autoconf-archive AX_BOOST_SYSTEM
        still tries to link `-lboost_system`. Upstream's own test program only
        constructs a header-inline `error_code`, so an empty archive satisfies
        both the configure link probe and any final `-lboost_system` link
        without contributing symbols. The stub lives in an isolated
        build_folder dir (never merged by package(), which only copies the
        private prefix), so it cannot leak into the deliverable.
        Fail-closed: no usable `ar` -> raise instead of running blind.
        """
        stub_dir = os.path.join(self.build_folder, "boost_stub")
        try:
            os.makedirs(stub_dir, exist_ok=True)
        except OSError:
            pass
        stub = os.path.join(stub_dir, "libboost_system.a")
        if os.path.isfile(stub) and os.path.getsize(stub) > 0:
            try:
                # Validate it is a real archive (starts with !<arch>).
                with open(stub, "rb") as handle:
                    if handle.read(8) == b"!<arch>\n":
                        return stub_dir
            except OSError:
                pass
            try:
                os.remove(stub)
            except OSError:
                pass
        archiver = shutil.which("ar") or shutil.which("llvm-ar")
        if not archiver:
            # conanbuild PATH is only applied to subprocesses, not to this
            # Python process, so probe the OHOS toolchain dir + conf too.
            _candidates = ["/data/service/hnp/bin/ar", "/data/service/hnp/bin/llvm-ar"]
            try:
                _compilers = self.conf.get("tools.build:compiler_executables", default={}, check_type=dict) or {}
                _cxx = _compilers.get("cpp") or _compilers.get("cxx") or ""
                if _cxx:
                    import pathlib as _pl
                    _candidates.insert(0, str(_pl.Path(_cxx).parent / "llvm-ar"))
                    _candidates.insert(0, str(_pl.Path(_cxx).parent / "ar"))
            except Exception:
                pass
            for _cand in _candidates:
                if _cand and os.path.isfile(_cand):
                    archiver = _cand
                    break
        if not archiver:
            raise ConanException(
                "need `ar` to materialize the header-only Boost.System stub")
        # `ar cr` with an empty file list still writes a valid empty archive
        # header on GNU/LLVM ar; do not compile a dummy object (extra fork).
        # Run with conanbuild env so the tool is on PATH in CI sandboxes.
        self.run("%s cr %s" % (shlex.quote(archiver), shlex.quote(stub)),
                 cwd=stub_dir, env="conanbuild")
        try:
            with open(stub, "rb") as handle:
                magic = handle.read(8)
        except OSError as exc:
            raise ConanException("Boost.System stub unreadable: %s" % exc)
        if magic != b"!<arch>\n":
            raise ConanException("Boost.System stub is not a valid archive")
        self.output.info("OHOS port: header-only Boost.System stub at %s" % stub)
        return stub_dir

    def generate(self):
        tc = AutotoolsToolchain(self)
        tc.configure_args.append("--disable-dependency-tracking")
        if not self.options.shared:
            tc.configure_args.append("--disable-shared")
            tc.configure_args.append("--enable-static")
        # E002: keep configure/make/mktemp and shell temp files off /tmp.
        env = tc.environment()
        tmpdir = self._writable_tmpdir()
        env.define("TMPDIR", tmpdir)
        env.define("TMP", tmpdir)
        env.define("TEMP", tmpdir)
        # exec-channel hardening (2026-10-16, different route from the
        # prior mtime/work-reduction round): propagate single-job
        # throttling through the toolchain env so EVERY child fork
        # (autoreconf/configure/make/xz) sees it, not just the build()
        # process env. Set-if-absent only, never override an injected value.
        if not os.environ.get("MAKEFLAGS"):
            env.define("MAKEFLAGS", "-j1")
        if not os.environ.get("XZ_OPT"):
            env.define("XZ_OPT", "-T1")
        if str(self.settings.get_safe("os")) == "OHOS":
            # Bake the clean shell into config.status/Makefile SHELL.
            env.define("CONFIG_SHELL", self._ohos_sh())
            env.define("SHELL", self._ohos_sh())
        tc.generate(env=env)

    def _ensure_configure(self):
        """Same autoreconf step as upstream autogen.sh for the main tree."""
        self._ensure_autoreconf(self.source_folder)

    def build(self):
        apply_conandata_patches(self)
        self._normalize_mtimes(self.source_folder)
        self._fix_boost_filesystem_v3(self.source_folder)
        self._fix_libcxx_swap_noexcept(self.source_folder)
        self._fix_register_keyword(self.source_folder)
        self._fix_boost_tuple_pushback(self.source_folder)
        tmpdir = self._writable_tmpdir()
        os.environ["TMPDIR"] = tmpdir
        os.environ["TMP"] = tmpdir
        os.environ["TEMP"] = tmpdir
        # Exec-channel hardening, part 2 (different route from prior
        # mtime/work-reduction round): drop stale files left in the
        # task-private tmpdir by earlier interrupted preflights. A reused
        # cache slot can accumulate autoreconf/libtool temp files until
        # fork/mmap starts failing and sshd rejects the next exec with
        # `exec request failed on channel 0`. Only contents are removed,
        # never the dir itself; fail-open so cleanup never masks the build.
        try:
            os.makedirs(tmpdir, exist_ok=True)
            for _entry in os.listdir(tmpdir):
                _p = os.path.join(tmpdir, _entry)
                try:
                    if os.path.isdir(_p) and not os.path.islink(_p):
                        shutil.rmtree(_p, ignore_errors=True)
                    else:
                        os.remove(_p)
                except OSError:
                    pass
        except OSError:
            pass
        self.output.info("OHOS port: task tmpdir cleaned at build start: %s" % tmpdir)
        # Preflight 2026-10-15 round 2: libgenome built+installed OK, then
        # the SSH transport dropped right after vendored libmuscle
        # `configure: creating ./config.status` with no compiler error
        # (`Connection to 47.122.125.180 closed by remote host`). Prior
        # round's single-job throttling (MAKEFLAGS=-j1/XZ_OPT=-T1, kept
        # below) was already in place, so this round changes route from
        # "more throttling" to "less work + consistent mtimes": clamp the
        # ~0.65s future-skew mtimes (see _normalize_mtimes) and build only
        # the vendored libmuscle static lib (skip the unconsumed `muscle`
        # program link, the heaviest single fork). No test scope changed.
        for _var, _val in (("MAKEFLAGS", "-j1"), ("XZ_OPT", "-T1")):
            if not os.environ.get(_var):
                os.environ[_var] = _val
        try:
            os.makedirs(tmpdir, exist_ok=True)
        except OSError:
            pass
        prefix = self._private_prefix()
        # Vendored order: genome first (no deps), then muscle, then main.
        self._build_vendored("libgenome", prefix)
        self._build_vendored("libmuscle", prefix)
        # Point the main configure at the private prefix (env + args).
        pc_dir = os.path.join(prefix, "lib", "pkgconfig")
        inc_dir = os.path.join(prefix, "include")
        lib_dir = os.path.join(prefix, "lib")
        os.environ["PKG_CONFIG_PATH"] = pc_dir + (os.pathsep + os.environ["PKG_CONFIG_PATH"] if os.environ.get("PKG_CONFIG_PATH") else "")
        self._ensure_configure()
        self._fix_configure_umask(self.source_folder)
        autotools = Autotools(self)
        extra = []
        if os.path.isdir(inc_dir):
            extra.append("CPPFLAGS=-I%s" % inc_dir)
        if os.path.isdir(lib_dir):
            extra.append("LDFLAGS=-L%s" % lib_dir)
        # Boost (remote requires): AX_BOOST_BASE honors --with-boost=DIR
        # (DIR/include + DIR/lib) and CPPFLAGS/LDFLAGS. Resolve via
        # dependencies (package_folder join for relative cpp_info dirs, same
        # pattern as abiword-plugin-sdw/arg_router in this repo). -I/-L are
        # collected host-wide (boost plus transitive zlib) below. Fail-closed
        # when the boost package folder is missing so configure never runs
        # blind.
        # Header-only Boost.System stub (see _ensure_boost_system_stub): the
        # published boost has no libboost_system binary, but AX_BOOST_SYSTEM
        # still probes `-lboost_system`. Its -L is appended here so both the
        # probe and any final link resolve; the isolated stub dir is never
        # merged by package().
        boost_args = ""
        try:
            _stub_dir = self._ensure_boost_system_stub()
            _li0 = next((i for i, e in enumerate(extra) if e.startswith("LDFLAGS=")), -1)
            if _li0 >= 0:
                extra[_li0] = extra[_li0] + " -L%s" % _stub_dir
            else:
                extra.append("LDFLAGS=-L%s" % _stub_dir)
            _bdep = self.dependencies["boost"]
            _bpf = getattr(_bdep, "package_folder", None) or ""
            if not _bpf or not os.path.isdir(_bpf):
                raise ConanException("boost package_folder missing for main configure")
            # Host-wide -I/-L/-D: boost itself plus its transitive host deps
            # (zlib). _dep_dirs returns (incs, libs, defs): top-level
            # cpp_info plus every component (boost_headers carries
            # BOOST_SP_NO_PTHREAD_SETCANCELSTATE for OHOS musl) plus
            # include/lib fallbacks, each joined against package_folder and
            # kept only when the directory exists.
            def _dep_dirs(_dep):
                _dpf = getattr(_dep, "package_folder", None) or ""
                _incs, _libs = [], []
                if not _dpf or not os.path.isdir(_dpf):
                    return _incs, _libs, []
                try:
                    _top_incs = list(_dep.cpp_info.includedirs)
                except Exception:
                    _top_incs = []
                try:
                    _top_libs = list(_dep.cpp_info.libdirs)
                except Exception:
                    _top_libs = []
                try:
                    _comps = list(_dep.cpp_info.components.values())
                except Exception:
                    _comps = []
                _defs = []
                try:
                    _defs += list(_dep.cpp_info.defines)
                except Exception:
                    pass
                for _c in _comps:
                    try:
                        _top_incs += list(_c.includedirs)
                    except Exception:
                        pass
                    try:
                        _top_libs += list(_c.libdirs)
                    except Exception:
                        pass
                    try:
                        _defs += list(_c.defines)
                    except Exception:
                        pass
                for _g in _top_incs:
                    _p = _g if os.path.isabs(_g) else os.path.join(_dpf, _g)
                    if not os.path.isdir(_p):
                        continue
                    if _p in _incs:
                        continue
                    _incs.append(_p)
                for _l in _top_libs:
                    _p = _l if os.path.isabs(_l) else os.path.join(_dpf, _l)
                    if not os.path.isdir(_p):
                        continue
                    if _p in _libs:
                        continue
                    _libs.append(_p)
                for _cand in (os.path.join(_dpf, "include"),):
                    if os.path.isdir(_cand) and _cand not in _incs:
                        _incs.append(_cand)
                for _cand in (os.path.join(_dpf, "lib"),):
                    if os.path.isdir(_cand) and _cand not in _libs:
                        _libs.append(_cand)
                _dedup = []
                for _d in _defs:
                    _d = str(_d).strip()
                    if _d and _d not in _dedup:
                        _dedup.append(_d)
                return _incs, _libs, _dedup
            try:
                _host_deps = list(self.dependencies.host.values())
            except Exception:
                _host_deps = [_bdep]
            _cpp_parts, _ld_parts = [], []
            for _tok in extra:
                if _tok.startswith("CPPFLAGS="):
                    _cpp_parts.append(_tok[len("CPPFLAGS="):])
                elif _tok.startswith("LDFLAGS="):
                    _ld_parts.append(_tok[len("LDFLAGS="):])
            extra = []
            _extra_host_lib = None
            _all_defs = []
            for _dep in _host_deps:
                try:
                    _incs, _libs, _defs = _dep_dirs(_dep)
                except Exception:
                    continue
                for _p in _incs:
                    _flag = "-I%s" % _p
                    if _flag not in _cpp_parts:
                        _cpp_parts.append(_flag)
                for _p in _libs:
                    _flag = "-L%s" % _p
                    if _flag not in _ld_parts:
                        _ld_parts.append(_flag)
                for _d in _defs:
                    _flagd = "-D%s" % _d
                    if _flagd not in _cpp_parts and _flagd not in _all_defs:
                        _all_defs.append(_flagd)
                try:
                    _ref = str(_dep.ref)
                except Exception:
                    _ref = ""
                if not _ref.startswith("zlib/"):
                    continue
                _extra_host_lib = "-lz"
            if _extra_host_lib and _extra_host_lib not in _ld_parts:
                _ld_parts.append(_extra_host_lib)
            # Fail-closed header evidence before configure runs. Also verify
            # the INNER headers the compiler actually opens
            # (options_description.hpp:16 chain) and log what :16 includes.
            _bincs, _blibs, _bdefs = _dep_dirs(_bdep)
            _po_cands = [os.path.join(p, "boost", "program_options.hpp") for p in _bincs]
            _po_hit = next((c for c in _po_cands if os.path.isfile(c)), None)
            if _po_hit is None:
                _listing = ""
                _inc0 = _bincs[0] if _bincs else _bpf
                try:
                    _listing = ("; inc0=" + _inc0 + " entries="
                                + ",".join(sorted(os.listdir(os.path.join(_inc0, "boost")))[:20]))
                except Exception as _e:
                    _listing = "; listing failed: %s" % _e
                raise ConanException(
                    "boost/program_options.hpp not found under boost package_folder "
                    "%s (searched %s)%s; refusing to run configure blind"
                    % (_bpf, _po_cands, _listing))
            self.output.info("OHOS port: boost headers verified at %s" % _po_hit)
            for _inner in ("boost/program_options/options_description.hpp",
                           "boost/program_options/config.hpp",
                           "boost/program_options/errors.hpp"):
                _found = any(os.path.isfile(os.path.join(p, _inner)) for p in _bincs)
                self.output.info("OHOS port: inner header %s present=%s" % (_inner, _found))
            try:
                _od = next(os.path.join(p, "boost/program_options/options_description.hpp")
                           for p in _bincs
                           if os.path.isfile(os.path.join(p, "boost/program_options/options_description.hpp")))
                with open(_od, "r", encoding="utf-8", errors="replace") as _h:
                    _od_lines = _h.read().splitlines()
                if len(_od_lines) >= 16:
                    self.output.info("OHOS port: options_description.hpp:16=[%s]" % _od_lines[15][:200])
            except Exception as _e:
                self.output.warning("OHOS port: cannot read options_description.hpp:16: %s" % _e)
            # Round-3 core: prior rounds propagated only -I/-L, never -D.
            # boost/1.85.0 exports BOOST_SP_NO_PTHREAD_SETCANCELSTATE via the
            # boost_headers component for every consumer (musl has no
            # pthread_setcancelstate); the configure AC_CHECK_HEADER test
            # compiles boost headers, so it needs the same -D. Merge all
            # collected defines into the flag set (env + both CPPFLAGS vars).
            for _flagd in _all_defs:
                if _flagd not in _cpp_parts:
                    _cpp_parts.append(_flagd)
            if _all_defs:
                self.output.info("OHOS port: consumer defines propagated: %s" % " ".join(_all_defs))
            if _cpp_parts:
                extra.append("CPPFLAGS=%s" % " ".join(_cpp_parts))
                extra.append("BOOST_CPPFLAGS=%s" % " ".join(_cpp_parts))
            if _ld_parts:
                extra.append("LDFLAGS=%s" % " ".join(_ld_parts))
                extra.append("BOOST_LDFLAGS=%s" % " ".join(_ld_parts))
            if _cpp_parts:
                _prev = os.environ.get("CPPFLAGS", "")
                os.environ["CPPFLAGS"] = " ".join(_cpp_parts) + (" " + _prev if _prev else "")
                os.environ["BOOST_CPPFLAGS"] = os.environ["CPPFLAGS"]
            if _ld_parts:
                _prev = os.environ.get("LDFLAGS", "")
                os.environ["LDFLAGS"] = " ".join(_ld_parts) + (" " + _prev if _prev else "")
                os.environ["BOOST_LDFLAGS"] = os.environ["LDFLAGS"]
            boost_args = " --with-boost=%s" % shlex.quote(_bpf)
            _blibdir = next((d for d in _blibs if d), "")
            if _blibdir:
                boost_args += " --with-boost-libdir=%s" % shlex.quote(_blibdir)
            os.environ["BOOST_ROOT"] = _bpf
        except KeyError:
            raise ConanException("boost dependency missing for main configure (requirements)")
        if str(self.settings.os) == "OHOS":
            args = "--prefix=/ --disable-dependency-tracking"
            if not self.options.shared:
                args += " --disable-shared --enable-static"
            args += " --build=x86_64-unknown-linux-gnu --host=aarch64-unknown-linux-ohos"
            args += boost_args
            if extra:
                # Quote each VAR=... entry: multi-flag values contain spaces
                # and must stay a single shell word (a bare join would turn
                # the second -I into a bogus command name).
                args += " " + " ".join(shlex.quote(a) for a in extra if a)
            # Belt-and-braces with _run_configure_safe: the autoconf cache
            # is disabled outright (file deletion alone left a "(cached)"
            # filesystem probe in the 2026-10-16 preflight).
            if "--cache-file" not in args:
                args += " --cache-file=/dev/null"
            self._run_configure_safe(self.source_folder, args, tmpdir=tmpdir)
            self.run("make -j1", cwd=self.source_folder, env="conanbuild")
            return
        if extra or boost_args:
            _cfg_args = list(extra) + [a for a in boost_args.split() if a]
            autotools.configure(args=_cfg_args)
            autotools.make(args=["-j1"])
            return
        autotools.configure()
        autotools.make(args=["-j1"])
        return

    def package(self):
        try:
            _shim = self._write_install_shim()
            self._redirect_install_to_shim(_shim, self.source_folder)
            self._redirect_install_to_shim(_shim, self.build_folder)
        except Exception as _e:
            self.output.warning("install shim setup failed, using system install: %s" % _e)
        if os.path.isfile(os.path.join(self.source_folder, "Makefile")):
            self.run('make install DESTDIR="%s" -j1' % self.package_folder,
                     cwd=self.source_folder, env="conanbuild")
        else:
            autotools = Autotools(self)
            autotools.install()
        prefix = os.path.join(self.build_folder, "private")
        if os.path.isdir(os.path.join(prefix, "include")):
            copy(self, "*",
                 src=os.path.join(prefix, "include"),
                 dst=os.path.join(self.package_folder, "include"))
        if os.path.isdir(os.path.join(prefix, "lib")):
            copy(self, "*.a",
                 src=os.path.join(prefix, "lib"),
                 dst=os.path.join(self.package_folder, "lib"))
            copy(self, "*.pc",
                 src=os.path.join(prefix, "lib", "pkgconfig"),
                 dst=os.path.join(self.package_folder, "lib", "pkgconfig"))
            import re
            pc_dir = os.path.join(self.package_folder, "lib", "pkgconfig")
            if os.path.isdir(pc_dir):
                for name in os.listdir(pc_dir):
                    if not name.endswith(".pc"):
                        continue
                    path = os.path.join(pc_dir, name)
                    try:
                        with open(path, "r", encoding="utf-8", errors="replace") as handle:
                            data = handle.read()
                    except OSError:
                        continue
                    updated, count = re.subn(r"(?m)^prefix=(?:/usr|/)$",
                                             "prefix=${pcfiledir}/../..", data, count=1)
                    if count != 1:
                        updated2, count2 = re.subn(r"(?m)^prefix=.*$",
                                                   "prefix=${pcfiledir}/../..", data, count=1)
                        if count2 == 1:
                            updated = updated2
                        else:
                            continue
                    try:
                        with open(path, "w", encoding="utf-8") as handle:
                            handle.write(updated)
                    except OSError:
                        continue
        rm(self, "*.la", os.path.join(self.package_folder, "lib"))
        rmdir(self, os.path.join(self.package_folder, "share"))
        copy(self, "COPYING", src=self.source_folder,
             dst=os.path.join(self.package_folder, "licenses"))

    def package_info(self):
        self.cpp_info.libs = ["Mems-1.6", "Genome-1.3", "MUSCLE-3.7"]
        self.cpp_info.set_property("cmake_file_name", "libmems")
        self.cpp_info.set_property("cmake_target_name", "libmems::libmems")
        self.cpp_info.set_property("pkg_config_name", "libMems-1.6")
        self.cpp_info.includedirs = [os.path.join("include", "libMems-1.6"),
                                     os.path.join("include", "libGenome-1.3"),
                                     os.path.join("include", "libMUSCLE-3.7"),
                                     "include"]
