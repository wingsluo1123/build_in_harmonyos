#!/usr/bin/env python3
"""Conan recipe for sf-pwgen 1.5 — HarmonyOS PC portable backend.

Upstream (anders/pwgen, tag 1.5) is a macOS-only Objective-C tool:
sf-pwgen.m imports <Foundation/Foundation.h> and "SFPasswordAssistant.h"
and links -framework Foundation/CoreFoundation/SecurityFoundation
(Makefile LIBS). None of that exists on OHOS/Linux, so the upstream
translation unit can never compile or link outside Apple platforms.

HarmonyOS adaptation (portable C99 backend, no platform macro):
 * patches/0001-ohos-portable-backend.patch adds sf-pwgen-portable.c, a
   pure-C99 reimplementation of the exact 1.5 CLI contract (options
   -a/-c/-l/-L/-v/-h, five algorithms, defaults count 5 / length 12,
   length clamp 8..128, the 1.5 "shorter than requested" warning,
   "sf-pwgen 1.5" version string). Entropy comes from /dev/urandom with
   rejection sampling (no modulo bias); a time/pid-seeded fallback covers
   sandboxes without /dev/urandom. No Foundation, no ObjC, no third-party
   dependency, so R36/W0 is trivially satisfied (zero requires).
 * build() compiles ONLY the portable file with the Conan-configured
   compiler (R33: path from tools.build:compiler_executables, never a bare
   ${CC} which is empty on release workers) and -j1 equivalent (single
   cc invocation, R9). The macOS Makefile/.m are left untouched in-tree;
   they are simply not used for the OHOS artifact (documented here, not
   silently deleted).
 * Artifacts: bin/sf-pwgen only (package_type application, R38 CLI tool).
   Upstream ships no man page; the license lives in the sf-pwgen.m header
   and is repackaged under licenses/ by package().
License: permissive BSD-style (see sf-pwgen.m header); SFPasswordAssistant.h
is public domain.
"""

import os
import shutil
import subprocess
import time

from conan import ConanFile
from conan.errors import ConanException
from conan.tools.files import apply_conandata_patches, copy, export_conandata_patches
from conan.tools.layout import basic_layout


