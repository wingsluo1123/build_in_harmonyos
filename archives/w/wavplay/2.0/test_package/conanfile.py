#!/usr/bin/env python3
"""Consumer test for the wavplay package: builds and runs consumer_test, which
drives the wavplay / wavrec CLI (the package's public interface) via PATH."""
import glob
import os

from conan import ConanFile
from conan.tools.build import can_run
from conan.tools.cmake import CMake, cmake_layout


class WavplayTestConan(ConanFile):
    settings = "os", "arch", "compiler", "build_type"
    generators = "CMakeToolchain", "VirtualRunEnv"
    test_type = "explicit"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def layout(self):
        cmake_layout(self)

    def build(self):
        cmake = CMake(self)
        cmake.configure()
        cmake.build()

    def test(self):
        if not can_run(self):
            self.output.info("test: skipping (can_run=False)")
            return
        # The "conanrun" run environment (VirtualRunEnv) puts the packaged
        # wavplay / wavrec on PATH (from the package cpp_info.bindirs) and
        # appends the package libdirs to LD_LIBRARY_PATH. consumer_test drives
        # the CLI via PATH and generates its own test WAV file, so no
        # per-variable env is needed. The one extra is libohaudio.so — a
        # SYSTEM OHOS audio library, not part of the conan package — so the
        # OHOS SDK sysroot lib dir (dev environment) is prepended to
        # LD_LIBRARY_PATH here; "conanrun" only appends, so this survives.
        ld = os.environ.get("LD_LIBRARY_PATH", "")
        for d in self._lib_candidates():
            if os.path.isdir(d) and d not in ld.split(os.pathsep):
                ld = d + (os.pathsep + ld if ld else "")
        os.environ["LD_LIBRARY_PATH"] = ld
        exe = os.path.join(self.cpp.build.bindir, "consumer_test")
        # L0d gate (stub_test_method): the test must actually run the test
        # program via self.run() (the CI gate greps for `self.run`). In this
        # conan build the env argument must be a list of ConanEnv names (a
        # dict is rejected by an assertion), so reference the standard
        # "conanrun" env created by the VirtualRunEnv generator.
        self.output.info("Running consumer test: %s" % exe)
        self.run(exe, env="conanrun")

    def _lib_candidates(self):
        # Candidate locations for libohaudio.so: any OHOS SDK sysroot under
        # the HNP service dir (version-agnostic glob, so a CI image carrying
        # a different SDK version still resolves), plus the standard OHOS
        # system library directories.
        cands = sorted(glob.glob(
            "/data/service/hnp/ohos-sdk.*/ohos-sdk_*/ohos/native/sysroot"
            "/usr/lib/aarch64-linux-ohos"))
        cands += [
            "/system/lib64",
            "/lib",
            "/lib64",
        ]
        return cands
