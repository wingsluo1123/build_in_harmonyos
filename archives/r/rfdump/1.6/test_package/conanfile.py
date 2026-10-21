#!/usr/bin/env python3
"""Consumer test for the packaged rfdump 1.6 executable.

Every assertion runs the installed binary (R34): the headless --version/--help
contract, the fail-closed launch without a display server, and the real
application under the GTK3 broadway backend - including the serial-line RFID
bring-up whose device node (/dev/ttyUSB0) does not exist on HarmonyOS PC.

Upstream rfdump 1.6 ships no automated tests (N = 0, see MANIFEST.yml); the
assertions below are the adapted-side tests carried by this package.
"""
import json
import os

from conan import ConanFile
from conan.errors import ConanException


class RfdumpTestConan(ConanFile):
    settings = "os", "arch", "compiler", "build_type"
    generators = "VirtualRunEnv"
    exports_sources = "test_rfdump.sh"
    test_type = "explicit"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def test(self):
        package_folder = self.dependencies["rfdump"].package_folder
        binary = os.path.join(package_folder, "bin", "rfdump")
        if not os.path.isfile(binary):
            raise ConanException(f"packaged binary missing: {binary}")
        data_dir = os.path.join(package_folder, "share", "rfdump")
        if not os.path.isfile(os.path.join(data_dir, "rfdump.ui")):
            raise ConanException(f"packaged GtkBuilder resource missing: {data_dir}")

        tmp_base = os.environ.get("TMPDIR") or os.path.expanduser("~/tmp")
        work = os.path.join(tmp_base, "rfdump-1.6-consumer-test")
        # keep the harness result out of the recipe tree (junk-check/JC)
        result_file = os.path.join(tmp_base, "rfdump-1.6-test-result.txt")

        shell = (os.environ.get("CONFIG_SHELL")
                 or os.environ.get("SHELL") or "/bin/sh")
        script = os.path.join(self.source_folder, "test_rfdump.sh")

        run_ok = True
        try:
            self.run(f'"{shell}" "{script}" "{binary}" "{result_file}" "{work}"',
                     env="conanrun")
        except Exception:
            run_ok = False

        discovered = 0
        passed = 0
        if os.path.isfile(result_file):
            with open(result_file, "r", encoding="utf-8") as handle:
                for line in handle:
                    parts = line.split()
                    if len(parts) == 2 and parts[0] == "discovered":
                        discovered = int(parts[1])
                    elif len(parts) == 2 and parts[0] == "passed":
                        passed = int(parts[1])
        result = {
            "executed": True,
            "passed": bool(run_ok and discovered > 0 and passed == discovered),
            "command": f"sh test_rfdump.sh <pkg>/bin/rfdump {result_file} <work>",
            "discovered": discovered,
            "passedCount": passed,
        }
        self.output.info(
            "HMBS_TEST_PACKAGE_RESULT=" + json.dumps(result, ensure_ascii=False))
        if not result["passed"]:
            raise ConanException(
                f"rfdump consumer test failed: {passed}/{discovered} assertions "
                "passed (see harness output above)")
