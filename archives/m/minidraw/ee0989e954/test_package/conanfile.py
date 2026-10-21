#!/usr/bin/env python3
"""test_package — minidraw (header-only) consumer tests.

Compiles and runs two real consumer translation units on HarmonyOS PC:
  1. test.c     — core UTF-8/UTF-16/UTF-32 text API roundtrip checks.
  2. test_e2e.c — end-to-end drawing pipeline: custom software rasterizer
                  backend drives md_init -> md_gc_init -> clear/rect/fill/
                  line/stroke -> md_gc_get_image_data -> pixel validation
                  -> release (r02 rule12 E2E requirement).
"""
import os

from conan import ConanFile
from conan.tools.build import cross_building


class MinidrawTestConan(ConanFile):
    settings = "os", "arch", "compiler", "build_type"
    test_type = "explicit"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def test(self):
        if cross_building(self):
            return  # CI 交叉场景下不本地运行，仅验证打包
        cc = os.environ.get("CC", "clang")
        dep = self.dependencies["minidraw"]
        include_dirs = [os.path.join(dep.package_folder, d) for d in dep.cpp_info.includedirs]
        inc_flags = " ".join(f"-I{d}" for d in include_dirs)
        # 1) 核心文本 API 消费者测试
        self.run(f"{cc} -std=c11 -Wall -Wextra {inc_flags} -o test_minidraw test.c -lm -ldl")
        self.run("./test_minidraw")
        # 2) 端到端绘制消费者测试（r02 rule12）
        self.run(f"{cc} -std=c11 -Wall -Wextra {inc_flags} -o test_minidraw_e2e test_e2e.c -lm -ldl")
        self.run("./test_minidraw_e2e")