#!/usr/bin/env python3
"""Conan test_package for trimadap 0.1-4 — L1 consumer test.

两层验证，均真实执行打包出的 `trimadap-mt`：

1) `test_consumer.c` —— **完整消费者端到端用例**（鸿蒙/PC 特有覆盖）：
   把 trimadap 当作下机 gzip FASTQ 的流式接头过滤器接入管线——
   gzip 输入 → `-p 4` 多线程流式修剪 → 下游消费者独立解析校验，
   再走一遍 `-t 8` 剪切流水线并核对产出等于已知插入片段。
   该用例覆盖 OHOS 平台相关路径：OHOS zlib（gzFile 读写）、OHOS pthread/kthread
   多线程，以及 aarch64 上本适配新增的标量比对内核（SSE2 属 x86 路径）。
2) `test_trimadap.sh` —— 上游样本数据与构造型用例的 CLI 行为断言（13 条）。
"""
import os

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration


class TrimadapTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"
    generators = "VirtualBuildEnv", "VirtualRunEnv"
    test_type = "explicit"

    def requirements(self):
        self.requires(self.tested_reference_str)
        # 消费者用例需要以 gzip 写出"下机数据"形态的输入；zlib 与主包同源依赖，
        # CI 已缓存，不引入额外构建。
        self.requires("zlib/1.3.1")

    def validate(self):
        if str(self.settings.os) not in ("Linux", "OHOS"):
            raise ConanInvalidConfiguration(
                f"trimadap test supports Linux and OHOS only, got {self.settings.os}"
            )

    def layout(self):
        # 生成器与环境脚本落在 build/，不污染归档的 test_package 目录
        self.folders.build = "build"
        self.folders.generators = "build/conan"

    def _compiler(self):
        compilers = self.conf.get(
            "tools.build:compiler_executables", default={}, check_type=dict
        ) or {}
        return compilers.get("c") or "clang"

    def _dependency_paths(self, dependency, field):
        paths = []
        for path in getattr(dependency.cpp_info, field, []):
            paths.append(
                path
                if os.path.isabs(path)
                else os.path.join(dependency.package_folder, path)
            )
        return paths

    def _trimadap_binary(self):
        return os.path.join(
            self.dependencies["trimadap"].package_folder, "bin", "trimadap-mt"
        )

    def build(self):
        """编译消费者程序（真实消费者视角的可执行文件）。"""
        zlib = self.dependencies["zlib"]
        include_flags = [f"-I{p}" for p in self._dependency_paths(zlib, "includedirs")]
        library_flags = [f"-L{p}" for p in self._dependency_paths(zlib, "libdirs")]

        source = os.path.join(self.source_folder, "test_consumer.c")
        target = os.path.join(self.build_folder, "test_consumer")
        # R33: 编译器取自 Conan conf，不裸用 shell 变量
        self.run(" ".join([
            f'"{self._compiler()}"',
            "-O2 -Wall -o",
            f'"{target}"',
            f'"{source}"',
            " ".join(include_flags),
            " ".join(library_flags),
            "-lz",
        ]))

    def test(self):
        binary = self._trimadap_binary()
        if not os.path.isfile(binary):
            raise ConanInvalidConfiguration(
                f"trimadap binary not found in package: {binary}"
            )

        # 1) 完整消费者端到端用例（鸿蒙/PC 特有覆盖）
        consumer = os.path.join(self.build_folder, "test_consumer")
        workdir = os.path.join(self.build_folder, "consumer-work")
        self.run(f'"{consumer}" "{binary}" "{workdir}"',
                 cwd=self.build_folder, env="conanrun")

        # 2) CLI 行为断言（上游样本数据 + 构造型用例）
        script = os.path.join(self.recipe_folder, "test_trimadap.sh")
        shell = os.environ.get("CONFIG_SHELL") or "sh"
        self.run(f'"{shell}" "{script}" "{binary}" "{self.recipe_folder}"',
                 cwd=self.build_folder, env="conanrun")
