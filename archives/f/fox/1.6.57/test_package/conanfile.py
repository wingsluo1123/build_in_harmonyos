#!/usr/bin/env python3
"""Installed-package tests for fox/1.6.57.

Two consumer-level checks:

* ``test_fox`` links against the packaged ``libFOX-1.6`` and exercises the
  display-free public API (the version record and ``FXString``).
* ``reswrap`` - upstream's resource compiler - is executed on a small resource
  file.  Downstream projects (rezound) run it from their build system, so the
  packaged tool must be present and functional, not just the library.
"""

import os
import shutil

from conan import ConanFile
from conan.errors import ConanException
from conan.tools.cmake import CMake, CMakeDeps, CMakeToolchain, cmake_layout
from conan.tools.env import VirtualRunEnv
from conan.tools.files import replace_in_file


class FoxTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"
    exports_sources = "CMakeLists.txt", "test_fox.cpp", "resources/*"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def layout(self):
        cmake_layout(self)

    def generate(self):
        CMakeDeps(self).generate()
        tc = CMakeToolchain(self)
        if str(self.settings.os) == "OHOS":
            tc.cache_variables["CMAKE_CXX_COMPILER"] = self._compiler_executable(
                "cpp", "clang++"
            )
        tc.generate()
        if str(self.settings.os) == "OHOS":
            self._patch_cmake_toolchain_compilers()
        VirtualRunEnv(self).generate()

    def build(self):
        cmake = CMake(self)
        cmake.configure()
        cmake.build()

    def test(self):
        test_bin = os.path.join(self.cpp.build.bindirs[0], "test_fox")
        self.run(test_bin, env="conanrun")
        self._test_reswrap()

    def _test_reswrap(self):
        reswrap = self._packaged_tool("reswrap")
        resource = os.path.join(self.source_folder, "resources", "sample.txt")
        if not os.path.isfile(resource):
            raise ConanException(f"test resource is missing: {resource}")
        output = os.path.join(self.build_folder, "reswrap-sample.cpp")
        self.run(f'"{reswrap}" -o "{output}" "{resource}"')
        if not os.path.isfile(output) or os.path.getsize(output) == 0:
            raise ConanException("reswrap produced no output")
        with open(output, "r", encoding="utf-8", errors="replace") as handle:
            generated = handle.read()
        # reswrap names the emitted array after the input file (sample.txt ->
        # sample) and declares it as an unsigned char array.
        if "const unsigned char sample[]" not in generated:
            raise ConanException(
                f"reswrap output is missing the expected array: {generated[:200]!r}"
            )
        # reswrap emits the resource as hex bytes wrapped every 16 of them, so the
        # bytes have to be compared after the line wrapping is taken out.
        with open(resource, "rb") as handle:
            content = handle.read()
        emitted = generated.replace(" ", "").replace("\n", "").replace("\r", "")
        expected = ",".join(f"0x{byte:02x}" for byte in content)
        if expected not in emitted:
            raise ConanException(
                f"reswrap output does not carry the resource bytes: {emitted[:200]!r}"
            )

    def _packaged_tool(self, name):
        for _, dependency in self.dependencies.items():
            if not dependency.package_folder:
                continue
            candidate = os.path.join(dependency.package_folder, "bin", name)
            if os.path.isfile(candidate):
                return candidate
        raise ConanException(f"{name} is missing from the installed package")

    def _compiler_executable(self, key, fallback_name):
        executables = self.conf.get(
            "tools.build:compiler_executables",
            default={},
            check_type=dict,
        ) or {}
        configured = executables.get(key)
        if configured and os.path.isfile(configured):
            return configured
        found = shutil.which(fallback_name)
        return found or configured or fallback_name

    def _patch_cmake_toolchain_compilers(self):
        toolchain = os.path.join(self.generators_folder, "conan_toolchain.cmake")
        replacements = {
            "/data/service/hnp/bin/clang++": self._compiler_executable(
                "cpp", "clang++"
            ),
            "/data/service/hnp/bin/clang": self._compiler_executable("c", "clang"),
        }
        for old, new in replacements.items():
            replace_in_file(self, toolchain, old, new, strict=False)
