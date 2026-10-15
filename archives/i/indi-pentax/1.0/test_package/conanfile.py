#!/usr/bin/env python3
"""Installed CLI consumer with image-content and error-path assertions."""
import json
import os
import shlex
import sys

from conan import ConanFile
from conan.tools.build import can_run
from conan.tools.env import VirtualRunEnv


class IndiPentaxConsumer(ConanFile):
    settings = "os", "arch", "compiler", "build_type"
    test_type = "explicit"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def generate(self):
        VirtualRunEnv(self).generate()

    def test(self):
        if not can_run(self):
            self.output.warning("CLI consumer execution pending: cross build")
            return
        bindir = os.path.join(self.dependencies["indi-pentax"].package_folder, "bin")
        report = os.path.join(self.build_folder, "consumer-results.json")
        command = [sys.executable, os.path.join(self.recipe_folder, "run_tests.py"),
                   "--bin-dir", bindir, "--report", report]
        self.run(" ".join(shlex.quote(arg) for arg in command), env="conanrun")
        with open(report, encoding="utf-8") as handle:
            result = json.load(handle)
        summary = {key: result[key] for key in ("discovered", "executed", "passed", "failed", "skipped")}
        summary.update(status="passed" if result["failed"] == 0 else "failed", framework="CLI-consumer")
        self.output.info("HMBS_TEST_PACKAGE_RESULT=" + json.dumps(summary))
