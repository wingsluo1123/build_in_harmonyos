#!/usr/bin/env python3
"""Conan consumer test for typst 0.15.1 (Rust binary package).

Layers:
  1. package integrity — the packaged `typst` executable exists;
  2. consumer smoke + HarmonyOS traits — test_typst.py runs the binary and
     asserts AArch64 / musl loader / OHOS code signature / real compilation;
  3. dependency functional test — test_openssl.c is compiled against the conan
     `openssl` package (typst links it statically, so nothing in the packaged
     binary proves the dependency works at runtime) and executed on HarmonyOS.
"""
import os
import shutil
import sys

from conan import ConanFile
from conan.tools.build import can_run
from conan.tools.layout import basic_layout


class TypstTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"
    test_type = "explicit"
    generators = "VirtualRunEnv"
    exports_sources = "test_typst.py", "test_openssl.c"

    def requirements(self):
        self.requires(self.tested_reference_str)
        # Declared explicitly so its package folder is resolvable here: typst
        # links OpenSSL statically, so nothing in the packaged binary proves it
        # works at runtime. Same version as typst's own requirement, so the
        # binary is shared, not rebuilt.
        self.requires("openssl/3.5.8.1")

    def layout(self):
        basic_layout(self)

    def _ohos_cc(self):
        candidates = []
        try:
            conf = self.conf.get("tools.build:compiler_executables")
            if isinstance(conf, dict):
                candidates.append(conf.get("c"))
        except Exception:  # noqa: BLE001
            pass
        candidates += [
            shutil.which("aarch64-unknown-linux-ohos-clang"),
            "/data/service/hnp/ohos-sdk.org/ohos-sdk_26.0.0.18/ohos/native/llvm/bin/"
            "aarch64-unknown-linux-ohos-clang",
            shutil.which("clang"),
        ]
        for candidate in candidates:
            if candidate and os.path.isfile(candidate):
                return candidate
        return None

    def _compile_openssl_test(self):
        cc = self._ohos_cc()
        dep = self.dependencies["openssl"]
        if cc is None:
            self.output.warning("openssl dependency test skipped: no OHOS cc")
            return None
        source = os.path.join(self.source_folder, "test_openssl.c")
        binary = os.path.join(self.build_folder, "test_openssl")
        incs = [os.path.join(dep.package_folder, d)
                for d in (dep.cpp_info.includedirs or ["include"])]
        libs = [os.path.join(dep.package_folder, d)
                for d in (dep.cpp_info.libdirs or ["lib"])]
        cmd = " ".join(
            ['"%s"' % cc, '"%s"' % source, "-o", '"%s"' % binary]
            + ['-I"%s"' % i for i in incs]
            + ['-L"%s"' % l for l in libs]
            + ["-lssl", "-lcrypto", "-ldl", "-lpthread"]
        )
        self.output.info(f"compiling openssl dependency test: {cmd}")
        if self.run(cmd, env="conanbuild", ignore_errors=True) != 0:
            raise AssertionError("openssl dependency test failed to compile")
        if not os.path.isfile(binary):
            raise AssertionError(f"openssl dependency test binary missing: {binary}")
        os.chmod(binary, 0o755)
        return binary

    def test(self):
        package_folder = self.dependencies["typst"].package_folder
        exe = os.path.join(package_folder, "bin", "typst")
        if not os.path.isfile(exe):
            raise AssertionError(f"Missing typst executable: {exe}")

        if not can_run(self):
            self.output.info("Cross-building: verified package layout only.")
            return

        script = os.path.join(self.source_folder, "test_typst.py")
        result = self.run(
            f'PACKAGE_FOLDER="{package_folder}" "{sys.executable}" "{script}"',
            env="conanrun", ignore_errors=True)
        if result != 0:
            raise AssertionError(f"typst test_package failed with exit code {result}")

        dep_test = self._compile_openssl_test()
        if dep_test is None:
            self.output.warning("SKIP: openssl dependency functional test")
            return
        result = self.run(f'"{dep_test}"', env="conanrun", ignore_errors=True)
        if result != 0:
            raise AssertionError(
                f"openssl dependency functional test failed with exit code {result}")
