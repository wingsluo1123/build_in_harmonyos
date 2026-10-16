#!/usr/bin/env python3
"""Consumer tests for the installed tsdecrypt command."""

import os
import platform
import re
import shutil
import subprocess
from io import StringIO

from conan import ConanFile
from conan.errors import ConanException
from conan.tools.layout import basic_layout


class TsdecryptTestConan(ConanFile):
    settings = "os", "arch", "compiler", "build_type"
    generators = "VirtualRunEnv"
    test_type = "explicit"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def layout(self):
        basic_layout(self)

    @staticmethod
    def _tool_output(*args):
        output = subprocess.check_output(args)
        return output.decode("utf-8", errors="replace") if isinstance(output, bytes) else output

    def test(self):
        package = self.dependencies[self.tested_reference_str].package_folder
        binary = os.path.join(package, "bin", "tsdecrypt")
        if not os.path.isfile(binary):
            raise ConanException("packaged tsdecrypt executable is missing")

        readelf = (
            shutil.which("llvm-readelf")
            or shutil.which("readelf")
            or "/data/service/hnp/bin/llvm-readelf"
        )
        sections = self._tool_output(readelf, "-S", binary)
        dynamic = self._tool_output(readelf, "-d", binary)
        if sections.count(".codesign") != 1:
            raise ConanException("consumer found an unsigned or multiply signed executable")
        if "RPATH" in dynamic or "RUNPATH" in dynamic or ".conan2" in dynamic:
            raise ConanException("consumer found a non-relocatable executable")
        if "libdvbcsa.so" not in dynamic:
            raise ConanException("consumer did not find the declared libdvbcsa runtime edge")

        if not (os.path.isdir("/system/bin") and platform.machine() in ("aarch64", "arm64")):
            self.output.warning(
                "Target runtime matrix skipped on the cross-build host; "
                "it is mandatory in the native HarmonyOS create run"
            )
            return
        version_output = StringIO()
        self.run(
            '"{}" --version'.format(binary),
            env="conanrun",
            stdout=version_output,
        )
        version_line = version_output.getvalue().strip()
        expected_version = (
            r"tsdecrypt v10\.0 \(release, build "
            r"\d{4}-\d{2}-\d{2}_\d{2}:\d{2} libdvbcsa\)"
        )
        if re.fullmatch(expected_version, version_line) is None:
            raise ConanException(
                "consumer found an unexpected tsdecrypt version line: {!r}".format(
                    version_line
                )
            )
        self.run(
            'python3 "{}" "{}"'.format(
                os.path.join(self.source_folder, "test_rtp_input.py"), binary
            ),
            env="conanrun",
        )
