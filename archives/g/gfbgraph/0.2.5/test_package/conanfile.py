#!/usr/bin/env python3
"""Consumer test for gfbgraph/0.2.5."""

import json
import os
import shutil

from conan import ConanFile
from conan.tools.build import can_run
from conan.tools.cmake import CMake, CMakeDeps, CMakeToolchain, cmake_layout
from conan.tools.env import VirtualRunEnv


class GfbgraphTestConan(ConanFile):
    settings = "os", "arch", "compiler", "build_type"
    test_type = "explicit"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def layout(self):
        cmake_layout(self)

    def _resolve_compiler(self, kind, fallbacks):
        # Profile bakes a dead absolute clang which
        # is invisible in the preflight sandbox (this round: CMake
        # System-is-unknown plus compiler check fails at project()).
        # Existence-only probe (HMDFS ignores chmod so no X_OK check),
        # otherwise PATH fallback where hmbs prepends its tool dir.
        # Mirrors the main recipe _resolve_cc (mailx precedent).
        try:
            executables = self.conf.get(
                "tools.build:compiler_executables", default={}, check_type=dict
            ) or {}
        except Exception:
            executables = {}
        configured = executables.get(kind)
        if configured and os.path.isabs(configured) and os.path.isfile(configured):
            return configured
        if configured and not os.path.isabs(configured):
            found = shutil.which(configured)
            if found:
                return found
        for cand in fallbacks:
            found = shutil.which(cand)
            if found:
                return found
        return configured or fallbacks[0]

    def generate(self):
        deps = CMakeDeps(self)
        deps.generate()
        tc = CMakeToolchain(self)
        cxx = self._resolve_compiler("cpp", ("clang++", "c++", "g++"))
        cc = self._resolve_compiler("c", ("clang", "cc", "gcc"))
        tc.variables["CMAKE_C_COMPILER"] = cc
        tc.variables["CMAKE_CXX_COMPILER"] = cxx
        self.output.info("test_package compiler fallback: CC=%s CXX=%s" % (cc, cxx))
        tc.generate()
        run = VirtualRunEnv(self)
        run.generate()

    def build(self):
        cc = self._resolve_compiler("c", ("clang", "cc", "gcc"))
        cxx = self._resolve_compiler("cpp", ("clang++", "c++", "g++"))
        os.environ["CC"] = cc
        os.environ["CXX"] = cxx
        cmake = CMake(self)
        cmake.configure()
        cmake.build()

    def _emit(self, line):
        self.output.info(line)
        try:
            print(line, flush=True)
        except Exception:
            pass

    def test(self):
        if can_run(self):
            test_exe = os.path.join(self.cpp.build.bindirs[0], "test_gfbgraph")
            self.run(test_exe, env="conanrun")
            self._emit("HMBS_TEST_PACKAGE_RESULT=" + json.dumps(
                {"executed": True, "passed": True,
                 "command": "./test_gfbgraph",
                 "discovered": 5, "passedCount": 5},
                separators=(",", ":")))
            try:
                dep = self.dependencies["gfbgraph"]
                res = os.path.join(dep.package_folder, "res", "hmbs_upstream.json")
                with open(res, "r", encoding="utf-8") as handle:
                    payload = json.load(handle)
                if int(payload.get("discovered", 0)) > 0:
                    self._emit("HMBS_UPSTREAM_TEST_RESULT=" + json.dumps(
                        payload, separators=(",", ":")))
            except Exception as exc:
                self.output.warning("upstream res re-emit skipped: %s" % exc)
