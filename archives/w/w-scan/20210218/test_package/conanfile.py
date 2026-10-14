#!/usr/bin/env python3
"""Consumer smoke test for w_scan 20210218."""

import os
import shutil

from conan import ConanFile
from conan.errors import ConanException
from conan.tools.build import can_run
from conan.tools.files import copy, load


class WScanTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"
    generators = "VirtualRunEnv"
    test_type = "explicit"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def export_sources(self):
        copy(
            self,
            "test_w_scan.sh",
            self.recipe_folder,
            self.export_sources_folder,
        )

    def test(self):
        if not can_run(self):
            return

        script = os.path.join(self.source_folder, "test_w_scan.sh")
        result = os.path.join(self.build_folder, "test-w-scan-result.txt")
        candidates = [
            os.environ.get("CONFIG_SHELL"),
            "/data/service/hnp/bin/bash",
            shutil.which("bash"),
            shutil.which("sh"),
        ]
        shell = next(
            (candidate for candidate in candidates if candidate and os.path.isfile(candidate)),
            None,
        )
        if not shell:
            raise ConanException("a POSIX shell is required to run the w_scan smoke test")

        self.run(f'"{shell}" "{script}" "{result}"', env="conanrun")
        output = load(self, result).strip()
        if output != "w_scan smoke: 8 passed":
            raise ConanException(f"unexpected w_scan smoke test result: {output!r}")
