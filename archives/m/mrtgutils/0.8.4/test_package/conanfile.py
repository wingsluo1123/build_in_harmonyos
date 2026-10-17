#!/usr/bin/env python3
"""Consumer test for the packaged mrtgutils command set."""

import os
import shutil

from conan import ConanFile
from conan.errors import ConanException
from conan.tools.files import load


class MrtgutilsTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"
    generators = "VirtualRunEnv"
    test_type = "explicit"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def test(self):
        dep = self.dependencies[self.tested_reference_str]
        bindir = os.path.join(dep.package_folder, "bin")
        for program in (
            "mrtg-load",
            "mrtg-uptime",
            "mrtg-ip-acct",
            "mrtg-apache",
            "mrtg-sensors",
        ):
            binary = os.path.join(bindir, program)
            if not os.path.isfile(binary):
                raise ConanException(f"packaged binary missing: {binary}")
            if not os.access(binary, os.X_OK):
                raise ConanException(f"packaged binary is not executable: {binary}")

        script = os.path.join(self.source_folder, "test_mrtgutils.sh")
        if not os.path.isfile(script):
            raise ConanException(f"consumer test script missing: {script}")

        candidates = (
            os.environ.get("CONFIG_SHELL"),
            "/data/service/hnp/bin/bash",
            shutil.which("bash"),
            shutil.which("sh"),
        )
        shell = next(
            (candidate for candidate in candidates
             if candidate and os.path.isfile(candidate)),
            None,
        )
        if not shell:
            raise ConanException("a POSIX shell is required to run the mrtgutils test")

        work = os.path.join(self.build_folder, "mrtgutils-consumer")
        result = os.path.join(self.build_folder, "mrtgutils-result.txt")
        self.run(
            f'MRTGUTILS_BIN="{bindir}" MRTGUTILS_WORK="{work}" '
            f'MRTGUTILS_RESULT="{result}" "{shell}" "{script}"',
            env="conanrun",
        )
        summary = load(self, result).strip()
        if summary != "mrtgutils smoke: 8 passed":
            raise ConanException(f"unexpected mrtgutils consumer test result: {summary!r}")
