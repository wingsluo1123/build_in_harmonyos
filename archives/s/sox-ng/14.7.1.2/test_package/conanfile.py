#!/usr/bin/env python3
"""Consumer test for the libSoX NG API and packaged CLI."""

import os
import shlex

from conan import ConanFile
from conan.errors import ConanException
from conan.tools.cmake import CMake, CMakeDeps, CMakeToolchain, cmake_layout


class SoxNgTestConan(ConanFile):
    settings = "os", "arch", "compiler", "build_type"
    generators = "VirtualRunEnv"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def layout(self):
        cmake_layout(self)

    def generate(self):
        CMakeDeps(self).generate()
        CMakeToolchain(self).generate()

    def build(self):
        cmake = CMake(self)
        cmake.configure()
        cmake.build()

    def test(self):
        runtime = self._openmp_runtime_dir()
        consumer = os.path.join(self.build_folder, "bin", "sox_ng_consumer")
        self._run_with_runtime('"{}"'.format(consumer), runtime)

        sox = os.path.join(self.dependencies["sox-ng"].package_folder, "bin", "sox_ng")
        self._run_with_runtime('"{}" --version'.format(sox), runtime)
        wav = os.path.join(self.build_folder, "consumer.wav")
        self._run_with_runtime(
            '"{}" -n -r 8000 -c 1 "{}" synth 0.05 sin 440'.format(sox, wav),
            runtime,
        )
        self._run_with_runtime(
            '"{}" "{}" -n stat'.format(sox, wav),
            runtime,
        )

    def _openmp_runtime_dir(self):
        cache = os.path.join(self.build_folder, "CMakeCache.txt")
        try:
            with open(cache, "r", encoding="utf-8") as stream:
                for line in stream:
                    if line.startswith("SOXNG_OPENMP_RUNTIME:FILEPATH="):
                        runtime = line.split("=", 1)[1].strip()
                        if os.path.isfile(runtime):
                            return os.path.dirname(runtime)
        except OSError as exc:
            raise ConanException("Could not read the consumer CMake cache: {}".format(exc)) from exc
        raise ConanException("Could not resolve the compiler OpenMP runtime for the consumer test")

    def _run_with_runtime(self, command, runtime_dir):
        # The SDK supplies libomp.so as a compiler runtime, outside the
        # device's default loader path. Add its resolved directory only while
        # exercising the consumer and installed CLI on the target device.
        runtime_prefix = 'LD_LIBRARY_PATH={}"${{LD_LIBRARY_PATH:+:$LD_LIBRARY_PATH}}"'.format(
            shlex.quote(runtime_dir)
        )
        self.run("{} {}".format(runtime_prefix, command), env="conanrun")
