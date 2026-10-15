#!/usr/bin/env python3
"""Conan test_package for yutu 0.10.9 — consumer smoke test of the packaged binary.

yutu is a Go CLI application, not a linkable C/C++ library. The consumer test
runs the packaged ``yutu`` binary and asserts that it really works:

  1. the packaged artefact is an ELF executable
  2. ``yutu version`` exits 0
  3. the version banner reports v0.10.9
  4. the version banner reports the linux/arm64 target
  5. ``yutu help`` exits 0
  6. the help listing exposes the ``video`` resource group
  7. the help listing exposes the ``playlist`` resource group
  8. ``yutu video --help`` (a real subcommand) exits 0
  9. the binary is statically linked (no DT_NEEDED / no interpreter)

This file also republishes the build-phase upstream test evidence
(``share/yutu/upstream-test-result.json``) as ``HMBS_UPSTREAM_TEST_RESULT`` so
that the HMBS evidence gate can read the real upstream suite numbers from the
test_package stdout. The upstream suite itself is NOT executed here: it can only
run where the source tree and module cache live (the recipe's ``build()``), and
this consumer test must not be mistaken for upstream coverage.

File location: archives/y/yutu/0.10.9/test_package/conanfile.py
"""
import json
import os

from conan import ConanFile
from conan.tools.build import can_run


class YutuTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"
    generators = "VirtualRunEnv"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def test(self):
        package_folder = self.dependencies["yutu"].package_folder
        exe_name = "yutu.exe" if str(self.settings.os) == "Windows" else "yutu"
        bin_path = os.path.join(package_folder, "bin", exe_name)
        assert os.path.isfile(bin_path), f"yutu binary not found: {bin_path}"

        if can_run(self):
            test_script = os.path.join(self.recipe_folder, "test.sh")
            # HMBS injects SHELL=/bin/sh; running from a writable cwd avoids the
            # HMDFS getcwd problem seen on HNP bash.
            shell = os.environ.get("SHELL", "/bin/sh")
            cwd = os.environ.get("TMPDIR") or os.environ.get("TMP") or self.recipe_folder
            self.run(f'"{shell}" "{test_script}" "{bin_path}"', env="conanrun", cwd=cwd)
            test_pkg = {
                "executed": True,
                "passed": True,
                "command": f'"{shell}" "{test_script}" "{bin_path}"',
                "discovered": 9,
                "passedCount": 9,
            }
            self.output.info("HMBS_TEST_PACKAGE_RESULT=" + json.dumps(test_pkg, ensure_ascii=False))
        else:
            with open(bin_path, "rb") as binary:
                magic = binary.read(4)
            assert magic == b"\x7fELF", f"yutu is not an ELF binary: {magic!r}"
            self.output.info(f"yutu binary exists and has ELF magic: {bin_path}")

        # ── republish the real upstream suite evidence (build() phase) ──────
        evidence_path = os.path.join(package_folder, "share", "yutu",
                                     "upstream-test-result.json")
        if os.path.isfile(evidence_path):
            with open(evidence_path, "r", encoding="utf-8") as handle:
                upstream = json.load(handle)
            print("HMBS_UPSTREAM_TEST_RESULT=" + json.dumps(upstream, ensure_ascii=False))
        else:
            print("HMBS_UPSTREAM_TEST_RESULT=" + json.dumps({
                "status": "unknown",
                "framework": "go-test",
                "reason": f"build-phase evidence file missing: {evidence_path}",
            }, ensure_ascii=False))
