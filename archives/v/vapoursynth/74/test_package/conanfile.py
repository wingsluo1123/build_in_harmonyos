#!/usr/bin/env python3
"""Consumer test for vapoursynth 74."""

import os
import shlex
import shutil

from conan import ConanFile
from conan.tools.build import can_run


class VapoursynthTestConan(ConanFile):
    settings = "os", "arch", "compiler", "build_type"
    generators = "VirtualRunEnv"
    test_type = "explicit"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def build(self):
        compilers = self.conf.get("tools.build:compiler_executables", default={}, check_type=dict) or {}
        cc = self._resolve_tool(compilers.get("c"), "clang")
        dep = self.dependencies["vapoursynth"].cpp_info

        exe = os.path.join(self.build_folder, "test_vapoursynth")
        cmd = [
            *self._exec_tool(cc),
            os.path.join(self.source_folder, "test_vapoursynth.c"),
            "-o",
            exe,
        ]
        for include_dir in dep.includedirs:
            cmd.append("-I" + include_dir)
        for lib_dir in dep.libdirs:
            cmd.append("-L" + lib_dir)
        for lib in dep.libs:
            cmd.append("-l" + lib)
        for system_lib in dep.system_libs:
            cmd.append("-pthread" if system_lib == "pthread" else "-l" + system_lib)

        self.run(" ".join(shlex.quote(part) for part in cmd))

    def test(self):
        if can_run(self):
            exe = os.path.join(self.build_folder, "test_vapoursynth")
            self.run(shlex.quote(exe), env="conanrun")

    def _resolve_tool(self, configured, fallback):
        if configured and os.path.exists(configured):
            return configured
        found = shutil.which(fallback)
        if found:
            return found
        if configured:
            bindir = os.path.dirname(configured) if os.path.isabs(configured) else ""
            candidate = os.path.join(bindir, fallback) if bindir else ""
            if candidate and os.path.exists(candidate):
                return candidate
        home_candidate = os.path.join(os.path.expanduser("~"), "usr", "local", "bin", fallback)
        if os.path.exists(home_candidate):
            return home_candidate
        return fallback

    def _exec_tool(self, tool):
        if self._is_script(tool):
            return ["sh", tool]
        return [tool]

    @staticmethod
    def _is_script(path):
        if not path or not os.path.isfile(path):
            return False
        try:
            with open(path, "rb") as handle:
                return handle.read(2) == b"#!"
        except OSError:
            return False
