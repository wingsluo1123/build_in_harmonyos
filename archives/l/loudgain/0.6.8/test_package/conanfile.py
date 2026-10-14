#!/usr/bin/env python3
"""Conan test_package for loudgain 0.6.8.

Runs test_loudgain.sh against the *installed* loudgain executable,
exercising the full consumer workflow: version banner, WAV generation
(pure shell, no external fixture), an EBU R128 scan via FFmpeg decode +
libebur128 analysis, ReplayGain tag writing via TagLib (experimental WAV
ID3 chunk), structural file-growth verification, NUL-stripped byte-level
verification of the written frames (toybox grep skips binary files), and
a tag re-read second run.
Emits the CI summary markers.
"""
import json
import os
import shlex

from conan import ConanFile
from conan.errors import ConanException


class LoudgainTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"
    test_type = "explicit"
    generators = "VirtualRunEnv"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def _bash(self):
        for candidate in (
            os.environ.get("CONFIG_SHELL"),
            "/storage/Users/currentUser/.harmonybrew/bin/bash",
            "/data/service/hnp/bin/bash",
            "/bin/bash",
        ):
            if candidate and os.path.isfile(candidate):
                return candidate
        return "sh"

    def test(self):
        dep = self.dependencies["loudgain"]
        bindir = dep.cpp_info.bindirs[0]
        here = os.path.dirname(os.path.abspath(__file__))
        script = os.path.join(here, "test_loudgain.sh")

        inner = f'LOUDGAIN_BINDIR={shlex.quote(bindir)} sh {shlex.quote(script)}'
        if self.settings.os == "OHOS":
            cmd = f"{shlex.quote(self._bash())} -c {shlex.quote(inner)}"
        else:
            cmd = inner

        rc = self.run(cmd, ignore_errors=True, env="conanrun")
        print("HMBS_TEST_PACKAGE_RESULT=" + json.dumps({
            "executed": True,
            "passed": rc == 0,
            "command": "test_loudgain.sh",
        }))
        if rc != 0:
            raise ConanException(f"loudgain consumer test failed (rc={rc})")
