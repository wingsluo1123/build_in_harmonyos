#!/usr/bin/env python3
"""Conan recipe — inotify 4.25.9.0 (makefile, hand-written minimal build).

inotify (upstream inotify-tools) is a C library (libinotifytools) and a set
of command-line programs (inotifywait/inotifywatch) providing a simple
interface to the Linux inotify filesystem-event API.

OHOS adaptations (verified against the 4.25.9.0 source tree):
  1. Upstream builds with Autotools, but the CI/real-machine toolchain has
     no aclocal (autoreconf fails), so build() writes a minimal Makefile +
     hand-generated config.h directly instead of running configure.
  2. Upstream generates inotify.h/fanotify.h from sys/inotify.h /
     sys/fanotify.h probes. OHOS ships sys/inotify.h but has no working
     sys/fanotify.h, so build() writes shims: inotify.h includes
     <sys/inotify.h>, fanotify.h undefines LINUX_FANOTIFY and falls back
     to the bundled fanotify-dfid-name.h.
  3. Upstream self-tests (libinotifytools/src/test + t/*.t sharness suite)
     run in build() on the native machine and emit
     HMBS_UPSTREAM_TEST_RESULT with deterministic per-case exit-code
     counting (never string arithmetic).
"""
import glob
import json
import os
import shutil
import subprocess

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.build import can_run
from conan.tools.env import VirtualBuildEnv
from conan.tools.files import (apply_conandata_patches, copy,
                               export_conandata_patches, get)
from conan.tools.layout import basic_layout

# Upstream registration-level总数 (official build_and_test.sh):
#   libinotifytools/src/test (automake TESTS, 1 binary)
#   + t/*.t sharness suite (14 files)
UPSTREAM_UNIT = 1
UPSTREAM_INTEGRATION_GLOB = "t/*.t"


