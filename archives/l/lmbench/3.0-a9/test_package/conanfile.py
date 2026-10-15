#!/usr/bin/env python3
"""test_package for lmbench — runs the packaged benchmarks and asserts real output (R34).

test_lmbench.sh receives the package folder, a writable work dir and the
compiler path.  It verifies the package layout, obtains the machine timing
parameters with the packaged enough/timing_o/loop_o helpers (same interface
as upstream's scripts/config-run), runs a real benchmark subset and asserts
labels + positive values, checks the platform capability statement of
lat_rpc, rejects an unknown benchmark mode (negative control) and compiles a
consumer C program against the packaged headers and libmbench.a.  The tests
fail if the package is missing or broken (CI L1e sabotages bin/ to prove the
dependency).
"""

import os
import shutil
import tempfile

from conan import ConanFile
from conan.errors import ConanException
from conan.tools.build import can_run


class LmbenchTestConan(ConanFile):
    settings = "os", "arch", "compiler", "build_type"
    generators = "VirtualRunEnv"
    test_type = "explicit"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def test(self):
        if not can_run(self):
            return

        pkg = self.dependencies["lmbench"].package_folder
        if not os.path.isfile(os.path.join(pkg, "bin", "lat_syscall")):
            raise ConanException("lmbench bin/lat_syscall not found at: {0}".format(pkg))

        compilers = self.conf.get(
            "tools.build:compiler_executables", default={}, check_type=dict
        )
        cc = compilers.get("c", "clang") if compilers else "clang"

        tmpdir = os.environ.get("TMPDIR")
        if not tmpdir:
            tmpdir = os.path.join(os.environ.get("HOME", "/tmp"), "tmp")
        os.makedirs(tmpdir, exist_ok=True)
        workdir = tempfile.mkdtemp(prefix="lmbench-test-", dir=tmpdir)
        try:
            self.run(
                'sh test_lmbench.sh "{0}" "{1}" "{2}"'.format(pkg, workdir, cc),
                env="conanrun",
            )
        finally:
            shutil.rmtree(workdir, ignore_errors=True)
