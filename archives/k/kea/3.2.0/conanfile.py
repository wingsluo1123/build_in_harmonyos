#!/usr/bin/env python3
"""Conan recipe — kea 3.2.0 (ISC Kea DHCP suite, Meson, whole tree).

The package is the complete ISC Kea 3.2.0 DHCP product: the kea-dhcp4,
kea-dhcp6, kea-dhcp-ddns and kea-lfc daemons, the perfdhcp benchmarking
client, every libkea-* shared library built by the tree, the bundled hook
plug-ins (libdhcp_*.so, e.g. the HA / lease-cmds / limits family) and the
public headers (include/kea/**) that server, hook and utility code compiles
against.

Kea 3.2.0 no longer ships the standalone kea-ctrl-agent - upstream removed the
deprecated daemon (ChangeLog: "The deprecated control agent has been
removed"); the servers' built-in control channels replace it, so the daemon
set is the four listed above.  The helper shell scripts (keactrl, kea-admin,
kea-shell) are not packaged either: they bake the absolute install prefix at
configure time and are not relocatable.

Family reuse: the recipe derives from the merged kea-hook-* 3.0.3 family
recipes (kea-hook-ha being the base) and reuses their machinery verbatim - the
sh-wrapped Meson invocation (the HarmonyOS PC kernel refuses script execve on
the Conan meson wrapper), the -j 8 compile cap (posix_spawn EAGAIN under the
OHOS process quota), materialized sonames (the /storage sandbox denies
symlinks), the package() 0-byte flush self-heal and the LD_LIBRARY_PATH
injection for the configure-time meson probes.  Patches 0001-0005 are the
family template rebased onto the 3.2.0 tree (0002/0005 re-anchored: 3.2.0
dropped the boost/static_assert.hpp include, moved the netlink include block
and replaced BOOST_STATIC_ASSERT with plain static_assert); patches 0006-0020
add the new exposures of the same platform classes (test-runner script
execve, run-time spawn fallback, /tmp read-only, AF_UNIX bind and
SIOCGIFHWADDR probes) - all listed in conandata.yml.

The build runs the whole upstream Meson test suite: the package adapts the
whole tree, so every registered test() suite is the honest verification scope
(the kea-hook-* family recipes run only their own component's suites).
"""
import json
import os
import shutil
import time

from conan import ConanFile
from conan.errors import ConanException
from conan.tools.env import Environment
from conan.tools.files import apply_conandata_patches, copy, export_conandata_patches, get
from conan.tools.gnu import PkgConfigDeps
from conan.tools.layout import basic_layout
from conan.tools.meson import MesonToolchain

# A worker whose process/thread table is momentarily exhausted makes ninja
# abort the whole compile on its first spawn:
#     ninja: fatal: posix_spawn: Resource temporarily unavailable
# The tree is fine - the identical command built 1433/1433 targets on a less
# loaded worker - so ninja's own wording (plus the plain errno text the
# kernel returns to any failing fork/exec) is the signature to retry on.
_SPAWN_PRESSURE_MARKERS = (
    "posix_spawn",
    "resource temporarily unavailable",
    "cannot fork",
    "can't fork",
    "fork: retry",
)


