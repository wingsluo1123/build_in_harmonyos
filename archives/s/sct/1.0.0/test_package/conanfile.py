#!/usr/bin/env python3
"""Conan test_package — sct 1.0.0.

Upstream has no automated tests. test.c runs the packaged binary end to end
(argument handling, no-display error contract) and asserts the HarmonyOS ELF
platform markers. When an X server (DISPLAY or Xvfb) is available, the test
additionally applies a real temperature and requires rc=0.
"""
import os
import shutil
import subprocess
import time

from conan import ConanFile
from conan.errors import ConanException
from conan.tools.cmake import CMake, cmake_layout


class SctTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"
    generators = "CMakeToolchain"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def layout(self):
        cmake_layout(self)

    def build(self):
        cmake = CMake(self)
        cmake.configure()
        cmake.build()

    def test(self):
        cmake = CMake(self)
        cmake.test()
        test_bin = os.path.join(self.cpp.build.bindirs[0], "test_sct")
        self.run(test_bin, env="conanrun")

        sct_bin = os.path.join(
            self.dependencies["sct"].package_folder,
            self.dependencies["sct"].cpp_info.bindirs[0],
            "sct",
        )
        if not os.path.isfile(sct_bin):
            self.output.warning("sct binary missing: %s" % sct_bin)
            return

        display = os.environ.get("DISPLAY", "").strip()
        xvfb_proc = None
        if not display:
            xvfb = shutil.which("Xvfb")
            if not xvfb:
                self.output.info(
                    "no X server (DISPLAY empty, Xvfb absent): real gamma "
                    "application skipped on this platform; error-contract and "
                    "ELF checks already passed"
                )
                return
            xvfb_proc = subprocess.Popen(
                [xvfb, ":98", "-screen", "0", "1024x768x24", "-ac"],
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
            )
            time.sleep(3)
            display = ":98"

        env = dict(os.environ)
        env["DISPLAY"] = display
        try:
            for temp in ("3000", "6500"):
                proc = subprocess.run(
                    [sct_bin, temp],
                    capture_output=True,
                    text=True,
                    timeout=60,
                    env=env,
                )
                if proc.returncode != 0:
                    raise ConanException(
                        "sct %s failed rc=%d: %s"
                        % (temp, proc.returncode, proc.stderr[-500:])
                    )
            self.output.info("real X display %s: sct 3000/6500 applied" % display)
        finally:
            if xvfb_proc is not None:
                xvfb_proc.terminate()
                time.sleep(1)
