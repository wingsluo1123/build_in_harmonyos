#!/usr/bin/env python3
"""Consumer tests for quesoglc 0.7.2 (QuesoGLC, OpenGL Character Renderer).

Two layers:

* ``test_quesoglc.c`` — links against the packaged library and drives its real
  global commands (chapter 3.4 of the GLC spec): error state, context
  enumeration, creation, recognition and deletion.  The binary is executed.
* ``_verify_ohos_elf()`` — asserts the packaged shared library is an AArch64
  ELF that really resolved the Conan dependency stack (fontconfig, FreeType,
  GLU and Mesa's OSMesa) through ``DT_NEEDED``, and that it carries **exactly
  one** ``.codesign`` section (HarmonyOS-only assertion, fail-closed).
"""
import os
import shutil
import subprocess

from conan import ConanFile
from conan.tools.build import can_run
from conan.tools.cmake import CMake, CMakeDeps, CMakeToolchain, cmake_layout


class QuesoglcTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"
    test_type = "explicit"

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
        if can_run(self):
            self.run(
                os.path.join(self.cpp.build.bindirs[0], "test_quesoglc"),
                env="conanrun",
            )
        else:
            self.output.info("skipped: cannot run the consumer binary on this host")
        self._verify_ohos_elf()

    # ── packaged-artifact contract checks ────────────────────────────────
    def _packaged_library(self):
        package_folder = self.dependencies["quesoglc"].package_folder
        libdir = os.path.join(package_folder, "lib")
        candidates = []
        for name in sorted(os.listdir(libdir)):
            path = os.path.join(libdir, name)
            # The versioned real file (libGLC.so.0.0.7), not the .so symlink.
            if ".so." in name and os.path.isfile(path) and not os.path.islink(path):
                candidates.append(path)
        if not candidates:
            raise RuntimeError(
                f"no versioned shared library found under {libdir}"
            )
        return candidates

    def _verify_ohos_elf(self):
        readelf = shutil.which("llvm-readelf") or shutil.which("readelf")
        if not readelf:
            raise RuntimeError("readelf is required for the packaged ELF contract test")
        for library in self._packaged_library():
            header = subprocess.run(
                [readelf, "-h", library],
                check=True, capture_output=True, text=True, timeout=30,
            ).stdout
            dynamic = subprocess.run(
                [readelf, "-d", library],
                check=True, capture_output=True, text=True, timeout=30,
            ).stdout
            if "AArch64" not in header:
                raise RuntimeError(f"{library} is not an AArch64 ELF")
            needed = [
                line.split("[", 1)[1].split("]", 1)[0]
                for line in dynamic.splitlines()
                if "(NEEDED)" in line and "[" in line
            ]
            # A build that quietly fell back to (non-existent) system GL, or
            # that skipped a dependency, would not resolve these.
            for name in ("libOSMesa.so", "libGLU.so", "libfontconfig.so",
                         "libfreetype.so"):
                if not any(entry.startswith(name) for entry in needed):
                    raise RuntimeError(
                        f"missing expected runtime dependency: {name} "
                        f"(DT_NEEDED={needed})"
                    )
            # ── HarmonyOS-specific assertion (platform-unique, fail-closed) ──
            # A signed HarmonyOS ELF carries exactly one `.codesign` section in
            # its section table (OHOS ld.lld writes it by default; package()
            # additionally re-signs with the SDK's binary-sign-tool).  A generic
            # Linux ELF has no such section, so this can only hold on a
            # HarmonyOS ELF.  Fail-closed: an unsigned artifact yields 0 and the
            # test fails loudly instead of silently passing.
            if str(self.settings.os) != "OHOS":
                self.output.info(
                    "skipped: .codesign assertion is HarmonyOS-only "
                    f"(os={self.settings.os})"
                )
                continue
            sections = subprocess.run(
                [readelf, "-S", library],
                check=True, capture_output=True, text=True, timeout=30,
            ).stdout
            codesign = sections.count(".codesign")
            if codesign != 1:
                raise RuntimeError(
                    "HarmonyOS signature segment check failed: expected exactly "
                    f"1 '.codesign' section, found {codesign} — "
                    "packaged library is not signed for HarmonyOS"
                )
            self.output.info(
                f"HarmonyOS .codesign segment (signed): PASS — {os.path.basename(library)}"
            )
        self.output.info("HarmonyOS AArch64 ELF contract: PASS")