class KeaConan(ConanFile):
    name = "kea"
    version = "3.2.0"
    description = ("ISC Kea 3.2.0 DHCP server suite for HarmonyOS PC: "
                   "kea-dhcp4/kea-dhcp6/kea-dhcp-ddns/kea-lfc daemons, perfdhcp "
                   "client, the libkea-* libraries, the bundled hook plug-ins "
                   "and the public headers")
    license = "MPL-2.0"
    homepage = "https://www.isc.org/kea/"
    url = "https://gitlab.isc.org/isc-projects/kea"

    package_type = "shared-library"
    settings = "os", "compiler", "build_type", "arch"
    options = {"tests": [True, False]}
    default_options = {"tests": True}

    # Executable artifacts (upstream installs them into SBINDIR); packaged under
    # bin/ the Conan way.  Tuples are (path under the build folder, name).
    binaries = (
        ("src/bin/dhcp4", "kea-dhcp4"),
        ("src/bin/dhcp6", "kea-dhcp6"),
        ("src/bin/d2", "kea-dhcp-ddns"),
        ("src/bin/lfc", "kea-lfc"),
        ("src/bin/perfdhcp", "perfdhcp"),
    )
    # Kea shared libraries are libkea-*.so*; the hook plug-ins under
    # src/hooks/** are libdhcp_<name>.so (the DHCP hooks) or
    # libddns_gss_tsig.so (the D2 hook, built only with the Kerberos back-end,
    # which this recipe disables).
    kea_lib_prefix = "libkea-"
    hook_lib_prefixes = ("libdhcp_", "libddns_")

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        # Mandatory third-party dependencies of the Kea 3.2.0 build.  boost is
        # pinned: 1.90/1.91 packages miss boost/interprocess, circular_buffer,
        # format and assign headers that Kea actually includes.  All three are
        # needed to compile the packaged headers (they appear in the include
        # chain of kea/dhcp, kea/asiolink and kea/log), hence
        # transitive_headers - same interface as the merged kea-hooks package.
        self.requires("boost/1.85.0", transitive_headers=True)
        self.requires("log4cplus/2.2.0.1", transitive_headers=True)
        self.requires("openssl/3.5.8.1", transitive_headers=True)

    def build_requirements(self):
        # Kea requires meson >= 1.10 here: the boost packages ship no
        # libboost_system, which only resolves through the header-only module
        # fallback added in meson 1.10.
        self.tool_requires("meson/1.11.0")
        if self.options.tests:
            self.test_requires("gtest/1.17.0.1")

    def layout(self):
        basic_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def generate(self):
        PkgConfigDeps(self).generate()
        tc = MesonToolchain(self)
        tc.project_options["tests"] = "enabled" if self.options.tests else "disabled"
        # Optional back-ends: no Conan dependency is provided for them, disable
        # them explicitly so the build does not depend on host-side probes.
        tc.project_options["crypto"] = "openssl"
        tc.project_options["mysql"] = "disabled"
        tc.project_options["postgresql"] = "disabled"
        tc.project_options["netconf"] = "disabled"
        tc.project_options["krb5"] = "disabled"
        # The OHOS musl <pthread.h> does not declare pthread_setcancelstate(),
        # which boost/core/detail/sp_thread_sleep.hpp calls (used through
        # Boost.Asio).  The upstream escape hatch keeps it compiling.
        tc.extra_cxxflags.append("-DBOOST_SP_NO_PTHREAD_SETCANCELSTATE")
        # Meson probes the static linker in project(); the configured compiler
        # directory carries llvm-ar/llvm-ranlib, and OHOS resolves binaries by
        # absolute path only, so derive them from the compiler location.
        compilers = self.conf.get("tools.build:compiler_executables", default={}, check_type=dict)
        cc = compilers.get("c") if compilers else None
        if cc:
            tool_dir = os.path.dirname(cc)
            tc.binaries["ar"] = os.path.join(tool_dir, "llvm-ar")
            tc.binaries["ranlib"] = os.path.join(tool_dir, "llvm-ranlib")
        tc.generate()
        # Meson runs compile-and-run feature probes during configure (log4cplus,
        # openssl, boost), so the shared dependencies must be resolvable at run
        # time while configuring.
        env = Environment()
        for dep in self.dependencies.values():
            for libdir in dep.cpp_info.libdirs:
                env.append_path("LD_LIBRARY_PATH", libdir)
        env.vars(self).save_script("conanbuildenv-kea-runtime")

    def _meson(self):
        # bin/meson in the Conan meson package is a shebang shell wrapper;
        # invoke it through sh so it runs on HarmonyOS PC too (see the module
        # docstring).  Returns the ready-made command prefix.
        meson_bin = os.path.join(self.dependencies.build["meson"].package_folder,
                                 "bin", "meson")
        return 'sh "{}"'.format(meson_bin)

    def build(self):
        apply_conandata_patches(self)
        # Replicate conan's Meson helper command line (same --native-file,
        # build dir, source dir and --prefix), only with the sh-prefixed
        # wrapper.
        native_file = os.path.join(self.build_folder, "conan",
                                   "conan_meson_native.ini")
        meson = self._meson()
        # Meson's release default compiles assertions out (-DNDEBUG); the
        # upstream suite exercises debug-only paths (the log formatter death
        # test relies on an assert), so keep the assertions enabled for the
        # test build while retaining the release optimisation level.
        ndebug = ' -Db_ndebug=false' if self.options.tests else ''
        self._meson_setup(meson, ndebug, native_file)
        self._meson_compile(meson)
        self._materialize_sonames()
        if self.options.tests:
            self._meson_test(meson)

    def _meson_setup(self, meson, ndebug, native_file):
        """Configure the tree, surviving a transient spawn-resource spike.

        Same exposure as @ref _meson_compile, one step earlier: ``meson setup``
        runs the compiler and library probes, so on a worker that is
        momentarily out of process/thread slots its first fork dies
        (PR CI #b84771: ``meson[2]: can't fork - try again``) and the whole
        ``conan create`` is lost before a single target is built, although
        nothing is wrong with the tree.

        Configuring is deterministic and costs seconds next to the build, so a
        spike is retried with the same backoff as the compile; anything else is
        re-raised on the first attempt, so a genuine configuration error still
        surfaces immediately.
        """
        cmd = '{} setup{} --native-file "{}" "{}" "{}" --prefix=/'.format(
            meson, ndebug, native_file, self.build_folder, self.source_folder)
        log_file = os.path.join(self.generators_folder or self.build_folder,
                                "meson-setup.log")
        rc_file = log_file + ".rc"
        attempts = 3
        for attempt in range(1, attempts + 1):
            self.output.info("kea: meson setup attempt {}/{}, host: {}".format(
                attempt, attempts, self._fork_free_pressure()))
            status, output = self._run_logged(cmd, log_file, rc_file)
            if status == 0:
                return
            if not self._spawn_spike(output):
                raise ConanException(
                    "kea: meson setup failed (exit {}); full output in "
                    "{}".format(status, log_file))
            if attempt == attempts:
                raise ConanException(
                    "kea: meson setup still aborted by spawn-resource "
                    "exhaustion after {} attempts (host: {}); full output in "
                    "{}".format(attempts, self._fork_free_pressure(), log_file))
            delay = 15 * 2 ** (attempt - 1)
            self.output.warning(
                "kea: meson setup aborted by spawn-resource exhaustion; "
                "resetting the configure state and retrying in {}s".format(delay))
            self._reset_meson_state()
            time.sleep(delay)

    def _reset_meson_state(self):
        """Drop meson's own configure state so ``meson setup`` can run again.

        A configure that dies mid-way leaves ``meson-private/`` - the coredata
        that makes the next ``meson setup`` answer "Directory already
        configured" - and ``meson-info/`` behind.  Both are meson's, so both go;
        the generated native file lives in the same directory tree and must
        survive, hence no wholesale cleanup of the build directory.
        """
        for name in ("meson-private", "meson-info"):
            shutil.rmtree(os.path.join(self.build_folder, name),
                          ignore_errors=True)

    def _meson_compile(self, meson):
        """Run ``meson compile``, surviving a transient spawn-resource spike.

        The OHOS workers momentarily run out of process/thread slots and ninja
        then aborts on its *first* spawn with ``posix_spawn: Resource
        temporarily unavailable``, losing the whole ``conan create`` even
        though nothing is wrong with the tree: PR CI #80227 built 1433/1433
        targets with this exact command line, while #89023 on the same PR died
        before the first target.  Retry such a spike with a smaller burst -
        ninja resumes incrementally from what is already built, so the spike
        costs wall time, not the build - and re-raise anything else at once so
        a genuine compile error still surfaces on the first try.

        The burst follows the ``tools.build:jobs`` device-admission conf (the
        lever the rest of the tree uses to cap the concurrent memory and
        process peak) and falls back to the 8 of the kea-hook-* family recipes.
        """
        jobs = self.conf.get("tools.build:jobs", default=8, check_type=int)
        ladder = [jobs]
        for burst in (max(2, jobs // 2), 2):
            if burst < ladder[-1]:
                ladder.append(burst)
        log_file = os.path.join(self.generators_folder or self.build_folder,
                                "meson-compile.log")
        rc_file = log_file + ".rc"
        for attempt, burst in enumerate(ladder, 1):
            # A spike is a property of the host, not of the tree, and it can be
            # over by the next attempt: snapshot (fork-free) what the worker
            # looked like, so a red CI log tells a loaded box from a broken one.
            self.output.info(
                "kea: meson compile attempt {}/{} (-j {}), host: {}".format(
                    attempt, len(ladder), burst, self._fork_free_pressure()))
            status, output = self._run_logged(
                '{} compile -C "{}" -j {}'.format(meson, self.build_folder,
                                                  burst),
                log_file, rc_file)
            if status == 0:
                self.output.info("kea: meson compile done with -j {}".format(burst))
                return
            if attempt == len(ladder) or not self._spawn_spike(output):
                raise ConanException(
                    "kea: meson compile failed with -j {} (exit {}); "
                    "full output in {}".format(burst, status, log_file))
            delay = 15 * 2 ** (attempt - 1)
            self.output.warning(
                "kea: meson compile aborted by spawn-resource exhaustion at "
                "-j {}; retrying with -j {} in {}s".format(
                    burst, ladder[attempt], delay))
            time.sleep(delay)

    def _meson_test(self, meson):
        """Run the upstream suite; re-run what failed, isolated, before failing.

        The whole upstream suite is the honest verification scope (this package
        adapts the whole tree), so no suite is skipped and the first pass is
        always the full suite.  Part of it is nevertheless sensitive to the
        *host's* wall time rather than to the tree: kea's HA state-transition
        matrix drives an in-process partner over real time, so a heartbeat
        starved by a loaded box makes a case assert a state its own timing
        never reached.  Measured on the porting box, the same cases take 0.3 s
        normally and 20 s / 70 s / 290 s under load, and the *set* of failures
        moves between runs (two cases in one pass, three other cases in the
        next) - the signature of a race, not of a defect.

        For PR #14646 that surfaced as CI-only noise: the same tree and the same
        command passed on worker CI-014 (#88903) and failed on CI-030 / CI-038
        (#89023, #89556) for this one suite.

        A failed pass therefore re-runs the *failing cases* alone, up to twice:
        measured here, re-running the whole suite was not the effective rescue
        - alone it failed twice more, each time with a different pair of cases
        (a rotating failure set), while the failing cases themselves passed in
        630 ms when run alone.  Each pass is bounded with `timeout` because the
        whole `conan create` has a 3600 s budget in CI and a starved box must
        not be able to eat it (a non-gtest suite, whose log carries no per-case
        list, is re-run whole and bounded the same way).  A genuine defect
        fails every attempt and is raised here together with the logs; a
        host-induced flake is reported as a warning naming the attempt that
        recovered, so an amber log still tells a loaded box from a broken tree.

        --timeout-multiplier 4 (8 for the retries): upstream raised the long HA
        test timeout to 240 s and the long DHCP service tests can exceed the
        default per-test budget on loaded workers; the family recipes use the
        same 4x headroom.
        """
        log_dir = os.path.join(self.build_folder, "meson-logs")
        log_file = os.path.join(log_dir, "testlog.json")
        status = self.run('{} test -v --timeout-multiplier 4 -C "{}"'.format(
            meson, self.build_folder), ignore_errors=True)
        if status == 0:
            return

        failed = self._failed_suites(log_file)
        if not failed:
            raise ConanException(
                "kea: meson test failed (exit {}) and {} lists no failing "
                "suite; the reason is in the run above".format(status, log_file))
        cases = self._failed_cases(log_file)
        host = self._fork_free_pressure()
        self.output.warning(
            "kea: meson test failed for {} (exit {}); re-running the failing "
            "case(s) alone, host: {}".format(", ".join(failed), status, host))

        # Two attempts, each pass capped at 150 s: an isolated case needs
        # milliseconds when the box is fair, and the cap keeps the worst case
        # (~300 s) inside the 3600 s budget of the CI `conan create` even if a
        # starved box stalls every case again.
        pending = failed
        for attempt in (1, 2):
            logbase = "kea-test-retry-{}".format(attempt)
            pending = []
            for suite in failed:
                if cases.get(suite):
                    rc = self._test_pass(
                        meson, [suite], logbase, timeout=150, verbose=True,
                        test_args="--gtest_filter=" + ":".join(cases[suite]))
                else:
                    # No per-case list in the log (shell suite): the finest
                    # scope available is the suite itself.
                    rc = self._test_pass(meson, [suite], logbase, timeout=150,
                                         verbose=True)
                if rc:
                    pending.append(suite)
            if not pending:
                self.output.warning(
                    "kea: {} failed on the loaded first pass and passed when "
                    "the failing case(s) were re-run alone (attempt {} of 2) - "
                    "host-induced flake, not a tree defect (log {})".format(
                        ", ".join(failed), attempt,
                        os.path.join(log_dir, logbase + ".txt")))
                return
        raise ConanException(
            "kea: {} still failing after the failing case(s) were re-run alone "
            "twice (host: {}); logs: {} and {}".format(
                ", ".join(pending), host, log_file,
                ", ".join(os.path.join(log_dir, "kea-test-retry-{}.txt".format(i))
                          for i in (1, 2))))

    def _test_pass(self, meson, suites, logbase, timeout, verbose=False,
                   test_args=None):
        """One `meson test` pass over ``suites``; returns its exit status.

        ``timeout`` bounds the pass so a starved case cannot consume the CI
        build budget (see @ref _meson_test); a killed pass simply counts as a
        failed attempt.
        """
        parts = ["timeout", str(timeout), meson, "test", "-C",
                 '"{}"'.format(self.build_folder), "--no-rebuild",
                 "--print-errorlogs", "--timeout-multiplier", "8",
                 "--logbase", logbase]
        if verbose:
            parts.append("-v")
        if test_args:
            parts.append('--test-args="{}"'.format(test_args))
        parts.extend('"{}"'.format(name) for name in suites)
        return self.run(" ".join(parts), ignore_errors=True)

    @staticmethod
    def _failed_suites(log_file):
        """Names of the suites meson reported as not OK in its JSON log.

        Meson writes one JSON object per test (JSON Lines) and prefixes the
        name with the project ("kea:dhcp-ha-lib-tests"), while ``meson test``
        filters on the bare name, so the prefix is stripped.  An unreadable log
        yields an empty list, which the caller treats as "no usable evidence"
        rather than as "everything passed".
        """
        failed = []
        for name, _ in KeaConan._log_entries(log_file):
            if name not in failed:
                failed.append(name)
        return failed

    @staticmethod
    def _failed_cases(log_file):
        """Failed gtest cases per failing suite, from meson's JSON log.

        kea's C++ suites are gtest binaries, so each case that failed is listed
        by the runner itself (``[  FAILED  ] Fixture.Case (12 ms)``); the
        summary header (``[  FAILED  ] 2 tests, listed below:``) is not a case.
        Suites that are shell scripts yield an empty list and are only ever
        retried whole.
        """
        cases = {}
        for name, entry in KeaConan._log_entries(log_file):
            found = []
            for line in entry.get("stdout", "").splitlines():
                if not line.startswith("[  FAILED  ] "):
                    continue
                case = line[len("[  FAILED  ] "):].split(" (")[0].strip()
                if not case or "listed below" in case or case.endswith("tests."):
                    continue
                if case not in found:
                    found.append(case)
            cases[name] = found
        return cases

    @staticmethod
    def _log_entries(log_file):
        """The non-OK meson test log entries as (bare name, entry) pairs."""
        entries = []
        try:
            with open(log_file, encoding="utf-8", errors="replace") as handle:
                for line in handle:
                    line = line.strip()
                    if not line:
                        continue
                    try:
                        entry = json.loads(line)
                    except ValueError:
                        continue
                    if entry.get("result", "OK") == "OK":
                        continue
                    name = entry.get("name", "").split(":", 1)[-1]
                    if name:
                        entries.append((name, entry))
        except OSError:
            pass
        return entries

    def _run_logged(self, cmd, log_file, rc_file):
        """Run ``cmd``; returns (exit status, this pass' output).

        The output is tee'd so that it stays live on the CI console while also
        being kept for triage, and the real status is carried out through fd 3:
        a pipeline reports tee's status, and POSIX sh has no ``pipefail``.
        """
        try:
            offset = os.path.getsize(log_file)
        except OSError:
            offset = 0
        self.run('exec 3>"{}"; {{ {} ; echo $? >&3 ; }} 2>&1 | tee -a "{}"; '
                 'exec 3>&-'.format(rc_file, cmd, log_file), ignore_errors=True)
        try:
            with open(rc_file) as handle:
                status = int(handle.read().strip() or 1)
        except (OSError, ValueError):
            status = 1
        try:
            with open(log_file, "rb") as handle:
                handle.seek(offset)
                output = handle.read().decode("utf-8", "replace")
        except OSError:
            output = ""
        return status, output

    @staticmethod
    def _spawn_spike(output):
        """True when ``output`` carries a spawn-resource failure signature."""
        low = output.lower()
        return any(marker in low for marker in _SPAWN_PRESSURE_MARKERS)

    @staticmethod
    def _fork_free_pressure():
        """Snapshot the host's process/thread pressure without forking.

        Reads /proc only: the moment a spawn fails with EAGAIN is exactly the
        wrong time to spawn a helper, so the diagnostics never fork.
        """
        bits = []
        try:
            with open("/proc/loadavg") as handle:
                bits.append("load=" + "/".join(handle.read().split()[:3]))
        except OSError:
            pass
        procs = threads = 0
        try:
            for entry in os.listdir("/proc"):
                if not entry.isdigit():
                    continue
                procs += 1
                try:
                    threads += len(os.listdir("/proc/{}/task".format(entry)))
                except OSError:
                    pass
        except OSError:
            pass
        if procs:
            bits.append("procs={} threads={}".format(procs, threads))
        try:
            with open("/proc/self/limits") as handle:
                for line in handle:
                    if line.startswith("Max processes"):
                        bits.append("max_procs=" + " ".join(line.split()[3:5]))
                        break
        except OSError:
            pass
        return ", ".join(bits) or "unavailable"

    def _iter_built_libs(self):
        """Yield (path, name) for every real Kea library built in the tree.

        Walks the library tree (src/lib) and the hook plug-in tree (src/hooks),
        skipping Meson intermediates (.p/), the test directories (test-only
        helper libraries must not ship) and the SHSYM .symbols intermediates.
        """
        for sub in ("src/lib", "src/hooks"):
            for root, dirs, files in os.walk(os.path.join(self.build_folder, sub)):
                dirs[:] = [d for d in dirs
                           if not d.endswith(".p") and "test" not in d.lower()]
                for name in files:
                    # meson's SHSYM intermediates (libkea-X.so.N.M.K.symbols)
                    # match the library patterns below and must not ship.
                    if name.endswith(".symbols") or ".so" not in name:
                        continue
                    if not (name.startswith(self.kea_lib_prefix) or
                            name.startswith(self.hook_lib_prefixes)):
                        continue
                    yield os.path.join(root, name), name

    def _materialize_sonames(self):
        """Create the versioned soname files as real copies in the build tree.

        Meson links the Kea libraries with ``version: 'N.M.K'`` and publishes
        the soname ``libkea-X.so.N`` as a *symlink* to the real
        ``libkea-X.so.N.M.K`` file.  The HarmonyOS /storage sandbox denies
        symlink creation (``ln -s`` -> EPERM), so those links never appear and
        every loader lookup by NEEDED name fails with "Error loading shared
        library libkea-X.so.N" (the meson test binaries, and later the packaged
        libraries at dlopen time, all need the soname files).  Recreate them as
        copies: idempotent, and on regular Linux hosts where meson already made
        the symlink the copy is skipped, keeping one physical library per name.
        """
        for path, name in self._iter_built_libs():
            parts = name.split(".")
            if not (len(parts) >= 4 and parts[1] == "so" and parts[2].isdigit()
                    and parts[3].isdigit()):
                continue
            soname = ".".join(parts[:3])
            soname_path = os.path.join(os.path.dirname(path), soname)
            if os.path.exists(soname_path) or os.path.islink(soname_path):
                continue
            shutil.copyfile(path, soname_path)

    def package(self):
        copy(self, "COPYING", src=self.source_folder,
             dst=os.path.join(self.package_folder, "licenses"))
        self._package_binaries()
        self._package_libraries()
        self._package_headers()

    def _package_binaries(self):
        bin_dst = os.path.join(self.package_folder, "bin")
        for subdir, name in self.binaries:
            src_dir = os.path.join(self.build_folder, subdir)
            if not os.path.exists(os.path.join(src_dir, name)):
                raise ConanException(
                    "package(): expected executable {} was not built in {}".format(
                        name, src_dir))
            copy(self, name, src=src_dir, dst=bin_dst)

    def _package_libraries(self):
        """Ship every built Kea library with its soname names materialized.

        The loader needs ``libX.so.N`` at run time and the compiler driver
        needs ``libX.so`` for ``-l`` at consumer link time; the HarmonyOS
        /storage sandbox denies symlink creation, so both are created as real
        copies when meson could not publish the links (on hosts where meson
        could, the build-tree links are recreated as links as the merged
        kea-hook-* family recipes do).
        """
        hooks_dst = os.path.join(self.package_folder, "lib", "kea", "hooks")
        lib_dst = os.path.join(self.package_folder, "lib")
        for path, name in self._iter_built_libs():
            dst_dir = hooks_dst if name.startswith(self.hook_lib_prefixes) else lib_dst
            dst_path = os.path.join(dst_dir, name)
            os.makedirs(dst_dir, exist_ok=True)
            if os.path.islink(path):
                if os.path.lexists(dst_path):
                    os.remove(dst_path)
                try:
                    os.symlink(os.readlink(path), dst_path)
                    continue
                except OSError:
                    # Filesystems without symlink support: fall back to a copy.
                    pass
            shutil.copyfile(path, dst_path)
            # Materialize the soname (libX.so.N) and the plain linker name
            # (libX.so) as copies when meson could not create the symlinks
            # (the OHOS sandbox denies them).  The plain name only matters for
            # the versioned libraries.
            parts = name.split(".")
            if len(parts) >= 4 and parts[1] == "so" and parts[2].isdigit():
                for extra in (".".join(parts[:3]), parts[0] + ".so"):
                    extra_path = os.path.join(dst_dir, extra)
                    if not os.path.lexists(extra_path):
                        shutil.copyfile(path, extra_path)
        self._heal_empty_libraries(hooks_dst, lib_dst)

    def _heal_empty_libraries(self, *dirs):
        """Defence against a transient OHOS /storage flush issue seen on the
        device: a copied library can land as a 0-byte file, which breaks the
        loader's NEEDED lookup at run time.  Re-check every packaged Kea
        library and re-copy any empty one from the build tree; the re-copy
        itself is verified as well - if the flush anomaly reproduces, the
        package step fails instead of shipping a 0-byte library.
        """
        src_map = {}
        for path, name in self._iter_built_libs():
            src_map.setdefault(name, path)
        for lib_dir in dirs:
            if not os.path.isdir(lib_dir):
                continue
            for name in os.listdir(lib_dir):
                dst_path = os.path.join(lib_dir, name)
                if os.path.islink(dst_path) or os.path.isdir(dst_path):
                    continue
                if ".so" not in name or os.path.getsize(dst_path) > 0:
                    continue
                src = src_map.get(name)
                if src is None:
                    # Soname / plain-name copy: resolve to the versioned source.
                    base = name[:name.index(".so")]
                    for cand_name, cand_path in src_map.items():
                        if cand_name.startswith(base + ".so."):
                            src = cand_path
                            break
                if src is None:
                    raise ConanException(
                        "package(): empty library {} has no build-tree source".format(
                            name))
                for _attempt in range(3):
                    shutil.copyfile(src, dst_path)
                    if os.path.getsize(dst_path) > 0:
                        break
                else:
                    raise ConanException(
                        "package(): {} is still 0 bytes after 3 re-copies from "
                        "the build tree (persistent /storage flush failure)".format(name))
                self.output.warning(
                    "package(): re-copied empty artifact {} from the build tree".format(name))

    def _package_headers(self):
        """Copy the public headers as upstream installs them:
        <prefix>/include/kea/<module-path>, matching the
        install_headers(subdir: 'kea/...') calls in the tree (the generated
        message headers are committed in the release tarball, so the source
        tree carries the full installed set).
        """
        src_root = os.path.join(self.source_folder, "src", "lib")
        dst_root = os.path.join(self.package_folder, "include", "kea")
        for root, dirs, files in os.walk(src_root):
            dirs[:] = [d for d in dirs if d != "tests"]
            for name in files:
                if not name.endswith(".h"):
                    continue
                relative = os.path.relpath(os.path.join(root, name), src_root)
                dst_path = os.path.join(dst_root, relative)
                os.makedirs(os.path.dirname(dst_path), exist_ok=True)
                shutil.copy2(os.path.join(root, name), dst_path)

    def package_info(self):
        # The package is the whole suite; the libraries a consumer links
        # against are the core ones the daemons and hooks build on - the error
        # model (libkea-exceptions) and the utility layer (libkea-util) - the
        # same "representative core library" pattern the sibling kea-hooks
        # package uses.
        self.cpp_info.libs = ["kea-exceptions", "kea-util"]
        self.cpp_info.bindirs = ["bin"]
        # Kea installs its headers under <prefix>/include/kea and includes them
        # as <exceptions/...>, <util/...>, so the include root is include/kea.
        self.cpp_info.includedirs = [os.path.join("include", "kea")]
        self.cpp_info.libdirs = ["lib"]
        if self.settings.os == "OHOS":
            # The packaged Kea headers reach boost/core/detail/sp_thread_sleep.hpp
            # (through Boost.Asio and boost/shared_ptr.hpp), which calls
            # pthread_setcancelstate() that the OHOS musl pthread.h does not
            # declare.  Consumers need the same boost escape hatch this recipe
            # uses while building.
            self.cpp_info.defines = ["BOOST_SP_NO_PTHREAD_SETCANCELSTATE"]
