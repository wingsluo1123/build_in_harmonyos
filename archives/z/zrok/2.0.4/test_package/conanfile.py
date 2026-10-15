#!/usr/bin/env python3
"""Conan test_package for zrok 2.0.4.

Runs test.sh (universal offline checks plus OHOS-specific checks against the
packaged binary) and emits the HMBS_TEST_PACKAGE_RESULT marker.

The test is *not* a shell, it actually executes the packaged `zrok2` binary:
  - `zrok2 version` must print the ASCII-art banner + "v2.0.4 [2.0.4]"
  - `zrok2 --help` must list the CLI commands and exit 0
  - `zrok2 completion bash` must generate a valid bash completion script
OHOS-specific additions (adaptation-point coverage, not upstream reuse):
  - the packaged Go ELF carries the mandatory OHOS signature section
    (.codesign / .note.ohos) added by binary-sign-tool in build();
  - the cgo binary links against ld-musl-aarch64 (OHOS native libc ABI).
"""

import json
import os
import re
import shutil
import tempfile

from conan import ConanFile
from conan.tools.build import can_run


class ZrokTestConan(ConanFile):
    settings = "os", "arch", "compiler", "build_type"
    generators = "VirtualRunEnv"
    test_type = "explicit"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def test(self):
        package_folder = self.dependencies["zrok"].package_folder
        bin_path = os.path.join(package_folder, "bin", "zrok2")
        assert os.path.isfile(bin_path), "zrok2 binary not found: %s" % bin_path
        with open(bin_path, "rb") as handle:
            assert handle.read(4) == b"\x7fELF", "zrok2 is not an ELF binary"

        is_ohos = str(self.settings.os) == "OHOS"
        if can_run(self):
            test_script = os.path.join(self.recipe_folder, "test.sh")
            shell = os.environ.get("CONFIG_SHELL") or shutil.which("bash") or "bash"
            fd, log_path = tempfile.mkstemp(suffix=".log", prefix="zrok-test-")
            os.close(fd)
            try:
                cmd = '%s "%s" "%s"' % (shell, test_script, bin_path)
                if is_ohos:
                    cmd += " --ohos"
                cmd += ' > "%s" 2>&1' % log_path
                self.run(cmd, env="conanrun")
                with open(log_path, "r", encoding="utf-8", errors="replace") as handle:
                    output = handle.read()
            finally:
                if os.path.exists(log_path):
                    os.unlink(log_path)

            # Parse the real per-check counts from test.sh instead of
            # hard-coding them (P3): HMBS_TEST_SUMMARY: pass=N fail=N.
            match = re.search(r"HMBS_TEST_SUMMARY: pass=(\d+) fail=(\d+)", output)
            if not match:
                raise ConanException(
                    "test.sh did not emit HMBS_TEST_SUMMARY; output:\n%s" % output
                )
            passed = int(match.group(1))
            failed = int(match.group(2))
            discovered = passed + failed
            if failed != 0:
                raise ConanException(
                    "zrok test_package failed: %d/%d checks failed" % (failed, discovered)
                )

            marker = {
                "executed": True,
                "passed": True,
                "command": "bash test.sh <bin/zrok2>" + (" --ohos" if is_ohos else ""),
                "discovered": discovered,
                "passedCount": passed,
            }
            line = "HMBS_TEST_PACKAGE_RESULT=" + json.dumps(marker)
            print(line, flush=True)
            self.output.info(line)
        else:
            self.output.info("zrok2 binary exists and has ELF magic: %s" % bin_path)
