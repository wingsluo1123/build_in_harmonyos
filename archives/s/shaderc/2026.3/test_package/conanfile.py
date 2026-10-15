#!/usr/bin/env python3
"""test_package for shaderc 2026.3 — L1 消费者验证。

消费者视角：链接本包静态库调用 libshaderc C API 编译着色器，
并调用本包交付的 `glslc` 命令行把 GLSL 编译为 SPIR-V。
"""
import os
import shutil
import time

from conan import ConanFile
from conan.tools.build import can_run
from conan.tools.cmake import CMake, CMakeDeps, CMakeToolchain, cmake_layout
from conan.tools.env import VirtualRunEnv

# 与主配方同款：受限 CI worker 上 CMake 的 try-compile 会瞬时 fork/exec EAGAIN
FORK_PRESSURE_MARKERS = (
    "resource temporarily unavailable",
    "can't fork",
    "cannot fork",
    "unable to fork",
    "fork failed",
    "try again",
)
_CMAKE_DIAG_FILES = (
    os.path.join("CMakeFiles", "CMakeConfigureLog.yaml"),
    os.path.join("CMakeFiles", "CMakeError.log"),
    os.path.join("CMakeFiles", "CMakeOutput.log"),
)


def _ninja_path(conanfile):
    """探测可用的 ninja；未命中返回 None，保持 conan 默认生成器。"""
    candidates = (
        os.environ.get("HMBS_NINJA"),
        conanfile.conf.get("user.hmbs:ninja_path", check_type=str),
        shutil.which("ninja"),
        "/data/service/hnp/bin/ninja",
    )
    for candidate in candidates:
        if candidate and os.path.isfile(candidate) and os.access(candidate, os.X_OK):
            return candidate
    return None


def _configure_with_fork_retry(conanfile, cmake, attempts=4, delay=20):
    """fork/exec EAGAIN 签名命中时退避重试，真实配置错误一次即抛。"""
    for attempt in range(1, attempts + 1):
        try:
            return cmake.configure()
        except Exception as exc:
            text = str(exc).lower()
            for rel in _CMAKE_DIAG_FILES:
                path = os.path.join(conanfile.build_folder, rel)
                try:
                    if os.path.isfile(path):
                        with open(path, encoding="utf-8", errors="replace") as handle:
                            text += handle.read()[-12000:].lower()
                except OSError:
                    pass
            if attempt >= attempts or not any(
                marker in text for marker in FORK_PRESSURE_MARKERS
            ):
                raise
            wait = delay * attempt
            conanfile.output.warning(
                "test_package CMake.configure 命中 worker fork/资源压力（第 {}/{} 次）："
                "{}；{} 秒后重试".format(attempt, attempts, exc, wait)
            )
            for rel in ("CMakeCache.txt", "CMakeFiles"):
                target = os.path.join(conanfile.build_folder, rel)
                try:
                    if os.path.isdir(target):
                        shutil.rmtree(target)
                    elif os.path.exists(target):
                        os.unlink(target)
                except OSError:
                    pass
            time.sleep(wait)


class ShadercTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"
    test_type = "explicit"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def layout(self):
        cmake_layout(self, generator="Ninja" if _ninja_path(self) else None)

    def generate(self):
        CMakeDeps(self).generate()
        ninja = _ninja_path(self)
        toolchain = CMakeToolchain(self, generator="Ninja" if ninja else None)
        if ninja:
            toolchain.cache_variables["CMAKE_MAKE_PROGRAM"] = ninja
        toolchain.generate()
        VirtualRunEnv(self).generate()

    def build(self):
        cmake = CMake(self)
        _configure_with_fork_retry(self, cmake)
        cmake.build()

    def test(self):
        if not can_run(self):
            self.output.warning("当前平台无法运行交叉编译产物，跳过运行期验证")
            return
        # OHOS: /system/bin/sh (mksh) 无法执行 ELF，统一由 bash 驱动；
        # test() 的工作目录是构建目录，故脚本与产物一律用绝对路径。
        bash = os.environ.get("CONFIG_SHELL", "/data/service/hnp/bin/bash")
        script = os.path.join(self.source_folder, "test.sh")
        test_exe = os.path.abspath(os.path.join(self.cpp.build.bindirs[0], "test_shaderc"))
        glslc = os.path.join(
            self.dependencies[self.tested_reference_str].package_folder, "bin", "glslc"
        )
        self.run(f'"{bash}" "{script}" "{test_exe}" "{glslc}"', env="conanrun")
