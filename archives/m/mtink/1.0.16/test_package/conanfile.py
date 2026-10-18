#!/usr/bin/env python3
"""Consumer test for the packaged mtink 1.0.16 executables.

Every assertion runs an installed binary (R34).  Upstream mtink 1.0.16 ships no
automated tests (N = 0, see notes.md), and HarmonyOS PC has no printer device
node, so the assertions drive upstream's own headless entry points - the
argument contract, the built-in printer database and the device bring-up path -
and check the resulting exit codes, exactly like the on-device probe recorded in
notes.md.
"""
import json
import os

from conan import ConanFile
from conan.errors import ConanException


class MtinkTestConan(ConanFile):
    settings = "os", "arch", "compiler", "build_type"
    generators = "VirtualRunEnv"
    exports_sources = "test_mtink.sh"
    test_type = "explicit"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def test(self):
        package_folder = self.dependencies["mtink"].package_folder
        for rel in ("bin/ttink", "bin/mtinkd", "bin/askPrinter",
                    "share/mtink/printer.desc.bldin"):
            path = os.path.join(package_folder, rel)
            if not os.path.isfile(path):
                raise ConanException(f"packaged artefact missing: {path}")

        tmp_base = os.environ.get("TMPDIR") or os.path.expanduser("~/tmp")
        work = os.path.join(tmp_base, "mtink-1.0.16-consumer-test")
        # keep the harness result out of the recipe tree (junk-check/JC)
        result_file = os.path.join(tmp_base, "mtink-1.0.16-test-result.txt")

        # Drive the harness with the platform bash from CONFIG_SHELL (the
        # ohos-aarch64 profile sets CONFIG_SHELL=/data/service/hnp/bin/bash) so
        # the shell semantics are the same on the device and on CI workers.
        shell = (os.environ.get("CONFIG_SHELL")
                 or os.environ.get("SHELL") or "/data/service/hnp/bin/bash")
        script = os.path.join(self.source_folder, "test_mtink.sh")

        run_ok = True
        try:
            self.run(f'"{shell}" "{script}" "{package_folder}" "{result_file}" "{work}"',
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
            "command": f"bash test_mtink.sh <pkg> {result_file} {work}",
            "discovered": discovered,
            "passedCount": passed,
        }
        self.output.info(
            "HMBS_TEST_PACKAGE_RESULT=" + json.dumps(result, ensure_ascii=False))
        if not result["passed"]:
            raise ConanException(
                f"mtink consumer test failed: {passed}/{discovered} assertions "
                "passed (see harness output above)")
