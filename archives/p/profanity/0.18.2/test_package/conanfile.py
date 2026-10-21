#!/usr/bin/env python3
"""Conan test_package -- profanity 0.18.2 static CLI verification.

profanity is a terminal tool, not a library. The device executable-
signature gate denies execve of the installed ELF with EPERM (shell 126)
both from the conan cache and from a relocated copy (preflight
2026-10-19, two rounds; qastools/1.4.0 P6 + gammastep EPERM precedent),
so this test builds the test_profanity helper by invoking the C compiler
directly and statically verifies the installed binary: valid 64-bit
AArch64 ELF header plus the embedded 0.18.2 version string. Emits the
HMBS_TEST_PACKAGE_RESULT hard-gate marker with the real assertion count
from test.c (2 checks).

No CMake: the vanilla CMake configure dies on OHOS with
"System is unknown to cmake ... CMAKE_C_COMPILER:
/data/service/hnp/bin/clang" (stale profile compiler path + unknown
HarmonyOS platform file). A single-file C helper needs no build
system; direct $CC invocation sidesteps both issues deterministically.
"""
import json
import os
import shutil

from conan import ConanFile
from conan.tools.build import can_run
from conan.tools.env import Environment
from conan.tools.layout import basic_layout


class ProfanityTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def layout(self):
        basic_layout(self)

    def _ensure_writable_tmp(self):
        """E002: OHOS /tmp 为 erofs 只读挂载，clang 临时文件会报
        "unable to make temporary file: No such file or directory"。

        优先复用 hmbs 注入的任务级临时目录（HMBS_TMPDIR/TMPDIR/TMP/TEMP
        及 HMBS_PLATFORM_CAPABILITIES.tmpdir），缺失时回退 $HOME/tmp 与
        build_folder 下隔离目录；确保目录存在且可写后同步到 os.environ。
        （backuppc-rsync/3.1.3.0 + zydis/4.1.1 同款先例；self.run(env=
        "conanbuild") 会隔离宿主 TMPDIR，所以 generate() 还需经
        Environment 写入 conanbuild，build() 另做命令级显式导出。）
        """
        candidates = []
        for key in ("HMBS_TMPDIR", "TMPDIR", "TMP", "TEMP",
                    "HMBS_AUTOCONF_MKTEMP_FALLBACK"):
            val = os.environ.get(key)
            if val and val not in candidates:
                candidates.append(val)
        cap = os.environ.get("HMBS_PLATFORM_CAPABILITIES")
        if cap:
            try:
                import json as _json
                tmpdir = _json.loads(cap).get("tmpdir")
                if tmpdir and tmpdir not in candidates:
                    candidates.insert(0, tmpdir)
            except Exception:
                pass
        home = os.path.expanduser("~")
        if home and home != "~":
            home_tmp = os.path.join(home, "tmp")
            if home_tmp not in candidates:
                candidates.append(home_tmp)
        try:
            bf = getattr(self, "build_folder", None)
            if bf:
                local_tmp = os.path.join(bf, "tmp")
                if local_tmp not in candidates:
                    candidates.append(local_tmp)
        except Exception:
            pass
        for cand in candidates:
            try:
                os.makedirs(cand, exist_ok=True)
                probe = os.path.join(cand, ".hmbs_write_probe")
                with open(probe, "w") as handle:
                    handle.write("ok")
                os.remove(probe)
                os.environ["TMPDIR"] = cand
                os.environ["TMP"] = cand
                os.environ["TEMP"] = cand
                return cand
            except Exception:
                continue
        return None

    def generate(self):
        tmpdir = self._ensure_writable_tmp()
        if tmpdir:
            env = Environment()
            env.define("TMPDIR", tmpdir)
            env.define("TMP", tmpdir)
            env.define("TEMP", tmpdir)
            env.vars(self, scope="build").save_sh("hmbs_tmpdir")

    def _resolve_c_compiler(self):
        try:
            comp_exes = self.conf.get(
                "tools.build:compiler_executables", default={},
                check_type=dict) or {}
        except Exception:
            comp_exes = {}
        configured = comp_exes.get("c", "") if isinstance(comp_exes, dict) else ""
        if configured and os.path.isfile(configured):
            return configured
        for name in ("clang", "cc", "gcc"):
            found = shutil.which(name)
            if found:
                return found
        home_bin = os.path.join(os.path.expanduser("~"), "usr", "local", "bin")
        for name in ("clang", "cc", "gcc"):
            cand = os.path.join(home_bin, name)
            if os.path.isfile(cand):
                return cand
        return configured or "cc"

    def build(self):
        tmpdir = self._ensure_writable_tmp()
        cc = self._resolve_c_compiler()
        self.output.info("test_package c compiler: '%s'" % cc)
        if tmpdir:
            self.output.info("test_package writable TMPDIR: '%s'" % tmpdir)
        else:
            # 宁缺毋假：无可写临时目录时如实告警，不伪造通过。
            self.output.warning(
                "test_package: no writable TMPDIR found; clang may fail "
                "with 'unable to make temporary file'")
        src = os.path.join(self.source_folder, "test.c")
        out = os.path.join(self.build_folder, "test_profanity")
        # conanbuild 聚合会隔离宿主 TMPDIR/OS 环境（本轮真机证据：
        # HMBS 注入的 runtime/tmp 未透传，clang 报 unable to make
        # temporary file），所以把可写目录以 VAR="value" 前缀显式带入
        # 编译命令；generate() 的 Environment 写入是第二重保障。
        prefix = ""
        if tmpdir:
            prefix = 'TMPDIR="%s" TMP="%s" TEMP="%s" ' % (
                tmpdir, tmpdir, tmpdir)
        self.run(prefix + '"%s" "%s" -o "%s"' % (cc, src, out),
                 env="conanbuild")

    def test(self):
        if can_run(self):
            dep = self.dependencies["profanity"]
            profanity_bin = os.path.join(dep.package_folder, "bin", "profanity")
            test_bin = os.path.join(self.build_folder, "test_profanity")
            # No exec of the installed ELF: the device signature gate denies
            # execve with EPERM (shell 126) both from the conan cache and
            # from a copy relocated into the build tree (preflight
            # 2026-10-19, two rounds). test_profanity only READS the binary
            # (ELF header + version string), so the package path is used
            # directly -- no copy, no chmod, no exec.
            test_cmd = f'{test_bin} "{profanity_bin}"'
            # 2 explicit static checks in test.c (ELF header + version string)
            test_pkg = {
                "executed": True,
                "passed": True,
                "command": test_cmd,
                "discovered": 2,
                "passedCount": 2,
            }
            try:
                self.run(test_cmd, env="conanrun")
            except Exception as exc:
                # Honest failure count: the helper failed before completing
                # both static checks. passedCount must be < discovered when
                # passed is false; never leave the success count in place
                # on the failure path.
                test_pkg["passed"] = False
                test_pkg["passedCount"] = 0
                self.output.info(
                    "HMBS_TEST_PACKAGE_RESULT=" + json.dumps(test_pkg, ensure_ascii=False)
                )
                raise
            self.output.info(
                "HMBS_TEST_PACKAGE_RESULT=" + json.dumps(test_pkg, ensure_ascii=False)
            )
