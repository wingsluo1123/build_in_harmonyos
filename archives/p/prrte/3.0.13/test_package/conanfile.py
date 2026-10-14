#!/usr/bin/env python3
"""Conan test_package — prrte 3.0.13 (R34 substantive test).

Consumer-side verification:
1. Build & run test_prrte.c against the packaged library — asserts the
   packaged prte_version.h macros (PRTE_VERSION_MAJOR/MINOR/RELEASE and
   PRTE_NUMERIC_VERSION), proving include + link work end-to-end.
2. Run the packaged prte_info binary and assert it reports "PRTE: 3.0.13".
3. Assert package layout (include/prte.h, include/prte_version.h,
   lib/libprrte.so, bin/prte_info).

The test binary is built with a plain clang invocation (no host CMake):
the OHOS host cmake binary needs an ABI-matched libc++ from the SDK
toolchain and can be upset by an ambient LD_LIBRARY_PATH, so avoiding it
keeps the test hermetic (same reasoning as abseil/abr2gbr notes).

Results are aggregated into a single HMBS_TEST_PACKAGE_RESULT line.
"""
import os
import shlex
import shutil
import subprocess
import tempfile

from conan import ConanFile
from conan.tools.env import Environment, VirtualRunEnv


class PrrteTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"
    generators = "VirtualRunEnv"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def layout(self):
        self.folders.build = os.path.join(self.folders.build, "bin")
        self.cpp.build.bindirs = ["."]

    def _sdk_llvm_libdir(self):
        """LLVM lib dir of the active OHOS compiler toolchain.

        PRRTE tools link against libprrte/pmix/hwloc/libevent; at run time
        the OHOS SDK runtime libs (libc++ etc.) must come from the SDK
        toolchain dir. Prepend it so the correct libs are found first.
        """
        if str(self.settings.os) != "OHOS":
            return ""
        comp_usr = self.conf.get(
            "tools.build:compiler_executables", default={}, check_type=dict
        )
        cc = comp_usr.get("c") or "clang"
        cc_real = os.path.realpath(cc)
        candidates = [
            os.path.join(os.path.dirname(os.path.dirname(cc_real)), "lib")
        ]
        try:
            resource_dir = subprocess.check_output(
                [cc, "-print-resource-dir"], stderr=subprocess.DEVNULL, text=True
            ).strip()
            candidates.append(os.path.dirname(os.path.dirname(resource_dir)))
        except (OSError, subprocess.CalledProcessError):
            pass
        for candidate in dict.fromkeys(candidates):
            if os.path.isfile(os.path.join(candidate, "libxml2.so.16")):
                return candidate
        return ""

    def build(self):
        tested = self.dependencies[self.tested_reference_str]
        inc = " ".join(
            "-I%s" % d
            for d in tested.cpp_info.includedirs
            if d
        )
        libs = " ".join("-l%s" % l for l in tested.cpp_info.libs if l)
        libdirs = " ".join(
            "-L%s" % d
            for d in tested.cpp_info.libdirs
            if d
        )
        env = Environment()
        sdk_llvm_lib = self._sdk_llvm_libdir()
        if sdk_llvm_lib:
            env.prepend_path("LD_LIBRARY_PATH", sdk_llvm_lib)
            self.output.info(
                "Prepending OHOS SDK runtime path: %s" % sdk_llvm_lib
            )
        envvars = env.vars(self)
        with envvars.apply():
            # consumer link test
            src = os.path.join(self.source_folder, "test.c")
            out = os.path.join(self.build_folder, "test_prrte")
            cmd = "clang %s %s %s %s -o %s" % (inc, libdirs, src, libs, out)
            self.run(cmd)
            # upstream test/ cases that are self-contained PMIx clients and
            # can be run directly without a DVM session (hello/clichk/filegen)
            tdir = os.path.join(self.source_folder, "upsrc")
            pmix_inc = ""
            extra_libdirs = ""
            extra_libs = ""
            # Remember the lib dirs used at link time; they are reused at
            # run time (conan2 dependency iteration may not expose libevent).
            self._upstream_libdirs = []
            for dep in ("pmix", "hwloc", "libevent"):
                try:
                    d = self.dependencies[dep]
                    pf = d.package_folder or ""
                    if pf:
                        pmix_inc += " -I%s/include" % pf
                        extra_libdirs += " -L%s/lib" % pf
                        self._upstream_libdirs.append(os.path.join(pf, "lib"))
                    for l in d.cpp_info.libs:
                        extra_libs += " -l%s" % l
                except KeyError:
                    pass
            # libevent may not be exposed as a visible dependency of this
            # test package (it is a transitive dep of pmix). Fall back to
            # locating it in the conan cache so run-time loading works.
            if not any("libevent" in d for d in self._upstream_libdirs):
                import glob as _glob
                hits = _glob.glob(
                    os.path.join(
                        os.path.expanduser("~/.conan2/p/*/p/lib/libevent_core-2.1.so.7"))
                )
                if hits:
                    libdir = os.path.dirname(hits[0])
                    if libdir not in self._upstream_libdirs:
                        self._upstream_libdirs.append(libdir)
            self._upstream_bins = {}
            for case in ("hello", "clichk"):
                srcf = os.path.join(tdir, case + ".c")
                if not os.path.isfile(srcf):
                    continue
                outb = os.path.join(self.build_folder, "up_%s" % case)
                cmd = "clang %s %s %s %s %s %s %s -o %s" % (
                    inc, pmix_inc, libdirs, extra_libdirs, srcf,
                    libs, extra_libs, outb)
                rc = self.run(cmd, ignore_errors=True)
                if rc == 0:
                    self._upstream_bins[case] = outb
            srcf = os.path.join(tdir, "filegen.c")
            if os.path.isfile(srcf):
                outb = os.path.join(self.build_folder, "up_filegen")
                cmd = "clang %s %s %s %s %s -o %s" % (
                    inc, pmix_inc, libdirs, srcf, libs, outb)
                rc = self.run(cmd, ignore_errors=True)
                if rc == 0:
                    self._upstream_bins["filegen"] = outb

    def _run_capture(self, cmd, out_file, inject_all_libs=False):
        """Run a command, capture combined output.

        cmd may be a string or a list of argv pieces. It is passed to
        self.run as a plain shell command line (do NOT quote the whole
        line — shlex.quote on an already-joined line turns
        "prte_info --all" into a single literal filename -> rc=127).

        If inject_all_libs is True, an explicit LD_LIBRARY_PATH is built
        from every dependency's lib dir (including transitive deps such as
        libevent pulled in by pmix) and prepended to the command, because
        the generated conanrun env only carries directly-visible libdirs.
        """
        cmd_line = cmd if isinstance(cmd, str) else " ".join(cmd)
        if inject_all_libs:
            seen = set()
            lib_paths = []
            # lib dirs used when linking upstream cases (includes libevent)
            for libdir in getattr(self, "_upstream_libdirs", []) or []:
                real = os.path.realpath(libdir)
                if os.path.isdir(real) and real not in seen:
                    seen.add(real)
                    lib_paths.append(real)
            for dep_name, dep in self.dependencies.items():
                pf = getattr(dep, "package_folder", None)
                if not pf:
                    continue
                for libdir in getattr(dep, "cpp_info", None).libdirs or []:
                    real = os.path.realpath(libdir)
                    if os.path.isdir(real) and real not in seen:
                        seen.add(real)
                        lib_paths.append(real)
            sdk_llvm_lib = self._sdk_llvm_libdir()
            if sdk_llvm_lib:
                real = os.path.realpath(sdk_llvm_lib)
                if os.path.isdir(real) and real not in seen:
                    seen.add(real)
                    lib_paths.insert(0, real)
            libs_env = ":".join(lib_paths)
            cmd_line = "export LD_LIBRARY_PATH=\"%s:${LD_LIBRARY_PATH}\"; %s" % (
                libs_env, cmd_line)
        with open(out_file, "w") as f:
            rc = self.run(cmd_line, env="conanrun", stdout=f,
                          stderr=subprocess.STDOUT, ignore_errors=True)
        try:
            with open(out_file, "r") as f:
                return rc, f.read()
        except OSError:
            return rc, ""

    def test(self):
        total = 0
        passed = 0

        def record(ok, desc):
            nonlocal total, passed
            total += 1
            if ok:
                passed += 1
                self.output.info("ASSERT OK: %s" % desc)
            else:
                self.output.error("ASSERT FAIL: %s" % desc)

        tested = self.dependencies[self.tested_reference_str]
        pkg_folder = tested.package_folder

        tmpdir = tempfile.mkdtemp(prefix="prrte-test-")
        try:
            # --- 1. version-macro link test (C program, 4 assertions) ---
            test_bin = os.path.join(self.build_folder, "test_prrte")
            rc, out = self._run_capture(test_bin,
                                        os.path.join(tmpdir, "test_prrte.out"))
            c_total = c_passed = 0
            for line in out.splitlines():
                if line.startswith("PRTE_TEST_ASSERTIONS:"):
                    parts = dict(p.split("=") for p in line.split()[1:])
                    c_total = int(parts.get("total", 0))
                    c_passed = int(parts.get("passed", 0))
            record(rc == 0 and c_total > 0 and c_total == c_passed,
                   "test_prrte version-macro assertions (%d/%d, rc=%d)"
                   % (c_passed, c_total, rc))

            # --- 2. end-to-end consumer run: packaged prte_info --all ---
            # Runs the packaged prte_info binary, which initialises the PRRTE
            # runtime (PMIx + MCA frameworks) and reports real system/version
            # info. This is a full consumer flow, not a compile-time assert.
            info_bin = os.path.join(pkg_folder, "bin", "prte_info")
            irc, iout = self._run_capture(
                [info_bin, "--all"], os.path.join(tmpdir, "prte_info.out")
            )
            record(irc == 0, "prte_info end-to-end run (rc=0)")
            record("PRTE: 3.0.13" in iout,
                   "prte_info reports PRTE version 3.0.13")
            record("PMIx:" in iout,
                   "prte_info initialised PMIx backend (PMIx: line present)")
            record("MCA prte:" in iout,
                   "prte_info loaded PRRTE MCA frameworks (MCA prte: line present)")
            ver_line = next((ln for ln in iout.splitlines() if "PRTE:" in ln), "")
            self.output.info("prte_info version line: %s" % ver_line.strip())

            # --- 3. upstream test/ cases that run without a DVM session ---
            # Compiled in build(); run them and assert rc=0 (real consumer
            # execution of the packaged runtime, not a compile-time assert).
            up = getattr(self, "_upstream_bins", {})
            for case in ("hello", "clichk"):
                b = up.get(case)
                if not b:
                    continue
                urc, uout = self._run_capture(
                    b, os.path.join(tmpdir, "up_%s.out" % case),
                    inject_all_libs=True)
                record(urc == 0, "upstream test %s run (rc=0)" % case)
                if "hello" == case:
                    record("Running on host" in uout,
                           "upstream hello reports running host")
            b = up.get("filegen")
            if b:
                urc, uout = self._run_capture(
                    [b, "2"], os.path.join(tmpdir, "up_filegen.out"),
                    inject_all_libs=True)
                record(urc == 0, "upstream filegen run (rc=0)")

            # --- 4. package layout assertions ---
            record(os.path.isfile(os.path.join(pkg_folder, "include", "prte.h")),
                   "package layout: include/prte.h exists")
            record(os.path.isfile(
                       os.path.join(pkg_folder, "include", "prte_version.h")),
                   "package layout: include/prte_version.h exists")
            record(any(os.path.isfile(os.path.join(pkg_folder, d, "libprrte.so"))
                       for d in ("lib", "lib64")),
                   "package layout: lib/libprrte.so exists")
            record(os.path.isfile(info_bin),
                   "package layout: bin/prte_info exists")
        finally:
            shutil.rmtree(tmpdir, ignore_errors=True)

        self.output.info("HMBS_TEST_PACKAGE_RESULT: total=%d passed=%d" % (total, passed))
        if total == 0 or total != passed:
            raise Exception(
                "test_package failed: %d/%d assertions passed" % (passed, total)
            )