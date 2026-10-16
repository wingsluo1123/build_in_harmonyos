#!/usr/bin/env python3
"""Installed-package consumer test for libsigrokcxx/0.5.2 (OHOS PC).

Upstream registers no test suite for bindings/cxx: that directory contains no
Makefile.am and no test source (only classes.cpp / the *_methods.* helpers and
the doxygen input). libsigrok's own tests/ Check suite belongs to the C library
and is counted under libsigrok/0.5.2, not here.

What this test_package verifies, mirroring the libsigrok/0.5.2 consumer pattern:

  * consumer.cpp is compiled and linked with the OHOS clang++ against the
    installed headers of libsigrokcxx + libsigrok + glibmm/giomm + glib + libsigc
    (compile/link feasibility of the C++ bindings).
  * The produced ELF is signed with binary-sign-tool and the .codesign section is
    verified, because an unsigned ELF is rejected by the OHOS loader.
  * The probe is executed on the target (can_run) via the conanrun environment.

OHOS-specific checks (rule12):
  * non-assertion check reported by the probe itself: shared-library closure
    load — dlopen("libsigrokcxx.so.0", RTLD_NOW) forces the OHOS loader to
    resolve the whole DT_NEEDED closure of the shipped library; the load result
    is observed and printed, no value is asserted.
  * observational artifact check: .codesign presence on the shipped
    libsigrokcxx.so.0.5.2 (see _check_shipped_signature).
"""

import os
import shutil
import subprocess

from conan import ConanFile
from conan.errors import ConanException, ConanInvalidConfiguration
from conan.tools.build import can_run
from conan.tools.env import VirtualRunEnv
from conan.tools.layout import basic_layout


class LibsigrokcxxTestConan(ConanFile):
    settings = "os", "arch", "compiler", "build_type"
    test_type = "explicit"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def layout(self):
        # build/ is git-ignored (see .gitignore "test_package/build/"), so the
        # probe binary and the conan generators never pollute the repository.
        basic_layout(self, build_folder="build")

    def generate(self):
        VirtualRunEnv(self).generate()

    # ── toolchain / path discovery ──────────────────────────────────────

    def _cxx(self):
        ce = self.conf.get("tools.build:compiler_executables",
                           default={}, check_type=dict) or {}
        cxx = ce.get("cpp") or ce.get("c++") or ""
        if not cxx or not os.path.isfile(cxx):
            cxx = shutil.which("clang++") or shutil.which("g++") or "clang++"
        return cxx

    @staticmethod
    def _add(dirs, seen, path):
        if os.path.isdir(path) and path not in seen:
            seen.add(path)
            dirs.append(path)

    def _include_dirs(self):
        """Header roots of every dependency in the graph.

        Handles the two real layouts used by this stack:
          <pkg>/include/<component>       (glib-2.0, glibmm-2.4, giomm-2.4,
                                           sigc++-2.0, libsigrok)
          <pkg>/lib/<component>/include   (glibconfig.h, glibmmconfig.h,
                                           sigc++config.h)
        """
        dirs, seen = [], set()
        for dep in self.dependencies.values():
            pkg = dep.package_folder
            if not pkg:
                continue
            inc = os.path.join(pkg, "include")
            self._add(dirs, seen, inc)
            if os.path.isdir(inc):
                for sub in sorted(os.listdir(inc)):
                    self._add(dirs, seen, os.path.join(inc, sub))
            libdir = os.path.join(pkg, "lib")
            if os.path.isdir(libdir):
                for comp in sorted(os.listdir(libdir)):
                    self._add(dirs, seen,
                              os.path.join(libdir, comp, "include"))
        return dirs

    def _lib_dirs(self):
        dirs, seen = [], set()
        for dep in self.dependencies.values():
            pkg = dep.package_folder
            if not pkg:
                continue
            self._add(dirs, seen, os.path.join(pkg, "lib"))
        return dirs

    def _libsigrokcxx_lib_dir(self):
        dep = self.dependencies.get("libsigrokcxx")
        if not (dep and dep.package_folder):
            raise ConanException("libsigrokcxx package folder unavailable")
        return os.path.join(dep.package_folder, "lib")

    # ── OHOS signing ────────────────────────────────────────────────────

    def _sign(self, path):
        signer = shutil.which("binary-sign-tool")
        readelf = shutil.which("llvm-readelf") or shutil.which("readelf")
        if not signer or not readelf:
            raise ConanInvalidConfiguration("OHOS ELF signer/readelf missing")
        subprocess.run([signer, "sign", "-inFile", path, "-outFile",
                        path + ".signed", "-selfSign", "1"],
                       check=True, capture_output=True, text=True, timeout=40)
        sections = subprocess.run([readelf, "-S", path + ".signed"],
                                  check=True, capture_output=True, text=True,
                                  timeout=20)
        if ".codesign" not in sections.stdout:
            raise ConanException("signed consumer has no .codesign")
        os.chmod(path + ".signed", os.stat(path).st_mode)
        os.replace(path + ".signed", path)

    def _check_shipped_signature(self):
        """OHOS-specific observational check: the shipped library is signed.

        Reads the section table of the real shipped ELF and reports the
        signature section found there. No specific value is asserted; a real
        OHOS consumer cannot load an unsigned library, so a missing section is
        an error rather than a silently skipped check.
        """
        readelf = shutil.which("llvm-readelf") or shutil.which("readelf")
        if not readelf:
            raise ConanInvalidConfiguration("OHOS readelf missing")
        shipped = os.path.join(self._libsigrokcxx_lib_dir(),
                               "libsigrokcxx.so.0.5.2")
        if not os.path.isfile(shipped):
            raise ConanException(f"shipped library missing: {shipped}")
        sections = subprocess.run([readelf, "-S", shipped], check=True,
                                  capture_output=True, text=True, timeout=20)
        if ".codesign" not in sections.stdout:
            raise ConanException(
                f"OHOS .codesign section missing from {shipped}")
        self.output.info(
            f"✅ OHOS signature check: .codesign present in {shipped}")

    # ── build / run ─────────────────────────────────────────────────────

    def build(self):
        cxx = self._cxx()
        out = os.path.join(self.build_folder, "consumer")
        src = os.path.join(self.recipe_folder, "consumer.cpp")

        cmd = [cxx, "-std=c++11", "-fvisibility=hidden", "-O2"]
        for d in self._include_dirs():
            cmd.append("-I" + d)
        for d in self._lib_dirs():
            cmd.append("-L" + d)
        cmd.extend(["-o", out, src])
        cmd.append("-lsigrokcxx")
        cmd.append("-Wl,-rpath," + self._libsigrokcxx_lib_dir())

        result = subprocess.run(cmd, capture_output=True, text=True, timeout=120)
        if result.returncode:
            self.output.error("STDOUT: " + (result.stdout or ""))
            self.output.error("STDERR: " + (result.stderr or ""))
            raise ConanException(
                f"consumer build failed (rc={result.returncode})")
        self.output.info("consumer built successfully (compile + link OK)")

        if str(self.settings.os) == "OHOS":
            self._sign(out)

    def test(self):
        # OHOS-specific checks run regardless of can_run: the signature check
        # inspects the shipped artifact rather than executing it.
        self._check_shipped_signature()

        if not can_run(self):
            self.output.warning(
                "cannot run on this host, skipping execution "
                "(compile+link+signature verified)")
            return

        self.run("./consumer", env="conanrun")
        self.output.info("CONSUMER_1_OF_1_PASS")
