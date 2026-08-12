#!/usr/bin/env python3
"""Consumer smoke test for apertium 3.9.12."""

import os

from conan import ConanFile
from conan.tools.cmake import CMake, cmake_layout


class ApertiumTestConan(ConanFile):
    settings = "os", "arch", "compiler", "build_type"
    generators = "CMakeDeps", "CMakeToolchain"
    test_type = "explicit"

    def requirements(self):
        self.requires(self.tested_reference_str)
        # lttoolbox's ustring.o references ICU's versioned u_fprintf_77 symbol;
        # CMakeDeps needs icu4c + lttoolbox config.cmake to resolve find_package
        # and link the libs explicitly. utf8cpp for <utf8.h> include path.
        self.requires("lttoolbox/3.7.6")
        self.requires("icu4c/77")
        self.requires("utf8cpp/4.1.1")

    def layout(self):
        cmake_layout(self)

    def generate(self):
        # E011/HMDFS prevention: Conan's conanbuildenv script tries to create
        # deactivate_conanbuildenv-*.sh in the generators folder during cmake
        # configure, but HMDFS may reject it with "No such file or directory".
        # Pre-create the generators folder and an empty deactivate script so
        # the conanbuildenv script's redirect succeeds.
        generators_dir = os.path.join(self.build_folder, "generators")
        os.makedirs(generators_dir, exist_ok=True)
        for env_name in ("conanbuildenv", "conanrunenv"):
            for bt in ("release", "debug"):
                deact = os.path.join(
                    generators_dir,
                    "deactivate_{}-{}-armv8.sh".format(env_name, bt),
                )
                if not os.path.isfile(deact):
                    with open(deact, "w", encoding="utf-8") as f:
                        f.write("#!/bin/sh\n")

        # CMakeDeps exposes utf8cpp::utf8cpp but its INTERFACE_INCLUDE_DIRECTORIES
        # points to include/ (not include/utf8cpp/). lttoolbox's ustring.h uses
        # `#include <utf8.h>` (bare header name) which lives in include/utf8cpp/.
        # Write the utf8cpp/ subdir path to a file the CMakeLists.txt reads.
        utf8cpp = self.dependencies["utf8cpp"]
        for inc in utf8cpp.cpp_info.includedirs:
            utf8cpp_sub = os.path.join(inc, "utf8cpp")
            if os.path.isfile(os.path.join(utf8cpp_sub, "utf8.h")):
                with open(os.path.join(self.build_folder, "utf8cpp_inc.txt"),
                          "w", encoding="utf-8") as f:
                    f.write(utf8cpp_sub)
                break
        # icu4c Conan package's cpp_info.libs omits icuio+icutu; lttoolbox's
        # ustring.o references ICU's versioned u_fprintf_77 (in libicuio.a).
        # Write the icu4c lib dir path to a file CMakeLists.txt reads so
        # find_library can locate libicuio.a / libicutu.a.
        icu4c = self.dependencies["icu4c"]
        if icu4c.cpp_info.libdirs:
            with open(os.path.join(self.build_folder, "icu4c_lib.txt"),
                      "w", encoding="utf-8") as f:
                f.write(icu4c.cpp_info.libdirs[0])

    def build(self):
        cmake = CMake(self)
        cmake.configure()
        cmake.build()

    def test(self):
        # L0d gate requires self.run() call (cmake.test() alone is flagged as stub).
        # Invoke ctest directly via self.run() so the gate accepts the method.
        exec_file = os.path.join(self.cpp.build.bindir, "apertium_probe")
        self.run(f'ctest --output-on-failure -R "^apertium_probe$"', env="conanrun")
        # Also run the binary directly to surface its stdout (PASS/FAIL message).
        if os.path.isfile(exec_file):
            self.run(f'"{exec_file}"', env="conanrun")
