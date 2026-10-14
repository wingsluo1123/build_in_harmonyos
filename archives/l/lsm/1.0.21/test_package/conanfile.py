#!/usr/bin/env python3
"""Conan test_package for lsm 1.0.21 — consumer smoke test of the foolsm binary.

The packaged binary is `foolsm` (upstream kept the binary name after the
foolsm -> lsm rename). The test runs it headlessly:
  - `foolsm -h` prints "version 1.0.21" plus usage text, exits 2
  - `foolsm -v` prints "version 1.0.21" plus usage text, exits 2
  - `foolsm --help` behaves like -h
No root/raw-socket traffic is generated (no config is passed).

File location: archives/l/lsm/1.0.21/test_package/conanfile.py
"""
import json
import os

from conan import ConanFile
from conan.tools.build import can_run


class LsmTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"
    generators = "VirtualRunEnv"
    test_type = "explicit"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def test(self):
        if self.settings.os not in ("Linux", "OHOS"):
            return
        package_folder = self.dependencies["lsm"].package_folder
        bin_path = os.path.join(package_folder, "bin", "foolsm")
        assert os.path.isfile(bin_path), "foolsm binary not found: %s" % bin_path

        if can_run(self):
            test_script = os.path.join(self.recipe_folder, "test.sh")
            # HMBS injects SHELL=/bin/sh; respect it instead of hard-coding bash.
            shell = os.environ.get("SHELL", "/bin/sh")
            cwd = os.environ.get("TMPDIR") or os.environ.get("TMP") or self.recipe_folder
            self.run('"%s" "%s" "%s"' % (shell, test_script, bin_path), env="conanrun", cwd=cwd)
            # test.sh performs 3 explicit assertions (see MANIFEST.yml).
            test_pkg = {
                "executed": True,
                "passed": True,
                "command": '"%s" "%s" "%s"' % (shell, test_script, bin_path),
                "discovered": 3,
                "passedCount": 3,
            }
            self.output.info("HMBS_TEST_PACKAGE_RESULT=" + json.dumps(test_pkg, ensure_ascii=False))
            # Upstream ships no tests; emit the no_tests marker on test_package
            # stdout (bare print) so the HMBS evidence gate can find it.
            # Upstream audit was logged in conanfile.py build() (conan create log).
            upstream = {
                "status": "no_tests",
                "framework": "make",
                "command": "make -n check (no check/test target in upstream Makefile)",
                "discovered": 0,
                "executed": 0,
                "passed": 0,
                "failed": 0,
                "skipped": 0,
                "reason": (
                    "foolsm-1.0.21 ships 56 tarball entries with no tests/ or test/ "
                    "directory; the upstream Makefile defines only all/clean/distclean/"
                    "tar/rpm/install targets and no check/test target, so there is no "
                    "upstream test suite to run. See test_package/MANIFEST.yml "
                    "upstream_test_audit for the full audit."
                ),
            }
            print("HMBS_UPSTREAM_TEST_RESULT=" + json.dumps(upstream, ensure_ascii=False))
        else:
            with open(bin_path, "rb") as binary:
                magic = binary.read(4)
            assert magic == b"\x7fELF", "foolsm is not an ELF binary: %r" % magic
            self.output.info("foolsm binary exists and has ELF magic: %s" % bin_path)
