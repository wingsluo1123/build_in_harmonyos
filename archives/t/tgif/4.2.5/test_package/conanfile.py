#!/usr/bin/env python3
"""Consumer tests for tgif 4.2.5 (X11/Motif-style 2-D drawing tool).

Two layers:

* ``test_tgif.py`` — executes the packaged ``bin/tgif`` through its real CLI
  (the version query, and the display-less startup path on a device with no
  X server) and asserts the exact upstream output.
* ``_verify_ohos_elf()`` — asserts the packaged ELF is an AArch64 binary that
  really resolved the Conan X11 stack, and that it carries **exactly one**
  ``.codesign`` section.
"""

import os
import shutil
import subprocess

from conan import ConanFile


class TgifTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"
    test_type = "explicit"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def test(self):
        package = self.dependencies["tgif"]
        binary = os.path.join(package.package_folder, "bin", "tgif")
        if not os.path.isfile(binary):
            raise RuntimeError(f"packaged tgif binary is missing: {binary}")

        python = shutil.which("python3") or "python3"
        script = os.path.join(self.source_folder, "test_tgif.py")
        self.run(self._command(python, script, binary), env="conanrun")
        self._verify_ohos_elf(binary)

    @staticmethod
    def _command(*arguments):
        return " ".join(f'"{value}"' for value in arguments)

    def _verify_ohos_elf(self, binary):
        readelf = shutil.which("llvm-readelf") or shutil.which("readelf")
        if not readelf:
            raise RuntimeError("readelf is required for the OHOS ELF contract test")
        header = subprocess.run(
            [readelf, "-h", binary],
            check=True,
            capture_output=True,
            text=True,
            timeout=30,
        ).stdout
        dynamic = subprocess.run(
            [readelf, "-d", binary],
            check=True,
            capture_output=True,
            text=True,
            timeout=30,
        ).stdout
        if "AArch64" not in header:
            raise RuntimeError("tgif is not an AArch64 ELF")
        # The X11 client stack must be resolved dynamically through Conan — a
        # build that quietly fell back to (non-existent) system X11 would fail.
        needed = [
            line.split("[", 1)[1].split("]", 1)[0]
            for line in dynamic.splitlines()
            if "(NEEDED)" in line and "[" in line
        ]
        for name in ("libX11.so", "libXt.so"):
            if not any(entry.startswith(name) for entry in needed):
                raise RuntimeError(
                    f"missing expected runtime dependency: {name} (DT_NEEDED={needed})"
                )
        # ── HarmonyOS-specific assertion (platform-unique, fail-closed) ──────
        # A signed HarmonyOS ELF carries exactly one `.codesign` section in its
        # section table: the OHOS toolchain's ld.lld writes it by default
        # (`--code-sign` — verified on the target: plain clang output yields 1,
        # `-Wl,--no-code-sign` yields 0), and package() additionally re-signs
        # with the SDK's binary-sign-tool. A generic Linux ELF has no such
        # section, so this assertion can only hold on a HarmonyOS ELF — it is a
        # platform property, not a generic ELF/CLI contract. It is fail-closed:
        # an unsigned artifact yields 0 and the test fails loudly instead of
        # silently passing.
        if str(self.settings.os) != "OHOS":
            self.output.info(
                f"skipped: .codesign assertion is HarmonyOS-only (os={self.settings.os})"
            )
            self.output.info("HarmonyOS AArch64 ELF contract: PASS (non-OHOS os: codesign skipped)")
            return
        sections = subprocess.run(
            [readelf, "-S", binary],
            check=True,
            capture_output=True,
            text=True,
            timeout=30,
        ).stdout
        codesign = sections.count(".codesign")
        if codesign != 1:
            raise RuntimeError(
                "HarmonyOS signature segment check failed: expected exactly 1 "
                f"'.codesign' section, found {codesign} — packaged binary is not "
                "signed for HarmonyOS"
            )
        self.output.info("HarmonyOS .codesign segment (signed): PASS")
        self.output.info("HarmonyOS AArch64 ELF contract: PASS")
