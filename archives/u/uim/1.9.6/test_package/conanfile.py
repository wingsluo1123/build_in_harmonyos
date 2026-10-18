#!/usr/bin/env python3
"""Conan test_package — OHOS HMDFS-safe.

HMDFS doesn't allow execve() of any script (even with ELF shebang).
Avoid make/cmake --build entirely — compile directly with clang.
"""
import os
import subprocess
from pathlib import Path

from conan import ConanFile


class UimTestConan(ConanFile):
    # 不声明 CMakeDeps/CMakeToolchain：本用例直接调用 clang 编译，
    # 生成器产物（*.cmake）既无消费方，又会在工作区留下未跟踪文件。
    settings = "os", "compiler", "build_type", "arch"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def layout(self):
        pass  # simple layout, no cmake_layout

    def build(self):
        # OHOS HMDFS: avoid make/cmake --build (execve script issues).
        # Compile test.c directly with real-ELF clang.
        src = Path(self.source_folder)
        build = Path(self.build_folder)
        self.output.info(f"src={src}, build={build}")
        build.mkdir(parents=True, exist_ok=True)

        # Get uim package include/lib paths from conan dependencies
        uim_dep = self.dependencies["uim"]
        inc_dir = uim_dep.cpp_info.includedirs[0] if uim_dep.cpp_info.includedirs else ""
        lib_dir = uim_dep.cpp_info.libdirs[0] if uim_dep.cpp_info.libdirs else ""

        # Real ELF clang path (HMDFS can't execve symlinks)
        clang_path = "/data/service/hnp/ohos-sdk.org/ohos-sdk_26.0.0.18/ohos/native/llvm/bin/clang"

        # Compile test.c → build/test.o
        obj_file = build / "test.o"
        self.output.info(f"Compiling: {clang_path} ... -c {src}/test.c -o {obj_file}")
        result = subprocess.run([
            clang_path,
            "-O2", "-DNDEBUG",
            f"-I{inc_dir}",
            "-c", str(src / "test.c"),
            "-o", str(obj_file),
        ], capture_output=True, text=True)
        self.output.info(f"clang exit={result.returncode}")
        if result.stdout:
            self.output.info(f"clang stdout: {result.stdout}")
        if result.stderr:
            self.output.info(f"clang stderr: {result.stderr}")
        if result.returncode != 0:
            raise Exception(f"clang compile failed: {result.stderr}")

        # Link → build/test_uim
        exe_file = build / "test_uim"
        self.output.info(f"Linking: {clang_path} ... -o {exe_file}")
        result = subprocess.run([
            clang_path,
            str(obj_file),
            f"-L{lib_dir}",
            "-luim", "-luim-scm", "-luim-custom", "-lgcroots",
            "-o", str(exe_file),
        ], capture_output=True, text=True)
        self.output.info(f"link exit={result.returncode}")
        if result.stderr:
            self.output.info(f"link stderr: {result.stderr}")
        if result.returncode != 0:
            raise Exception(f"link failed: {result.stderr}")

        self.output.info(f"Built test executable: {exe_file}")

    def test(self):
        exe = Path(self.build_folder) / "test_uim"
        if not exe.exists():
            raise Exception(f"Test executable not found: {exe}")
        # uim_init() locates its Scheme runtime data via these two env vars
        # (documented in uim.c: LIBUIM_SYSTEM_SCM_FILES / LIBUIM_SCM_FILES).
        uim_dep = self.dependencies["uim"]
        resdirs = uim_dep.cpp_info.resdirs or []
        data_dir = Path(resdirs[0]) if resdirs else None
        env = dict(os.environ)
        env.pop("BASH_ENV", None)
        if data_dir:
            env["LIBUIM_SYSTEM_SCM_FILES"] = str(data_dir / "system")
            env["LIBUIM_SCM_FILES"] = str(data_dir / "lib")
            self.output.info(f"LIBUIM_SYSTEM_SCM_FILES={env['LIBUIM_SYSTEM_SCM_FILES']}")
            self.output.info(f"LIBUIM_SCM_FILES={env['LIBUIM_SCM_FILES']}")
        self.output.info(f"Running consumer test: {exe}")
        result = subprocess.run([str(exe)], capture_output=True, text=True, env=env)
        self.output.info(f"stdout: {result.stdout}")
        if result.stderr:
            self.output.warning(f"stderr: {result.stderr}")
        if result.returncode != 0:
            raise Exception(f"Consumer test failed with exit code {result.returncode}")
        self.output.info("Consumer test PASSED")
        # Alternatively, run the binary directly:
        # self.run(f"{os.path.join(self.cpp.build.bindirs[0], 'test_uim')}", env="conanrun")
