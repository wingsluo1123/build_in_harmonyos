#!/usr/bin/env python3
"""Conan test_package — zerolang 0.3.4 consumer smoke test.

The `zero` compiler is a CLI tool, so the consumer test drives it like the
upstream README/Homebrew test does: `zero --version` must report 0.3.4, and a
hello-world source must `check` and `run` to produce the expected output.
Emits HMBS_TEST_PACKAGE_RESULT with the real assertion count (2 checks in
test.sh: version string match, and hello-world run output match).

Then re-emits the upstream native-smoke result persisted by the main recipe
into package res/upstream_test_result.json (HMBS marker chain): test_package
runs on every preflight even when conan skips a cached build(), so the
HMBS_UPSTREAM_TEST_RESULT evidence is always present.
"""
import json
import os
import shutil

from conan import ConanFile
from conan.errors import ConanException


class ZerolangTestConan(ConanFile):
    settings = "os", "arch", "compiler", "build_type"
    test_type = "explicit"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def test(self):
        dep = self.dependencies["zerolang"]
        bin_path = os.path.join(dep.package_folder, "bin", "zero")
        if not os.path.isfile(bin_path):
            raise ConanException(
                f"zero binary not found at {bin_path} — package bin not populated")
        script = os.path.join(self.source_folder, "test.sh")
        # HMBS injects SHELL=/bin/sh; never hard-code `bash` (the HNP bash
        # under /data/service/hnp/bin/bash cannot getcwd on the HMFS working
        # directory — [shell_getcwd]).
        shell = os.environ.get("SHELL", "/bin/sh")
        # Exec-capable + writable work dir for `zero run`. zero run compiles
        # the hello-world into <work>/.zero/out/<base>.run-<pid> and then
        # executes it via execv (run_executable_artifact -> _exit(127)).
        #
        # Root cause of the earlier persistent `zero run: Permission denied`
        # (rc=127, execv EACCES): `zero run`'s DEFAULT (direct) backend writes
        # a static absolute-addressed ET_EXEC image via z_elf_write_executable64
        # (no clang, no -no-pie/-pie flag). HarmonyOS (Linux kernel,
        # PIE-mandatory, like Android) rejects execve of that non-PIE ET_EXEC
        # with EACCES regardless of the directory it lives in — verified by
        # moving the work dir across TMPDIR, the test_package source dir, and
        # this conan-home tree: identical "Permission denied". The recipe's
        # smoke/zero binaries are clang PIE (ET_DYN) and exec fine from the
        # same conan-home tree, ruling out any noexec-mount theory.
        #
        # Fix: test.sh runs the hello-world via the LLVM backend
        # (`zero run --backend llvm`), which produces a clang-linked executable;
        # the main recipe's _patch_no_pie makes that clang link PIE (ET_DYN),
        # which OHOS accepts. The work dir is kept under the writable
        # conan-home package tree (package_folder's parent).
        dep_pkg = self.dependencies["zerolang"].package_folder
        exec_root = os.path.dirname(dep_pkg)  # conan-home/p/b/<pkg_id>/ (exec+write)
        work_root = os.path.join(exec_root, "test_package_run")
        os.makedirs(work_root, exist_ok=True)
        cwd = work_root
        # Defensive: force `zero run`'s internal LLVM/CC toolchain to exactly
        # the compiler that produced the runnable `zero` + smoke binaries so
        # the hello-world exe is built against the known-good native clang.
        # Mirror the main recipe's _cc() priority (CC env > conf
        # tools.build:compiler_executables.c > PATH cc > clang) so ZERO_LLVM_CLANG
        # always resolves to the device's clang, which the LLVM backend uses
        # (`--backend llvm`) to compile the runtime object and link the PIE exe.
        cc = os.environ.get("CC")
        if not cc:
            try:
                cc_conf = self.conf.get("tools.build:compiler_executables",
                                        default={})
            except Exception:
                cc_conf = {}
            if isinstance(cc_conf, dict) and cc_conf.get("c"):
                cc = cc_conf["c"]
        if not cc:
            cc = shutil.which("cc") or shutil.which("clang") or "clang"
        prefix = f"ZERO_LLVM_CLANG='{cc}' "
        self.run(f'{prefix}"{shell}" "{script}" "{bin_path}" "{cwd}"',
                 env="conanrun", cwd=cwd)

        upstream_json = os.path.join(
            dep.package_folder, "res", "upstream_test_result.json")
        if not os.path.isfile(upstream_json):
            raise ConanException(
                f"upstream_test_result.json missing from package res/: "
                f"{upstream_json} — upstream tests did not run during "
                f"build(); refusing to pass silently")
        with open(upstream_json, "r", encoding="utf-8") as fh:
            upstream = json.load(fh)
        self.output.info("HMBS_UPSTREAM_TEST_RESULT=" +
                         json.dumps(upstream, ensure_ascii=False))
        print("HMBS_UPSTREAM_TEST_RESULT=" +
              json.dumps(upstream, ensure_ascii=False), flush=True)
