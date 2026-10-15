#!/usr/bin/env python3
"""Conan test_package for vxi 0.0.20121221 (R34: real consumer of the RPC API).

Builds test_vxi.c against the installed headers + static archives and
runs it. The binary performs 4 real checks (program numbers, two XDR
round-trips, stub symbol resolution); exit 0 means 4/4 passed. Markers
are emitted in both conan output and raw stdout for the HMBS evidence
gate; the upstream no_tests marker is re-emitted every run so cache-hit
rounds (main build() skipped) still carry evidence.
"""
import json
import os

from conan import ConanFile
from conan.errors import ConanException
from conan.tools.build import can_run


class VxiTestConan(ConanFile):
    settings = "os", "arch", "compiler", "build_type"
    generators = "VirtualRunEnv"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def build(self):
        vxi = self.dependencies[self.tested_reference_str]
        tirpc = self.dependencies["libtirpc"]
        incs = []
        libdirs = []
        for dep in (vxi, tirpc):
            pf = dep.package_folder or ""
            for inc in dep.cpp_info.includedirs:
                incs.append(inc if os.path.isabs(inc) else os.path.join(pf, inc))
            for libd in dep.cpp_info.libdirs:
                libdirs.append(libd if os.path.isabs(libd) else os.path.join(pf, libd))
        inc_flags = " ".join(f'-I"{p}"' for p in dict.fromkeys(incs))
        lib_flags = " ".join(f'-L"{p}"' for p in dict.fromkeys(libdirs) if p)
        compilers = self.conf.get("tools.build:compiler_executables", default={}, check_type=dict) or {}
        cc = compilers.get("c") or os.environ.get("CC") or "clang"
        # Diagnostics: dump the packaged headers so a stale/empty vxi.h
        # is visible in the log instead of surfacing as 20 cascading
        # 'undeclared identifier' errors (true preflight 2026-10-14).
        try:
            vxi_pf = vxi.package_folder or ""
            vxi_inc = os.path.join(vxi_pf, "include")
            self.output.info(f"vxi test: package include dir: {vxi_inc}")
            for fn in sorted(os.listdir(vxi_inc)):
                fp = os.path.join(vxi_inc, fn)
                sz = os.path.getsize(fp) if os.path.isfile(fp) else -1
                self.output.info(f"vxi test: include/{fn} ({sz} B)")
            for hdr, syms in (("vxi.h", ("DEVICE_CORE", "Create_LinkParms",
                                         "xdr_Create_LinkParms")),
                              ("vxi_intr.h", ("DEVICE_INTR", "Device_SrqParms"))):
                fp = os.path.join(vxi_inc, hdr)
                if os.path.isfile(fp):
                    with open(fp, "r", encoding="utf-8",
                              errors="replace") as f:
                        content = f.read()
                    missing = [s for s in syms if s not in content]
                    self.output.info(
                        f"vxi test: {hdr} {len(content)} chars, "
                        f"missing={missing}")
                else:
                    self.output.warning(f"vxi test: {hdr} NOT FOUND in {vxi_inc}")
        except Exception as exc:
            self.output.warning(f"vxi test: header diagnostics skipped: {exc}")
        # Static archives first (symbol order matters), tirpc runtime last.
        self.run(
            f'{cc} test_vxi.c -o test_vxi {inc_flags} {lib_flags} '
            f'-lvxiclient -lvxiserver -ltirpc -O2 -fPIC',
            env="conanbuild",
        )

    def test(self):
        if not can_run(self):
            self.output.info("cross-building: compile+link verified, runtime skipped")
            return
        bash = os.environ.get("CONFIG_SHELL", "/bin/sh")
        if not os.path.isfile(bash.split()[0]):
            bash = "/bin/sh"
        # Writable TMPDIR for the XDR test (never touch read-only /tmp).
        tmpdir = ""
        for var in ("TMPDIR", "TMP", "TEMP"):
            cand = os.environ.get(var, "")
            if cand and cand != "/tmp" and os.path.isdir(cand):
                try:
                    probe = os.path.join(cand, ".vxi_test_wtest")
                    with open(probe, "w") as f:
                        f.write("ok")
                    os.remove(probe)
                    tmpdir = cand
                    break
                except Exception:
                    continue
        if not tmpdir:
            tmpdir = os.path.join(self.build_folder, "tmp-test")
            os.makedirs(tmpdir, exist_ok=True)
        for var in ("TMPDIR", "TMP", "TEMP"):
            os.environ[var] = tmpdir
        command = f'TMPDIR="{tmpdir}" "{bash}" -c \'./test_vxi\''
        discovered = 4
        passed = 0
        try:
            self.run(command, env="conanrun")
            passed = discovered
        except Exception as exc:
            self.output.error(f"test_vxi failed: {exc}")
        tp_result = {
            "executed": True,
            "passed": passed == discovered,
            "command": "./test_vxi",
            "discovered": discovered,
            "passedCount": passed,
        }
        tp_line = "HMBS_TEST_PACKAGE_RESULT=" + json.dumps(tp_result)
        print(tp_line, flush=True)
        self.output.info(tp_line)
        # Upstream ships no test suite (audited); re-emit no_tests every run.
        upstream_marker = {
            "status": "no_tests",
            "framework": "none",
            "command": "make check",
            "discovered": 0,
            "executed": 0,
            "passed": 0,
            "failed": 0,
            "skipped": 0,
            "reason": "vxi 0.0.20121221 upstream has no test suite: 14-file tarball, no tests/ dir, no TESTS/check_PROGRAMS in Makefile.am; make check is a no-op",
        }
        up_line = "HMBS_UPSTREAM_TEST_RESULT=" + json.dumps(upstream_marker)
        print(up_line, flush=True)
        self.output.info(up_line)
        if passed != discovered:
            raise ConanException("test_package checks failed")
