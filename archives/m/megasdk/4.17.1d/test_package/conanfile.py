#!/usr/bin/env python3
"""Conan test_package for megasdk/4.17.1d.

Builds test_megasdk.cpp against the packaged libmega with an explicit
compiler invocation (flags assembled from the dependency graph, no
pkg-config indirection), runs it, and emits the HMBS machine-evidence
markers. The counting source is the binary's own
"MEGASDK_CHECKS_PASSED=a/b" line (single regex, no arithmetic patching).
The upstream marker is re-emitted from the res/megasdk_upstream_result.json
file the main recipe persisted, so cache-hit rounds still report evidence.
"""

import json
import os
import re
import shutil

from conan import ConanFile
from conan.errors import ConanException
from conan.tools.build import can_run


EXPECTED_CHECKS = 6


class MegasdkTestConan(ConanFile):
    settings = "os", "arch", "compiler", "build_type"
    test_type = "explicit"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def _resolve_compiler(self):
        # Round 5 adapt of libapreq2/2.17: the profile-baked absolute
        # compiler is "inaccessible or not found" on this worker, and
        # exists/isfile alone cannot prove usability on HMDFS, so every
        # candidate must pass a real --version spawn before it is used.
        try:
            configured = self.conf.get("tools.build:compiler_executables:cpp",
                                       check_type=str)
        except Exception:
            configured = None
        cands = []
        if configured:
            cands.append(configured)
        for name in ("clang++", "c++", "g++"):
            found = shutil.which(name)
            if found and found not in cands:
                cands.append(found)
        home_bin = os.path.join(os.path.expanduser("~"), "usr", "local",
                                "bin")
        for name in ("clang++", "c++"):
            cand = os.path.join(home_bin, name)
            if cand not in cands:
                cands.append(cand)
        for cand in cands:
            try:
                rc = self.run('"%s" --version' % cand, env="conanbuild",
                              ignore_errors=True)
            except Exception:
                continue
            if rc == 0:
                return cand
            self.output.info("[hmbs] test compiler unusable: %s" % cand)
        return configured or "clang++"

    def _dep_dir(self, dep, *subdirs):
        folder = self.dependencies[dep].package_folder
        for sub in subdirs:
            cand = os.path.join(folder, sub)
            if os.path.isdir(cand):
                return cand
        return os.path.join(folder, subdirs[0])

    def build(self):
        cxx = self._resolve_compiler()
        src = os.path.join(self.source_folder, "test_megasdk.cpp")
        exe = os.path.join(self.build_folder, "test_megasdk")
        incs = []
        libdirs = []
        for dep in ("megasdk", "cryptopp", "libsodium", "sqlite3",
                    "curl", "openssl", "c-ares", "zlib", "libuv"):
            try:
                incs.append(self._dep_dir(dep, "include"))
                libdirs.append(self._dep_dir(dep, "lib"))
            except Exception as exc:
                raise ConanException("test dep dir missing for %s: %s"
                                     % (dep, exc))
        cmd = [cxx, "-std=c++14", "-O1", src, "-o", exe]
        cmd += ["-I%s" % d for d in incs]
        cmd += ["-L%s" % d for d in libdirs]
        # Static libmega: all transitive archives must be spelled out.
        # -luv covers MegaTCPServer's uv_* references (true-device
        # 2026-10-17: undefined uv_async_init/uv_tcp_init/uv_run, ...);
        # it must follow -lmega so the static archive resolves.
        cmd += ["-lmega", "-luv", "-lcryptopp", "-lsodium", "-lsqlite3", "-lcurl",
                "-lssl", "-lcrypto", "-lcares", "-lz", "-lpthread", "-ldl"]
        self.output.info("[hmbs] compile: %s" % " ".join(cmd))
        self.run(" ".join('"%s"' % c for c in cmd), env="conanbuild")

    def test(self):
        if not can_run(self):
            raise ConanException("megasdk target consumers are not runnable")
        for key in ("TMPDIR", "TMP", "TEMP"):
            if not os.environ.get(key):
                tmp = os.path.join(self.build_folder, "tmp_hmbs")
                try:
                    os.makedirs(tmp, exist_ok=True)
                except OSError:
                    pass
                os.environ[key] = tmp
        exe = os.path.join(self.build_folder, "test_megasdk")
        log_path = os.path.join(self.build_folder, "consumer_test.log")
        # ignore_errors + always dump the log: the 2026-10-17 preflight
        # aborted with Error 134 (SIGABRT) inside test_megasdk, and the
        # bare self.run() raised before the log was emitted, leaving no
        # evidence of which of the 6 checks crashed. Dumping first
        # preserves the per-check MEGASDK-CHECK lines plus the new
        # MEGASDK-PROGRESS construct/destruct markers for the next round.
        # No counts are guessed here; a crash still fails below without a
        # test_package marker (honest incomplete, not a faked pass).
        rc = self.run('"%s" > "%s" 2>&1' % (exe, log_path),
                      env="conanrun", ignore_errors=True)
        out = ""
        try:
            with open(log_path, encoding="utf-8",
                      errors="replace") as handle:
                out = handle.read()
        except OSError as exc:
            raise ConanException("consumer test log missing: %s" % exc)
        for line in out.splitlines():
            self.output.info("[consumer] %s" % line)
        self.output.info("[hmbs] consumer exit code: %s" % rc)
        if rc != 0:
            raise ConanException(
                "consumer test_megasdk crashed with exit code %s; "
                "log above shows the last MEGASDK-CHECK/MEGASDK-PROGRESS "
                "line before the abort" % rc)
        match = re.search(r"^MEGASDK_CHECKS_PASSED=(\d+)/(\d+)\s*$", out,
                          flags=re.MULTILINE)
        if not match:
            raise ConanException(
                "MEGASDK_CHECKS_PASSED line missing in consumer output")
        passed, total = int(match.group(1)), int(match.group(2))
        if total != EXPECTED_CHECKS:
            raise ConanException(
                "consumer check count drift: expected %d, got %d"
                % (EXPECTED_CHECKS, total))
        ok = (passed == total)
        tp_result = {
            "executed": True,
            "passed": ok,
            "command": "./test_megasdk (Base64/URLCodec/MegaProxy/MegaApi checks)",
            "discovered": total,
            "passedCount": passed,
        }
        line = "HMBS_TEST_PACKAGE_RESULT=%s" % json.dumps(
            tp_result, separators=(",", ":"))
        self.output.info(line)
        print(line, flush=True)

        # Re-emit the real upstream result carried in the package res so
        # cache-hit runs still provide evidence every round.
        try:
            res = os.path.join(
                self.dependencies["megasdk"].package_folder,
                "res", "megasdk_upstream_result.json")
            with open(res, "r", encoding="utf-8") as handle:
                payload = json.load(handle)
            if not isinstance(payload, dict) or "status" not in payload:
                raise ValueError("invalid upstream payload: %r" % payload)
            uline = "HMBS_UPSTREAM_TEST_RESULT=%s" % json.dumps(
                payload, separators=(",", ":"))
            self.output.info(uline)
            print(uline, flush=True)
        except Exception as exc:
            self.output.warning("[hmbs] upstream res missing: %s" % exc)
            fallback = {
                "status": "failed",
                "framework": "automake",
                "command": "make check",
                "discovered": 0,
                "executed": 0,
                "passed": 0,
                "failed": 0,
                "skipped": 0,
                "reason": "res/megasdk_upstream_result.json missing: %s"
                          % exc,
            }
            fline = "HMBS_UPSTREAM_TEST_RESULT=%s" % json.dumps(
                fallback, separators=(",", ":"))
            self.output.info(fline)
            print(fline, flush=True)

        if not ok:
            raise ConanException("consumer checks failed: %d/%d"
                                 % (passed, total))
