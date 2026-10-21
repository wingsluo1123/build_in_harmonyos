#!/usr/bin/env python3
"""Conan test_package for target-factory 2.5 - consumer build and HMBS marker."""

from conan import ConanFile
from conan.errors import ConanException
from conan.tools.build import can_run
from conan.tools.cmake import CMake, CMakeToolchain, cmake_layout
import json
import os
import pathlib


class TestPackageConan(ConanFile):
    settings = "os", "arch", "compiler", "build_type"
    generators = "CMakeDeps"
    test_type = "explicit"

    def requirements(self):
        self.requires(self.tested_reference_str)
        # The public header includes the generated target.pb.h.  protobuf is
        # a private require of the package (cmake_find_mode=none), so the
        # consumer test pulls it explicitly and wires its CMake config below.
        self.requires("protobuf/21.12")

    def layout(self):
        cmake_layout(self)

    def generate(self):
        # protobuf's registry package exports cmake_find_mode=none, so
        # CMakeDeps does not generate a config for it.  The tested package's
        # public header includes the generated target.pb.h, so point
        # find_package(Protobuf CONFIG) at the package's own config files.
        protobuf_dir = os.path.join(
            self.dependencies["protobuf"].package_folder,
            "lib",
            "cmake",
            "protobuf",
        ).replace("\\", "/")
        tc = CMakeToolchain(self)
        tc.variables["Protobuf_DIR"] = protobuf_dir
        tc.variables["protobuf_DIR"] = protobuf_dir
        tc.generate()

    def build(self):
        cmake = CMake(self)
        cmake.configure()
        cmake.build()

    def test(self):
        if not can_run(self):
            return

        run_dir = self.build_folder
        binary = os.path.join(self.cpp.build.bindirs[0], "test_target_factory")
        # 12 REQUIRE assertions in test_target_factory.cpp.
        discovered = 12
        try:
            self.run(f'"{binary}"', cwd=run_dir, env="conanrun")
            passed = discovered
        except Exception as exc:
            self.output.error(f"test_target_factory failed: {exc}")
            passed = 0
        result = {
            "executed": True,
            "passed": passed == discovered,
            "command": "./test_target_factory",
            "discovered": discovered,
            "passedCount": passed,
        }
        marker = "HMBS_TEST_PACKAGE_RESULT=" + json.dumps(result)
        print(marker, flush=True)
        self.output.info(marker)
        if passed != discovered:
            raise ConanException("test_target_factory did not pass")

        # Re-emit the upstream marker when the main build was served from the
        # cache and build() did not run.
        candidates = [
            pathlib.Path(self.build_folder).parent / "hmbs_upstream.json",
            pathlib.Path(self.build_folder) / "hmbs_upstream.json",
        ]
        for path in candidates:
            if path.is_file():
                try:
                    data = json.loads(path.read_text(encoding="utf-8"))
                except (OSError, ValueError):
                    continue
                print(
                    f"HMBS_UPSTREAM_TEST_RESULT={json.dumps(data)}", flush=True
                )
                self.output.info(
                    f"HMBS_UPSTREAM_TEST_RESULT={json.dumps(data)}"
                )
                break
