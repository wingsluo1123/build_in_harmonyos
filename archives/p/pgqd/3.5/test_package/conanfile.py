#!/usr/bin/env python3
"""test_package for pgqd — drives the installed daemon end to end on OHOS.

The functional flow lives in test_pgqd.sh: it provisions a throwaway PostgreSQL
cluster (postgresql/16.10 is a test-only tool_require) and runs the installed
`pgqd` against it as a real daemon, then runs the upstream cases that do not
need the PgQ extension.

Execution goes through `self.run()` (the CI's L0d gate requires it in test()),
but the *retry* is deliberately Python-side.  OHOS CI workers intermittently
cannot fork under load ("fork: Resource temporarily unavailable"), and a
shell-level retry cannot survive that: its backoff (`sleep`), its log reading
(`cat`) and its signature matching (`grep`) are all external commands that need
to fork too, so the retry dies before the retried command gets a second chance
— which is exactly what happened to the first version of this file.  In Python
nothing on the retry path forks: `time.sleep()` is a syscall, the transcript is
matched in-process, and a failed fork/posix_spawn reaches us as a
ConanException that we can catch.

Retrying the whole flow blind would still waste the attempts on a worker that is
*currently* unable to fork, so each attempt first waits for fork to come back
(`/bin/true` as probe) and only then starts the cluster.  A cluster whose shell
was killed by a burst is stopped before the next attempt, so one CI run never
stacks two PostgreSQL instances.
"""

import glob
import os
import shutil
import subprocess
import tempfile
import time

from conan import ConanFile
from conan.errors import ConanException
from conan.tools.env import VirtualRunEnv


class PgqdTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"
    generators = "VirtualRunEnv"
    test_type = "explicit"

    # Only these signatures count as "the worker could not fork".  Every other
    # failure (assertion output, missing binary, bad config) is raised at once.
    _eagain_markers = (
        "Resource temporarily unavailable",
        "can't fork",
        "cannot fork",
        "No record of process",
        "fork: retry",
    )
    _attempts = 8
    _backoff = 20
    # How long to wait for the worker to be able to fork again before giving up
    # on the flow.  The starvation arrives in bursts of seconds to minutes, and
    # waiting it out is far cheaper than burning attempts on it.
    _fork_wait = 600
    # The test script names its work dir "<prefix>$$", so the pid of the shell
    # that owns a cluster can be read back out of the directory name.
    _work_prefix = "pgqd-e2e-"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def build_requirements(self):
        # pgqd is useless without a PostgreSQL server to maintain; the test
        # brings up its own cluster from this package instead of assuming one.
        self.tool_requires("postgresql/16.10")

    def test(self):
        package_folder = self.dependencies["pgqd"].package_folder
        pg_bin = os.path.join(self.dependencies.build["postgresql"].package_folder, "bin")
        # OHOS /system/bin/sh (mksh) cannot drive ELF binaries; use bash.
        bash = os.environ.get("CONFIG_SHELL") or "/data/service/hnp/bin/bash"
        script = os.path.join(self.recipe_folder, "test_pgqd.sh")
        # R9: a runtime transcript belongs in $TMPDIR, not in the recipe tree —
        # anything left lying in archives/ can be picked up by the
        # `git add archives/` the workflow suggests and then trips the CI
        # junk-file gates.  The pid keeps concurrent jobs on one host apart.
        run_log = os.path.join(tempfile.gettempdir(), f"pgqd-test_package-{os.getpid()}.log")

        # Keep the dependency runtime (libpq/libevent lib dirs) in effect for the
        # script and for anything it spawns.
        with VirtualRunEnv(self).environment().vars(self).apply():
            for attempt in range(1, self._attempts + 1):
                self._await_fork(attempt)
                self._stop_stale_clusters(pg_bin)
                # Start from an empty transcript: when the fork itself never
                # happened, the redirect never ran either and the previous
                # attempt's log would still be sitting there.
                try:
                    os.unlink(run_log)
                except OSError:
                    pass
                try:
                    self.run(
                        f'"{bash}" "{script}" "{package_folder}" "{pg_bin}" '
                        f'>{run_log} 2>&1',
                        env="conanrun",
                    )
                except ConanException as exc:
                    transcript = self._read(run_log)
                    self.output.info(transcript)
                    # An empty transcript means the script never got to run at
                    # all — under fork starvation that is the same condition as
                    # an explicit EAGAIN message, so it is retried too.  Both
                    # cases surface the full transcript when attempts run out.
                    starved = (
                        not transcript.strip()
                        or any(m in transcript for m in self._eagain_markers)
                        or any(m in str(exc) for m in self._eagain_markers)
                    )
                    if not starved or attempt == self._attempts:
                        raise ConanException(
                            f"pgqd end-to-end test failed (attempt {attempt}/"
                            f"{self._attempts}); transcript kept at {run_log}\n"
                            f"{transcript[-4000:]}"
                        )
                    self.output.warning(
                        f"worker could not fork while running the e2e flow "
                        f"(attempt {attempt}/{self._attempts}); "
                        f"retrying in {self._backoff}s"
                    )
                    time.sleep(self._backoff)
                    continue

                self.output.info(self._read(run_log))
                return

        raise ConanException("pgqd end-to-end test kept failing with fork EAGAIN")

    def _await_fork(self, attempt):
        """Block until the worker can fork again.

        `/bin/true` is the cheapest possible fork probe: no arguments, no
        dependencies, none of the shell machinery — just the fork() that
        PostgreSQL needs several of in a row.  A fork denied by the worker
        raises OSError (EAGAIN) right here, which is the same condition that
        kills the shell script mid-flow.  A probe that cannot be found at all is
        a different problem, so the gate steps aside instead of spinning.
        """
        deadline = time.monotonic() + self._fork_wait
        announced = False
        while True:
            try:
                probe = subprocess.Popen(["/bin/true"], stdout=subprocess.DEVNULL,
                                         stderr=subprocess.DEVNULL)
            except FileNotFoundError:
                return
            except OSError:
                if time.monotonic() >= deadline:
                    raise ConanException(
                        f"worker still cannot fork after {self._fork_wait}s "
                        f"(probe before attempt {attempt}/{self._attempts})"
                    )
                if not announced:
                    self.output.warning(
                        f"worker cannot fork right now (before attempt "
                        f"{attempt}/{self._attempts}); waiting for it to recover"
                    )
                    announced = True
                time.sleep(self._backoff)
                continue
            probe.wait()
            return

    def _stop_stale_clusters(self, pg_bin):
        """Stop clusters whose owning shell is gone.

        The test script's EXIT trap stops its own cluster, but that trap has to
        fork as well: under starvation it fails silently and the postmaster — a
        daemon with half a dozen children of its own — survives, so every later
        attempt would start from a worse position.  Only clusters whose `$$` is
        no longer alive are touched, so a job running concurrently on the same
        host is never disturbed.
        """
        prefix = self._work_prefix
        root = os.environ.get("TMPDIR") or os.path.join(os.path.expanduser("~"), "tmp")
        pg_ctl = os.path.join(pg_bin, "pg_ctl")
        for work in glob.glob(os.path.join(root, prefix + "*")):
            owner = os.path.basename(work)[len(prefix):]
            if not owner.isdigit() or self._alive(int(owner)):
                continue
            data = os.path.join(work, "pgdata")
            if os.path.isdir(data):
                self._quiet([pg_ctl, "-D", data, "-m", "immediate", "stop"])
            shutil.rmtree(work, ignore_errors=True)

    @staticmethod
    def _alive(pid):
        try:
            os.kill(pid, 0)
        except OSError:
            return False
        return True

    @staticmethod
    def _quiet(argv):
        """Best-effort helper: no output, no error, never blocks for long."""
        try:
            proc = subprocess.Popen(argv, stdout=subprocess.DEVNULL,
                                    stderr=subprocess.DEVNULL)
        except OSError:
            return
        try:
            proc.wait(timeout=60)
        except subprocess.TimeoutExpired:
            proc.kill()

    @staticmethod
    def _read(path):
        try:
            with open(path, "r", encoding="utf-8", errors="replace") as handle:
                return handle.read()
        except OSError:
            return ""
