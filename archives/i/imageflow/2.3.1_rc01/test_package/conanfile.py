#!/usr/bin/env python3
"""Conan consumer test for imageflow 2.3.1_rc01.

Two layers (R34: the test must really depend on the package):

  1. test_imageflow.py - runs the packaged imageflow_tool against an
     embedded 32x32 PNG (base64 payload materialized at runtime; no
     tracked binary, since forge PR diffs cannot carry binary patch
     data): PNG->JPEG stretch resize (mozjpeg path), PNG->PNG width
     resize (libpng path), plus HarmonyOS traits (AArch64 ELF, OHOS musl
     loader, OHOS code signature, RUNPATH hygiene) on imageflow_tool and
     libimageflow.so;
  2. test_consumer.c - a C consumer compiled against the packaged headers and
     linked against libimageflow.so, calling the stable C ABI
     (version query + context create/destroy) to prove the shared library is
     usable from C on HarmonyOS.
"""
import os
import shutil
import sys

from conan import ConanFile
from conan.tools.build import can_run
from conan.tools.layout import basic_layout


class ImageflowTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"
    test_type = "explicit"
    generators = "VirtualRunEnv"
    exports_sources = "test_imageflow.py", "test_consumer.c"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def layout(self):
        basic_layout(self)

    def _ohos_cc(self):
        candidates = []
        try:
            conf = self.conf.get("tools.build:compiler_executables")
            if isinstance(conf, dict):
                candidates.append(conf.get("c"))
        except Exception:  # noqa: BLE001 - conf may be absent on some runners
            pass
        candidates += [
            "/data/service/hnp/bin/aarch64-unknown-linux-ohos-clang",
            "/data/service/hnp/ohos-sdk.org/ohos-sdk_26.0.0.18/ohos/native/"
            "llvm/bin/aarch64-unknown-linux-ohos-clang",
            shutil.which("aarch64-unknown-linux-ohos-clang"),
            shutil.which("clang"),
        ]
        for candidate in candidates:
            if candidate and os.path.isfile(candidate):
                return candidate
        return None

    def test(self):
        package_folder = self.dependencies["imageflow"].package_folder
        exe = os.path.join(package_folder, "bin", "imageflow_tool")
        lib = os.path.join(package_folder, "lib", "libimageflow.so")
        if not os.path.isfile(exe):
            raise AssertionError(f"Missing imageflow_tool: {exe}")
        if not os.path.isfile(lib):
            raise AssertionError(f"Missing libimageflow.so: {lib}")

        if not can_run(self):
            self.output.info("Cross-building: verified package layout only.")
            return

        script = os.path.join(self.source_folder, "test_imageflow.py")
        run_dir = os.path.join(self.build_folder, "run")
        result = self.run(
            f'PACKAGE_FOLDER="{package_folder}" TEST_RUN_DIR="{run_dir}" '
            f'"{sys.executable}" "{script}"',
            env="conanrun", ignore_errors=True)
        if result != 0:
            raise AssertionError(f"test_imageflow.py failed (rc={result})")

        cc = self._ohos_cc()
        if cc is None:
            self.output.warning("OHOS clang not found; C ABI test skipped")
            return
        test_c = os.path.join(self.source_folder, "test_consumer.c")
        consumer = os.path.join(self.build_folder, "test_consumer")
        compile_cmd = " ".join([
            f'"{cc}"', f'"{test_c}"',
            "-std=gnu11", "-Wall", "-Werror",
            f'-I"{os.path.join(package_folder, "include")}"',
            f'-L"{os.path.join(package_folder, "lib")}"',
            "-limageflow", "-Wl,-z,relro,-z,now",
            "-o", f'"{consumer}"',
        ])
        self.output.info(f"compiling C ABI consumer: {compile_cmd}")
        if self.run(compile_cmd, env="conanbuild", ignore_errors=True) != 0:
            raise AssertionError(
                "failed to compile test_consumer.c against libimageflow.so")
        if self.run(f'"{consumer}"', env="conanrun", ignore_errors=True) != 0:
            raise AssertionError(
                "C ABI consumer test failed (see output above)")
        self.output.info("C ABI consumer test OK")