class InotifyConan(ConanFile):
    name = "inotify"
    version = "4.25.9.0"
    description = "inotify filesystem event monitoring C library and command-line tools"
    license = "GPL-2.0-or-later"
    homepage = "https://github.com/inotify-tools/inotify-tools"
    url = "https://github.com/inotify-tools/inotify-tools"
    topics = ("linux", "filesystem", "monitoring", "inotify")
    package_type = "library"

    settings = "os", "compiler", "build_type", "arch"
    options = {"shared": [True, False], "fPIC": [True, False]}
    default_options = {"shared": False, "fPIC": True}

    def validate(self):
        if str(self.settings.os) not in ("Linux", "OHOS"):
            raise ConanInvalidConfiguration("inotify is built for Linux/OHOS only")

    def export_sources(self):
        export_conandata_patches(self)

    def layout(self):
        basic_layout(self)

    def source(self):
        # R39: official source only; CI adds mirror fallback automatically.
        get(self, **self.conan_data["sources"][self.version], strip_root=True)

    def generate(self):
        # Hand-written Makefile carries its own CC/CXX/AR/CXXFLAGS; only
        # the conanbuild env (compiler paths, CFLAGS/LDFLAGS) is needed.
        VirtualBuildEnv(self).generate()

    def _is_runnable(self, exe):
        # A conf-provided absolute path may be stale (e.g. a toolchain
        # directory that no longer exists on the real machine). Accept a
        # candidate only if it resolves and answers --version.
        if not exe:
            return False
        path = exe if os.path.isabs(exe) else (shutil.which(exe) or exe)
        if not path or not os.path.isfile(path):
            # Bare tool names on PATH (no directory separator) are still
            # usable when the HMBS preflight prepends the tool directory
            # to PATH; verify via which() instead of isfile().
            if shutil.which(exe):
                path = shutil.which(exe)
            else:
                return False
        if not os.access(path, os.X_OK):
            return False
        try:
            proc = subprocess.run(
                [path, "--version"], stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT, timeout=30)
            return proc.returncode == 0
        except Exception:
            return False

    def _pick(self, conf_val, env_val, fallbacks):
        for cand in ([conf_val] if conf_val else []) + \
                   ([env_val] if env_val else []) + list(fallbacks):
            if not cand:
                continue
            if os.path.isabs(cand):
                if self._is_runnable(cand):
                    return cand
                continue
            found = shutil.which(cand)
            if found and self._is_runnable(found):
                return found
            if self._is_runnable(cand):
                return cand
        return None

    def _resolve_tools(self):
        compilers = self.conf.get("tools.build:compiler_executables",
                                  default={}, check_type=dict) or {}
        cc = self._pick(compilers.get("c"), os.environ.get("CC"),
                        ["clang", "gcc", "cc"])
        cxx = self._pick(compilers.get("cpp"), os.environ.get("CXX"),
                         ["clang++", "g++", "c++"])
        ar = self._pick(compilers.get("archive"), os.environ.get("AR"),
                        ["llvm-ar", "ar"])
        missing = [n for n, v in (("CC", cc), ("CXX", cxx), ("AR", ar)) if not v]
        if missing:
            raise RuntimeError(
                "no runnable compiler found (missing: %s; conf=%r; "
                "PATH=%s)" % (",".join(missing), compilers,
                              os.environ.get("PATH", "")[:500]))
        self.output.info("resolved compilers: CC=%s CXX=%s AR=%s" % (cc, cxx, ar))
        # Double insurance (per libnl3 experience): export to the build
        # process env so make/subprocess invocations agree with Makefile.
        os.environ["CC"] = cc
        os.environ["CXX"] = cxx
        os.environ["AR"] = ar
        make = None
        try:
            make = self._pick(
                self.conf.get("user.hmbs:make_path", default=None, check_type=str),
                os.environ.get("HMBS_MAKE"),
                ["make", "gmake"])
        except Exception:
            make = self._pick(None, os.environ.get("HMBS_MAKE"), ["make", "gmake"])
        if make:
            os.environ.setdefault("HMBS_MAKE", make)
            self.output.info("resolved make: %s" % make)
        else:
            self.output.warning("no HMBS_MAKE/user.hmbs:make_path; using plain 'make' from PATH")
        return cc, cxx, ar, (make or "make")

    def build(self):
        apply_conandata_patches(self)
        cc, cxx, ar, make_bin = self._resolve_tools()
        # Upstream #include "inotifytools/inotify.h" is generated by
        # configure from the sys/inotify.h probe. OHOS ships
        # sys/inotify.h, so write a shim header including it.
        inotify_h_dir = os.path.join(self.source_folder, "libinotifytools", "src", "inotifytools")
        with open(os.path.join(inotify_h_dir, "inotify.h"), "w", encoding="utf-8") as f:
            f.write("#ifndef _INOTIFYTOOLS_INOTIFY_H_SHIM\n")
            f.write("#define _INOTIFYTOOLS_INOTIFY_H_SHIM\n")
            f.write("#include <sys/inotify.h>\n")
            f.write("#endif\n")
        # Upstream #include "inotifytools/fanotify.h" is generated from
        # the sys/fanotify.h probe. OHOS has no working fanotify, so
        # disable the LINUX_FANOTIFY path and use the bundled fallback.
        with open(os.path.join(inotify_h_dir, "fanotify.h"), "w", encoding="utf-8") as f:
            f.write("#ifndef _INOTIFYTOOLS_FANOTIFY_H_SHIM\n")
            f.write("#define _INOTIFYTOOLS_FANOTIFY_H_SHIM\n")
            f.write("#undef LINUX_FANOTIFY\n")
            f.write('#include "fanotify-dfid-name.h"\n')
            f.write("#endif\n")
        # Hand-generated config.h (OHOS aarch64: sys/inotify.h works,
        # sys/fanotify.h does not; aclocal unavailable so configure
        # never runs).
        config_h = os.path.join(self.source_folder, "config.h")
        with open(config_h, "w", encoding="utf-8") as f:
            f.write("/* Hand-generated config.h for OHOS (aclocal unavailable) */\n")
            f.write('#define PACKAGE_NAME "inotify-tools"\n')
            f.write('#define PACKAGE_TARNAME "inotify-tools"\n')
            f.write('#define PACKAGE_VERSION "4.25.9.0"\n')
            f.write('#define PACKAGE_STRING "inotify-tools 4.25.9.0"\n')
            f.write('#define PACKAGE_BUGREPORT "https://github.com/inotify-tools/inotify-tools/issues"\n')
            f.write('#define PACKAGE_URL "https://github.com/inotify-tools/inotify-tools"\n')
            f.write('#define INOTIFYTOOLS_VERSION "4.25.9.0"\n')
            f.write("#define HAVE_STDLIB_H 1\n")
            f.write("#define HAVE_STDIO_H 1\n")
            f.write("#define HAVE_STRING_H 1\n")
            f.write("#define HAVE_STRINGS_H 1\n")
            f.write("#define HAVE_UNISTD_H 1\n")
            f.write("#define HAVE_INTTYPES_H 1\n")
            f.write("#define HAVE_STDINT_H 1\n")
            f.write("#define HAVE_SYS_STAT_H 1\n")
            f.write("#define HAVE_SYS_TYPES_H 1\n")
            # NOTE: no HAVE_MCHECK_H here. Upstream test.cpp includes
            # <mcheck.h> only under HAVE_MCHECK_H; that header is
            # glibc-specific and absent from the OHOS sysroot, so defining
            # it breaks the unit-test build (main library never includes
            # it, which is why the library itself compiled fine).
            f.write("#define HAVE_DAEMON 1\n")
            f.write("#define HAVE_SYS_INOTIFY_H 1\n")
            f.write("#define SYS_INOTIFY_H_EXISTS_AND_WORKS 1\n")
            f.write("#define STDC_HEADERS 1\n")
        env_script = os.path.join(self.generators_folder, "conanbuild.sh")
        prefix = os.path.join(self.build_folder, "staging")
        inc_dir = os.path.join(self.source_folder, "libinotifytools", "src")
        common_cxx = (
            "-std=c++17 -fno-exceptions -Wall -Wextra -Wshadow -Werror "
            "-Wno-unused-parameter -Wno-sign-compare "
            "-Wno-unused-command-line-argument -Wno-missing-field-initializers "
            "-I{inc} -I{inc}/inotifytools "
            "-DINOTIFYTOOLS_VERSION=\\\"4.25.9.0\\\"".format(inc=inc_dir)
        )
        makefile_path = os.path.join(self.build_folder, "Makefile")
        with open(makefile_path, "w", encoding="utf-8") as f:
            f.write("# Minimal Makefile for inotify OHOS build (aclocal unavailable)\n")
            f.write("CC = %s\nCXX = %s\nAR = %s\n" % (cc, cxx, ar))
            f.write("PREFIX = %s\n" % prefix)
            f.write("CXXFLAGS += %s\n" % common_cxx)
            f.write("CXXFLAGS += $(EXTRA_CXXFLAGS)\n")
            f.write("LDFLAGS += $(EXTRA_LDFLAGS)\n\n")
            f.write("LIB_OBJS = libinotifytools/src/inotifytools.o libinotifytools/src/redblack.o libinotifytools/src/stats.o\n")
            f.write("libinotifytools/libinotifytools.a: $(LIB_OBJS)\n")
            f.write("\t$(AR) rcs $@ $^\n\n")
            f.write("libinotifytools/src/%.o: libinotifytools/src/%.cpp\n")
            f.write("\t$(CXX) $(CXXFLAGS) -c $< -o $@\n\n")
            f.write("src/inotifywait: src/inotifywait.cpp src/common.o libinotifytools/libinotifytools.a\n")
            f.write("\t$(CXX) $(CXXFLAGS) src/inotifywait.cpp src/common.o -Ilibinotifytools/src -Llibinotifytools -linotifytools $(LDFLAGS) -o $@\n\n")
            f.write("src/inotifywatch: src/inotifywatch.cpp src/common.o libinotifytools/libinotifytools.a\n")
            f.write("\t$(CXX) $(CXXFLAGS) src/inotifywatch.cpp src/common.o -Ilibinotifytools/src -Llibinotifytools -linotifytools $(LDFLAGS) -o $@\n\n")
            f.write("src/common.o: src/common.cpp\n")
            f.write("\t$(CXX) $(CXXFLAGS) -c $< -o $@\n\n")
            f.write("install: all\n")
            # Portable install (no `install(1)`): the HMBS install shim
            # only accepts single-file two-arg calls and HMBS_CAP_CHMOD=0
            # breaks `install -m`, so use mkdir + cp which work everywhere.
            f.write("\tmkdir -p $(PREFIX)/bin $(PREFIX)/lib $(PREFIX)/include/inotifytools\n")
            f.write("\tcp -f src/inotifywait src/inotifywatch $(PREFIX)/bin/\n")
            f.write("\tcp -f libinotifytools/libinotifytools.a $(PREFIX)/lib/\n")
            f.write("\tcp -f libinotifytools/src/inotifytools/inotifytools.h libinotifytools/src/inotifytools/inotify-nosys.h libinotifytools/src/inotifytools/inotify.h $(PREFIX)/include/inotifytools/\n\n")
            f.write("all: libinotifytools/libinotifytools.a src/inotifywait src/inotifywatch\n")
        if os.path.exists(env_script):
            make_cmd = ". \"%s\" && \"%s\" -f \"%s\" -j1 all" % (env_script, make_bin, makefile_path)
        else:
            make_cmd = "\"%s\" -f \"%s\" -j1 all" % (make_bin, makefile_path)
        self.run(make_cmd, cwd=self.source_folder)
        # Layer 1: run the upstream self-tests on the native machine.
        self._run_upstream_tests(cxx, common_cxx)

    def _run_case(self, argv, cwd, timeout):
        try:
            proc = subprocess.run(
                argv, cwd=cwd, env=dict(os.environ),
                stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                text=True, timeout=timeout)
            out = proc.stdout or ""
            return proc.returncode == 0, out
        except subprocess.TimeoutExpired as exc:
            out = exc.stdout or ""
            if isinstance(out, bytes):
                out = out.decode("utf-8", "replace")
            return False, out + "\n[TIMEOUT after %ss]\n" % timeout
        except Exception as exc:
            return False, "[HARNESS-ERROR] %s\n" % exc

    @staticmethod
    def _fail_lines(out, limit=4):
        # Evidence helper only (counting stays exit-code based): prefer
        # the harness failure lines ("not ok", "failed", "error") over
        # the trailing TAP plan line ("1..1"), which carries no diagnosis.
        lines = [l for l in (out or "").strip().splitlines() if l.strip()]
        if not lines:
            return ["(no output)"]
        key = [l for l in lines
               if "not ok" in l.lower() or "failed" in l.lower() or "error" in l.lower()]
        return (key or lines[-2:])[:limit] if key else lines[-2:]

    def _split_environment_failures(self, by_name):
        # Separate sandbox-restriction failures (category environment) from
        # genuine functional failures. Every decision is made from on-device
        # probes and the failing case's own output/content; nothing is
        # assumed from the build host.
        try:
            probe = os.path.join("/tmp", "hmbs-tmp-probe-%d" % os.getpid())
            with open(probe, "w") as fh:
                fh.write("x")
            os.remove(probe)
            tmp_writable = True
        except Exception:
            tmp_writable = False
        bash_missing = not shutil.which("bash")
        self.output.info("env probes: /tmp writable=%s bash_missing=%s"
                         % (tmp_writable, bash_missing))
        env_names, rest = [], []
        t_dir = os.path.join(self.source_folder, "t")
        for name, (out, _interp) in by_name.items():
            low = (out or "").lower()
            if name == "libinotifytools/src/test":
                # Proven this round: watch / -> EACCES, TEST_DIR mkdir /tmp fails.
                if ("/tmp" in (out or "") and "mkdir" in low) or \
                   "permission denied" in low:
                    env_names.append(name)
                    continue
                rest.append(name)
                continue
            content = ""
            try:
                with open(os.path.join(t_dir, os.path.basename(name)),
                          encoding="utf-8", errors="replace") as fh:
                    content = fh.read()
            except Exception:
                pass
            first = content.splitlines()[0] if content.splitlines() else ""
            needs_bash = "bash" in first
            uses_tmp = "/tmp" in content
            if (needs_bash and bash_missing) or (uses_tmp and not tmp_writable):
                env_names.append(name)
            else:
                rest.append(name)
        return env_names, rest

    def _run_upstream_tests(self, cxx=None, common_cxx=None):
        t_dir = os.path.join(self.source_folder, "t")
        t_files = sorted(glob.glob(os.path.join(t_dir, "*.t")))
        discovered = UPSTREAM_UNIT + len(t_files)
        if not can_run(self):
            marker = {
                "status": "skipped",
                "framework": "sharness",
                "command": "cross-building: upstream tests not executed",
                "discovered": discovered,
                "executed": 0,
                "passed": 0,
                "failed": 0,
                "skipped": discovered,
                "reason": "cross-building: binaries cannot run on the build host",
            }
            line = "HMBS_UPSTREAM_TEST_RESULT=" + json.dumps(marker)
            self.output.info(line)
            print(line, flush=True)
            return
        default_shell = os.environ.get("CONFIG_SHELL") or os.environ.get("SHELL") or "sh"
        bash_path = shutil.which("bash")
        if bash_path:
            self.output.info("bash available at %s; .t files with a bash shebang will use it" % bash_path)
        else:
            self.output.warning("no bash on PATH; .t files requiring bash may fail (recorded as-is)")
        results = []
        # Case 1: automake unit (libinotifytools/src/test).
        unit_src = os.path.join(self.source_folder, "libinotifytools", "src")
        unit_bin = os.path.join(unit_src, "inotify_unit_test")
        unit_out = ""
        unit_ok = False
        try:
            inc = os.path.join(self.source_folder, "libinotifytools", "src")
            unit_cxx = cxx or os.environ.get("CXX") or "clang++"
            # Run the compile via subprocess (not self.run) so the real
            # compiler diagnostics land in unit_out and stay visible in
            # the preflight log even when the summary is truncated.
            cmd = (
                "%s -std=c++17 -fno-exceptions -Wall -Wextra -Wno-unused-parameter "
                "-Wno-sign-compare -Wno-missing-field-initializers "
                "-I\"%s\" -I\"%s/inotifytools\" -I\"%s\" "
                "\"%s/test.cpp\" \"%s\" -o \"%s\"" % (
                    unit_cxx,
                    inc, inc, self.source_folder,
                    unit_src,
                    os.path.join(unit_src, "..", "libinotifytools.a"),
                    unit_bin,
                ))
            proc = subprocess.run(
                cmd, shell=True, cwd=self.source_folder,
                env=dict(os.environ), stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT, text=True, timeout=300)
            build_out = proc.stdout or ""
            if proc.returncode != 0:
                unit_out = "[UNIT-BUILD-ERROR] compiler exit %d\n%s\n" % (
                    proc.returncode, build_out)
                unit_ok = False
                self.output.warning(
                    "[upstream] libinotifytools/src/test BUILD FAIL:\n%s" % build_out[-3000:])
            else:
                unit_ok, unit_out = self._run_case([unit_bin], cwd=unit_src, timeout=300)
        except Exception as exc:
            unit_out = "[UNIT-BUILD-ERROR] %s\n" % exc
            unit_ok = False
        results.append(("libinotifytools/src/test", unit_ok, unit_out, "compile+run"))
        if unit_ok:
            self.output.info("[upstream] libinotifytools/src/test: PASS")
        else:
            tail = " | ".join([l for l in unit_out.strip().splitlines() if l.strip()][-3:])
            self.output.warning("[upstream] libinotifytools/src/test: FAIL (%s)" % tail)
        # Cases 2..N: sharness integration suite, one case per .t file.
        # Pass/fail comes from each script's exit code only (deterministic
        # single source; no stdout keyword counting or arithmetic fixes).
        # Honor each file's own shebang: two upstream .t files are
        # #!/bin/bash and use bash-isms ([[ ]]); forcing them under sh
        # fails deterministically. Fall back to the default shell only
        # when the shebang interpreter is unavailable.
        for t_file in t_files:
            name = "t/" + os.path.basename(t_file)
            interp = default_shell
            try:
                with open(t_file, encoding="utf-8", errors="replace") as fh:
                    first = fh.readline().strip()
                if first.startswith("#!"):
                    want = first[2:].strip().split()
                    prog = os.path.basename(want[-1]) if want else ""
                    if "bash" in prog:
                        if bash_path:
                            interp = bash_path
                        else:
                            self.output.warning(
                                "[upstream] %s needs bash (shebang %r) but no bash on PATH" % (name, first))
                    elif prog and shutil.which(prog):
                        interp = shutil.which(prog)
            except Exception as exc:
                self.output.warning("[upstream] %s shebang probe failed: %s" % (name, exc))
            ok, out = self._run_case([interp, t_file], cwd=t_dir, timeout=180)
            results.append((name, ok, out, interp))
            tail = " | ".join(self._fail_lines(out)[-2:])
            if ok:
                self.output.info("[upstream] %s: PASS" % name)
            else:
                self.output.warning("[upstream] %s: FAIL (%s)" % (name, tail))
        passed = sum(1 for _, ok, _, _ in results if ok)
        failed = len(results) - passed
        executed = len(results)
        status = "passed" if failed == 0 else "incomplete"
        marker = {
            "status": status,
            "framework": "sharness",
            "command": "libinotifytools/src/test + per-file-shebang sh *.t in t/ (%d files)" % len(t_files),
            "discovered": discovered,
            "executed": executed,
            "passed": passed,
            "failed": failed,
            "skipped": 0,
        }
        if failed:
            fail_names = [n for (n, ok, _, _) in results if not ok]
            fanotify_names = [n for n in fail_names if "fanotify" in n or "fsnotify" in n]
            other_names = [n for n in fail_names if n not in fanotify_names]
            # --no-dereference symlink cases depend on kernel symlink-watch
            # semantics (watching the link itself vs its target; touch -h
            # updating the link inode). Both failed on-device with opposite
            # expectations (ignore-target expects timeout exit 2 but saw an
            # event; respond-to-link expects exit 0 but saw none), which
            # points at OHOS/HMFS symlink event behavior, not at the recipe.
            symlink_names = [n for n in other_names if "no-dereference" in n]
            core_names = [n for n in other_names if n not in symlink_names]
            marker["reason"] = (
                "upstream %d/%d passed, %d real failures on device; "
                "technical causes and evidence in gaps" % (passed, discovered, failed))
            marker["gaps"] = []
            if fanotify_names:
                marker["gaps"].append({
                    "count": len(fanotify_names),
                    "category": "ohos_feature",
                    "detail": (
                        "OHOS has no working fanotify (no fanotify_init/fanotify_mark; "
                        "recipe undefines LINUX_FANOTIFY and uses the bundled fallback); "
                        "affected: %s" % ", ".join(fanotify_names)),
                    "evidence": "recipe fanotify.h shim (undef LINUX_FANOTIFY); failing case names + exit codes above",
                })
            if symlink_names:
                by_all = {n: (out, interp) for (n, ok, out, interp) in results if not ok}
                tails = [n + " [" + str(by_all[n][1]) + "]: " + " | ".join(self._fail_lines(by_all[n][0]))
                         for n in symlink_names]
                marker["gaps"].append({
                    "count": len(symlink_names),
                    "category": "ohos_feature",
                    "detail": (
                        "inotify --no-dereference symlink-watch semantics differ on device: "
                        "ignore-symlinked-file watches the link (touch target) and expects "
                        "timeout exit 2, respond-to-symlink-event touches the link itself "
                        "(touch -h) and expects exit 0; both failed with opposite "
                        "expectations, pointing at kernel/HMFS symlink event behavior, not "
                        "the recipe; affected: %s" % ", ".join(symlink_names)),
                    "evidence": "upstream t/ scripts (touch test vs touch -h test-symlink, "
                                "expected exits 2 vs 0) + case outputs: %s" % " | ".join(tails),
                })
            if core_names:
                by_name = {n: (out, interp) for (n, ok, out, interp) in results
                           if not ok and n in core_names}
                env_names, fail_names_rest = self._split_environment_failures(by_name)
                if env_names:
                    tails = [n + ": " + " | ".join(self._fail_lines(by_name[n][0]))
                             for n in env_names]
                    marker["gaps"].append({
                        "count": len(env_names),
                        "category": "environment",
                        "detail": (
                            "preflight sandbox restrictions, corroborated on-device: "
                            "/tmp is not writable (unit TEST_DIR mkdir fails; HMBS "
                            "injects a private TMPDIR for this reason) which breaks "
                            "upstream cases hardcoding /tmp (unit mkdir asserts, "
                            ".t cases with 'cp log /tmp/'); watching / is denied "
                            "(EACCES); no bash on PATH for upstream #!/bin/bash "
                            "cases; affected: %s" % ", ".join(env_names)),
                        "evidence": "case outputs: %s" % " | ".join(tails),
                    })
                if fail_names_rest:
                    tails = [n + " [%s]: " % by_name[n][1] + " | ".join(self._fail_lines(by_name[n][0]))
                             for n in fail_names_rest]
                    marker["gaps"].append({
                        "count": len(fail_names_rest),
                        "category": "test_failure",
                        "detail": "remaining upstream cases report runtime failures: %s" % ", ".join(fail_names_rest),
                        "evidence": "case outputs: %s" % " | ".join(tails),
                    })
        if not (marker["passed"] + marker["failed"] == marker["executed"]
                and marker["executed"] + marker["skipped"] <= marker["discovered"]
                and marker["executed"] <= marker["discovered"]
                and sum(g["count"] for g in marker.get("gaps", [])) == failed):
            raise RuntimeError("upstream marker identity broken: %r" % (marker,))
        line = "HMBS_UPSTREAM_TEST_RESULT=" + json.dumps(marker)
        self.output.info(line)
        print(line, flush=True)

    def package(self):
        copy(self, "COPYING", dst=os.path.join(self.package_folder, "licenses"), src=self.source_folder)
        env_script = os.path.join(self.generators_folder, "conanbuild.sh")
        prefix = os.path.join(self.build_folder, "staging")
        makefile_path = os.path.join(self.build_folder, "Makefile")
        pkg_make = (os.environ.get("HMBS_MAKE") or shutil.which("make") or "make")
        try:
            conf_make = self.conf.get("user.hmbs:make_path", default=None, check_type=str)
            if conf_make:
                pkg_make = conf_make if os.path.isfile(conf_make) else pkg_make
        except Exception:
            pass
        if os.path.exists(env_script):
            make_cmd = ". \"%s\" && \"%s\" -f \"%s\" install PREFIX=%s" % (env_script, pkg_make, makefile_path, prefix)
        else:
            make_cmd = "\"%s\" -f \"%s\" install PREFIX=%s" % (pkg_make, makefile_path, prefix)
        self.run(make_cmd, cwd=self.source_folder)
        copy(self, "*", src=prefix, dst=self.package_folder)

    def package_info(self):
        # CMakeDeps default target would be inotify::inotify, but the
        # test_package links inotify::inotifytools (the actual lib name).
        # Declare it explicitly so find_package(inotify) provides it.
        self.cpp_info.set_property("cmake_file_name", "inotify")
        self.cpp_info.set_property("cmake_target_name", "inotify::inotifytools")
        self.cpp_info.set_property("pkg_config_name", "inotify")
        self.cpp_info.libs = ["inotifytools"]
        self.cpp_info.includedirs = ["include"]
        self.cpp_info.bindirs = ["bin"]
