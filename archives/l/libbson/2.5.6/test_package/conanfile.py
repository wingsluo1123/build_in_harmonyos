#!/usr/bin/env python3
"""Conan test_package — libbson 2.5.6 (2.x package line, libbson2).

L1 consumer test: compile test_bson.c directly against the installed package
(same R33 pattern as the snowball recipe — no CMake involved, robust on both
the adaptation machine and CI workers), then run it natively on the OHOS
aarch64 host. test_bson.c mirrors the upstream suite (src/libbson/tests/,
464 TestSuite_Add registrations plus 1015 JSON corpus/vector cases upstream
wires into the libmongoc test tree) at consumer level: version consistency,
all BSON type append+iterate, nested documents/arrays, BCON, JSON<->BSON
both ways incl. malformed-input error paths, serialization round-trips,
corpus canonical_bson scenarios, writer/reader round-trip, OID, decimal128,
UTF-8 validation, 1000-key large document, monotonic clock.
"""
import os

from conan import ConanFile
from conan.tools.build import can_run


class LibbsonTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"
    test_type = "explicit"
    generators = "VirtualRunEnv"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def test(self):
        # R33: compiler from Conan conf (same as main recipe), never env.
        ce = self.conf.get("tools.build:compiler_executables",
                           default={}, check_type=dict)
        cc = ce.get("c") or "clang"

        pkg = self.dependencies["libbson"].package_folder
        inc = os.path.join(pkg, "include", "bson-2.5.6")
        lib = os.path.join(pkg, "lib")
        src = os.path.join(self.source_folder, "test_bson.c")
        exe = os.path.join(self.build_folder, "test_bson")

        # 1) consumer compile+link against the installed package
        self.run(f'"{cc}" -O2 -Wall -I"{inc}" "{src}" -L"{lib}" -lbson2 -o "{exe}"')

        if can_run(self):
            # 2) library consumer binary (native OHOS arm64: runs directly),
            #    with the conanrun env (LD_LIBRARY_PATH -> package lib/)
            ret = self.run(f'"{exe}"', env="conanrun", ignore_errors=True)
            tp_passed = (ret == 0)
            print(f"HMBS_TEST_PACKAGE libbson/2.5.6: {'PASS' if tp_passed else 'FAIL'} (exit={ret})")
            if not tp_passed:
                raise Exception("test_bson consumer test FAILED")
