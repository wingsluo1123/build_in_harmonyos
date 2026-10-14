#!/usr/bin/env python3
"""Conan test_package for zfs-fuse 0.7.0 — Conan L1 official test.

Delegates the real binary execution to run_smoke.py via self.run (R34):
  1. zpool list CLI smoke (daemonless).
  2. Full user-space pool cycle with the zfs-fuse daemon:
     daemon -> zpool create (file vdev) -> zfs list -> zdb -l -> destroy.

run_smoke.py also re-emits the HMBS_UPSTREAM_TEST_RESULT marker persisted
by the recipe build() into <package>/res/upstream_test_result.json so the
upstream evidence survives Conan cache hits.
"""

import os

from conan import ConanFile
from conan.errors import ConanException
from conan.tools.build import can_run


class ZfsFuseTestConan(ConanFile):
    settings = "os", "arch", "compiler", "build_type"
    test_type = "explicit"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def _dep_bin_dir(self):
        for req in self.dependencies.values():
            name = getattr(getattr(req, "ref", None), "name", "") or ""
            if name != "zfs-fuse":
                continue
            pkg = getattr(req, "package_folder", "") or ""
            cand = os.path.join(pkg, "bin")
            if os.path.isdir(cand):
                return cand
        raise ConanException("zfs-fuse package bin/ not found")

    def test(self):
        if not can_run(self):
            self.output.info("Host cannot run binaries; skipping run test")
            return
        bin_dir = self._dep_bin_dir()
        script = os.path.join(os.path.dirname(__file__), "run_smoke.py")
        self.run("python3 \"%s\" \"%s\"" % (script, bin_dir),
                 env="conanrun")