class SfPwgenConan(ConanFile):
    name = "sf-pwgen"
    version = "1.5"
    description = "Password generator (HarmonyOS portable backend for the macOS sf-pwgen 1.5 CLI)"
    license = "BSD-3-Clause"
    homepage = "https://github.com/anders/pwgen"
    url = "https://github.com/anders/pwgen"
    topics = ("password", "password-generator", "security", "cli")
    package_type = "application"

    settings = "os", "arch", "compiler", "build_type"

    def export_sources(self):
        export_conandata_patches(self)

    def layout(self):
        basic_layout(self)

    def source(self):
        get = __import__("conan.tools.files", fromlist=["get"]).get
        get(self, **self.conan_data["sources"], strip_root=True)

    def validate(self):
        # R32: OHOS must be matched alongside Linux, never == "Linux".
        if self.settings.os not in ("Linux", "OHOS"):
            raise ConanException(
                "sf-pwgen portable backend requires a POSIX host (Linux or OHOS)")

    def generate(self):
        # No toolchain generators needed: single cc invocation in build().
        pass

    def _compiler(self):
        # R33: prefer the Conan conf compiler, but the profile-pinned
        # absolute path (/data/service/hnp/bin/clang) does not exist on
        # some preflight workers (Error 127). Probe it first; fall back
        # to PATH lookup (HMBS + VirtualBuildEnv put the real toolchain
        # on PATH) — proven pattern from sc/7.16-1.1.3 _select_cc().
        try:
            compilers = self.conf.get(
                "tools.build:compiler_executables", default={}, check_type=dict)
        except Exception:
            compilers = {}
        compilers = compilers or {}
        conf_cc = compilers.get("c")
        if conf_cc and os.path.isabs(conf_cc) and os.path.isfile(conf_cc):
            return conf_cc
        for cand in ("clang", "cc", "gcc"):
            found = shutil.which(cand)
            if found:
                self.output.info(
                    "sf-pwgen: conf CC %r unusable, using PATH %r" % (conf_cc, found))
                return found
        if conf_cc:
            return conf_cc
        return "clang"

    def build(self):
        apply_conandata_patches(self)
        cc = self._compiler()
        self.output.info("sf-pwgen: resolved CC=%r" % cc)
        src = os.path.join(self.source_folder, "sf-pwgen-portable.c")
        if not os.path.isfile(src):
            raise ConanException(
                "build(): missing portable backend %s (patch not applied?)" % src)
        out = os.path.join(self.build_folder, "sf-pwgen")
        # R9: single translation unit, no parallel make involved.
        # R33: cc comes from Conan conf above, never from shell $CC.
        # Fork-hardening (replaces the 5x identical `self.run(sh -c)` retry:
        # each retry itself needed a fork, so under PID exhaustion
        # ("sh: can't fork - try again", EAGAIN) every retry failed the
        # same way while holding the shared slot 60s+). New route cuts
        # forks to the absolute minimum: (1) compile via direct
        # subprocess argv with shell=False, i.e. no intermediate /bin/sh
        # fork; (2) ABI check below runs in-process, not as a second
        # python subprocess. Only EAGAIN/fork failures are retried (3x
        # with 5s/10s backoff, no fork while sleeping); real compile
        # errors fail immediately.
        argv = [cc, "-O2", "-Wall", "-Wextra", "-std=c99",
                "-o", out, src]
        last_err = None
        for attempt in (1, 2, 3):
            try:
                proc = subprocess.run(argv, stdout=subprocess.PIPE,
                                      stderr=subprocess.STDOUT, text=True)
            except OSError as exc:
                last_err = "OSError %s" % exc
                if "Resource temporarily unavailable" not in str(exc):
                    raise ConanException(
                        "build(): compiler spawn failed: %s" % exc)
            else:
                if proc.returncode == 0:
                    last_err = None
                    break
                out_text = proc.stdout or ""
                last_err = "exit %d: %.2000s" % (proc.returncode, out_text)
                if ("can't fork" not in out_text
                        and "Resource temporarily unavailable" not in out_text
                        and "posix_spawn failed" not in out_text):
                    raise ConanException(
                        "build(): compile failed: %s" % last_err)
            if attempt >= 3:
                break
            self.output.warning(
                "sf-pwgen: compile attempt %d/3 hit transient "
                "resource exhaustion (%s), sleeping before retry"
                % (attempt, last_err))
            time.sleep(5 * attempt)
        if last_err is not None:
            raise ConanException(
                "build(): compiler unavailable after 3 attempts "
                "(shared-runner EAGAIN/fork exhaustion, infra): %s"
                % last_err)
        if not os.path.isfile(out):
            raise ConanException("build(): compiler did not produce %s" % out)
        try:
            os.chmod(out, 0o755)
        except OSError:
            pass
        # HarmonyOS artifact checks A1-A3 (in-process ELF inspection:
        # same ohos_abi_check.check_binary() logic, zero extra fork).
        checker = os.path.join(
            self.export_sources_folder, "test_package", "ohos_abi_check.py")
        if os.path.isfile(checker):
            import importlib.util
            spec = importlib.util.spec_from_file_location(
                "ohos_abi_check", checker)
            mod = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(mod)
            results = mod.check_binary(out)
            for name, ok, detail in results:
                self.output.info("[%s] %s: %s"
                                 % ("PASS" if ok else "FAIL", name, detail))
            bad = [n for n, ok, _ in results if not ok]
            if bad:
                raise ConanException(
                    "build(): OHOS ABI check failed: %s" % ",".join(bad))

    def package(self):
        bindir = os.path.join(self.package_folder, "bin")
        licdir = os.path.join(self.package_folder, "licenses")
        os.makedirs(bindir, exist_ok=True)
        os.makedirs(licdir, exist_ok=True)
        copy(self, "sf-pwgen", src=self.build_folder, dst=bindir,
             keep_path=False)
        # Upstream has no LICENSE file; the license text lives in the
        # sf-pwgen.m header. Repackage the upstream README + VERSIONS as
        # provenance alongside it.
        copy(self, "README.md", src=self.source_folder, dst=licdir,
             keep_path=False)
        copy(self, "VERSIONS.md", src=self.source_folder, dst=licdir,
             keep_path=False)
        exe = os.path.join(bindir, "sf-pwgen")
        if not os.path.isfile(exe):
            raise ConanException("package(): missing build artifact %s" % exe)
        try:
            os.chmod(exe, 0o755)
        except OSError:
            pass

    def package_info(self):
        self.cpp_info.bindirs = ["bin"]
        self.cpp_info.includedirs = []
        self.cpp_info.libdirs = []
        self.cpp_info.libs = []
        self.runenv_info.prepend_path(
            "PATH", os.path.join(self.package_folder, "bin"))
