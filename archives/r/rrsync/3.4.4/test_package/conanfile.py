#!/usr/bin/env python3
"""Conan test_package for rrsync 3.4.4.

Real-invocation tests (R34 — no print-only stubs):
  1. rrsync -h             → usage help, exit 0
  2. sshd guard            → without SSH_ORIGINAL_COMMAND rrsync must die with
                              "Not invoked via sshd" (exit 1)
  3. end-to-end transfer   → client rsync pulls a file through rrsync -ro
                              using an rsh shim that emulates sshd
                              (requires rsync/3.3.0 as test dependency)
"""
import os
import platform
import textwrap

from conan import ConanFile
from conan.tools.build import cross_building


class RrsyncTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"
    test_type = "explicit"

    def requirements(self):
        self.requires(self.tested_reference_str)
        # rsync binary used by the end-to-end transfer test
        self.requires("rsync/3.3.0")

    def test(self):
        if cross_building(self):
            self.output.info("Skip run on cross build (host run executed on device CI)")
            return
        rrsync_bin = os.path.join(
            self.dependencies["rrsync"].cpp_info.bindir, "rrsync")
        rsync_bin = self.dependencies["rsync"].cpp_info.bindir
        self.run("python3 %s -h" % rrsync_bin)
        self.run("PATH=%s:$PATH RRSYNC=%s sh %s" % (rsync_bin, rrsync_bin,
                 os.path.join(self.source_folder, "test_rrsync.sh")))
