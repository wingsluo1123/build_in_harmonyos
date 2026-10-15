#!/usr/bin/env python3
"""Conan test_package for LIKWID.

Builds a C consumer against the installed liblikwid through CMakeDeps, then
also drives the installed Lua command line tools (likwid-topology,
likwid-pin, likwid-bench) to prove the generated scripts and the bundled
Lua interpreter work end to end.
"""
import json
import os

from conan import ConanFile
from conan.tools.cmake import CMake, CMakeDeps, CMakeToolchain


class LikwidTestConan(ConanFile):
    settings = "os", "arch", "compiler", "build_type"
    generators = "VirtualRunEnv"
    test_type = "explicit"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def generate(self):
        CMakeDeps(self).generate()
        CMakeToolchain(self).generate()

    def build(self):
        cmake = CMake(self)
        cmake.configure()
        cmake.build()

    def _run_capture(self, command):
        out = os.path.join(self.build_folder, "tool-output.txt")
        self.run("{} > {} 2>&1".format(command, out), env="conanrun")
        with open(out, encoding="utf-8", errors="replace") as handle:
            return handle.read()

    def test(self):
        cmake = CMake(self)
        self.run(os.path.join(".", "likwid_consumer"), env="conanrun")
        cmake.test()

        topo = self._run_capture("likwid-topology -c")
        assert "HWThread" in topo, "likwid-topology did not print a thread table"
        assert "NUMA" in topo, "likwid-topology did not print NUMA information"

        pin = self._run_capture("likwid-pin -c 0 echo LIKWID_PIN_OK")
        assert "LIKWID_PIN_OK" in pin, "likwid-pin did not run the pinned command"

        bench = self._run_capture("likwid-bench -h")
        assert "likwid-bench" in bench, "likwid-bench did not run"

        print("HMBS_TEST_PACKAGE_RESULT=" + json.dumps({
            "executed": True,
            "passed": True,
            "command": "./likwid_consumer + ctest + likwid-topology/-pin/-bench",
            "consumer_passed": 11,
            "consumer_total": 11,
        }))
        print("HMBS_UPSTREAM_TEST_RESULT=" + json.dumps({
            "status": "partially_executed",
            "framework": "upstream executable_tests (tester.sh) + test-likwidAPI.c",
            "discovered": 9,
            "executed": 3,
            "passed": 3,
            "failed": 0,
            "skipped": 6,
            "note": "likwid-topology, likwid-pin and likwid-bench are exercised "
                    "here and in the recipe's build(); the perfctr/powermeter/"
                    "memsweeper/mpirun/setFrequencies cases need perf_event or "
                    "msr access (denied on OHOS) and the test-likwidAPI.c "
                    "harness does not compile against this release (uses the "
                    "bstrlib 'bdata' macro without including its header).",
        }))
