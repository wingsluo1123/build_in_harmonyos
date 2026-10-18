#!/usr/bin/env python3
"""Consumer tests for maim 5.8.0 (X11 screenshot CLI)."""

import os
import shutil
import subprocess

from conan import ConanFile


class MaimTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"
    test_type = "explicit"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def test(self):
        package = self.dependencies["maim"]
        binary = os.path.join(package.package_folder, "bin", "maim")
        if not os.path.isfile(binary):
            raise RuntimeError(f"packaged maim binary is missing: {binary}")

        python = shutil.which("python3") or "python3"
        script = os.path.join(self.source_folder, "test_maim.py")
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
            raise RuntimeError("maim is not an AArch64 ELF")
        expected = [
            "libX11.so",
            "libXext.so",
            "libXrender.so",
            "libXfixes.so",
            "libXcomposite.so",
            "libXrandr.so",
            "libpng",
            "libjpeg.so",
            "libwebp.so",
        ]
        for name in expected:
            if name not in dynamic:
                raise RuntimeError(f"missing expected runtime dependency: {name}")
        for forbidden in ("libGL.so", "libGLX.so", "libGLEW.so"):
            if forbidden in dynamic:
                raise RuntimeError(f"unexpected GLX dependency: {forbidden}")
        # ── HarmonyOS 特有断言（真实鸿蒙特有测试）────────────────────────────
        # 产物必须已由 binary-sign-tool 自签名：ELF 段表中恰好 1 个 `.codesign`。
        # 该段只由 OHOS 签名工具写入 —— 通用 Linux ELF 没有它，故这条断言在非 OHOS
        # 平台必然失败，属平台特有属性而非通用 ELF 契约。
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
                "HarmonyOS signature segment check failed: expected exactly 1 '.codesign' "
                f"section, found {codesign} — packaged binary is not signed for HarmonyOS"
            )
        self.output.info("HarmonyOS .codesign segment (signed): PASS")
        self.output.info("HarmonyOS AArch64 ELF contract: PASS")
