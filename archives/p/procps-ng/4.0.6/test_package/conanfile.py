#!/usr/bin/env python3
"""Conan test_package for procps-ng 4.0.6 — consumer tests on the OHOS PC host.

Two layers, both consuming the package the way it is really used:

  1. C consumer (CMake + CMakeDeps): links libproc2 through the exported target
     and cross-checks load average, uptime, the utmp user count and a full pids
     walk against /proc — see src/test_libproc2.c.

  2. Command line tools: the installed binaries are executed and their output
     asserted — free, uptime, ps, vmstat, top -b, w, sysctl, pidof and the
     pgrep/pkill pair checked against a sleeper this test spawns.
"""
import os
import subprocess
import time

from conan import ConanFile
from conan.tools.cmake import CMake, CMakeToolchain, cmake_layout


class ProcpsNgTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"
    generators = "CMakeDeps", "VirtualRunEnv"
    test_type = "explicit"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def generate(self):
        toolchain = CMakeToolchain(self)
        toolchain.generate()

    def layout(self):
        cmake_layout(self)

    def build(self):
        cmake = CMake(self)
        cmake.configure()
        cmake.build()

    # ------------------------------------------------------------------
    # helpers
    # ------------------------------------------------------------------
    def _env(self):
        env = os.environ.copy()
        pkg = self.dependencies["procps-ng"].package_folder
        libdir = os.path.join(pkg, "lib")
        old = env.get("LD_LIBRARY_PATH", "")
        env["LD_LIBRARY_PATH"] = libdir + (os.pathsep + old if old else "")
        # top and watch look their terminal description up at run time, and
        # HarmonyOS PC ships no terminfo database at all, so point them at the
        # copy the ncurses build they link against carries.  Without it
        # setupterm("dumb") makes even `top -b` leave with a non zero status.
        for dep in self.dependencies.values():
            if dep.ref.name != "ncurses" or not dep.package_folder:
                continue
            for sub in ("share/terminfo", "lib/terminfo"):
                candidate = os.path.join(dep.package_folder, sub)
                if os.path.isdir(candidate):
                    env.setdefault("TERMINFO", candidate)
                    env.setdefault("TERMINFO_DIRS", candidate)
        return env

    def _run(self, argv, timeout=120):
        return subprocess.run(argv, capture_output=True, text=True,
                              timeout=timeout, env=self._env())

    def _tool(self, name):
        pkg = self.dependencies["procps-ng"].package_folder
        for sub in ("bin", "sbin"):
            path = os.path.join(pkg, sub, name)
            if os.path.isfile(path):
                return path
        raise Exception(f"{name} was not installed by the package")

    @staticmethod
    def _text(res):
        return (res.stdout or "") + (res.stderr or "")

    # ------------------------------------------------------------------
    def test(self):
        # ---- C consumer: libproc2 through the exported CMake target ----
        # build() only links this binary and the test package has no ctest
        # driver, so run it here: its assertions against /proc are the point of
        # the C layer, and a wrong value has to fail the test package.
        binary = os.path.join(self.build_folder, "test_libproc2")
        res = self._run([binary], timeout=600)
        assert res.returncode == 0, \
            f"libproc2 C consumer test failed (rc={res.returncode}): {self._text(res)}"
        self.output.info(self._text(res).strip())

        # ---- smoke pass through the aggregated run environment ---------
        # conan applies the whole dependency graph's run environment here
        # (library search path plus the ncurses terminfo database that top and
        # w resolve at run time), so a binary that cannot start aborts the
        # test package right here instead of being masked by the hand built
        # environment the detailed checks below use.
        for argv in (["free", "-h"], ["uptime"], ["vmstat"],
                     ["top", "-b", "-n", "1"], ["w"],
                     ["sysctl", "-n", "kernel.pid_max"]):
            self.run('"{}" {}'.format(self._tool(argv[0]), " ".join(argv[1:])),
                     env="conanrun")

        # ---- free: /proc/meminfo --------------------------------------
        res = self._run([self._tool("free"), "-h"])
        text = self._text(res)
        assert res.returncode == 0, f"free -h failed (rc={res.returncode}): {text}"
        assert "total" in text, f"free -h printed no column header: {text}"
        assert "Mem:" in text, f"free -h printed no Mem: row: {text}"
        assert "Swap:" in text, f"free -h printed no Swap: row: {text}"

        # ---- uptime: /proc/uptime + load average ----------------------
        res = self._run([self._tool("uptime")])
        text = self._text(res)
        assert res.returncode == 0, f"uptime failed (rc={res.returncode}): {text}"
        assert "load average" in text, f"uptime printed no load average: {text}"

        # ---- ps: this very process must be the one it reports ---------
        res = self._run([self._tool("ps"), "-o", "pid=", "-p", str(os.getpid())])
        assert res.returncode == 0, f"ps failed (rc={res.returncode}): {self._text(res)}"
        assert res.stdout.strip() == str(os.getpid()), \
            f"ps -p {os.getpid()} reported {res.stdout!r}"

        # ---- vmstat ---------------------------------------------------
        res = self._run([self._tool("vmstat")])
        text = self._text(res)
        assert res.returncode == 0, f"vmstat failed (rc={res.returncode}): {text}"
        assert "procs" in text, f"vmstat printed no procs header: {text}"

        # ---- top in batch mode (the ncurses linked build) -------------
        res = self._run([self._tool("top"), "-b", "-n", "1"])
        text = self._text(res)
        assert res.returncode == 0, f"top -b -n 1 failed (rc={res.returncode}): {text}"
        assert "load average" in text, f"top -b printed no load average: {text}"
        assert "PID" in text, f"top -b printed no process table: {text}"

        # ---- w: the patched utmp/utmpx guard lives in this binary -----
        res = self._run([self._tool("w")])
        text = self._text(res)
        assert res.returncode == 0, f"w failed (rc={res.returncode}): {text}"
        assert text.strip(), "w printed nothing at all"

        # ---- sysctl: /proc/sys ----------------------------------------
        res = self._run([self._tool("sysctl"), "-n", "kernel.pid_max"])
        assert res.returncode == 0, \
            f"sysctl -n kernel.pid_max failed (rc={res.returncode}): {self._text(res)}"
        assert res.stdout.strip().isdigit(), \
            f"sysctl -n kernel.pid_max printed {res.stdout!r}"

        # ---- pgrep / pidof / pkill against a process we spawn ---------
        # The victim is the packaged vmstat on a one second interval: a long
        # running process of this very package that needs no controlling
        # terminal, unlike the device's own sleep applet, which no launcher
        # PATH of this platform resolves to an executable.
        argv = [self._tool("vmstat"), "1"]
        marker = " ".join(argv)
        sleeper = subprocess.Popen(argv, stdout=subprocess.DEVNULL,
                                   stderr=subprocess.DEVNULL, env=self._env())
        try:
            time.sleep(1.0)

            res = self._run([self._tool("pgrep"), "-f", marker])
            assert res.returncode == 0, \
                f"pgrep -f '{marker}' failed (rc={res.returncode}): {self._text(res)}"
            assert str(sleeper.pid) in res.stdout.split(), \
                f"pgrep -f '{marker}' did not report {sleeper.pid}: {res.stdout!r}"

            res = self._run([self._tool("pidof"), os.path.basename(argv[0])])
            assert res.returncode == 0, \
                f"pidof {os.path.basename(argv[0])} failed (rc={res.returncode}): {self._text(res)}"
            assert str(sleeper.pid) in res.stdout.split(), \
                f"pidof {os.path.basename(argv[0])} did not report {sleeper.pid}: {res.stdout!r}"

            res = self._run([self._tool("pkill"), "-f", marker])
            assert res.returncode == 0, \
                f"pkill -f '{marker}' failed (rc={res.returncode}): {self._text(res)}"
            sleeper.wait(timeout=30)
            assert sleeper.returncode == -15, \
                f"the sleeper was not terminated by pkill (rc={sleeper.returncode})"

            res = self._run([self._tool("pgrep"), "-f", marker])
            assert str(sleeper.pid) not in res.stdout.split(), \
                f"pgrep still reports the pkill'ed process: {res.stdout!r}"
        finally:
            if sleeper.poll() is None:
                sleeper.kill()
                sleeper.wait(timeout=30)

        print("procps-ng: libproc2 consumer test + 10 command line checks passed")
