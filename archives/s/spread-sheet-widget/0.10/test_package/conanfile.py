#!/usr/bin/env python3
"""Conan test_package for spread-sheet-widget 0.10.

The consumer program is built with pkg-config
(`pkg_check_modules(... spread-sheet-widget)`) so the installed headers, the
libtool shared library and the upstream `Requires: gtk+-3.0 >= 3.18.0
glib-2.0 >= 2.44` chain are exercised exactly the way a downstream project on
OHOS would consume the package.

test() runs the binary for real. It is a GTK program (gtk_init_check), so it
runs on the headless **broadway** GDK backend served by broadwayd from the
gtk package (same technique as gspell/1.14.4 and gtksourceview3/3.24.11).
The per-check TEST PASS/TEST FAIL lines, the TEST SUMMARY line and the exit
code are parsed, so "the test passed" means "N checks executed and all of
them held", not "the process exited 0 without doing anything".
"""
import glob
import os
import re
import subprocess
import time

from conan import ConanFile
from conan.tools.cmake import CMake, cmake_layout
from conan.tools.env import Environment

# GTK3 broadway clients ignore DISPLAY; the server is addressed through
# BROADWAY_DISPLAY. ":tcpN" avoids the HMDFS AF_UNIX socket issue:
# broadwayd listens on TCP 9090 + N (see gtksourceview3/3.24.11 notes).
BROADWAY_DISPLAY = ":tcp66"


class SpreadSheetWidgetTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"
    generators = "CMakeToolchain", "PkgConfigDeps"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def layout(self):
        cmake_layout(self)

    def _sdk_llvm_libdir(self):
        """Locate the active OHOS SDK llvm/lib that ships libc++_shared.so.

        GTK's harfbuzz has DT_NEEDED libc++_shared.so; the CI shell prepends
        ~/usr/local/lib which shadows the ABI-matching copy, so the directory
        is probed and put on LD_LIBRARY_PATH (gspell/gtksourceview3 同款).
        """
        if str(self.settings.os) != "OHOS":
            return ""
        compilers = self.conf.get(
            "tools.build:compiler_executables", default={}, check_type=dict)
        cxx = compilers.get("cpp") or compilers.get("c")
        candidates = []
        if cxx:
            try:
                resource_dir = subprocess.check_output(
                    [cxx, "-print-resource-dir"],
                    stderr=subprocess.DEVNULL, text=True).strip()
                candidates.append(os.path.dirname(os.path.dirname(resource_dir)))
            except (OSError, subprocess.CalledProcessError):
                pass
            compiler = os.path.realpath(cxx)
            candidates.append(
                os.path.join(os.path.dirname(os.path.dirname(compiler)), "lib"))
        expanded = []
        for cand in dict.fromkeys(candidates):
            expanded.append(cand)
            sub = os.path.join(cand, "aarch64-linux-ohos")
            if os.path.isdir(sub):
                expanded.append(sub)
        for cand in dict.fromkeys(expanded):
            if os.path.isfile(os.path.join(cand, "libc++_shared.so")):
                return cand
        return ""

    def _resolved_lib_dirs(self):
        dirs = []
        for dependency in self.dependencies.values():
            if not getattr(dependency, "package_folder", None):
                continue
            for libdir in dependency.cpp_info.libdirs or []:
                if not libdir:
                    continue
                full = libdir if os.path.isabs(libdir) else os.path.join(
                    dependency.package_folder, libdir)
                if full not in dirs:
                    dirs.append(full)
        if os.path.isdir("/system/lib64") and "/system/lib64" not in dirs:
            dirs.append("/system/lib64")
        # OHOS HNP layout: transitive runtime libs (pcre2/ffi/expat/intl/
        # epoxy) live under /data/service/hnp/*/*/lib.
        for pattern in ("libpcre2-8.so*", "libffi.so*", "libexpat.so*",
                        "libintl.so*", "libepoxy.so*"):
            for match in glob.glob("/data/service/hnp/*/*/lib/{}".format(pattern)):
                libdir = os.path.dirname(match)
                if libdir not in dirs:
                    dirs.append(libdir)
        return dirs

    def _env(self):
        env = Environment()
        sdk_llvm_lib = self._sdk_llvm_libdir()
        if sdk_llvm_lib:
            self.output.info(
                "Prepending OHOS SDK runtime path: {}".format(sdk_llvm_lib))
            env.prepend_path("LD_LIBRARY_PATH", sdk_llvm_lib)
        env.prepend_path("PKG_CONFIG_PATH", self.generators_folder)
        for dependency in self.dependencies.values():
            if not getattr(dependency, "package_folder", None):
                continue
            for libdir in dependency.cpp_info.libdirs or []:
                if not libdir:
                    continue
                full = libdir if os.path.isabs(libdir) else os.path.join(
                    dependency.package_folder, libdir)
                env.prepend_path("LD_LIBRARY_PATH", full)
                env.prepend_path(
                    "PKG_CONFIG_PATH", os.path.join(full, "pkgconfig"))
        for libdir in self._resolved_lib_dirs():
            env.prepend_path("LD_LIBRARY_PATH", libdir)
        return env

    def _broadway_env(self):
        """Start broadwayd; return (env, process)."""
        env = self._env()
        proc = None
        gtk_pkg = self.dependencies.get("gtk")
        if gtk_pkg is not None and gtk_pkg.package_folder:
            broadwayd = os.path.join(gtk_pkg.package_folder, "bin", "broadwayd")
            if os.path.isfile(broadwayd):
                libdirs = self._resolved_lib_dirs()
                run_env = dict(os.environ)
                sdk_llvm_lib = self._sdk_llvm_libdir()
                parts = ([sdk_llvm_lib] if sdk_llvm_lib else []) + libdirs
                if parts:
                    run_env["LD_LIBRARY_PATH"] = ":".join(
                        parts + [run_env.get("LD_LIBRARY_PATH", "")]
                    ).strip(":")
                proc = subprocess.Popen([broadwayd, BROADWAY_DISPLAY],
                                        env=run_env,
                                        stdout=subprocess.DEVNULL,
                                        stderr=subprocess.DEVNULL)
                for _ in range(20):
                    if proc.poll() is not None:
                        break
                    time.sleep(0.5)
                if proc.poll() is None:
                    env.define("GDK_BACKEND", "broadway")
                    env.define("BROADWAY_DISPLAY", BROADWAY_DISPLAY)
                else:
                    self.output.warning(
                        "broadwayd exited early (rc=%s); running the consumer "
                        "test without a display backend" % proc.returncode)
                    proc = None
        return env, proc

    def build(self):
        envvars = self._env().vars(self)
        with envvars.apply():
            cmake = CMake(self)
            cmake.configure()
            cmake.build()

    def test(self):
        bindirs = self.cpp.build.bindirs
        if not bindirs:
            raise RuntimeError(
                "test_spread_sheet_widget executable directory was not produced")
        exe = os.path.join(bindirs[0], "test_spread_sheet_widget")
        if not os.path.isfile(exe):
            raise RuntimeError(
                "test_spread_sheet_widget binary missing: {}".format(exe))

        required = (
            "libspread-sheet-widget.so",
            "libgtk-3.so.0",
            "libgdk-3.so.0",
            "libglib-2.0.so.0",
        )
        lib_dirs = self._resolved_lib_dirs()
        missing = [lib for lib in required
                   if not any(os.path.isfile(os.path.join(d, lib))
                              for d in lib_dirs if d)]
        if missing:
            raise RuntimeError(
                "spread-sheet-widget runtime libs missing from the dependency "
                "graph; the consumer checks would not execute: {}".format(
                    missing))

        env, broadwayd_proc = self._broadway_env()
        log = os.path.join(self.build_folder, "test_spread_sheet_widget.log")
        run_error = None
        try:
            envvars = env.vars(self)
            with envvars.apply():
                self.run('"{}" > "{}" 2>&1'.format(exe, log), env="conanrun")
        except Exception as exc:      # re-raised below, after the log is shown
            run_error = exc
        finally:
            if broadwayd_proc is not None and broadwayd_proc.poll() is None:
                broadwayd_proc.terminate()

        try:
            with open(log, encoding="utf-8", errors="replace") as f:
                out = f.read()
        except OSError:
            out = ""
        self.output.info(
            "----- test_spread_sheet_widget log -----\n{}".format(out))

        passes = len(re.findall(r"^TEST PASS: ", out, re.M))
        fails = len(re.findall(r"^TEST FAIL: ", out, re.M))
        summary = re.search(
            r"^TEST SUMMARY: (\d+) passed, (\d+) failed\s*$", out, re.M)
        summary_passed = int(summary.group(1)) if summary else -1
        summary_failed = int(summary.group(2)) if summary else -1
        if (run_error is not None or summary is None or passes < 1
                or fails != 0 or summary_failed != 0
                or summary_passed != passes):
            raise RuntimeError(
                "consumer checks did not all pass ({}): TEST PASS={} "
                "TEST FAIL={} summary_passed={} summary_failed={}\n{}".format(
                    run_error, passes, fails, summary_passed,
                    summary_failed, out))
        self.output.info(
            "HMBS_TEST_PACKAGE_RESULT={{\"status\": \"passed\", "
            "\"assertions\": {}}}".format(passes))
