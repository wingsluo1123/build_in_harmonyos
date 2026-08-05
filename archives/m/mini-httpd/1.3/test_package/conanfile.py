#!/usr/bin/env python3
"""Conan test_package for mini-httpd 1.3 — executes mini_httpd -V smoke test."""
import os
import subprocess

from conan import ConanFile
from conan.errors import ConanException


class MinihttpdTestConan(ConanFile):
    settings = "os", "arch"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def test(self):
        # Locate the packaged binary via Conan dependency info.
        bin_dir = self.dependencies["mini-httpd"].cpp_info.bindirs[0]
        mini_httpd = os.path.join(bin_dir, "mini_httpd")
        self.output.info(f"mini_httpd binary: {mini_httpd}")

        if not os.path.isfile(mini_httpd):
            raise ConanException(f"mini_httpd binary not found at {mini_httpd}")

        # Real smoke test: test_smoke.sh executes mini_httpd -V, verifies
        # exit code and version output, and exits non-zero on failure.
        script = os.path.join(os.path.dirname(os.path.abspath(__file__)), "test_smoke.sh")
        self.run(f"sh {script} {mini_httpd}", env="conanrun")

        # Cross-check the version output with subprocess, checking returncode
        # and handling timeout / missing binary explicitly.
        try:
            result = subprocess.run(
                [mini_httpd, "-V"],
                capture_output=True,
                timeout=10,
            )
        except subprocess.TimeoutExpired:
            raise ConanException("mini_httpd -V timed out after 10s")
        except FileNotFoundError:
            raise ConanException(f"cannot execute mini_httpd at {mini_httpd}")

        stdout = result.stdout.decode(errors="replace").strip()
        stderr = result.stderr.decode(errors="replace").strip()
        combined = f"{stdout}\n{stderr}".strip()
        self.output.info(f"mini_httpd -V exit={result.returncode} output={combined}")

        if result.returncode != 0:
            raise ConanException(
                f"mini_httpd -V returned non-zero exit code {result.returncode}: {combined}"
            )

        expected = "mini_httpd/1.30 26Oct2018"
        if expected not in combined:
            raise ConanException(
                f"mini_httpd -V output does not contain '{expected}': got '{combined}'"
            )