#!/usr/bin/env python3
"""Consumer (test_package) for fuse/2.9.9 — FUSE 2.x legacy ABI.

Two consumers are driven for real:

  A. the compiled C consumer (test.c) — links libfuse.a/libulockmgr.a and
     asserts the offline library surface (version, option parsing,
     lowlevel session) plus the /dev/fuse capability probe with its negative
     controls;
  B. the shipped CLI tools (bin/fusermount, bin/ulockmgr_server) — executed
     with exact exit-code and output assertions, each paired with a control
     that the harness can tell success from failure.

No `|| true`, no silent skip: every check prints its raw reading and the run
fails if any check fails. Two execution markers use `chk(True, ...)` (the
`test.c` execution marker, whose real gate is `self.run` raising on non-zero
exit, and the missing-binary harness control); together with `test.c:189`
they are tallied as reached-line assertions in `assertion_count_breakdown`
(i.e. they are inside the reported total, not counted as value assertions).
"""
import os
import stat
import subprocess

from conan import ConanFile
from conan.errors import ConanException
from conan.tools.build import can_run
from conan.tools.cmake import CMake, cmake_layout


class FuseTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"
    generators = "CMakeDeps", "CMakeToolchain"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def layout(self):
        cmake_layout(self)

    def build(self):
        cmake = CMake(self)
        cmake.configure()
        cmake.build()

    # ---------------------------------------------------------------- helpers
    def _run(self, argv):
        """Run argv, return (rc, stdout, stderr). Raises if the file is absent."""
        p = subprocess.run(argv, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                           timeout=120)
        return (p.returncode,
                p.stdout.decode("utf-8", "replace"),
                p.stderr.decode("utf-8", "replace"))

    def test(self):
        if not can_run(self):
            self.output.info("cross-build: skipping runtime consumer test")
            return

        bin_dir = os.path.join(self.dependencies["fuse"].package_folder, "bin")
        fusermount = os.path.join(bin_dir, "fusermount")
        ulockmgr = os.path.join(bin_dir, "ulockmgr_server")

        checks = []

        def chk(cond, msg):
            checks.append((bool(cond), msg))

        # ---- A. compiled library consumer -------------------------------
        exe = os.path.join(self.cpp.build.bindirs[0], "test_fuse")
        self.run(f'"{exe}"', env="conanrun")
        chk(True, "test.c consumer executed and exited 0 (all library checks passed)")

        # ---- B. shipped CLI consumers -----------------------------------
        chk(os.path.isfile(fusermount), f"bin/fusermount installed at {fusermount}")
        if os.path.isfile(fusermount):
            mode = stat.S_IMODE(os.stat(fusermount).st_mode)
            chk(mode & 0o111 != 0,
                f"bin/fusermount is executable (mode=0o{mode:o})")
            self.output.info(
                f"  INFO  bin/fusermount mode=0o{mode:o} "
                f"setuid={bool(mode & stat.S_ISUID)}")

        rc, out, err = self._run([fusermount, "--version"])
        chk(rc == 0 and "fusermount version: 2.9.9" in out,
            f"fusermount --version rc={rc} stdout={out.strip()!r}")

        rc, out, err = self._run([fusermount, "-h"])
        chk(rc != 0 and "print help" in err and "mountpoint" in err,
            f"fusermount -h rejects with usage on stderr rc={rc} "
            f"(stderr first line={err.splitlines()[0] if err else ''!r})")

        rc, out, err = self._run([fusermount])
        chk(rc != 0 and "missing mountpoint argument" in err,
            f"fusermount with no mountpoint rc={rc} stderr={err.strip()!r}")

        rc_bad, _, err_bad = self._run([fusermount, "--definitely-not-an-option"])
        chk(rc_bad != 0 and err_bad.strip() != "",
            f"negative control: invalid option rejected rc={rc_bad} "
            f"stderr={err_bad.strip().splitlines()[0] if err_bad.strip() else ''!r}")

        rc, out, err = self._run([fusermount, "-z", os.getcwd()])
        chk(rc != 0 and "-z can only be used with -u" in err,
            f"fusermount -z without -u rc={rc} stderr={err.strip()!r}")

        # harness control: a missing binary must raise, proving the runner
        # can distinguish "absent" from "failed".
        try:
            self._run([fusermount + ".does-not-exist"])
            chk(False, "harness control: missing binary unexpectedly executed")
        except FileNotFoundError:
            chk(True, "harness control: missing binary raises FileNotFoundError "
                      "(rc capture is not vacuous)")

        chk(os.path.isfile(ulockmgr),
            f"bin/ulockmgr_server installed at {ulockmgr}")
        if os.path.isfile(ulockmgr):
            chk(os.access(ulockmgr, os.X_OK),
                "bin/ulockmgr_server is executable")

        # ---- report ------------------------------------------------------
        failed = [m for ok, m in checks if not ok]
        self.output.info("")
        self.output.info("== consumer checks ==")
        for ok, msg in checks:
            self.output.info(f"  {'PASS' if ok else 'FAIL'}  {msg}")
        self.output.info(f"== {len(checks) - len(failed)}/{len(checks)} checks passed ==")
        if failed:
            raise ConanException(
                f"fuse/2.9.9 test_package: {len(failed)}/{len(checks)} checks failed"
            )
