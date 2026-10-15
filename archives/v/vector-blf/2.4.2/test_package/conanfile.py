#!/usr/bin/env python3
"""Conan test_package — consumer-side L1 tests for vector-blf.

File location: archives/v/vector-blf/2.4.2/test_package/conanfile.py
CI runs this automatically through `conan create`.

Two cases are executed, in order:

1. ``test_vector_blf``   — L1 API round trip: 4000 CAN messages written and read
   back field by field (>128 KiB, hence several zlib compressed log containers).
2. ``test_ohos_e2e``     — HarmonyOS-specific end-to-end consumer case:
   construct 6000 deterministic messages, write them to the OHOS filesystem
   ($TMPDIR; /tmp is read-only on OHOS, E002), read the whole stream back twice
   and emit a deterministic report.
   ``ref_blf_parser`` then re-decodes the very same file **without linking
   vector-blf** (own BLF container/object parser + zlib) and ``test_compare``
   cross-checks both reports field by field and enforces the container /
   compression-method invariants.
3. ``ohos_dlopen_probe`` — OHOS ELF loadability: a binary that does **not** link
   vector-blf, so the loader maps the packaged ``libVector_BLF.so`` for the first
   time inside that process.

``zlib`` is required explicitly so that the independent parser can inflate the
log containers itself.
"""
import os

from conan import ConanFile
from conan.tools.cmake import CMake, cmake_layout


class VectorBlfTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"
    generators = "CMakeDeps", "CMakeToolchain"

    def requirements(self):
        self.requires(self.tested_reference_str)
        # needed by the independent reference parser (test harness only)
        self.requires("zlib/1.3.2.1")

    def layout(self):
        cmake_layout(self)

    def build(self):
        cmake = CMake(self)
        cmake.configure()
        cmake.build()

    def test(self):
        bindir = self.cpp.build.bindirs[0]
        tmpdir = os.environ.get("TMPDIR") or "."
        blf = os.path.join(tmpdir, "vector_blf_ohos_e2e.blf")
        report = os.path.join(bindir, "ohos_e2e.report")
        ref_report = os.path.join(bindir, "ohos_e2e_ref.report")

        # 1) API round trip
        self.run(f'"{os.path.join(bindir, "test_vector_blf")}"', env="conanrun")
        # 2) OHOS end-to-end consumer case (writes the BLF file on $TMPDIR)
        self.run(f'"{os.path.join(bindir, "test_ohos_e2e")}" "{report}" "{blf}"',
                 env="conanrun")
        # 3) independent reference decoder for the same file
        self.run(f'"{os.path.join(bindir, "ref_blf_parser")}" "{blf}" "{ref_report}"',
                 env="conanrun")
        # 4) cross-check both reports + enforce container/compression invariants
        self.run(f'"{os.path.join(bindir, "test_compare")}" "{report}" "{ref_report}"',
                 env="conanrun")
        # 5) OHOS ELF loadability of the packaged library (probe does not link it)
        dep = self.dependencies[self.tested_reference_str]
        lib = os.path.join(dep.package_folder, "lib", "libVector_BLF.so")
        self.run(f'"{os.path.join(bindir, "ohos_dlopen_probe")}" "{lib}"',
                 env="conanrun")
