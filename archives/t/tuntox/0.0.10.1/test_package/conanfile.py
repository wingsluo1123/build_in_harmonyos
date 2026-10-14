#!/usr/bin/env python3
"""Conan test_package — tuntox 0.0.10.1 (application/CLI smoke test).

L1 test: run the packaged tuntox binary with `-h`, which triggers
print_version() -> toxcore tox_version_major/minor/patch (real toxcore API)
and help() output, verifying the binary links toxcore/libsodium and runs on
the device. test.sh echoes HMBS_TEST_PACKAGE_RESULT / HMBS_UPSTREAM_TEST_RESULT
evidence markers directly to stdout (numbers come from its real assertion
counting); exit code 0 = all assertions passed.
"""
import os

from conan import ConanFile
from conan.tools.build import can_run


class TuntoxTestConan(ConanFile):
    settings = "os", "arch", "compiler", "build_type"
    generators = "VirtualRunEnv"
    test_type = "explicit"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def test(self):
        if not can_run(self):
            return
        dep = self.dependencies["tuntox"]
        bin_dir = os.path.join(dep.package_folder, "bin")
        tuntox_cmd = os.path.join(bin_dir, "tuntox")
        if not os.path.isfile(tuntox_cmd):
            raise Exception(f"tuntox binary not found: {tuntox_cmd}")
        test_script = os.path.join(self.recipe_folder, "test.sh")
        # Running the packaged tuntox ELF via `sh` (mksh/toybox /bin/sh) fails on
        # OHOS — the packaged ELF binary is not runnable that way, exactly like the
        # wwwoffle precedent ("wwwoffle: inaccessible or not found"). The proven
        # canonical pattern (templates/test_package-executable, keychain, wwwoffle)
        # runs the packaged ELF via bash with its explicit absolute path. Use
        # CONFIG_SHELL (HNP bash by default) instead of the HMBS-injected SHELL=/bin/sh.
        # Run the script from a writable cwd (HMBS-injected TMPDIR) instead of the
        # HMDFS package folder so bash can resolve its working directory.
        shell = os.environ.get("CONFIG_SHELL") or os.environ.get("SHELL") or "/data/service/hnp/bin/bash"
        cwd = os.environ.get("TMPDIR") or os.environ.get("TMP") or self.recipe_folder
        # test.sh runs real assertions on the packaged tuntox binary, echoes
        # HMBS_TEST_PACKAGE_RESULT / HMBS_UPSTREAM_TEST_RESULT markers to
        # stdout, and exits non-zero if any assertion failed (raises Conan error).
        marker_cmd = f'"{shell}" "{test_script}" "{tuntox_cmd}"'
        self.run(marker_cmd, env="conanrun", cwd=cwd)
