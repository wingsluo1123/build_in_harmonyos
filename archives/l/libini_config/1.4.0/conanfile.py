#!/usr/bin/env python3
"""Conan recipe for libini_config 1.4.0.

INI file parser for C from the SSSD ding-libs project. The task version
1.4.0 names the ini_config component; the source is the official ding-libs
release tarball, which contains the ini implementation together with its
historical companion libraries. The recipe builds the full upstream tree
(so `make check` runs the complete Automake suite) but packages and exposes
only the libini_config artifact.
"""

import glob
import json
import os
import shlex
import shutil
import subprocess

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.env import Environment, VirtualBuildEnv
from conan.tools.files import (
    apply_conandata_patches,
    copy,
    export_conandata_patches,
    get,
    rm,
    rmdir,
)
from conan.tools.gnu import AutotoolsDeps, AutotoolsToolchain, PkgConfigDeps
from conan.tools.layout import basic_layout


class LibiniConfigConan(ConanFile):
    name = "libini_config"
    version = "1.4.0"
    description = "INI file parser for C (SSSD ding-libs ini_config component)"
    license = "LGPL-3.0-or-later"
    homepage = "https://github.com/SSSD/ding-libs"
    url = "https://gitcode.com/OpenHarmonyPCDeveloper/build_in_harmonyos"
    package_type = "library"

    settings = "os", "arch", "compiler", "build_type"
    options = {"shared": [True, False], "fPIC": [True, False]}
    default_options = {"shared": False, "fPIC": True}
    implements = ["auto_shared_fpic"]

    def export_sources(self):
        export_conandata_patches(self)

    def config_options(self):
        if self.settings.os == "Windows":
            self.options.rm_safe("fPIC")

    def configure(self):
        if self.options.shared:
            self.options.rm_safe("fPIC")

    def validate(self):
        if str(self.settings.os) not in ("Linux", "OHOS"):
            raise ConanInvalidConfiguration(
                f"libini_config supports Linux and OHOS, not {self.settings.os}"
            )
        if str(self.settings.os) == "OHOS" and str(self.settings.arch) != "armv8":
            raise ConanInvalidConfiguration(
                "libini_config OHOS support is validated for armv8/AArch64"
            )

    def build_requirements(self):
        # The release tarball already ships pregenerated configure and
        # Makefile.in. Keep generated files as-is (R6) and fix the HMDFS
        # umask at build time via sed (E129/zzuf precedent). This avoids
        # autoconf/automake/libtool tool-requires, whose conancenter m4
        # rebuild fails on preflight workers where the profile's
        # /data/service/hnp/bin/bash is inaccessible
        # (`configure[139]: ... inaccessible or not found`) while HMBS
        # guarantees /bin/sh.
        # The pregenerated configure hard-requires a pkg-config binary
        # (`checking for pkg-config... no` -> `configure: error: pkg-config
        # not found`); HMBS only injects cmake/make/ninja/python3, so supply
        # it via pkgconf (zurl/fcft/xwrited precedent: pkgconf/3.0.5).
        # Only the upstream Check-based tests need this dependency; it is not
        # part of the installed libini_config link interface.
        self.tool_requires("pkgconf/3.0.5")
        self.test_requires("check/0.15.2")

    def layout(self):
        basic_layout(self, src_folder=".")

    def source(self):
        get(self, **self.conan_data["sources"][self.version], strip_root=True)

    def generate(self):
        # check.pc is consumed by configure when HAVE_CHECK is detected.
        PkgConfigDeps(self).generate()
        AutotoolsDeps(self).generate()
        VirtualBuildEnv(self).generate()

        tc = AutotoolsToolchain(self)
        # pkgconf/3.0.5 installs `pkgconf`, NOT a `pkg-config` alias
        # (ext2fuse/0.8.1 precedent). The pregenerated configure probes
        # `AC_PATH_TOOL(PKG_CONFIG, pkg-config)`, so without this it fails
        # with `checking for pkg-config... no` even though pkgconf is on
        # conanbuild PATH. Point the probe at the real binary by name and
        # let PATH (VirtualBuildEnv + tool_requires) resolve it.
        _tc_env = tc.environment()
        _tc_env.define("PKG_CONFIG", "pkgconf")
        check = self._dependency("check")
        if check is not None:
            # The upstream dhash target has a historical CFLAGS typo. Keep
            # Check's include directory in the recipe toolchain so the target
            # compiles without patching generated Makefile.in. Environment
            # channel only (ufiformat/0.9.9 precedent): never duplicate this
            # as a quoted 'CPPFLAGS=\"...\"'/'CFLAGS=\"...\"' inline prefix
            # or configure arg; that leaks literal quotes into the conftest
            # compile and fails with "C compiler cannot create executables".
            check_include = os.path.join(check.package_folder, "include")
            if os.path.isdir(check_include):
                tc.extra_cflags.append(f"-I{check_include}")
                self.output.info(f"libini_config check include via toolchain: -I{check_include}")
            else:
                self.output.info(f"libini_config check include missing: {check_include}")
        tc.configure_args.extend(
            [
                "--disable-nls",
                "--disable-dependency-tracking",
            ]
        )
        if self.options.shared:
            tc.configure_args.extend(["--enable-shared", "--disable-static"])
        else:
            tc.configure_args.extend(["--disable-shared", "--enable-static"])
        tc.generate(env=_tc_env)

    def _writable_tmpdir(self):
        # coinor-vol/1.5.4 precedent: an unwritable TMPDIR makes clang fail
        # its very first sanity link with "C compiler cannot create
        # executables" (Error 77): `unable to make temporary file:
        # Read-only file system / No such file or directory`. HMDFS ignores
        # chmod and os.access, so only makedirs + open(w) + unlink counts.
        # Prefer the HMBS-injected task TMPDIR/TMP/TEMP (guaranteed writable
        # per preflight contract), then the recipe-local build tmp dirs.
        candidates = []
        for var in ("TMPDIR", "TMP", "TEMP"):
            try:
                value = os.environ.get(var)
            except Exception:
                value = None
            if value and value not in candidates:
                candidates.append(value)
        if self.build_folder:
            for sub in ("tmp", ".tmp"):
                cand = os.path.join(self.build_folder, sub)
                if cand not in candidates:
                    candidates.append(cand)
        for cand in candidates:
            try:
                os.makedirs(cand, exist_ok=True)
                probe = os.path.join(cand, ".libini_config-tmp-write-probe")
                with open(probe, "w", encoding="utf-8") as handle:
                    handle.write("ok")
                os.unlink(probe)
                return cand
            except OSError:
                continue
        # Last resort: best-effort makedirs on the first recipe-local dir so
        # the failure (if any) is explicit downstream, never silent.
        fallback = (
            os.path.join(self.build_folder, "tmp")
            if self.build_folder
            else (os.environ.get("TMPDIR") or "/tmp")
        )
        try:
            os.makedirs(fallback, exist_ok=True)
        except OSError:
            pass
        return fallback

    def _dump_config_log(self):
        # Configure prints only the summary line; the failing command lives
        # in config.log (ufiformat precedent). Bounded dump so the next
        # preflight proves compiler-vs-tmpdir cause instead of guessing.
        searched = []
        hits = []
        for pattern in (
            os.path.join(self.build_folder or ".", "config.log"),
            os.path.join(self.build_folder or ".", "**", "config.log"),
        ):
            searched.append(pattern)
            try:
                hits.extend(glob.glob(pattern, recursive=True))
            except OSError:
                continue
        seen = set()
        for log_path in hits:
            if log_path in seen:
                continue
            seen.add(log_path)
            try:
                with open(log_path, "r", encoding="utf-8", errors="replace") as handle:
                    lines = handle.read().splitlines()
            except OSError as exc:
                self.output.warning(f"libini_config config.log unreadable {log_path}: {exc!r}")
                continue
            idx = next(
                (i for i, line in enumerate(lines) if "cannot create executables" in line),
                None,
            )
            if idx is not None:
                self.output.info(f"libini_config config.log failing section ({log_path} around line {idx + 1}):")
                for line in lines[max(0, idx - 35):idx + 10]:
                    self.output.info(f"libini_config-config-log| {line}")
            self.output.info(f"libini_config config.log tail ({log_path}, last 20):")
            for line in lines[-20:]:
                self.output.info(f"libini_config-config-log| {line}")
        if not seen:
            self.output.warning(
                "libini_config config.log not found; searched "
                + ", ".join(searched)
            )

    def _probe_compiler(self, cc):
        # Real hello-world link test (ufiformat precedent): existence/X_OK
        # is not enough, only a driver that creates executables is
        # accepted. Returns True (works), False (broken), None (transient
        # fork pressure: EAGAIN/posix_spawn failed/can't fork).
        try:
            tmpdir = self._writable_tmpdir()
        except Exception:
            return False
        src = os.path.join(tmpdir, ".libini_config-cc-probe.c")
        out = os.path.join(tmpdir, ".libini_config-cc-probe")
        try:
            with open(src, "w", encoding="utf-8") as handle:
                handle.write("int main(void){return 0;}\n")
        except OSError:
            return False
        try:
            proc = subprocess.run(
                [cc, src, "-o", out],
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                timeout=120,
            )
            if proc.returncode == 0 and os.path.isfile(out):
                return True
            err = (proc.stderr or b"").decode("utf-8", "replace").lower()
            if any(
                mark in err
                for mark in (
                    "resource temporarily unavailable",
                    "posix_spawn failed",
                    "can't fork",
                    "cannot fork",
                    "try again",
                )
            ):
                return None
            return False
        except Exception as exc:
            lowered = repr(exc).lower()
            if "temporarily unavailable" in lowered or "try again" in lowered:
                return None
            return False
        finally:
            for path in (src, out):
                try:
                    if os.path.isfile(path):
                        os.unlink(path)
                except OSError:
                    pass

    def _find_working_compiler(self):
        # The ohos-aarch64 profile pins CC to /data/service/hnp/bin/clang,
        # which is inaccessible on some preflight workers (config.log:
        # ".../clang: inaccessible or not found", exit 127 -> Error 77).
        # Discover a driver that really links (alberta/ufiformat pattern,
        # generic candidates only, no lib-specific paths). Single-token
        # CC override is kept (experience 2 allows single-token precious
        # vars); multi-token flag quoting stays in the toolchain channel.
        try:
            execs = self.conf.get(
                "tools.build:compiler_executables", default={}, check_type=dict
            )
        except Exception:
            execs = {}
        profile_c = (execs or {}).get("c")

        def _dedupe(items):
            seen = set()
            result = []
            for item in items:
                if not item or item in seen:
                    continue
                seen.add(item)
                result.append(item)
            return result

        sdk_clangs = []
        try:
            sdk_clangs = sorted(
                glob.glob("/data/service/hnp/ohos-sdk*/ohos/native/llvm/bin/clang")
            )
        except OSError:
            sdk_clangs = []
        candidates = _dedupe(
            [
                profile_c,
                os.environ.get("CC"),
                shutil.which("clang"),
                "/storage/Users/currentUser/usr/local/bin/clang",
                "/data/service/hnp/bin/clang",
                "/usr/bin/clang",
                "/usr/local/bin/clang",
            ]
            + sdk_clangs
        )
        self.output.info(f"libini_config CC candidates: {candidates}")
        for cand in candidates:
            try:
                if not (cand and os.path.isfile(cand)):
                    continue
            except Exception:
                continue
            result = self._probe_compiler(cand)
            if result is True:
                self.output.info(f"libini_config working CC: {cand}")
                return cand
            if result is None:
                self.output.warning(
                    f"libini_config CC probe transient (EAGAIN) on {cand}; "
                    "stop probing, keep profile driver"
                )
                return ""
            self.output.info(f"libini_config CC probe rejected {cand}")
        self.output.warning("libini_config no working CC found; keep profile driver")
        return ""

    def _make_args_list(self):
        # -j1: HMBS injects tools.build:jobs=1; keep explicit serialization
        # for the fork-sensitive HMDFS worker (E074/R9 precedent).
        # SHELL/CONFIG_SHELL pinned to HMBS-guaranteed /bin/sh; profile's
        # /data/service/hnp/bin/bash is inaccessible on preflight workers.
        # ACLOCAL/AUTOMAKE/AUTOCONF/AUTOHEADER=true prevents Automake from
        # trying to regenerate config.guess/config.sub with an incompatible
        # Perl/m4 stack (R6: keep pregenerated files as-is).
        return [
            "-j1",
            "SHELL=/bin/sh",
            "CONFIG_SHELL=/bin/sh",
            "ACLOCAL=true",
            "AUTOMAKE=true",
            "AUTOCONF=true",
            "AUTOHEADER=true",
        ]

    def _check_include_dir(self):
        # Validated check include directory or None. Used by both the
        # toolchain channel (generate) and the inline/manual channel
        # (build). Validation keeps the inline double-quoted form safe:
        # paths containing double-quote, dollar, backtick or backslash are rejected so
        # no shell expansion or quote leak can occur.
        try:
            check = self._dependency("check")
        except Exception:
            return None
        if check is None:
            return None
        try:
            folder = check.package_folder
        except Exception:
            return None
        if not folder:
            return None
        inc = os.path.join(folder, "include")
        try:
            if not os.path.isdir(inc):
                return None
        except Exception:
            return None
        for bad in ('"', "$", "`", "\\"):
            if bad in inc:
                return None
        return inc

    def _inline_prefix(self, for_tests=False):
        # Inline `VAR=val` assignments win over the profile's conanbuild.sh
        # aggregator (`[buildenv] CONFIG_SHELL/SHELL=/data/service/hnp/bin/bash`,
        # inaccessible on preflight workers -> `configure[139]: ... inaccessible
        # or not found`). `Environment.define(SHELL=...)` in _environment() is
        # applied to os.environ but `self.run(..., env="conanbuild")` and
        # `Autotools.configure()` re-source conanbuild.sh afterwards, so the
        # profile value wins there (ballandpaddle/0.8.1 precedent: inline prefix
        # + env="conanbuild"). All _environment() keys needed by configure/make
        # are therefore repeated inline here so nothing is lost.
        parts = [
            "CONFIG_SHELL=/bin/sh",
            "SHELL=/bin/sh",
            # pkgconf/3.0.5 provides `pkgconf`, not `pkg-config`
            # (ext2fuse/0.8.1 precedent). Must ride inline: the manual
            # /bin/sh configure line wins over conanbuild.sh, so a bare
            # Environment.define would lose here (same SHELL pattern).
            # Single-token precious var, no quoting leak (experience 2).
            "PKG_CONFIG=pkgconf",
            "am_cv_sleep_fractional_seconds=yes",
            "am_cv_filesystem_timestamp_resolution=2",
            f"PKG_CONFIG_PATH={shlex.quote(self.generators_folder)}:$PKG_CONFIG_PATH",
            f"PWD={shlex.quote(self.build_folder)}",
        ]
        if str(self.settings.os) == "OHOS":
            # Write-probed (coinor-vol precedent): never assume
            # build_folder/tmp is writable on HMDFS; prefer the HMBS-injected
            # task TMPDIR which the platform guarantees.
            test_tmp = self._writable_tmpdir()
            parts.append(f"TMPDIR={shlex.quote(test_tmp)}")
            parts.append(f"TMP={shlex.quote(test_tmp)}")
            parts.append(f"TEMP={shlex.quote(test_tmp)}")
            if for_tests:
                parts.append("CK_FORK=no")
                check = self._dependency("check")
                if check is not None:
                    check_libdir = os.path.join(check.package_folder, "lib")
                    if os.path.isdir(check_libdir):
                        parts.append(
                            f"LD_LIBRARY_PATH={shlex.quote(check_libdir)}:$LD_LIBRARY_PATH"
                        )
        # Upstream dhash has a historical CFLAGS typo so CHECK_CFLAGS from
        # configure never reaches dhash_ut_check.o (preflight proves it:
        # `fatal error: 'check.h' file not found` while the
        # tc.extra_cflags toolchain channel alone did not reach the manual
        # `/bin/sh configure` + `make` lines). Propagate the validated
        # include inline for every configure/make invocation. Double-quoted
        # form preserves conanbuild.sh flags via $CFLAGS/$CPPFLAGS; the path
        # is pre-validated by _check_include_dir (no `"`, `$`, backtick,
        # backslash) so no literal-quote leak into the compiler. Verified
        # safe: single -I token, no spaces in HMBS check paths, quotes are
        # shell syntax (removed before exec), not literals.
        check_include = self._check_include_dir()
        if check_include is not None:
            parts.append(f'CPPFLAGS="-I{check_include} $CPPFLAGS"')
            parts.append(f'CFLAGS="-I{check_include} $CFLAGS"')
            self.output.info(f"libini_config check include inline: -I{check_include}")
        else:
            self.output.warning("libini_config check include not found for inline prefix")
        # Single-token precious vars above (SHELL/CONFIG_SHELL/...) stay.
        return " ".join(parts)

    def _select_install_args(self):
        # Adapted from kyua round 30 (same fingerprint: HMBS runtime
        # `.../bin/install` wrapper rejects multi-file
        # `install -c -m 644 a b c dir` DATA installs with EX_USAGE/64
        # while single-file libtool installs succeed; here it surfaced as
        # `install-dist_docDATA` Error 64). Automake derives
        # INSTALL_PROGRAM/INSTALL_DATA/INSTALL_SCRIPT from INSTALL, and a
        # make command-line INSTALL= override wins over the configure-baked
        # value, so one probe-verified override repairs the whole install
        # tree in a single lever (E312/E313 precedent:
        # `make install INSTALL=/system/bin/install -c`). Selection is by
        # real file-evidence probe (multi-file copy with -m 644 in a
        # scratch dir under build_folder, content compared), never by PATH
        # order; the HMBS wrapper fails the probe and is skipped. No
        # working install -> cp trio fallback (INSTALL/INSTALL_PROGRAM/
        # INSTALL_DATA/INSTALL_SCRIPT all set, because automake expands
        # INSTALL_DATA as `$(INSTALL) -m 644`).
        # Returns a list of `VAR="value"` make tokens (empty = plain
        # `make install`).
        probe = os.path.join(self.build_folder, "install-probe")
        try:
            os.makedirs(probe, exist_ok=True)
        except OSError:
            return []
        src1 = os.path.join(probe, "probe1.txt")
        src2 = os.path.join(probe, "probe2.txt")
        dest = os.path.join(probe, "dest")
        try:
            with open(src1, "w", encoding="utf-8") as handle:
                handle.write("probe-one\n")
            with open(src2, "w", encoding="utf-8") as handle:
                handle.write("probe-two\n")
            try:
                shutil.rmtree(dest, ignore_errors=True)
            except OSError:
                pass
            os.makedirs(dest, exist_ok=True)
        except OSError as exc:
            self.output.info("libini_config: install probe setup skipped: %s" % exc)
            return []

        def _trial(argv):
            try:
                shutil.rmtree(dest, ignore_errors=True)
                os.makedirs(dest, exist_ok=True)
                completed = subprocess.run(
                    argv, stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE, timeout=60)
                if completed.returncode != 0:
                    return False
                for name, want in (("probe1.txt", "probe-one\n"),
                                   ("probe2.txt", "probe-two\n")):
                    got_path = os.path.join(dest, name)
                    try:
                        with open(got_path, "r",
                                  encoding="utf-8") as handle:
                            if handle.read() != want:
                                return False
                    except OSError:
                        return False
                return True
            except Exception:
                return False

        ordered = ["/system/bin/install", "/bin/install",
                   "/usr/bin/install"]
        try:
            for name in ("ginstall", "install"):
                found = shutil.which(name)
                if found and found not in ordered:
                    ordered.append(found)
        except Exception:
            pass
        for cand in ordered:
            try:
                if not (os.path.isfile(cand) and os.access(cand, os.X_OK)):
                    continue
            except OSError:
                continue
            if _trial([cand, "-c", "-m", "644", src1, src2, dest]):
                self.output.info(
                    "libini_config: INSTALL probe passed: %s" % cand)
                return ["INSTALL=\"%s -c\"" % cand]
            self.output.info(
                "libini_config: INSTALL probe rejected: %s" % cand)
        cp_cands = []
        try:
            found_cp = shutil.which("cp")
            if found_cp:
                cp_cands.append(found_cp)
        except Exception:
            pass
        for extra in ("/system/bin/cp", "/bin/cp", "/usr/bin/cp"):
            if extra not in cp_cands:
                cp_cands.append(extra)
        for cp_bin in cp_cands:
            try:
                if not (os.path.isfile(cp_bin)
                        and os.access(cp_bin, os.X_OK)):
                    continue
            except OSError:
                continue
            if _trial([cp_bin, "-fp", src1, src2, dest]):
                self.output.info(
                    "libini_config: INSTALL cp fallback: %s" % cp_bin)
                return ["INSTALL=\"%s -fp\"" % cp_bin,
                        "INSTALL_PROGRAM=\"%s -fp\"" % cp_bin,
                        "INSTALL_DATA=\"%s -fp\"" % cp_bin,
                        "INSTALL_SCRIPT=\"%s -fp\"" % cp_bin]
        self.output.info("libini_config: no working INSTALL found; plain install")
        return []

    def _configure_args_list(self):
        args = [
            "--prefix=/",
            "--bindir=${prefix}/bin",
            "--sbindir=${prefix}/bin",
            "--libdir=${prefix}/lib",
            "--includedir=${prefix}/include",
            "--oldincludedir=${prefix}/include",
            "--disable-nls",
            "--disable-dependency-tracking",
        ]
        if self.options.shared:
            args.extend(["--enable-shared", "--disable-static"])
        else:
            args.extend(["--disable-shared", "--enable-static"])
        return args

    def _dependency(self, name):
        for dependencies in (
            self.dependencies.test,
            self.dependencies.host,
            self.dependencies.build,
        ):
            try:
                return dependencies[name]
            except KeyError:
                continue
        return None

    def _environment(self, for_tests=False):
        env = Environment()
        # PkgConfigDeps writes check.pc into the generators directory. Keep
        # the profile's existing search path while putting generated metadata
        # first.
        env.prepend_path("PKG_CONFIG_PATH", self.generators_folder)

        # Preflight workers guarantee /bin/sh (HMBS_PLATFORM_CAPABILITIES)
        # while the ohos-aarch64 profile pins SHELL/CONFIG_SHELL to
        # /data/service/hnp/bin/bash, which is inaccessible there
        # (`configure[139]: ... inaccessible or not found`, m4 rebuild).
        # Pin both to /bin/sh for our own configure/make steps; this only
        # scopes to this recipe's build env and does not touch the profile.
        env.define("SHELL", "/bin/sh")
        env.define("CONFIG_SHELL", "/bin/sh")

        # Skip Automake's fork-intensive filesystem timestamp resolution
        # probe (`ls -t` in a command-substitution subshell). On HMDFS the
        # probe's fork can fail with `fork: Out of memory` when the worker
        # is under memory pressure, and configure then hard-errors with
        # `ls -t produces unexpected output` (cdecl/18.7.2 precedent, same
        # shared-device family). Both cache values select the upstream
        # documented worst-case default (2s resolution, fractional sleep
        # available), so configure takes the `(cached)` branch without
        # changing build semantics; it only affects the sanity-check sleep
        # interval.
        env.define("am_cv_sleep_fractional_seconds", "yes")
        env.define("am_cv_filesystem_timestamp_resolution", "2")

        # Check include via Environment channel as well (covers any future
        # Autotools-helper path and documents intent alongside generate()).
        # Manual /bin/sh lines rely on the inline prefix above; this append
        # never uses quoted inline form so no leak risk here.
        check_inc = self._check_include_dir()
        if check_inc is not None:
            env.append("CFLAGS", f"-I{check_inc}")
            env.append("CPPFLAGS", f"-I{check_inc}")
        if str(self.settings.os) == "OHOS":
            # /tmp is read-only on the target. Check 0.15.2 also consults
            # TEMP before P_tmpdir, so set all common spellings explicitly.
            # Write-probed (coinor-vol precedent): HMDFS ignores chmod, so
            # makedirs alone does not prove writability.
            test_tmp = self._writable_tmpdir()
            env.define("TMPDIR", test_tmp)
            env.define("TMP", test_tmp)
            env.define("TEMP", test_tmp)
            if for_tests:
                # Check's forked runner uses temporary IPC files, which are
                # restricted on HMDFS. In-process mode keeps all tests.
                env.define("CK_FORK", "no")
                check = self._dependency("check")
                if check is not None:
                    check_libdir = os.path.join(check.package_folder, "lib")
                    if os.path.isdir(check_libdir):
                        # Scoped to make check only; never leaks into
                        # compiler/linker discovery during the build.
                        env.prepend_path("LD_LIBRARY_PATH", check_libdir)
        return env

    def _hmbs_emit(self, line):
        # Dual-channel: conan output + raw stdout so preflight catches it.
        self.output.info(line)
        try:
            print(line, flush=True)
        except Exception:
            pass

    @staticmethod
    def _automake_count(text, label):
        # Single deterministic source: `# LABEL: N` from an automake
        # parallel-tests test-suite.log. No stdout word counting, no
        # arithmetic repair across sources.
        for line in text.splitlines():
            if line.startswith("# " + label + ":"):
                try:
                    return int(line.split(":", 1)[1].strip())
                except ValueError:
                    return 0
        return 0

    def _emit_upstream_test_result(self):
        # Parse the real automake test-suite.log counts and emit the
        # HMBS_UPSTREAM_TEST_RESULT machine-evidence marker (adcli/0.9.2
        # precedent). ding-libs builds several subdirs each with its own
        # test-suite.log plus a top-level aggregate; the aggregate carries
        # the largest TOTAL, so select by largest TOTAL instead of summing
        # (summing would double-count the aggregate).
        suite_logs = []
        try:
            base = self.build_folder or "."
            for root, _dirs, files in os.walk(base):
                if "test-suite.log" in files:
                    suite_logs.append(os.path.join(root, "test-suite.log"))
        except OSError as exc:
            raise ConanInvalidConfiguration(
                f"libini_config upstream log walk failed: {exc!r}")
        if not suite_logs:
            raise ConanInvalidConfiguration(
                "libini_config make check produced no test-suite.log under "
                + str(self.build_folder))
        best = None
        best_total = -1
        best_content = ""
        for log_path in suite_logs:
            try:
                with open(log_path, "r", encoding="utf-8",
                          errors="replace") as handle:
                    content = handle.read()
            except OSError:
                continue
            total = self._automake_count(content, "TOTAL")
            if total > best_total:
                best_total = total
                best = log_path
                best_content = content
        if best is None:
            raise ConanInvalidConfiguration(
                "libini_config test-suite.log unreadable; searched "
                + ", ".join(suite_logs))
        self.output.info(f"libini_config upstream suite log: {best}")
        for line in best_content.splitlines():
            if line.startswith("# "):
                self.output.info(f"libini_config-suite| {line}")
        total = self._automake_count(best_content, "TOTAL")
        passed = self._automake_count(best_content, "PASS")
        xfailed = self._automake_count(best_content, "XFAIL")
        skipped = self._automake_count(best_content, "SKIP")
        failed = (self._automake_count(best_content, "FAIL")
                  + self._automake_count(best_content, "XPASS")
                  + self._automake_count(best_content, "ERROR"))
        discovered = total
        executed = total - skipped
        passed_total = passed + xfailed
        # Self-check identities before emitting; never patch numbers to
        # fit. Fail loudly with the searched paths instead.
        ok_shape = (
            isinstance(discovered, int) and isinstance(executed, int)
            and isinstance(passed_total, int) and isinstance(failed, int)
            and isinstance(skipped, int)
            and discovered >= 0 and executed >= 0
            and passed_total >= 0 and failed >= 0 and skipped >= 0
            and passed_total + failed == executed
            and executed + skipped <= discovered
            and executed <= discovered
        )
        if not ok_shape:
            raise ConanInvalidConfiguration(
                "libini_config upstream counts inconsistent "
                f"(log {best}: TOTAL={total} PASS={passed} XFAIL={xfailed} "
                f"SKIP={skipped} FAIL/XPASS/ERROR={failed})")
        if discovered != 20:
            self.output.warning(
                f"libini_config upstream TOTAL={discovered}, "
                "expected 20 per Makefile.am TESTS audit")
        status = "passed" if failed == 0 else "failed"
        payload = {
            "status": status,
            "framework": "automake",
            "command": "make -j1 check",
            "discovered": discovered,
            "executed": executed,
            "passed": passed_total,
            "failed": failed,
            "skipped": skipped,
        }
        self._hmbs_emit("HMBS_UPSTREAM_TEST_RESULT=" + json.dumps(
            payload, separators=(",", ":")))
        try:
            with open(os.path.join(self.build_folder, "hmbs_upstream.json"),
                      "w", encoding="utf-8") as handle:
                json.dump(payload, handle)
        except OSError as exc:
            self.output.warning(
                f"libini_config persist upstream failed: {exc!r}")
        if status != "passed":
            raise ConanInvalidConfiguration(
                "libini_config upstream make check did not pass: "
                + json.dumps(payload))
        return payload

    def build(self):
        apply_conandata_patches(self)

        # HMDFS ignores chmod and sets setgid on new directories; autoconf's
        # `umask 077` then yields drwx--S--- and config.status fails with
        # `Permission denied` writing subs1.awk (E129). The tarball's
        # pregenerated configure already contains that umask, so patch the
        # generated script in place at build time (zzuf 0.15 precedent).
        # No autoreconf is run, so no autoconf/m4 rebuild is needed.
        configure_path = os.path.join(self.source_folder, "configure")
        if os.path.isfile(configure_path):
            with open(configure_path, "r", encoding="utf-8", errors="surrogateescape") as f:
                content = f.read()
            if "umask 077" in content:
                content = content.replace("umask 077", "umask 022")
                with open(configure_path, "w", encoding="utf-8", errors="surrogateescape") as f:
                    f.write(content)
                self.output.info("patched umask 077 -> 022 in pregenerated configure (E129)")

        # HMDFS: once Conan has created the build tree the parent directories
        # are no longer reachable through getcwd(), so the `pwd` probe that
        # Autoconf runs before re-executing configure under
        # CONFIG_SHELL=bash fails with "working directory cannot be
        # determined". Publishing the logical $PWD lets the shell resolve the
        # directory without calling getcwd().
        os.environ["PWD"] = self.build_folder
        # Probed TMPDIR (coinor-vol precedent) at process level too: clang
        # creates temp files via TMPDIR during the sanity link, and an
        # unprobed/unwritable dir fails there with Error 77 even when the
        # compiler itself is fine. Log the choice so the preflight proves it.
        if str(self.settings.os) == "OHOS":
            probed_tmp = self._writable_tmpdir()
            os.environ["TMPDIR"] = probed_tmp
            os.environ["TMP"] = probed_tmp
            os.environ["TEMP"] = probed_tmp
            self.output.info(f"libini_config probed TMPDIR: {probed_tmp}")
        # Configure must bypass the profile's inaccessible hnp bash. The
        # profile sets `[buildenv] CONFIG_SHELL/SHELL=/data/service/hnp/bin/bash`,
        # and `Autotools.configure()` (like any `self.run(..., env="conanbuild")`)
        # re-sources conanbuild.sh after our with-block os.environ, so
        # `Environment.define(SHELL=/bin/sh)` alone loses and the pregenerated
        # configure re-execs under the bad bash at line 139. Use an inline
        # `CONFIG_SHELL=/bin/sh SHELL=/bin/sh /bin/sh configure` prefix which
        # wins over conanbuild.sh (ballandpaddle/0.8.1 precedent). All
        # _environment() keys are repeated inline in _inline_prefix() so the
        # manual line keeps TMPDIR/am_cv_*/PKG_CONFIG_PATH/PWD semantics that
        # a bare manual call would otherwise discard.
        configure_cmd = shlex.join(
            ["/bin/sh", configure_path] + self._configure_args_list()
        )
        # Compiler fallback (config.log proves profile CC is "inaccessible
        # or not found", exit 127 -> Error 77): probe a driver that really
        # links and pass it as a single-token CC precious var inline, which
        # wins over conanbuild.sh for this invocation (same SHELL pattern
        # as above; experience 2 keeps single-token vars). No flags change.
        configure_prefix = self._inline_prefix()
        if str(self.settings.os) == "OHOS":
            try:
                working_cc = self._find_working_compiler()
            except Exception as exc:
                self.output.warning(f"libini_config CC discovery skipped: {exc!r}")
                working_cc = ""
            if working_cc:
                configure_prefix = f"CC={shlex.quote(working_cc)} {configure_prefix}"
        try:
            self.run(f"{configure_prefix} {configure_cmd}", env="conanbuild")
        except Exception:
            # Surface the real first error (config.log holds the failing
            # conftest command; the summary line alone hides TMPDIR vs
            # toolchain cause). Bounded dump, then re-raise.
            try:
                self._dump_config_log()
            except Exception as exc:
                self.output.warning(f"libini_config config.log dump skipped: {exc!r}")
            raise
        make_args = shlex.join(self._make_args_list())
        self.run(f"{self._inline_prefix()} make {make_args}", env="conanbuild")

        # Run every upstream Automake test, not a reduced smoke subset.
        self.run(
            f"{self._inline_prefix(for_tests=True)} make check {make_args}",
            env="conanbuild",
        )
        # Machine evidence for the HMBS gate: counts come from the real
        # test-suite.log (# TOTAL/# PASS/... block), never estimates.
        self._emit_upstream_test_result()

    def package(self):
        make_args = shlex.join(self._make_args_list())
        install_tokens = self._select_install_args()
        install_suffix = (" " + " ".join(install_tokens)
                          if install_tokens else "")
        self.run(
            f"{self._inline_prefix()} make install {make_args}{install_suffix} "
            f"DESTDIR={shlex.quote(self.package_folder)}",
            env="conanbuild",
        )

        # This recipe ships only the ini_config component. The ding-libs
        # source tree also builds the companion dhash helper library; remove
        # its artifacts so consumers link only against libini_config.
        rm(self, "libdhash.*", folder=os.path.join(self.package_folder, "lib"))
        rm(self, "dhash.h", folder=os.path.join(self.package_folder, "include"))
        rm(self, "dhash.pc", folder=os.path.join(self.package_folder, "lib", "pkgconfig"))
        rmdir(self, os.path.join(self.package_folder, "share"))
        # Libtool archives contain the build-time absolute libdir and are not
        # needed by Conan consumers; cpp_info/pkg-config provide link metadata.
        rm(self, "*.la", folder=os.path.join(self.package_folder, "lib"))
        copy(self, "COPYING", src=self.source_folder, dst=os.path.join(self.package_folder, "licenses"), keep_path=False)
        copy(
            self,
            "COPYING.LESSER",
            src=self.source_folder,
            dst=os.path.join(self.package_folder, "licenses"),
            keep_path=False,
        )
        # Carry the real upstream result into the package so cache-hit
        # test_package runs can re-emit without re-running the build
        # (zydis/4.1.1 precedent).
        try:
            src = os.path.join(self.build_folder, "hmbs_upstream.json")
            if os.path.isfile(src):
                dst_dir = os.path.join(self.package_folder, "res")
                os.makedirs(dst_dir, exist_ok=True)
                shutil.copyfile(
                    src, os.path.join(dst_dir, "hmbs_upstream.json"))
            else:
                self.output.warning(
                    "HMBS diag hmbs_upstream.json missing in package()")
        except Exception as exc:
            self.output.warning(
                f"libini_config package upstream copy failed: {exc!r}")

    def package_info(self):
        self.cpp_info.set_property("cmake_file_name", "libini_config")
        self.cpp_info.set_property("cmake_target_name", "libini_config::libini_config")
        self.cpp_info.set_property("pkg_config_name", "ini_config")
        self.cpp_info.libs = ["ini_config"]
        if str(self.settings.os) in ("Linux", "OHOS"):
            self.cpp_info.system_libs = ["m", "pthread"]
